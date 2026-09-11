"""
Extrait le texte d'un constat scanné (OCR) puis le structure en champs exploitables — sans ressaisie manuelle.
POC — Wajih Jemli
"""

import json
import os
import re

import openai
import pytesseract
import streamlit as st
from PIL import Image

st.set_page_config(page_title="🔎 AssurOCR - Extraction de Constats", page_icon="🔎", layout="wide")

st.markdown("""
<style>
    .main-title { font-size: 2.2rem; font-weight: bold; color: #1E3A5F; text-align: center; }
    .subtitle { font-size: 1rem; color: #5A6C7D; text-align: center; margin-bottom: 2rem; }
    .extracted-field { background-color: #E8F5E9; color: #1a1a1a; padding: 10px 15px; border-radius: 8px; margin: 5px 0; border-left: 4px solid #4CAF50; }
    .missing-field { background-color: #FFEBEE; color: #1a1a1a; padding: 10px 15px; border-radius: 8px; margin: 5px 0; border-left: 4px solid #F44336; }
</style>
""", unsafe_allow_html=True)

GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY", ""))
if not GROQ_API_KEY or GROQ_API_KEY == "VOTRE_CLE_API":
    GROQ_API_KEY = st.text_input("🔑 Clé API Groq", type="password")

client = openai.OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1") if GROQ_API_KEY else None

CRITICAL_FIELDS = ["Date du sinistre", "Heure", "Assuré", "Nature du sinistre", "Lieu", "Immatriculation(s)"]
OTHER_FIELDS = ["Montant estimé", "Témoin(s)", "Téléphone témoin", "Blessures", "Plainte", "Objets/Véhicules"]
ALL_FIELDS = CRITICAL_FIELDS + OTHER_FIELDS

EXEMPLES_CONSTATS = [
    "Le 15 juillet 2026 à 14h30, M. Dupont Jean a heurté un poteau dans le parking du centre commercial Carrefour à Nice. Le pare-chocs avant de sa Renault Clio immatriculée AB-123-CD est endommagé. Témoin : Mme Martin Sophie, 06 12 34 56 78. Le conducteur n'est pas blessé. Dégâts estimés : 800 euros.",
    "Sinistre du 22/08/2026 vers 9h du matin. Mme Bernard Claire, 12 rue des Lilas 75011 Paris. Cambriolage de son appartement. Vol d'un ordinateur portable MacBook Pro, d'une télévision Samsung 55 pouces et de bijoux (bague en or, valeur estimée 1200€). Porte fracturée. Dépôt de plainte au commissariat du 10ème le même jour. Référence plainte : 2026-084521.",
    "Accident de la route ce matin 03/08/2026 à 7h45 sur l'autoroute A7 au niveau de Salon-de-Provence. Collision par l'arrière impliquant 2 véhicules : ma Peugeot 308 immatriculée EF-456-GH et un camion Renault. Conducteur du camion : M. Garcia Miguel. Légères blessures au cou. Transport à l'hôpital de Salon. Témoin : M. Petit Laurent, 07 89 01 23 45.",
]


def ocr_image(image):
    """Extrait le texte brut d'une image via Tesseract OCR (français)."""
    try:
        return pytesseract.image_to_string(image, lang="fra")
    except pytesseract.TesseractNotFoundError:
        return None


