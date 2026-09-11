"""
Estime la gravité d'un sinistre à partir d'une simple photo envoyée par l'assuré — accélère le premier diagnostic avant expertise.
POC — Wajih Jemli
"""

import streamlit as st
import openai
import os
import base64
from PIL import Image
import io

st.set_page_config(
    page_title="📸 AssurVision - IA Vision Sinistres",
    page_icon="📸",
    layout="centered"
)

st.markdown("""
<style>
    .main-title { font-size: 2.2rem; font-weight: bold; color: #1E3A5F; text-align: center; }
    .result-box { background-color: #E8F5E9; padding: 15px; border-radius: 10px; border-left: 5px solid #4CAF50; margin: 10px 0; }
    .warning-box { background-color: #FFF3E0; padding: 15px; border-radius: 10px; border-left: 5px solid #FF9800; margin: 10px 0; }
    .model-info { background-color: #E3F2FD; padding: 10px; border-radius: 8px; margin-bottom: 15px; font-size: 0.9rem; }
    .translate-info { background-color: #F3E5F5; padding: 10px; border-radius: 8px; margin-bottom: 15px; font-size: 0.9rem; border-left: 4px solid #9C27B0; }
</style>
""", unsafe_allow_html=True)

# Récupération clé API Groq
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

st.markdown('<div class="main-title">📸 AssurVision</div>', unsafe_allow_html=True)
st.markdown('<div style="text-align:center; color:#5A6C7D; margin-bottom:2rem;">Analyse Intelligente des Photos de Sinistres par IA</div>', unsafe_allow_html=True)

if client:
    st.markdown('<div class="model-info">🤖 <b>Analyse vision IA</b> avec correction automatique de langue | <b>Développeur :</b> Wajih Jemli</div>', unsafe_allow_html=True)

def encode_image_to_base64(image):
    """Convertit une image PIL en base64 pour l'API Groq Vision"""
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

def clean_qwen_output(text):
    """
    Filtre le 'chain of thought' / raisonnement interne de Qwen.
    Ne conserve que la réponse finale structurée (à partir du point 1. 🏷️).
    """
    lines = text.split('\n')
    result = []
    started = False
    
    for line in lines:
        stripped = line.strip()
        if (stripped.startswith('1.') and '🏷️' in stripped and 'TYPE DE SINISTRE' in stripped) or \
           (stripped.startswith('1.') and '🏷️' in stripped and 'SINISTRE' in stripped):
            started = True
        elif not started and '🏷️' in stripped and 'TYPE DE SINISTRE' in stripped and stripped[0].isdigit():
            started = True
        
        if started:
            result.append(line)
    
    if result:
        return '\n'.join(result).strip()
    
    thinking_keywords = [
        'analyze user input', 'brouillon mental', 'correspondance avec la structure',
        'thinking process', 'draft', 'reasoning', 'step-by-step', 'plan de réponse',
        'réflexion préalable', 'analyse préliminaire'
    ]
    cleaned_lines = []
    for line in lines:
        lower_line = line.lower()
        if any(kw in lower_line for kw in thinking_keywords):
            continue
        cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines).strip()

def is_english_response(text):
    """Détecte si une réponse d'analyse de sinistre est majoritairement en anglais."""
    text_lower = text.lower()
    english_keywords = [
        "damage", "damaged", "vehicle", "accident", "collision", "repair", "estimated",
        "the ", "and ", "this ", "based", "image", "photo", "shows", "visible",
        "severe", "light", "moderate", "total", "yes", "no", "days", "euros",
        "recommendations", "expertise", "necessary", "drivable", "uncertain",
        "type", "loss", "front", "rear", "side", "bumper", "hood", "windshield",
        "scratch", "dent", "broken", "crack", "impact", "insurance", "claim"
    ]
    count = sum(1 for word in english_keywords if word in text_lower)
    return count >= 3

def translate_to_french(client, english_text):
    """Traduit une analyse de sinistre de l'anglais vers le français professionnel d'assurance."""
    system_prompt = (
        "Tu es un expert en assurance automobile français. "
        "Tu traduis des analyses de sinistres de l'anglais vers un français professionnel, structuré et concis. "
        "Tu conserves EXACTEMENT la même structure numérotée (1. à 8.). "
        "Tu adaptes les termes techniques à la terminologie française du secteur de l'assurance. "
        "Tu ne dois JAMAIS ajouter de texte hors des 8 points. "
        "Tu ne dois JAMAIS répondre en anglais. "
        "Tu ne dois JAMAIS inventer des informations."
    )
    
    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Traduis cette analyse de sinistre en français professionnel structuré (8 points) :\n\n{english_text}"}
        ],
        temperature=0.2,
        max_tokens=800
    )
    return response.choices[0].message.content

