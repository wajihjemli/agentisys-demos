const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('fileInput');
const previewStrip = document.getElementById('previewStrip');
const ocrText = document.getElementById('ocrText');
const extractBtn = document.getElementById('extractBtn');
const resultBlock = document.getElementById('resultBlock');
const resultGrid = document.getElementById('resultGrid');

let currentFile = null;

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
      cell.innerHTML = `<div class="k">${escapeHtml(key)}</div><div class="v">${escapeHtml(value || '—')}</div>`;
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
