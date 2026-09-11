# 📚 AssurRAG

Répond aux questions sur un document (conditions générales, procédure, document interne...) en citant l'article concerné — sans jamais inventer une réponse hors du texte fourni.

Interface FastAPI + HTML/CSS/JS (design system `agentisys-demos`), pas de framework front.

## Fonctionnement — vrai pipeline RAG

1. **Chunking** — le document collé est découpé en sections (paragraphes séparés par une ligne vide).
2. **Retrieval** — la question est comparée à chaque section par similarité cosinus TF-IDF ; seules les sections dont le score dépasse un seuil absolu et un seuil relatif au meilleur score sont conservées (évite de garder des sections faiblement pertinentes juste parce qu'elles partagent du vocabulaire commun avec les autres, comme "franchise" ou "plafond").
3. **Generation** — seules les sections retenues (pas le document entier) sont injectées dans le prompt envoyé au moteur IA, qui doit répondre uniquement à partir de ces extraits.
4. Les sections effectivement utilisées, avec leur score de similarité, sont affichées dans un panneau "Sections utilisées" pour vérifier ce qui a réellement nourri la réponse.

En production, on remplacerait le TF-IDF (recherche par mots-clés pondérés) par des embeddings sémantiques et une base vectorielle (FAISS/Pinecone), plus robustes aux questions reformulées avec un vocabulaire différent du document.

## Lancer en local

```bash
pip install -r requirements.txt
export GROQ_API_KEY="votre_clé"
uvicorn main:app --reload
```
