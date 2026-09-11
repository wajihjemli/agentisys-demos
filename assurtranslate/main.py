"""
AssurTranslate — Traduit les échanges avec un assuré non francophone, en gardant le vocabulaire technique de l'assurance.
POC — Wajih Jemli
"""

import io
import os

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

LANGUES = {
    "fr": {"label": "🇫🇷 Français", "tts": "fr"},
    "en": {"label": "🇬🇧 English", "tts": "en"},
    "ar": {"label": "🇸🇦 العربية", "tts": "ar"},
    "it": {"label": "🇮🇹 Italiano", "tts": "it"},
    "es": {"label": "🇪🇸 Español", "tts": "es"},
    "de": {"label": "🇩🇪 Deutsch", "tts": "de"},
}
TARGET_LANGUES = ["en", "ar", "it", "fr"]

EXEMPLE_TEXTE = "Bonjour, votre sinistre a bien été enregistré. Un gestionnaire vous contactera sous 48 heures."


@app.get("/")
def index():
    return FileResponse("static/index.html")


@app.get("/api/bootstrap")
def bootstrap():
    return {
        "languages": LANGUES,
        "target_languages": TARGET_LANGUES,
        "example_text": EXEMPLE_TEXTE,
    }


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

    prompt = f"""Tu es un traducteur professionnel spécialisé dans le secteur de l'assurance.
Traduis ce texte du {LANGUES[req.source]['tts']} vers le {LANGUES[req.target]['tts']}.
Conserve le ton professionnel et les termes techniques assurance.
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
