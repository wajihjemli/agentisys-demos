const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('fileInput');
const photoPreview = document.getElementById('photoPreview');
const previewImg = document.getElementById('previewImg');
const analyzeBtn = document.getElementById('analyzeBtn');
const translateInfo = document.getElementById('translateInfo');
const resultBlock = document.getElementById('resultBlock');
const severityBadge = document.getElementById('severityBadge');
const severityValue = document.getElementById('severityValue');
const analysisText = document.getElementById('analysisText');
const errorBox = document.getElementById('errorBox');

let currentFile = null;

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function formatAnalysis(text) {
  return escapeHtml(text)
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>');
}

function severityClass(severity) {
  return 'severity-' + severity.toLowerCase()
    .replace('é', 'e').replace('è', 'e');
}

function setStep(id, state) {
  const el = document.getElementById(id);
  el.classList.remove('active', 'done');
  if (state) el.classList.add(state);
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
  previewImg.src = URL.createObjectURL(file);
  photoPreview.style.display = 'block';
  analyzeBtn.disabled = false;
  resultBlock.style.display = 'none';
  translateInfo.style.display = 'none';
  errorBox.style.display = 'none';
  setStep('step-upload', 'done');
  setStep('step-vision', null);
  setStep('step-check', null);
}

async function analyze() {
  if (!currentFile) return;
  analyzeBtn.disabled = true;
  analyzeBtn.textContent = 'Analyse en cours...';
  resultBlock.style.display = 'none';
  translateInfo.style.display = 'none';
  errorBox.style.display = 'none';
  setStep('step-vision', 'active');

  const formData = new FormData();
  formData.append('file', currentFile);

  try {
    const res = await fetch('/api/assurvision/analyze', { method: 'POST', body: formData });
    const data = await res.json();

    if (data.error) {
      errorBox.style.display = 'block';
      errorBox.textContent = data.error;
      setStep('step-vision', null);
      return;
    }

    setStep('step-vision', 'done');
    setStep('step-check', data.translated ? 'active' : 'done');

    if (data.translated) {
      translateInfo.style.display = 'block';
    }

    if (data.severity) {
      severityBadge.style.display = 'flex';
      severityBadge.className = 'severity-badge ' + severityClass(data.severity);
      severityValue.textContent = data.severity;
    } else {
      severityBadge.style.display = 'none';
    }

    analysisText.innerHTML = formatAnalysis(data.analysis || '');
    resultBlock.style.display = 'block';
  } catch (err) {
    errorBox.style.display = 'block';
    errorBox.textContent = "L'analyse a échoué. Réessayez dans un instant.";
    setStep('step-vision', null);
  } finally {
    analyzeBtn.disabled = false;
    analyzeBtn.textContent = 'Analyser la photo';
  }
}

analyzeBtn.addEventListener('click', analyze);
