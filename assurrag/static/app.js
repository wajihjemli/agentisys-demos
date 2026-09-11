const documentText = document.getElementById('documentText');
const questionInput = document.getElementById('questionInput');
const askBtn = document.getElementById('askBtn');
const answerBox = document.getElementById('answerBox');
const errorBox = document.getElementById('errorBox');

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function renderAnswer(text) {
  return escapeHtml(text).replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br>');
}

async function ask() {
  const doc = documentText.value.trim();
  const question = questionInput.value.trim();
  if (!doc || !question) return;

  askBtn.disabled = true;
  askBtn.textContent = 'Recherche en cours...';
  errorBox.style.display = 'none';
  answerBox.style.display = 'none';

  try {
    const res = await fetch('/api/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ document: doc, question })
    });
    const data = await res.json();
    if (data.error) {
      errorBox.style.display = 'block';
      errorBox.textContent = data.error;
    } else {
      answerBox.style.display = 'block';
      answerBox.innerHTML = renderAnswer(data.answer);
    }
  } catch (err) {
    errorBox.style.display = 'block';
    errorBox.textContent = "La réponse a échoué. Réessayez dans un instant.";
  } finally {
    askBtn.disabled = false;
    askBtn.textContent = 'Répondre avec RAG';
  }
}

askBtn.addEventListener('click', ask);

async function init() {
  const res = await fetch('/api/bootstrap');
  const data = await res.json();
  documentText.value = data.example_document || '';
  questionInput.value = data.example_question || '';
}

init();
