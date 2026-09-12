# agentisys-demos

Portfolio de démonstrateurs IA pour la relation client assurance — Wajih Jemli, consultant en transition vers l'IA appliquée (20 ans d'expérience en centres de contact).

**[`agentisys-suite/`](agentisys-suite)** est le point d'entrée unique du portfolio : une seule application FastAPI qui regroupe les 8 outils, avec sélection du secteur d'activité et navigation directe entre les outils.

| Outil | Description |
|---|---|
| [`assurbot`](agentisys-suite/tools/assurbot) | Répond aux questions d'assurance à partir d'une FAQ interne (RAG) |
| [`senticlaim`](agentisys-suite/tools/senticlaim) | Détecte le sentiment, l'urgence et la catégorie métier d'une réclamation |
| [`assurocr`](agentisys-suite/tools/assurocr) | Extrait le texte d'un constat scanné (Tesseract) puis le structure |
| [`assurmeet`](agentisys-suite/tools/assurmeet) | Résume un appel client et en extrait les actions à suivre |
| [`assurrag`](agentisys-suite/tools/assurrag) | Répond aux questions sur un document en citant l'article exact (RAG) |
| [`assurtranslate`](agentisys-suite/tools/assurtranslate) | Traduit les échanges avec un assuré non francophone |
| [`assurvision`](agentisys-suite/tools/assurvision) | Estime la gravité d'un sinistre à partir d'une photo |
| [`assurvoice`](agentisys-suite/tools/assurvoice) | Callbot vocal : déclaration de sinistre à la voix |

`sectorbot/` contient la configuration multi-secteur (prompts, libellés, base de connaissances) partagée par les 8 outils du hub — c'est une dépendance requise, pas un dossier annexe.

Chaque outil est construit sur le même design system, utilisant Groq comme unique fournisseur IA. Voir [`agentisys-suite/README.md`](agentisys-suite/README.md) pour le lancer en local. Preuves de concept liées à AgentiSys.
