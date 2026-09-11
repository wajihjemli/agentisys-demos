# 📊 SentiClaim

Analyse le sentiment, l'intensité émotionnelle, l'urgence et la catégorie métier d'une réclamation client assurance, et recommande une action avec délai — à partir d'un moteur IA haute performance.

## Fonctionnement

1. Le texte de la réclamation est envoyé à un prompt structuré qui contraint le modèle à répondre en JSON strict (sentiment, intensité, urgence, catégorie, mots-clés, action recommandée).
2. Si aucune clé API n'est configurée, ou si l'appel échoue, l'app se rabat automatiquement sur une analyse par lexique métier (hors-ligne, instantanée) plutôt que de planter.
3. Un aperçu rapide sur 6 réclamations types utilise ce même lexique de secours, pour un balayage de lot sans multiplier les appels API.

## Lancer en local

```bash
pip install -r requirements.txt
streamlit run app.py
```

Configurer la clé API dans `.streamlit/secrets.toml` :

```toml
GROQ_API_KEY = "votre_clé"
```

(ou via la variable d'environnement `GROQ_API_KEY`, ou en la saisissant directement dans l'interface).
