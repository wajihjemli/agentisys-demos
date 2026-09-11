# 🔎 AssurOCR

Extrait le texte d'un constat scanné ou photographié via OCR (Tesseract), puis le structure en champs exploitables (date, lieu, identité de l'assuré, nature du sinistre, immatriculation, montant, témoins, blessures) grâce à un moteur IA haute performance.

Complémentaire d'AssurVision (qui analyse la gravité d'un dégât à partir d'une photo) : AssurOCR se concentre sur l'extraction de **texte** depuis un document, pas sur l'analyse visuelle des dommages.

Interface FastAPI + HTML/CSS/JS (design system `agentisys-demos`), pas de framework front — contrôle total du rendu.

## Fonctionnement

1. **Lecture (OCR)** — le document (JPG/PNG) déposé dans l'interface est envoyé à `/api/ocr`, qui le passe à Tesseract (français) pour en extraire le texte brut. Le texte est affiché dans une zone éditable pour correction avant traitement.
2. **Structuration** — ce texte est envoyé à `/api/structure`, qui contraint le moteur IA à répondre en JSON strict avec les champs métier attendus.
3. **Vérification** — si aucune clé API n'est configurée, ou si l'appel échoue, ou si un champ manque, l'app se rabat automatiquement sur des règles métier (regex), hors-ligne.

## Lancer en local

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

**Prérequis système** : Tesseract OCR doit être installé sur la machine.
- Linux (Debian/Ubuntu) : `sudo apt install tesseract-ocr tesseract-ocr-fra`
- Le fichier `packages.txt` fourni installe automatiquement ces paquets sur les plateformes qui le supportent.

Configurer la clé API via la variable d'environnement `GROQ_API_KEY` :

```bash
export GROQ_API_KEY="votre_clé"
uvicorn main:app --reload
```
