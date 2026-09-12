"""
AssurTranslate — Traduit les échanges avec un assuré non francophone, en gardant le vocabulaire technique de l'assurance.
Multi-secteur : le moteur (traduction contextuelle + TTS, langues supportées) ne change jamais, seul le secteur actif
(config dans sectorbot/) détermine le nom affiché et le texte d'exemple.
POC — Wajih Jemli
"""

import io
import json
import os
from pathlib import Path

import openai
from fastapi import FastAPI
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from gtts import gTTS
from pydantic import BaseModel

app = FastAPI(title="AssurTranslate")
app.mount("/static", StaticFiles(directory="static"), name="static")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
client = openai.OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1") if GROQ_API_KEY else None

# sectorbot/ vit à la racine du repo, en frère de ce dossier — nécessite que le repo
# entier soit cloné ensemble (ce n'est pas un microservice isolé).
SECTORBOT_DIR = Path(__file__).parent.parent / "sectorbot"

with open(SECTORBOT_DIR / "assurtranslate.config.json", "r", encoding="utf-8") as f:
    _config = json.load(f)
SECTORS = _config["sectors"]
DEFAULT_SECTOR = _config["default_sector"]

current_sector = DEFAULT_SECTOR

LANGUES = {
    "fr": {"label": "🇫🇷 Français", "tts": "fr"},
    "en": {"label": "🇬🇧 English", "tts": "en"},
    "ar": {"label": "🇸🇦 العربية", "tts": "ar"},
    "it": {"label": "🇮🇹 Italiano", "tts": "it"},
    "es": {"label": "🇪🇸 Español", "tts": "es"},
    "de": {"label": "🇩🇪 Deutsch", "tts": "de"},
}
TARGET_LANGUES = ["en", "ar", "it", "fr"]


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
        "languages": LANGUES,
        "target_languages": TARGET_LANGUES,
        "example_text": cfg["example_text"],
    }


@app.get("/api/bootstrap")
def bootstrap():
    return sector_payload(current_sector)


class TranslateRequest(BaseModel):
    text: str
    source: str
    target: str


@app.post("/api/translate")
def translate(req: TranslateRequest):
    if not client:
        return {"error": "Clé API Groq manquante. Configurez GROQ_API_KEY pour utiliser AssurTranslate."}
    if not req.text.strip():
        return {"error": "Texte requis."}
    if req.source not in LANGUES or req.target not in LANGUES:
        return {"error": "Langue non reconnue."}

    cfg = SECTORS[current_sector]
    prompt = f"""Tu es un traducteur professionnel spécialisé dans le {cfg['persona']}.
Traduis ce texte du {LANGUES[req.source]['tts']} vers le {LANGUES[req.target]['tts']}.
Conserve le ton professionnel et les termes techniques du secteur.
Ne donne QUE la traduction, sans explication.

Texte : {req.text}"""

    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        translated = response.choices[0].message.content.strip()
        return {"translated": translated}
    except Exception:
        return {"error": "La traduction a échoué. Réessayez dans un instant."}


class TtsRequest(BaseModel):
    text: str
    lang: str


@app.post("/api/tts")
def tts(req: TtsRequest):
    lang_tts = LANGUES.get(req.lang, {}).get("tts", "en")
    buffer = io.BytesIO()
    gTTS(text=req.text, lang=lang_tts, slow=False).write_to_fp(buffer)
    buffer.seek(0)
    return Response(content=buffer.read(), media_type="audio/mpeg")
