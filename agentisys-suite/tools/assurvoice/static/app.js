const hubNavBtn = document.getElementById('hubNavBtn');
const hubNavMenu = document.getElementById('hubNavMenu');
const hubNavList = document.getElementById('hubNavList');
const sectorSelect = document.getElementById('sectorSelect');
const toolIcon = document.getElementById('toolIcon');
const toolName = document.getElementById('toolName');
const toolTagline = document.getElementById('toolTagline');
const assistantNameInline = document.getElementById('assistantNameInline');
const assistantNameReply = document.getElementById('assistantNameReply');
const micBtn = document.getElementById('micBtn');
const micIcon = document.getElementById('micIcon');
const micStatus = document.getElementById('micStatus');
const recordedAudio = document.getElementById('recordedAudio');
const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('fileInput');
const fileChip = document.getElementById('fileChip');
const textInput = document.getElementById('textInput');
const voiceSelect = document.getElementById('voiceSelect');
const processBtn = document.getElementById('processBtn');
const errorBox = document.getElementById('errorBox');
const resultBlock = document.getElementById('resultBlock');
const transcriptionBox = document.getElementById('transcriptionBox');
const transcriptionText = document.getElementById('transcriptionText');
const replyBox = document.getElementById('replyBox');
const replyText = document.getElementById('replyText');
const extractionBlock = document.getElementById('extractionBlock');
const extractionGrid = document.getElementById('extractionGrid');
const audioRow = document.getElementById('audioRow');
const ttsPlayer = document.getElementById('ttsPlayer');
const downloadLink = document.getElementById('downloadLink');

let mediaRecorder = null;
let recordedChunks = [];
let recordedBlob = null;
let uploadedFile = null;
let fieldLabels = {};

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function formatText(text) {
  return escapeHtml(text)
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>');
}

function setStep(id, state) {
  const el = document.getElementById(id);
  el.classList.remove('active', 'done');
  if (state) el.classList.add(state);
}

function resetSteps() {
  setStep('step-stt', null);
  setStep('step-llm', null);
  setStep('step-tts', null);
}

// ===== Micro =====
micBtn.addEventListener('click', async () => {
  if (mediaRecorder && mediaRecorder.state === 'recording') {
    mediaRecorder.stop();
    return;
  }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    recordedChunks = [];
    mediaRecorder = new MediaRecorder(stream);
    mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) recordedChunks.push(e.data); };
    mediaRecorder.onstop = () => {
      recordedBlob = new Blob(recordedChunks, { type: 'audio/webm' });
      recordedAudio.src = URL.createObjectURL(recordedBlob);
      recordedAudio.style.display = 'block';
      micBtn.classList.remove('recording');
      micIcon.textContent = '🎙️';
      micStatus.textContent = 'Enregistrement prêt — vous pouvez réenregistrer si besoin';
      uploadedFile = null;
      fileChip.style.display = 'none';
      stream.getTracks().forEach(t => t.stop());
    };
    mediaRecorder.start();
    micBtn.classList.add('recording');
    micIcon.textContent = '⏹️';
    micStatus.textContent = 'Enregistrement en cours — appuyez pour arrêter';
  } catch (err) {
    errorBox.style.display = 'block';
    errorBox.textContent = "Impossible d'accéder au micro. Vérifiez les autorisations du navigateur.";
  }
});

// ===== Upload fichier =====
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
  uploadedFile = file;
  fileChip.style.display = 'block';
  fileChip.textContent = '📁 ' + file.name;
  recordedBlob = null;
  recordedAudio.style.display = 'none';
}

// ===== Voix =====
function loadVoices(voices) {
  voiceSelect.innerHTML = '';
  Object.entries(voices).forEach(([code, label]) => {
    const opt = document.createElement('option');
    opt.value = code;
    opt.textContent = label;
    voiceSelect.appendChild(opt);
  });
}

