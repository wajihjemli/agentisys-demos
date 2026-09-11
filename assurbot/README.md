# 🤖 AssurBot

Assistant conversationnel multi-secteur en RAG (Retrieval-Augmented Generation) : recherche par similarité dans une FAQ, puis reformulation de la réponse par un moteur IA haute performance — sans halluciner hors de la base de connaissances fournie.

Le code ne change jamais d'un secteur à l'autre : seule la configuration (`sectorbot/sectors.config.json`) et la base de connaissances (`sectorbot/knowledge/*.txt`) changent. Passer d'AssurBot (assurance) à TechBot (télécom) ou OrthoBot (dispositifs médicaux) se fait en direct depuis l'interface, sans redéploiement — une preuve de configurabilité plutôt qu'une affirmation.

Interface FastAPI + HTML/CSS/JS (design system `agentisys-demos`), pas de framework front.

## Fonctionnement

1. **Sélection du secteur** — le sélecteur en haut de la page appelle `/api/sector`, qui change le secteur actif côté serveur ; le nom de l'outil, l'icône, le message d'accueil et les exemples de questions se mettent à jour immédiatement dans l'interface.
2. **Retrieval** — la question envoyée à `/api/chat` est comparée aux entrées de la base de connaissances du secteur actif par similarité cosinus TF-IDF, et les extraits les plus proches sont récupérés.
3. **Generation** — ces extraits sont injectés, avec le prompt système propre au secteur, dans un appel qui contraint le moteur IA à répondre uniquement à partir du contexte fourni, sinon à l'admettre.
4. Si aucun extrait pertinent n'est trouvé, ou si aucune clé API n'est configurée, ou si l'appel échoue, l'app se rabat sur une réponse directe (extrait brut de FAQ) plutôt que d'inventer une réponse.

Les 7 secteurs disponibles sont définis dans [`../sectorbot/sectors.config.json`](../sectorbot/sectors.config.json) — nécessite que ce dossier soit présent en frère d'`assurbot/` (clone complet du repo).

## Lancer en local

```bash
pip install -r requirements.txt
export GROQ_API_KEY="votre_clé"
uvicorn main:app --reload
```
