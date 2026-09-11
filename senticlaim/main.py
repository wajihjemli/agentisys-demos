"""
SentiClaim — Analyse de sentiment, urgence et catégorie métier d'une réclamation assurance.
POC — Wajih Jemli
"""

import json
import os
import re

import openai
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="SentiClaim")
app.mount("/static", StaticFiles(directory="static"), name="static")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
client = openai.OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1") if GROQ_API_KEY else None

CATEGORIES = ["sinistre", "remboursement", "contrat", "service_client", "resiliation", "général"]

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
]
CATEGORIE_KEYWORDS = {
    "sinistre": ["sinistre", "accident", "dégât", "dommage", "vol", "incendie", "inondation"],
    "remboursement": ["remboursement", "rembourser", "frais", "facture", "devis", "paiement"],
    "contrat": ["contrat", "garantie", "couverture", "exclusion", "condition", "clause"],
    "service_client": ["conseiller", "appel", "attente", "standard", "accueil", "réponse"],
    "resiliation": ["résilier", "résiliation", "résilié", "annuler"],
}

EXEMPLES = [
    "Mon sinistre n'est toujours pas traité après 3 semaines. C'est inacceptable ! Je veux parler à un responsable.",
    "Merci pour votre rapidité. Le remboursement a été effectué sous 5 jours. Très satisfait de votre service.",
    "J'attends depuis 2 mois un remboursement de 850€ pour mes frais dentaires. Personne ne me répond. C'est du vol !",
    "Le conseiller était très aimable et a résolu mon problème en 10 minutes. Bravo à votre équipe.",
    "Mon père est hospitalisé en urgence à l'étranger et votre assistance ne décroche pas. C'est une urgence vitale !",
    "Je souhaite résilier mon contrat. Vos conditions ont changé sans préavis. Je vais saisir le médiateur.",
]


def analyze_lexicon(text: str) -> dict:
    """Analyse de secours par lexique métier, sans appel IA (hors-ligne, instantanée)."""
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
    cat_scores = {cat: sum(1 for k in kws if k in text_lower) for cat, kws in CATEGORIE_KEYWORDS.items()}
    categorie = max(cat_scores, key=cat_scores.get) if max(cat_scores.values()) > 0 else "général"
    intensity = min(100, int((abs(score) + (2 if urgence else 0)) * 15))

    if sentiment == "NÉGATIF" and urgence:
        action = "ESCALADE IMMÉDIATE : Appeler le client sous 1h. Sinistre/urgence détecté(e)."
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


def analyze_with_ai(text: str) -> dict:
    prompt = f"""Tu es un analyste qualité senior dans une compagnie d'assurance.
Analyse cette réclamation client et réponds UNIQUEMENT par un objet JSON strict (pas de texte autour, pas de markdown), avec exactement ces clés :
{{
  "sentiment": "POSITIF" ou "NÉGATIF" ou "NEUTRE",
  "intensity": entier de 0 à 100 (intensité émotionnelle),
  "urgence": true ou false (urgence vitale, sinistre grave, hospitalisation...),
  "categorie": une valeur parmi {CATEGORIES},
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
    result["categorie"] = result.get("categorie") if result.get("categorie") in CATEGORIES else "général"
    result["mots_cles"] = result.get("mots_cles", [])
    result["action"] = result.get("action", "")
    return result


@app.get("/")
def index():
    return FileResponse("static/index.html")


@app.get("/api/bootstrap")
def bootstrap():
    """Exemples cliquables + aperçu rapide (lexique, hors-ligne) des 6 réclamations types."""
    quick_scan = [{"text": ex, **analyze_lexicon(ex)} for ex in EXEMPLES]
    return {"examples": EXEMPLES, "quick_scan": quick_scan}


class AnalyzeRequest(BaseModel):
    text: str


@app.post("/api/analyze")
def analyze(req: AnalyzeRequest):
    if client:
        try:
            result = analyze_with_ai(req.text)
            return {**result, "mode": "ai"}
        except Exception:
            pass
    result = analyze_lexicon(req.text)
    return {**result, "mode": "lexicon"}
