// ---------- Planning-health dashboard ----------
(function () {
  function examCardHTML(key) {
    var e = EXAM_DATES[key];
    if (!e) return "";
    var parts = formatCountdownParts(e.date);
    var days = parts ? parts.days : 0;
    return (
      '<div class="g12-stat"><strong>' + (parts ? days : "Exams underway") + "</strong>" +
      "<span>" + escapeHtml(e.label) + (parts ? " — days to IB exams" : "") + "</span></div>"
    );
  }

  function renderExams() {
    var el = document.getElementById("dash-exams");
    if (!el || typeof EXAM_DATES === "undefined") return;
    el.innerHTML = Object.keys(EXAM_DATES).map(examCardHTML).join("");
  }

  function semesterCardHTML(s) {
    var pct = s.total ? Math.round((s.taught / s.total) * 100) : 0;
    return (
      '<div class="dash-card">' +
      '<div class="dash-card-top"><strong>' + escapeHtml(s.title) + "</strong>" +
      '<span>' + s.taught + " / " + s.total + " weeks taught</span></div>" +
      '<div class="dash-bar"><div class="dash-bar-fill" style="width:' + pct + '%"></div></div>' +
      (s.noResources
        ? '<div class="dash-warn">⚠ ' + s.noResources + " week" + (s.noResources === 1 ? "" : "s") + " with no resources attached</div>"
        : '<div class="dash-ok">✓ Every week has at least one resource</div>') +
      "</div>"
    );
  }

  function renderSemesters(semesters) {
    var el = document.getElementById("dash-semesters");
    if (!el) return;
    el.innerHTML = semesters.map(semesterCardHTML).join("");
  }

  function renderGrade12(g) {
    var el = document.getElementById("dash-grade12");
    if (!el) return;
    el.innerHTML =
      '<div class="g12-stat"><strong>' + g.done + " / " + g.total + "</strong><span>syllabus points done</span></div>" +
      '<div class="g12-stat"><strong>' + g.inPlan + "</strong><span>in the exam-prep plan</span></div>" +
      '<div class="g12-stat"><strong>' + g.noResources + "</strong><span>topics with no resources attached</span></div>";
  }

  document.addEventListener("DOMContentLoaded", function () {
    renderExams();
    fetch("/unit-plan/api/dashboard-stats")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        renderSemesters(data.semesters || []);
        renderGrade12(data.grade12 || { done: 0, total: 0, inPlan: 0, noResources: 0 });
      });
  });
})();
