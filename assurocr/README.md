# 🔎 AssurOCR

Extrait le texte d'un constat scanné ou photographié via OCR (Tesseract), puis le structure en champs exploitables (date, assuré, nature du sinistre, lieu, immatriculation, montant, témoins, blessures, plainte...) grâce à un moteur IA haute performance.

Complémentaire d'AssurVision (qui analyse la gravité d'un dégât à partir d'une photo) : AssurOCR se concentre sur l'extraction de **texte** depuis un document, pas sur l'analyse visuelle des dommages.

## Fonctionnement

1. **OCR** — le document (JPG/PNG) est passé à Tesseract (français) pour en extraire le texte brut. Le texte est affiché dans une zone éditable pour correction avant traitement.
2. **Structuration** — ce texte est envoyé à un prompt qui contraint le modèle à répondre en JSON strict avec les champs métier attendus.
3. Si aucune clé API n'est configurée, ou si l'appel échoue, l'app se rabat automatiquement sur une extraction par règles (regex métier), hors-ligne.
4. Il est aussi possible de coller directement du texte (sans passer par l'OCR), utile en démo sans document scanné sous la main.

## Lancer en local

```bash
pip install -r requirements.txt
streamlit run app.py
```

**Prérequis système** : Tesseract OCR doit être installé sur la machine.
- Linux (Debian/Ubuntu) : `sudo apt install tesseract-ocr tesseract-ocr-fra`
- Sur Streamlit Community Cloud : le fichier `packages.txt` fourni installe automatiquement ces paquets.

Configurer la clé API dans `.streamlit/secrets.toml` :

```toml
GROQ_API_KEY = "votre_clé"
```

(ou via la variable d'environnement `GROQ_API_KEY`, ou en la saisissant directement dans l'interface).
