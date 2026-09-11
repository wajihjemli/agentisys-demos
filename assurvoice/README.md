# 🎤️ AssurVoice

Callbot vocal qui recueille une déclaration de sinistre à la voix et y répond en temps réel — comme un premier contact téléphonique automatisé.

Interface FastAPI + HTML/CSS/JS (design system `agentisys-demos`), pas de framework front.

## Fonctionnement

1. L'utilisateur parle au micro (enregistrement dans le navigateur), uploade un fichier audio, ou saisit directement du texte.
2. Si l'entrée est audio, elle est envoyée à `/api/transcribe` pour être transcrite par un moteur de reconnaissance vocale.
3. Le texte (transcrit ou saisi) est envoyé à `/api/reply` : Eva, l'assistante virtuelle, génère une réponse professionnelle et empathique, et les informations clés du sinistre sont extraites au format structuré (nature, date, lieu, dégâts, blessures, urgence).
4. La réponse d'Eva est envoyée à `/api/tts` pour être synthétisée en voix (Edge TTS, voix françaises neurales), lisible et téléchargeable directement dans le navigateur.

## Lancer en local

```bash
pip install -r requirements.txt
export GROQ_API_KEY="votre_clé"
uvicorn main:app --reload
```

L'enregistrement au micro nécessite `localhost` ou HTTPS (contrainte des navigateurs sur l'accès au micro).
