"""
Répond aux questions d'assurance en langage naturel, en s'appuyant uniquement sur la FAQ interne — sans halluciner.
POC — Wajih Jemli
"""

import os
import re

import numpy as np
import openai
import streamlit as st
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

st.set_page_config(page_title="🤖 AssurBot - Assistant Virtuel Assurance", page_icon="🤖", layout="centered")

st.markdown("""
<style>
    .main-title { font-size: 2.2rem; font-weight: bold; color: #1E3A5F; text-align: center; }
    .source-box { background-color: #F5F5F5; padding: 12px 15px; border-radius: 10px; border-left: 5px solid #9E9E9E; margin: 6px 0; font-size: 0.85rem; color: #444; }
</style>
""", unsafe_allow_html=True)

GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY", ""))
if not GROQ_API_KEY or GROQ_API_KEY == "VOTRE_CLE_API":
    GROQ_API_KEY = st.text_input("🔑 Clé API Groq", type="password")

client = openai.OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1") if GROQ_API_KEY else None

st.markdown('<div class="main-title">🤖 AssurBot</div>', unsafe_allow_html=True)
st.markdown('<div style="text-align:center; color:#5A6C7D; margin-bottom:2rem;">Assistant Virtuel Assurance — RAG (Retrieval-Augmented Generation)</div>', unsafe_allow_html=True)


@st.cache_data
def load_knowledge_base():
    """Charge la FAQ assurance et la découpe en paires question/réponse."""
    with open("faq_assurance.txt", "r", encoding="utf-8") as f:
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


def retrieve_context(query, questions, reponses, top_k=3, threshold=0.1):
    """Retourne les entrées de FAQ les plus proches de la question, par similarité cosinus TF-IDF."""
    if not questions:
        return []

    vectorizer = TfidfVectorizer(lowercase=True, strip_accents="unicode", ngram_range=(1, 2))
    tfidf_matrix = vectorizer.fit_transform(questions + [query])
    similarities = cosine_similarity(tfidf_matrix[-1], tfidf_matrix[:-1]).flatten()

    ranked = sorted(range(len(similarities)), key=lambda i: similarities[i], reverse=True)[:top_k]
    return [(questions[i], reponses[i], similarities[i]) for i in ranked if similarities[i] >= threshold]


def generate_answer(query, contexts):
    """Génère une réponse ancrée dans les extraits de FAQ récupérés — pas d'invention hors contexte."""
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


FALLBACK_MSG = """Je n'ai pas trouvé de réponse à votre question dans ma base de connaissances.

- 📞 **Contacter un conseiller** au 01 23 45 67 89 (du lundi au vendredi, 8h-19h)
- 💬 **Reformuler votre question** avec d'autres termes
- 📧 **Envoyer un email** via votre espace client"""

WELCOME_MSG = """Bonjour ! 👋 Je suis **AssurBot**, votre assistant virtuel assurance.

Je peux vous aider sur la déclaration de sinistres, les remboursements, la gestion de votre contrat, l'assistance à l'étranger et vos garanties.

*Exemple : "Comment déclarer un sinistre auto ?"*"""

with st.sidebar:
    st.markdown("### 📋 Informations")
    st.markdown("""
    **Technologie :**
    RAG (Retrieval-Augmented Generation)
    Un moteur IA haute performance

    **Base de connaissances :** FAQ assurance

    **Fonctionnalités :**
    - Recherche sémantique dans la FAQ
    - Réponse générée à partir des extraits trouvés
    - Pas d'hallucination hors base de connaissances

    **Développeur :** Wajih Jemli
    """)
    st.markdown("### 🎯 Exemples de questions")
    for ex in [
        "Comment déclarer un sinistre ?",
        "Quel est le délai de remboursement ?",
        "Comment résilier mon contrat ?",
        "Quels documents pour un sinistre auto ?",
        "Que faire en cas d'urgence à l'étranger ?",
    ]:
        st.markdown(f"• *{ex}*")

questions, reponses = load_knowledge_base()

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": WELCOME_MSG}]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_input = st.chat_input("Posez votre question sur votre assurance...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        contexts = retrieve_context(user_input, questions, reponses)

        if not contexts:
            answer = FALLBACK_MSG
            st.markdown(answer)
        elif not client:
            st.warning("Clé API Groq manquante : affichage de l'extrait de FAQ le plus proche, sans reformulation par l'IA.")
            answer = contexts[0][1]
            st.markdown(answer)
        else:
            with st.spinner("Recherche et génération de la réponse..."):
                answer = generate_answer(user_input, contexts)
            st.markdown(answer)
            with st.expander("📄 Sources utilisées dans la FAQ"):
                for q, r, score in contexts:
                    st.markdown(f'<div class="source-box"><b>{q}</b> (similarité {score:.2f})<br>{r}</div>', unsafe_allow_html=True)

    st.session_state.messages.append({"role": "assistant", "content": answer})

st.markdown("""
<div style="text-align:center; color:#888; font-size:0.8rem; margin-top:3rem; padding-top:1rem; border-top:1px solid #eee;">
    🤖 <b>AssurBot</b> — POC par Wajih Jemli | RAG | IBM AI Developer
</div>
""", unsafe_allow_html=True)
