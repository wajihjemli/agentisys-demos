"""
AssurVoice — Callbot vocal qui recueille une déclaration de sinistre à la voix et y répond en temps réel.
POC — Wajih Jemli
"""
import io
import json
import os
import re

import edge_tts
import openai
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="AssurVoice")
app.mount("/static", StaticFiles(directory="static"), name="static")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
client = openai.OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1") if GROQ_API_KEY else None

STT_MODEL = "whisper-large-v3"
LLM_MODEL = "openai/gpt-oss-20b"

VOICES = {
    "fr-FR-DeniseNeural": "🇫🇷 Denise — Femme, chaleureuse (recommandée)",
    "fr-FR-EloiseNeural": "🇫🇷 Éloïse — Femme, douce",
    "fr-FR-HenriNeural": "🇫🇷 Henri — Homme, clair",
}

SYSTEM_PROMPT = """Tu es Eva, l'assistante virtuelle d'une compagnie d'assurance française.
Tu aides les clients à déclarer des sinistres et réponds à leurs questions.
Règles :
- Sois professionnelle, empathique et concise (max 4 phrases)
- Identifie la nature du sinistre, la date, le lieu, les dégâts
- Propose les prochaines étapes concrètes
- Si c'est une urgence (blessures, incendie), indique immédiatement le numéro d'assistance 24h/24 : 01 23 45 67 90"""

EXTRACTION_FIELDS = ["nature_sinistre", "date_sinistre", "lieu", "degats", "blessures", "contact_urgence"]


@app.get("/")
def index():
    return FileResponse("static/index.html")


@app.get("/api/bootstrap")
def bootstrap():
    return {"voices": VOICES}


@app.post("/api/transcribe")
async def transcribe(file: UploadFile = File(...)):
    if not client:
        return {"error": "Clé API Groq manquante. Configurez GROQ_API_KEY pour utiliser AssurVoice."}
    try:
        contents = await file.read()
        audio_file = io.BytesIO(contents)
        audio_file.name = file.filename or "audio.webm"
        transcript = client.audio.transcriptions.create(
            model=STT_MODEL,
            file=audio_file,
            language="fr",
            response_format="text",
        )
        text = transcript if isinstance(transcript, str) else getattr(transcript, "text", str(transcript))
        return {"text": text.strip()}
    except Exception:
        return {"error": "La transcription a échoué. Vérifiez le format audio et réessayez."}


class ReplyRequest(BaseModel):
    text: str


def extract_claim_info(text: str) -> dict:
    prompt = f"""À partir de ce message client, extrais UNIQUEMENT ces informations au format JSON strict
avec exactement ces clés : {", ".join(EXTRACTION_FIELDS)}.
Si une information est absente, mets la valeur null.

Message : {text}

Réponds UNIQUEMENT en JSON, sans texte avant ou après."""
    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        raw = response.choices[0].message.content.strip()
        raw = re.sub(r"^```json|```$", "", raw, flags=re.MULTILINE).strip()
        return json.loads(raw)
    except Exception:
        return {k: None for k in EXTRACTION_FIELDS}


@app.post("/api/reply")
def reply(req: ReplyRequest):
    if not client:
        return {"error": "Clé API Groq manquante. Configurez GROQ_API_KEY pour utiliser AssurVoice."}
    if not req.text.strip():
        return {"error": "Aucun texte à traiter."}

    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": req.text},
            ],
            temperature=0.7,
            max_tokens=300,
        )
        ai_reply = response.choices[0].message.content
        extraction = extract_claim_info(req.text)
        return {"reply": ai_reply, "extraction": extraction}
    except Exception:
        return {"error": "L'assistante n'a pas pu répondre. Réessayez dans un instant."}


class TtsRequest(BaseModel):
    text: str
    voice: str = "fr-FR-DeniseNeural"


@app.post("/api/tts")
async def tts(req: TtsRequest):
    voice = req.voice if req.voice in VOICES else "fr-FR-DeniseNeural"
    buffer = io.BytesIO()
    communicate = edge_tts.Communicate(req.text, voice)
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buffer.write(chunk["data"])
    buffer.seek(0)
    return Response(content=buffer.read(), media_type="audio/mpeg")
