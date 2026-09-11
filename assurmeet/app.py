"""
Résume un appel client et en extrait les actions à suivre — sans écoute manuelle a posteriori.
POC — Wajih Jemli
"""

import streamlit as st
import openai
import os

st.set_page_config(page_title="📝 AssurMeet - AI Meeting Companion", page_icon="📝", layout="wide")

st.markdown("""
<style>
    .main-title { font-size: 2.2rem; font-weight: bold; color: #1E3A5F; text-align: center; }
    .result-box { background-color: #E3F2FD; padding: 15px; border-radius: 10px; margin: 10px 0; border-left: 5px solid #2196F3; }
    .action-box { background-color: #E8F5E9; padding: 12px; border-radius: 8px; margin: 8px 0; border-left: 4px solid #4CAF50; }
    .risk-box { background-color: #FFEBEE; padding: 12px; border-radius: 8px; margin: 8px 0; border-left: 4px solid #F44336; }
</style>
""", unsafe_allow_html=True)

GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY", ""))
if not GROQ_API_KEY or GROQ_API_KEY == "VOTRE_CLE_API":
    GROQ_API_KEY = st.text_input("🔑 Clé API Groq", type="password")

if GROQ_API_KEY:
    client = openai.OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")

st.markdown('<div class="main-title">📝 AssurMeet</div>', unsafe_allow_html=True)
st.markdown('<div style="text-align:center; color:#5A6C7D; margin-bottom:2rem;">AI Meeting Companion - Analyse d\'Appels Clients Assurance</div>', unsafe_allow_html=True)

EXEMPLE_TRANSCRIPT = """Conseiller : Bonjour Madame, je vous écoute.
Client : Bonjour, j'appelle pour mon sinistre du 15 juillet. J'attends depuis 3 semaines et personne ne me donne de nouvelles.
Conseiller : Je comprends votre impatience Madame. Pouvez-vous me donner votre numéro de dossier ?
Client : C'est le 2026-084521. J'ai envoyé tous les documents, le constat, les photos, le devis... Et depuis, silence radio !
Conseiller : Je vois votre dossier Madame. Il est effectivement en attente de validation par notre service expertise. Je vais faire une relance immédiate.
Client : Ça fait 3 semaines que j'attends ! J'ai besoin de ma voiture pour aller travailler. C'est inacceptable !
Conseiller : Je comprends tout à fait. Je vous propose de vous rappeler demain avant 14h avec une réponse définitive. Est-ce que cela vous convient ?
Client : D'accord, mais si je n'ai pas de nouvelles, je résilie mon contrat et je vais voir ailleurs.
Conseiller : Je vous garantis un retour demain Madame. Merci de votre patience."""

col1, col2 = st.columns([2, 1])

with col1:
    transcript = st.text_area("Collez le transcript de l'appel", value=EXEMPLE_TRANSCRIPT, height=250)
    analyze_btn = st.button("🔍 Analyser l'appel", use_container_width=True)

with col2:
    st.subheader("ℹ️ Fonctionnalités")
    st.markdown("""
    **AssurMeet analyse :**
    • Résumé de l'appel (3 lignes)
    • Points clés discutés
    • Actions à suivre
    • Sentiment client
    • Risques identifiés
    • Promesses faites
    
    **Technologie :**
    Un moteur IA haute performance
    Prompt engineering métier
    
    **Développeur :** Wajih Jemli
    """)

if analyze_btn and GROQ_API_KEY and transcript.strip():
    with st.spinner("Analyse par l'IA..."):
        prompt = f"""Tu es un analyste qualité senior dans une compagnie d'assurance.
Analyse ce transcript d'appel client et fournis UNIQUEMENT :

## 📋 RÉSUMÉ (2-3 lignes max)

## 🎯 POINTS CLÉS
• Liste à puces des sujets abordés

## ✅ ACTIONS À SUIVRE
| Action | Responsable | Délai | Priorité |

## 😊 SENTIMENT CLIENT
• Émotion dominante
• Niveau de satisfaction (1-10)
• Risque de départ

## ⚠️ RISQUES IDENTIFIÉS
• Liste des risques

## 📌 PROMESSES FAITES PAR LE CONSEILLER
• Liste des engagements

Transcript :
{transcript}"""
        response = client.chat.completions.create(model="openai/gpt-oss-120b", messages=[{"role": "user", "content": prompt}], temperature=0.3)
        analysis = response.choices[0].message.content
    
    st.markdown("---")
    st.subheader("📊 Résultat de l'analyse")
    st.markdown(analysis)
    st.markdown("""
    <div class="result-box">
    <b>💡 Gain métier :</b> Cette analyse automatique remplace l'écoute manuelle (2% des appels contrôlés) par une couverture de 100% des appels, avec détection automatique des risques de résiliation et des non-conformités.
    </div>
    """, unsafe_allow_html=True)

st.markdown("""
<div style="text-align:center; color:#888; font-size:0.8rem; margin-top:3rem; padding-top:1rem; border-top:1px solid #eee;">
    📝 <b>AssurMeet</b> — POC par Wajih Jemli | IBM AI Developer
</div>
""", unsafe_allow_html=True)
