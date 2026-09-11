# 🤖 AssurBot

Assistant virtuel assurance en RAG (Retrieval-Augmented Generation) : recherche par similarité dans une FAQ assurance, puis reformulation de la réponse par un moteur IA haute performance — sans halluciner hors de la base de connaissances fournie.

## Fonctionnement

1. **Retrieval** — la question de l'utilisateur est comparée aux entrées de la FAQ (`faq_assurance.txt`) par similarité cosinus TF-IDF, et les extraits les plus proches sont récupérés.
2. **Generation** — ces extraits sont injectés dans un prompt qui contraint le modèle à répondre uniquement à partir du contexte fourni, sinon à l'admettre.
3. Si aucun extrait pertinent n'est trouvé, ou si aucune clé API n'est configurée, l'app se rabat sur une réponse directe (contact conseiller, ou extrait brut de FAQ) plutôt que d'inventer une réponse.

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
