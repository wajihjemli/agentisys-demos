# 📸 AssurVision

Estime la gravité d'un sinistre à partir d'une simple photo envoyée par l'assuré — accélère le premier diagnostic avant expertise.

Interface FastAPI + HTML/CSS/JS (design system `agentisys-demos`), pas de framework front.

## Fonctionnement

1. La photo est envoyée à `/api/analyze` et encodée en base64 pour l'API vision.
2. Un moteur IA vision analyse l'image et répond selon une structure fixe en 8 points : type de sinistre, dommages détectés, gravité estimée, état de circulation du véhicule, besoin d'expertise, délai et coût de réparation estimés, recommandations.
3. Le raisonnement interne éventuel du modèle est filtré pour ne garder que la réponse structurée.
4. Si le modèle répond en anglais (cas rare), la réponse est automatiquement retraduite en français par un second appel au moteur IA.
5. La gravité est extraite du texte pour être mise en avant sous forme de badge coloré.

## Lancer en local

```bash
pip install -r requirements.txt
export GROQ_API_KEY="votre_clé"
uvicorn main:app --reload
```
