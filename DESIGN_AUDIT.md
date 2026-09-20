# Design System Audit — The Oracle

**Date:** 2026-08-01
**Scope:** All 77 templates in `templates/`, checked against `DESIGN.md`'s own rules (not generic best practice — the question was compliance with the system already documented).
**Net read:** the design system itself is solid and well-specified — the gap is entirely in *coverage*. Pages built/touched recently (Lesson Library, the test-presentation countdown, the report-card AI feature) follow it closely; most of the rest of the app predates `DESIGN.md` and was never retrofitted.

Nothing in this file has been fixed yet — it's the audit, for prioritizing follow-up work.

---

## 1. Emoji/glyph icons — systemic, highest priority

**68 of 77 templates** use emoji or unicode arrows as icons, directly against DESIGN.md's #1 named anti-pattern ("this is one of the most common 'AI-generated UI' tells").

Worst offenders (occurrence count):
- `book_page.html` — 119
- `admin_analytics_hub.html` — 33
- `quiz_manage.html` — 32
- `dashboard.html` — 30
- `quiz.html` — 27
- `flashcards_study.html` — 25
- `editor.html` — 22
- `ia_guide.html` — 22

Clean (recently touched, confirms the rule *is* enforced on new work): `slide_library.html`, `test_present.html`'s countdown, `report_card.html`'s icon set (via `report_icons.py`).

## 2. Colour drift — 275 off-system hex values across 54 files

Nothing enforces the DESIGN.md palette as the single source of truth; most pages define their own near-duplicates instead of reusing the tokens.

- **A second, uncoordinated purple** — `#a84fd4`, `#c77dff`, `#9d4edd`, `#b565ff`, `#b592ff` — competing with Study Violet in 13 files, including `test_present.html` (this session's countdown redesign used `#b592ff` where the DESIGN.md dark-theme token is `#9d84ff`).
- **`report_card.html`'s "performance-card" system** runs entirely on Material Design colors (`#2196F3`, `#4CAF50`, `#FF9800`, `#f44336`) instead of the app's own semantic set (`signal-blue #3b82f6`, `progress-emerald #10b981`, `caution-amber #f59e0b`, `alert-red #ef4444`) — on a page built this session.

## 3. `border-left` accent bars — 27 files

DESIGN.md already names this as a known-but-unfixed anti-pattern ("the existing HL-warning banner's amber left-border... to eventually revisit") — turns out that's one instance of 27. `report_card.html` alone has 10, paired with the off-palette colors above.

Files: `_quiz_analytics_body.html`, `admin_base.html`, `admin_reading_analytics.html`, `admin_student_analytics.html`, `admin_student_resources.html`, `admin_vocabulary.html`, `book-hierarchy-example.html`, `book_learn.html`, `book_page.html`, `concept_chain_play.html`, `dashboard.html`, `editor.html`, `homepage.html`, `ia_guide.html`, `login.html`, `my_resources.html`, `quiz.html`, `quiz_manage.html`, `reading-page-example.html`, `report_card.html`, `signup.html`, `student_base.html`, `student_page_detail.html`, `student_reading.html`, `syllabus.html`, `test_assign.html`, `test_builder.html`.

## 4. Button system bypassed — 22 files

Ad-hoc `<button style="...">` instead of the three-tier `.admin-btn` / `-ghost` / `-text` / `-danger` classes. Some are legitimately outside the system (icon-only reading-mode toggles in the reader toolbar), but several just reimplement a tier inline — e.g. `dashboard.html`'s stop button hardcodes `background: var(--danger)` instead of using `.admin-btn-danger`.

## 5. Typography — one real deviation

`book_page.html` sets `'Georgia', 'Garamond', serif !important` for reading text, against the "single typeface, no serif pairing" rule. Plausibly a deliberate reading-mode legibility choice (serif-for-long-form is a defensible, common pattern) — but it's undocumented, so drift vs. intent can't be told apart from the code alone.

**Decision needed:** if intentional, add it to `DESIGN.md` as a scoped exception for the reading surface; if not, it should follow Inter like everything else.

## 6. Minor: hover-triggered `box-shadow` — 6 files

Violates the "Flat-at-Rest Rule" (shadows should be ambient/constant, not a hover effect). Small in scope, low priority.

---

## Suggested order of attack

1. Emoji sweep (#1) — most visible, most emphatic rule in DESIGN.md, mechanical to fix per-file using the existing `report_icons.py`-style SVG pattern.
2. Resolve the book_page.html serif question (#5) — quick decision, unblocks whether it's a bug or a documented exception.
3. `report_card.html` semantic-color/border-left cleanup (#2 + #3 overlap) — one page, high-visibility (parents/students see this), already has the palette to swap onto.
4. Off-palette purple cluster (#2) — small file count (13), mechanical find/replace to the real token.
5. Remaining `border-left` instances (#3) and inline buttons (#4) — larger sweep, lower urgency.
6. Hover box-shadow (#6) — cleanup pass, no urgency.