// ===== Traitement complet =====
async function process() {
  const hasAudio = recordedBlob || uploadedFile;
  const typedText = textInput.value.trim();

  if (!hasAudio && !typedText) {
    errorBox.style.display = 'block';
    errorBox.textContent = 'Veuillez parler dans le micro, uploader un audio, ou saisir un texte.';
    return;
  }

  processBtn.disabled = true;
  processBtn.textContent = 'Analyse en cours...';
  errorBox.style.display = 'none';
  resultBlock.style.display = 'none';
  transcriptionBox.style.display = 'none';
  replyBox.style.display = 'none';
  extractionBlock.style.display = 'none';
  audioRow.style.display = 'none';
  resetSteps();

  try {
    let userText = typedText;

    if (hasAudio) {
      setStep('step-stt', 'active');
      const formData = new FormData();
      formData.append('file', recordedBlob ? new File([recordedBlob], 'recording.webm', { type: 'audio/webm' }) : uploadedFile);
      const sttRes = await fetch('/api/assurvoice/transcribe', { method: 'POST', body: formData });
      const sttData = await sttRes.json();
      if (sttData.error) throw new Error(sttData.error);
      userText = sttData.text;
      transcriptionBox.style.display = 'block';
      transcriptionText.textContent = userText;
      setStep('step-stt', 'done');
    } else {
      setStep('step-stt', 'done');
    }

    resultBlock.style.display = 'block';

    setStep('step-llm', 'active');
    const replyRes = await fetch('/api/assurvoice/reply', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: userText }),
    });
    const replyData = await replyRes.json();
    if (replyData.error) throw new Error(replyData.error);
    setStep('step-llm', 'done');

    replyBox.style.display = 'block';
    replyText.innerHTML = formatText(replyData.reply || '');

    extractionGrid.innerHTML = '';
    for (const [key, value] of Object.entries(replyData.extraction || {})) {
      const cell = document.createElement('div');
      cell.className = 'result-field';
      cell.innerHTML = `<div class="k">${escapeHtml(fieldLabels[key] || key)}</div><div class="v">${escapeHtml(value != null ? String(value) : '—')}</div>`;
      extractionGrid.appendChild(cell);
    }
    extractionBlock.style.display = 'block';

    setStep('step-tts', 'active');
    const ttsRes = await fetch('/api/assurvoice/tts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: replyData.reply, voice: voiceSelect.value }),
    });
    const blob = await ttsRes.blob();
    const url = URL.createObjectURL(blob);
    ttsPlayer.src = url;
    downloadLink.href = url;
    audioRow.style.display = 'flex';
    setStep('step-tts', 'done');
  } catch (err) {
    errorBox.style.display = 'block';
    errorBox.textContent = err.message || "Le traitement a échoué. Réessayez dans un instant.";
  } finally {
    processBtn.disabled = false;
    processBtn.textContent = "Lancer l'analyse complète";
  }
}

processBtn.addEventListener('click', process);

function applySectorData(data) {
  toolIcon.textContent = data.icon;
  toolName.textContent = data.tool_name;
  toolTagline.textContent = data.tagline;
  assistantNameInline.textContent = data.assistant_name;
  assistantNameReply.textContent = data.assistant_name;
  document.title = `${data.tool_name} — Callbot vocal`;
  fieldLabels = data.field_labels || {};
  textInput.value = '';
  textInput.placeholder = `Ex : ${data.example_message}`;
  loadVoices(data.voices);
  recordedBlob = null;
  uploadedFile = null;
  recordedAudio.style.display = 'none';
  fileChip.style.display = 'none';
  errorBox.style.display = 'none';
  resultBlock.style.display = 'none';
  transcriptionBox.style.display = 'none';
  replyBox.style.display = 'none';
  extractionBlock.style.display = 'none';
  audioRow.style.display = 'none';
  resetSteps();
}

sectorSelect.addEventListener('change', async () => {
  const res = await fetch('/api/assurvoice/sector', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sector: sectorSelect.value })
  });
  const data = await res.json();
  if (!data.error) applySectorData(data);
});

async function init() {
  const sectorsRes = await fetch('/api/assurvoice/sectors');
  const sectorsData = await sectorsRes.json();

  sectorSelect.innerHTML = '';
  Object.entries(sectorsData.sectors).forEach(([id, s]) => {
    const opt = document.createElement('option');
    opt.value = id;
    opt.textContent = `${s.icon} ${s.tool_name}`;
    sectorSelect.appendChild(opt);
  });
  sectorSelect.value = sectorsData.default;

  const bootstrapRes = await fetch('/api/assurvoice/bootstrap');
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
