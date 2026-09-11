# agentisys-demos

Portfolio de démonstrateurs IA pour la relation client assurance — Wajih Jemli, consultant en transition vers l'IA appliquée (20 ans d'expérience en centres de contact).

8 outils, chacun déployable indépendamment ou via le hub unique **[`agentisys-suite/`](agentisys-suite)** (une seule application, un seul outil présenté à la fois) :

| Outil | Description |
|---|---|
| [`assurbot/`](assurbot) | Répond aux questions d'assurance à partir d'une FAQ interne (RAG) |
| [`senticlaim/`](senticlaim) | Détecte le sentiment, l'urgence et la catégorie métier d'une réclamation |
| [`assurocr/`](assurocr) | Extrait le texte d'un constat scanné (Tesseract) puis le structure |
| [`assurmeet/`](assurmeet) | Résume un appel client et en extrait les actions à suivre |
| [`assurrag/`](assurrag) | Répond aux questions sur un document en citant l'article exact (RAG) |
| [`assurtranslate/`](assurtranslate) | Traduit les échanges avec un assuré non francophone |
| [`assurvision/`](assurvision) | Estime la gravité d'un sinistre à partir d'une photo |
| [`assurvoice/`](assurvoice) | Callbot vocal : déclaration de sinistre à la voix |

Chaque outil est un démonstrateur FastAPI + HTML/CSS/JS indépendant, construit sur le même design system, utilisant Groq comme unique fournisseur IA. Preuves de concept liées à AgentiSys.
