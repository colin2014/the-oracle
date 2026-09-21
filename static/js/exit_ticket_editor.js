/* Exit ticket editor. Edits happen in memory and are saved with one PUT (the server validates everything).
   Text handlers only update state; structural changes (add, remove, move, change type) redraw the list. */
(function () {
  'use strict';

  const cfg = JSON.parse(document.getElementById('eteConfig').textContent);
  const root = document.getElementById('eteApp');
  const TYPES = cfg.types;
  const ORDER = ['mcq', 'truefalse', 'fill', 'match', 'order', 'short', 'explain'];
  const BLANK = '____';

  let t = JSON.parse(JSON.stringify(cfg.ticket));
  let dirty = false;
  let statusEl = null;
  let objectiveWasAuto = !t.objective || (cfg.topics.find((x) => x.topic_id === t.topic_id) || {}).statement === t.objective;

  // ------------------------------------------------------------------ helpers
  function h(tag, attrs, ...kids) {
    const el = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v === null || v === undefined || v === false) continue;
      if (k === 'class') el.className = v;
      else if (k === 'text') el.textContent = v;
      else if (k === 'value') el.value = v;
      else if (k.startsWith('on')) el.addEventListener(k.slice(2), v);
      else el.setAttribute(k, v === true ? '' : v);
    }
    for (const kid of kids.flat()) {
      if (kid === null || kid === undefined || kid === false) continue;
      el.append(kid.nodeType ? kid : document.createTextNode(String(kid)));
    }
    return el;
  }
  const markDirty = () => { dirty = true; setStatus('Unsaved changes', ''); updateTotal(); };
  function setStatus(msg, cls) { if (statusEl) { statusEl.textContent = msg; statusEl.className = 'ete-status ' + (cls || ''); } }
  function updateTotal() {
    if (typeof total !== 'undefined' && total) total.textContent = 'Total marks: ' + (Math.round(t.questions.reduce((n, q) => n + Number(q.marks || 0), 0) * 100) / 100);
  }

  function countBlanks(text) { return (text.split(BLANK).length - 1); }
  function defaultMarks(q) {
    const d = q.data;
    switch (q.qtype) {
      case 'mcq': return 1;
      case 'truefalse': return d.statements.length;
      case 'fill': return d.sentences.reduce((n, s) => n + s.blanks.length, 0);
      case 'match': return d.pairs.length;
      case 'order': return d.items.length;
      default: return q.qtype === 'short' ? 2 : 4;
    }
  }
  function refreshMarks(q) { if (q._auto) q.marks = Math.max(0.5, defaultMarks(q)); }

  function blankData(qtype) {
    switch (qtype) {
      case 'mcq': return { options: ['', '', '', ''], correct: 0 };
      case 'truefalse': return { statements: [{ text: '', answer: true }, { text: '', answer: true }, { text: '', answer: true }] };
      case 'fill': return { sentences: [{ text: 'The ' + BLANK + ' ...', blanks: [['']] }] };
      case 'match': return { pairs: [{ left: '', right: '' }, { left: '', right: '' }, { left: '', right: '' }, { left: '', right: '' }], distractors: [] };
      case 'order': return { items: ['', '', ''] };
      default: return { model_answer: '', marking_points: [] };
    }
  }
  function newQuestion(qtype) {
    const prompts = { truefalse: 'True or false?', fill: 'Complete each sentence.' };
    const q = { id: null, qtype, prompt: prompts[qtype] || '', marks: 1, data: blankData(qtype), _auto: true };
    refreshMarks(q);
    return q;
  }
  t.questions.forEach((q) => { q._auto = Number(q.marks) === defaultMarks(q); });

  // ------------------------------------------------------------------ small building blocks
  function textRow(value, placeholder, onInput, extra) {
    const input = h('input', { type: 'text', value: value || '', placeholder, maxlength: '300', 'aria-label': placeholder });
    input.addEventListener('input', () => { onInput(input.value); markDirty(); });
    return h('div', { class: 'ete-row' }, input, extra || null);
  }
  function iconBtn(label, glyph, onclick, opts) {
    return h('button', { type: 'button', class: 'ete-icon' + (opts && opts.danger ? ' danger' : ''), 'aria-label': label, title: label, text: glyph, disabled: !!(opts && opts.disabled), onclick });
  }
  function listEditor(arr, cfgL) {
    // a simple list of text inputs with add/remove (and optional reordering)
    const wrap = h('div');
    function draw() {
      wrap.replaceChildren();
      arr.forEach((val, i) => {
        const btns = [];
        if (cfgL.reorder) {
          btns.push(iconBtn('Move up', '▲', () => { [arr[i - 1], arr[i]] = [arr[i], arr[i - 1]]; markDirty(); draw(); }, { disabled: i === 0 }));
          btns.push(iconBtn('Move down', '▼', () => { [arr[i + 1], arr[i]] = [arr[i], arr[i + 1]]; markDirty(); draw(); }, { disabled: i === arr.length - 1 }));
        }
        btns.push(iconBtn('Remove', '✕', () => { arr.splice(i, 1); cfgL.onChange && cfgL.onChange(); markDirty(); draw(); }, { danger: true, disabled: arr.length <= cfgL.min }));
        const row = textRow(val, cfgL.placeholder + ' ' + (i + 1), (v) => { arr[i] = v; }, h('span', { class: 'ete-row', style: 'gap:.25rem' }, btns));
        wrap.append(row);
      });
      if (arr.length < cfgL.max) wrap.append(h('button', { type: 'button', class: 'ete-add', text: cfgL.addLabel, onclick: () => { arr.push(''); cfgL.onChange && cfgL.onChange(); markDirty(); draw(); } }));
    }
    draw();
    return wrap;
  }

  // ------------------------------------------------------------------ type-specific editors
  function editMcq(q, redraw) {
    const d = q.data, wrap = h('div');
    const name = 'mcq' + Math.random().toString(36).slice(2);
    function draw() {
      wrap.replaceChildren(h('label', { class: 'ete-lbl', text: 'Options (tick the correct one)' }));
      d.options.forEach((val, i) => {
        const radio = h('input', { type: 'radio', name, 'aria-label': 'Option ' + (i + 1) + ' is correct' });
        radio.checked = d.correct === i;
        radio.addEventListener('change', () => { d.correct = i; markDirty(); });
        const input = h('input', { type: 'text', value: val, placeholder: 'Option ' + String.fromCharCode(65 + i), maxlength: '300', 'aria-label': 'Option ' + String.fromCharCode(65 + i) });
        input.addEventListener('input', () => { d.options[i] = input.value; markDirty(); });
        wrap.append(h('div', { class: 'ete-row' }, radio, h('strong', { text: String.fromCharCode(65 + i) }), input,
          iconBtn('Remove option', '✕', () => { d.options.splice(i, 1); if (d.correct >= d.options.length) d.correct = 0; else if (d.correct > i) d.correct--; markDirty(); draw(); }, { danger: true, disabled: d.options.length <= 2 })));
      });
      if (d.options.length < 8) wrap.append(h('button', { type: 'button', class: 'ete-add', text: '+ Add option', onclick: () => { d.options.push(''); markDirty(); draw(); } }));
    }
    draw();
    return wrap;
  }

  function editTrueFalse(q, redraw) {
    const d = q.data, wrap = h('div');
    function draw() {
      wrap.replaceChildren(h('label', { class: 'ete-lbl', text: 'Statements' }));
      d.statements.forEach((s, i) => {
        const input = h('input', { type: 'text', value: s.text, placeholder: 'Statement ' + (i + 1), maxlength: '300', 'aria-label': 'Statement ' + (i + 1) });
        input.addEventListener('input', () => { s.text = input.value; markDirty(); });
        const sel = h('select', { class: 'ete-tf', 'aria-label': 'Answer for statement ' + (i + 1) }, h('option', { value: 'true', text: 'True' }), h('option', { value: 'false', text: 'False' }));
        sel.value = String(s.answer);
        sel.addEventListener('change', () => { s.answer = sel.value === 'true'; markDirty(); });
        wrap.append(h('div', { class: 'ete-row' }, input, sel,
          iconBtn('Remove statement', '✕', () => { d.statements.splice(i, 1); refreshMarks(q); markDirty(); redraw(); }, { danger: true, disabled: d.statements.length <= 1 })));
      });
      if (d.statements.length < 8) wrap.append(h('button', { type: 'button', class: 'ete-add', text: '+ Add statement', onclick: () => { d.statements.push({ text: '', answer: true }); refreshMarks(q); markDirty(); redraw(); } }));
    }
    draw();
    return wrap;
  }

  function editFill(q, redraw) {
    const d = q.data, wrap = h('div');
    wrap.append(h('p', { class: 'ete-hint', text: 'Write each sentence with ' + BLANK + ' where the gap goes. Then give the correct answer for each gap; separate alternatives with | (for example: Control Unit | CU).' }));
    d.sentences.forEach((s, i) => {
      const blanksEl = h('div', { class: 'ete-blanks' });
      const drawBlanks = () => {
        blanksEl.replaceChildren();
        s.blanks.forEach((alts, j) => {
          const input = h('input', { type: 'text', value: alts.join(' | '), placeholder: 'Correct answer', maxlength: '300', 'aria-label': 'Answers for blank ' + (j + 1) + ' of sentence ' + (i + 1) });
          input.addEventListener('input', () => { s.blanks[j] = input.value.split('|').map((x) => x.trim()); markDirty(); });
          blanksEl.append(h('div', { class: 'ete-row' }, h('span', { text: 'Blank ' + (j + 1) }), input));
        });
      };
      const input = h('input', { type: 'text', value: s.text, placeholder: 'The ' + BLANK + ' directs the CPU.', maxlength: '400', 'aria-label': 'Sentence ' + (i + 1) });
      input.addEventListener('input', () => {
        s.text = input.value;
        const n = countBlanks(s.text);
        while (s.blanks.length < n) s.blanks.push(['']);
        s.blanks.length = n;
        refreshMarks(q); drawBlanks(); markDirty();
      });
      wrap.append(h('div', { class: 'ete-row' }, input, iconBtn('Remove sentence', '✕', () => { d.sentences.splice(i, 1); refreshMarks(q); markDirty(); redraw(); }, { danger: true, disabled: d.sentences.length <= 1 })), blanksEl);
      drawBlanks();
    });
    if (d.sentences.length < 6) wrap.append(h('button', { type: 'button', class: 'ete-add', text: '+ Add sentence', onclick: () => { d.sentences.push({ text: 'The ' + BLANK + ' ...', blanks: [['']] }); refreshMarks(q); markDirty(); redraw(); } }));
    return wrap;
  }

  function editMatch(q, redraw) {
    const d = q.data, wrap = h('div');
    wrap.append(h('label', { class: 'ete-lbl', text: 'Pairs: each term with its correct description' }));
    d.pairs.forEach((p, i) => {
      const a = h('input', { type: 'text', value: p.left, placeholder: 'Term', maxlength: '200', 'aria-label': 'Term ' + (i + 1), style: 'max-width:14rem' });
      const b = h('input', { type: 'text', value: p.right, placeholder: 'Description', maxlength: '300', 'aria-label': 'Description ' + (i + 1) });
      a.addEventListener('input', () => { p.left = a.value; markDirty(); });
      b.addEventListener('input', () => { p.right = b.value; markDirty(); });
      wrap.append(h('div', { class: 'ete-row' }, a, h('span', { text: '→', 'aria-hidden': 'true' }), b,
        iconBtn('Remove pair', '✕', () => { d.pairs.splice(i, 1); refreshMarks(q); markDirty(); redraw(); }, { danger: true, disabled: d.pairs.length <= 2 })));
    });
    if (d.pairs.length < 8) wrap.append(h('button', { type: 'button', class: 'ete-add', text: '+ Add pair', onclick: () => { d.pairs.push({ left: '', right: '' }); refreshMarks(q); markDirty(); redraw(); } }));
    wrap.append(h('label', { class: 'ete-lbl', text: 'Extra wrong descriptions (optional, to make it harder)' }),
      listEditor(d.distractors, { min: 0, max: 4, placeholder: 'Distractor', addLabel: '+ Add distractor' }));
    return wrap;
  }

  function editOrder(q, redraw) {
    const d = q.data, wrap = h('div');
    wrap.append(h('p', { class: 'ete-hint', text: 'Enter the items in the CORRECT order. Students see them shuffled and put them back in order.' }),
      listEditor(d.items, { min: 2, max: 8, placeholder: 'Step', addLabel: '+ Add item', reorder: true, onChange: () => { refreshMarks(q); } }));
    return wrap;
  }

  function editWritten(q, redraw) {
    const d = q.data, wrap = h('div');
    const model = h('textarea', { rows: '3', maxlength: '2000', placeholder: 'What a good answer says', 'aria-label': 'Model answer' });
    model.value = d.model_answer || '';
    model.addEventListener('input', () => { d.model_answer = model.value; markDirty(); });
    wrap.append(h('label', { class: 'ete-lbl', text: 'Model answer (the AI marks against this; students only see it after submitting, if you allow it)' }), model,
      h('label', { class: 'ete-lbl', text: 'Marking points (one idea per line, each worth marks)' }),
      listEditor(d.marking_points, { min: 0, max: 10, placeholder: 'Marking point', addLabel: '+ Add marking point' }));
    return wrap;
  }

  const EDITORS = { mcq: editMcq, truefalse: editTrueFalse, fill: editFill, match: editMatch, order: editOrder, short: editWritten, explain: editWritten };

  // ------------------------------------------------------------------ the question list
  function questionCard(q, i) {
    const info = TYPES[q.qtype];
    const card = h('section', { class: 'ete-q', 'aria-label': 'Question ' + (i + 1) + ': ' + info.label });
    card.style.setProperty('--accent', info.accent);
    card.style.setProperty('--tint', info.tint);
    const marks = h('input', { type: 'number', min: '0.5', max: '20', step: '0.5', value: q.marks, 'aria-label': 'Marks for question ' + (i + 1) });
    marks.addEventListener('input', () => { q.marks = Number(marks.value); q._auto = false; markDirty(); });
    card.append(h('div', { class: 'ete-q-head' },
      h('span', { class: 'ete-num', text: String(i + 1) }), h('span', { class: 'ete-pill', text: info.label }), h('span', { class: 'ete-spacer' }),
      h('label', { class: 'ete-marks' }, 'Marks', marks),
      iconBtn('Move question up', '▲', () => move(i, i - 1), { disabled: i === 0 }),
      iconBtn('Move question down', '▼', () => move(i, i + 1), { disabled: i === t.questions.length - 1 }),
      iconBtn('Duplicate question', '⧉', () => { const c = JSON.parse(JSON.stringify(q)); c.id = null; t.questions.splice(i + 1, 0, c); markDirty(); draw(); }),
      iconBtn('Delete question', '✕', () => { if (confirm('Delete this question?')) { t.questions.splice(i, 1); markDirty(); draw(); } }, { danger: true })));
    const prompt = h('textarea', { rows: '2', maxlength: '1000', 'aria-label': 'Question text', placeholder: q.qtype === 'truefalse' ? 'True or false?' : (q.qtype === 'fill' ? 'Complete each sentence.' : 'Question text') });
    prompt.value = q.prompt || '';
    prompt.addEventListener('input', () => { q.prompt = prompt.value; markDirty(); });
    card.append(h('label', { class: 'ete-lbl', text: 'Question' }), prompt);
    const redrawCard = () => { const fresh = questionCard(q, i); card.replaceWith(fresh); };
    card.append(EDITORS[q.qtype](q, redrawCard));
    return card;
  }
  function move(from, to) {
    if (to < 0 || to >= t.questions.length) return;
    const [q] = t.questions.splice(from, 1); t.questions.splice(to, 0, q);
    markDirty(); draw();
  }

  // ------------------------------------------------------------------ page
  const list = h('div');
  function draw() {
    list.replaceChildren();
    if (!t.questions.length) list.append(h('div', { class: 'ete-empty', text: 'No questions yet. Add one below.' }));
    t.questions.forEach((q, i) => list.append(questionCard(q, i)));
    updateTotal();
  }
  const total = h('span', { style: 'font-weight:700' });

  function field(label, control, span) { return h('div', { class: 'ete-field' + (span ? ' ete-span' : '') }, h('label', { text: label }), control); }

  function detailsCard() {
    const title = h('input', { type: 'text', value: t.title, maxlength: '200', 'aria-label': 'Title' });
    title.addEventListener('input', () => { t.title = title.value; markDirty(); });
    const code = h('input', { type: 'text', value: t.code || '', maxlength: '30', placeholder: 'e.g. A1.1.1', 'aria-label': 'Topic code' });
    code.addEventListener('input', () => { t.code = code.value; markDirty(); });
    const objective = h('textarea', { rows: '2', maxlength: '1000', 'aria-label': 'Objective' });
    objective.value = t.objective || '';
    objective.addEventListener('input', () => { t.objective = objective.value; objectiveWasAuto = false; markDirty(); });
    const topic = h('select', { 'aria-label': 'Syllabus topic' }, h('option', { value: '', text: 'No syllabus topic' }),
      cfg.topics.map((x) => h('option', { value: x.topic_id, text: x.code + '  ' + x.statement.slice(0, 80) })));
    topic.value = t.topic_id || '';
    topic.addEventListener('change', () => {
      const x = cfg.topics.find((y) => y.topic_id === topic.value);
      t.topic_id = x ? x.topic_id : null;
      if (x) { t.code = x.code; code.value = x.code; if (objectiveWasAuto || !t.objective) { t.objective = x.statement; objective.value = x.statement; objectiveWasAuto = true; } }
      markDirty();
    });
    const status = h('select', { 'aria-label': 'Status' }, h('option', { value: 'draft', text: 'Draft (students can’t see it)' }), h('option', { value: 'published', text: 'Published (can be assigned)' }));
    status.value = t.status;
    status.addEventListener('change', () => { t.status = status.value; markDirty(); });
    const show = h('select', { 'aria-label': 'Show correct answers' }, h('option', { value: 'after', text: 'Show correct answers after they submit' }), h('option', { value: 'never', text: 'Never show correct answers' }));
    show.value = t.show_answers;
    show.addEventListener('change', () => { t.show_answers = show.value; markDirty(); });
    const retry = h('input', { type: 'checkbox', 'aria-label': 'Allow retries' });
    retry.checked = !!t.allow_retries;
    retry.addEventListener('change', () => { t.allow_retries = retry.checked; markDirty(); });
    return h('div', { class: 'ete-card' }, h('div', { class: 'ete-grid' },
      field('Title', title), field('Syllabus topic', topic), field('Topic code', code),
      field('Objective (shown under the header)', objective, true),
      field('Status', status), field('Answers', show),
      h('label', { class: 'ete-check' }, retry, 'Students can try again')));
  }

  function build() {
    statusEl = h('span', { class: 'ete-status', role: 'status', text: 'Saved' });
    const saveBtn = h('button', { type: 'button', class: 'btn btn-primary', text: 'Save' });
    saveBtn.addEventListener('click', save);
    const preview = h('a', { class: 'btn btn-secondary', href: cfg.previewUrl, text: 'Preview' });
    preview.addEventListener('click', (e) => { if (dirty && !confirm('You have unsaved changes. The preview shows the last saved version. Continue?')) e.preventDefault(); });
    const results = h('a', { class: 'btn btn-secondary', href: cfg.resultsUrl, text: 'Results & assigning' });
    const version = h('span', { class: 'ete-version', text: 'Version ' + (t.version || 1), title: 'Goes up whenever a save changes the questions' });
    const bar = h('div', { class: 'ete-bar' }, h('strong', { text: 'Exit ticket' }), version, total, statusEl, preview, results, saveBtn);
    const hint = h('p', { class: 'ete-hint', style: 'margin:0 0 1rem',
      text: 'Changes only affect new attempts. Students who have already started or finished keep the version they took, and their results stay as they were.' });

    const addbar = h('div', { class: 'ete-addbar' }, h('strong', { text: 'Add a question:' }),
      ORDER.map((k) => {
        const b = h('button', { type: 'button', class: 'ete-addbtn', text: TYPES[k].label });
        b.style.background = TYPES[k].accent;
        b.addEventListener('click', () => { t.questions.push(newQuestion(k)); markDirty(); draw(); const last = list.lastElementChild; if (last) last.scrollIntoView({ block: 'center', behavior: 'smooth' }); });
        return b;
      }));
    root.replaceChildren(bar, hint, detailsCard(), list, addbar);
    draw();
  }

  function payload() {
    return {
      title: t.title, code: t.code || '', topic_id: t.topic_id || '', objective: t.objective || '', status: t.status,
      allow_retries: !!t.allow_retries, show_answers: t.show_answers,
      questions: t.questions.map((q) => {
        const d = JSON.parse(JSON.stringify(q.data));
        if (q.qtype === 'fill') d.sentences.forEach((s) => { s.blanks = s.blanks.map((alts) => alts.map((a) => a.trim()).filter(Boolean)); });
        if (q.qtype === 'match') d.distractors = d.distractors.filter((x) => x.trim());
        if (q.qtype === 'short' || q.qtype === 'explain') d.marking_points = d.marking_points.filter((x) => x.trim());
        return { id: q.id, qtype: q.qtype, prompt: q.prompt, marks: Number(q.marks), data: d };
      }),
    };
  }

  async function save() {
    setStatus('Saving…', '');
    try {
      const res = await fetch(cfg.saveUrl, { method: 'PUT', credentials: 'same-origin', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': cfg.csrf }, body: JSON.stringify(payload()) });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) { setStatus(data.error || 'Could not save.', 'err'); return; }
      const autoFlags = t.questions.map((q) => q._auto);
      t = data.ticket;
      t.questions.forEach((q, i) => { q._auto = autoFlags[i] !== undefined ? autoFlags[i] : Number(q.marks) === defaultMarks(q); });
      dirty = false; build(); setStatus('Saved', 'ok');
    } catch (e) { setStatus('Network problem: ' + e.message, 'err'); }
  }

  window.addEventListener('beforeunload', (e) => { if (dirty) { e.preventDefault(); e.returnValue = ''; } });
  build();
})();
