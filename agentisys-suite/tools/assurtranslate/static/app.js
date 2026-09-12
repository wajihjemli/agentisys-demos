const hubNavBtn = document.getElementById('hubNavBtn');
const hubNavMenu = document.getElementById('hubNavMenu');
const hubNavList = document.getElementById('hubNavList');
const sectorSelect = document.getElementById('sectorSelect');
const toolIcon = document.getElementById('toolIcon');
const toolName = document.getElementById('toolName');
const toolTagline = document.getElementById('toolTagline');
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

function applySectorData(data) {
  toolIcon.textContent = data.icon;
  toolName.textContent = data.tool_name;
  toolTagline.textContent = data.tagline;
  document.title = `${data.tool_name} — Traducteur Intelligent`;
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
  resultBlock.style.display = 'none';
  audioRow.style.display = 'none';
  errorBox.style.display = 'none';
}

sectorSelect.addEventListener('change', async () => {
  const res = await fetch('/api/assurtranslate/sector', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sector: sectorSelect.value })
  });
  const data = await res.json();
  if (!data.error) applySectorData(data);
});

async function init() {
  const sectorsRes = await fetch('/api/assurtranslate/sectors');
  const sectorsData = await sectorsRes.json();

  sectorSelect.innerHTML = '';
  Object.entries(sectorsData.sectors).forEach(([id, s]) => {
    const opt = document.createElement('option');
    opt.value = id;
    opt.textContent = `${s.icon} ${s.tool_name}`;
    sectorSelect.appendChild(opt);
  });
  sectorSelect.value = sectorsData.default;

  const bootstrapRes = await fetch('/api/assurtranslate/bootstrap');
  const bootstrapData = await bootstrapRes.json();
  applySectorData(bootstrapData);
}

init();

hubNavBtn.addEventListener('click', (e) => {
  e.stopPropagation();
  hubNavMenu.classList.toggle('open');
});
document.addEventListener('click', (e) => {
  if (!hubNavMenu.contains(e.target) && e.target !== hubNavBtn) {
    hubNavMenu.classList.remove('open');
  }
});

async function loadHubNav() {
  try {
    const res = await fetch('/api/hub/tools');
    const data = await res.json();
    const currentSlug = window.location.pathname.slice(1);
    hubNavList.innerHTML = '';
    data.tools.forEach(t => {
      const a = document.createElement('a');
      a.className = 'hub-nav-item' + (t.slug === currentSlug ? ' active' : '');
      a.href = `/${t.slug}`;
      a.innerHTML = `<span>${t.icon}</span><span>${t.name}</span>`;
      hubNavList.appendChild(a);
    });
  } catch (err) {
    // Silencieux : le menu reste utilisable via le lien Accueil même si la liste ne charge pas.
  }
}

loadHubNav();
