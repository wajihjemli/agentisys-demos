"""
SentiClaim — Analyse de sentiment, urgence et catégorie métier d'une réclamation, multi-secteur.
Le code ne change jamais : seul le secteur actif (config dans sectorbot/) détermine le nom
affiché, les catégories métier et les exemples utilisés.
POC — Wajih Jemli
"""

import json
import os
import re
from pathlib import Path

import openai
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
client = openai.OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1") if GROQ_API_KEY else None

# sectorbot/ vit à la racine du repo, en frère de agentisys-suite/ — nécessite que le
# repo entier soit cloné ensemble (ce n'est pas un microservice isolé).
SECTORBOT_DIR = Path(__file__).parent.parent.parent.parent / "sectorbot"

with open(SECTORBOT_DIR / "senticlaim.config.json", "r", encoding="utf-8") as f:
    _config = json.load(f)
SECTORS = _config["sectors"]
DEFAULT_SECTOR = _config["default_sector"]

MOTS_NEGATIFS = [
    "refusé", "refus", "rejette", "rejeté", "impossible", "inacceptable", "scandaleux",
    "indigné", "furieux", "énervé", "mécontent", "insatisfait", "déçu", "déception",
    "attendre", "retard", "lent", "aucun", "jamais", "rien", "problème", "bug",
    "erreur", "faux", "mensonge", "arnaque", "vol", "escroquerie", "honteux",
    "incompétent", "nul", "catastrophe", "horrible", "désastre", "pire", "abandonner",
    "résilier", "plainte", "tribunal", "médiateur", "huissier", "avocat", "procès",
]
MOTS_POSITIFS = [
    "merci", "satisfait", "content", "heureux", "ravi", "excellent", "parfait",
    "super", "génial", "bravo", "félicitations", "efficace", "rapide", "réactif",
    "professionnel", "aimable", "gentil", "compétent", "résolu", "solution",
    "réglé", "remboursé", "indemnisé", "recommande", "confiance", "rassuré",
]
MOTS_URGENCE = [
    "urgent", "urgence", "hospitalisation", "décès", "accident", "grave",
    "incapacité", "sinistre", "catastrophe", "inondation", "incendie", "vol", "agression",
    "panne", "fraude", "piraté", "bloqué",
]

current_sector = DEFAULT_SECTOR


def analyze_lexicon(text: str, sector_id: str) -> dict:
    """Analyse de secours par lexique métier, sans appel IA (hors-ligne, instantanée)."""
    cfg = SECTORS[sector_id]
    text_lower = text.lower()
    words = re.findall(r"\b\w+\b", text_lower)

    neg_count = sum(1 for w in words if w in MOTS_NEGATIFS)
    pos_count = sum(1 for w in words if w in MOTS_POSITIFS)
    if any(x in text_lower for x in ["!", "??", "trop", "très", "vraiment", "extrêmement"]):
        neg_count *= 1.3
        pos_count *= 1.3
    score = pos_count - neg_count

    if score >= 1:
        sentiment = "POSITIF"
    elif score <= -1:
        sentiment = "NÉGATIF"
    else:
        sentiment = "NEUTRE"

    urgence = any(u in text_lower for u in MOTS_URGENCE)
    cat_keywords = cfg["category_keywords"]
    cat_scores = {cat: sum(1 for k in kws if k in text_lower) for cat, kws in cat_keywords.items()}
    categorie = max(cat_scores, key=cat_scores.get) if cat_scores and max(cat_scores.values()) > 0 else "général"
    intensity = min(100, int((abs(score) + (2 if urgence else 0)) * 15))

    if sentiment == "NÉGATIF" and urgence:
        action = "ESCALADE IMMÉDIATE : Appeler le client sous 1h. Incident/urgence détecté(e)."
    elif sentiment == "NÉGATIF" and intensity > 60:
        action = "PRIORITAIRE : Contacter le client sous 4h. Risque de plainte/résiliation."
    elif sentiment == "NÉGATIF":
        action = "À TRAITER : Répondre sous 24h. Proposer une solution concrète."
    elif sentiment == "POSITIF":
        action = "SATISFACTION : Enregistrer le feedback positif. Demander un témoignage."
    else:
        action = "STANDARD : Traiter dans les délais habituels."

    return {
        "sentiment": sentiment,
        "intensity": intensity,
        "urgence": urgence,
        "categorie": categorie,
        "mots_cles": sorted(set(w for w in words if w in MOTS_NEGATIFS or w in MOTS_POSITIFS)),
        "action": action,
    }


def analyze_with_ai(text: str, sector_id: str) -> dict:
    cfg = SECTORS[sector_id]
    categories = cfg["categories"]
    prompt = f"""Tu es un analyste qualité senior dans un(e) {cfg['persona']}.
Analyse cette réclamation client et réponds UNIQUEMENT par un objet JSON strict (pas de texte autour, pas de markdown), avec exactement ces clés :
{{
  "sentiment": "POSITIF" ou "NÉGATIF" ou "NEUTRE",
  "intensity": entier de 0 à 100 (intensité émotionnelle),
  "urgence": true ou false (urgence vitale, incident grave...),
  "categorie": une valeur parmi {categories},
  "mots_cles": liste de 2 à 6 mots ou expressions déclencheurs tirés du texte,
  "action": une phrase d'action recommandée pour le conseiller, avec délai
}}

Réclamation : "{text}" """
    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )
    content = response.choices[0].message.content
    match = re.search(r"\{.*\}", content, re.DOTALL)
    result = json.loads(match.group(0) if match else content)

    result["sentiment"] = str(result.get("sentiment", "NEUTRE")).upper()
    if result["sentiment"] not in ("POSITIF", "NÉGATIF", "NEUTRE"):
        result["sentiment"] = "NEUTRE"
    result["intensity"] = max(0, min(100, int(result.get("intensity", 0))))
    result["urgence"] = bool(result.get("urgence", False))
    result["categorie"] = result.get("categorie") if result.get("categorie") in categories else "général"
    result["mots_cles"] = result.get("mots_cles", [])
    result["action"] = result.get("action", "")
    return result


@router.get("/sectors")
def list_sectors():
    return {
        "sectors": {sid: {"tool_name": c["tool_name"], "icon": c["icon"], "tagline": c["tagline"]} for sid, c in SECTORS.items()},
        "default": DEFAULT_SECTOR,
    }


class SectorRequest(BaseModel):
    sector: str


@router.post("/sector")
def set_sector(req: SectorRequest):
    global current_sector
    if req.sector not in SECTORS:
        return {"error": "Secteur inconnu."}
    current_sector = req.sector
    return sector_payload(current_sector)


def sector_payload(sector_id: str) -> dict:
    cfg = SECTORS[sector_id]
    quick_scan = [{"text": ex, **analyze_lexicon(ex, sector_id)} for ex in cfg["examples"]]
    return {
        "sector": sector_id,
        "tool_name": cfg["tool_name"],
        "icon": cfg["icon"],
        "tagline": cfg["tagline"],
        "examples": cfg["examples"],
        "quick_scan": quick_scan,
    }


@router.get("/bootstrap")
def bootstrap():
    return sector_payload(current_sector)


class AnalyzeRequest(BaseModel):
    text: str


@router.post("/analyze")
def analyze(req: AnalyzeRequest):
    if client:
        try:
            result = analyze_with_ai(req.text, current_sector)
            return {**result, "mode": "ai"}
        except Exception:
            pass
    result = analyze_lexicon(req.text, current_sector)
    return {**result, "mode": "lexicon"}
