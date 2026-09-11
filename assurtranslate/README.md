# 🌍 AssurTranslate

Traduit les échanges avec un assuré non francophone, en gardant le vocabulaire technique de l'assurance, avec lecture audio de la traduction.

Interface FastAPI + HTML/CSS/JS (design system `agentisys-demos`), pas de framework front.

## Fonctionnement

1. Le texte, la langue source et la langue cible envoyés à `/api/translate` sont injectés dans un prompt qui contraint le moteur IA à traduire en conservant le ton professionnel et les termes techniques du secteur.
2. La traduction obtenue est envoyée à `/api/tts`, qui génère l'audio correspondant (gTTS) et le renvoie directement en mémoire (pas de fichier temporaire sur le serveur).
3. L'audio est lisible dans le navigateur et téléchargeable.

## Lancer en local

```bash
pip install -r requirements.txt
export GROQ_API_KEY="votre_clé"
uvicorn main:app --reload
```
