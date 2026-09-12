const hubNavBtn = document.getElementById('hubNavBtn');
const hubNavMenu = document.getElementById('hubNavMenu');
const hubNavList = document.getElementById('hubNavList');
const sectorSelect = document.getElementById('sectorSelect');
const toolIcon = document.getElementById('toolIcon');
const toolName = document.getElementById('toolName');
const toolTagline = document.getElementById('toolTagline');
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
    const res = await fetch('/api/assurmeet/analyze', {
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

function applySectorData(data) {
  toolIcon.textContent = data.icon;
  toolName.textContent = data.tool_name;
  toolTagline.textContent = data.tagline;
  document.title = `${data.tool_name} — AI Meeting Companion`;
  transcriptText.value = data.example_transcript || '';
  resultBlock.style.display = 'none';
}

sectorSelect.addEventListener('change', async () => {
  const res = await fetch('/api/assurmeet/sector', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sector: sectorSelect.value })
  });
  const data = await res.json();
  if (!data.error) applySectorData(data);
});

async function init() {
  const sectorsRes = await fetch('/api/assurmeet/sectors');
  const sectorsData = await sectorsRes.json();

  sectorSelect.innerHTML = '';
  Object.entries(sectorsData.sectors).forEach(([id, s]) => {
    const opt = document.createElement('option');
    opt.value = id;
    opt.textContent = `${s.icon} ${s.tool_name}`;
    sectorSelect.appendChild(opt);
  });
  sectorSelect.value = sectorsData.default;

  const bootstrapRes = await fetch('/api/assurmeet/bootstrap');
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
