"""
AssurMeet — Résume un appel client et en extrait les actions à suivre, sans écoute manuelle a posteriori.
POC — Wajih Jemli
"""

import json
import os
import re

import openai
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
client = openai.OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1") if GROQ_API_KEY else None

EXEMPLE_TRANSCRIPT = """Conseiller : Bonjour Madame, je vous écoute.
Client : Bonjour, j'appelle pour mon sinistre du 15 juillet. J'attends depuis 3 semaines et personne ne me donne de nouvelles.
Conseiller : Je comprends votre impatience Madame. Pouvez-vous me donner votre numéro de dossier ?
Client : C'est le 2026-084521. J'ai envoyé tous les documents, le constat, les photos, le devis... Et depuis, silence radio !
Conseiller : Je vois votre dossier Madame. Il est effectivement en attente de validation par notre service expertise. Je vais faire une relance immédiate.
Client : Ça fait 3 semaines que j'attends ! J'ai besoin de ma voiture pour aller travailler. C'est inacceptable !
Conseiller : Je comprends tout à fait. Je vous propose de vous rappeler demain avant 14h avec une réponse définitive. Est-ce que cela vous convient ?
Client : D'accord, mais si je n'ai pas de nouvelles, je résilie mon contrat et je vais voir ailleurs.
Conseiller : Je vous garantis un retour demain Madame. Merci de votre patience."""


def analyze_transcript(transcript: str) -> dict:
    prompt = f"""Tu es un analyste qualité senior dans une compagnie d'assurance.
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


@router.get("/bootstrap")
def bootstrap():
    return {"example_transcript": EXEMPLE_TRANSCRIPT}


class AnalyzeRequest(BaseModel):
    transcript: str


@router.post("/analyze")
def analyze(req: AnalyzeRequest):
    if not client:
        return {"error": "Clé API Groq manquante. Configurez GROQ_API_KEY pour utiliser AssurMeet."}
    try:
        result = analyze_transcript(req.transcript)
        return {"result": result}
    except Exception:
        return {"error": "L'analyse a échoué. Réessayez dans un instant."}
