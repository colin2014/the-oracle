// ---------- Theme (respect OS + allow override via localStorage later if needed) ----------
(function () {
  var saved = localStorage.getItem("cs-theme");
  if (saved) document.documentElement.setAttribute("data-theme", saved);
})();

// ---------- HL/SL level view (toggle control lives in _base.html) ----------
function currentLevelView() {
  return typeof window.getLevelView === "function" ? window.getLevelView() : "all";
}

// ---------- Nav toggle (mobile) ----------
document.addEventListener("DOMContentLoaded", function () {
  var toggle = document.querySelector(".nav-toggle");
  var links = document.querySelector(".nav-links");
  if (toggle && links) {
    toggle.addEventListener("click", function () {
      links.classList.toggle("open");
    });
  }
  var here = location.pathname.split("/").pop() || "index.html";
  document.querySelectorAll(".nav-links a").forEach(function (a) {
    var href = a.getAttribute("href");
    if (href === here) a.classList.add("active");
  });
});

// ---------- Countdown ----------
const EXAM_DATES = {
  grade11: { label: "Grade 11 — Class of 2028", date: new Date("2028-04-25T09:00:00"), accentClass: "" },
  grade12: { label: "Grade 12 — Class of 2027", date: new Date("2027-04-30T09:00:00"), accentClass: "grade12" },
};

function formatCountdownParts(target) {
  var now = new Date();
  var diff = target.getTime() - now.getTime();
  if (diff <= 0) return null;
  var sec = Math.floor(diff / 1000);
  var days = Math.floor(sec / 86400);
  sec -= days * 86400;
  var hours = Math.floor(sec / 3600);
  sec -= hours * 3600;
  var mins = Math.floor(sec / 60);
  sec -= mins * 60;
  return { days: days, hours: hours, mins: mins, secs: sec };
}

function renderCountdowns() {
  var container = document.getElementById("countdowns");
  if (!container) return;
  container.innerHTML = Object.keys(EXAM_DATES)
    .map(function (key) {
      var e = EXAM_DATES[key];
      return (
        '<div class="countdown-card ' + e.accentClass + '" id="cd-' + key + '">' +
        '<div class="cd-label"><span class="dot"></span>' + e.label + "</div>" +
        '<div class="cd-date">IB exams begin ' +
        e.date.toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" }) +
        "</div>" +
        '<div class="cd-timer" data-key="' + key + '">' +
        '<div class="cd-unit"><div class="num">--</div><div class="lbl">Days</div></div>' +
        '<div class="cd-unit"><div class="num">--</div><div class="lbl">Hours</div></div>' +
        '<div class="cd-unit"><div class="num">--</div><div class="lbl">Mins</div></div>' +
        '<div class="cd-unit"><div class="num">--</div><div class="lbl">Secs</div></div>' +
        "</div>" +
        "</div>"
      );
    })
    .join("");
  tickCountdowns();
  setInterval(tickCountdowns, 1000);
}

function tickCountdowns() {
  Object.keys(EXAM_DATES).forEach(function (key) {
    var timer = document.querySelector('.cd-timer[data-key="' + key + '"]');
    if (!timer) return;
    var parts = formatCountdownParts(EXAM_DATES[key].date);
    if (!parts) {
      timer.parentElement.innerHTML =
        '<div class="cd-label"><span class="dot"></span>' + EXAM_DATES[key].label + "</div>" +
        '<div class="cd-done">Exams have begun — good luck!</div>';
      return;
    }
    var nums = timer.querySelectorAll(".num");
    nums[0].textContent = parts.days;
    nums[1].textContent = String(parts.hours).padStart(2, "0");
    nums[2].textContent = String(parts.mins).padStart(2, "0");
    nums[3].textContent = String(parts.secs).padStart(2, "0");
  });
}

// ---------- School calendar page ----------
function renderSchoolCalendar() {
  var root = document.getElementById("calendar-root");
  if (!root || typeof SCHOOL_CALENDAR === "undefined") return;
  root.innerHTML = SCHOOL_CALENDAR.map(function (yr) {
    var semsHtml = yr.semesters
      .map(function (sem) {
        var itemsHtml = sem.events
          .map(function (ev) {
            return (
              "<li><span class=\"ev-label\">" + escapeHtml(ev.label) + "</span>" +
              "<span class=\"ev-date\">" + escapeHtml(ev.date) + "</span></li>"
            );
          })
          .join("");
        return '<div class="cal-card"><h3>' + escapeHtml(sem.name) + "</h3><ul>" + itemsHtml + "</ul></div>";
      })
      .join("");
    return (
      '<div class="cal-year"><h2>' + escapeHtml(yr.year) + " Calendar</h2>" +
      '<div class="cal-semesters">' + semsHtml + "</div></div>"
    );
  }).join("");
}

