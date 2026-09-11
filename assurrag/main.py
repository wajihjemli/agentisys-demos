"""
AssurRAG — Répond aux questions sur un document (conditions générales, procédure...), en citant l'article exact — sans inventer.
POC — Wajih Jemli
"""

import os

import openai
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="AssurRAG")
app.mount("/static", StaticFiles(directory="static"), name="static")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
client = openai.OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1") if GROQ_API_KEY else None

EXEMPLE_DOCUMENT = """CONDITIONS GÉNÉRALES - GARANTIE HABITATION
Article 12 - Dégâts des eaux
La garantie couvre les dommages matériels causés par l'eau provenant d'appareils fixes de plomberie, de chauffage ou de climatisation, ainsi que les infiltrations d'eau de pluie par la toiture.

Franchise : 250€ par sinistre.
Plafond : 50 000€ par sinistre et 150 000€ par année d'assurance.
Exclusions : inondations par remontée des eaux souterraines, dégâts causés par un manque d'entretien.

Article 15 - Responsabilité Civile Vie Privée
La garantie couvre les dommages corporels, matériels et immatériels causés à des tiers dans le cadre de la vie privée.

Plafond : 5 000 000€ par sinistre.
Franchise : 0€."""

EXEMPLE_QUESTION = "Quelle est la franchise pour un dégât des eaux ?"


def answer_question(document: str, question: str) -> str:
    prompt = f"""Tu es un expert en assurance. Réponds à la question UNIQUEMENT sur la base du document fourni ci-dessous.
Si la réponse n'est pas dans le document, dis exactement : "Cette information ne figure pas dans le document fourni."
Sois concis et précis. Cite l'article concerné si possible.

--- DOCUMENT ---
{document}
--- FIN DOCUMENT ---

Question : {question}

Réponse :"""
    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )
    return response.choices[0].message.content


@app.get("/")
def index():
    return FileResponse("static/index.html")


@app.get("/api/bootstrap")
def bootstrap():
    return {"example_document": EXEMPLE_DOCUMENT, "example_question": EXEMPLE_QUESTION}


class AskRequest(BaseModel):
    document: str
    question: str


@app.post("/api/ask")
def ask(req: AskRequest):
    if not client:
        return {"error": "Clé API Groq manquante. Configurez GROQ_API_KEY pour utiliser AssurRAG."}
    if not req.document.strip() or not req.question.strip():
        return {"error": "Document et question requis."}
    try:
        answer = answer_question(req.document, req.question)
        return {"answer": answer}
    except Exception:
        return {"error": "La réponse a échoué. Réessayez dans un instant."}