uploaded = st.file_uploader("📤 Uploader une photo du sinistre", type=["jpg", "jpeg", "png"])

if uploaded and client:
    img = Image.open(uploaded)
    st.image(img, width=500, caption="Photo chargée")
    
    with st.spinner("🔍 Analyse visuelle en cours..."):
        try:
            base64_image = encode_image_to_base64(img)
            
            response = client.chat.completions.create(
                model="qwen/qwen3.8-27b",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an automotive insurance expert. "
                            "You MUST respond in FRENCH only. "
                            "NEVER respond in English. "
                            "NEVER respond in any other language. "
                            "French only. "
                            "Tu es un expert en assurance automobile. "
                            "Tu réponds TOUJOURS et EXCLUSIVEMENT en français. "
                            "Jamais une seule phrase en anglais. "
                            "Ne montre JAMAIS ton raisonnement interne. "
                            "Ne commence PAS par 'Analyze User Input' ou 'Brouillon mental'. "
                            "Réponds DIRECTEMENT avec les 8 points demandés, sans introduction."
                        )
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "RÉPONDS EN FRANÇAIS UNIQUEMENT. FRENCH ONLY.\n\n"
                                    "Analyse cette photo de sinistre et réponds STRUCTURÉEMENT :\n\n"
                                    "1. 🏷️ TYPE DE SINISTRE\n"
                                    "2. 🔍 DOMMAGES DÉTECTÉS\n"
                                    "3. ⚠️ GRAVITÉ ESTIMÉE : Légère / Modérée / Élevée / Totale\n"
                                    "4. 🚗 VÉHICULE ROULANT : Oui / Non / Incertain\n"
                                    "5. 👨‍🔧 EXPERTISE NÉCESSAIRE : Oui / Non / Facultative\n"
                                    "6. ⏱️ DÉLAI RÉPARATION ESTIMÉ\n"
                                    "7. 💰 COÛT ESTIMÉ : Fourchette en euros\n"
                                    "8. 📋 RECOMMANDATIONS : 3 actions concrètes\n\n"
                                    "Sois professionnel, concis, objectif. N'invente rien.\n\n"
                                    "RÈGLE ABSOLUE : Ne montre PAS ton raisonnement. "
                                    "Ne commence PAS par '1. Analyze User Input' ou 'Brouillon mental'. "
                                    "Réponds DIRECTEMENT avec les 8 points ci-dessus.\n\n"
                                    "RAPPEL FINAL : TA RÉPONSE DOIT ÊTRE 100% EN FRANÇAIS, SANS RAISONNEMENT INTERNE."
                                )
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=800,
                temperature=0.3
            )
            
            raw_analysis = response.choices[0].message.content
            cleaned_analysis = clean_qwen_output(raw_analysis)
            
            if is_english_response(cleaned_analysis):
                with st.spinner("🔄 Qwen a répondu en anglais — traduction en cours par un moteur IA haute performance..."):
                    analysis = translate_to_french(client, cleaned_analysis)
                st.markdown('<div class="translate-info">ℹ️ <b>Traduction automatique :</b> Qwen a répondu en anglais — la réponse a été traduite en français par un moteur IA haute performance.</div>', unsafe_allow_html=True)
            else:
                analysis = cleaned_analysis
            
            st.markdown("---")
            st.subheader("📝 Analyse générée par l'IA")
            st.markdown(f'<div class="result-box">{analysis.replace(chr(10), "<br>")}</div>', unsafe_allow_html=True)
            
        except Exception as e:
            st.error(f"❌ Erreur lors de l'analyse : {str(e)}")
            st.info("💡 Vérifiez que votre clé API est valide et correctement configurée.")
    
    st.info("💡 **En production**, ce modèle serait affiné sur des milliers de photos de sinistres annotées pour une précision encore meilleure.")

elif uploaded and not client:
    st.error("❌ Clé API Groq non configurée. Veuillez entrer votre clé ci-dessus.")

st.markdown("""
<div style="text-align:center; color:#888; font-size:0.8rem; margin-top:3rem; padding-top:1rem; border-top:1px solid #eee;">
    📸 <b>AssurVision</b> — POC par Wajih Jemli | IBM AI Developer
</div>
""", unsafe_allow_html=True)
