/* Exit ticket player: answering, results review, and the teacher's mark overrides.
   Everything from the server is inserted with textContent (never innerHTML), so question and answer
   text can't inject markup. */
(function () {
  'use strict';

  const cfg = JSON.parse(document.getElementById('etConfig').textContent);
  const root = document.getElementById('etApp');
  const TYPES = cfg.types;
  const MODE = cfg.mode;                       // student | teacher | preview

  let payload = null;
  let answers = {};                            // question id -> response
  let touched = new Set();                     // questions the student has interacted with
  let confidence = null;
  let note = '';
  let submitting = false;
  let progressEl = null;
  let submitBtn = null;
  let liveRegion = null;

  // ------------------------------------------------------------------ small helpers
  function h(tag, attrs, ...kids) {
    const el = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v === null || v === undefined || v === false) continue;
      if (k === 'class') el.className = v;
      else if (k === 'text') el.textContent = v;
      else if (k.startsWith('on')) el.addEventListener(k.slice(2), v);
      else el.setAttribute(k, v === true ? '' : v);
    }
    for (const kid of kids.flat()) {
      if (kid === null || kid === undefined || kid === false) continue;
      el.append(kid.nodeType ? kid : document.createTextNode(String(kid)));
    }
    return el;
  }

  async function api(url, method, body) {
    const res = await fetch(url, {
      method: method || 'GET', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': cfg.csrf },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    let data = null;
    try { data = await res.json(); } catch (e) { /* not JSON */ }
    if (!res.ok) throw new Error((data && data.error) || 'Something went wrong (' + res.status + ').');
    return data;
  }

  const num = (x) => (Math.round(x * 100) / 100).toString();
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const letter = (i) => String.fromCharCode(65 + i);

  function announce(msg) { if (liveRegion) liveRegion.textContent = msg; }

  // draft answers survive an accidental refresh (this tab only)
  const draftKey = () => 'et-draft-' + (payload && payload.attempt.id);
  function saveDraft() {
    if (MODE !== 'student' || !payload || payload.state !== 'in_progress') return;
    try { sessionStorage.setItem(draftKey(), JSON.stringify({ answers, touched: [...touched], confidence, note })); } catch (e) { /* private mode */ }
  }
  function loadDraft() {
    if (MODE !== 'student') return;
    try {
      const d = JSON.parse(sessionStorage.getItem(draftKey()) || 'null');
      if (d) { answers = d.answers || {}; touched = new Set(d.touched || []); confidence = d.confidence || null; note = d.note || ''; }
    } catch (e) { /* ignore */ }
  }

  // ------------------------------------------------------------------ drag and drop (mouse, touch, pen)
  let suppressClick = false;
  function makeDraggable(el, opts) {
    el.addEventListener('pointerdown', (e) => {
      if (e.button !== 0 && e.pointerType === 'mouse') return;
      const sx = e.clientX, sy = e.clientY;
      let dragging = false, ghost = null, over = null;
      try { el.setPointerCapture(e.pointerId); } catch (err) { /* ignore */ }
      const move = (ev) => {
        if (!dragging) {
          if (Math.hypot(ev.clientX - sx, ev.clientY - sy) < 6) return;
          dragging = true;
          ghost = el.cloneNode(true);
          ghost.classList.add('et-ghost');
          ghost.style.width = el.offsetWidth + 'px';
          document.body.append(ghost);
          el.classList.add('dragging');
        }
        ghost.style.left = (ev.clientX - ghost.offsetWidth / 2) + 'px';
        ghost.style.top = (ev.clientY - ghost.offsetHeight / 2) + 'px';
        const t = opts.targetAt(ev.clientX, ev.clientY);
        if (t !== over) { if (over) over.classList.remove(opts.overClass); over = t; if (over) over.classList.add(opts.overClass); }
      };
      const up = () => {
        el.removeEventListener('pointermove', move);
        el.removeEventListener('pointerup', up);
        el.removeEventListener('pointercancel', up);
        try { el.releasePointerCapture(e.pointerId); } catch (err) { /* ignore */ }
        if (!dragging) return;
        ghost.remove();
        el.classList.remove('dragging');
        if (over) over.classList.remove(opts.overClass);
        suppressClick = true;
        setTimeout(() => { suppressClick = false; }, 0);
        if (over) opts.onDrop(over);
      };
      el.addEventListener('pointermove', move);
      el.addEventListener('pointerup', up);
      el.addEventListener('pointercancel', up);
    });
    el.addEventListener('click', (e) => {
      if (suppressClick) { e.preventDefault(); e.stopPropagation(); return; }
      if (opts.onClick) opts.onClick(e);
    });
  }

  function dropTargetAt(container, attr) {
    return (x, y) => {
      const el = document.elementFromPoint(x, y);
      const t = el && el.closest('[' + attr + ']');
      return t && container.contains(t) ? t : null;
    };
  }

  // ------------------------------------------------------------------ answering widgets
  function widgetMcq(q) {
    const group = h('div', { class: 'et-opts', role: 'radiogroup', 'aria-label': q.prompt || 'Choose one' });
    const buttons = q.options.map((text, i) => {
      const b = h('button', { type: 'button', class: 'et-opt', role: 'radio', 'aria-checked': String(answers[q.id] === i) },
        h('span', { class: 'et-letter', text: letter(i) }), h('span', { text }));
      b.addEventListener('click', () => {
        answers[q.id] = i; touched.add(q.id);
        buttons.forEach((x, j) => x.setAttribute('aria-checked', String(j === i)));
        changed();
      });
      return b;
    });
    group.append(...buttons);
    return group;
  }

  function widgetTrueFalse(q) {
    if (!Array.isArray(answers[q.id])) answers[q.id] = q.statements.map(() => null);
    const wrap = h('div', { class: 'et-tf' });
    q.statements.forEach((text, i) => {
      const btns = [true, false].map((val) => {
        const b = h('button', { type: 'button', class: 'et-tf-btn', 'aria-pressed': String(answers[q.id][i] === val),
          'aria-label': (val ? 'True' : 'False') + ': ' + text, text: val ? 'T' : 'F' });
        b.addEventListener('click', () => {
          answers[q.id][i] = val; touched.add(q.id);
          btns.forEach((x, k) => x.setAttribute('aria-pressed', String(answers[q.id][i] === (k === 0))));
          changed();
        });
        return b;
      });
      wrap.append(h('div', { class: 'et-tf-row' }, h('span', { class: 'et-tf-text', text }), h('span', { class: 'et-tf-btns' }, btns)));
    });
    return wrap;
  }

  function widgetFill(q) {
    const total = q.blank_counts.reduce((a, b) => a + b, 0);
    if (!Array.isArray(answers[q.id])) answers[q.id] = new Array(total).fill('');
    const wrap = h('div', { class: 'et-fill' });
    let k = 0;
    q.sentences.forEach((text) => {
      const line = h('div', { class: 'et-fill-line' });
      text.split('____').forEach((part, i, arr) => {
        line.append(document.createTextNode(part));
        if (i < arr.length - 1) {
          const idx = k++;
          const input = h('input', { type: 'text', class: 'et-blank', autocomplete: 'off', autocapitalize: 'off', spellcheck: 'false',
            maxlength: '120', 'aria-label': 'Answer for blank ' + (idx + 1), value: answers[q.id][idx] || '' });
          input.addEventListener('input', () => { answers[q.id][idx] = input.value; touched.add(q.id); changed(); });
          line.append(input);
        }
      });
      wrap.append(line);
    });
    return wrap;
  }

  function widgetWritten(q) {
    const box = h('div');
    const area = h('textarea', { class: 'et-lines', maxlength: '2000', rows: q.qtype === 'explain' ? '6' : '4',
      'aria-label': 'Your answer', placeholder: 'Type your answer here' });
    area.value = typeof answers[q.id] === 'string' ? answers[q.id] : '';
    const count = h('div', { class: 'et-count', text: area.value.length + ' / 2000' });
    area.addEventListener('input', () => { answers[q.id] = area.value; touched.add(q.id); count.textContent = area.value.length + ' / 2000'; changed(); });
    box.append(area, count);
    return box;
  }

  // Match: click a description then click a slot, or drag it there.
  function widgetMatch(q) {
    const text = Object.fromEntries(q.rights.map((r) => [r.id, r.text]));
    const saved = answers[q.id] && typeof answers[q.id] === 'object' ? answers[q.id] : {};
    const state = { slots: q.left.map((_, i) => (saved[String(i)] && text[saved[String(i)]] ? saved[String(i)] : null)), sel: null };
    const wrap = h('div');

    const inTray = () => { const used = new Set(state.slots.filter(Boolean)); return q.rights.map((r) => r.id).filter((id) => !used.has(id)); };
    const commit = () => {
      const a = {}; state.slots.forEach((t, i) => { if (t) a[String(i)] = t; });
      answers[q.id] = a; touched.add(q.id); changed();
    };
    function place(token, from, target) {
      if (target === 'tray') { if (typeof from === 'number') state.slots[from] = null; }
      else {
        const t = Number(target);
        if (from === t) { state.sel = null; draw(); return; }
        const occupant = state.slots[t];
        state.slots[t] = token;
        if (typeof from === 'number') state.slots[from] = occupant && occupant !== token ? occupant : null;
      }
      state.sel = null; draw(); commit();
      announce(target === 'tray' ? 'Returned to the word bank.' : 'Placed next to ' + q.left[Number(target)] + '.');
    }
    function chip(token, from) {
      const c = h('button', { type: 'button', class: 'et-chip' + (state.sel && state.sel.token === token ? ' selected' : ''), 'data-token': token, text: text[token],
        'aria-pressed': String(!!(state.sel && state.sel.token === token)) });
      makeDraggable(c, {
        targetAt: dropTargetAt(wrap, 'data-drop'), overClass: 'drag-over',
        onDrop: (t) => place(token, from, t.dataset.drop),
        onClick: () => {
          if (state.sel && state.sel.token !== token && typeof from === 'number') { place(state.sel.token, state.sel.from, from); return; }
          state.sel = state.sel && state.sel.token === token ? null : { token, from };
          draw();
          if (state.sel) announce('Selected. Now choose where it goes.');
        },
      });
      return c;
    }
    function draw() {
      wrap.replaceChildren();
      wrap.append(h('p', { class: 'et-hint', text: 'Drag each description next to its term, or click a description then click where it goes.' }));
      const rows = h('div', { class: 'et-match' });
      q.left.forEach((term, i) => {
        const token = state.slots[i];
        let slot;
        if (token) {
          slot = h('div', { class: 'et-slot filled', 'data-drop': String(i) }, chip(token, i),
            h('button', { type: 'button', class: 'et-chip', style: 'width:auto;flex:none;margin-left:.4rem;padding:.35rem .6rem', 'aria-label': 'Remove: ' + text[token], text: '✕',
              onclick: () => place(token, i, 'tray') }));
        } else {
          slot = h('button', { type: 'button', class: 'et-slot', 'data-drop': String(i), 'aria-label': 'Place a description next to ' + term, text: 'Drop or click a description here',
            onclick: () => { if (state.sel) place(state.sel.token, state.sel.from, i); } });
        }
        rows.append(h('div', { class: 'et-match-row' }, h('div', { class: 'et-term', text: term }), h('span', { class: 'et-dots', 'aria-hidden': 'true', text: '●●' }), slot));
      });
      wrap.append(rows, h('div', { class: 'et-tray-label', text: 'Word bank' }));
      const tokens = inTray();
      const tray = h('div', { class: 'et-tray', 'data-drop': 'tray' }, tokens.length ? tokens.map((t) => chip(t, 'tray')) : h('span', { class: 'et-tray-empty', text: 'All placed. Drag one back here to change it.' }));
      wrap.append(tray);
    }
    wrap.addEventListener('keydown', (e) => { if (e.key === 'Escape' && state.sel) { state.sel = null; draw(); } });
    draw();
    return wrap;
  }

  // Order: drag items, or use the arrows.
  function widgetOrder(q) {
    const known = new Set(q.items.map((i) => i.id));
    const text = Object.fromEntries(q.items.map((i) => [i.id, i.text]));
    let order = Array.isArray(answers[q.id]) && answers[q.id].length === q.items.length && answers[q.id].every((t) => known.has(t))
      ? answers[q.id].slice() : q.items.map((i) => i.id);
    answers[q.id] = order.slice();
    const wrap = h('div');
    function move(from, to) {
      if (to < 0 || to >= order.length || from === to) return;
      const [t] = order.splice(from, 1); order.splice(to, 0, t);
      answers[q.id] = order.slice(); touched.add(q.id); draw(); changed();
      announce(text[t] + ' is now number ' + (to + 1) + '.');
    }
    function draw() {
      wrap.replaceChildren(h('p', { class: 'et-hint', text: 'Drag the items into the right order, or use the arrows.' }));
      const list = h('ol', { class: 'et-order' });
      order.forEach((token, i) => {
        const label = h('div', { class: 'et-order-text', text: text[token] });
        const li = h('li', { class: 'et-order-item', 'data-drop-token': token, 'data-index': String(i) },
          h('span', { class: 'et-order-n', text: String(i + 1) }), label,
          h('span', { class: 'et-order-btns' },
            h('button', { type: 'button', 'aria-label': 'Move up: ' + text[token], text: '▲', disabled: i === 0, onclick: () => move(i, i - 1) }),
            h('button', { type: 'button', 'aria-label': 'Move down: ' + text[token], text: '▼', disabled: i === order.length - 1, onclick: () => move(i, i + 1) })));
        makeDraggable(label, {
          targetAt: dropTargetAt(list, 'data-drop-token'), overClass: 'over',
          onDrop: (t) => move(i, Number(t.dataset.index)),
        });
        list.append(li);
      });
      wrap.append(list);
    }
    draw();
    return wrap;
  }

  const WIDGETS = { mcq: widgetMcq, truefalse: widgetTrueFalse, fill: widgetFill, match: widgetMatch, order: widgetOrder, short: widgetWritten, explain: widgetWritten };

  function isAnswered(q) {
    const a = answers[q.id];
    switch (q.qtype) {
      case 'mcq': return Number.isInteger(a);
      case 'truefalse': return Array.isArray(a) && a.every((x) => x !== null);
      case 'fill': return Array.isArray(a) && a.length > 0 && a.every((s) => String(s).trim() !== '');
      case 'match': return !!a && Object.keys(a).length === q.left.length;
      case 'order': return touched.has(q.id);
      default: return typeof a === 'string' && a.trim() !== '';
    }
  }

  function changed() {
    saveDraft();
    if (!progressEl) return;
    const done = payload.questions.filter(isAnswered).length;
    progressEl.textContent = done + ' of ' + payload.questions.length + ' answered';
  }

  // ------------------------------------------------------------------ page pieces
  function panel(q, i, badge) {
    const info = TYPES[q.qtype];
    const sec = h('section', { class: 'et-q', 'aria-labelledby': 'etq' + q.id });
    sec.style.setProperty('--accent', info.accent);
    sec.style.setProperty('--tint', info.tint);
    sec.append(h('div', { class: 'et-q-head' }, h('span', { class: 'et-pill', text: info.label }), badge || h('span', { class: 'et-marks', text: num(q.marks) + (q.marks === 1 ? ' mark' : ' marks') })));
    if (q.prompt) sec.append(h('p', { class: 'et-q-text', id: 'etq' + q.id }, h('span', { class: 'et-num', text: String(i + 1) }), q.prompt));
    else sec.append(h('p', { class: 'et-q-text', id: 'etq' + q.id }, h('span', { class: 'et-num', text: String(i + 1) })));
    return sec;
  }

  function header(p, scoreLabel, scoreValue) {
    const t = p.ticket;
    const sub = 'Computer Science · ' + t.title + (MODE === 'teacher' && p.student ? ' · ' + p.student + ' · attempt ' + p.attempt.number : '');
    return [
      h('header', { class: 'et-head' },
        h('div', { class: 'et-logo' }, h('img', { src: cfg.logo, alt: '' })),
        h('div', { class: 'et-head-text' }, h('h1', { text: 'EXIT TICKET' }), h('p', { class: 'et-sub', text: sub })),
        h('div', { class: 'et-score', role: 'status' }, h('span', { class: 'et-score-label', text: scoreLabel }), h('span', { class: 'et-score-value', text: scoreValue }))),
      h('div', { class: 'et-stripe' }),
      (t.code || t.objective) ? h('div', { class: 'et-objective' }, t.code ? h('span', { class: 'et-code', text: t.code }) : null, t.objective || '') : null,
    ];
  }

  // ------------------------------------------------------------------ answering screen
  function drawAnswering() {
    const p = payload;
    const sheet = h('div', { class: 'et-sheet' });
    sheet.append(...header(p, 'TOTAL MARKS', num(p.total_marks)));
    if (MODE === 'preview') sheet.append(h('div', { class: 'et-banner', text: 'Preview: this is what students see. Nothing you do here is saved or marked.' }));
    const body = h('div', { class: 'et-body' });
    p.questions.forEach((q, i) => {
      const sec = panel(q, i);
      sec.append(WIDGETS[q.qtype](q));
      body.append(sec);
    });

    const refl = h('section', { class: 'et-q et-reflect', 'aria-labelledby': 'etreflect' });
    refl.append(h('div', { class: 'et-q-head' }, h('span', { class: 'et-pill', text: 'Reflection' })),
      h('p', { class: 'et-q-text', id: 'etreflect', text: 'How confident do you feel about this objective?' }));
    const scale = h('div', { class: 'et-scale', role: 'group', 'aria-label': 'Confidence from 1 to 5' });
    const sbtns = [1, 2, 3, 4, 5].map((n) => {
      const b = h('button', { type: 'button', 'aria-pressed': String(confidence === n), text: String(n) });
      b.addEventListener('click', () => { confidence = confidence === n ? null : n; sbtns.forEach((x, j) => x.setAttribute('aria-pressed', String(confidence === j + 1))); saveDraft(); });
      return b;
    });
    scale.append(...sbtns, h('span', { class: 'et-scale-key', text: '1 = not yet     5 = confident' }));
    const noteIn = h('input', { type: 'text', class: 'et-note', maxlength: '500', 'aria-label': 'One thing I still want to check', placeholder: 'One thing I still want to check…', value: note });
    noteIn.addEventListener('input', () => { note = noteIn.value; saveDraft(); });
    refl.append(scale, noteIn);
    body.append(refl);
    sheet.append(body);

    progressEl = h('span', { class: 'et-progress' });
    const err = h('span', { class: 'et-error', role: 'alert' });
    submitBtn = h('button', { type: 'button', class: 'et-btn', text: MODE === 'preview' ? 'Submit (preview only)' : 'Submit my answers', disabled: MODE === 'preview' });
    submitBtn.addEventListener('click', () => submit(err));
    sheet.append(h('div', { class: 'et-foot' }, progressEl, err, submitBtn));
    liveRegion = h('div', { class: 'sr-only', 'aria-live': 'polite', style: 'position:absolute;left:-9999px' });
    sheet.append(liveRegion);
    root.replaceChildren(sheet);
    changed();
  }

  async function submit(errEl) {
    if (submitting || MODE !== 'student') return;
    const unanswered = payload.questions.filter((q) => !isAnswered(q)).length;
    if (unanswered && !window.confirm('You haven’t answered ' + unanswered + (unanswered === 1 ? ' question' : ' questions') + '. Submit anyway?')) return;
    submitting = true; submitBtn.disabled = true; submitBtn.textContent = 'Submitting…'; errEl.textContent = '';
    try {
      payload = await api(cfg.submitUrl, 'POST', { answers, confidence, note });
      try { sessionStorage.removeItem(draftKey()); } catch (e) { /* ignore */ }
      window.scrollTo({ top: 0 });
      drawResult();
      pollWhilePending();
    } catch (e) {
      errEl.textContent = e.message; submitBtn.disabled = false; submitBtn.textContent = 'Submit my answers';
    } finally { submitting = false; }
  }

  // ------------------------------------------------------------------ results screen
  function reviewBody(rq, reveal) {
    const r = rq.review;
    const wrap = h('div', { class: 'et-review' });
    const mark = (ok) => h('span', { class: 'et-mark ' + (ok ? 'ok' : 'bad'), 'aria-label': ok ? 'Correct' : 'Incorrect', text: ok ? '✓' : '✗' });
    const rowCls = (ok) => 'et-review-row ' + (ok ? 'et-row-ok' : 'et-row-bad');
    switch (rq.qtype) {
      case 'mcq':
        r.options.forEach((text, i) => {
          const isChosen = r.chosen === i, isCorrect = reveal && r.correct === i;
          const cls = isCorrect ? 'et-row-ok' : (isChosen ? 'et-row-bad' : '');
          wrap.append(h('div', { class: 'et-review-row ' + cls }, h('span', { class: 'et-mark ' + (isCorrect ? 'ok' : 'bad'), text: isCorrect ? '✓' : (isChosen ? '✗' : '') }),
            h('span', { text: letter(i) + '  ' + text }), isChosen ? h('span', { class: 'et-answer-line', text: 'Your answer' }) : null));
        });
        break;
      case 'truefalse':
        r.rows.forEach((row) => wrap.append(h('div', { class: rowCls(row.ok) }, mark(row.ok), h('span', { text: row.text }),
          h('span', { class: 'et-answer-line' }, 'You said: ' + (row.chosen === null ? 'no answer' : (row.chosen ? 'True' : 'False')),
            reveal && !row.ok ? h('span', null, '  ·  Correct: ', h('b', { text: row.answer ? 'True' : 'False' })) : null))));
        break;
      case 'fill':
        r.rows.forEach((row) => wrap.append(h('div', { class: 'et-review-row' }, h('span', { text: row.text }),
          row.given.map((g, i) => h('span', { class: 'et-answer-line' }, mark(row.ok[i]), ' Blank ' + (i + 1) + ': ' + (g || 'no answer'),
            reveal && !row.ok[i] ? h('span', null, '  ·  Answer: ', h('b', { text: row.answers[i] })) : null)))));
        break;
      case 'match':
        r.rows.forEach((row) => wrap.append(h('div', { class: rowCls(row.ok) }, mark(row.ok), h('b', { text: row.left }), h('span', { text: '→ ' + (row.chosen || 'no answer') }),
          reveal && !row.ok ? h('span', { class: 'et-answer-line' }, 'Correct: ', h('b', { text: row.answer })) : null)));
        break;
      case 'order':
        r.rows.forEach((row, i) => wrap.append(h('div', { class: rowCls(row.ok) }, mark(row.ok), h('span', { text: (i + 1) + '.  ' + (row.text || 'no answer') }),
          reveal && !row.ok ? h('span', { class: 'et-answer-line' }, 'Correct: ', h('b', { text: row.answer })) : null)));
        break;
      default:
        wrap.append(h('div', { class: 'et-written' + (r.answer ? '' : ' empty'), text: r.answer || 'No answer was given.' }));
    }
    return wrap;
  }

  function drawResult() {
    const p = payload;
    const pending = p.written_pending > 0;
    const sheet = h('div', { class: 'et-sheet' });
    sheet.append(...header(p, pending ? 'SCORE SO FAR' : 'SCORE', num(p.total_awarded) + ' / ' + num(p.total_possible)));
    if (MODE === 'teacher' && p.attempt.version && p.ticket.version && p.attempt.version !== p.ticket.version) {
      sheet.append(h('div', { class: 'et-banner', text: 'This attempt was taken on version ' + p.attempt.version + ' of the ticket (it is now on version ' + p.ticket.version + '). It shows the questions and answers exactly as this student saw them.' }));
    }
    const body = h('div', { class: 'et-body' });
    p.questions.forEach((rq, i) => {
      const awarded = rq.marks_awarded;
      let badge;
      if (awarded === null) badge = h('span', { class: 'et-status' }, h('span', { class: 'et-spin', 'aria-hidden': 'true' }), 'Marking…');
      else badge = h('span', { class: 'et-result-badge' + (awarded >= rq.marks ? ' full' : (awarded <= 0 ? ' zero' : '')), text: num(awarded) + ' / ' + num(rq.marks) });
      const sec = panel(rq, i, badge);
      sec.append(reviewBody(rq, p.reveal));
      if (rq.feedback && (rq.qtype === 'short' || rq.qtype === 'explain')) {
        const who = rq.marked_by === 'teacher' ? 'Teacher feedback' : (rq.marked_by === 'ai' ? 'AI feedback' : 'Feedback');
        sec.append(h('div', { class: 'et-feedback' }, h('span', { class: 'et-fb-title', text: who }), rq.feedback));
      } else if (rq.feedback && rq.qtype !== 'short') {
        // objective questions: a one-word verdict is already shown by the badge
      }
      if (p.reveal && (rq.qtype === 'short' || rq.qtype === 'explain') && (rq.review.model_answer || (rq.review.marking_points || []).length)) {
        const m = h('div', { class: 'et-model' });
        if (rq.review.model_answer) m.append(h('b', { text: 'Model answer: ' }), rq.review.model_answer);
        if ((rq.review.marking_points || []).length) m.append(h('ul', null, rq.review.marking_points.map((x) => h('li', { text: x }))));
        sec.append(m);
      }
      if (rq.status === 'needs_review' && MODE === 'teacher') sec.append(h('span', { class: 'et-flag', text: 'Needs your marking' }));
      if (rq.low_confidence && MODE === 'teacher') sec.append(h('span', { class: 'et-flag', text: 'AI was unsure: worth a look' }));
      if (MODE === 'teacher') sec.append(overrideBox(rq));
      body.append(sec);
    });
    if (p.confidence || p.reflection_note) {
      const refl = h('section', { class: 'et-q et-reflect' });
      refl.append(h('div', { class: 'et-q-head' }, h('span', { class: 'et-pill', text: 'Reflection' })),
        h('p', { class: 'et-q-text', text: 'Confidence: ' + (p.confidence ? p.confidence + ' out of 5' : 'not given') }));
      if (p.reflection_note) refl.append(h('div', { class: 'et-written', text: p.reflection_note }));
      body.append(refl);
    }
    sheet.append(body);

    const foot = h('div', { class: 'et-foot' });
    if (pending) foot.append(h('span', { class: 'et-status', role: 'status' }, h('span', { class: 'et-spin', 'aria-hidden': 'true' }), 'Your written answers are being marked…'));
    else foot.append(h('span', { class: 'et-progress', text: MODE === 'student' ? 'Well done for finishing. Check the feedback above.' : '' }));
    if (MODE === 'student') {
      foot.append(h('a', { class: 'et-btn ghost', href: cfg.listUrl, text: 'Back to exit tickets' }));
      if (p.ticket.allow_retries) {
        foot.append(h('form', { method: 'post', action: cfg.startUrl, style: 'display:inline' },
          h('input', { type: 'hidden', name: 'csrf_token', value: cfg.csrf }), h('button', { type: 'submit', class: 'et-btn', text: 'Try again' })));
      }
    } else {
      foot.append(h('a', { class: 'et-btn ghost', href: cfg.listUrl, text: 'Back to results' }));
      const re = h('button', { type: 'button', class: 'et-btn', text: 'Re-mark written answers with AI' });
      re.addEventListener('click', async () => {
        re.disabled = true; re.textContent = 'Queued…';
        try { await api(cfg.remarkUrl, 'POST'); await sleep(1500); payload = await api(cfg.apiUrl); drawResult(); pollWhilePending(); }
        catch (e) { re.textContent = e.message; }
      });
      foot.append(re);
    }
    sheet.append(foot);
    liveRegion = h('div', { style: 'position:absolute;left:-9999px', 'aria-live': 'polite' });
    sheet.append(liveRegion);
    root.replaceChildren(sheet);
  }

  function overrideBox(rq) {
    const marks = h('input', { type: 'number', min: '0', max: String(rq.marks), step: '0.5', value: rq.marks_awarded === null ? '' : String(rq.marks_awarded), 'aria-label': 'Marks' });
    const fb = h('input', { type: 'text', maxlength: '800', placeholder: 'Optional feedback for the student', value: rq.marked_by === 'teacher' ? (rq.feedback || '') : '', 'aria-label': 'Feedback' });
    const msg = h('span', { class: 'et-status' });
    const save = h('button', { type: 'button', class: 'et-btn ghost', style: 'padding:.4rem .9rem', text: 'Save mark' });
    save.addEventListener('click', async () => {
      msg.textContent = 'Saving…';
      try {
        await api(cfg.overrideBase + rq.answer_id + '/override', 'POST', { marks: Number(marks.value), feedback: fb.value });
        payload = await api(cfg.apiUrl); drawResult();
      } catch (e) { msg.textContent = e.message; }
    });
    return h('div', { class: 'et-override' }, h('label', null, 'Marks (out of ' + num(rq.marks) + ')', marks), h('label', { style: 'flex:1' }, 'Feedback', fb), save, msg);
  }

  async function pollWhilePending() {
    if (MODE === 'preview') return;
    for (let i = 0; i < 30 && payload && payload.state === 'submitted' && payload.written_pending > 0; i++) {
      await sleep(2500);
      try { payload = await api(cfg.apiUrl); } catch (e) { return; }
      drawResult();
    }
  }

  // ------------------------------------------------------------------ start
  async function start() {
    root.replaceChildren(h('div', { class: 'et-sheet' }, h('div', { class: 'et-loading', text: 'Loading…' })));
    try {
      payload = MODE === 'preview' ? cfg.previewPayload : await api(cfg.apiUrl);
    } catch (e) {
      root.replaceChildren(h('div', { class: 'et-sheet' }, h('div', { class: 'et-loading', text: e.message })));
      return;
    }
    if (payload.state === 'in_progress') { loadDraft(); drawAnswering(); }
    else { drawResult(); if (MODE !== 'teacher') pollWhilePending(); }
  }
  start();
})();
