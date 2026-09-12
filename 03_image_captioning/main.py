"""
AssurVision — Estime la gravité d'un problème visible à partir d'une simple photo,
pour accélérer le premier diagnostic avant expertise.
Multi-secteur : le pipeline (analyse vision IA en 8 points structurés, détection anglais +
retraduction automatique, extraction de la gravité) ne change jamais, seul le secteur actif
(config dans sectorbot/) détermine la persona experte et le type de photo analysée.
POC — Wajih Jemli
"""
import base64
import io
import json
import os
import re
from pathlib import Path

import openai
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image
from pydantic import BaseModel

app = FastAPI(title="AssurVision")
app.mount("/static", StaticFiles(directory="static"), name="static")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
client = openai.OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1") if GROQ_API_KEY else None

VISION_MODEL = "qwen/qwen3.6-27b"
TRANSLATE_MODEL = "openai/gpt-oss-20b"

SEVERITES = ["Légère", "Modérée", "Élevée", "Totale"]

# sectorbot/ vit à la racine du repo, en frère de ce dossier — nécessite que le repo
# entier soit cloné ensemble (ce n'est pas un microservice isolé).
SECTORBOT_DIR = Path(__file__).parent.parent / "sectorbot"

with open(SECTORBOT_DIR / "assurvision.config.json", "r", encoding="utf-8") as f:
    _config = json.load(f)
SECTORS = _config["sectors"]
DEFAULT_SECTOR = _config["default_sector"]

current_sector = DEFAULT_SECTOR


def build_analysis_system_prompt(sector_id: str) -> str:
    cfg = SECTORS[sector_id]
    return (
        "You are an expert analyzing damage or defects in a photo. "
        "You MUST respond in FRENCH only. "
        "NEVER respond in English. "
        "NEVER respond in any other language. "
        "French only. "
        f"Tu es {cfg['persona']}. "
        "Tu réponds TOUJOURS et EXCLUSIVEMENT en français. "
        "Jamais une seule phrase en anglais. "
        "Ne montre JAMAIS ton raisonnement interne. "
        "Ne commence PAS par 'Analyze User Input' ou 'Brouillon mental'. "
        "Réponds DIRECTEMENT avec les 8 points demandés, sans introduction."
    )


def build_analysis_user_prompt(sector_id: str) -> str:
    cfg = SECTORS[sector_id]
    return (
        "RÉPONDS EN FRANÇAIS UNIQUEMENT. FRENCH ONLY.\n\n"
        f"Analyse cette {cfg['item_label']} et réponds STRUCTURÉEMENT :\n\n"
        "1. 🏷️ TYPE DE PROBLÈME\n"
        "2. 🔍 DOMMAGES / DÉFAUTS DÉTECTÉS\n"
        "3. ⚠️ GRAVITÉ ESTIMÉE : Légère / Modérée / Élevée / Totale\n"
        "4. ✅ UTILISABLE EN L'ÉTAT : Oui / Non / Incertain\n"
        "5. 👨‍🔧 EXPERTISE NÉCESSAIRE : Oui / Non / Facultative\n"
        "6. ⏱️ DÉLAI DE RÉSOLUTION ESTIMÉ\n"
        "7. 💰 COÛT ESTIMÉ : Fourchette en euros\n"
        "8. 📋 RECOMMANDATIONS : 3 actions concrètes\n\n"
        "Sois professionnel, concis, objectif. N'invente rien.\n\n"
        "RÈGLE ABSOLUE : Ne montre PAS ton raisonnement. "
        "Ne commence PAS par '1. Analyze User Input' ou 'Brouillon mental'. "
        "Réponds DIRECTEMENT avec les 8 points ci-dessus.\n\n"
        "RAPPEL FINAL : TA RÉPONSE DOIT ÊTRE 100% EN FRANÇAIS, SANS RAISONNEMENT INTERNE."
    )


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
        "upload_label": cfg["upload_label"],
    }


@app.get("/api/bootstrap")
def bootstrap():
    return sector_payload(current_sector)


def encode_image_to_base64(image: Image.Image) -> str:
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")


