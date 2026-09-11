"""
AssurOCR — Extraction de texte (Tesseract) puis structuration (Groq) de constats de sinistre.
POC — Wajih Jemli
"""

import os
import re
import json
import io

from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel
from PIL import Image
import pytesseract
import openai

router = APIRouter()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
client = openai.OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1") if GROQ_API_KEY else None

FIELDS = ["date_sinistre", "lieu", "identite_assure", "nature_sinistre", "immatriculation", "montant_estime", "temoins", "blessures"]


@router.post("/ocr")
async def ocr(file: UploadFile = File(...)):
    """Étape 1 : lecture du document via Tesseract (local, pas de dépendance externe)."""
    contents = await file.read()
    image = Image.open(io.BytesIO(contents))
    text = pytesseract.image_to_string(image, lang="fra")
    return {"text": text.strip()}


class StructureRequest(BaseModel):
    text: str


def rule_based_fallback(text: str) -> dict:
    """Étape 3 : repli par règles métier si l'API n'est pas disponible ou si un champ manque."""
    fields = {k: None for k in FIELDS}
    date_match = re.search(r"\b(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4})\b", text)
    if date_match:
        fields["date_sinistre"] = date_match.group(1)
    plate_match = re.search(r"\b([A-Z]{2}[-\s]?\d{3}[-\s]?[A-Z]{2})\b", text.upper())
    if plate_match:
        fields["immatriculation"] = plate_match.group(1)
    amount_match = re.search(r"(\d[\d\s]{1,7})\s?(€|EUR|euros)", text, re.IGNORECASE)
    if amount_match:
        fields["montant_estime"] = amount_match.group(0).strip()
    return fields


@router.post("/structure")
def structure(req: StructureRequest):
    """Étape 2 : structuration du texte libre en champs — via un moteur IA si la clé est
    configurée, sinon repli automatique sur des règles métier (étape 3)."""
    if not client:
        return {"fields": rule_based_fallback(req.text), "fallback_used": True}

    prompt = f"""Extrait les informations suivantes de ce constat de sinistre, au format JSON strict
avec exactement ces clés : {", ".join(FIELDS)}.
Si une information est absente, mets la valeur null. Ne réponds qu'avec le JSON, rien d'autre.

Texte du constat :
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
        fields = rule_based_fallback(req.text)
        fallback_used = True

    fallback = rule_based_fallback(req.text)
    for k in FIELDS:
        if not fields.get(k) and fallback.get(k):
            fields[k] = fallback[k]
            fallback_used = True

    return {"fields": fields, "fallback_used": fallback_used}
