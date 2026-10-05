const form = document.querySelector('#question-form');
const question = document.querySelector('#question');
const model = document.querySelector('#model');
const submit = document.querySelector('#submit');
const status = document.querySelector('#status');
const results = document.querySelector('#results');
const documentView = document.querySelector('#document');
const selectedOnly = document.querySelector('#selected-only');
let catalog;
const passages = new Map();

function element(tag, className, text) {
  const node = document.createElement(tag);
  node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function clearPrediction() {
  results.replaceChildren();
  for (const passage of passages.values()) {
    passage.classList.remove('selected');
    passage.hidden = false;
    passage.querySelector('.score')?.remove();
  }
  selectedOnly.checked = false;
  selectedOnly.disabled = true;
}

function showModel() {
  const item = catalog.models.find(item => item.id === model.value);
  document.querySelector('#model-info').textContent =
    `Validierungs-Q-F1: ${(item.validation_f1 * 100).toFixed(1)} % · maximal ${item.max_chunks} Chunk`;
}

function jumpTo(id) {
  const passage = passages.get(id);
  passage.scrollIntoView({ behavior: 'smooth', block: 'start' });
  passage.focus({ preventScroll: true });
}

async function request(url, options) {
  const response = await fetch(url, options);
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || 'Die Anfrage ist fehlgeschlagen.');
  return body;
}

async function initialize() {
  try {
    catalog = await request('/api/catalog');
    model.replaceChildren(...catalog.models.map((item, index) => {
      const option = document.createElement('option');
      option.value = item.id;
      option.textContent = `${index + 1}. ${item.label}`;
      return option;
    }));
    const fragment = document.createDocumentFragment();
    for (const chunk of catalog.chunks) {
      const passage = element('article', 'passage');
      passage.id = chunk.chunk_id;
      passage.tabIndex = -1;
      const meta = element('div', 'passage-meta');
      meta.append(element('span', '', chunk.section_path.join(' / ')));
      const page = chunk.page_start === chunk.page_end ? `${chunk.page_start}` : `${chunk.page_start}–${chunk.page_end}`;
      const link = element('a', '', `S. ${page} ↗`);
      link.href = `/regulation.pdf?chunk_id=${encodeURIComponent(chunk.chunk_id)}#page=${chunk.page_start}&zoom=125`;
      link.title = "PDF mit markiertem Chunk öffnen";
      link.target = '_blank';
      link.rel = 'noopener';
      meta.append(link);
      passage.append(meta, element('p', 'passage-text', chunk.chunk_text), element('div', 'chunk-id', chunk.chunk_id));
      passages.set(chunk.chunk_id, passage);
      fragment.append(passage);
    }
    documentView.append(fragment);
    document.querySelector('#chunk-count').textContent = `${catalog.chunks.length} Chunks · Dokumentreihenfolge`;
    model.disabled = false;
    submit.disabled = false;
    showModel();
    status.textContent = 'Bereit für deine Frage.';
  } catch (error) {
    status.textContent = error.message;
    status.classList.add('error');
  }
}

form.addEventListener('submit', async event => {
  event.preventDefault();
  if (!question.value.trim()) {
    question.setCustomValidity('Bitte gib eine Frage ein.');
    question.reportValidity();
    return;
  }
  clearPrediction();
  status.classList.remove('error');
  status.textContent = 'Das Modell sucht … E5 kann beim ersten Aufruf etwas länger brauchen.';
  submit.disabled = true;
  model.disabled = true;
  question.disabled = true;
  form.setAttribute('aria-busy', 'true');
  document.querySelectorAll('[data-question]').forEach(button => { button.disabled = true; });
  try {
    const prediction = await request('/api/predict', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: question.value, model_id: model.value }),
    });
    status.textContent = prediction.chunk_ids.length
      ? `${prediction.chunk_ids.length} Textstelle ausgewählt und im Dokument markiert.`
      : 'Keine Textstelle ausgewählt. Kein Chunk erfüllt die Auswahlregel dieses Modells.';
    prediction.chunk_ids.forEach((id, index) => {
      const passage = passages.get(id);
      passage.classList.add('selected');
      passage.querySelector('.passage-meta').prepend(element('span', 'score', `Treffer ${index + 1} · Cosinus ${prediction.scores[index].toFixed(3)}`));
      const chunk = catalog.chunks.find(chunk => chunk.chunk_id === id);
      const button = element('button', 'result-link', `${chunk.section_path.join(' / ')} →`);
      button.type = 'button';
      button.addEventListener('click', () => jumpTo(id));
      results.append(button);
    });
    selectedOnly.disabled = prediction.chunk_ids.length === 0;
    if (prediction.chunk_ids.length) jumpTo(prediction.chunk_ids[0]);
  } catch (error) {
    status.textContent = error.message;
    status.classList.add('error');
  } finally {
    submit.disabled = false;
    model.disabled = false;
    question.disabled = false;
    form.removeAttribute('aria-busy');
    document.querySelectorAll('[data-question]').forEach(button => { button.disabled = false; });
  }
});

question.addEventListener('input', () => {
  question.setCustomValidity('');
  if (catalog) { clearPrediction(); status.textContent = 'Bereit für deine Frage.'; }
});
model.addEventListener('change', () => {
  clearPrediction(); showModel(); status.textContent = 'Bereit für deine Frage.';
});
selectedOnly.addEventListener('change', () => {
  for (const passage of passages.values()) {
    passage.hidden = selectedOnly.checked && !passage.classList.contains('selected');
  }
});
document.querySelectorAll('[data-question]').forEach(button => {
  button.addEventListener('click', () => {
    question.value = button.dataset.question;
    question.dispatchEvent(new Event('input'));
    question.focus();
  });
});
initialize();