def extract_regex(text):
    """Extraction de secours par regex métier, sans appel IA (hors-ligne, instantanée)."""
    text_lower = text.lower()
    extracted = {}

    date_patterns = [
        r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})",
        r"(\d{1,2})\s+(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+(\d{4})",
        r"\b(\d{1,2})\s+(janv|févr|mars|avr|mai|juin|juil|août|sept|oct|nov|déc)\.?\s+(\d{4})\b",
    ]
    dates_found = []
    for pattern in date_patterns:
        for m in re.findall(pattern, text, re.IGNORECASE):
            dates_found.append(" ".join(m) if isinstance(m, tuple) else m)
    extracted["Date du sinistre"] = dates_found[0] if dates_found else None

    heures = re.findall(r"\b(\d{1,2})[h:](\d{2})?\b", text)
    extracted["Heure"] = (f"{heures[0][0]}h{heures[0][1]}" if heures[0][1] else f"{heures[0][0]}h00") if heures else None

    noms = re.findall(r"\b(M\.?|Mme\.?|Madame|Monsieur)\s+([A-Z][a-z]+)\s+([A-Z][a-z]+)", text)
    if noms:
        extracted["Assuré"] = f"{noms[0][0]} {noms[0][1]} {noms[0][2]}"
    else:
        noms_simple = re.findall(r"\bM(?:\.|me)?\s+([A-Z][a-z]+)\b", text)
        extracted["Assuré"] = noms_simple[0] if noms_simple else None

    immats = re.findall(r"\b([A-Z]{2}-\d{3}-[A-Z]{2})\b", text)
    extracted["Immatriculation(s)"] = ", ".join(immats) if immats else None

    natures = {
        "Accident de la route": ["accident", "collision", "heurter", "heurté", "tamponné", "carambolage"],
        "Cambriolage/Vol": ["cambriolage", "vol", "fracturé", "effraction", "dérobé", "dérober"],
        "Dégâts des eaux": ["dégât des eaux", "inondation", "fuite", "dégât d'eau", "écoulement"],
        "Incendie": ["incendie", "feu", "brûlé", "fumée"],
        "Vandalisme": ["vandalisme", "dégradation", "graffiti", "cassé"],
        "Tempête": ["tempête", "grêle", "orage", "vent"],
    }
    extracted["Nature du sinistre"] = next((nat for nat, kws in natures.items() if any(k in text_lower for k in kws)), None)

    lieu_patterns = [
        r"\bà\s+([A-Z][a-z]+(?:[-\s][A-Z][a-z]+)*)\b",
        r"\bsur\s+(l'autoroute\s+[A-Z]\d+)\b",
        r"\bdans\s+(le\s+parking\s+du\s+[^.]+)",
        r"\b(\d{1,4}\s+(?:rue|avenue|boulevard|chemin|place|impasse)\s+[^,\d]+)\b",
    ]
    lieux = []
    for pattern in lieu_patterns:
        lieux.extend(re.findall(pattern, text, re.IGNORECASE))
    extracted["Lieu"] = lieux[0] if lieux else None

    montants = re.findall(r"(\d+[\s.]?\d*)\s*(€|euros?)", text_lower)
    extracted["Montant estimé"] = f"{montants[0][0]} €" if montants else None

    temoins = re.findall(r"[Tt]émoin\s*:?\s*(?:M(?:me?)?\.?\s+)?([A-Z][a-z]+\s+[A-Z][a-z]+)", text)
    extracted["Témoin(s)"] = ", ".join(temoins) if temoins else None

    tels = re.findall(r"(\d{2}[\s.]?\d{2}[\s.]?\d{2}[\s.]?\d{2}[\s.]?\d{2})", text)
    extracted["Téléphone témoin"] = tels[0] if tels else None

    extracted["Blessures"] = "OUI - Vérifier garantie corporelle" if any(w in text_lower for w in ["blessé", "blessure", "hôpital", "urgence", "médical", "transport"]) else "Non détecté"

    if "plainte" in text_lower or "commissariat" in text_lower or "gendarmerie" in text_lower:
        ref_plainte = re.search(r"référence\s+plainte\s*:?\s*([\w-]+)", text_lower)
        extracted["Plainte"] = f"OUI - Réf: {ref_plainte.group(1)}" if ref_plainte else "OUI - Vérifier la référence"
    else:
        extracted["Plainte"] = "Non détecté"

    vehicules = re.findall(r"\b(Renault|Peugeot|Citroën|BMW|Mercedes|Audi|Volkswagen|Toyota|Ford|Clio|308|208|Golf|MacBook|Samsung|iPhone)\b", text, re.IGNORECASE)
    extracted["Objets/Véhicules"] = ", ".join(sorted(set(v.title() for v in vehicules))) if vehicules else None

    return extracted


def extract_with_ai(text):
    """Structuration via le moteur IA, à partir du texte brut (OCR ou saisi) — plus robuste au bruit OCR que le regex."""
    prompt = f"""Tu es un assistant qui structure des constats de sinistre assurance rédigés en texte libre (éventuellement issu d'une reconnaissance optique de caractères, donc potentiellement bruité).
Réponds UNIQUEMENT par un objet JSON strict (pas de texte autour, pas de markdown), avec exactement ces clés, en français, et `null` si l'information est absente :
{{
  "Date du sinistre": string ou null,
  "Heure": string ou null,
  "Assuré": string ou null,
  "Nature du sinistre": string ou null,
  "Lieu": string ou null,
  "Immatriculation(s)": string ou null,
  "Montant estimé": string ou null,
  "Témoin(s)": string ou null,
  "Téléphone témoin": string ou null,
  "Blessures": string ou null,
  "Plainte": string ou null,
  "Objets/Véhicules": string ou null
}}

Texte du constat :
\"\"\"{text}\"\"\""""
    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )
    content = response.choices[0].message.content
    match = re.search(r"\{.*\}", content, re.DOTALL)
    data = json.loads(match.group(0) if match else content)
    return {field: data.get(field) for field in ALL_FIELDS}


