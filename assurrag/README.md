# 📚 AssurRAG

Répond aux questions sur un document (conditions générales, procédure, document interne...) en citant l'article concerné — sans jamais inventer une réponse hors du texte fourni.

Interface FastAPI + HTML/CSS/JS (design system `agentisys-demos`), pas de framework front.

## Fonctionnement

Le document et la question envoyés à `/api/ask` sont injectés dans un prompt qui contraint le moteur IA à répondre uniquement à partir du texte fourni, et à l'admettre explicitement si l'information n'y figure pas.

En production, le document serait découpé en chunks et indexé dans une base vectorielle (FAISS/Pinecone) pour ne récupérer que les passages pertinents ; cette démo envoie le document entier tel quel.

## Lancer en local

```bash
pip install -r requirements.txt
export GROQ_API_KEY="votre_clé"
uvicorn main:app --reload
```
