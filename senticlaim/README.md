# 📊 SentiClaim

Détecte le sentiment, l'intensité émotionnelle, l'urgence et la catégorie métier d'une réclamation client assurance, et recommande une action avec délai — via un moteur IA haute performance.

Interface FastAPI + HTML/CSS/JS (design system `agentisys-demos`), pas de framework front.

## Fonctionnement

1. Le texte envoyé à `/api/analyze` est structuré par un prompt qui contraint le moteur IA à répondre en JSON strict (sentiment, intensité, urgence, catégorie, mots-clés, action recommandée).
2. Si aucune clé API n'est configurée, ou si l'appel échoue, l'app se rabat automatiquement sur une analyse par lexique métier (hors-ligne, instantanée) plutôt que de planter.
3. Un aperçu rapide sur 6 réclamations types (rail de droite) utilise ce même lexique de secours, pour un balayage de lot sans multiplier les appels API.

## Lancer en local

```bash
pip install -r requirements.txt
export GROQ_API_KEY="votre_clé"
uvicorn main:app --reload
```
