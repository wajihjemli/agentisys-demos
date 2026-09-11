const transcriptText = document.getElementById('transcriptText');
const analyzeBtn = document.getElementById('analyzeBtn');
const resultBlock = document.getElementById('resultBlock');
const errorBox = document.getElementById('errorBox');
const summaryBox = document.getElementById('summaryBox');
const pointsCles = document.getElementById('pointsCles');
const actionsBody = document.getElementById('actionsBody');
const sentimentRow = document.getElementById('sentimentRow');
const risquesList = document.getElementById('risquesList');
const promessesList = document.getElementById('promessesList');

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function renderText(str) {
  return escapeHtml(str || '').replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
}

function priorityClass(p) {
  return 'priority-pill ' + (p || '').toLowerCase();
}

function riskLevelClass(niveau) {
  const n = (niveau || '').toLowerCase();
  if (n === 'élevé' || n === 'eleve') return 'risque-eleve';
  if (n === 'modéré' || n === 'modere') return 'risque-modere';
  return 'risque-faible';
}

function fillList(el, items) {
  el.innerHTML = '';
  (items || []).forEach(item => {
    const li = document.createElement('li');
    li.innerHTML = renderText(item);
    el.appendChild(li);
  });
  if (!items || !items.length) {
    const li = document.createElement('li');
    li.textContent = 'Aucun élément identifié.';
    el.appendChild(li);
  }
}

function renderResult(result) {
  errorBox.style.display = 'none';
  resultBlock.style.display = 'block';

  summaryBox.innerHTML = renderText(result.resume);

  fillList(pointsCles, result.points_cles);
  fillList(risquesList, result.risques);
  fillList(promessesList, result.promesses);

  actionsBody.innerHTML = '';
  (result.actions || []).forEach(a => {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${renderText(a.action)}</td><td>${escapeHtml(a.responsable || '')}</td><td>${escapeHtml(a.delai || '')}</td>
      <td><span class="${priorityClass(a.priorite)}">${escapeHtml(a.priorite || '')}</span></td>`;
    actionsBody.appendChild(tr);
  });
  if (!result.actions || !result.actions.length) {
    actionsBody.innerHTML = '<tr><td colspan="4" style="color:var(--muted);">Aucune action identifiée.</td></tr>';
  }

  const s = result.sentiment_client || {};
  sentimentRow.innerHTML = '';
  const tiles = [
    { val: s.emotion || '—', lbl: 'Émotion dominante', cls: '' },
    { val: (s.satisfaction != null ? s.satisfaction + '/10' : '—'), lbl: 'Satisfaction', cls: '' },
    { val: s.risque_depart || '—', lbl: 'Risque de départ', cls: riskLevelClass(s.risque_depart) },
  ];
  tiles.forEach(t => {
    const tile = document.createElement('div');
    tile.className = 'metric-tile' + (t.cls ? ' ' + t.cls : '');
    tile.innerHTML = `<div class="val">${t.val}</div><div class="lbl">${t.lbl}</div>`;
    sentimentRow.appendChild(tile);
  });
}

async function analyze() {
  const transcript = transcriptText.value.trim();
  if (!transcript) return;
  analyzeBtn.disabled = true;
  analyzeBtn.textContent = 'Analyse en cours...';
  errorBox.style.display = 'none';

  try {
    const res = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ transcript })
    });
    const data = await res.json();
    if (data.error) {
      resultBlock.style.display = 'none';
      errorBox.style.display = 'block';
      errorBox.textContent = data.error;
    } else {
      renderResult(data.result);
    }
  } catch (err) {
    resultBlock.style.display = 'none';
    errorBox.style.display = 'block';
    errorBox.textContent = "L'analyse a échoué. Réessayez dans un instant.";
  } finally {
    analyzeBtn.disabled = false;
    analyzeBtn.textContent = "Analyser l'appel";
  }
}

analyzeBtn.addEventListener('click', analyze);

async function init() {
  const res = await fetch('/api/bootstrap');
  const data = await res.json();
  transcriptText.value = data.example_transcript || '';
}

init();
