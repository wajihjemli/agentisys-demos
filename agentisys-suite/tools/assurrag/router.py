"""
AssurRAG — Répond aux questions sur un document (conditions générales, procédure...), en citant l'article exact — sans inventer.
Vrai pipeline RAG : le document est découpé en sections, seules les plus pertinentes (recherche TF-IDF) sont envoyées au moteur IA.
POC — Wajih Jemli
"""

import os
import re

import openai
from fastapi import APIRouter
from pydantic import BaseModel
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

router = APIRouter()

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
Franchise : 0€.

Article 18 - Vol et Cambriolage
La garantie couvre le vol des biens mobiliers commis par effraction, escalade ou usage de fausses clés, ainsi que le vandalisme consécutif à un vol.
Franchise : 150€ par sinistre.
Plafond : 30 000€ pour le mobilier courant, 5 000€ pour les objets de valeur (bijoux, œuvres d'art).
Exclusions : vol commis sans effraction constatée, vol dans un logement resté inoccupé plus de 90 jours consécutifs.

Article 21 - Incendie et Explosion
La garantie couvre les dommages causés par un incendie, une explosion, la foudre ou la chute d'un appareil de navigation aérienne.
Franchise : 200€ par sinistre.
Plafond : valeur de reconstruction à neuf, sans limitation.
Exclusions : incendie volontaire de l'assuré, dommages causés par un défaut d'entretien des installations électriques signalé et non réparé.

Article 27 - Résiliation du contrat
L'assuré peut résilier son contrat à tout moment après la première année, conformément à la loi Hamon, par courrier recommandé ou via son espace client.
La résiliation prend effet 30 jours après réception de la demande.
L'assureur peut résilier en cas de non-paiement de cotisation, d'aggravation du risque non déclarée, ou de sinistralité anormale."""

EXEMPLE_QUESTION = "Quelle est la franchise pour un dégât des eaux ?"


def chunk_document(document: str) -> list[str]:
    """Découpe le document en sections (paragraphes séparés par une ligne vide)."""
    chunks = [c.strip() for c in re.split(r"\n\s*\n", document.strip()) if c.strip()]
    return chunks


def retrieve_chunks(chunks: list[str], question: str, top_k: int = 3, min_score: float = 0.05, relative_cutoff: float = 0.7):
    """Recherche par similarité cosinus TF-IDF : ne garde que les sections les plus pertinentes.

    Un seuil purement absolu laisse passer du bruit sur un petit corpus (les articles partagent du
    vocabulaire commun : "franchise", "plafond"...). On combine donc un plancher absolu et un seuil
    relatif au meilleur score trouvé, pour ne garder que ce qui est vraiment proche de la question.
    """
    if not chunks:
        return []
    vectorizer = TfidfVectorizer(lowercase=True, strip_accents="unicode", ngram_range=(1, 2))
    tfidf_matrix = vectorizer.fit_transform(chunks + [question])
    similarities = cosine_similarity(tfidf_matrix[-1], tfidf_matrix[:-1]).flatten()

    ranked = sorted(range(len(similarities)), key=lambda i: similarities[i], reverse=True)[:top_k]
    if not ranked or similarities[ranked[0]] < min_score:
        return []

    cutoff = max(min_score, similarities[ranked[0]] * relative_cutoff)
    return [(chunks[i], float(similarities[i])) for i in ranked if similarities[i] >= cutoff]


def answer_question(retrieved: list[tuple[str, float]], question: str) -> str:
    context_block = "\n\n".join(excerpt for excerpt, _score in retrieved)
    prompt = f"""Tu es un expert en assurance. Réponds à la question UNIQUEMENT sur la base des extraits fournis ci-dessous.
Si la réponse n'est pas dans les extraits, dis exactement : "Cette information ne figure pas dans les extraits fournis."
Sois concis et précis. Cite l'article concerné si possible.

--- EXTRAITS ---
{context_block}
--- FIN DES EXTRAITS ---

Question : {question}

Réponse :"""
    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )
    return response.choices[0].message.content


@router.get("/bootstrap")
def bootstrap():
    return {"example_document": EXEMPLE_DOCUMENT, "example_question": EXEMPLE_QUESTION}


class AskRequest(BaseModel):
    document: str
    question: str


@router.post("/ask")
def ask(req: AskRequest):
    if not client:
        return {"error": "Clé API Groq manquante. Configurez GROQ_API_KEY pour utiliser AssurRAG."}
    if not req.document.strip() or not req.question.strip():
        return {"error": "Document et question requis."}

    chunks = chunk_document(req.document)
    retrieved = retrieve_chunks(chunks, req.question)

    if not retrieved:
        return {
            "answer": "Cette information ne figure pas dans les extraits fournis.",
            "sources": [],
            "chunks_total": len(chunks),
        }

    try:
        answer = answer_question(retrieved, req.question)
        sources = [{"excerpt": excerpt, "score": round(score, 2)} for excerpt, score in retrieved]
        return {"answer": answer, "sources": sources, "chunks_total": len(chunks)}
    except Exception:
        return {"error": "La réponse a échoué. Réessayez dans un instant."}
