"""
Analyse le sentiment et l'urgence d'une réclamation client assurance, et recommande une action.
POC — Wajih Jemli
"""

import json
import os
import re

import openai
import streamlit as st

st.set_page_config(page_title="📊 SentiClaim - Analyse de Sentiment", page_icon="📊", layout="wide")

st.markdown("""
<style>
    .main-title { font-size: 2.2rem; font-weight: bold; color: #1E3A5F; text-align: center; }
    .subtitle { font-size: 1rem; color: #5A6C7D; text-align: center; margin-bottom: 2rem; }
    .positive { background-color: #E8F5E9; color: #1a1a1a; padding: 15px; border-radius: 10px; border-left: 5px solid #4CAF50; }
    .negative { background-color: #FFEBEE; color: #1a1a1a; padding: 15px; border-radius: 10px; border-left: 5px solid #F44336; }
    .neutral { background-color: #FFF3E0; color: #1a1a1a; padding: 15px; border-radius: 10px; border-left: 5px solid #FF9800; }
    .metric-box { background-color: #F5F5F5; color: #1a1a1a; padding: 15px; border-radius: 10px; text-align: center; }
    .action-box { background-color: #E3F2FD; color: #1a1a1a; padding: 12px; border-radius: 8px; margin-top: 10px; }
</style>
""", unsafe_allow_html=True)

GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY", ""))
if not GROQ_API_KEY or GROQ_API_KEY == "VOTRE_CLE_API":
    GROQ_API_KEY = st.text_input("🔑 Clé API Groq", type="password")

client = openai.OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1") if GROQ_API_KEY else None

CATEGORIES = ["sinistre", "remboursement", "contrat", "service_client", "resiliation", "général"]

EMOJI_PAR_SENTIMENT = {"POSITIF": "😊", "NÉGATIF": "😠", "NEUTRE": "😐"}
CLASSE_PAR_SENTIMENT = {"POSITIF": "positive", "NÉGATIF": "negative", "NEUTRE": "neutral"}

# Lexique de secours, utilisé uniquement si la clé API est absente ou l'appel échoue
MOTS_NEGATIFS = [
    "refusé", "refus", "rejette", "rejeté", "impossible", "inacceptable", "scandaleux",
    "indigné", "furieux", "énervé", "mécontent", "insatisfait", "déçu", "déception",
    "attendre", "retard", "lent", "aucun", "jamais", "rien", "problème", "bug",
    "erreur", "faux", "mensonge", "arnaque", "vol", "escroquerie", "honteux",
    "incompétent", "nul", "catastrophe", "horrible", "désastre", "pire", "abandonner",
    "résilier", "plainte", "tribunal", "médiateur", "huissier", "avocat", "procès",
]
MOTS_POSITIFS = [
    "merci", "satisfait", "content", "heureux", "ravi", "excellent", "parfait",
    "super", "génial", "bravo", "félicitations", "efficace", "rapide", "réactif",
    "professionnel", "aimable", "gentil", "compétent", "résolu", "solution",
    "réglé", "remboursé", "indemnisé", "recommande", "confiance", "rassuré",
]
MOTS_URGENCE = [
    "urgent", "urgence", "hospitalisation", "décès", "accident", "grave",
    "incapacité", "sinistre", "catastrophe", "inondation", "incendie", "vol", "agression",
]
CATEGORIE_KEYWORDS = {
    "sinistre": ["sinistre", "accident", "dégât", "dommage", "vol", "incendie", "inondation"],
    "remboursement": ["remboursement", "rembourser", "frais", "facture", "devis", "paiement"],
    "contrat": ["contrat", "garantie", "couverture", "exclusion", "condition", "clause"],
    "service_client": ["conseiller", "appel", "attente", "standard", "accueil", "réponse"],
    "resiliation": ["résilier", "résiliation", "résilié", "annuler"],
}

