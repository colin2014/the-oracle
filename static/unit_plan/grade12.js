// ---------- Grade 12 syllabus checklist + catch-up plan ----------
// Independent of the calendar-bound Year 2 Sem 1/2 unit plans: this page
// lists every individual syllabus statement (A1.1.1, A1.1.2, ... B4.1.6,
// plus IA and Case Study), lets each be marked done/not done, and lets
// not-done items be dragged into a separate, reorderable "Plan to Exam
// Date" list.
(function () {
  var searchInput = null;
  var draggedId = null;

  var PART_ORDER = ["A1", "A2", "A3", "A4", "B1", "B2", "B3", "B4", "assessment"];

  function topicHay(t) {
    return [t.code, t.statement, t.partLabel].filter(Boolean).join(" ").toLowerCase();
  }

  function statusPillHTML(t) {
    var done = t.status === "done";
    var cls = "g12-status " + (done ? "done" : "not-done");
    var label = (done ? "✓ Done" : "◻ Not done");
    if (!window.CAN_EDIT) {
      return '<span class="' + cls + '">' + label + "</span>";
    }
    return '<button type="button" class="' + cls + '" data-id="' + escapeHtml(t.id) + '">' + label + "</button>";
  }

  function topicCardHTML(t) {
    var inPlan = GRADE12_EXAM_PLAN.indexOf(t.id) !== -1;
    return (
      '<div class="g12-card" draggable="' + (window.CAN_EDIT ? "true" : "false") + '" data-id="' + escapeHtml(t.id) + '">' +
      '<div class="g12-card-top">' +
      statusPillHTML(t) +
      '<span class="badge">' + escapeHtml(t.code) + "</span>" +
      (t.hlOnly ? '<span class="g12-hl-badge">HL only</span>' : "") +
      "</div>" +
      '<div class="g12-card-statement">' + escapeHtml(t.statement) + "</div>" +
      (t.materials && t.materials.length
        ? '<div class="wk-materials">📎 ' + t.materials.length + (t.materials.length === 1 ? " resource" : " resources") + "</div>"
        : "") +
      (inPlan ? '<div class="g12-in-plan">📌 In the exam-prep plan</div>' : "") +
      "</div>"
    );
  }

  function planItemHTML(t) {
    return (
      '<div class="g12-plan-item" draggable="' + (window.CAN_EDIT ? "true" : "false") + '" data-id="' + escapeHtml(t.id) + '">' +
      '<div class="g12-plan-info">' +
      '<span class="badge">' + escapeHtml(t.code) + "</span>" +
      (t.hlOnly ? '<span class="g12-hl-badge">HL</span>' : "") +
      '<div class="g12-plan-title">' + escapeHtml(t.statement) + "</div>" +
      "</div>" +
      (window.CAN_EDIT ? '<button type="button" class="g12-plan-remove" data-id="' + escapeHtml(t.id) + '" title="Remove from plan">✕</button>' : "") +
      "</div>"
    );
  }

  function renderGroupedList(container, items) {
    if (!items.length) {
      container.innerHTML = '<div class="empty-state">Nothing here.</div>';
      return;
    }
    var byPart = {};
    items.forEach(function (t) {
      (byPart[t.part] = byPart[t.part] || []).push(t);
    });
    var html = "";
    PART_ORDER.forEach(function (part) {
      var group = byPart[part];
      if (!group || !group.length) return;
      html += '<div class="g12-group-header">' + escapeHtml(group[0].partLabel) + " (" + group.length + ")</div>";
      html += group.map(topicCardHTML).join("");
    });
    container.innerHTML = html;
  }

  function renderStats(notDoneCount, doneCount) {
    var el = document.getElementById("g12-stats");
    if (!el) return;
    var total = notDoneCount + doneCount;
    var examWeek = null;
    var teachingWeeksLeft = 0;
    if (typeof COURSE_DATA !== "undefined" && COURSE_DATA.year2sem2) {
      examWeek = COURSE_DATA.year2sem2.weeks.find(function (w) { return w.isExam; });
      teachingWeeksLeft = COURSE_DATA.year2sem2.weeks.filter(function (w) { return !w.isBreak && !w.isExam; }).length;
    }
    var examDateText = examWeek ? examWeek.calendarDates.replace(/^From\s+/, "") : "TBC";
    el.innerHTML =
      '<div class="g12-stat"><strong>' + doneCount + " / " + total + "</strong><span>syllabus points done</span></div>" +
      '<div class="g12-stat"><strong>' + examDateText + '</strong><span>IB exams begin</span></div>' +
      '<div class="g12-stat"><strong>' + teachingWeeksLeft + '</strong><span>teaching weeks currently scheduled before then</span></div>';
  }

  function levelFilteredTopics() {
    var level = typeof window.getLevelView === "function" ? window.getLevelView() : "all";
    return level === "SL" ? GRADE12_TOPICS.filter(function (t) { return !t.hlOnly; }) : GRADE12_TOPICS;
  }

  function renderBoard(filter) {
    var notDoneCol = document.getElementById("g12-incomplete");
    var doneCol = document.getElementById("g12-complete");
    var planCol = document.getElementById("g12-plan");
    if (!notDoneCol || !doneCol || !planCol) return;

    var f = (filter || "").toLowerCase().trim();
    var visible = levelFilteredTopics();
    var topics = visible.filter(function (t) { return !f || topicHay(t).indexOf(f) !== -1; });

    var notDone = topics.filter(function (t) { return t.status !== "done"; });
    var done = topics.filter(function (t) { return t.status === "done"; });

    renderGroupedList(notDoneCol, notDone);
    renderGroupedList(doneCol, done);

    var planTopics = GRADE12_EXAM_PLAN
      .map(function (id) { return visible.find(function (t) { return t.id === id; }); })
      .filter(Boolean);
    planCol.innerHTML = planTopics.length
      ? planTopics.map(planItemHTML).join("")
      : '<div class="empty-state">Drag not-done topics here to build the plan up to exam day.</div>';

    wireCardEvents();
    updateCounts(notDone.length, done.length, planTopics.length);
    renderStats(
      visible.filter(function (t) { return t.status !== "done"; }).length,
      visible.filter(function (t) { return t.status === "done"; }).length
    );
  }

  function updateCounts(nNotDone, nDone, nPlan) {
    var el;
    el = document.getElementById("g12-count-incomplete");
    if (el) el.textContent = nNotDone;
    el = document.getElementById("g12-count-complete");
    if (el) el.textContent = nDone;
    el = document.getElementById("g12-count-plan");
    if (el) el.textContent = nPlan;
  }

  function wireCardEvents() {
    if (window.CAN_EDIT) {
      document.querySelectorAll(".g12-status").forEach(function (btn) {
        btn.addEventListener("click", function (e) {
          e.stopPropagation();
          toggleStatus(btn.getAttribute("data-id"));
        });
      });
    }

    document.querySelectorAll(".g12-card").forEach(function (card) {
      card.addEventListener("click", function () {
        openTopicModal(card.getAttribute("data-id"));
      });
      if (window.CAN_EDIT) {
        card.addEventListener("dragstart", function (e) {
          draggedId = card.getAttribute("data-id");
          e.dataTransfer.setData("text/plain", draggedId);
          e.dataTransfer.effectAllowed = "copy";
        });
        card.addEventListener("dragend", function () { draggedId = null; });
      }
    });

    if (window.CAN_EDIT) {
      document.querySelectorAll(".g12-plan-item").forEach(function (item) {
        item.addEventListener("dragstart", function (e) {
          draggedId = item.getAttribute("data-id");
          e.dataTransfer.setData("text/plain", draggedId);
          e.dataTransfer.effectAllowed = "move";
          setTimeout(function () { item.classList.add("dragging"); }, 0);
        });
        item.addEventListener("dragend", function () {
          item.classList.remove("dragging");
          draggedId = null;
        });
      });

      document.querySelectorAll(".g12-plan-remove").forEach(function (btn) {
        btn.addEventListener("click", function (e) {
          e.stopPropagation();
          removeFromPlan(btn.getAttribute("data-id"));
        });
      });
    }
  }

  function getDragAfterElement(container, y) {
    var items = Array.prototype.slice.call(container.querySelectorAll(".g12-plan-item:not(.dragging)"));
    return items.reduce(function (closest, child) {
      var box = child.getBoundingClientRect();
      var offset = y - box.top - box.height / 2;
      if (offset < 0 && offset > closest.offset) {
        return { offset: offset, element: child };
      }
      return closest;
    }, { offset: -Infinity, element: null }).element;
  }

  function setPlanOrder(order) {
    GRADE12_EXAM_PLAN.splice(0, GRADE12_EXAM_PLAN.length);
    order.forEach(function (id) { GRADE12_EXAM_PLAN.push(id); });
  }

  function toggleStatus(id) {
    var t = GRADE12_TOPICS.find(function (x) { return x.id === id; });
    if (!t) return;
    t.status = t.status === "done" ? "not-done" : "done";
    persistAndRenderBoard();
  }

  function removeFromPlan(id) {
    var idx = GRADE12_EXAM_PLAN.indexOf(id);
    if (idx === -1) return;
    GRADE12_EXAM_PLAN.splice(idx, 1);
    persistAndRenderBoard();
  }

  async function persistAndRenderBoard() {
    if (typeof window.saveEditorData === "function") await window.saveEditorData();
    renderBoard(searchInput ? searchInput.value : "");
  }

  function setupPlanDropzone() {
    var planCol = document.getElementById("g12-plan");
    if (!planCol) return;

    planCol.addEventListener("dragover", function (e) {
      e.preventDefault();
      planCol.classList.add("drag-over");
      var draggingEl = planCol.querySelector(".g12-plan-item.dragging");
      if (draggingEl) {
        var after = getDragAfterElement(planCol, e.clientY);
        if (after == null) planCol.appendChild(draggingEl);
        else planCol.insertBefore(draggingEl, after);
      }
    });

    planCol.addEventListener("dragleave", function (e) {
      if (e.target === planCol) planCol.classList.remove("drag-over");
    });

    planCol.addEventListener("drop", function (e) {
      e.preventDefault();
      planCol.classList.remove("drag-over");
      var id = draggedId || e.dataTransfer.getData("text/plain");
      if (!id) return;

      var reorderingEl = planCol.querySelector(".g12-plan-item.dragging");
      if (reorderingEl) {
        var order = Array.prototype.map.call(planCol.querySelectorAll(".g12-plan-item"), function (el) {
          return el.getAttribute("data-id");
        });
        setPlanOrder(order);
      } else if (GRADE12_EXAM_PLAN.indexOf(id) === -1) {
        var after = getDragAfterElement(planCol, e.clientY);
        if (after == null) {
          GRADE12_EXAM_PLAN.push(id);
        } else {
          var idx = GRADE12_EXAM_PLAN.indexOf(after.getAttribute("data-id"));
          GRADE12_EXAM_PLAN.splice(idx, 0, id);
        }
      } else {
        return; // already in the plan and not a reorder — nothing to do
      }
      persistAndRenderBoard();
    });
  }

  function openTopicModal(id) {
    var t = GRADE12_TOPICS.find(function (x) { return x.id === id; });
    if (!t) return;
    var overlay = document.getElementById("modal-overlay");
    var modal = document.getElementById("modal-body");
    var hasResourcesTab = typeof window.renderResourcesPane === "function";

    var readingItems = (t.materials || []).filter(function (m) { return m.kind === "reading"; });
    var manualItems = (t.materials || []).filter(function (m) { return m.kind !== "reading"; });

    var html = "";
    html += '<div class="modal-topbar"><div class="modal-tabs">';
    html += '<button type="button" class="mtab active" data-tab="overview">Overview</button>';
    if (hasResourcesTab) {
      html += '<button type="button" class="mtab" data-tab="resources">Resources' +
        (manualItems.length ? ' <span class="mtab-count">' + manualItems.length + "</span>" : "") +
        "</button>";
      if (readingItems.length) {
        html += '<button type="button" class="mtab" data-tab="reading">Reading' +
          ' <span class="mtab-count">' + readingItems.length + "</span>" +
          "</button>" +
          '<button type="button" class="mtab" data-tab="vocabulary">Vocabulary</button>';
      }
    }
    html += "</div></div>";

    html += '<div class="modal-pane" id="pane-overview">';
    html += '<div class="m-week">' + escapeHtml(t.partLabel) + "</div>";
    html += "<h2>" + escapeHtml(t.code) + (t.hlOnly ? ' <span class="g12-hl-badge">HL only</span>' : "") + "</h2>";
    html += '<p class="m-bigidea">' + escapeHtml(t.statement) + "</p>";
    if (window.CAN_EDIT) {
      html += '<div class="m-section"><h4>Status</h4>' +
        '<button type="button" class="ef-btn' + (t.status === "done" ? " primary" : "") + '" id="modal-status-toggle">' +
        (t.status === "done" ? "✓ Marked done — click to reopen" : "◻ Marked not done — click to mark done") +
        "</button></div>";
    } else {
      html += '<div class="m-section"><h4>Status</h4><p>' + (t.status === "done" ? "✓ Marked done" : "◻ Not yet done") + "</p></div>";
    }
    html += "</div>"; // #pane-overview

    if (hasResourcesTab) {
      html += '<div class="modal-pane" id="pane-resources" hidden></div>';
      if (readingItems.length) {
        html += '<div class="modal-pane" id="pane-reading" hidden></div>';
        html += '<div class="modal-pane" id="pane-vocabulary" hidden></div>';
      }
    }

    modal.innerHTML = html;
    overlay.classList.add("open");
    document.body.style.overflow = "hidden";

    var statusToggle = document.getElementById("modal-status-toggle");
    if (statusToggle) {
      statusToggle.addEventListener("click", function () {
        toggleStatus(t.id);
        openTopicModal(t.id);
      });
    }

    modal.querySelectorAll(".mtab").forEach(function (tabBtn) {
      tabBtn.addEventListener("click", function () {
        modal.querySelectorAll(".mtab").forEach(function (b) { b.classList.remove("active"); });
        tabBtn.classList.add("active");
        var target = tabBtn.getAttribute("data-tab");
        modal.querySelectorAll(".modal-pane").forEach(function (pane) {
          pane.hidden = pane.id !== "pane-" + target;
        });
        if (target === "resources") {
          window.renderResourcesPane(document.getElementById("pane-resources"), "grade12", t, function () {
            openTopicModal(t.id);
            var resourcesTab = document.querySelector('.mtab[data-tab="resources"]');
            if (resourcesTab) resourcesTab.click();
          });
        } else if (target === "reading") {
          window.renderReadingPane(document.getElementById("pane-reading"), t);
        } else if (target === "vocabulary") {
          window.renderVocabularyPane(document.getElementById("pane-vocabulary"), "grade12", t, function () {
            openTopicModal(t.id);
            var vocabTab = document.querySelector('.mtab[data-tab="vocabulary"]');
            if (vocabTab) vocabTab.click();
          });
        }
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    searchInput = document.getElementById("g12-search");
    if (window.CAN_EDIT) setupPlanDropzone();

    window.__editorCtx = {
      dataKey: "grade12",
      refresh: function () { renderBoard(searchInput ? searchInput.value : ""); }
    };
    if (typeof window.initEditorUI === "function") window.initEditorUI();

    function openDeepLinkedTopic() {
      var id = new URLSearchParams(location.search).get("topic");
      if (id && GRADE12_TOPICS.some(function (t) { return t.id === id; })) openTopicModal(id);
    }

    // GRADE12_TOPICS/GRADE12_EXAM_PLAN now arrive via an async fetch (see grade12.html)
    // rather than being defined synchronously by a <script> tag, so they may not exist yet.
    if (typeof GRADE12_TOPICS !== "undefined") {
      renderBoard("");
      openDeepLinkedTopic();
    } else {
      document.addEventListener("unitplan:grade12-ready", function () {
        renderBoard("");
        openDeepLinkedTopic();
      });
    }
    if (searchInput) {
      searchInput.addEventListener("input", function () { renderBoard(searchInput.value); });
    }
  });
})();
