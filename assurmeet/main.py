"""
AssurMeet — Résume un appel client et en extrait les actions à suivre, multi-secteur.
Le code ne change jamais : seul le secteur actif (config dans sectorbot/) détermine le nom
affiché et le transcript d'exemple. Le schéma de sortie reste identique.
POC — Wajih Jemli
"""

import json
import os
import re
from pathlib import Path

import openai
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="AssurMeet")
app.mount("/static", StaticFiles(directory="static"), name="static")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
client = openai.OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1") if GROQ_API_KEY else None

# sectorbot/ vit à la racine du repo, en frère de ce dossier — nécessite que le repo
# entier soit cloné ensemble (ce n'est pas un microservice isolé).
SECTORBOT_DIR = Path(__file__).parent.parent / "sectorbot"

with open(SECTORBOT_DIR / "assurmeet.config.json", "r", encoding="utf-8") as f:
    _config = json.load(f)
SECTORS = _config["sectors"]
DEFAULT_SECTOR = _config["default_sector"]

current_sector = DEFAULT_SECTOR


def analyze_transcript(transcript: str, sector_id: str) -> dict:
    cfg = SECTORS[sector_id]
    prompt = f"""Tu es un analyste qualité senior dans un(e) {cfg['persona']}.
Analyse ce transcript d'appel client et réponds UNIQUEMENT par un objet JSON strict (pas de texte autour, pas de markdown), avec exactement ces clés :
{{
  "resume": "résumé de l'appel en 2-3 phrases",
  "points_cles": ["liste des sujets abordés"],
  "actions": [{{"action": "...", "responsable": "...", "delai": "...", "priorite": "Haute" ou "Moyenne" ou "Basse"}}],
  "sentiment_client": {{"emotion": "émotion dominante", "satisfaction": entier de 1 à 10, "risque_depart": "Faible" ou "Modéré" ou "Élevé"}},
  "risques": ["liste des risques identifiés (non-conformité, réputation, juridique...)"],
  "promesses": ["liste des engagements pris par le conseiller"]
}}

Transcript :
{transcript}"""
    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    content = response.choices[0].message.content
    match = re.search(r"\{.*\}", content, re.DOTALL)
    return json.loads(match.group(0) if match else content)


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
        "example_transcript": cfg["example_transcript"],
    }


@app.get("/api/bootstrap")
def bootstrap():
    return sector_payload(current_sector)


class AnalyzeRequest(BaseModel):
    transcript: str


@app.post("/api/analyze")
def analyze(req: AnalyzeRequest):
    if not client:
        return {"error": "Clé API Groq manquante. Configurez GROQ_API_KEY pour utiliser cet outil."}
    try:
        result = analyze_transcript(req.transcript, current_sector)
        return {"result": result}
    except Exception:
        return {"error": "L'analyse a échoué. Réessayez dans un instant."}
