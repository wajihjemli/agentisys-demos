"""
AssurOCR — Extraction de texte (Tesseract) puis structuration (Groq) de documents métier.
Multi-secteur : le pipeline (OCR puis structuration IA avec repli par règles métier) ne change jamais,
seul le secteur actif (config dans sectorbot/) détermine le type de document, les champs à extraire
et les règles de repli — chaque secteur traite un document différent (constat, facture, ordonnance...).
POC — Wajih Jemli
"""

import os
import re
import json
import io
from pathlib import Path

from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from PIL import Image
import pytesseract
import openai

app = FastAPI(title="AssurOCR")
app.mount("/static", StaticFiles(directory="static"), name="static")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
client = openai.OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1") if GROQ_API_KEY else None

# sectorbot/ vit à la racine du repo, en frère de ce dossier — nécessite que le repo
# entier soit cloné ensemble (ce n'est pas un microservice isolé).
SECTORBOT_DIR = Path(__file__).parent.parent / "sectorbot"

with open(SECTORBOT_DIR / "assurocr.config.json", "r", encoding="utf-8") as f:
    _config = json.load(f)
SECTORS = _config["sectors"]
DEFAULT_SECTOR = _config["default_sector"]

current_sector = DEFAULT_SECTOR


@app.get("/")
def index():
    return FileResponse("static/index.html")


@app.get("/api/sectors")
def list_sectors():
    return {
        "sectors": {sid: {"tool_name": c["tool_name"], "icon": c["icon"], "tagline": c["tagline"]} for sid, c in SECTORS.items()},
        "default": DEFAULT_SECTOR,
    }


class SectorRequest(BaseModel):
    sector: str


@app.post("/api/sector")
def set_sector(req: SectorRequest):
    global current_sector
    if req.sector not in SECTORS:
        return {"error": "Secteur inconnu."}
    current_sector = req.sector
    return sector_payload(current_sector)


def sector_payload(sector_id: str) -> dict:
    cfg = SECTORS[sector_id]
    return {
        "sector": sector_id,
        "tool_name": cfg["tool_name"],
        "icon": cfg["icon"],
        "tagline": cfg["tagline"],
        "document_label": cfg["document_label"],
        "extracts_summary": cfg["extracts_summary"],
        "field_labels": cfg["field_labels"],
    }


@app.get("/api/bootstrap")
def bootstrap():
    return sector_payload(current_sector)


@app.post("/api/ocr")
async def ocr(file: UploadFile = File(...)):
    """Étape 1 : lecture du document via Tesseract (local, pas de dépendance externe)."""
    contents = await file.read()
    image = Image.open(io.BytesIO(contents))
    text = pytesseract.image_to_string(image, lang="fra")
    return {"text": text.strip()}


class StructureRequest(BaseModel):
    text: str


def rule_based_fallback(text: str, sector_id: str) -> dict:
    """Étape 3 : repli par règles métier si l'API n'est pas disponible ou si un champ manque."""
    cfg = SECTORS[sector_id]
    fields = {k: None for k in cfg["fields"]}
    for field, pattern in cfg.get("field_patterns", {}).items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            fields[field] = match.group(0).strip()
    return fields


@app.post("/api/structure")
def structure(req: StructureRequest):
    """Étape 2 : structuration du texte libre en champs — via un moteur IA si la clé est
    configurée, sinon repli automatique sur des règles métier (étape 3)."""
    cfg = SECTORS[current_sector]
    fields_list = cfg["fields"]

    if not client:
        return {"fields": rule_based_fallback(req.text, current_sector), "fallback_used": True}

    prompt = f"""Tu travailles pour un(e) {cfg['persona']}. Extrait les informations suivantes de ce document ({cfg['document_label']}),
au format JSON strict avec exactement ces clés : {", ".join(fields_list)}.
Si une information est absente, mets la valeur null. Ne réponds qu'avec le JSON, rien d'autre.

Texte du document :
{req.text}"""

    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        raw = response.choices[0].message.content.strip()
        raw = re.sub(r"^```json|```$", "", raw, flags=re.MULTILINE).strip()
        fields = json.loads(raw)
        fallback_used = False
    except Exception:
        fields = rule_based_fallback(req.text, current_sector)
        fallback_used = True

    fallback = rule_based_fallback(req.text, current_sector)
    for k in fields_list:
        if not fields.get(k) and fallback.get(k):
            fields[k] = fallback[k]
            fallback_used = True

    return {"fields": fields, "fallback_used": fallback_used}
