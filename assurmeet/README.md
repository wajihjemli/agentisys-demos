# 📝 AssurMeet

Résume un appel client et en extrait les actions à suivre, le sentiment et les risques — sans écoute manuelle a posteriori, via un moteur IA haute performance.

Interface FastAPI + HTML/CSS/JS (design system `agentisys-demos`), pas de framework front.

## Fonctionnement

Le transcript envoyé à `/api/analyze` est structuré par un prompt qui contraint le moteur IA à répondre en JSON strict : résumé, points clés, actions à suivre (avec responsable, délai, priorité), sentiment client (émotion, satisfaction /10, risque de départ), risques identifiés et promesses faites par le conseiller.

## Lancer en local

```bash
pip install -r requirements.txt
export GROQ_API_KEY="votre_clé"
uvicorn main:app --reload
```
