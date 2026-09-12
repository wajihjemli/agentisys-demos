"""
AssurRAG — Répond aux questions sur un document (conditions générales, procédure...), en citant l'article exact — sans inventer.
Vrai pipeline RAG : le document est découpé en sections, seules les plus pertinentes (recherche TF-IDF) sont envoyées au moteur IA.
Multi-secteur : le pipeline ne change jamais, seul le secteur actif (config dans sectorbot/) détermine le nom affiché
et le document/question d'exemple.
POC — Wajih Jemli
"""

import json
import os
import re
from pathlib import Path

import openai
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

app = FastAPI(title="AssurRAG")
app.mount("/static", StaticFiles(directory="static"), name="static")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
client = openai.OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1") if GROQ_API_KEY else None

# sectorbot/ vit à la racine du repo, en frère de ce dossier — nécessite que le repo
# entier soit cloné ensemble (ce n'est pas un microservice isolé).
SECTORBOT_DIR = Path(__file__).parent.parent / "sectorbot"

with open(SECTORBOT_DIR / "assurrag.config.json", "r", encoding="utf-8") as f:
    _config = json.load(f)
SECTORS = _config["sectors"]
DEFAULT_SECTOR = _config["default_sector"]

current_sector = DEFAULT_SECTOR


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


def answer_question(retrieved: list[tuple[str, float]], question: str, sector_id: str) -> str:
    cfg = SECTORS[sector_id]
    context_block = "\n\n".join(excerpt for excerpt, _score in retrieved)
    prompt = f"""Tu es un expert dans un(e) {cfg['persona']}. Réponds à la question UNIQUEMENT sur la base des extraits fournis ci-dessous.
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
        "example_document": cfg["example_document"],
        "example_question": cfg["example_question"],
    }


@app.get("/api/bootstrap")
def bootstrap():
    return sector_payload(current_sector)


class AskRequest(BaseModel):
    document: str
    question: str


@app.post("/api/ask")
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
        answer = answer_question(retrieved, req.question, current_sector)
        sources = [{"excerpt": excerpt, "score": round(score, 2)} for excerpt, score in retrieved]
        return {"answer": answer, "sources": sources, "chunks_total": len(chunks)}
    except Exception:
        return {"error": "La réponse a échoué. Réessayez dans un instant."}