// ---------- Week grid + modal (semester pages) ----------
function initSemesterPage(dataKey) {
  var sem = COURSE_DATA[dataKey];
  if (!sem) return;

  document.getElementById("sem-title").textContent = sem.title;
  document.getElementById("sem-sub").textContent = sem.subtitle;
  var dateRangeEl = document.getElementById("sem-daterange");
  if (dateRangeEl && sem.dateRange) dateRangeEl.textContent = sem.dateRange;

  var grid = document.getElementById("week-grid");
  var search = document.getElementById("week-search");

  function taughtPillHTML(w) {
    var cls = "wk-taught-pill" + (w.taught ? " is-taught" : "");
    var label = w.taught ? "✓ Taught" : "◻ Not taught";
    if (!window.CAN_EDIT) return '<span class="' + cls + '">' + label + "</span>";
    return '<button type="button" class="' + cls + '" data-week="' + escapeHtml(w.week) + '">' + label + "</button>";
  }

  function toggleTaught(weekNo) {
    var w = sem.weeks.find(function (x) { return x.week === weekNo; });
    if (!w) return;
    // Optimistic: flip locally and re-render immediately, save in the background —
    // same pattern grade12.js's toggleStatus() uses.
    w.taught = !w.taught;
    render(search ? search.value : "");
    fetch("/unit-plan/api/week/" + encodeURIComponent(dataKey) + "/" + encodeURIComponent(weekNo) + "/taught", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ taught: w.taught })
    }).catch(function (e) {
      console.error("Couldn't update taught status:", e);
    });
  }

  function weekCardHTML(w) {
    if (w.isBreak) {
      var cls = "week-card is-break" + (w.isExam ? " is-exam" : "");
      return (
        '<div class="' + cls + '">' +
        '<div class="wk-num">Week ' + w.week + "</div>" +
        '<div class="wk-topic">' + escapeHtml(w.topic) + "</div>" +
        (w.calendarDates ? '<div class="wk-dates">' + escapeHtml(w.calendarDates) + "</div>" : "") +
        "</div>"
      );
    }
    var hasDetail = !!w.detail;
    var hlsl = "";
    if (w.hl !== undefined && w.sl !== undefined && w.hl !== w.sl) {
      var level = currentLevelView();
      hlsl =
        '<div class="hlsl-row">' +
        (level !== "SL" ? '<div><span class="k">HL</span>' + escapeHtml(w.hl) + "</div>" : "") +
        (level !== "HL" ? '<div><span class="k">SL</span>' + escapeHtml(w.sl) + "</div>" : "") +
        "</div>";
    }
    return (
      '<div class="week-card' + (hasDetail ? " has-detail" : "") + '" data-week="' + w.week + '" tabindex="0">' +
      '<div class="wk-num"><span>Week ' + w.week + "</span>" +
      (hasDetail
        ? '<span class="badge detail">Full plan</span>'
        : w.syllabus
        ? '<span class="badge">' + escapeHtml(w.syllabus) + "</span>"
        : "") +
      "</div>" +
      '<div class="wk-topic">' + escapeHtml(w.topic) + "</div>" +
      (w.calendarDates ? '<div class="wk-dates">' + escapeHtml(w.calendarDates) + "</div>" : "") +
      '<div class="wk-focus">' + escapeHtml(w.contentFocus || "") + "</div>" +
      hlsl +
      '<div class="wk-footer">' +
      (w.materials && w.materials.length
        ? '<span class="wk-materials">📎 ' + w.materials.length + (w.materials.length === 1 ? " resource" : " resources") + "</span>"
        : "<span></span>") +
      taughtPillHTML(w) +
      "</div>" +
      "</div>"
    );
  }

  function render(filter) {
    var f = (filter || "").toLowerCase().trim();
    var onlyNotTaught = document.getElementById("wk-not-taught-filter");
    var weeks = sem.weeks.filter(function (w) {
      if (onlyNotTaught && onlyNotTaught.checked && !w.isBreak && w.taught) return false;
      if (!f) return true;
      var hay = [w.topic, w.contentFocus, w.bigIdea, w.hl, w.sl, w.syllabus]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return hay.indexOf(f) !== -1;
    });
    if (!weeks.length) {
      grid.innerHTML = '<div class="empty-state">No weeks match "' + escapeHtml(filter) + '".</div>';
      return;
    }
    grid.innerHTML = weeks.map(weekCardHTML).join("");
    grid.querySelectorAll(".week-card[data-week]").forEach(function (card) {
      card.addEventListener("click", function () {
        openWeekModal(sem, card.getAttribute("data-week"));
      });
    });
    if (window.CAN_EDIT) {
      grid.querySelectorAll(".wk-taught-pill").forEach(function (btn) {
        btn.addEventListener("click", function (e) {
          e.stopPropagation();
          toggleTaught(btn.getAttribute("data-week"));
        });
      });
    }
  }

  render("");
  if (search) {
    search.addEventListener("input", function () {
      render(search.value);
    });
  }
  var notTaughtFilter = document.getElementById("wk-not-taught-filter");
  if (notTaughtFilter) {
    notTaughtFilter.addEventListener("change", function () {
      render(search ? search.value : "");
    });
  }

  // Deep link from an assignment, e.g. /unit-plan/semester/year1sem1?week=5
  var deepLinkWeek = new URLSearchParams(location.search).get("week");
  if (deepLinkWeek && sem.weeks.some(function (x) { return x.week === deepLinkWeek; })) {
    openWeekModal(sem, deepLinkWeek);
  }

  window.__editorCtx = {
    dataKey: dataKey,
    sem: sem,
    refresh: function () { render(search ? search.value : ""); },
    toggleTaught: toggleTaught
  };
  if (typeof window.initEditorUI === "function") window.initEditorUI();
}

