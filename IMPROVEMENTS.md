# Website Improvements — Implementation Specs

Ten improvements to navigation, layout, and aesthetics, focused on students using
this as a learning resource. Each spec is self-contained: implement one at a time,
in any order. Key files: `templates/editor.html`, `templates/index.html`,
`static/js/app.js` (class `ContentScraperApp`), `static/css/style.css`, `app.py`.

---

## 1. Student course home page

**Problem:** The site's landing page (`/`) is a scraping dashboard with a URL input —
useless and confusing for a student who just wants to read the textbook. Students
have no entry point that shows the course.

**Implement:**
1. In `app.py`, add a route `/learn` that renders a new template `templates/learn.html`.
2. `learn.html`: fetch `/api/syllabus` with JS. Render each **top-level item** as a card
   in a responsive grid (`display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 1rem;`).
   Each card shows the theme title, the count of pages inside it (recursively count
   items that have a `folder`), and its first 3 child topic names as a preview list.
3. Clicking a card expands it in place (or navigates) to show all nested topics as
   links; items with a `folder` link to `/editor/<folder>` (URL-encode the folder).
   Items without a folder are non-clickable group labels.
4. Add a "🎓 Course Home" link in the header of `templates/index.html` and in the
   `editor-header` of `templates/editor.html` pointing to `/learn`.

**Done when:** Visiting `/learn` shows theme cards; clicking through reaches a
textbook page in ≤ 2 clicks; no scraping UI is visible anywhere on the page.

---

## 2. Breadcrumbs on every textbook page

**Problem:** A student on "A1.1.5 Describe the fetch, decode and execute cycle" has
no visible sense of where they are in the course (Theme A → A1 → A1.1 → this page).

**Implement:**
1. In `static/js/app.js`, method `loadSyllabusTree()` already computes the ancestor
   chain via `this.findPathToFolder(...)`. Store the result: `this.currentPath = path || []`.
2. In `displayContent()`, just before the meta info is appended to `mainCol`, build
   a breadcrumb div when `this.currentPath.length > 0`: for each id in the path,
   look up the item with `getItemById`-style search over `this.syllabusItems`
   (add a small helper `findItemInTree(id)`), and render:
   `Theme A › A1 › A1.1 › <current page title>` — ancestor crumbs are plain text
   (or link to `/learn`), current title is bold.
3. Style in `style.css`: class `.breadcrumbs` — `font-size: 0.85rem; color: var(--text-light); margin-bottom: 0.75rem;`
   with `›` separators, single line, `overflow: hidden; text-overflow: ellipsis; white-space: nowrap;`.
4. Note: `loadSyllabusTree()` is async and runs in parallel with `loadContent()` —
   after computing `currentPath` inside `loadSyllabusTree()`, re-render the
   breadcrumb container if the page content is already displayed (give the
   breadcrumb div id `breadcrumbBar` and update its innerHTML directly).

**Done when:** Every `/editor/<folder>` page shows its full syllabus path above the
title, and it doesn't break on pages that aren't in the syllabus (breadcrumb simply hidden).

---

## 3. Previous / Next page navigation

**Problem:** Students read topics in sequence but must reopen the sidebar tree after
every page. Linear navigation is the single most-used pattern in a textbook.

**Implement:**
1. In `static/js/app.js`, after the syllabus loads, flatten the tree depth-first
   into an ordered array of items that have a `folder`: `this.readingOrder`.
2. Find the index of `this.currentFolder`. Previous = index−1, next = index+1.
3. In `displayContent()` (read mode only, i.e. `!this.isEditMode`), append a pager
   div after the canvas grid: two large clickable cards side by side
   (`display: flex; justify-content: space-between; gap: 1rem; margin: 2rem 0 1rem;`).
   Left card: `← Previous` + the previous topic's title; right card: `Next →` + title.
   Each links to `/editor/<encodeURIComponent(folder)>`. Omit a card at either end.
4. Style: class `.pager-card` — flex: 1, padding 1rem, border 1px solid var(--border),
   border-radius 8px, hover: border-color var(--primary), background #f8fbff.
   Right card text-aligned right.
5. Same async caveat as spec 2: render the pager from `loadSyllabusTree()` completion
   if content displayed first (give the pager container an id and fill it late).

**Done when:** Every textbook page has working Prev/Next cards at the bottom that
follow the syllabus order shown in the sidebar.

---

## 4. Filter box for the sidebar navigation

**Problem:** The nav tree has 70+ topics. Finding "logic gates" means expanding
folders and scanning. Students give up and scroll the main page instead.

