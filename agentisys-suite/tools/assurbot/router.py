"""
AssurBot — Assistant conversationnel assurance en RAG (TF-IDF + moteur IA), ancré sur une FAQ interne.
POC — Wajih Jemli
"""

import os
import re
from pathlib import Path

import numpy as np
import openai
from fastapi import APIRouter
from pydantic import BaseModel
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

router = APIRouter()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
client = openai.OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1") if GROQ_API_KEY else None

WELCOME_MSG = ("Bonjour ! Je suis AssurBot, votre assistant virtuel assurance. Je peux vous aider sur la "
               "déclaration de sinistres, les remboursements, la gestion de votre contrat, l'assistance à "
               "l'étranger et vos garanties.")

FALLBACK_MSG = ("Je n'ai pas trouvé de réponse à votre question dans ma base de connaissances. "
                 "Contactez un conseiller au 01 23 45 67 89 (lundi-vendredi, 8h-19h), reformulez votre "
                 "question, ou passez par votre espace client.")

EXEMPLES = [
    "Comment déclarer un sinistre ?",
    "Quel est le délai de remboursement ?",
    "Comment résilier mon contrat ?",
    "Quels documents pour un sinistre auto ?",
    "Que faire en cas d'urgence à l'étranger ?",
]


def load_knowledge_base():
    faq_path = Path(__file__).parent / "faq_assurance.txt"
    with open(faq_path, "r", encoding="utf-8") as f:
        content = f.read()

    questions, reponses = [], []
    for entry in re.split(r"\n\s*\n", content.strip()):
        q, r = "", ""
        for line in entry.strip().split("\n"):
            if line.startswith("Question:"):
                q = line.replace("Question:", "").strip()
            elif line.startswith("Réponse:"):
                r = line.replace("Réponse:", "").strip()
            elif q and r and line.strip():
                r += " " + line.strip()
        if q and r:
            questions.append(q)
            reponses.append(r)
    return questions, reponses


QUESTIONS, REPONSES = load_knowledge_base()


def retrieve_context(query, top_k=3, threshold=0.1):
    """Similarité cosinus TF-IDF entre la question et la FAQ."""
    if not QUESTIONS:
        return []
    vectorizer = TfidfVectorizer(lowercase=True, strip_accents="unicode", ngram_range=(1, 2))
    tfidf_matrix = vectorizer.fit_transform(QUESTIONS + [query])
    similarities = cosine_similarity(tfidf_matrix[-1], tfidf_matrix[:-1]).flatten()
    ranked = sorted(range(len(similarities)), key=lambda i: similarities[i], reverse=True)[:top_k]
    return [(QUESTIONS[i], REPONSES[i], float(similarities[i])) for i in ranked if similarities[i] >= threshold]


def generate_answer(query, contexts):
    context_block = "\n\n".join(f"Q: {q}\nR: {r}" for q, r, _score in contexts)
    prompt = f"""Tu es AssurBot, l'assistant virtuel d'une compagnie d'assurance.
Réponds à la question du client UNIQUEMENT à partir des extraits de FAQ fournis ci-dessous.
Si les extraits ne permettent pas de répondre, dis exactement : "Je n'ai pas trouvé de réponse exacte à votre question dans ma base de connaissances."
Sois clair, concis et rassurant.

--- EXTRAITS DE FAQ ---
{context_block}
--- FIN DES EXTRAITS ---

Question du client : {query}

Réponse :"""
    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    return response.choices[0].message.content


@router.get("/bootstrap")
def bootstrap():
    """Contenu initial (message d'accueil, exemples) pour peupler le frontend au chargement."""
    return {"welcome": WELCOME_MSG, "examples": EXEMPLES}


class ChatRequest(BaseModel):
    message: str


@router.post("/chat")
def chat(req: ChatRequest):
    contexts = retrieve_context(req.message)
    sources = [{"question": q, "answer": r, "score": round(s, 2)} for q, r, s in contexts]

    if not contexts:
        return {"answer": FALLBACK_MSG, "sources": [], "mode": "no_match"}

    if not client:
        return {"answer": contexts[0][1], "sources": sources, "mode": "raw_faq"}

    try:
        answer = generate_answer(req.message, contexts)
        return {"answer": answer, "sources": sources, "mode": "ai"}
    except Exception:
        return {"answer": contexts[0][1], "sources": sources, "mode": "raw_faq"}
