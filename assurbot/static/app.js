const chatLog = document.getElementById('chatLog');
const chatInput = document.getElementById('chatInput');
const sendBtn = document.getElementById('sendBtn');
const examplesList = document.getElementById('examplesList');

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function renderAssistantMessage({ answer, sources, mode }) {
  const wrap = document.createElement('div');
  wrap.className = 'msg assistant';

  const bubble = document.createElement('div');
  bubble.className = 'msg-bubble';
  bubble.innerHTML = escapeHtml(answer).replace(/\n/g, '<br>');

  if (mode === 'raw_faq') {
    const flag = document.createElement('div');
    flag.className = 'msg-flag';
    flag.textContent = 'Extrait de FAQ affiché tel quel (moteur IA indisponible).';
    bubble.appendChild(flag);
  }

  if (sources && sources.length) {
    const details = document.createElement('details');
    details.className = 'sources-details';
    const summary = document.createElement('summary');
    summary.textContent = 'Sources utilisées dans la FAQ';
    details.appendChild(summary);
    sources.forEach(s => {
      const item = document.createElement('div');
      item.className = 'source-item';
      item.innerHTML = `<b>${escapeHtml(s.question)}</b> (similarité ${s.score})<br>${escapeHtml(s.answer)}`;
      details.appendChild(item);
    });
    bubble.appendChild(details);
  }

  wrap.appendChild(bubble);
  chatLog.appendChild(wrap);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function renderUserMessage(text) {
  const wrap = document.createElement('div');
  wrap.className = 'msg user';
  const bubble = document.createElement('div');
  bubble.className = 'msg-bubble';
  bubble.textContent = text;
  wrap.appendChild(bubble);
  chatLog.appendChild(wrap);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function renderTyping() {
  const wrap = document.createElement('div');
  wrap.className = 'msg assistant';
  wrap.id = 'typingIndicator';
  const bubble = document.createElement('div');
  bubble.className = 'msg-bubble typing';
  bubble.textContent = 'AssurBot rédige une réponse...';
  wrap.appendChild(bubble);
  chatLog.appendChild(wrap);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function removeTyping() {
  const el = document.getElementById('typingIndicator');
  if (el) el.remove();
}

async function sendMessage(text) {
  if (!text.trim()) return;
  renderUserMessage(text);
  chatInput.value = '';
  sendBtn.disabled = true;
  renderTyping();

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text })
    });
    const data = await res.json();
    removeTyping();
    renderAssistantMessage(data);
  } catch (err) {
    removeTyping();
    renderAssistantMessage({ answer: "Une erreur est survenue, réessayez dans un instant.", sources: [], mode: 'no_match' });
  } finally {
    sendBtn.disabled = false;
    chatInput.focus();
  }
}

sendBtn.addEventListener('click', () => sendMessage(chatInput.value));
chatInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage(chatInput.value);
  }
});

async function init() {
  const res = await fetch('/api/bootstrap');
  const data = await res.json();
  renderAssistantMessage({ answer: data.welcome, sources: [], mode: 'ai' });

  data.examples.forEach(ex => {
    const chip = document.createElement('button');
    chip.className = 'example-chip';
    chip.textContent = ex;
    chip.addEventListener('click', () => sendMessage(ex));
    examplesList.appendChild(chip);
  });
}

init();
