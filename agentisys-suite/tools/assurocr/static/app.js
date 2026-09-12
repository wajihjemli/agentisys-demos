const hubNavBtn = document.getElementById('hubNavBtn');
const hubNavMenu = document.getElementById('hubNavMenu');
const hubNavList = document.getElementById('hubNavList');
const sectorSelect = document.getElementById('sectorSelect');
const toolIcon = document.getElementById('toolIcon');
const toolName = document.getElementById('toolName');
const toolTagline = document.getElementById('toolTagline');
const extractsSummary = document.getElementById('extractsSummary');
const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('fileInput');
const previewStrip = document.getElementById('previewStrip');
const ocrText = document.getElementById('ocrText');
const extractBtn = document.getElementById('extractBtn');
const resultBlock = document.getElementById('resultBlock');
const resultGrid = document.getElementById('resultGrid');

let currentFile = null;
let fieldLabels = {};

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

dropzone.addEventListener('click', () => fileInput.click());
dropzone.addEventListener('dragover', (e) => { e.preventDefault(); dropzone.classList.add('drag'); });
dropzone.addEventListener('dragleave', () => dropzone.classList.remove('drag'));
dropzone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropzone.classList.remove('drag');
  if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
});
fileInput.addEventListener('change', (e) => { if (e.target.files.length) handleFile(e.target.files[0]); });

function handleFile(file) {
  currentFile = file;
  previewStrip.innerHTML = '';
  const img = document.createElement('img');
  img.src = URL.createObjectURL(file);
  previewStrip.appendChild(img);
  runOcr(file);
}

function setStep(id, state) {
  const el = document.getElementById(id);
  el.classList.remove('active', 'done');
  if (state) el.classList.add(state);
}

async function runOcr(file) {
  setStep('step-ocr', 'active');
  setStep('step-ai', null);
  setStep('step-check', null);
  ocrText.value = 'Lecture en cours…';
  extractBtn.disabled = true;

  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await fetch('/api/assurocr/ocr', { method: 'POST', body: formData });
    const data = await res.json();
    ocrText.value = data.text || '';
    setStep('step-ocr', 'done');
    extractBtn.disabled = false;
  } catch (err) {
    ocrText.value = '';
    setStep('step-ocr', null);
    alert("La lecture du document a échoué. Vérifiez le format du fichier et réessayez.");
  }
}

extractBtn.addEventListener('click', async () => {
  if (!ocrText.value.trim()) return;
  setStep('step-ai', 'active');
  extractBtn.disabled = true;
  resultBlock.style.display = 'none';

  try {
    const res = await fetch('/api/assurocr/structure', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: ocrText.value })
    });
    const data = await res.json();
    setStep('step-ai', 'done');
    setStep('step-check', data.fallback_used ? 'active' : 'done');

    resultGrid.innerHTML = '';
    for (const [key, value] of Object.entries(data.fields || {})) {
      const cell = document.createElement('div');
      cell.className = 'result-field';
      cell.innerHTML = `<div class="k">${escapeHtml(fieldLabels[key] || key)}</div><div class="v">${escapeHtml(value || '—')}</div>`;
      resultGrid.appendChild(cell);
    }
    resultBlock.style.display = 'block';
  } catch (err) {
    alert("L'extraction a échoué. Réessayez dans un instant.");
    setStep('step-ai', null);
  } finally {
    extractBtn.disabled = false;
  }
});

function applySectorData(data) {
  toolIcon.textContent = data.icon;
  toolName.textContent = data.tool_name;
  toolTagline.textContent = data.tagline;
  extractsSummary.textContent = data.extracts_summary;
  document.title = `${data.tool_name} — Extraction intelligente de documents`;
  fieldLabels = data.field_labels || {};
  currentFile = null;
  previewStrip.innerHTML = '';
  ocrText.value = '';
  extractBtn.disabled = true;
  resultBlock.style.display = 'none';
  setStep('step-ocr', null);
  setStep('step-ai', null);
  setStep('step-check', null);
}

sectorSelect.addEventListener('change', async () => {
  const res = await fetch('/api/assurocr/sector', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sector: sectorSelect.value })
  });
  const data = await res.json();
  if (!data.error) applySectorData(data);
});

async function init() {
  const sectorsRes = await fetch('/api/assurocr/sectors');
  const sectorsData = await sectorsRes.json();

  sectorSelect.innerHTML = '';
  Object.entries(sectorsData.sectors).forEach(([id, s]) => {
    const opt = document.createElement('option');
    opt.value = id;
    opt.textContent = `${s.icon} ${s.tool_name}`;
    sectorSelect.appendChild(opt);
  });
  sectorSelect.value = sectorsData.default;

  const bootstrapRes = await fetch('/api/assurocr/bootstrap');
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
