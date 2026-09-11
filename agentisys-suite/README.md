# AgentiSys Suite

Point d'entrée unique regroupant les 8 démonstrateurs IA du portfolio (AssurBot, SentiClaim, AssurOCR, AssurMeet, AssurRAG, AssurTranslate, AssurVision, AssurVoice), pour n'avoir qu'une seule application à partager plutôt que 8 apps séparées.

Chaque outil reste un module indépendant (`tools/<outil>/router.py`) : il pourrait être re-séparé en service distinct plus tard sans réécrire sa logique métier, qui est identique à sa version autonome dans les autres dossiers de ce repo.

## Structure

```
/                     -> hub (choix de l'outil)
/<outil>              -> page de l'outil, ex: /assurbot
/api/<outil>/...      -> API de l'outil, ex: /api/assurbot/chat
```

## Lancer en local

```bash
pip install -r requirements.txt
cp .env.example .env   # puis renseigner GROQ_API_KEY
uvicorn main:app --reload
```

**AssurOCR** nécessite en plus le binaire Tesseract installé sur le système (`apt install tesseract-ocr tesseract-ocr-fra` sous Debian/Ubuntu) — c'est une dépendance système, pas une bibliothèque Python.

**AssurVoice** (enregistrement au micro) nécessite `localhost` ou HTTPS, contrainte des navigateurs sur l'accès au micro.

Une seule clé Groq, partagée par les 8 outils.
