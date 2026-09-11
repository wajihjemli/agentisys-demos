"""
AssurBot — Assistant conversationnel multi-secteur en RAG (TF-IDF + moteur IA).
Le code ne change jamais : seul le secteur actif (config + base de connaissances dans
sectorbot/) détermine le nom affiché, le prompt système et le contenu utilisé.
POC — Wajih Jemli
"""

import json
import os
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

# sectorbot/ vit à la racine du repo, en frère de agentisys-suite/ — nécessite que le
# repo entier soit cloné ensemble (ce n'est pas un microservice isolé).
SECTORBOT_DIR = Path(__file__).parent.parent.parent.parent / "sectorbot"

with open(SECTORBOT_DIR / "sectors.config.json", "r", encoding="utf-8") as f:
    _config = json.load(f)
SECTORS = _config["sectors"]
DEFAULT_SECTOR = _config["default_sector"]

FALLBACK_MSG = ("Je n'ai pas trouvé de réponse à votre question dans ma base de connaissances. "
                 "Reformulez votre question ou contactez le service client.")

# État courant du secteur actif — démonstrateur mono-utilisateur, pas de session.
current_sector = DEFAULT_SECTOR

_knowledge_cache: dict[str, tuple[list[str], list[str]]] = {}


def load_knowledge_base(path: Path) -> tuple[list[str], list[str]]:
    """Parse un fichier Q:/R: — ignore les titres, notes entre crochets et séparateurs ---."""
    questions, reponses = [], []
    q, r = None, None
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("Q:"):
            if q is not None and r is not None:
                questions.append(q)
                reponses.append(r)
            q, r = stripped[2:].strip(), None
        elif stripped.startswith("R:"):
            r = stripped[2:].strip()
    if q is not None and r is not None:
        questions.append(q)
        reponses.append(r)
    return questions, reponses


def get_knowledge(sector_id: str) -> tuple[list[str], list[str]]:
    if sector_id not in _knowledge_cache:
        kb_path = SECTORBOT_DIR / SECTORS[sector_id]["sample_knowledge_file"]
        _knowledge_cache[sector_id] = load_knowledge_base(kb_path)
    return _knowledge_cache[sector_id]


def retrieve_context(query: str, sector_id: str, top_k=3, threshold=0.1):
    """Similarité cosinus TF-IDF entre la question et la base du secteur actif."""
    questions, reponses = get_knowledge(sector_id)
    if not questions:
        return []
    vectorizer = TfidfVectorizer(lowercase=True, strip_accents="unicode", ngram_range=(1, 2))
    tfidf_matrix = vectorizer.fit_transform(questions + [query])
    similarities = cosine_similarity(tfidf_matrix[-1], tfidf_matrix[:-1]).flatten()
    ranked = sorted(range(len(similarities)), key=lambda i: similarities[i], reverse=True)[:top_k]
    return [(questions[i], reponses[i], float(similarities[i])) for i in ranked if similarities[i] >= threshold]


def generate_answer(query: str, contexts, sector_id: str) -> str:
    cfg = SECTORS[sector_id]
    context_block = "\n\n".join(f"Q: {q}\nR: {r}" for q, r, _score in contexts)
    prompt = f"""{cfg['system_prompt']}
Réponds à la question UNIQUEMENT à partir des extraits fournis ci-dessous.
Si les extraits ne permettent pas de répondre, dis exactement : "Je n'ai pas trouvé de réponse exacte à votre question dans ma base de connaissances."
Sois clair, concis et rassurant.

--- EXTRAITS ---
{context_block}
--- FIN DES EXTRAITS ---

{cfg['field_labels']['input']} : {query}

Réponse :"""
    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    return response.choices[0].message.content


def sector_payload(sector_id: str) -> dict:
    cfg = SECTORS[sector_id]
    questions, _ = get_knowledge(sector_id)
    return {
        "sector": sector_id,
        "tool_name": cfg["tool_name"],
        "icon": cfg["icon"],
        "tagline": cfg["tagline"],
        "field_labels": cfg["field_labels"],
        "welcome": f"Bonjour ! Je suis {cfg['tool_name']}. {cfg['tagline']}",
        "examples": questions[:5],
    }


@router.get("/sectors")
def list_sectors():
    """Métadonnées légères des 7 secteurs, pour peupler le sélecteur (pas les prompts)."""
    return {
        "sectors": {sid: {"tool_name": c["tool_name"], "icon": c["icon"], "tagline": c["tagline"]} for sid, c in SECTORS.items()},
        "default": DEFAULT_SECTOR,
    }


@router.get("/bootstrap")
def bootstrap():
    return sector_payload(current_sector)


class SectorRequest(BaseModel):
    sector: str


@router.post("/sector")
def set_sector(req: SectorRequest):
    global current_sector
    if req.sector not in SECTORS:
        return {"error": "Secteur inconnu."}
    current_sector = req.sector
    return sector_payload(current_sector)


class ChatRequest(BaseModel):
    message: str


@router.post("/chat")
def chat(req: ChatRequest):
    contexts = retrieve_context(req.message, current_sector)
    sources = [{"question": q, "answer": r, "score": round(s, 2)} for q, r, s in contexts]

    if not contexts:
        return {"answer": FALLBACK_MSG, "sources": [], "mode": "no_match"}

    if not client:
        return {"answer": contexts[0][1], "sources": sources, "mode": "raw_faq"}

    try:
        answer = generate_answer(req.message, contexts, current_sector)
        return {"answer": answer, "sources": sources, "mode": "ai"}
    except Exception:
        return {"answer": contexts[0][1], "sources": sources, "mode": "raw_faq"}