def clean_vision_output(text: str) -> str:
    """Filtre le raisonnement interne du modèle vision, ne garde que la réponse structurée."""
    lines = text.split("\n")
    result = []
    started = False

    for line in lines:
        stripped = line.strip()
        if not started and stripped.startswith("1.") and "🏷️" in stripped:
            started = True

        if started:
            result.append(line)

    if result:
        return "\n".join(result).strip()

    thinking_keywords = [
        "analyze user input", "brouillon mental", "correspondance avec la structure",
        "thinking process", "draft", "reasoning", "step-by-step", "plan de réponse",
        "réflexion préalable", "analyse préliminaire",
    ]
    cleaned_lines = [line for line in lines if not any(kw in line.lower() for kw in thinking_keywords)]
    return "\n".join(cleaned_lines).strip()


def is_english_response(text: str) -> bool:
    text_lower = text.lower()
    english_keywords = [
        "damage", "damaged", "vehicle", "accident", "collision", "repair", "estimated",
        "the ", "and ", "this ", "based", "image", "photo", "shows", "visible",
        "severe", "light", "moderate", "total", "yes", "no", "days", "euros",
        "recommendations", "expertise", "necessary", "drivable", "uncertain",
        "type", "loss", "front", "rear", "side", "bumper", "hood", "windshield",
        "scratch", "dent", "broken", "crack", "impact", "insurance", "claim",
    ]
    # Comparaison sur des mots entiers (pas de sous-chaîne) pour éviter les faux positifs
    # du type "dent" détecté dans "accident". Seuil élevé volontairement : plusieurs mots
    # de la liste (collision, impact, expertise, type...) sont aussi des mots français
    # courants du vocabulaire assurance — un texte français en contient souvent quelques-uns
    # sans être anglais pour autant.
    count = sum(1 for word in english_keywords if re.search(r"\b" + re.escape(word.strip()) + r"\b", text_lower))
    return count >= 6


def translate_to_french(english_text: str, sector_id: str) -> str:
    cfg = SECTORS[sector_id]
    system_prompt = (
        f"Tu es {cfg['persona']}. "
        "Tu traduis des analyses de problèmes de l'anglais vers un français professionnel, structuré et concis. "
        "Tu conserves EXACTEMENT la même structure numérotée (1. à 8.). "
        "Tu adaptes les termes techniques à la terminologie française du secteur concerné. "
        "Tu ne dois JAMAIS ajouter de texte hors des 8 points. "
        "Tu ne dois JAMAIS répondre en anglais. "
        "Tu ne dois JAMAIS inventer des informations."
    )
    response = client.chat.completions.create(
        model=TRANSLATE_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Traduis cette analyse en français professionnel structuré (8 points) :\n\n{english_text}"},
        ],
        temperature=0.2,
        max_tokens=800,
    )
    return response.choices[0].message.content


def extract_severity(text: str) -> str | None:
    """Cherche le niveau de gravité retenu dans le bloc du point 3. Le modèle recopie parfois
    la liste des choix proposés avant de trancher (ex: "Légère / Modérée / ...\nModérée") —
    on retire cette liste avant de chercher le premier niveau réellement cité."""
    match = re.search(r"GRAVIT[ÉE]\s*ESTIMÉE.*?(?=\n\s*\d\.|\Z)", text, re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    section = re.sub(r"L[ée]g[èe]re\s*/\s*Mod[ée]r[ée]e\s*/\s*[ÉE]lev[ée]e\s*/\s*Totale", "", match.group(0), flags=re.IGNORECASE)
    for s in SEVERITES:
        if re.search(r"\b" + re.escape(s) + r"\b", section, re.IGNORECASE):
            return s
    return None


@app.post("/api/analyze")
async def analyze(file: UploadFile = File(...)):
    if not client:
        return {"error": "Clé API Groq manquante. Configurez GROQ_API_KEY pour utiliser AssurVision."}

    try:
        contents = await file.read()
        img = Image.open(io.BytesIO(contents))
        base64_image = encode_image_to_base64(img)

        response = client.chat.completions.create(
            model=VISION_MODEL,
            messages=[
                {"role": "system", "content": build_analysis_system_prompt(current_sector)},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": build_analysis_user_prompt(current_sector)},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}},
                    ],
                },
            ],
            max_tokens=800,
            temperature=0.3,
            extra_body={"reasoning_effort": "none"},
        )

        raw_analysis = response.choices[0].message.content
        cleaned_analysis = clean_vision_output(raw_analysis)

        translated = False
        if is_english_response(cleaned_analysis):
            analysis = translate_to_french(cleaned_analysis, current_sector)
            translated = True
        else:
            analysis = cleaned_analysis

        return {"analysis": analysis, "severity": extract_severity(analysis), "translated": translated}
    except Exception:
        return {"error": "L'analyse a échoué. Vérifiez le format de l'image et réessayez."}
