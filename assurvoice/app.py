"""
Callbot vocal qui recueille une déclaration de sinistre à la voix et y répond en temps réel.
POC — Wajih Jemli
"""

import streamlit as st
import openai
import os
import tempfile
import asyncio
import edge_tts

st.set_page_config(
    page_title="🎙️ AssurVoice - Callbot Vocal",
    page_icon="🎙️",
    layout="centered"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%); background-attachment: fixed; }
    .main .block-container { max-width: 900px; padding: 2rem 3rem; }
    .main-title { font-size: 2.8rem; font-weight: 700; background: linear-gradient(90deg, #60a5fa, #a78bfa); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-align: center; letter-spacing: -0.02em; margin-bottom: 0.5rem; animation: fadeInDown 0.8s ease-out; }
    .subtitle { font-size: 1.1rem; color: #94a3b8; text-align: center; font-weight: 300; margin-bottom: 2.5rem; animation: fadeInDown 0.8s ease-out 0.2s both; }
    .glass-card { background: rgba(30, 41, 59, 0.6); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); border: 1px solid rgba(148, 163, 184, 0.1); border-radius: 16px; padding: 1.5rem; margin: 1rem 0; box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3); animation: fadeInUp 0.6s ease-out; }
    .step-box { background: rgba(59, 130, 246, 0.08); border-left: 4px solid #3b82f6; padding: 1.2rem 1.5rem; border-radius: 0 12px 12px 0; margin: 1rem 0; color: #e2e8f0; animation: slideInLeft 0.5s ease-out; }
    .result-box { background: rgba(34, 197, 94, 0.08); border-left: 4px solid #22c55e; padding: 1.5rem; border-radius: 0 12px 12px 0; margin: 1rem 0; color: #e2e8f0; font-size: 1rem; line-height: 1.7; animation: fadeInUp 0.6s ease-out; }
    .model-info { background: rgba(99, 102, 241, 0.08); border: 1px solid rgba(99, 102, 241, 0.2); padding: 1rem 1.2rem; border-radius: 12px; color: #c7d2fe; font-size: 0.9rem; margin-bottom: 1.5rem; text-align: center; }
    .stButton > button { background: linear-gradient(135deg, #3b82f6, #6366f1) !important; color: white !important; border: none !important; border-radius: 12px !important; padding: 0.8rem 2rem !important; font-weight: 600 !important; font-size: 1rem !important; transition: all 0.3s ease !important; box-shadow: 0 4px 15px rgba(59, 130, 246, 0.3) !important; }
    .stButton > button:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(59, 130, 246, 0.5) !important; }
    .stTextInput > div > div > input, .stTextArea > div > div > textarea { background: rgba(30, 41, 59, 0.8) !important; border: 1px solid rgba(148, 163, 184, 0.2) !important; border-radius: 10px !important; color: #e2e8f0 !important; padding: 0.8rem 1rem !important; }
    .stFileUploader > div > button { background: rgba(30, 41, 59, 0.8) !important; border: 2px dashed rgba(148, 163, 184, 0.3) !important; border-radius: 12px !important; color: #94a3b8 !important; }
    .stSelectbox > div > div > div { background: rgba(30, 41, 59, 0.8) !important; border: 1px solid rgba(148, 163, 184, 0.2) !important; border-radius: 10px !important; color: #e2e8f0 !important; }
    .stSpinner > div { color: #60a5fa !important; }
    audio { width: 100%; border-radius: 12px; margin-top: 1rem; }
    @keyframes fadeInDown { from { opacity: 0; transform: translateY(-20px); } to { opacity: 1; transform: translateY(0); } }
    @keyframes fadeInUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
    @keyframes slideInLeft { from { opacity: 0; transform: translateX(-30px); } to { opacity: 1; transform: translateX(0); } }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    ::-webkit-scrollbar { width: 8px; }
    ::-webkit-scrollbar-track { background: #0f172a; }
    ::-webkit-scrollbar-thumb { background: #334155; border-radius: 4px; }
    ::-webkit-scrollbar-thumb:hover { background: #475569; }
</style>
""", unsafe_allow_html=True)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
if not GROQ_API_KEY:
    try:
        GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "")
    except Exception:
        pass

if not GROQ_API_KEY:
    st.warning("🔑 Clé API Groq requise")
    GROQ_API_KEY = st.text_input("Entrez votre clé API Groq", type="password")

client = None
if GROQ_API_KEY:
    client = openai.OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")

st.markdown('<div class="main-title">🎙️ AssurVoice</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Callbot Intelligent — Parlez, l\'IA répond en direct</div>', unsafe_allow_html=True)

if client:
    st.markdown('<div class="model-info">🤖 <b>Modèle IA :</b> Whisper Large v3 | LLM: un moteur IA haute performance | TTS: Edge TTS (Microsoft Neural) | <b>Développeur :</b> Wajih Jemli</div>', unsafe_allow_html=True)

async def generate_speech(text: str, voice: str, output_path: str):
    """Génère la synthèse vocale avec Edge TTS."""
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("🎙️ Étape 1 : Parlez ou uploader un audio")
    st.markdown("**Option A : Parler directement**")
    audio_input = st.audio_input("🎤 Appuyez pour enregistrer votre voix", key="micro_input")
    st.markdown("---")
    st.markdown("**Option B : Uploader un fichier audio**")
    audio_file = st.file_uploader("Choisir un fichier (MP3, WAV, M4A)", type=["mp3", "wav", "m4a", "webm"])
    text_input = st.text_area("Ou saisir le texte directement :", placeholder="Ex: Bonjour, j'ai eu un accident ce matin sur l'autoroute...", height=80)
    st.markdown("**🎙️ Voix de l'assistante**")
    voice_choice = st.selectbox(
        "Choisir la voix d'Eva",
        options=[
            ("fr-FR-DeniseNeural", "🇫🇷 Denise — Femme, chaleureuse (recommandée)"),
            ("fr-FR-EloiseNeural", "🇫🇷 Éloïse — Femme, douce"),
            ("fr-FR-HenriNeural", "🇫🇷 Henri — Homme, clair"),
        ],
        format_func=lambda x: x[1],
        index=0
    )
    selected_voice = voice_choice[0]
    process_btn = st.button("🚀 Lancer l'analyse complète", use_container_width=True)

with col2:
    st.subheader("ℹ️ Chaîne vocale")
    st.markdown("""
    <div class="glass-card">
    <b>1. STT</b> 🎤 → 📝<br>
    <code>whisper-large-v3</code><br>
    Reconnaissance vocale<br><br>
    <b>2. LLM</b> 📝 → 🧠<br>
    <code>openai/gpt-oss-20b</code><br>
    Compréhension & réponse<br><br>
    <b>3. TTS</b> 🧠 → 🔊<br>
    <code>Edge TTS</code> (Microsoft Neural)<br>
    Synthèse vocale haute qualité<br><br>
    <b>Développeur :</b> Wajih Jemli
    </div>
    """, unsafe_allow_html=True)

if process_btn and client:
    user_text = ""
    source = ""
    
    if audio_input:
        with st.spinner("🎤 Étape 1/3 : Transcription avec Whisper Large v3..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                tmp.write(audio_input.read())
                tmp_path = tmp.name
            with open(tmp_path, "rb") as f:
                transcript = client.audio.transcriptions.create(model="whisper-large-v3", file=f, language="fr", response_format="text")
            user_text = transcript.text if hasattr(transcript, 'text') else str(transcript)
            source = "🎤 Micro intégré"
        st.markdown(f'<div class="step-box"><b>📝 Transcription (Whisper) :</b><br><i>"{user_text}"</i></div>', unsafe_allow_html=True)
    elif audio_file:
        with st.spinner("🎤 Étape 1/3 : Transcription fichier avec Whisper Large v3..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{audio_file.name.split('.')[-1]}") as tmp:
                tmp.write(audio_file.read())
                tmp_path = tmp.name
            with open(tmp_path, "rb") as f:
                transcript = client.audio.transcriptions.create(model="whisper-large-v3", file=f, language="fr", response_format="text")
            user_text = transcript.text if hasattr(transcript, 'text') else str(transcript)
            source = "📁 Fichier uploadé"
        st.markdown(f'<div class="step-box"><b>📝 Transcription (Whisper) :</b><br><i>"{user_text}"</i></div>', unsafe_allow_html=True)
    elif text_input.strip():
        user_text = text_input
        source = "⌨️ Texte saisi"
        st.markdown(f'<div class="step-box"><b>📝 Texte :</b><br><i>"{user_text}"</i></div>', unsafe_allow_html=True)
    else:
        st.error("Veuillez parler dans le micro, uploader un audio, OU saisir un texte.")
        st.stop()
    
    with st.spinner("🤖 Étape 2/3 : Analyse par un moteur IA haute performance..."):
        system_prompt = """Tu es Eva, l'assistante virtuelle d'une compagnie d'assurance française. 
Tu aides les clients à déclarer des sinistres et réponds à leurs questions.
Règles :
- Sois professionnelle, empathique et concise (max 4 phrases)
- Identifie la nature du sinistre, la date, le lieu, les dégâts
- Propose les prochaines étapes concrètes
- Si c'est une urgence (blessures, incendie), indique immédiatement le numéro d'assistance 24h/24 : 01 23 45 67 90"""
        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_text}],
            temperature=0.7,
            max_tokens=300
        )
        ai_reply = response.choices[0].message.content
    
    st.markdown(f'<div class="result-box"><b>🤖 Réponse de l\'assistante (un moteur IA haute performance) :</b><br><br>{ai_reply}</div>', unsafe_allow_html=True)
    
    with st.spinner("📊 Extraction des informations clés..."):
        extraction_prompt = f"""À partir de ce message client, extrais UNIQUEMENT ces informations au format JSON :
- nature_sinistre
- date_sinistre
- lieu
- degats
- blessures (oui/non)
- contact_urgence (oui/non)

Message : {user_text}

Réponds UNIQUEMENT en JSON, sans texte avant ou après."""
        try:
            extraction = client.chat.completions.create(model="openai/gpt-oss-20b", messages=[{"role": "user", "content": extraction_prompt}], temperature=0.1)
            st.json(extraction.choices[0].message.content)
        except:
            pass
    
    with st.spinner(f"🔊 Étape 3/3 : Génération vocale (Edge TTS — {selected_voice})..."):
        tts_path = tempfile.mktemp(suffix=".mp3")
        asyncio.run(generate_speech(ai_reply, selected_voice, tts_path))
    
    st.subheader("🔊 Écouter la réponse")
    st.audio(tts_path, format="audio/mp3")
    st.download_button("⬇️ Télécharger la réponse audio", open(tts_path, "rb"), "reponse_assurvoice.mp3", mime="audio/mp3")
    st.info(f"💡 Source : {source} | Voix : `{selected_voice}` | **En production**, ce callbot serait connecté à la téléphonie (Twilio/Aircall) pour des conversations vocales temps réel 24h/24.")

elif process_btn and not client:
    st.error("❌ Clé API Groq manquante. Veuillez la configurer ci-dessus.")

st.markdown("""
<div style="text-align:center; color:#64748b; font-size:0.8rem; margin-top:3rem; padding-top:1.5rem; border-top:1px solid rgba(148,163,184,0.1);">
    🎙️ <b>AssurVoice</b> — POC par Wajih Jemli | Groq API (Whisper + un moteur IA haute performance + Edge TTS) | IBM AI Developer
</div>
""", unsafe_allow_html=True)