**Implement:**
1. In `templates/editor.html`, above `<div id="syllabusNavTree">`, add
   `<input type="search" id="navFilter" placeholder="Filter topics…">` styled full-width,
   `padding: 0.5rem; margin-bottom: 0.75rem; border: 1px solid var(--border); border-radius: 6px;`.
2. In `static/js/app.js` `renderNavTree()`: read `this.navFilterText` (default '').
   When non-empty (case-insensitive): render only items whose title contains the text
   **or** that have a matching descendant; force-expand every rendered group node
   (ignore `this.navExpanded` while filtering); wrap the matching substring in
   `<mark>` in the label.
3. Wire up in `loadSyllabusTree()`: `navFilter.addEventListener('input', e => { this.navFilterText = e.target.value.trim(); this.renderNavTree(); })`.
4. When the filter is cleared, restore normal expand/collapse behaviour.

**Done when:** Typing "logic" instantly narrows the tree to A1.2.3 / A.1.2.5 (etc.)
with their parent folders visible and the match highlighted; clearing restores the tree.

---

## 5. Reading typography and line measure

**Problem:** Body text spans the full main column — on a wide monitor that's 100+
characters per line, which is hard to read and skims poorly. Text is also small
relative to reading distance, and headings are all the same blue which flattens
the visual hierarchy.

**Implement (all in `static/css/style.css`):**
1. Constrain the measure: `.main-col { max-width: 46rem; }` (the grid column can stay
   wide; the text column inside it should not).
2. Base reading size: add `.editor-content-panel { font-size: 1.0625rem; }` and ensure
   paragraph line-height ≥ 1.7 (blocks currently use inline `line-height: 1.8` — fine, keep).
3. Heading scale + hierarchy: inside `.editor-content-panel`, set
   `h1 { font-size: 1.6rem; }`, `h2 { font-size: 1.35rem; }`, `h3 { font-size: 1.15rem; }`,
   `h4 { font-size: 1rem; }`. Keep h1 in `var(--primary)` but make h3/h4
   `color: var(--text-dark)` so only top-level headings are blue.
4. Add `p { max-width: 100%; }` guard and `letter-spacing: -0.011em` on headings.
5. Add spacing rhythm: headings get `margin-top: 1.75rem` (except first child), so
   sections visually separate without the dashed metadata clutter.

**Done when:** On a 1920px screen, body lines are ~70–80 characters; heading sizes
step down visibly; h3/h4 are no longer blue.

---

## 6. Hide scraper metadata from students

**Problem:** Every page opens with "🔗 URL: https://app.growhall.com/… 📅 Scraped: 7/10/2026" —
teacher debugging info. It's the first thing a student reads and it means nothing to them.

**Implement:**
1. In `static/js/app.js` `displayContent()`, the `metaInfo` div is always appended to
   `mainCol`. Wrap it: only create/append when `this.isEditMode` is true.
2. In edit mode, keep it but restyle smaller: `font-size: 0.75rem; opacity: 0.7;`.

**Done when:** Read mode shows the page title then content immediately; the URL/date
line appears only in edit mode.

---

## 7. Topic progress tracking (localStorage)

**Problem:** Students working through 70+ topics can't see what they've done. Progress
is the strongest motivator for self-paced study and requires no backend.

**Implement:**
1. In `static/js/app.js`, add helpers:
   `getProgress()` → `JSON.parse(localStorage.getItem('topicProgress') || '{}')`;
   `setProgress(folder, done)` → update and save the map.
2. In read mode on `/editor/<folder>` pages, render a "✔ Mark as complete" button at
   the very bottom (above/next to the pager from spec 3). Clicking toggles the state
   for `this.currentFolder`, button switches to "✓ Completed — tap to undo" with
   `background: var(--success)`.
3. In `renderNavTree()`, append `✓` (green, `float: right`) to nav items whose
   `item.folder` is marked complete.
4. At the top of the nav sidebar, render a thin progress summary:
   `X of Y topics complete` + a bar (`<div>` with inner div width = percentage,
   height 6px, border-radius 3px, background var(--success)). Y = count of tree
   items with a folder, X = how many of those are in the progress map.

**Done when:** Marking a page complete survives reload, shows a ✓ in the tree, and
the sidebar bar updates. No server changes required.

---

## 8. Dark mode toggle

**Problem:** Students revise at night. The site is bright white with no option.
All colors already flow through CSS variables in `:root`, so this is cheap.

