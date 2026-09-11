"""
AssurVision — Estime la gravité d'un sinistre à partir d'une simple photo envoyée par l'assuré,
pour accélérer le premier diagnostic avant expertise.
POC — Wajih Jemli
"""
import base64
import io
import os
import re

import openai
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image

app = FastAPI(title="AssurVision")
app.mount("/static", StaticFiles(directory="static"), name="static")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
client = openai.OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1") if GROQ_API_KEY else None

VISION_MODEL = "qwen/qwen3.6-27b"
TRANSLATE_MODEL = "openai/gpt-oss-20b"

SEVERITES = ["Légère", "Modérée", "Élevée", "Totale"]

ANALYSIS_SYSTEM_PROMPT = (
    "You are an automotive insurance expert. "
    "You MUST respond in FRENCH only. "
    "NEVER respond in English. "
    "NEVER respond in any other language. "
    "French only. "
    "Tu es un expert en assurance automobile. "
    "Tu réponds TOUJOURS et EXCLUSIVEMENT en français. "
    "Jamais une seule phrase en anglais. "
    "Ne montre JAMAIS ton raisonnement interne. "
    "Ne commence PAS par 'Analyze User Input' ou 'Brouillon mental'. "
    "Réponds DIRECTEMENT avec les 8 points demandés, sans introduction."
)

ANALYSIS_USER_PROMPT = (
    "RÉPONDS EN FRANÇAIS UNIQUEMENT. FRENCH ONLY.\n\n"
    "Analyse cette photo de sinistre et réponds STRUCTURÉEMENT :\n\n"
    "1. 🏷️ TYPE DE SINISTRE\n"
    "2. 🔍 DOMMAGES DÉTECTÉS\n"
    "3. ⚠️ GRAVITÉ ESTIMÉE : Légère / Modérée / Élevée / Totale\n"
    "4. 🚗 VÉHICULE ROULANT : Oui / Non / Incertain\n"
    "5. 👨‍🔧 EXPERTISE NÉCESSAIRE : Oui / Non / Facultative\n"
    "6. ⏱️ DÉLAI RÉPARATION ESTIMÉ\n"
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
        if (stripped.startswith("1.") and "🏷️" in stripped and "TYPE DE SINISTRE" in stripped) or \
           (stripped.startswith("1.") and "🏷️" in stripped and "SINISTRE" in stripped):
            started = True
        elif not started and "🏷️" in stripped and "TYPE DE SINISTRE" in stripped and stripped[0].isdigit():
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


def translate_to_french(english_text: str) -> str:
    system_prompt = (
        "Tu es un expert en assurance automobile français. "
        "Tu traduis des analyses de sinistres de l'anglais vers un français professionnel, structuré et concis. "
        "Tu conserves EXACTEMENT la même structure numérotée (1. à 8.). "
        "Tu adaptes les termes techniques à la terminologie française du secteur de l'assurance. "
        "Tu ne dois JAMAIS ajouter de texte hors des 8 points. "
        "Tu ne dois JAMAIS répondre en anglais. "
        "Tu ne dois JAMAIS inventer des informations."
    )
    response = client.chat.completions.create(
        model=TRANSLATE_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Traduis cette analyse de sinistre en français professionnel structuré (8 points) :\n\n{english_text}"},
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
                {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": ANALYSIS_USER_PROMPT},
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
            analysis = translate_to_french(cleaned_analysis)
            translated = True
        else:
            analysis = cleaned_analysis

        return {"analysis": analysis, "severity": extract_severity(analysis), "translated": translated}
    except Exception:
        return {"error": "L'analyse a échoué. Vérifiez le format de l'image et réessayez."}