EXEMPLES = [
    "Mon sinistre n'est toujours pas traité après 3 semaines. C'est inacceptable ! Je veux parler à un responsable.",
    "Merci pour votre rapidité. Le remboursement a été effectué sous 5 jours. Très satisfait de votre service.",
    "J'attends depuis 2 mois un remboursement de 850€ pour mes frais dentaires. Personne ne me répond. C'est du vol !",
    "Le conseiller était très aimable et a résolu mon problème en 10 minutes. Bravo à votre équipe.",
    "Mon père est hospitalisé en urgence à l'étranger et votre assistance ne décroche pas. C'est une urgence vitale !",
    "Je souhaite résilier mon contrat. Vos conditions ont changé sans préavis. Je vais saisir le médiateur.",
]


def analyze_lexicon(text):
    """Analyse de secours par lexique métier, sans appel IA (hors-ligne, instantanée)."""
    text_lower = text.lower()
    words = re.findall(r"\b\w+\b", text_lower)

    neg_count = sum(1 for w in words if w in MOTS_NEGATIFS)
    pos_count = sum(1 for w in words if w in MOTS_POSITIFS)
    if any(x in text_lower for x in ["!", "??", "trop", "très", "vraiment", "extrêmement"]):
        neg_count *= 1.3
        pos_count *= 1.3
    score = pos_count - neg_count

    if score >= 1:
        sentiment = "POSITIF"
    elif score <= -1:
        sentiment = "NÉGATIF"
    else:
        sentiment = "NEUTRE"

    urgence = any(u in text_lower for u in MOTS_URGENCE)
    cat_scores = {cat: sum(1 for k in kws if k in text_lower) for cat, kws in CATEGORIE_KEYWORDS.items()}
    categorie = max(cat_scores, key=cat_scores.get) if max(cat_scores.values()) > 0 else "général"
    intensity = min(100, int((abs(score) + (2 if urgence else 0)) * 15))

    if sentiment == "NÉGATIF" and urgence:
        action = "🔴 ESCALADE IMMÉDIATE : Appeler le client sous 1h. Sinistre/urgence détecté(e)."
    elif sentiment == "NÉGATIF" and intensity > 60:
        action = "🟠 PRIORITAIRE : Contacter le client sous 4h. Risque de plainte/résiliation."
    elif sentiment == "NÉGATIF":
        action = "🟡 À TRAITER : Répondre sous 24h. Proposer une solution concrète."
    elif sentiment == "POSITIF":
        action = "🟢 SATISFACTION : Enregistrer le feedback positif. Demander un témoignage."
    else:
        action = "⚪ STANDARD : Traiter dans les délais habituels."

    return {
        "sentiment": sentiment,
        "intensity": intensity,
        "urgence": urgence,
        "categorie": categorie,
        "mots_cles": sorted(set(w for w in words if w in MOTS_NEGATIFS or w in MOTS_POSITIFS)),
        "action": action,
    }


def analyze_with_ai(text):
    """Analyse via le moteur IA : sentiment, intensité, urgence, catégorie et action recommandée."""
    prompt = f"""Tu es un analyste qualité senior dans une compagnie d'assurance.
Analyse cette réclamation client et réponds UNIQUEMENT par un objet JSON strict (pas de texte autour, pas de markdown), avec exactement ces clés :
{{
  "sentiment": "POSITIF" ou "NÉGATIF" ou "NEUTRE",
  "intensity": entier de 0 à 100 (intensité émotionnelle),
  "urgence": true ou false (urgence vitale, sinistre grave, hospitalisation...),
  "categorie": une valeur parmi {CATEGORIES},
  "mots_cles": liste de 2 à 6 mots ou expressions déclencheurs tirés du texte,
  "action": une phrase d'action recommandée pour le conseiller, avec délai
}}

Réclamation : "{text}" """
    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )
    content = response.choices[0].message.content
    match = re.search(r"\{.*\}", content, re.DOTALL)
    result = json.loads(match.group(0) if match else content)

    result["sentiment"] = result.get("sentiment", "NEUTRE").upper()
    if result["sentiment"] not in EMOJI_PAR_SENTIMENT:
        result["sentiment"] = "NEUTRE"
    result["intensity"] = max(0, min(100, int(result.get("intensity", 0))))
    result["urgence"] = bool(result.get("urgence", False))
    result["categorie"] = result.get("categorie") if result.get("categorie") in CATEGORIES else "général"
    result["mots_cles"] = result.get("mots_cles", [])
    result["action"] = result.get("action", "")
    return result