**Implement:**
1. In `static/css/style.css`, add a `[data-theme="dark"]` block overriding the
   variables: `--bg-light: #1a1d21; --bg-white: #24272c; --text-dark: #e8eaed;
   --text-light: #9aa0a6; --border: #3c4043; --shadow: 0 2px 8px rgba(0,0,0,0.5);`.
   Audit hard-coded colors that break in dark mode: the sidebox gradients
   (`.sidebar-section*`), `.question-block`, `.task-block` — for each add a
   `[data-theme="dark"]` override using darker tints of the same hue with light text
   (e.g. vocab: `background: #1e3325; border-left-color: #27ae60; color: #d7ecd9;`).
2. In `static/js/app.js` constructor (or `init()`): read `localStorage.getItem('theme')`
   and set `document.documentElement.dataset.theme` accordingly.
3. Add a 🌙/☀️ toggle button: in `templates/editor.html` header (`header-right`) and
   `templates/index.html` header. Clicking flips the attribute and persists to localStorage.

**Done when:** Toggling swaps the whole UI (including sideboxes, question/task blocks,
nav tree) with readable contrast, and the choice persists across pages and reloads.

---

## 9. Mobile / narrow-screen layout

**Problem:** The editor page is a fixed three-column grid. On a phone or a half-screen
window the content is crushed and the nav is unusable — students will often open
this on phones.

**Implement (in `static/css/style.css`):**
1. Add `@media (max-width: 900px)` overrides:
   - `.editor-grid { grid-template-columns: 1fr !important; }`
   - `#navSidebar` becomes an overlay drawer: `position: fixed; left: 0; top: 0; bottom: 0;
     width: min(85vw, 320px); z-index: 100; transform: translateX(-100%);
     transition: transform 0.25s; background: var(--bg-white); box-shadow: 2px 0 12px rgba(0,0,0,0.2);`
     and when the grid does **not** have class `nav-collapsed`, `transform: translateX(0)`.
     (Reuse the existing ☰ `toggleNavBtn` / `nav-collapsed` mechanics in `toggleSidebar()` —
     on mobile it shows/hides the drawer instead of collapsing a column. Start pages
     in the hidden state on mobile: in `init()`, if `window.innerWidth < 900`, add `nav-collapsed`.)
   - `.page-canvas-grid { grid-template-columns: 1fr !important; }` — sideboxes flow
     under the main content.
   - `.editor-content-panel { padding: 0.75rem; }`
   - `.format-toolbar { overflow-x: auto; flex-wrap: nowrap; }`
2. Ensure tap targets in the nav tree are ≥ 40px tall on mobile (`padding: 0.65rem 0.75rem`).

**Done when:** At 375px width: content is single-column and readable, ☰ opens/closes
the nav drawer over the content, and the right palette never squeezes the reading column.

---

## 10. Unified card design system (aesthetic polish)

**Problem:** The page mixes several visual dialects: five different pastel gradient
sideboxes, a purple question block, an amber task block, dashed edit borders, and
default-blue headings. It reads as assembled-from-parts, and the gradients look
dated. Students take a resource more seriously when it looks coherent.

**Implement (all in `static/css/style.css`):**
1. Replace every `.sidebar-section*` gradient with a flat tint + stronger left accent:
   pattern `background: <hue>08–10% tint (flat, no gradient); border-left: 4px solid <accent>;
   border-radius: 10px;`. Keep each category's hue (study amber, theory blue, applied red,
   vocab green, funfact pink) so color still encodes meaning.
2. Same treatment for `.question-block` (violet tint, flat) and `.task-block` (amber tint,
   flat, remove the full border — keep only border-left).
3. Normalize card anatomy everywhere: `padding: 1rem 1.25rem; border-radius: 10px;
   margin-bottom: 1rem;` and card titles `font-size: 0.8rem; font-weight: 700;
   text-transform: uppercase; letter-spacing: 0.06em; opacity: 0.75;` with the body
   at normal case — the small-caps label look makes box types scannable.
4. Reveal-answer animation: give `.q-answer` `max-height: 0; overflow: hidden;
   transition: max-height 0.3s ease;` and `.q-answer.revealed { max-height: 1000px; }`
   instead of display none/block, so answers unfold smoothly.
5. Slim the editor header: `.editor-header { padding: 0.5rem 1rem; }` and reduce its
   h1 to `1.05rem` so content, not chrome, owns the viewport.

**Done when:** All boxes share identical radius/padding/label treatment and differ only
by hue; no gradients remain; answers animate open; the header is ≤ 52px tall.

