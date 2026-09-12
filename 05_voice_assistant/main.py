"""
AssurVoice — Callbot vocal qui recueille une déclaration à la voix et y répond en temps réel.
Multi-secteur : la chaîne vocale (STT Whisper, LLM, extraction JSON, TTS) ne change jamais, seul le
secteur actif (config dans sectorbot/) détermine le nom et la persona de l'assistant(e), les champs
extraits et le message d'exemple.
POC — Wajih Jemli
"""
import io
import json
import os
import re
from pathlib import Path

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

# sectorbot/ vit à la racine du repo, en frère de ce dossier — nécessite que le repo
# entier soit cloné ensemble (ce n'est pas un microservice isolé).
SECTORBOT_DIR = Path(__file__).parent.parent / "sectorbot"

with open(SECTORBOT_DIR / "assurvoice.config.json", "r", encoding="utf-8") as f:
    _config = json.load(f)
SECTORS = _config["sectors"]
DEFAULT_SECTOR = _config["default_sector"]

current_sector = DEFAULT_SECTOR


def build_system_prompt(sector_id: str) -> str:
    cfg = SECTORS[sector_id]
    return f"""Tu es {cfg['assistant_name']}, l'assistant virtuel d'un(e) {cfg['persona']}.
Tu aides les clients à signaler un problème et réponds à leurs questions.
Règles :
- Sois professionnel(le), empathique et concis(e) (max 4 phrases)
- Identifie {cfg['context_description']}
- Propose les prochaines étapes concrètes
- Si c'est une urgence ({cfg['urgency_description']}), indique immédiatement le numéro d'assistance 24h/24 : {cfg['emergency_number']}"""


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
        "assistant_name": cfg["assistant_name"],
        "example_message": cfg["example_message"],
        "field_labels": cfg["field_labels"],
        "voices": VOICES,
    }


@app.get("/api/bootstrap")
def bootstrap():
    return sector_payload(current_sector)


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


def extract_claim_info(text: str, sector_id: str) -> dict:
    cfg = SECTORS[sector_id]
    fields_list = cfg["fields"]
    prompt = f"""À partir de ce message client, extrais UNIQUEMENT ces informations au format JSON strict
avec exactement ces clés : {", ".join(fields_list)}.
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
        return {k: None for k in fields_list}


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
                {"role": "system", "content": build_system_prompt(current_sector)},
                {"role": "user", "content": req.text},
            ],
            temperature=0.7,
            max_tokens=300,
        )
        ai_reply = response.choices[0].message.content
        extraction = extract_claim_info(req.text, current_sector)
        return {"reply": ai_reply, "extraction": extraction}
    except Exception:
        return {"error": "L'assistant(e) n'a pas pu répondre. Réessayez dans un instant."}


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
