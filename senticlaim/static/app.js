const exampleSelect = document.getElementById('exampleSelect');
const claimText = document.getElementById('claimText');
const analyzeBtn = document.getElementById('analyzeBtn');
const resultBlock = document.getElementById('resultBlock');
const metricRow = document.getElementById('metricRow');
const quoteBox = document.getElementById('quoteBox');
const tagRow = document.getElementById('tagRow');
const actionCallout = document.getElementById('actionCallout');
const modeFlag = document.getElementById('modeFlag');
const quickScan = document.getElementById('quickScan');

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function sentimentClass(sentiment) {
  return 'sentiment-' + sentiment.toLowerCase().replace('é', 'e');
}

function renderResult(result, sourceText) {
  resultBlock.style.display = 'block';

  metricRow.innerHTML = '';
  const tiles = [
    { val: result.sentiment, lbl: 'Sentiment', cls: sentimentClass(result.sentiment) },
    { val: result.intensity + '%', lbl: 'Intensité', cls: '' },
    { val: result.urgence ? 'OUI' : 'Non', lbl: 'Urgence', cls: '' },
    { val: result.categorie.replace('_', ' '), lbl: 'Catégorie', cls: '' },
  ];
  tiles.forEach(t => {
    const tile = document.createElement('div');
    tile.className = 'metric-tile' + (t.cls ? ' ' + t.cls : '');
    tile.innerHTML = `<div class="val">${t.val}</div><div class="lbl">${t.lbl}</div>`;
    metricRow.appendChild(tile);
  });

  quoteBox.textContent = `"${sourceText}"`;

  tagRow.innerHTML = '';
  (result.mots_cles || []).forEach(mc => {
    const tag = document.createElement('span');
    tag.className = 'tag';
    tag.textContent = mc;
    tagRow.appendChild(tag);
  });

  actionCallout.innerHTML = `<b>Action recommandée —</b> ${escapeHtml(result.action || '')}`;

  if (result.mode === 'lexicon') {
    modeFlag.style.display = 'block';
    modeFlag.textContent = 'Analyse par lexique métier (moteur IA indisponible ou clé API absente).';
  } else {
    modeFlag.style.display = 'none';
  }
}

async function analyze() {
  const text = claimText.value.trim();
  if (!text) return;
  analyzeBtn.disabled = true;
  analyzeBtn.textContent = 'Analyse en cours...';

  try {
    const res = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    });
    const data = await res.json();
    renderResult(data, text);
  } catch (err) {
    alert("L'analyse a échoué. Réessayez dans un instant.");
  } finally {
    analyzeBtn.disabled = false;
    analyzeBtn.textContent = 'Analyser le sentiment';
  }
}

analyzeBtn.addEventListener('click', analyze);

exampleSelect.addEventListener('change', () => {
  if (exampleSelect.value) claimText.value = exampleSelect.value;
});

async function init() {
  const res = await fetch('/api/bootstrap');
  const data = await res.json();

  data.examples.forEach(ex => {
    const opt = document.createElement('option');
    opt.value = ex;
    opt.textContent = ex.length > 70 ? ex.slice(0, 70) + '…' : ex;
    exampleSelect.appendChild(opt);
  });

  quickScan.innerHTML = '';
  data.quick_scan.forEach(item => {
    const row = document.createElement('div');
    row.className = 'quick-scan-item';
    const short = item.text.length > 46 ? item.text.slice(0, 46) + '…' : item.text;
    row.innerHTML = `<span class="qs-text">${short}</span><span class="qs-badge ${sentimentClass(item.sentiment)}">${item.sentiment}</span>`;
    quickScan.appendChild(row);
  });
}

init();