---

### Suggested order

Quick wins first: **6 → 5 → 10** (pure CSS/small JS, immediate visual payoff), then
navigation: **2 → 3 → 4**, then features: **7 → 8 → 9 → 1**.

---

# Editing Experience — Google Sites Smoothness (Specs 11–15)

These five specs target the editor on `/editor/<folder>` pages (edit mode).
Key code: `static/js/app.js` — `displayContent()`, `renderBlockHTML()`,
`reorderBlocks()`, `saveChanges()`, block markup class `.canvas-block`,
hover controls `.block-controls`. Implement one spec at a time.

---

## 11. Drag handle instead of drag-anywhere (stop drags breaking text selection)

**Problem:** Every `.canvas-block` has `draggable=true` on the whole block. Trying to
select text inside a contenteditable paragraph frequently starts a block drag instead —
the single most jarring difference from Google Sites, which only drags from a handle.

**Implement:**
1. In `displayContent()` (edit mode), stop setting `blockWrapper.draggable = true`.
   Instead add a drag handle element to each block:
   `<div class="drag-handle" title="Drag to move">⋮⋮</div>` appended to `blockWrapper`.
2. Make only the handle initiate dragging: on handle `mousedown`, set
   `blockWrapper.draggable = true`; on `dragend` (and on handle `mouseup`), set it
   back to `false`. Keep the existing `dragstart/dragover/drop` listeners on the block.
3. CSS (`static/css/style.css`):
   `.drag-handle { position: absolute; left: -22px; top: 50%; transform: translateY(-50%);
   cursor: grab; color: var(--text-light); font-size: 0.9rem; padding: 4px;
   opacity: 0; transition: opacity 0.15s; user-select: none; }`
   `.editor-grid.editing .canvas-block:hover .drag-handle { opacity: 1; }`
   `.drag-handle:active { cursor: grabbing; }`
   Give `.canvas-block` in edit mode `margin-left: 24px` so the handle has gutter room.

**Done when:** Text inside blocks can be selected by click-dragging without ever moving
the block; blocks move only when dragged by the ⋮⋮ handle.

---

## 12. Insertion-line drop indicator with before/after targeting

**Problem:** While dragging, the target block just gets a green top border. There's no
clear indication of *where* the block will land, and dropping always inserts at the
target's index regardless of whether the pointer is above or below its midpoint.
Google Sites shows a thick blue line at the exact insertion point.

**Implement (in `static/js/app.js`):**
1. In the block `dragover` handler, compute position:
   `const rect = blockWrapper.getBoundingClientRect(); const before = e.clientY < rect.top + rect.height / 2;`
   Toggle classes: `blockWrapper.classList.toggle('drop-before', before);
   blockWrapper.classList.toggle('drop-after', !before);` (remove both on
   dragleave/drop/dragend).
2. In the `drop` handler, replace the current `reorderBlocks(srcIdx, targetIdx)` call:
   compute `let insertIdx = before ? targetIdx : targetIdx + 1; if (srcIdx < insertIdx) insertIdx--;`
   then splice: remove at `srcIdx`, insert at `insertIdx`. (Add a method
   `moveBlock(srcIdx, insertIdx)` and use it here.)
