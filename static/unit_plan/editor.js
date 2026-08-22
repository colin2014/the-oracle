// ---------- In-browser content editor ----------
// Lets a teacher (window.CAN_EDIT === true) edit week/topic content and resources from the
// page, saving straight to the Oracle backend (/unit-plan/api/...). Students get the same
// resource-viewing UI (renderResourcesPane) but with no upload/edit affordances.
(function () {
  // ---------- status toast ----------
  function toast(message, isError) {
    var el = document.getElementById("editor-toast");
    if (!el) {
      el = document.createElement("div");
      el.id = "editor-toast";
      document.body.appendChild(el);
    }
    el.textContent = message;
    el.className = "editor-toast show" + (isError ? " error" : "");
    clearTimeout(el._t);
    el._t = setTimeout(function () { el.classList.remove("show"); }, 4200);
  }

  function itemRef(item) {
    return item.week !== undefined ? item.week : item.id;
  }

  function fullscreenElement() {
    return document.fullscreenElement || document.webkitFullscreenElement || document.mozFullScreenElement || document.msFullscreenElement || null;
  }

  function requestFullscreenOn(el) {
    var req = el.requestFullscreen || el.webkitRequestFullscreen || el.mozRequestFullScreen || el.msRequestFullscreen;
    if (req) req.call(el);
  }

  function exitFullscreen() {
    var exit = document.exitFullscreen || document.webkitExitFullscreen || document.mozCancelFullScreen || document.msExitFullscreen;
    if (exit) exit.call(document);
  }

  // Track fullscreen state off the same event the browser fires when Escape exits it,
  // rather than re-reading document.fullscreenElement synchronously at click time.
  var currentlyFullscreen = false;
  ["fullscreenchange", "webkitfullscreenchange", "mozfullscreenchange", "MSFullscreenChange"].forEach(function (evt) {
    document.addEventListener(evt, function () { currentlyFullscreen = !!fullscreenElement(); });
  });

  // Toggles fullscreen on `el` — if anything (including a different element) is already
  // fullscreen, this exits it instead of silently failing to re-request.
  function toggleFullscreenOn(el) {
    if (currentlyFullscreen || fullscreenElement()) exitFullscreen();
    else requestFullscreenOn(el);
  }

  // ---------- save current in-memory data back to the server ----------
  async function saveDataFile() {
    var ctx = window.__editorCtx;
    if (!ctx) return;
    try {
      var res;
      if (ctx.dataKey === "grade12") {
        res = await fetch("/unit-plan/api/grade12", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ topics: GRADE12_TOPICS, plan: GRADE12_EXAM_PLAN })
        });
      } else {
        res = await fetch("/unit-plan/api/semester/" + ctx.dataKey, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ weeks: ctx.sem.weeks })
        });
      }
      if (!res.ok) throw new Error("Server returned " + res.status);
      toast("Saved.");
    } catch (e) {
      toast("Save failed: " + (e && e.message ? e.message : e), true);
    }
  }

  // ---------- edit form (week detail) ----------
  function esc(v) { return typeof escapeHtml === "function" ? escapeHtml(v) : String(v == null ? "" : v); }

  function textField(id, label, value, placeholder) {
    return '<label class="ef-field"><span>' + esc(label) + '</span>' +
      '<input type="text" id="' + id + '" value="' + esc(value || "") + '"' +
      (placeholder ? ' placeholder="' + esc(placeholder) + '"' : "") + " /></label>";
  }

  function areaField(id, label, value, rows) {
    return '<label class="ef-field"><span>' + esc(label) + '</span>' +
      '<textarea id="' + id + '" rows="' + (rows || 3) + '">' + esc(value || "") + "</textarea></label>";
  }

  function listField(id, label, items, rows) {
    var value = (items || []).join("\n");
    return '<label class="ef-field"><span>' + esc(label) + ' <em>(one per line)</em></span>' +
      '<textarea id="' + id + '" rows="' + (rows || 4) + '">' + esc(value) + "</textarea></label>";
  }

  function checkboxField(id, label, checked) {
    return '<label class="ef-checkbox"><input type="checkbox" id="' + id + '"' + (checked ? " checked" : "") + " /> " + esc(label) + "</label>";
  }

  function detailFormHTML(d) {
    return (
      '<div id="ef-detail-fields">' +
      areaField("ef-d-bigIdea", "Detail: big idea", d.bigIdea, 2) +
      textField("ef-d-syllabusLinks", "Syllabus links", d.syllabusLinks) +
      listField("ef-d-learningObjectives", "Learning objectives", d.learningObjectives) +
      areaField("ef-d-keyVocabulary", "Key vocabulary", d.keyVocabulary, 2) +
      textField("ef-d-commandTerms", "Command terms", d.commandTerms) +
      listField("ef-d-formativeAssessment", "Formative assessment", d.formativeAssessment) +
      areaField("ef-d-summativeAssessment", "Summative assessment", d.summativeAssessment, 2) +
      areaField("ef-d-resources", "Resources", d.resources, 2) +
      listField("ef-d-atl", "Approaches to Learning (ATL)", d.atl) +
      listField("ef-d-lesson1", "Lesson 1", d.lesson1) +
      listField("ef-d-lesson2", "Lesson 2", d.lesson2) +
      listField("ef-d-differentiation", "Differentiation", d.differentiation) +
      listField("ef-d-iaTok", "Links to IA / TOK", d.iaTok) +
      "</div>"
    );
  }

  function renderEditForm(weekNo) {
    var ctx = window.__editorCtx;
    if (!ctx) return;
    var sem = ctx.sem;
    var idx = sem.weeks.findIndex(function (x) { return x.week === weekNo; });
    if (idx === -1) return;
    var w = sem.weeks[idx];
    var modal = document.getElementById("modal-body");

    var html = "";
    html += '<div class="m-week">Editing Week ' + esc(w.week) + " · " + esc(sem.title) + "</div>";
    html += "<h2>Edit week " + esc(w.week) + "</h2>";
    html += '<form id="ef-form" class="edit-form">';
    html += checkboxField("ef-isBreak", "This is a break / non-teaching week", !!w.isBreak);
    html += checkboxField("ef-isExam", "Mark as exam week (styles the card red)", !!w.isExam);
    html += textField("ef-topic", "Topic", w.topic);
    html += textField("ef-calendarDates", "Calendar dates", w.calendarDates);
    html += textField("ef-contentFocus", "Content focus", w.contentFocus);
    html += textField("ef-hl", "HL focus (leave blank if none)", w.hl);
    html += textField("ef-sl", "SL focus (leave blank if none)", w.sl);
    html += textField("ef-syllabus", "Syllabus tag (short form, e.g. A4.1)", w.syllabus);
    html += areaField("ef-bigIdea", "Big idea (summary)", w.bigIdea, 2);
    html += listField("ef-objectives", "Objectives (summary list)", w.objectives);
    html += areaField("ef-assessment", "Assessment (summary)", w.assessment, 2);
    html += areaField("ef-note", "Note (shown as a callout, optional)", w.note, 2);
    html += areaField("ef-mergedNote", "Merged-week note (optional)", w.mergedNote, 2);

    html += '<fieldset class="ef-fieldset"><legend>Full lesson plan</legend>';
    if (w.detail) {
      html += detailFormHTML(w.detail);
    } else {
      html += '<p class="ef-hint">This week doesn\'t have a full lesson plan yet.</p>';
      html += '<button type="button" id="ef-add-detail" class="ef-btn">+ Add full lesson plan</button>';
    }
    html += "</fieldset>";

    html += '<div class="ef-actions">' +
      '<button type="submit" class="ef-btn primary">💾 Save changes</button>' +
      '<button type="button" id="ef-cancel" class="ef-btn">Cancel</button>' +
      "</div>";
    html += "</form>";

    modal.innerHTML = html;

    var addDetailBtn = document.getElementById("ef-add-detail");
    if (addDetailBtn) {
      addDetailBtn.addEventListener("click", function () {
        w.detail = {
          bigIdea: w.bigIdea || "",
          syllabusLinks: "",
          learningObjectives: [],
          keyVocabulary: "",
          commandTerms: "",
          formativeAssessment: [],
          summativeAssessment: "",
          resources: "",
          atl: [],
          lesson1: [],
          lesson2: [],
          differentiation: [],
          iaTok: []
        };
        renderEditForm(weekNo);
      });
    }

    document.getElementById("ef-cancel").addEventListener("click", function () {
      openWeekModal(sem, weekNo);
    });

    document.getElementById("ef-form").addEventListener("submit", function (e) {
      e.preventDefault();
      saveWeekEdits(weekNo);
    });
  }

  function linesToList(value) {
    return (value || "")
      .split("\n")
      .map(function (s) { return s.trim(); })
      .filter(Boolean);
  }

  function setOrDelete(obj, key, value) {
    if (value === "" || value == null) delete obj[key];
    else obj[key] = value;
  }

  function saveWeekEdits(weekNo) {
    var ctx = window.__editorCtx;
    var sem = ctx.sem;
    var idx = sem.weeks.findIndex(function (x) { return x.week === weekNo; });
    if (idx === -1) return;
    var w = sem.weeks[idx];

    w.isBreak = document.getElementById("ef-isBreak").checked;
    var isExam = document.getElementById("ef-isExam").checked;
    if (isExam) w.isExam = true; else delete w.isExam;

    w.topic = document.getElementById("ef-topic").value.trim();
    setOrDelete(w, "calendarDates", document.getElementById("ef-calendarDates").value.trim());
    setOrDelete(w, "contentFocus", document.getElementById("ef-contentFocus").value.trim());
    setOrDelete(w, "hl", document.getElementById("ef-hl").value.trim());
    setOrDelete(w, "sl", document.getElementById("ef-sl").value.trim());
    setOrDelete(w, "syllabus", document.getElementById("ef-syllabus").value.trim());
    setOrDelete(w, "bigIdea", document.getElementById("ef-bigIdea").value.trim());
    setOrDelete(w, "assessment", document.getElementById("ef-assessment").value.trim());
    setOrDelete(w, "note", document.getElementById("ef-note").value.trim());
    setOrDelete(w, "mergedNote", document.getElementById("ef-mergedNote").value.trim());

    var objectives = linesToList(document.getElementById("ef-objectives").value);
    if (objectives.length) w.objectives = objectives; else delete w.objectives;

    if (w.detail && document.getElementById("ef-d-bigIdea")) {
      var d = w.detail;
      d.bigIdea = document.getElementById("ef-d-bigIdea").value.trim();
      d.syllabusLinks = document.getElementById("ef-d-syllabusLinks").value.trim();
      d.learningObjectives = linesToList(document.getElementById("ef-d-learningObjectives").value);
      d.keyVocabulary = document.getElementById("ef-d-keyVocabulary").value.trim();
      d.commandTerms = document.getElementById("ef-d-commandTerms").value.trim();
      d.formativeAssessment = linesToList(document.getElementById("ef-d-formativeAssessment").value);
      d.summativeAssessment = document.getElementById("ef-d-summativeAssessment").value.trim();
      d.resources = document.getElementById("ef-d-resources").value.trim();
      d.atl = linesToList(document.getElementById("ef-d-atl").value);
      d.lesson1 = linesToList(document.getElementById("ef-d-lesson1").value);
      d.lesson2 = linesToList(document.getElementById("ef-d-lesson2").value);
      d.differentiation = linesToList(document.getElementById("ef-d-differentiation").value);
      d.iaTok = linesToList(document.getElementById("ef-d-iaTok").value);
    }

    persistAndReturn(weekNo);
  }

  async function persistAndReturn(weekNo) {
    await saveDataFile();
    var ctx = window.__editorCtx;
    if (ctx && ctx.refresh) ctx.refresh();
    openWeekModal(ctx.sem, weekNo);
  }

  // ---------- resources: naming/formatting helpers ----------
  function formatBytes(n) {
    if (n === undefined || n === null) return "";
    if (n < 1024) return n + " B";
    if (n < 1024 * 1024) return (n / 1024).toFixed(1) + " KB";
    return (n / (1024 * 1024)).toFixed(1) + " MB";
  }

  function formatDate(iso) {
    try {
      return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
    } catch (e) {
      return "";
    }
  }

  function extIcon(fileName) {
    var ext = (fileName || "").split(".").pop().toLowerCase();
    var map = {
      ppt: "📊", pptx: "📊", key: "📊", odp: "📊",
      pdf: "📄", doc: "📝", docx: "📝", txt: "📝", rtf: "📝",
      xls: "📈", xlsx: "📈", csv: "📈",
      mp4: "🎬", mov: "🎬", avi: "🎬", webm: "🎬", mkv: "🎬",
      mp3: "🎵", wav: "🎵", m4a: "🎵",
      png: "🖼️", jpg: "🖼️", jpeg: "🖼️", gif: "🖼️", svg: "🖼️", webp: "🖼️",
      zip: "🗜️", rar: "🗜️", "7z": "🗜️"
    };
    return map[ext] || "📎";
  }

  function linkIcon(linkType) {
    var map = { video: "🎬", slides: "📊", document: "📄", link: "🔗" };
    return map[linkType] || "🔗";
  }

  // ---------- resources: inline preview support ----------
  function getEmbedUrl(url) {
    try {
      var u = new URL(url);
      var host = u.hostname.replace(/^www\.|^m\./, "");
      if (host === "youtube.com") {
        if (u.pathname === "/watch") {
          var id = u.searchParams.get("v");
          if (id) return "https://www.youtube.com/embed/" + id;
        }
        var embedMatch = u.pathname.match(/^\/embed\/([\w-]+)/);
        if (embedMatch) return "https://www.youtube.com/embed/" + embedMatch[1];
        var shortsMatch = u.pathname.match(/^\/shorts\/([\w-]+)/);
        if (shortsMatch) return "https://www.youtube.com/embed/" + shortsMatch[1];
      }
      if (host === "youtu.be") {
        var id2 = u.pathname.slice(1);
        if (id2) return "https://www.youtube.com/embed/" + id2;
      }
      if (host === "vimeo.com") {
        var m = u.pathname.match(/\/(\d+)/);
        if (m) return "https://player.vimeo.com/video/" + m[1];
      }
    } catch (e) {
      // not a valid absolute URL — no embed possible
    }
    return null;
  }

  var VIDEO_EXTS = ["mp4", "webm", "mov", "ogg", "ogv", "m4v"];
  var AUDIO_EXTS = ["mp3", "wav", "m4a"];
  var IMAGE_EXTS = ["png", "jpg", "jpeg", "gif", "webp", "svg"];
  var SLIDE_EXTS = ["ppt", "pptx", "key", "odp"];

  function getPreviewInfo(m) {
    if (m.kind === "file") {
      var ext = (m.fileName || "").split(".").pop().toLowerCase();
      if (m.slides && m.slides.count) return { type: "slides", slides: m.slides };
      if (m.previewPath && SLIDE_EXTS.indexOf(ext) !== -1) return { type: "pdf", src: m.previewPath };
      if (VIDEO_EXTS.indexOf(ext) !== -1) return { type: "video", src: m.path };
      if (ext === "pdf") return { type: "pdf", src: m.path };
      if (IMAGE_EXTS.indexOf(ext) !== -1) return { type: "image", src: m.path };
      if (AUDIO_EXTS.indexOf(ext) !== -1) return { type: "audio", src: m.path };
      return null;
    }
    if (m.kind === "link") {
      var embed = getEmbedUrl(m.url);
      if (embed) return { type: "embed", src: embed };
      if (/\.pdf(\?|#|$)/i.test(m.url)) return { type: "pdf", src: m.url };
      return null;
    }
    return null;
  }

  function slideUrl(slides, n) {
    return slides.urlPattern.replace("{n}", n);
  }

  function previewHTML(info) {
    if (info.type === "video") return '<video controls preload="metadata" src="' + esc(info.src) + '"></video>';
    if (info.type === "audio") return '<audio controls src="' + esc(info.src) + '"></audio>';
    if (info.type === "image") return '<img src="' + esc(info.src) + '" alt="" />';
    if (info.type === "pdf") return '<iframe src="' + esc(info.src) + '" title="PDF preview"></iframe>';
    if (info.type === "embed") return '<iframe src="' + esc(info.src) + '" title="Video preview" allowfullscreen></iframe>';
    if (info.type === "slides") {
      return (
        '<div class="slide-viewer" tabindex="0">' +
        '<div class="slide-stage">' +
        '<div class="slide-nav-zone prev">‹</div>' +
        '<img class="slide-img" src="' + esc(slideUrl(info.slides, 1)) + '" alt="Slide 1" />' +
        '<div class="slide-nav-zone next">›</div>' +
        "</div>" +
        '<div class="slide-controls">' +
        '<button type="button" class="slide-prev" title="Previous slide">‹</button>' +
        '<span class="slide-counter">1 / ' + info.slides.count + "</span>" +
        '<button type="button" class="slide-next" title="Next slide">›</button>' +
        '<button type="button" class="slide-fullscreen" title="Fullscreen">⛶</button>' +
        "</div>" +
        "</div>"
      );
    }
    return "";
  }

  // Wires prev/next/keyboard/click-zone navigation for a just-inserted .slide-viewer.
  // Returns a cleanup function that removes the document-level keydown listener —
  // callers must invoke it when the viewer is hidden/removed.
  function wireSlideViewer(root, slides) {
    var viewer = root.querySelector(".slide-viewer");
    if (!viewer) return function () {};
    var img = viewer.querySelector(".slide-img");
    var counter = viewer.querySelector(".slide-counter");
    var current = 1;

    function show(n) {
      current = Math.max(1, Math.min(slides.count, n));
      img.src = slideUrl(slides, current);
      img.alt = "Slide " + current;
      counter.textContent = current + " / " + slides.count;
    }

    function next() { show(current + 1); }
    function prev() { show(current - 1); }

    viewer.querySelector(".slide-next").addEventListener("click", function (e) { e.stopPropagation(); next(); });
    viewer.querySelector(".slide-prev").addEventListener("click", function (e) { e.stopPropagation(); prev(); });
    viewer.querySelector(".slide-nav-zone.next").addEventListener("click", next);
    viewer.querySelector(".slide-nav-zone.prev").addEventListener("click", prev);
    viewer.querySelector(".slide-fullscreen").addEventListener("click", function (e) {
      e.stopPropagation();
      toggleFullscreenOn(viewer);
    });

    function onKeydown(e) {
      if (e.key === "ArrowRight" || e.key === " ") { e.preventDefault(); next(); }
      else if (e.key === "ArrowLeft") { e.preventDefault(); prev(); }
    }
    viewer.addEventListener("keydown", onKeydown);
    viewer.focus();

    return function () { viewer.removeEventListener("keydown", onKeydown); };
  }

  // ---------- resources: talk to the server ----------
  async function addFileMaterial(file, bucketKey, item, onChange) {
    try {
      var form = new FormData();
      form.append("bucketKey", bucketKey);
      form.append("itemRef", itemRef(item));
      form.append("file", file);
      var res = await fetch("/unit-plan/api/materials/file", { method: "POST", body: form });
      if (!res.ok) throw new Error((await res.json().catch(function () { return {}; })).error || ("Server returned " + res.status));
      var data = await res.json();
      item.materials = data.materials;
      onChange();
    } catch (e) {
      toast('Couldn\'t save "' + file.name + '": ' + (e && e.message ? e.message : e), true);
    }
  }

  async function handleFiles(fileList, bucketKey, item, onChange) {
    var files = Array.prototype.slice.call(fileList || []);
    if (!files.length) return;
    for (var i = 0; i < files.length; i++) {
      await addFileMaterial(files[i], bucketKey, item, onChange);
    }
    var ctx = window.__editorCtx;
    if (ctx && ctx.refresh) ctx.refresh();
  }

  async function addLinkMaterial(bucketKey, item, label, url, linkType, onChange) {
    try {
      var res = await fetch("/unit-plan/api/materials/link", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ bucketKey: bucketKey, itemRef: itemRef(item), label: label, url: url, linkType: linkType })
      });
      if (!res.ok) throw new Error("Server returned " + res.status);
      var data = await res.json();
      item.materials = data.materials;
      var ctx = window.__editorCtx;
      if (ctx && ctx.refresh) ctx.refresh();
      onChange();
    } catch (e) {
      toast("Couldn't add the link: " + (e && e.message ? e.message : e), true);
    }
  }

  async function removeMaterial(bucketKey, item, id, onChange) {
    try {
      var res = await fetch("/unit-plan/api/materials/" + encodeURIComponent(bucketKey) + "/" + encodeURIComponent(itemRef(item)) + "/" + encodeURIComponent(id), {
        method: "DELETE"
      });
      if (!res.ok) throw new Error("Server returned " + res.status);
      var data = await res.json();
      item.materials = data.materials;
      var ctx = window.__editorCtx;
      if (ctx && ctx.refresh) ctx.refresh();
      onChange();
    } catch (e) {
      toast("Couldn't remove that resource: " + (e && e.message ? e.message : e), true);
    }
  }

  function materialItemHTML(m) {
    var icon = m.kind === "file" ? extIcon(m.fileName) : m.kind === "reading" ? "📖" : linkIcon(m.linkType);
    var href = m.kind === "file" ? m.path : m.url;
    var ext = m.kind === "file" ? (m.fileName || "").split(".").pop().toLowerCase() : null;
    var meta;
    if (m.kind === "file") {
      meta = formatBytes(m.sizeBytes) + " · " + formatDate(m.addedAt) +
        (SLIDE_EXTS.indexOf(ext) !== -1
          ? (m.slides ? " · presentation mode (" + m.slides.count + " slides)" : m.previewPath ? " · viewable inline" : " · opens in your slides app")
          : "");
    } else if (m.kind === "reading") {
      meta = "From the course textbook" + (m.readingTimeMinutes ? " · " + m.readingTimeMinutes + " min read" : "");
    } else {
      meta = m.url + " · " + formatDate(m.addedAt);
    }
    var preview = getPreviewInfo(m);
    var removable = window.CAN_EDIT && m.kind !== "reading";
    // When a preview is available, clicking the title opens it right there (one click,
    // no new tab/app) instead of navigating to the raw file. The raw file is still
    // reachable via the small download icon for file-kind materials.
    var labelHtml = preview
      ? '<a class="res-label" href="javascript:void(0)" data-preview-for="' + esc(m.id) + '">' + esc(m.label) + "</a>"
      : '<a class="res-label" href="' + esc(href) + '" target="_blank" rel="noopener">' + esc(m.label) + "</a>";
    // Reading entries point at the real textbook page, which may already have its own
    // quiz (see quiz_routes.py) — link straight to it instead of building a second one.
    var quizLine = "";
    if (m.kind === "reading" && m.quizUrl) {
      var quizText = m.quizCount
        ? "📝 " + m.quizCount + " quiz question" + (m.quizCount === 1 ? "" : "s")
        : "📝 No quiz yet";
      quizLine = '<div class="res-quiz-line"><a href="' + esc(m.quizUrl) + '" target="_blank" rel="noopener">' + quizText + "</a>" +
        (window.CAN_EDIT && m.assignUrl
          ? ' · <a href="' + esc(m.assignUrl) + '" target="_blank" rel="noopener">🎯 Assign to class</a>'
          : "") +
        "</div>";
    }
    return (
      '<div class="res-item-wrap">' +
      '<div class="res-item">' +
      '<div class="res-icon">' + icon + "</div>" +
      '<div class="res-info">' +
      labelHtml +
      '<div class="res-meta">' + esc(meta) + "</div>" +
      quizLine +
      "</div>" +
      (preview ? '<button type="button" class="res-preview-toggle" data-id="' + esc(m.id) + '">👁 View</button>' : "") +
      (m.kind === "file" ? '<a class="res-download" href="' + esc(href) + '" target="_blank" rel="noopener" title="Download original">⬇</a>' : "") +
      (removable ? '<button type="button" class="res-remove" data-id="' + esc(m.id) + '" title="Remove">✕</button>' : "") +
      "</div>" +
      (preview ? '<div class="res-preview" id="res-preview-' + esc(m.id) + '" hidden></div>' : "") +
      "</div>"
    );
  }

  function renderResourcesPane(paneEl, bucketKey, item, onChange) {
    // Auto-linked textbook reading lives in its own "Reading" tab now (see
    // renderReadingPane) — this pane is just the teacher's manually-added files/links.
    var materials = (item.materials || []).filter(function (m) { return m.kind !== "reading"; });

    var html = "";
    if (window.CAN_EDIT) {
      html += '<div class="res-dropzone" id="res-dropzone">📁 Drag files here or click to upload (slides, PDFs, videos, docs…)' +
        '<input type="file" id="res-file-input" multiple /></div>';
      html += '<div class="res-add-link">' +
        '<select id="res-link-type">' +
        '<option value="link">Link</option>' +
        '<option value="video">Video</option>' +
        '<option value="slides">Slides</option>' +
        '<option value="document">Document</option>' +
        "</select>" +
        '<input type="text" id="res-link-label" placeholder="Label (e.g. Intro slides)" />' +
        '<input type="text" id="res-link-url" placeholder="https://…" />' +
        '<button type="button" id="res-add-link-btn" class="ef-btn">+ Add link</button>' +
        "</div>";
    }
    html += materials.length
      ? '<div class="res-list">' + materials.map(materialItemHTML).join("") + "</div>"
      : '<p class="res-empty">No extra resources added yet.</p>';

    paneEl.innerHTML = html;
    paneEl.hidden = false;

    if (window.CAN_EDIT) {
      var dropzone = document.getElementById("res-dropzone");
      var fileInput = document.getElementById("res-file-input");
      dropzone.addEventListener("click", function () { fileInput.click(); });
      dropzone.addEventListener("dragover", function (e) { e.preventDefault(); dropzone.classList.add("drag-over"); });
      dropzone.addEventListener("dragleave", function () { dropzone.classList.remove("drag-over"); });
      dropzone.addEventListener("drop", function (e) {
        e.preventDefault();
        dropzone.classList.remove("drag-over");
        handleFiles(e.dataTransfer.files, bucketKey, item, onChange);
      });
      fileInput.addEventListener("change", function () {
        handleFiles(fileInput.files, bucketKey, item, onChange);
        fileInput.value = "";
      });

      document.getElementById("res-add-link-btn").addEventListener("click", function () {
        var label = document.getElementById("res-link-label").value.trim();
        var url = document.getElementById("res-link-url").value.trim();
        var linkType = document.getElementById("res-link-type").value;
        if (!url) { toast("Add a URL first.", true); return; }
        if (!/^https?:\/\//i.test(url)) url = "https://" + url;
        addLinkMaterial(bucketKey, item, label || url, url, linkType, onChange);
      });

      paneEl.querySelectorAll(".res-remove").forEach(function (btn) {
        btn.addEventListener("click", function () {
          removeMaterial(bucketKey, item, btn.getAttribute("data-id"), onChange);
        });
      });
    }

    paneEl.querySelectorAll(".res-preview-toggle").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var id = btn.getAttribute("data-id");
        var container = document.getElementById("res-preview-" + id);
        if (!container) return;
        if (!container.hidden) {
          if (container._cleanup) container._cleanup();
          container._cleanup = null;
          container.hidden = true;
          container.innerHTML = "";
          btn.textContent = "👁 View";
          return;
        }
        var m = materials.find(function (x) { return x.id === id; });
        var info = m && getPreviewInfo(m);
        if (!info) return;

        if (info.type === "slides") {
          container.innerHTML = previewHTML(info);
          container._cleanup = wireSlideViewer(container, info.slides);
        } else {
          container.innerHTML =
            '<div class="res-preview-inner">' + previewHTML(info) +
            (info.type !== "audio" ? '<button type="button" class="res-fullscreen-btn" title="Fullscreen">⛶ Fullscreen</button>' : "") +
            "</div>";
          var fsBtn = container.querySelector(".res-fullscreen-btn");
          if (fsBtn) {
            fsBtn.addEventListener("click", function () {
              var media = container.querySelector("iframe, video, img");
              if (media) toggleFullscreenOn(media);
            });
          }
        }

        container.hidden = false;
        btn.textContent = "🙈 Hide";
        container.scrollIntoView({ behavior: "smooth", block: "nearest" });
      });
    });

    // Clicking the title itself does the same thing as the "View" button — one click
    // to see it inline, no navigation away.
    paneEl.querySelectorAll(".res-label[data-preview-for]").forEach(function (a) {
      a.addEventListener("click", function (e) {
        e.preventDefault();
        var btn = paneEl.querySelector('.res-preview-toggle[data-id="' + a.getAttribute("data-preview-for") + '"]');
        if (btn) btn.click();
      });
    });
  }

  // ---------- Reading tab: auto-linked textbook pages + their existing quizzes ----------
  function renderReadingPane(paneEl, item) {
    var readingItems = (item.materials || []).filter(function (m) { return m.kind === "reading"; });
    paneEl.innerHTML = readingItems.length
      ? '<div class="res-list">' + readingItems.map(materialItemHTML).join("") + "</div>"
      : '<p class="res-empty">No linked textbook reading found for this content yet.</p>';
    paneEl.hidden = false;
  }

  // ---------- Vocabulary tab: curated terms + flashcard sets, one block per subtopic ----------
  function flashcardSetItemHTML(s) {
    return (
      '<div class="flashcard-set-item">' +
      '<span class="flashcard-set-icon">🗂️</span>' +
      '<span class="flashcard-set-title">' + esc(s.title) + " <em>(" + s.cardCount + (s.cardCount === 1 ? " card" : " cards") + ")</em></span>" +
      '<a href="/flashcards/' + s.id + '" target="_blank" rel="noopener">Study</a>' +
      (window.CAN_EDIT
        ? ' · <a href="/admin/flashcards/' + s.id + '" target="_blank" rel="noopener">Manage</a>' +
          ' · <a href="/admin/flashcards/' + s.id + '" target="_blank" rel="noopener">🎯 Assign to class</a>'
        : "") +
      "</div>"
    );
  }

  function vocabTopicBlockHTML(m) {
    var html = '<div class="vocab-topic-block">';
    html += '<div class="vocab-topic-header">' + esc(m.label) + "</div>";
    if (m.vocabTerms && m.vocabTerms.length) {
      html += '<div class="vocab-list">' + m.vocabTerms.map(function (t) {
        return '<div class="vocab-term"><strong>' + esc(t.term) + "</strong><span>" + esc(t.definition) + "</span></div>";
      }).join("") + "</div>";
    } else {
      html += '<p class="res-empty">No vocabulary terms found for this page.</p>';
    }
    var sets = m.flashcardSets || [];
    if (sets.length) {
      html += '<div class="flashcard-sets">' + sets.map(flashcardSetItemHTML).join("") + "</div>";
    }
    if (window.CAN_EDIT) {
      html += '<div class="flashcard-actions">' +
        '<button type="button" class="ef-btn flashcard-generate-btn" data-id="' + esc(m.id) + '">✨ Generate with Claude</button>' +
        '<button type="button" class="ef-btn flashcard-addmanual-btn" data-id="' + esc(m.id) + '">+ Add manually</button>' +
        "</div>";
      html += '<div class="flashcard-editor" id="flashcard-editor-' + esc(m.id) + '" hidden></div>';
    }
    html += "</div>";
    return html;
  }

  function renderVocabularyPane(paneEl, bucketKey, item, onChange) {
    var readingItems = (item.materials || []).filter(function (m) { return m.kind === "reading"; });
    var visible = readingItems.filter(function (m) {
      return window.CAN_EDIT || (m.vocabTerms && m.vocabTerms.length) || (m.flashcardSets && m.flashcardSets.length);
    });
    paneEl.innerHTML = visible.length
      ? visible.map(vocabTopicBlockHTML).join("")
      : '<p class="res-empty">No vocabulary found for this content yet.</p>';
    paneEl.hidden = false;

    if (!window.CAN_EDIT) return;

    paneEl.querySelectorAll(".flashcard-generate-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var m = readingItems.find(function (x) { return x.id === btn.getAttribute("data-id"); });
        if (m) openFlashcardEditor(paneEl, bucketKey, item, onChange, m, true);
      });
    });
    paneEl.querySelectorAll(".flashcard-addmanual-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var m = readingItems.find(function (x) { return x.id === btn.getAttribute("data-id"); });
        if (m) openFlashcardEditor(paneEl, bucketKey, item, onChange, m, false);
      });
    });
  }

  async function openFlashcardEditor(paneEl, bucketKey, item, onChange, m, useAI) {
    var container = document.getElementById("flashcard-editor-" + m.id);
    if (!container) return;
    container.hidden = false;
    container.innerHTML = useAI ? '<p class="res-empty">Asking Claude for card ideas…</p>' : "";

    var cards = [];
    if (useAI) {
      try {
        var res = await fetch("/admin/api/flashcards/ai-generate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            book_folder: m.bookFolder,
            page_id: m.pageId,
            count: 10,
            existing_terms: (m.vocabTerms || []).map(function (t) { return t.term; })
          })
        });
        var data = await res.json();
        if (!res.ok) throw new Error(data.error || "Generation failed");
        cards = (data.cards || []).map(function (c) { return { term: c.term, definition: c.definition }; });
      } catch (e) {
        container.innerHTML = '<p class="res-empty">Couldn\'t generate cards: ' + esc(e.message || e) + "</p>" +
          '<button type="button" class="ef-btn fc-retry">Try again</button> ' +
          '<button type="button" class="ef-btn fc-cancel-err">Cancel</button>';
        container.querySelector(".fc-retry").addEventListener("click", function () {
          openFlashcardEditor(paneEl, bucketKey, item, onChange, m, useAI);
        });
        container.querySelector(".fc-cancel-err").addEventListener("click", function () {
          container.hidden = true;
          container.innerHTML = "";
        });
        return;
      }
    }
    if (!cards.length) cards = [{ term: "", definition: "" }];
    renderFlashcardEditor(container, paneEl, bucketKey, item, onChange, m, cards);
  }

  function renderFlashcardEditor(container, paneEl, bucketKey, item, onChange, m, cards) {
    function paint() {
      container.innerHTML =
        '<label class="ef-field"><span>Set title</span><input type="text" class="fc-title" value="' + esc(m.label) + '" /></label>' +
        '<div class="flashcard-editor-rows">' +
        cards.map(function (c, i) {
          return '<div class="flashcard-editor-row" data-i="' + i + '">' +
            '<input type="text" class="fc-term" placeholder="Term" value="' + esc(c.term) + '" />' +
            '<input type="text" class="fc-def" placeholder="Definition" value="' + esc(c.definition) + '" />' +
            '<button type="button" class="fc-remove-row" title="Remove">✕</button>' +
            "</div>";
        }).join("") +
        "</div>" +
        '<div class="flashcard-editor-actions">' +
        '<button type="button" class="ef-btn fc-add-row">+ Add card</button>' +
        '<button type="button" class="ef-btn primary fc-save">💾 Save as flashcard set</button>' +
        '<button type="button" class="ef-btn fc-cancel">Cancel</button>' +
        "</div>";
      wire();
    }

    function syncFromInputs() {
      container.querySelectorAll(".flashcard-editor-row").forEach(function (row, i) {
        cards[i].term = row.querySelector(".fc-term").value;
        cards[i].definition = row.querySelector(".fc-def").value;
      });
    }

    function wire() {
      container.querySelector(".fc-add-row").addEventListener("click", function () {
        syncFromInputs();
        cards.push({ term: "", definition: "" });
        paint();
      });
      container.querySelectorAll(".fc-remove-row").forEach(function (btn) {
        btn.addEventListener("click", function () {
          syncFromInputs();
          var i = parseInt(btn.closest(".flashcard-editor-row").getAttribute("data-i"), 10);
          cards.splice(i, 1);
          if (!cards.length) cards.push({ term: "", definition: "" });
          paint();
        });
      });
      container.querySelector(".fc-cancel").addEventListener("click", function () {
        container.hidden = true;
        container.innerHTML = "";
      });
      container.querySelector(".fc-save").addEventListener("click", async function () {
        syncFromInputs();
        var title = container.querySelector(".fc-title").value.trim() || m.label;
        var cleanCards = cards
          .map(function (c) { return { term: (c.term || "").trim(), definition: (c.definition || "").trim() }; })
          .filter(function (c) { return c.term && c.definition; });
        if (!cleanCards.length) { toast("Add at least one term and definition.", true); return; }
        try {
          var res = await fetch("/admin/api/flashcards", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              title: title,
              book_folder: m.bookFolder,
              card_type: "flashcard",
              cards: cleanCards.map(function (c) { return { page_id: m.pageId, term: c.term, definition: c.definition }; })
            })
          });
          var data = await res.json();
          if (!res.ok) throw new Error(data.error || "Save failed");
          m.flashcardSets = (m.flashcardSets || []).concat([{ id: data.set_id, title: title, cardCount: cleanCards.length }]);
          toast("Flashcard set saved.");
          renderVocabularyPane(paneEl, bucketKey, item, onChange);
        } catch (e) {
          toast("Couldn't save: " + (e.message || e), true);
        }
      });
    }

    paint();
  }

  // ---------- public hooks used by app.js / grade12.js ----------
  window.renderResourcesPane = renderResourcesPane;
  window.renderReadingPane = renderReadingPane;
  window.renderVocabularyPane = renderVocabularyPane;
  window.saveEditorData = saveDataFile;
  window.initEditorUI = function () {};

  if (window.CAN_EDIT) {
    window.startEditWeek = function (weekNo) {
      renderEditForm(weekNo);
    };
  }
})();