def main():
    st.markdown('<div class="main-title">📊 SentiClaim</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Analyse de Sentiment des Réclamations Assurance</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("📝 Texte à analyser")
        selected_example = st.selectbox("Charger un exemple :", ["-- Écrire manuellement --"] + EXEMPLES)
        default_text = selected_example if selected_example != "-- Écrire manuellement --" else ""
        text_input = st.text_area("Réclamation client :", value=default_text, height=120, placeholder="Collez ici le texte de la réclamation...")
        analyze_btn = st.button("🔍 Analyser le sentiment", use_container_width=True)

    with col2:
        st.subheader("ℹ️ À propos")
        st.markdown("""
        **SentiClaim** détecte automatiquement :
        • Le sentiment (Positif / Négatif / Neutre)
        • Le niveau d'intensité émotionnelle
        • Les mots-clés déclencheurs
        • La catégorie métier
        • L'urgence (sinistre, hospitalisation...)
        • L'action recommandée

        **Technologie :**
        Un moteur IA haute performance

        **Développeur :** Wajih Jemli
        """)

    if analyze_btn and text_input.strip():
        if client:
            try:
                with st.spinner("Analyse par l'IA..."):
                    result = analyze_with_ai(text_input)
            except Exception:
                st.warning("Le moteur IA n'a pas répondu correctement : repli sur l'analyse par lexique métier.")
                result = analyze_lexicon(text_input)
        else:
            st.warning("Clé API Groq manquante : analyse par lexique métier (hors-ligne), sans reformulation par l'IA.")
            result = analyze_lexicon(text_input)

        emoji = EMOJI_PAR_SENTIMENT[result["sentiment"]]
        color_class = CLASSE_PAR_SENTIMENT[result["sentiment"]]

        st.markdown("---")
        st.subheader("📈 Résultats de l'analyse")

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f'<div class="metric-box"><h2>{emoji}</h2><h3>{result["sentiment"]}</h3></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="metric-box"><h2>{result["intensity"]}%</h2><h3>Intensité</h3></div>', unsafe_allow_html=True)
        with c3:
            urgence_txt = "🔴 OUI" if result["urgence"] else "🟢 Non"
            st.markdown(f'<div class="metric-box"><h2>{urgence_txt}</h2><h3>Urgence</h3></div>', unsafe_allow_html=True)
        with c4:
            cat_display = result["categorie"].replace("_", " ").title()
            st.markdown(f'<div class="metric-box"><h2>{cat_display}</h2><h3>Catégorie</h3></div>', unsafe_allow_html=True)

        st.markdown(f'<div class="{color_class}"><h4>📝 Texte analysé</h4><p><i>"{text_input}"</i></p></div>', unsafe_allow_html=True)

        if result["mots_cles"]:
            st.markdown("**🔑 Mots-clés déclencheurs :** " + ", ".join(result["mots_cles"]))

        st.markdown(f'<div class="action-box"><h4>🎯 Action recommandée</h4><p>{result["action"]}</p></div>', unsafe_allow_html=True)

        st.markdown("---")
        st.subheader("📊 Aperçu rapide — 6 réclamations (heuristique hors-ligne)")
        st.caption("Aperçu instantané par lexique métier, pour un balayage rapide d'un lot. L'analyse détaillée ci-dessus utilise le moteur IA.")
        for i, ex in enumerate(EXEMPLES, 1):
            res = analyze_lexicon(ex)
            with st.expander(f"Réclamation #{i} - {res['sentiment']} {EMOJI_PAR_SENTIMENT[res['sentiment']]} (Intensité: {res['intensity']}%)"):
                st.markdown(f"**Texte :** *{ex}*")
                st.markdown(f"**Action :** {res['action']}")

    st.markdown("""
    <div style="text-align:center; color:#888; font-size:0.8rem; margin-top:3rem; padding-top:1rem; border-top:1px solid #eee;">
        📊 <b>SentiClaim</b> — POC par Wajih Jemli | IBM AI Developer
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