3. CSS: replace the `.canvas-block.drag-over` border-top rule with:
   `.canvas-block.drop-before { box-shadow: 0 -3px 0 0 var(--primary); }`
   `.canvas-block.drop-after { box-shadow: 0 3px 0 0 var(--primary); }`
   (box-shadow doesn't shift layout, so nothing jumps while dragging.)
4. Remove the old `.drag-over` class usage in these handlers.

**Done when:** Dragging shows a crisp blue line above or below the hovered block that
tracks the mouse, and the block lands exactly where the line was — including dropping
below the last block.

---

## 13. Preserve scroll and eliminate re-render jumps

**Problem:** Nearly every edit action (`reorderBlocks`, `deleteBlock`, `updateBlockLevel`,
`updateBlockStyle`, `updateBlockAlign`, adding blocks) calls
`this.displayContent(this.currentContent)`, which rebuilds the entire page DOM.
The panel jumps to the top, hover state is lost, and the whole page flashes —
the opposite of Google Sites' in-place feel.

**Implement (in `static/js/app.js`):**
1. Add a wrapper method:
   `rerender() { const panel = document.getElementById('contentView'); const scroll = panel ? panel.scrollTop : 0; this.displayContent(this.currentContent); if (panel) panel.scrollTop = scroll; }`
2. Replace every internal `this.displayContent(this.currentContent)` call that follows
   a block mutation (reorder, delete, add, level/style/align/side changes) with
   `this.rerender()`. Keep direct `displayContent` calls only in `loadContent`,
   `toggleEditMode`, `cancelChanges`, `saveChanges`.
3. In the `addXBlock()` methods, keep `scrollToBottom()` — that jump is intentional —
   but everywhere else no scroll change should occur.
4. Add a settle animation so moves feel physical: in `style.css`,
   `@keyframes blockSettle { from { background: #e8f0fe; } to { background: transparent; } }`
   — after a reorder, add class `just-moved` (`animation: blockSettle 0.6s ease;`) to
   the moved block (find it by `data-index` after rerender) and remove the class on
   `animationend`.

**Done when:** Reordering, deleting, restyling, and resizing blocks never changes the
scroll position; the moved block briefly highlights, then fades.

---

## 14. Undo / redo (Ctrl+Z / Ctrl+Y)

**Problem:** There is no undo. A mis-drop or accidental delete can only be fixed by
"Cancel", which throws away *all* unsaved work. Google Sites makes every action
reversible instantly.

**Implement (in `static/js/app.js`):**
1. Add to the class: `this.undoStack = []; this.redoStack = [];` (init in constructor).
2. Add `pushUndo()`: pushes `JSON.stringify(this.currentContent.blocks)` onto
   `undoStack` (cap at 50 entries — `shift()` when longer) and clears `redoStack`.
   Call `pushUndo()` at the START of every mutating method: `moveBlock`/`reorderBlocks`,
   `deleteBlock`, every `add*Block`, `updateBlockLevel`, `updateBlockStyle`,
   `updateBlockAlign`, `updateBlockSide`, and once per resize gesture at the start of
   `startImageResize`. For text edits, snapshot when editing begins: add
   `onfocus="window.app.pushUndo()"` alongside the existing `onblur` handlers in
   `renderBlockHTML` (one undo step per field-editing session is fine).
3. Add `undo()` / `redo()`: pop from one stack, push the current state onto the other,
   `this.currentContent.blocks = JSON.parse(snapshot)`, then `this.rerender()`.
4. Keyboard: in `setupEditorEvents()`, add a `keydown` listener on `document`:
   Ctrl/Cmd+Z → `undo()`, Ctrl/Cmd+Y or Ctrl/Cmd+Shift+Z → `redo()` — only when
   `this.isEditMode`. When focus is inside a `[contenteditable]` element, do NOT
   intercept — let the browser's native character-level undo handle typing.
5. UI: in the format toolbar built in `displayContent`, prepend `↩` and `↪` buttons
   wired to `window.app.undo()` / `window.app.redo()`, each with
   `onmousedown="event.preventDefault()"` like the other toolbar buttons.

**Done when:** Delete a block → Ctrl+Z restores it in place; redo re-deletes; history
holds 50 steps; typing inside a field still supports the browser's native text undo.

---

## 15. Autosave with save-status indicator

**Problem:** Work is only persisted when the user remembers to click "💾 Save Changes";
closing the tab silently loses everything since the last save. Google Sites saves
continuously and shows "All changes saved".

**Implement (in `static/js/app.js`):**
1. Add `this.isDirty = false; this.autosaveTimer = null;` to the class. Add
   `markDirty()`: sets `isDirty = true`, sets the status chip to "Saving…", then
   clears and re-arms `this.autosaveTimer = setTimeout(() => this.autosave(), 2000)`.
   Call `markDirty()` at the END of every mutating method listed in spec 14 step 2,
   and from the contenteditable update handlers (`updateBlockText`,
   `updateBlockTitle`, `updateBlockAnswer`, `updateBlockSrc`, `updateBlockAlt`).
2. `autosave()`: same POST as `saveChanges()` (`/api/content/<folder>/save` with
   `this.currentContent`) but WITHOUT exiting edit mode and without re-rendering.
   On success: `isDirty = false`, chip → "✓ All changes saved". On failure:
   chip → "⚠ Not saved — retrying", re-arm the timer for 10 seconds.
3. Status chip UI: in `displayContent()` edit-mode header actions, add
   `<span id="saveStatus" style="font-size: 0.8rem; opacity: 0.85; margin-right: 0.5rem;">✓ All changes saved</span>`
   before the Save button; update its `textContent` from `markDirty`/`autosave`.
   Keep the manual "💾 Save Changes" button — it still saves and exits edit mode,
   while autosave persists silently in the background.
4. Add a `beforeunload` guard in `setupEditorEvents()`:
   `window.addEventListener('beforeunload', (e) => { if (this.isEditMode && this.isDirty) { e.preventDefault(); e.returnValue = ''; } });`
5. `cancelChanges()` note: discard now reloads the server copy, which may already
   include autosaved changes — update its confirm text to
   "Discard edits made since the last autosave?" so the promise is accurate.

**Done when:** Stop typing for 2 seconds → chip shows "Saving…" then "✓ All changes
saved"; closing the tab right after an edit triggers the browser's leave warning;
content survives a browser crash up to the last autosave.

### Suggested order for 11–15

**13 first** (rerender/scroll — 11, 12, and 14 all build on it), then **11 → 12**
(drag feel), then **14 → 15** (safety nets).

---

## 16. Insert-in-place "+" button between blocks

**Problem:** The only way to add content is the right-hand palette, which always
appends to the BOTTOM of the page and auto-scrolls there. Adding a paragraph in the
middle of a page means: add at bottom, then drag it up past 30 blocks. Google Sites
inserts exactly where you point.

**Implement:**
1. In `static/js/app.js` `displayContent()` (edit mode only), after appending each
   `blockWrapper` to its column, also append an insert zone between blocks:
   `<div class="insert-zone" data-insert-at="${index + 1}"><button class="insert-btn">+</button></div>`.
   Also render one insert zone at the very top of `mainCol` with `data-insert-at="0"`.
2. Clicking an insert button opens a small popover menu anchored to it (one shared
   `<div id="insertMenu">` appended to `document.body`, positioned with
   `getBoundingClientRect()`): menu entries mirror the palette —
   Heading, Paragraph, Study Tip, Vocabulary, Fun Fact, Question, Task, Image, Video.
   Store the pending index in `this.insertAt`.
3. Add a generic `insertBlockAt(index, block)` method: `pushUndo()` (spec 14),
   `this.currentContent.blocks.splice(index, 0, block)`, `markDirty()` (spec 15),
   `this.rerender()` (spec 13 — if those specs aren't implemented yet, fall back to
   `displayContent`). Refactor the existing `add*Block()` methods to build their
   default block object via a shared `makeBlock(kind)` helper so the popover and the
   palette share one code path; palette buttons call
   `insertBlockAt(blocks.length, makeBlock(kind))`.
4. Close the popover on outside click or Escape. After inserting, focus the new
   block's first contenteditable element (`blockWrapper.querySelector('[contenteditable]')?.focus()`).
5. CSS: `.insert-zone { height: 14px; position: relative; opacity: 0; transition: opacity 0.15s; }`
   `.insert-zone:hover { opacity: 1; }`
   `.insert-zone::before { content: ''; position: absolute; left: 0; right: 0; top: 50%; height: 2px; background: var(--primary); }`
   `.insert-btn { position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%);
   width: 22px; height: 22px; border-radius: 50%; border: none; background: var(--primary);
   color: white; font-size: 14px; line-height: 1; cursor: pointer; }`
   `#insertMenu { position: absolute; z-index: 200; background: var(--bg-white);
   border: 1px solid var(--border); border-radius: 8px; box-shadow: var(--shadow);
   padding: 0.4rem; display: grid; grid-template-columns: 1fr 1fr; gap: 0.25rem; }`
   Menu items: plain buttons, `font-size: 0.85rem; padding: 0.4rem 0.6rem; text-align: left;`.

**Done when:** Hovering between any two blocks reveals a blue line with a + button;
clicking it and choosing "Paragraph" inserts an empty paragraph exactly there, focused
and ready to type — no scroll jump, no drag needed.

---

## 17. Natural typing flow: Enter splits, Backspace merges, real placeholders

**Problem:** Text blocks behave like form fields, not like a document. Enter inside a
paragraph just inserts a line break in the same block — you can't "keep typing" into
new paragraphs. Backspace at the start of an empty block does nothing; deleting a
block requires the hover 🗑️ button. Empty blocks are invisible (the `placeholder`
attribute does nothing on divs/p tags), so new paragraphs look like blank gaps.

**Implement:**
1. **Enter splits:** in `renderBlockHTML()` edit mode, add
   `onkeydown="window.app.handleBlockKeydown(event, ${index})"` to the paragraph
   (`text` block) contenteditable. In `handleBlockKeydown`: on plain Enter (no Shift),
   `preventDefault()`, then split: take the text after the caret
   (use `window.getSelection().getRangeAt(0)`, `range.setEndAfter(el.lastChild)` and
   `range.extractContents()` into a temp div → its innerHTML), save the remaining
   HTML to the current block, and `insertBlockAt(index + 1, { type: 'text', text: tailHtml })`
   (spec 16 helper), then focus the new block and place the caret at its start.
   Shift+Enter keeps the default behaviour (line break within the block).
2. **Backspace on empty deletes:** in the same handler, if key is Backspace and the
   element's `innerText.trim() === ''`: `preventDefault()`, delete the block
   (skip the `confirm()` — deleting an empty block must be instant; route through a
   `deleteBlockSilent(index)` that skips the dialog), then focus the previous block's
   contenteditable with the caret at the END (`selection.collapse(node, node.childNodes.length)`).
3. **Placeholders:** add CSS
   `[contenteditable][data-placeholder]:empty::before { content: attr(data-placeholder); color: var(--text-light); opacity: 0.6; pointer-events: none; }`
   and in `renderBlockHTML()` replace the non-functional `placeholder="…"` attributes
   with `data-placeholder="…"` on every contenteditable (headings: "Heading",
   text: "Type something…", question fields, task fields, sidebox fields).
   Note: `:empty` requires the element to have NO child nodes — when rendering an
   empty block, emit the contenteditable with zero whitespace between the tags
   (`>${block.text || ''}<` is already tight; also trim `block.text` when saving so
   `<br>`-only content is stored as '').
4. Also apply the keydown handler to `heading` blocks: Enter at the end of a heading
   creates an empty `text` block below it (people finish a heading and keep typing).

**Done when:** You can click into a paragraph, press Enter mid-sentence and the rest
moves into a new block; press Backspace in an empty block and land at the end of the
previous one; every empty editable shows grey hint text. Typing a heading then Enter
drops you into a fresh paragraph — a full page can be written without touching the palette.

---

## 18. Block selection with keyboard actions (duplicate, move, delete)

**Problem:** Blocks can only be manipulated via tiny hover controls and mouse dragging.
Google Sites lets you click a block to select it, then duplicate/move/delete from the
keyboard — much faster for bulk editing and precise reordering.

**Implement (in `static/js/app.js`):**
1. **Selection state:** add `this.selectedBlockIndex = null`. In edit mode, clicking a
   `blockWrapper` (attach in `displayContent`, ignore clicks inside `[contenteditable]`,
   inputs, selects, buttons) sets it and adds class `block-selected` (remove from any
   other block). Clicking empty canvas or pressing Escape deselects. After any
   `rerender()`, re-apply the class via `querySelector('[data-index="${selectedBlockIndex}"]')`.
2. **Keyboard actions** in the spec-14 `keydown` listener (edit mode, focus NOT inside
   contenteditable/input, and `selectedBlockIndex !== null`):
   - `Ctrl/Cmd+D` → duplicate: `pushUndo()`, deep-copy via
     `JSON.parse(JSON.stringify(blocks[i]))`, splice in at `i + 1`, select the copy,
     `markDirty()`, `rerender()`. `preventDefault()` (browser bookmark dialog).
   - `Alt+ArrowUp` / `Alt+ArrowDown` → move the block one position (swap with
     neighbour), keep it selected, reuse the spec-13 settle animation.
   - `Delete` or `Backspace` → delete the selected block (with the existing confirm),
     then select the next block at the same index if any.
   - `ArrowUp` / `ArrowDown` (bare) → move the SELECTION to the previous/next block
     and `scrollIntoView({ block: 'nearest' })`.
3. **Duplicate in hover controls:** in the `controls.innerHTML` template next to the
   🗑️ button, add
   `<button class="btn-control" onclick="window.app.duplicateBlock(${index})" title="Duplicate Block">⧉</button>`
   backed by a `duplicateBlock(idx)` method (same logic as Ctrl+D).
4. CSS: `.canvas-block.block-selected { border-color: var(--primary) !important;
   box-shadow: 0 0 0 2px rgba(74, 144, 226, 0.35); }`
5. Escape also blurs any focused contenteditable first (first Esc leaves the text
   field and selects its block — set `selectedBlockIndex` from the block containing
   `document.activeElement` — second Esc deselects). This gives a smooth
   type → adjust → type loop without the mouse.

**Done when:** Click a block → blue selection ring; Ctrl+D duplicates it below;
Alt+↑/↓ walks it up and down the page; Delete removes it; arrow keys move the
selection; Esc steps out of text editing into block selection, then clears it.

### Suggested order for 16–18

**16 first** (its `insertBlockAt`/`makeBlock` helpers are reused by 17), then **17**,
then **18**. All three assume 13's `rerender()` exists; implement spec 13 before any of these.

---

## 19. Create pages and sections from the UI (Google Sites "Pages" panel)

**Problem:** Every page in the site comes from scraping — there is no way to write a
new page from scratch (e.g. a teacher-authored "Exam Technique" or "Glossary" page),
and no way to organise pages into sections without opening the separate Syllabus
Manager. Google Sites has a Pages panel: "+ New page", nest pages under sections,
rename, delete — all in the editor.

**Implement:**

**Part A — server endpoints (`app.py`):**
1. `POST /api/pages` with JSON `{ "title": "...", "parent_id": "<syllabus item id or null>" }`:
   - Sanitize the title into a folder name (reuse the sanitize + collision logic from
     `/api/scrape-dom`; if the folder exists, append ` (2)`, ` (3)`, …).
   - Create `data/<folder>/content.json` with a starter document:
     `{ "url": "", "scraped_at": <now iso>, "title": <title>, "main_heading": <title>,
     "blocks": [ { "type": "heading", "level": 1, "text": <title> },
     { "type": "text", "text": "" } ], "images": [], "main_content": {}, "sidebar_sections": {} }`
   - If `data/syllabus.json` exists, insert `{ "id": <uuid8>, "title": <title>,
     "folder": <folder>, "children": [] }` into the tree — as a child of the item
     whose `id == parent_id`, else appended top-level — and save the file.
   - Return `{ "success": true, "folder": <folder> }`.
2. `POST /api/pages/<folder>/rename` with `{ "title": "..." }`: update `title` and
   `main_heading` in content.json (folder name stays — links keep working) and update
   the matching syllabus item's `title`.
3. `DELETE /api/pages/<folder>`: delete the folder (`shutil.rmtree`) and remove any
   syllabus item referencing it (keep the item's children: promote them to the
   removed item's position). Guard against path traversal: reject any `folder`
   containing `..` or path separators, and resolve the final path to confirm it is
   inside `data/`.
4. `POST /api/sections` with `{ "title": "...", "parent_id": <id or null> }`: insert a
   group item (`folder: null`) into syllabus.json the same way; return its id.

**Part B — editor sidebar UI (`templates/editor.html` + `static/js/app.js`):**
1. Under the "Syllabus Navigation" heading, add a button row:
   `<button id="newPageBtn" class="btn btn-small">+ Page</button>
   <button id="newSectionBtn" class="btn btn-small">+ Section</button>`.
2. `newPageBtn` click → `prompt('Page title:')` → if the nav tree has a selected/current
   item, pass its **parent** section id as `parent_id` (so the new page lands as a
   sibling of the page being viewed; null if at top level) → `POST /api/pages` →
   on success `window.location.href = '/editor/' + encodeURIComponent(folder)`.
   (The new page opens showing the starter heading; the user clicks ✏️ Edit Page.)
3. `newSectionBtn` click → `prompt('Section title:')` → `POST /api/sections` with the
   same parent logic → `loadSyllabusTree()` to refresh the sidebar in place.
4. In `renderNavTree()`, add a small hover-only "⋯" button on each nav item that
   opens a 3-entry menu: **Rename** (prompt, then the rename endpoint for pages, or
   `POST /api/syllabus` with the edited tree for folder-less sections), **New subpage**
   (calls the newPage flow with this item's id as `parent_id`), **Delete**
   (`confirm`, then `DELETE /api/pages/<folder>` for pages / tree-edit for sections,
   then `loadSyllabusTree()`; if the deleted page is the one currently open,
   redirect to `/learn`).
5. Section rows (items with children but no folder) already render as folders — keep
   that, and make "New subpage" on a section the primary way to fill it.

**Part C — empty-section affordance:** a section with no children shows a muted
"＋ Add a page" row beneath it in the nav tree, wired to the newPage flow with that
section's id — so building a book outline (sections first, pages inside) is possible
entirely from the editor sidebar.

**Done when:** From any textbook page you can: create "Exam Technique" as a new page
inside the current section and be editing it within ~3 seconds; create an empty
"Revision" section and add pages into it; rename and delete both — with the sidebar
tree, `/learn`, and the Syllabus Manager all reflecting the change (they all read the
same `syllabus.json`). Deleting a page never deletes other pages' folders, and page
URLs contain no `..` traversal.