function escapeHtml(str) {
  if (str === undefined || str === null) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function listBlock(title, items) {
  if (!items || !items.length) return "";
  return (
    '<div class="m-section"><h4>' + title + "</h4><ul>" +
    items.map(function (i) { return "<li>" + escapeHtml(i) + "</li>"; }).join("") +
    "</ul></div>"
  );
}

function textBlock(title, text) {
  if (!text) return "";
  return '<div class="m-section"><h4>' + title + "</h4><p>" + escapeHtml(text) + "</p></div>";
}

function openWeekModal(sem, weekNo) {
  var w = sem.weeks.find(function (x) { return x.week === weekNo; });
  if (!w) return;
  var overlay = document.getElementById("modal-overlay");
  var modal = document.getElementById("modal-body");
  var hasResourcesTab = typeof window.renderResourcesPane === "function";

  var d = w.detail;
  var hasEditBtn = typeof window.startEditWeek === "function";
  var readingItems = (w.materials || []).filter(function (m) { return m.kind === "reading"; });
  var manualItems = (w.materials || []).filter(function (m) { return m.kind !== "reading"; });
  var html = "";
  if (hasResourcesTab || hasEditBtn) {
    html += '<div class="modal-topbar">';
    html += '<div class="modal-tabs">';
    if (hasResourcesTab) {
      html += '<button type="button" class="mtab active" data-tab="overview">Overview</button>' +
        '<button type="button" class="mtab" data-tab="resources">Resources' +
        (manualItems.length ? ' <span class="mtab-count">' + manualItems.length + "</span>" : "") +
        "</button>";
      if (readingItems.length) {
        html += '<button type="button" class="mtab" data-tab="reading">Reading' +
          ' <span class="mtab-count">' + readingItems.length + "</span>" +
          "</button>" +
          '<button type="button" class="mtab" data-tab="vocabulary">Vocabulary</button>';
      }
    }
    html += "</div>";
    if (hasEditBtn) {
      html += '<button class="modal-edit-btn" id="modal-edit-btn" data-week="' + escapeHtml(w.week) + '">✏️ Edit week</button>';
    }
    html += "</div>"; // .modal-topbar
  }
  html += '<div class="modal-pane" id="pane-overview">';
  html += '<div class="m-week">Week ' + w.week + " · " + sem.title +
    (w.calendarDates ? " · " + escapeHtml(w.calendarDates) : "") + "</div>";
  html += "<h2>" + escapeHtml(w.topic) + "</h2>";
  if (window.CAN_EDIT) {
    html += '<button type="button" class="wk-taught-pill modal-taught-pill' + (w.taught ? " is-taught" : "") + '" id="modal-taught-toggle">' +
      (w.taught ? "✓ Taught — click to unmark" : "◻ Not taught — click to mark") + "</button>";
  } else {
    html += '<span class="wk-taught-pill modal-taught-pill' + (w.taught ? " is-taught" : "") + '">' +
      (w.taught ? "✓ Taught" : "◻ Not yet taught") + "</span>";
  }
  html += '<p class="m-bigidea">' + escapeHtml((d && d.bigIdea) || w.bigIdea || "") + "</p>";

  if (w.mergedNote) {
    html += '<p class="m-note">' + escapeHtml(w.mergedNote) + "</p>";
  }
  if (w.note) {
    // w.note carries the CSV's "HL Notes / Extensions" column — genuinely HL-only
    // content, so it gets the HL band treatment rather than blending in as a plain note.
    html += '<div class="m-note-hl"><span class="m-hl-pill">HL</span><span>' + escapeHtml(w.note) + "</span></div>";
  }

  if (d) {
    var tags = [];
    if (d.syllabusLinks) tags.push.apply(tags, d.syllabusLinks.split(",").map(function (s) { return s.trim(); }));
    if (tags.length) {
      html += '<div class="m-section"><h4>Syllabus links</h4><div class="m-tags">' +
        tags.map(function (t) { return "<span>" + escapeHtml(t) + "</span>"; }).join("") +
        "</div></div>";
    }
    html += listBlock("Learning objectives", d.learningObjectives);
    html += textBlock("Key vocabulary", d.keyVocabulary);
    html += textBlock("Command terms", d.commandTerms);
    html += listBlock("Formative assessment", d.formativeAssessment);
    html += textBlock("Summative assessment", d.summativeAssessment);
    if (d.lesson1.length || d.lesson2.length) {
      html += '<div class="m-section"><h4>Lesson breakdown</h4><div class="m-lessons">';
      if (d.lesson1.length) {
        html += '<div class="lesson-box"><h5>Lesson 1</h5><ul>' +
          d.lesson1.map(function (i) { return "<li>" + escapeHtml(i) + "</li>"; }).join("") + "</ul></div>";
      }
      if (d.lesson2.length) {
        html += '<div class="lesson-box"><h5>Lesson 2</h5><ul>' +
          d.lesson2.map(function (i) { return "<li>" + escapeHtml(i) + "</li>"; }).join("") + "</ul></div>";
      }
      html += "</div></div>";
    }
    html += listBlock("Approaches to Learning (ATL)", d.atl);
    html += listBlock("Differentiation", d.differentiation);
    html += textBlock("Resources needed", d.resources);
    html += listBlock("Links to IA / TOK", d.iaTok);
  } else {
    html += textBlock("Content focus", w.contentFocus);
    html += listBlock("Learning objectives", w.objectives);
    html += textBlock("Assessment", w.assessment);
    if (w.hl !== undefined && w.sl !== undefined && w.hl !== w.sl) {
      var modalLevel = currentLevelView();
      if (modalLevel !== "SL") html += '<div class="m-section hl"><h4><span class="m-hl-pill">HL</span> focus</h4><p>' + escapeHtml(w.hl) + "</p></div>";
      if (modalLevel !== "HL") html += '<div class="m-section"><h4>SL focus</h4><p>' + escapeHtml(w.sl) + "</p></div>";
    }
    if (w.syllabus) {
      html += '<div class="m-section"><h4>Syllabus reference</h4><p>' + escapeHtml(w.syllabus) + "</p></div>";
    }
    html += '<p class="m-note">A detailed lesson-by-lesson plan for this week hasn’t been published yet.</p>';
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

  var editBtn = document.getElementById("modal-edit-btn");
  if (editBtn) {
    editBtn.addEventListener("click", function () {
      window.startEditWeek(editBtn.getAttribute("data-week"));
    });
  }

  var taughtToggle = document.getElementById("modal-taught-toggle");
  if (taughtToggle && window.__editorCtx && window.__editorCtx.toggleTaught) {
    taughtToggle.addEventListener("click", function () {
      window.__editorCtx.toggleTaught(w.week);
      openWeekModal(sem, weekNo);
    });
  }

  if (hasResourcesTab) {
    modal.querySelectorAll(".mtab").forEach(function (tabBtn) {
      tabBtn.addEventListener("click", function () {
        modal.querySelectorAll(".mtab").forEach(function (b) { b.classList.remove("active"); });
        tabBtn.classList.add("active");
        var target = tabBtn.getAttribute("data-tab");
        modal.querySelectorAll(".modal-pane").forEach(function (pane) {
          pane.hidden = pane.id !== "pane-" + target;
        });
        var bucketKey = (window.__editorCtx && window.__editorCtx.dataKey) || "";
        if (target === "resources") {
          window.renderResourcesPane(document.getElementById("pane-resources"), bucketKey, w, function () {
            openWeekModal(sem, weekNo);
            var resourcesTab = document.querySelector('.mtab[data-tab="resources"]');
            if (resourcesTab) resourcesTab.click();
          });
        } else if (target === "reading") {
          window.renderReadingPane(document.getElementById("pane-reading"), w);
        } else if (target === "vocabulary") {
          window.renderVocabularyPane(document.getElementById("pane-vocabulary"), bucketKey, w, function () {
            openWeekModal(sem, weekNo);
            var vocabTab = document.querySelector('.mtab[data-tab="vocabulary"]');
            if (vocabTab) vocabTab.click();
          });
        }
      });
    });
  }
}

function closeWeekModal() {
  document.getElementById("modal-overlay").classList.remove("open");
  document.body.style.overflow = "";
}

document.addEventListener("DOMContentLoaded", function () {
  var overlay = document.getElementById("modal-overlay");
  if (!overlay) return;
  overlay.addEventListener("click", function (e) {
    if (e.target === overlay) closeWeekModal();
  });
  var closeBtn = document.getElementById("modal-close");
  if (closeBtn) closeBtn.addEventListener("click", closeWeekModal);
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") closeWeekModal();
  });
});
