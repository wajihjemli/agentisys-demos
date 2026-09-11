const sourceText = document.getElementById('sourceText');
const sourceLang = document.getElementById('sourceLang');
const targetLang = document.getElementById('targetLang');
const translateBtn = document.getElementById('translateBtn');
const resultBlock = document.getElementById('resultBlock');
const originalText = document.getElementById('originalText');
const translatedText = document.getElementById('translatedText');
const targetBox = document.getElementById('targetBox');
const audioRow = document.getElementById('audioRow');
const audioPlayer = document.getElementById('audioPlayer');
const downloadLink = document.getElementById('downloadLink');
const errorBox = document.getElementById('errorBox');

let languages = {};

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

async function translate() {
  const text = sourceText.value.trim();
  if (!text) return;

  translateBtn.disabled = true;
  translateBtn.textContent = 'Traduction en cours...';
  errorBox.style.display = 'none';
  resultBlock.style.display = 'none';
  audioRow.style.display = 'none';

  try {
    const res = await fetch('/api/assurtranslate/translate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, source: sourceLang.value, target: targetLang.value })
    });
    const data = await res.json();
    if (data.error) {
      errorBox.style.display = 'block';
      errorBox.textContent = data.error;
      return;
    }

    resultBlock.style.display = 'block';
    originalText.textContent = text;
    translatedText.textContent = data.translated;
    targetBox.setAttribute('dir', targetLang.value === 'ar' ? 'rtl' : 'ltr');

    translateBtn.textContent = 'Génération audio...';
    const ttsRes = await fetch('/api/assurtranslate/tts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: data.translated, lang: targetLang.value })
    });
    const blob = await ttsRes.blob();
    const url = URL.createObjectURL(blob);
    audioPlayer.src = url;
    downloadLink.href = url;
    downloadLink.download = `traduction_${targetLang.value}.mp3`;
    audioRow.style.display = 'flex';
  } catch (err) {
    errorBox.style.display = 'block';
    errorBox.textContent = "La traduction a échoué. Réessayez dans un instant.";
  } finally {
    translateBtn.disabled = false;
    translateBtn.textContent = 'Traduire';
  }
}

translateBtn.addEventListener('click', translate);

async function init() {
  const res = await fetch('/api/assurtranslate/bootstrap');
  const data = await res.json();
  languages = data.languages;

  sourceLang.innerHTML = '';
  Object.keys(languages).forEach(code => {
    const opt = document.createElement('option');
    opt.value = code;
    opt.textContent = languages[code].label;
    sourceLang.appendChild(opt);
  });
  sourceLang.value = 'fr';

  targetLang.innerHTML = '';
  data.target_languages.forEach(code => {
    const opt = document.createElement('option');
    opt.value = code;
    opt.textContent = languages[code].label;
    targetLang.appendChild(opt);
  });
  targetLang.value = 'en';

  sourceText.value = data.example_text || '';
}

init();
