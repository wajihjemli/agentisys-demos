"""
Traduit les échanges avec un assuré non francophone, en gardant le vocabulaire technique de l'assurance.
POC — Wajih Jemli
"""

import streamlit as st
import openai
import os
import tempfile
from gtts import gTTS

st.set_page_config(page_title="🌍 AssurTranslate Pro", page_icon="🌍", layout="centered")

st.markdown("""
<style>
    .main-title { font-size: 2.2rem; font-weight: bold; color: #1E3A5F; text-align: center; }
    .lang-box { padding: 15px; border-radius: 10px; margin: 10px 0; }
    .fr { background-color: #E8EAF6; border-left: 5px solid #3F51B5; }
    .en { background-color: #E3F2FD; border-left: 5px solid #2196F3; }
    .ar { background-color: #E0F2F1; border-left: 5px solid #009688; direction: rtl; text-align: right; }
    .it { background-color: #FFF3E0; border-left: 5px solid #FF9800; }
    .flag { font-size: 1.5rem; margin-right: 10px; }
</style>
""", unsafe_allow_html=True)

GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY", ""))
if not GROQ_API_KEY or GROQ_API_KEY == "VOTRE_CLE_API":
    GROQ_API_KEY = st.text_input("🔑 Clé API Groq", type="password")

if GROQ_API_KEY:
    client = openai.OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")

st.markdown('<div class="main-title">🌍 AssurTranslate Pro</div>', unsafe_allow_html=True)
st.markdown('<div style="text-align:center; color:#5A6C7D; margin-bottom:2rem;">Traducteur Intelligent avec IA (moteur haute performance + TTS)</div>', unsafe_allow_html=True)

LANGUES = {
    "fr": ("🇫🇷 Français", "fr"),
    "en": ("🇬🇧 English", "en"),
    "ar": ("🇸🇦 العربية", "ar"),
    "it": ("🇮🇹 Italiano", "it"),
    "es": ("🇪🇸 Español", "es"),
    "de": ("🇩🇪 Deutsch", "de")
}

col1, col2 = st.columns([2, 1])

with col1:
    text = st.text_area("Texte à traduire", "Bonjour, votre sinistre a bien été enregistré. Un gestionnaire vous contactera sous 48 heures.", height=100)
    
    c1, c2 = st.columns(2)
    with c1:
        source = st.selectbox("Source", list(LANGUES.keys()), format_func=lambda x: LANGUES[x][0])
    with c2:
        target = st.selectbox("Cible", ["en", "ar", "it", "fr"], format_func=lambda x: LANGUES[x][0])
    
    translate_btn = st.button("🔄 Traduire avec Un moteur IA haute performance", use_container_width=True)

with col2:
    st.subheader("ℹ️ À propos")
    st.markdown("""
    **Technologie :**
    • LLM : un moteur IA haute performance
    • Traduction contextuelle métier
    • TTS intégré (gTTS)
    
    **Langues assurance :**
    🇫🇷 FR → 🇬🇧 EN (expatriés)
    🇫🇷 FR → 🇸🇦 AR (communauté)
    🇫🇷 FR → 🇮🇹 IT (frontaliers)
    
    **Développeur :** Wajih Jemli
    """)

if translate_btn and GROQ_API_KEY and text.strip():
    with st.spinner("Traduction en cours..."):
        prompt = f"""Tu es un traducteur professionnel spécialisé dans le secteur de l'assurance.
Traduis ce texte du {LANGUES[source][1]} vers le {LANGUES[target][1]}.
Conserve le ton professionnel et les termes techniques assurance.
Ne donne QUE la traduction, sans explication.

Texte : {text}"""
        
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        translated = response.choices[0].message.content.strip()
    
    st.markdown("---")
    st.subheader("📋 Résultat")
    
    col_fr, col_tr = st.columns(2)
    with col_fr:
        st.markdown(f'<div class="lang-box fr"><span class="flag">🇫🇷</span><b>Original</b><br><br>{text}</div>', unsafe_allow_html=True)
    with col_tr:
        css_class = "ar" if target == "ar" else ("it" if target == "it" else "en")
        st.markdown(f'<div class="lang-box {css_class}"><span class="flag">{LANGUES[target][0][:4]}</span><b>Traduction</b><br><br>{translated}</div>', unsafe_allow_html=True)
    
    with st.spinner("Génération audio..."):
        lang_tts = LANGUES[target][1]
        if lang_tts == "ar":
            lang_tts = "ar"
        elif lang_tts == "it":
            lang_tts = "it"
        elif lang_tts == "fr":
            lang_tts = "fr"
        else:
            lang_tts = "en"
        
        tts = gTTS(text=translated, lang=lang_tts, slow=False)
        tts_path = tempfile.mktemp(suffix=".mp3")
        tts.save(tts_path)
    
    st.subheader("🔊 Écouter la traduction")
    st.audio(tts_path, format="audio/mp3")
    
    st.download_button("⬇️ Télécharger l'audio", open(tts_path, "rb"), f"traduction_{target}.mp3")

st.markdown("""
<div style="text-align:center; color:#888; font-size:0.8rem; margin-top:3rem; padding-top:1rem; border-top:1px solid #eee;">
    🌍 <b>AssurTranslate Pro</b> — POC par Wajih Jemli | gTTS | IBM AI Developer
</div>
""", unsafe_allow_html=True)
