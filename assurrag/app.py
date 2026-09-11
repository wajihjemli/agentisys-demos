"""
Répond aux questions sur les conditions générales d'un contrat, en citant l'article exact — sans inventer de réponse.
POC — Wajih Jemli
"""

import streamlit as st
import openai
import os

st.set_page_config(page_title="📚 AssurRAG - Base de Connaissances", page_icon="📚", layout="centered")

st.markdown("""
<style>
    .main-title { font-size: 2.2rem; font-weight: bold; color: #1E3A5F; text-align: center; }
    .doc-box { background-color: #F5F5F5; padding: 15px; border-radius: 10px; border-left: 5px solid #9E9E9E; margin: 10px 0; font-family: monospace; font-size: 0.9rem; }
    .answer-box { background-color: #E8F5E9; padding: 15px; border-radius: 10px; border-left: 5px solid #4CAF50; margin: 10px 0; }
</style>
""", unsafe_allow_html=True)

GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY", ""))
if not GROQ_API_KEY or GROQ_API_KEY == "VOTRE_CLE_API":
    GROQ_API_KEY = st.text_input("🔑 Clé API Groq", type="password")

if GROQ_API_KEY:
    client = openai.OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")

st.markdown('<div class="main-title">📚 AssurRAG</div>', unsafe_allow_html=True)
st.markdown('<div style="text-align:center; color:#5A6C7D; margin-bottom:2rem;">Assistant Base de Connaissances - RAG (Retrieval-Augmented Generation)</div>', unsafe_allow_html=True)

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

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📄 Document de référence")
    document = st.text_area("Collez les conditions générales, une procédure, ou un document interne :", value=EXEMPLE_DOCUMENT, height=200)
    st.subheader("❓ Question")
    question = st.text_input("Question de l'assuré ou du conseiller :", "Quelle est la franchise pour un dégât des eaux ?")
    ask_btn = st.button("🔍 Répondre avec RAG", use_container_width=True)

with col2:
    st.subheader("ℹ️ À propos")
    st.markdown("""
    **AssurRAG** utilise le RAG :
    • Le LLM ne répond QUE sur la base du document
    • Pas d'hallucination
    • Sources vérifiables
    
    **Applications :**
    • Assistant conseiller
    • FAQ assurés
    • Conformité réglementaire
    
    **Technologie :**
    Un moteur IA haute performance
    Prompt engineering RAG
    
    **Développeur :** Wajih Jemli
    """)

if ask_btn and GROQ_API_KEY and document.strip() and question.strip():
    with st.spinner("Recherche dans la base de connaissances..."):
        prompt = f"""Tu es un expert en assurance. Réponds à la question UNIQUEMENT sur la base du document fourni ci-dessous.
Si la réponse n'est pas dans le document, dis exactement : "Cette information ne figure pas dans le document fourni."
Sois concis et précis. Cite l'article concerné si possible.

--- DOCUMENT ---
{document}
--- FIN DOCUMENT ---

Question : {question}

Réponse :"""
        response = client.chat.completions.create(model="openai/gpt-oss-120b", messages=[{"role": "user", "content": prompt}], temperature=0.1)
        answer = response.choices[0].message.content
    
    st.markdown("---")
    st.subheader("✅ Réponse")
    st.markdown(f'<div class="answer-box">{answer}</div>', unsafe_allow_html=True)
    st.info("💡 **En production**, le document serait découpé en chunks, indexé dans une base vectorielle (FAISS/Pinecone), et le système récupérerait automatiquement les passages pertinents avant de générer la réponse.")

st.markdown("""
<div style="text-align:center; color:#888; font-size:0.8rem; margin-top:3rem; padding-top:1rem; border-top:1px solid #eee;">
    📚 <b>AssurRAG</b> — POC par Wajih Jemli | RAG | IBM AI Developer
</div>
""", unsafe_allow_html=True)