def render_results(result, source_text):
    st.markdown("---")
    st.subheader("📊 Informations extraites")

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**🎯 Informations clés**")
        for field in CRITICAL_FIELDS:
            val = result.get(field)
            css = "extracted-field" if val else "missing-field"
            display = val if val else "<i>Non détecté</i>"
            st.markdown(f'<div class="{css}"><b>{field}:</b> {display}</div>', unsafe_allow_html=True)
    with col_b:
        st.markdown("**📋 Informations complémentaires**")
        for field in OTHER_FIELDS:
            val = result.get(field)
            css = "extracted-field" if (val and val != "Non détecté") else "missing-field"
            display = val if (val and val != "Non détecté") else "<i>Non détecté</i>"
            st.markdown(f'<div class="{css}"><b>{field}:</b> {display}</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("📋 Résumé structuré pour le gestionnaire")
    resume = f"""
    **SINISTRE** | {result.get('Nature du sinistre') or 'Non classé'} | {result.get('Date du sinistre') or 'Date ?'} {result.get('Heure') or ''}
    **ASSURÉ** | {result.get('Assuré') or 'Non identifié'}
    **LIEU** | {result.get('Lieu') or 'Non précisé'}
    **VÉHICULE** | {result.get('Immatriculation(s)') or 'N/A'} | {result.get('Objets/Véhicules') or ''}
    **MONTANT** | {result.get('Montant estimé') or 'Non estimé'}
    **URGENCE** | {result.get('Blessures') or ''} | {result.get('Plainte') or ''}
    **TÉMOIN** | {result.get('Témoin(s)') or 'Aucun'} | {result.get('Téléphone témoin') or ''}
    """
    st.code(resume, language=None)
    st.info("💡 **En production**, cet outil serait connecté au CRM pour créer automatiquement le dossier sinistre avec ces données pré-remplies.")


def main():
    st.markdown('<div class="main-title">🔎 AssurOCR</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">OCR + Structuration Intelligente de Constats de Sinistres</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("📄 Document à traiter")
        uploaded_file = st.file_uploader("Scan ou photo du constat (JPG, PNG)", type=["jpg", "jpeg", "png"])

        ocr_text = ""
        if uploaded_file is not None:
            image = Image.open(uploaded_file)
            st.image(image, caption="Document chargé", use_container_width=True)
            with st.spinner("Extraction du texte (OCR)..."):
                ocr_result = ocr_image(image)
            if ocr_result is None:
                st.error("Tesseract OCR n'est pas installé sur ce serveur. Collez le texte du constat manuellement ci-dessous en attendant.")
            else:
                ocr_text = ocr_result

        st.subheader("📝 Texte du constat")
        selected = st.selectbox("Ou charger un exemple :", ["-- Utiliser le texte OCR / écrire manuellement --"] + EXEMPLES_CONSTATS)
        default_text = selected if selected != "-- Utiliser le texte OCR / écrire manuellement --" else ocr_text

        text_input = st.text_area(
            "Texte extrait par OCR ou saisi manuellement (corrigez si besoin avant extraction) :",
            value=default_text,
            height=180,
            placeholder="Ex: Le 15/07/2026 à 14h30, M. Dupont a heurté...",
        )

        extract_btn = st.button("🔍 Extraire les informations", use_container_width=True)

    with col2:
        st.subheader("ℹ️ À propos")
        st.markdown("""
        **AssurOCR** extrait automatiquement :
        • Date et heure du sinistre
        • Identité de l'assuré
        • Nature du sinistre
        • Lieu, immatriculation, montant
        • Témoins et coordonnées
        • Blessures et plainte déposée

        **Pipeline :**
        1. OCR (Tesseract) sur le document scanné
        2. Structuration par un moteur IA haute performance
        3. Repli par règles métier si aucune clé API

        **Gain métier :**
        Réduction du temps de saisie, standardisation des données.

        **Développeur :** Wajih Jemli
        """)

    if extract_btn and text_input.strip():
        if client:
            try:
                with st.spinner("Structuration par l'IA..."):
                    result = extract_with_ai(text_input)
            except Exception:
                st.warning("Le moteur IA n'a pas répondu correctement : repli sur l'extraction par règles métier.")
                result = extract_regex(text_input)
        else:
            st.warning("Clé API Groq manquante : extraction par règles métier (hors-ligne), sans reformulation par l'IA.")
            result = extract_regex(text_input)

        render_results(result, text_input)

    st.markdown("""
    <div style="text-align:center; color:#888; font-size:0.8rem; margin-top:3rem; padding-top:1rem; border-top:1px solid #eee;">
        🔎 <b>AssurOCR</b> — POC par Wajih Jemli | IBM AI Developer
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
