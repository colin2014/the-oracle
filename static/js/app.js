// Content Scraper & Visual Page Builder Script
class ContentScraperApp {
    constructor() {
        this.currentContent = null;
        this.currentFolder = null;
        this.isEditMode = false;
        this.currentPath = [];
        this.readingOrder = [];
        this.navFilterText = '';

        // Spec 13: scroll preservation & re-render
        this.lastScrollTop = 0;

        // Spec 14: undo/redo
        this.undoStack = [];
        this.redoStack = [];

        // Spec 15: autosave
        this.isDirty = false;
        this.autosaveTimer = null;

        // Spec 16: insert menu
        this.insertAt = null;

        // Spec 18: block selection
        this.selectedBlockIndex = null;

        this.init();
        window.app = this; // Expose globally for inline events
    }

    init() {
        // Initialize theme from localStorage
        this.initTheme();

        // Detect page route
        const isEditorPage = window.location.pathname.startsWith('/editor/');

        if (isEditorPage) {
            this.currentFolder = window.currentFolder;
            this.setupEditorEvents();

            // Keep the chapters sidebar visible (same navigation as the reading
            // page); only start collapsed on small screens.
            if (window.innerWidth < 900) {
                const editorGrid = document.getElementById('editorGrid');
                if (editorGrid) {
                    editorGrid.classList.add('nav-collapsed');
                }
            }

            // Load the specific page/folder (currentFolder already has the right path)
            this.loadContent(this.currentFolder);
            this.loadSyllabusTree();

            // Apply any saved heading styles from the database
            this.applyHeadingStylesToPage();
        } else {
            this.setupDashboardEvents();
            this.loadAllContent();
        }
    }

    clearCachesAndReload() {
        /**
         * Clears all localStorage and sessionStorage, then forces a hard reload
         * bypassing browser cache. Call this when edits aren't appearing on reload.
         */
        try {
            // Clear localStorage (preserving only theme preference)
            const savedTheme = localStorage.getItem('theme') || 'light';
            localStorage.clear();
            localStorage.setItem('theme', savedTheme);

            // Clear sessionStorage
            sessionStorage.clear();

            // Force hard reload with cache bust (Ctrl+Shift+R equivalent)
            const timestamp = new Date().getTime();
            window.location.href = window.location.href + (window.location.href.includes('?') ? '&' : '?') + '_t=' + timestamp;
        } catch (err) {
            console.error('Error clearing caches:', err);
            // Fallback: just do a hard reload
            window.location.reload(true);
        }
    }

    initTheme() {
        const savedTheme = localStorage.getItem('theme') || 'light';
        document.documentElement.dataset.theme = savedTheme;
        this.updateThemeToggle();
    }

    toggleTheme() {
        const currentTheme = document.documentElement.dataset.theme || 'light';
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        document.documentElement.dataset.theme = newTheme;
        localStorage.setItem('theme', newTheme);
        this.updateThemeToggle();
    }

    updateThemeToggle() {
        const toggleBtn = document.getElementById('themeToggle');
        if (toggleBtn) {
            const isDark = document.documentElement.dataset.theme === 'dark';
            toggleBtn.textContent = isDark ? '☀️' : '🌙';
        }
    }

    // --- Spec 13: Preserve scroll and eliminate re-render jumps ---
    rerender() {
        const panel = document.getElementById('contentView');
        const scroll = panel ? panel.scrollTop : 0;
        this.displayContent(this.currentContent);
        if (panel) {
            panel.scrollTop = scroll;
        }
        // Re-apply block selection after rerender
        if (this.selectedBlockIndex !== null && this.isEditMode) {
            setTimeout(() => {
                const block = document.querySelector(`[data-index="${this.selectedBlockIndex}"]`);
                if (block) {
                    block.classList.add('block-selected');
                }
            }, 0);
        }
    }

    // --- Spec 14: Undo / redo ---
    pushUndo() {
        if (!this.isEditMode || !this.currentContent) return;
        this.undoStack.push(JSON.stringify(this.currentContent.blocks));
        if (this.undoStack.length > 50) {
            this.undoStack.shift();
        }
        this.redoStack = [];
    }

    undo() {
        if (this.undoStack.length === 0) return;
        this.redoStack.push(JSON.stringify(this.currentContent.blocks));
        const prevState = this.undoStack.pop();
        this.currentContent.blocks = JSON.parse(prevState);
        this.rerender();
    }

    redo() {
        if (this.redoStack.length === 0) return;
        this.undoStack.push(JSON.stringify(this.currentContent.blocks));
        const nextState = this.redoStack.pop();
        this.currentContent.blocks = JSON.parse(nextState);
        this.rerender();
    }

    // --- Spec 15: Autosave ---
    markDirty() {
        if (!this.isEditMode) return;
        this.isDirty = true;
        const statusChip = document.getElementById('saveStatus');
        if (statusChip) {
            statusChip.textContent = '💾 Saving…';
        }
        clearTimeout(this.autosaveTimer);
        this.autosaveTimer = setTimeout(() => this.autosave(), 2000);
    }

    async autosave() {
        if (!this.isEditMode || !this.currentFolder || !this.isDirty) return;
        try {
            const response = await fetch(`/api/content/${this.currentFolder}/save`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(this.currentContent)
            });
            const result = await response.json();
            if (result.success) {
                this.isDirty = false;
                const statusChip = document.getElementById('saveStatus');
                if (statusChip) {
                    statusChip.textContent = '✓ All changes saved';
                }
            } else {
                const statusChip = document.getElementById('saveStatus');
                if (statusChip) {
                    statusChip.textContent = '⚠ Not saved — retrying';
                }
                this.autosaveTimer = setTimeout(() => this.autosave(), 10000);
            }
        } catch (err) {
            const statusChip = document.getElementById('saveStatus');
            if (statusChip) {
                statusChip.textContent = '⚠ Not saved — retrying';
            }
            this.autosaveTimer = setTimeout(() => this.autosave(), 10000);
        }
    }

    // --- Event Listeners Setup ---
    setupDashboardEvents() {
        const scrapeForm = document.getElementById('scrapeForm');
        if (scrapeForm) {
            scrapeForm.addEventListener('submit', (e) => this.handleScrape(e));
        }
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') this.performSearch();
            });
        }
    }

    setupEditorEvents() {
        const toggleNavBtn = document.getElementById('toggleNavBtn');
        if (toggleNavBtn) {
            toggleNavBtn.addEventListener('click', () => this.toggleSidebar());
        }

        // Remember the text selection inside editable blocks so toolbar
        // dropdowns (size/colour) can restore it after stealing focus
        document.addEventListener('selectionchange', () => {
            const sel = document.getSelection();
            if (sel && sel.rangeCount > 0) {
                const node = sel.anchorNode;
                const el = node && (node.nodeType === 1 ? node : node.parentElement);
                if (el && el.closest('[contenteditable="true"]')) {
                    this.savedRange = sel.getRangeAt(0).cloneRange();
                }
            }
        });

        // Spec 14: Keyboard shortcuts for undo/redo and block actions
        // Spec 18: Block selection keyboard actions
        document.addEventListener('keydown', (e) => {
            const isMac = /Mac|iPhone|iPad|iPod/.test(navigator.platform);
            const isCtrlCmd = isMac ? e.metaKey : e.ctrlKey;
            const isContenteditable = document.activeElement?.closest('[contenteditable="true"]');

            if (!this.isEditMode) return;

            // Bold / Italic / Underline (Ctrl/Cmd+B/I/U) in any editable text field.
            // Handled explicitly so it works in embedded webviews that don't give
            // contenteditable these shortcuts natively.
            if (isCtrlCmd && !e.altKey && isContenteditable) {
                const key = e.key.toLowerCase();
                const command = key === 'b' ? 'bold' : key === 'i' ? 'italic' : key === 'u' ? 'underline' : null;
                if (command) {
                    e.preventDefault();
                    this.applyFormat(command);
                    return;
                }
            }

            // Undo (Ctrl/Cmd+Z)
            if (isCtrlCmd && e.key === 'z' && !isContenteditable) {
                e.preventDefault();
                this.undo();
                return;
            }

            // Redo (Ctrl/Cmd+Y or Ctrl/Cmd+Shift+Z)
            if ((isCtrlCmd && e.key === 'y') || (isCtrlCmd && e.shiftKey && e.key === 'z') && !isContenteditable) {
                e.preventDefault();
                this.redo();
                return;
            }

            // Save and exit edit mode (Ctrl/Cmd+S)
            if (isCtrlCmd && e.key === 's') {
                e.preventDefault();
                this.saveChanges();
                return;
            }

            // Block selection keyboard actions (only if a block is selected and focus is not in contenteditable)
            if (this.selectedBlockIndex !== null && !isContenteditable) {
                // Duplicate (Ctrl/Cmd+D)
                if (isCtrlCmd && e.key === 'd') {
                    e.preventDefault();
                    this.duplicateBlock(this.selectedBlockIndex);
                    return;
                }

                // Move up (Alt+ArrowUp)
                if (e.altKey && e.key === 'ArrowUp') {
                    e.preventDefault();
                    this.moveBlockUp(this.selectedBlockIndex);
                    return;
                }

                // Move down (Alt+ArrowDown)
                if (e.altKey && e.key === 'ArrowDown') {
                    e.preventDefault();
                    this.moveBlockDown(this.selectedBlockIndex);
                    return;
                }

                // Delete or Backspace
                if (e.key === 'Delete' || e.key === 'Backspace') {
                    e.preventDefault();
                    this.deleteBlock(this.selectedBlockIndex);
                    return;
                }

                // Arrow up to select previous block
                if (e.key === 'ArrowUp' && !e.altKey) {
                    e.preventDefault();
                    if (this.selectedBlockIndex > 0) {
                        this.selectBlock(this.selectedBlockIndex - 1);
                    }
                    return;
                }

                // Arrow down to select next block
                if (e.key === 'ArrowDown' && !e.altKey) {
                    e.preventDefault();
                    if (this.selectedBlockIndex < this.currentContent.blocks.length - 1) {
                        this.selectBlock(this.selectedBlockIndex + 1);
                    }
                    return;
                }
            }

            // Escape to deselect or unfocus
            if (e.key === 'Escape') {
                if (isContenteditable) {
                    // First Esc: leave text field and select the block
                    const blockEl = document.activeElement.closest('[data-index]');
                    if (blockEl) {
                        const idx = parseInt(blockEl.getAttribute('data-index'), 10);
                        if (!isNaN(idx)) {
                            document.activeElement.blur();
                            this.selectBlock(idx);
                            e.preventDefault();
                        }
                    }
                } else if (this.selectedBlockIndex !== null) {
                    // Second Esc: deselect
                    this.selectBlock(null);
                    e.preventDefault();
                }
            }
        });

        // Spec 15: beforeunload guard for unsaved changes
        window.addEventListener('beforeunload', (e) => {
            if (this.isEditMode && this.isDirty) {
                e.preventDefault();
                e.returnValue = '';
            }
        });
    }

    // --- Rich Text Formatting ---
    applyFormat(command, value = null) {
        if (this.savedRange) {
            const sel = window.getSelection();
            sel.removeAllRanges();
            sel.addRange(this.savedRange);
        }
        document.execCommand(command, false, value);
    }

    applyHeading(value) {
        if (!value) return;

        // Find the block that currently holds the cursor/selection
        let blockEl = null;
        if (this.savedRange) {
            const node = this.savedRange.startContainer;
            const el = node.nodeType === 1 ? node : node.parentElement;
            blockEl = el && el.closest('[data-index]');
        }
        if (!blockEl && document.activeElement) {
            blockEl = document.activeElement.closest('[data-index]');
        }
        if (!blockEl) {
            alert('Click into a text block first, then choose a heading level.');
            return;
        }

        const index = parseInt(blockEl.getAttribute('data-index'), 10);
        const block = this.currentContent.blocks[index];
        if (!block) return;

        this.pushUndo();

        if (value === 'text') {
            // Convert a heading back into body text
            block.type = 'text';
            delete block.level;
        } else {
            // value is like "h2" — convert to a heading block of that level
            block.type = 'heading';
            block.level = parseInt(value.replace('h', ''), 10);
        }

        this.markDirty();
        this.rerender();

        // Re-focus the converted block so editing can continue
        setTimeout(() => {
            const newBlockEl = document.querySelector(`[data-index="${index}"]`);
            const editable = newBlockEl && newBlockEl.querySelector('[contenteditable="true"]');
            if (editable) {
                editable.focus();
                const range = document.createRange();
                range.selectNodeContents(editable);
                range.collapse(false);
                const sel = window.getSelection();
                sel.removeAllRanges();
                sel.addRange(range);
            }
        }, 0);
    }

    async openHeadingStylesDialog() {
        const dialog = document.createElement('div');
        dialog.id = 'heading-styles-dialog';
        dialog.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10000;
        `;

        const content = document.createElement('div');
        content.style.cssText = `
            background: white;
            border-radius: 12px;
            padding: 2rem;
            width: 90%;
            max-width: 500px;
            max-height: 80vh;
            overflow-y: auto;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        `;

        const headingStyles = await this.loadHeadingStyles();
        let html = '<h2 style="margin-top: 0; margin-bottom: 1.5rem; color: #2c3e50;">Heading Styles</h2>';

        for (let i = 1; i <= 6; i++) {
            const level = `h${i}`;
            const style = headingStyles[level] || { fontSize: '1rem', fontFamily: 'Arial', color: '#000000' };
            const colorValue = typeof style.color === 'string' && style.color.includes('rgb')
                ? this.rgbToHex(style.color)
                : style.color;

            html += `
                <div style="margin-bottom: 1.5rem; padding-bottom: 1.5rem; border-bottom: 1px solid #e0e0e0;">
                    <h3 style="margin: 0 0 0.75rem 0; color: #2c3e50;">Heading ${i}</h3>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1rem;">
                        <div>
                            <label style="display: block; font-size: 0.85rem; margin-bottom: 0.5rem; color: #555;">Font Size</label>
                            <input type="number" id="fontSize-${level}" value="${parseInt(style.fontSize)}" step="1" style="width: 100%; padding: 0.5rem; border: 1px solid #ccc; border-radius: 4px;">
                            <span style="font-size: 0.75rem; color: #888;">px</span>
                        </div>
                        <div>
                            <label style="display: block; font-size: 0.85rem; margin-bottom: 0.5rem; color: #555;">Color</label>
                            <input type="color" id="color-${level}" value="${colorValue}" style="width: 100%; height: 40px; padding: 0.25rem; border: 1px solid #ccc; border-radius: 4px; cursor: pointer;">
                        </div>
                    </div>
                    <div>
                        <label style="display: block; font-size: 0.85rem; margin-bottom: 0.5rem; color: #555;">Font Family</label>
                        <select id="fontFamily-${level}" style="width: 100%; padding: 0.5rem; border: 1px solid #ccc; border-radius: 4px;">
                            <option value="Arial" ${style.fontFamily === 'Arial' ? 'selected' : ''}>Arial</option>
                            <option value="Georgia" ${style.fontFamily === 'Georgia' ? 'selected' : ''}>Georgia</option>
                            <option value="Times New Roman" ${style.fontFamily === 'Times New Roman' ? 'selected' : ''}>Times New Roman</option>
                            <option value="Courier New" ${style.fontFamily === 'Courier New' ? 'selected' : ''}>Courier New</option>
                            <option value="Verdana" ${style.fontFamily === 'Verdana' ? 'selected' : ''}>Verdana</option>
                        </select>
                    </div>
                    <div style="margin-top: 1rem; padding: 1rem; background: #f5f5f5; border-radius: 4px;">
                        <p style="margin: 0; font-size: ${style.fontSize}; color: ${colorValue}; font-family: ${style.fontFamily}; font-weight: bold;">Preview Heading ${i}</p>
                    </div>
                </div>
            `;
        }

        html += `
            <div style="display: flex; gap: 1rem; margin-top: 2rem;">
                <button onclick="window.app.saveHeadingStyles().then(() => { const d = document.getElementById('heading-styles-dialog'); if (d) d.remove(); });" style="flex: 1; padding: 0.75rem; background: #3498db; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: 600;">Save</button>
                <button onclick="const d = document.getElementById('heading-styles-dialog'); if (d) d.remove();" style="flex: 1; padding: 0.75rem; background: #e0e0e0; color: #333; border: none; border-radius: 4px; cursor: pointer; font-weight: 600;">Cancel</button>
            </div>
        `;

        content.innerHTML = html;
        dialog.appendChild(content);
        document.body.appendChild(dialog);
    }

    // Returns only the styles the user has actually saved in the database,
    // or an empty object if none. Used when applying styles on page load.
    async fetchSavedHeadingStyles() {
        try {
            const response = await fetch('/api/heading-styles');
            if (response.ok) {
                return await response.json();
            }
        } catch (e) {
            console.warn('Failed to load heading styles from database:', e);
        }
        return {};
    }

    async loadHeadingStyles() {
        const saved = await this.fetchSavedHeadingStyles();
        if (Object.keys(saved).length > 0) {
            return saved;
        }

        // Get current styles from the page if none saved
        const styles = {};
        for (let i = 1; i <= 6; i++) {
            const level = `h${i}`;
            const el = document.querySelector(level);
            if (el) {
                const computed = window.getComputedStyle(el);
                styles[level] = {
                    fontSize: computed.fontSize,
                    color: computed.color,
                    fontFamily: computed.fontFamily
                };
            } else {
                // Fallback to sensible defaults
                const baseSizes = { h1: '2rem', h2: '1.35rem', h3: '1.15rem', h4: '1rem', h5: '0.9rem', h6: '0.8rem' };
                styles[level] = {
                    fontSize: baseSizes[level],
                    color: '#2c2c2c',
                    fontFamily: 'Arial'
                };
            }
        }
        return styles;
    }

    rgbToHex(rgb) {
        // Convert rgb(r, g, b) to #rrggbb
        const match = rgb.match(/^rgb\((\d+),\s*(\d+),\s*(\d+)\)$/);
        if (match) {
            const hex = x => {
                return ("0" + parseInt(x).toString(16)).slice(-2);
            };
            return "#" + hex(match[1]) + hex(match[2]) + hex(match[3]);
        }
        return rgb; // Return as-is if not rgb format
    }

    async saveHeadingStyles() {
        const styles = {};
        for (let i = 1; i <= 6; i++) {
            const level = `h${i}`;
            styles[level] = {
                fontSize: document.getElementById(`fontSize-${level}`).value + 'px',
                color: document.getElementById(`color-${level}`).value,
                fontFamily: document.getElementById(`fontFamily-${level}`).value
            };
        }

        try {
            const response = await fetch('/api/heading-styles', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(styles)
            });

            if (!response.ok) {
                throw new Error('Failed to save heading styles');
            }

            this.applyHeadingStylesToPage(styles);
        } catch (e) {
            console.error('Error saving heading styles:', e);
            alert('Failed to save heading styles. Please try again.');
        }
    }

    async applyHeadingStylesToPage(styles = null) {
        if (!styles) {
            // Only apply styles the user has genuinely saved — never the
            // computed/default fallback, which would clobber the page CSS.
            styles = await this.fetchSavedHeadingStyles();
        }
        for (let i = 1; i <= 6; i++) {
            const level = `h${i}`;
            const style = styles[level];
            if (style) {
                const styleEl = document.getElementById(`heading-style-${level}`);
                if (styleEl) styleEl.remove();

                const newStyle = document.createElement('style');
                newStyle.id = `heading-style-${level}`;
                // Scoped to the content body on purpose: an unscoped `h2 { ... !important }`
                // also hits the sticky titlebar's h2 and pins its font-size.
                newStyle.textContent = `
                    .page-body ${level} {
                        font-size: ${style.fontSize} !important;
                        color: ${style.color} !important;
                        font-family: ${style.fontFamily} !important;
                    }
                `;
                document.head.appendChild(newStyle);
            }
        }
    }

    toggleSidebar() {
        const editorGrid = document.getElementById('editorGrid');
        if (editorGrid) {
            editorGrid.classList.toggle('nav-collapsed');
        }
    }

    // --- Dashboard Scraping Handler ---
    async handleScrape(e) {
        e.preventDefault();
        const url = document.getElementById('urlInput').value.trim();
        const statusDiv = document.getElementById('scrapeStatus');

        if (!url) {
            this.showStatus('Please enter a URL', 'error', statusDiv);
            return;
        }

        this.showStatus('Scraping in progress...', 'loading', statusDiv);

        try {
            const response = await fetch('/api/scrape', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url })
            });

            const data = await response.json();

            if (data.success) {
                this.showStatus('✓ Successfully scraped! Refreshing list...', 'success', statusDiv);
                document.getElementById('urlInput').value = '';
                setTimeout(() => this.loadAllContent(), 1000);
            } else {
                this.showStatus(`✗ ${data.error || data.message}`, 'error', statusDiv);
            }
        } catch (error) {
            this.showStatus(`✗ Error: ${error.message}`, 'error', statusDiv);
        }
    }

    // --- Dashboard Loading List ---
    async loadAllContent() {
        try {
            const response = await fetch('/api/content');
            const data = await response.json();

            const list = document.getElementById('contentList');
            if (!list) return;
            list.innerHTML = '';

            if (data.items.length === 0) {
                list.innerHTML = '<p style="color: #7f8c8d; text-align: center; padding: 1rem;">No scraped content yet</p>';
                return;
            }

            data.items.forEach(item => {
                const div = document.createElement('div');
                div.className = 'content-item';
                div.innerHTML = `
                    <h4>${this.truncate(item.title, 30)}</h4>
                    <p>📅 ${new Date(item.scraped_at).toLocaleDateString()}</p>
                    <p>📦 ${item.image_count} images</p>
                `;
                // Redirect dashboard click to standalone editor page
                div.addEventListener('click', () => {
                    window.location.href = `/editor/${item.folder}`;
                });
                list.appendChild(div);
            });
        } catch (error) {
            console.error('Failed to load content:', error);
        }
    }

    // --- Standalone Editor Content Loading ---
    async loadContent(folder, editModeOverride = null) {
        try {
            const response = await fetch(`/api/content/${folder}`);
            const content = await response.json();

            this.currentContent = content;
            if (editModeOverride !== null) {
                this.isEditMode = editModeOverride;
            } else {
                // Open straight into edit mode when arriving from the ✏️ pencil (?edit=1)
                this.isEditMode = new URLSearchParams(window.location.search).get('edit') === '1';
            }
            this.displayContent(content);

            // Scroll to & select a specific block when arriving from the ✏️ pencil
            // on the reading page (?blockIndex=N). Runs after render so [data-index]
            // elements exist in the DOM.
            const blockParam = new URLSearchParams(window.location.search).get('blockIndex');
            if (blockParam !== null && this.isEditMode) {
                const blockIndex = parseInt(blockParam, 10);
                if (!Number.isNaN(blockIndex)) {
                    setTimeout(() => {
                        this.selectBlock(blockIndex);
                        const block = document.querySelector(`[data-index="${blockIndex}"]`);
                        if (block) block.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }, 100);
                }
            }

            // Check if this is a book with subpages
            this.loadBookPages(folder);
        } catch (error) {
            console.error('Failed to load content details:', error);
            const view = document.getElementById('contentView');
            if (view) {
                view.innerHTML = `<p style="color: var(--danger); text-align: center; padding: 2rem;">Error loading page: ${error.message}</p>`;
            }
        }
    }

    async loadBookPages(bookFolder) {
        // Check if this folder has subpages
        try {
            const response = await fetch(`/api/book-pages/${encodeURIComponent(bookFolder)}`);
            if (!response.ok) return;

            const data = await response.json();
            if (data.pages && data.pages.length > 0) {
                const selector = document.getElementById('pageSelector');
                const dropdown = document.getElementById('pageDropdown');
                if (selector && dropdown) {
                    dropdown.innerHTML = '';
                    data.pages.forEach(page => {
                        const option = document.createElement('option');
                        option.value = page.folder;
                        option.textContent = page.title;
                        if (page.folder === bookFolder + '/' + this.getCurrentPageId?.()) {
                            option.selected = true;
                        }
                        dropdown.appendChild(option);
                    });
                    dropdown.addEventListener('change', (e) => {
                        if (e.target.value) {
                            window.location.href = `/editor/${encodeURIComponent(e.target.value)}`;
                        }
                    });
                    selector.style.display = 'block';
                }
            }
        } catch (error) {
            // Not a book with subpages, that's fine
        }
    }

    getCurrentPageId() {
        const parts = this.currentFolder.split('/');
        return parts[parts.length - 1];
    }

    // --- Standalone Sidebar Syllabus Tree ---
    // Renders the hierarchy saved by the Syllabus Manager (/syllabus) as a
    // collapsible tree. Group nodes toggle open/closed; linked nodes navigate.
    async loadSyllabusTree() {
        try {
            let items = null;

            // Prefer the book-scoped tree so the editor shows the SAME navigation
            // as the reader/view page (just this book's pages, not every course).
            if (this.currentFolder && this.currentFolder.includes('/')) {
                const bookFolder = this.currentFolder.split('/')[0];
                try {
                    const bookResp = await fetch(`/api/book/${encodeURIComponent(bookFolder)}/pages`);
                    if (bookResp.ok) {
                        const bookData = await bookResp.json();
                        if (bookData.tree && bookData.tree.length > 0) {
                            items = bookData.tree;
                        }
                    }
                } catch (e) {
                    // fall back to the full syllabus below
                }
            }

            if (!items) {
                const response = await fetch('/api/syllabus');
                const data = await response.json();
                items = data.items || [];
            }

            this.syllabusItems = items;
            this.navExpanded = new Set();

            // Expand every top-level section, plus the chain down to the current page
            this.syllabusItems.forEach(item => {
                if (item.children && item.children.length > 0) this.navExpanded.add(item.id);
            });
            const path = this.findPathToFolder(this.syllabusItems, this.currentFolder, []);
            this.currentPath = path || [];
            if (path) path.forEach(id => this.navExpanded.add(id));

            this.readingOrder = this.flattenSyllabusToReadingOrder();

            this.renderNavTree();
            this.renderBreadcrumbs();
            this.renderPager();

            // Wire up filter input
            const navFilter = document.getElementById('navFilter');
            if (navFilter) {
                navFilter.addEventListener('input', (e) => {
                    this.navFilterText = e.target.value.trim();
                    this.renderNavTree();
                });
            }

            // Spec 19: Wire up new page/section buttons
            const newPageBtn = document.getElementById('newPageBtn');
            if (newPageBtn) {
                newPageBtn.addEventListener('click', () => this.promptNewPage());
            }

            const newSectionBtn = document.getElementById('newSectionBtn');
            if (newSectionBtn) {
                newSectionBtn.addEventListener('click', () => this.promptNewSection());
            }
        } catch (error) {
            console.error('Failed to render navigation tree:', error);
        }
    }

    // --- Spec 19: Create pages and sections from the UI ---
    promptNewPage() {
        const title = prompt('Page title:');
        if (!title) return;
        this.createNewPage(title);
    }

    promptNewSection() {
        const title = prompt('Section title:');
        if (!title) return;
        this.createNewSection(title);
    }

    async createNewPage(title) {
        // Get parent ID if current page is inside a section
        let parentId = null;
        if (this.currentPath.length > 0) {
            // The parent of the current page is its section (the item before it in the path)
            parentId = this.currentPath[this.currentPath.length - 1];
        }

        try {
            const response = await fetch('/api/pages', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title, parent_id: parentId })
            });

            const result = await response.json();
            if (result.success) {
                window.location.href = '/editor/' + encodeURIComponent(result.folder);
            } else {
                alert('Error creating page: ' + result.error);
            }
        } catch (err) {
            alert('Error creating page: ' + err.message);
        }
    }

    async createNewSection(title) {
        let parentId = null;
        if (this.currentPath.length > 0) {
            parentId = this.currentPath[this.currentPath.length - 1];
        }

        try {
            const response = await fetch('/api/sections', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title, parent_id: parentId })
            });

            const result = await response.json();
            if (result.success) {
                this.loadSyllabusTree();
            } else {
                alert('Error creating section: ' + result.error);
            }
        } catch (err) {
            alert('Error creating section: ' + err.message);
        }
    }

    findPathToFolder(items, folder, path) {
        for (const item of items) {
            if (item.folder === folder) return path;
            if (item.children) {
                const found = this.findPathToFolder(item.children, folder, [...path, item.id]);
                if (found) return found;
            }
        }
        return null;
    }

    findItemInTree(items, id) {
        for (const item of items) {
            if (item.id === id) return item;
            if (item.children) {
                const found = this.findItemInTree(item.children, id);
                if (found) return found;
            }
        }
        return null;
    }

    flattenSyllabusToReadingOrder(items = this.syllabusItems) {
        const order = [];
        const traverse = (item) => {
            if (item.folder) {
                order.push(item);
            }
            if (item.children) {
                item.children.forEach(child => traverse(child));
            }
        };
        items.forEach(item => traverse(item));
        return order;
    }

    itemMatchesFilter(item, query) {
        if (!query) return true;
        const lowerQuery = query.toLowerCase();
        return item.title.toLowerCase().includes(lowerQuery);
    }

    hasMatchingDescendant(item, query) {
        if (this.itemMatchesFilter(item, query)) return true;
        if (item.children) {
            return item.children.some(child => this.hasMatchingDescendant(child, query));
        }
        return false;
    }

    getProgress() {
        try {
            return JSON.parse(localStorage.getItem('topicProgress') || '{}');
        } catch (e) {
            return {};
        }
    }

    setProgress(folder, done) {
        const progress = this.getProgress();
        if (done) {
            progress[folder] = true;
        } else {
            delete progress[folder];
        }
        localStorage.setItem('topicProgress', JSON.stringify(progress));
    }

    isTopicComplete(folder) {
        return this.getProgress()[folder] === true;
    }

    renderBreadcrumbs() {
        const breadcrumbBar = document.getElementById('breadcrumbBar');
        if (!breadcrumbBar || this.currentPath.length === 0) {
            if (breadcrumbBar) breadcrumbBar.innerHTML = '';
            return;
        }

        let crumbs = [];
        for (const id of this.currentPath) {
            const item = this.findItemInTree(this.syllabusItems, id);
            if (item) crumbs.push(item.title);
        }

        if (this.currentContent && this.currentContent.title) {
            crumbs.push(this.currentContent.title);
        }

        const html = crumbs.map((crumb, idx) => {
            if (idx === crumbs.length - 1) {
                return `<span style="font-weight: bold;">${crumb}</span>`;
            }
            return `<span>${crumb}</span>`;
        }).join(' <span style="opacity: 0.6;">›</span> ');

        breadcrumbBar.innerHTML = html;
    }

    renderPager() {
        const pagerContainer = document.getElementById('pagerContainer');
        if (!pagerContainer || this.isEditMode) return;

        const currentIdx = this.readingOrder.findIndex(item => item.folder === this.currentFolder);
        if (currentIdx === -1) {
            pagerContainer.innerHTML = '';
            return;
        }

        const prev = currentIdx > 0 ? this.readingOrder[currentIdx - 1] : null;
        const next = currentIdx < this.readingOrder.length - 1 ? this.readingOrder[currentIdx + 1] : null;

        let html = '<div class="pager" style="display: flex; justify-content: space-between; gap: 1rem; margin: 2rem 0 1rem;">';

        if (prev) {
            html += `
                <div class="pager-card" style="flex: 1; padding: 1rem; border: 1px solid var(--border); border-radius: 8px; cursor: pointer; transition: all 0.2s;" onclick="window.location.href='/editor/${encodeURIComponent(prev.folder)}'">
                    <div style="font-size: 0.9rem; color: var(--text-light);">← Previous</div>
                    <div style="font-weight: 600; color: var(--text-dark); margin-top: 0.25rem;">${this.truncate(prev.title, 40)}</div>
                </div>
            `;
        } else {
            html += '<div style="flex: 1;"></div>';
        }

        if (next) {
            html += `
                <div class="pager-card" style="flex: 1; padding: 1rem; border: 1px solid var(--border); border-radius: 8px; cursor: pointer; text-align: right; transition: all 0.2s;" onclick="window.location.href='/editor/${encodeURIComponent(next.folder)}'">
                    <div style="font-size: 0.9rem; color: var(--text-light);">Next →</div>
                    <div style="font-weight: 600; color: var(--text-dark); margin-top: 0.25rem;">${this.truncate(next.title, 40)}</div>
                </div>
            `;
        } else {
            html += '<div style="flex: 1;"></div>';
        }

        html += '</div>';
        pagerContainer.innerHTML = html;
    }

    renderNavTree() {
        const navTree = document.getElementById('syllabusNavTree');
        if (!navTree) return;
        navTree.innerHTML = '';

        if (this.syllabusItems.length === 0) {
            navTree.innerHTML = '<p style="color: #7f8c8d; font-size: 0.85rem;">No items scraped yet.</p>';
            return;
        }

        // Calculate progress
        const allItems = this.flattenSyllabusToReadingOrder();
        const completed = allItems.filter(item => this.isTopicComplete(item.folder)).length;
        const total = allItems.length;

        // Render progress bar
        if (total > 0 && !this.navFilterText) {
            const progressDiv = document.createElement('div');
            progressDiv.style.marginBottom = '0.75rem';
            progressDiv.innerHTML = `
                <div style="font-size: 0.75rem; font-weight: 600; color: var(--text-light); margin-bottom: 0.25rem;">${completed} of ${total} topics complete</div>
                <div style="width: 100%; height: 6px; background: var(--border); border-radius: 3px; overflow: hidden;">
                    <div style="height: 100%; width: ${(completed / total) * 100}%; background: var(--success); transition: width 0.3s ease;"></div>
                </div>
            `;
            navTree.appendChild(progressDiv);
        }

        const isFiltering = this.navFilterText.length > 0;

        const buildNode = (item, depth) => {
            // Skip items that don't match filter
            if (isFiltering && !this.hasMatchingDescendant(item, this.navFilterText)) {
                return;
            }

            const hasChildren = item.children && item.children.length > 0;
            const shouldExpand = isFiltering || this.navExpanded.has(item.id);
            const isExpanded = shouldExpand;

            const div = document.createElement('div');
            div.className = 'nav-item' + (this.currentFolder && this.currentFolder === item.folder ? ' active' : '');
            div.style.marginLeft = depth > 0 ? `${depth * 0.9}rem` : '0';
            if (hasChildren) div.style.fontWeight = '600';

            const arrow = document.createElement('span');
            arrow.textContent = hasChildren ? (isExpanded ? '▾ ' : '▸ ') : '';
            arrow.style.display = 'inline-block';
            arrow.style.width = hasChildren ? '1rem' : '0';
            div.appendChild(arrow);

            // Render label with highlight on match
            const label = document.createElement('span');
            if (isFiltering && this.itemMatchesFilter(item, this.navFilterText)) {
                const text = item.title || 'Untitled';
                const lowerText = text.toLowerCase();
                const lowerQuery = this.navFilterText.toLowerCase();
                const idx = lowerText.indexOf(lowerQuery);
                if (idx >= 0) {
                    label.innerHTML = text.substring(0, idx) +
                        `<mark style="background: #ffeb3b; font-weight: bold;">${text.substring(idx, idx + this.navFilterText.length)}</mark>` +
                        text.substring(idx + this.navFilterText.length);
                } else {
                    label.textContent = text;
                }
            } else {
                label.textContent = item.title || 'Untitled';
            }
            div.appendChild(label);

            // Add checkmark for completed items
            if (item.folder && this.isTopicComplete(item.folder)) {
                const checkmark = document.createElement('span');
                checkmark.textContent = ' ✓';
                checkmark.style.color = 'var(--success)';
                checkmark.style.fontWeight = 'bold';
                checkmark.style.float = 'right';
                div.appendChild(checkmark);
            }

            div.addEventListener('click', (e) => {
                e.stopPropagation();
                if (item.folder) {
                    window.location.href = `/editor/${encodeURIComponent(item.folder)}`;
                } else if (hasChildren) {
                    if (isExpanded && !isFiltering) this.navExpanded.delete(item.id);
                    else this.navExpanded.add(item.id);
                    this.renderNavTree();
                }
            });

            // Clicking the arrow always toggles, even on linked nodes with children
            if (hasChildren) {
                arrow.addEventListener('click', (e) => {
                    e.stopPropagation();
                    if (this.navExpanded.has(item.id)) this.navExpanded.delete(item.id);
                    else this.navExpanded.add(item.id);
                    this.renderNavTree();
                });
            }

            navTree.appendChild(div);
            if (hasChildren && isExpanded) {
                item.children.forEach(child => buildNode(child, depth + 1));
            }
        };

        this.syllabusItems.forEach(item => buildNode(item, 0));
    }

    // --- Visual Builder Canvas Renderer ---
    displayContent(content) {
        const view = document.getElementById('contentView');
        const editorGrid = document.getElementById('editorGrid');
        const componentSidebar = document.getElementById('componentSidebar');
        const pageTitleText = document.getElementById('pageTitleText');
        const headerActions = document.getElementById('headerActions');

        if (!view) return;
        view.innerHTML = '';

        // Update main page window title
        document.title = `${content.title} | Textbook Editor`;
        if (pageTitleText) {
            pageTitleText.textContent = content.title;
            // Page title becomes directly editable in edit mode
            pageTitleText.contentEditable = this.isEditMode ? 'true' : 'false';
            pageTitleText.onblur = this.isEditMode
                ? () => this.updatePageTitle(pageTitleText.textContent.trim())
                : null;
        }

        // Toggle editor styling columns
        if (this.isEditMode) {
            if (editorGrid) editorGrid.classList.add('editing');
            if (componentSidebar) componentSidebar.style.display = 'block';

            if (headerActions) {
                headerActions.innerHTML = `
                    <div style="display: flex; gap: 0.5rem; align-items: center;">
                        <span id="saveStatus" style="font-size: 0.8rem; opacity: 0.85;">✓ All changes saved</span>
                        <button class="btn btn-primary btn-small" onclick="window.app.saveChanges()" style="background: var(--success); width: auto;">💾 Save Changes</button>
                        <button class="btn class-secondary btn-small" onclick="window.app.cancelChanges()" style="background: var(--danger); width: auto;">❌ Cancel</button>
                        <button class="btn btn-secondary btn-small" onclick="window.app.deletePage()" style="background: #cc0000; width: auto;">🗑️ Delete</button>
                    </div>
                `;
            }
        } else {
            if (editorGrid) editorGrid.classList.remove('editing');
            if (componentSidebar) componentSidebar.style.display = 'none';

            if (headerActions) {
                headerActions.innerHTML = `
                    <button class="btn btn-secondary btn-small" onclick="window.app.toggleEditMode()" style="background: var(--primary); width: auto;">✏️ Edit Page</button>
                `;
            }
        }

        // Breadcrumb navigation
        const breadcrumbBar = document.createElement('div');
        breadcrumbBar.id = 'breadcrumbBar';
        breadcrumbBar.className = 'breadcrumbs';
        view.appendChild(breadcrumbBar);

        // Pager container (previous/next navigation)
        const pagerContainer = document.createElement('div');
        pagerContainer.id = 'pagerContainer';
        // Will be populated after content and syllabus load

        // Rich text formatting toolbar (edit mode only)
        if (this.isEditMode) {
            const toolbar = document.createElement('div');
            toolbar.className = 'format-toolbar';
            toolbar.innerHTML = `
                <button onmousedown="event.preventDefault()" onclick="window.app.undo()" title="Undo (Ctrl+Z)">↩</button>
                <button onmousedown="event.preventDefault()" onclick="window.app.redo()" title="Redo (Ctrl+Y)">↪</button>
                <span class="toolbar-divider"></span>
                <button onmousedown="event.preventDefault()" onclick="window.app.applyFormat('bold')" title="Bold"><b>B</b></button>
                <button onmousedown="event.preventDefault()" onclick="window.app.applyFormat('italic')" title="Italic"><i>I</i></button>
                <button onmousedown="event.preventDefault()" onclick="window.app.applyFormat('underline')" title="Underline"><u>U</u></button>
                <span class="toolbar-divider"></span>
                <select onmousedown="event.stopPropagation()" onchange="window.app.applyHeading(this.value); this.selectedIndex = 0;" title="Convert the current block to a heading or body text">
                    <option value="">Heading…</option>
                    <option value="h1">Heading 1</option>
                    <option value="h2">Heading 2</option>
                    <option value="h3">Heading 3</option>
                    <option value="h4">Heading 4</option>
                    <option value="h5">Heading 5</option>
                    <option value="h6">Heading 6</option>
                    <option value="text">¶ Body text</option>
                </select>
                <button onmousedown="event.preventDefault()" onclick="window.app.openHeadingStylesDialog()" title="Configure heading styles">⚙️ H-Styles</button>
                <span class="toolbar-divider"></span>
                <button onmousedown="event.preventDefault()" onclick="window.app.applyFormat('insertUnorderedList')" title="Bullet list">• List</button>
                <span class="toolbar-divider"></span>
                <select onmousedown="event.stopPropagation()" onchange="window.app.applyFormat('fontSize', this.value); this.selectedIndex = 0;" title="Font size">
                    <option value="">Size…</option>
                    <option value="1">Tiny</option>
                    <option value="2">Small</option>
                    <option value="3">Normal</option>
                    <option value="4">Large</option>
                    <option value="5">X-Large</option>
                    <option value="6">Huge</option>
                    <option value="7">Giant</option>
                </select>
                <input type="color" value="#2c3e50" onchange="window.app.applyFormat('foreColor', this.value)" title="Text colour">
                <span class="toolbar-divider"></span>
                <button onmousedown="event.preventDefault()" onclick="window.app.applyFormat('removeFormat')" title="Clear formatting">🧹</button>
                <span style="font-size: 0.75rem; color: var(--text-light); margin-left: auto;">Highlight text, then pick a format</span>
            `;
            view.appendChild(toolbar);
        }

        // Create page layout sub-grid (2 column split)
        const canvasGrid = document.createElement('div');
        canvasGrid.className = 'page-canvas-grid';

        const mainCol = document.createElement('div');
        mainCol.className = 'canvas-column main-col';

        const sidebarCol = document.createElement('div');
        sidebarCol.className = 'canvas-column sidebar-col';

        canvasGrid.appendChild(mainCol);
        canvasGrid.appendChild(sidebarCol);
        view.appendChild(canvasGrid);
        view.appendChild(pagerContainer);

        // Renders Blocks (with insert zones between them for spec 16)
        if (content.blocks && content.blocks.length > 0) {
            // Insert zone at the very top (spec 16)
            if (this.isEditMode) {
                const topInsertZone = document.createElement('div');
                topInsertZone.className = 'insert-zone';
                topInsertZone.setAttribute('data-insert-at', '0');
                topInsertZone.innerHTML = '<button class="insert-btn" data-insert-at="0" onclick="window.app.showInsertMenu(0)">+</button>';
                mainCol.appendChild(topInsertZone);
            }

            content.blocks.forEach((block, index) => {
                const blockWrapper = document.createElement('div');
                blockWrapper.className = 'canvas-block';
                blockWrapper.setAttribute('data-index', index);

                // HTML5 Drag and Drop events in edit mode (spec 11, 12)
                if (this.isEditMode) {
                    // Spec 18: Block selection
                    blockWrapper.addEventListener('click', (e) => {
                        // Don't select if clicking on a button, input, or contenteditable
                        if (e.target.closest('button') || e.target.closest('input') || e.target.closest('select') ||
                            e.target.closest('[contenteditable="true"]')) {
                            return;
                        }
                        this.selectBlock(index);
                    });

                    // Spec 11: Drag handle instead of draggable on whole block
                    const dragHandle = document.createElement('div');
                    dragHandle.className = 'drag-handle';
                    dragHandle.innerHTML = '⋮⋮';
                    dragHandle.title = 'Drag to move';

                    dragHandle.addEventListener('mousedown', () => {
                        blockWrapper.draggable = true;
                    });

                    dragHandle.addEventListener('mouseup', () => {
                        blockWrapper.draggable = false;
                    });

                    blockWrapper.addEventListener('dragstart', (e) => {
                        e.dataTransfer.effectAllowed = 'move';
                        e.dataTransfer.setData('text/plain', index);
                        blockWrapper.classList.add('dragging');
                    });

                    blockWrapper.addEventListener('dragend', () => {
                        blockWrapper.classList.remove('dragging');
                        blockWrapper.classList.remove('drop-before');
                        blockWrapper.classList.remove('drop-after');
                        blockWrapper.draggable = false;
                    });

                    // Spec 12: Before/after drop indicator
                    blockWrapper.addEventListener('dragover', (e) => {
                        e.preventDefault();
                        const rect = blockWrapper.getBoundingClientRect();
                        const before = e.clientY < rect.top + rect.height / 2;
                        blockWrapper.classList.toggle('drop-before', before);
                        blockWrapper.classList.toggle('drop-after', !before);
                    });

                    blockWrapper.addEventListener('dragleave', () => {
                        blockWrapper.classList.remove('drop-before');
                        blockWrapper.classList.remove('drop-after');
                    });

                    blockWrapper.addEventListener('drop', (e) => {
                        e.preventDefault();
                        const srcIdx = parseInt(e.dataTransfer.getData('text/plain'), 10);
                        const rect = blockWrapper.getBoundingClientRect();
                        const before = e.clientY < rect.top + rect.height / 2;
                        blockWrapper.classList.remove('drop-before');
                        blockWrapper.classList.remove('drop-after');

                        if (!isNaN(srcIdx) && srcIdx !== index) {
                            let insertIdx = before ? index : index + 1;
                            if (srcIdx < insertIdx) insertIdx--;
                            this.moveBlock(srcIdx, insertIdx);
                        }
                    });

                    blockWrapper.appendChild(dragHandle);

                    // In-block drop-down selectors and trash buttons
                    const controls = document.createElement('div');
                    controls.className = 'block-controls';
                    let extraSelectors = '';
                    if (block.type === 'heading') {
                        extraSelectors = `
                            <select onchange="window.app.updateBlockLevel(${index}, parseInt(this.value, 10))"
                                    style="font-size: 0.75rem; padding: 2px 4px; border: 1px solid var(--border); border-radius: 4px; background: white; cursor: pointer;">
                                <option value="1" ${block.level === 1 ? 'selected' : ''}>H1</option>
                                <option value="2" ${block.level === 2 ? 'selected' : ''}>H2</option>
                                <option value="3" ${block.level === 3 ? 'selected' : ''}>H3</option>
                                <option value="4" ${block.level === 4 ? 'selected' : ''}>H4</option>
                            </select>
                        `;
                    } else if (block.type === 'sidebox') {
                        extraSelectors = `
                            <select onchange="window.app.updateBlockStyle(${index}, this.value)"
                                    style="font-size: 0.75rem; padding: 2px 4px; border: 1px solid var(--border); border-radius: 4px; background: white; cursor: pointer;">
                                <option value="study" ${block.style === 'study' ? 'selected' : ''}>Study</option>
                                <option value="theory" ${block.style === 'theory' ? 'selected' : ''}>TOK</option>
                                <option value="applied" ${block.style === 'applied' ? 'selected' : ''}>Applied</option>
                                <option value="vocab" ${block.style === 'vocab' ? 'selected' : ''}>Vocab</option>
                                <option value="funfact" ${block.style === 'funfact' ? 'selected' : ''}>Fun Fact</option>
                            </select>
                        `;
                    } else if (block.type === 'video' || block.type === 'image' || block.type === 'pptx') {
                        extraSelectors = `
                            <select onchange="window.app.updateBlockSide(${index}, this.value === 'side')"
                                    style="font-size: 0.75rem; padding: 2px 4px; border: 1px solid var(--border); border-radius: 4px; background: white; cursor: pointer;">
                                <option value="main" ${!block.side ? 'selected' : ''}>Main column</option>
                                <option value="side" ${block.side ? 'selected' : ''}>Side panel</option>
                            </select>
                        `;
                    }
                    controls.innerHTML = `
                        ${extraSelectors}
                        <button class="btn-control duplicate" onclick="window.app.duplicateBlock(${index})" title="Duplicate Block">⧉</button>
                        <button class="btn-control delete" onclick="window.app.deleteBlock(${index})" title="Delete Block">🗑️</button>
                    `;
                    blockWrapper.appendChild(controls);
                }

                // Render block HTML contents
                const blockContent = document.createElement('div');
                this.renderBlockHTML(block, index, blockContent);
                blockWrapper.appendChild(blockContent);

                // Image layout: width + float so surrounding text wraps around it
                if (block.type === 'image') {
                    const align = block.align || 'center';
                    const width = Math.min(100, Math.max(10, block.width || 100));
                    blockWrapper.style.width = width + '%';
                    if (align === 'left') {
                        blockWrapper.classList.add('float-left');
                    } else if (align === 'right') {
                        blockWrapper.classList.add('float-right');
                    } else {
                        blockWrapper.style.marginLeft = 'auto';
                        blockWrapper.style.marginRight = 'auto';
                    }
                }

                // Sideboxes (Study Tips, TOK, Vocabulary...) and any block
                // flagged side:true (e.g. scraped videos) go in the right column
                if (block.type === 'sidebox' || block.side) {
                    sidebarCol.appendChild(blockWrapper);
                } else {
                    mainCol.appendChild(blockWrapper);
                }

                // Insert zone after this block (spec 16)
                if (this.isEditMode) {
                    const insertZone = document.createElement('div');
                    insertZone.className = 'insert-zone';
                    insertZone.setAttribute('data-insert-at', String(index + 1));
                    insertZone.innerHTML = `<button class="insert-btn" data-insert-at="${index + 1}" onclick="window.app.showInsertMenu(${index + 1})">+</button>`;
                    if (block.type === 'sidebox' || block.side) {
                        sidebarCol.appendChild(insertZone);
                    } else {
                        mainCol.appendChild(insertZone);
                    }
                }
            });
        } else {
            const emptyHint = document.createElement('div');
            emptyHint.className = 'placeholder';
            emptyHint.innerHTML = `
                <p style="color: var(--text-light); text-align: center; padding: 2rem;">No content blocks present. Use the palette on the right to insert items.</p>
            `;
            mainCol.appendChild(emptyHint);
        }

        // Add drop listeners on columns to handle drops at the very bottom
        if (this.isEditMode) {
            [mainCol, sidebarCol].forEach(col => {
                col.addEventListener('dragover', (e) => {
                    e.preventDefault();
                    col.classList.add('drag-over-col');
                });
                col.addEventListener('dragleave', () => {
                    col.classList.remove('drag-over-col');
                });
                col.addEventListener('drop', (e) => {
                    e.preventDefault();
                    col.classList.remove('drag-over-col');
                    const srcIdx = parseInt(e.dataTransfer.getData('text/plain'), 10);
                    if (!isNaN(srcIdx)) {
                        const draggedBlock = this.currentContent.blocks[srcIdx];
                        if (draggedBlock) {
                            const isSidebarDrop = col.classList.contains('sidebar-col');
                            const isSidebarBlock = draggedBlock.type === 'sidebox' || !!draggedBlock.side;
                            if (isSidebarDrop === isSidebarBlock) {
                                window.app.moveBlockToBottom(srcIdx);
                            }
                        }
                    }
                });
            });
        }

        // Create insert menu (spec 16)
        if (this.isEditMode && !document.getElementById('insertMenu')) {
            const insertMenu = document.createElement('div');
            insertMenu.id = 'insertMenu';
            insertMenu.style.position = 'fixed';
            insertMenu.style.zIndex = '200';
            insertMenu.style.background = 'var(--bg-white)';
            insertMenu.style.border = '1px solid var(--border)';
            insertMenu.style.borderRadius = '8px';
            insertMenu.style.boxShadow = 'var(--shadow)';
            insertMenu.style.padding = '0.4rem';
            insertMenu.style.display = 'none';
            insertMenu.style.gridTemplateColumns = '1fr 1fr';
            insertMenu.style.gap = '0.25rem';
            insertMenu.innerHTML = `
                <button style="font-size: 0.85rem; padding: 0.4rem 0.6rem; text-align: left;" onclick="window.app.insertBlockType('heading'); event.stopPropagation();">📝 Heading</button>
                <button style="font-size: 0.85rem; padding: 0.4rem 0.6rem; text-align: left;" onclick="window.app.insertBlockType('paragraph'); event.stopPropagation();">✍️ Paragraph</button>
                <button style="font-size: 0.85rem; padding: 0.4rem 0.6rem; text-align: left;" onclick="window.app.insertBlockType('study'); event.stopPropagation();">💡 Study Tip</button>
                <button style="font-size: 0.85rem; padding: 0.4rem 0.6rem; text-align: left;" onclick="window.app.insertBlockType('vocab'); event.stopPropagation();">📖 Vocabulary</button>
                <button style="font-size: 0.85rem; padding: 0.4rem 0.6rem; text-align: left;" onclick="window.app.insertBlockType('funfact'); event.stopPropagation();">🎉 Fun Fact</button>
                <button style="font-size: 0.85rem; padding: 0.4rem 0.6rem; text-align: left;" onclick="window.app.insertBlockType('question'); event.stopPropagation();">❓ Question</button>
                <button style="font-size: 0.85rem; padding: 0.4rem 0.6rem; text-align: left;" onclick="window.app.insertBlockType('task'); event.stopPropagation();">📋 Task</button>
                <button style="font-size: 0.85rem; padding: 0.4rem 0.6rem; text-align: left;" onclick="window.app.insertBlockType('image'); event.stopPropagation();">🖼️ Image</button>
                <button style="font-size: 0.85rem; padding: 0.4rem 0.6rem; text-align: left;" onclick="window.app.insertBlockType('video'); event.stopPropagation();">🎥 Video</button>
            `;
            document.body.appendChild(insertMenu);

            // Close menu on Escape or outside click
            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape') this.hideInsertMenu();
            });
            document.addEventListener('click', (e) => {
                if (!e.target.closest('#insertMenu') && !e.target.closest('.insert-btn')) {
                    this.hideInsertMenu();
                }
            });
        }

        // Render breadcrumbs
        this.renderBreadcrumbs();

        // Add "Mark as complete" button in read mode
        if (!this.isEditMode && this.currentFolder) {
            const isComplete = this.isTopicComplete(this.currentFolder);
            const completeBtn = document.createElement('button');
            completeBtn.className = 'btn btn-small';
            completeBtn.style.marginTop = '1rem';
            completeBtn.style.alignSelf = 'flex-start';
            completeBtn.style.background = isComplete ? 'var(--success)' : 'var(--primary)';
            completeBtn.textContent = isComplete ? '✓ Completed — tap to undo' : '✔ Mark as complete';
            completeBtn.addEventListener('click', () => {
                this.setProgress(this.currentFolder, !isComplete);
                this.renderNavTree();
                // Re-render button
                const btn = document.querySelector('[data-progress-btn]');
                if (btn) {
                    const newIsComplete = this.isTopicComplete(this.currentFolder);
                    btn.style.background = newIsComplete ? 'var(--success)' : 'var(--primary)';
                    btn.textContent = newIsComplete ? '✓ Completed — tap to undo' : '✔ Mark as complete';
                }
            });
            completeBtn.setAttribute('data-progress-btn', 'true');
            view.appendChild(completeBtn);
        }
    }

    // --- Spec 17: Natural typing flow (Enter splits, Backspace merges) ---
    handleBlockKeydown(e, index) {
        const block = this.currentContent.blocks[index];
        const el = e.target;

        // Plain Enter (no Shift) splits the block
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            const sel = window.getSelection();
            const range = sel.getRangeAt(0);
            const afterRange = range.cloneRange();
            afterRange.setEndAfter(el.lastChild || el);
            const tailHtml = afterRange.extractContents().innerHTML;

            // Save remaining text to current block
            const headHtml = el.innerHTML;
            this.updateBlockText(index, headHtml);

            // Create new block with tail
            const newBlock = this.makeBlock(block.type === 'heading' ? 'paragraph' : 'text');
            newBlock.text = tailHtml;
            this.insertBlockAt(index + 1, newBlock);

            return;
        }

        // Backspace on empty block deletes it
        if (e.key === 'Backspace' && el.innerText.trim() === '') {
            e.preventDefault();
            if (index > 0) {
                this.deleteBlockSilent(index);
                this.markDirty();
                this.rerender();
                // Focus previous block at the end
                setTimeout(() => {
                    const prevBlock = document.querySelector(`[data-index="${index - 1}"]`);
                    if (prevBlock) {
                        const editable = prevBlock.querySelector('[contenteditable="true"]');
                        if (editable) {
                            editable.focus();
                            const range = document.createRange();
                            range.selectNodeContents(editable);
                            range.collapse(false);
                            const sel = window.getSelection();
                            sel.removeAllRanges();
                            sel.addRange(range);
                        }
                    }
                }, 0);
            }
        }
    }

    renderBlockHTML(block, index, container) {
        if (this.isEditMode) {
            // Render visual inline-editable blocks (contenteditable)
            switch (block.type) {
                case 'heading':
                    const lvl = block.level || 1;
                    container.innerHTML = `
                        <h${lvl} contenteditable="true"
                            onblur="window.app.updateBlockText(${index}, this.innerHTML)"
                            onfocus="window.app.pushUndo()"
                            onkeydown="window.app.handleBlockKeydown(event, ${index})"
                            data-placeholder="Heading"
                            style="color: var(--primary); margin: 1.5rem 0 0.75rem 0; outline: none; border-bottom: 1px dashed var(--primary);">
                            ${block.text || ''}
                        </h${lvl}>
                    `;
                    break;
                case 'text':
                    container.innerHTML = `
                        <div contenteditable="true"
                           onblur="window.app.updateBlockText(${index}, this.innerHTML)"
                           onfocus="window.app.pushUndo()"
                           onkeydown="window.app.handleBlockKeydown(event, ${index})"
                           data-placeholder="Type something…"
                           style="line-height: 1.8; color: var(--text-dark); margin: 0.5rem 0; outline: none; border-bottom: 1px dashed var(--primary); padding-bottom: 2px; min-height: 1.5rem;">
                           ${this.renderRich(block.text)}
                        </div>
                    `;
                    break;
                case 'sidebox':
                    const style = block.style || 'study';
                    container.innerHTML = `
                        <div class="sidebar-section ${style}" style="margin: 0; border: 1px dashed var(--primary);">
                            <h4 contenteditable="true"
                                onblur="window.app.updateBlockTitle(${index}, this.innerHTML)"
                                placeholder="Card Title..."
                                style="margin: 0 0 0.5rem 0; font-size: 1.1rem; font-weight: bold; outline: none; border-bottom: 1px dashed rgba(0,0,0,0.15); padding-bottom: 2px;">
                                ${block.title || ''}
                            </h4>
                            <div contenteditable="true"
                               onblur="window.app.updateBlockText(${index}, this.innerHTML)"
                               placeholder="Card body text..."
                               style="margin: 0; line-height: 1.6; font-size: 0.95rem; outline: none; min-height: 1.5rem;">
                               ${this.renderRich(block.text)}
                            </div>
                        </div>
                    `;
                    break;
                case 'question':
                    container.innerHTML = `
                        <div class="question-block" style="border: 1px dashed var(--primary);">
                            <div style="font-size: 0.75rem; font-weight: bold; color: #5e35b1; margin-bottom: 0.25rem;">❓ QUESTION</div>
                            <div class="q-text" contenteditable="true"
                                 onblur="window.app.updateBlockText(${index}, this.innerHTML)"
                                 style="outline: none; min-height: 1.5rem; border-bottom: 1px dashed rgba(0,0,0,0.15); padding-bottom: 2px;">${this.renderRich(block.text)}</div>
                            <div style="font-size: 0.75rem; font-weight: bold; color: #5e35b1; margin: 0.75rem 0 0.25rem 0;">✅ ANSWER (hidden until student clicks reveal)</div>
                            <div class="q-answer revealed" contenteditable="true"
                                 onblur="window.app.updateBlockAnswer(${index}, this.innerHTML)"
                                 style="outline: none; min-height: 1.5rem;">${this.renderRich(block.answer)}</div>
                        </div>
                    `;
                    break;
                case 'task':
                    container.innerHTML = `
                        <div class="task-block" style="border-style: dashed;">
                            <span class="task-label">📋 Task</span>
                            <h4 contenteditable="true"
                                onblur="window.app.updateBlockTitle(${index}, this.innerHTML)"
                                style="outline: none; border-bottom: 1px dashed rgba(0,0,0,0.15); padding-bottom: 2px;">${block.title || ''}</h4>
                            <div class="task-body" contenteditable="true"
                                 onblur="window.app.updateBlockText(${index}, this.innerHTML)"
                                 style="outline: none; min-height: 1.5rem;">${this.renderRich(block.text)}</div>
                        </div>
                    `;
                    break;
                case 'image':
                    container.innerHTML = `
                        <div class="img-frame" id="imgFrame_${index}">
                            <img src="${block.src || '/static/images/placeholder.png'}" alt="${block.alt || ''}"
                                 id="imgPreview_${index}"
                                 onerror="this.src='/static/images/placeholder.png'">
                            <div class="img-resize-handle" title="Drag to resize"
                                 onmousedown="window.app.startImageResize(event, ${index})"></div>
                            ${block.caption ? `<div class="image-caption" style="font-size: 0.85rem; color: var(--text-light); text-align: center; margin-top: 4px;">${block.caption}</div>` : ''}
                        </div>
                        <div style="display: flex; gap: 0.4rem; margin-top: 0.4rem; align-items: center; justify-content: center;">
                            <input type="text" value="${block.caption || ''}" oninput="window.app.updateBlockCaption(${index}, this.value)" 
                                   placeholder="Image Caption..." style="flex: 1; padding: 0.3rem; font-size: 0.8rem; border: 1px solid var(--border); border-radius: 4px;">
                            <button class="btn-control" onclick="document.getElementById('imgUpload_${index}').click()" title="Replace image">🔄 Replace</button>
                            <select onchange="window.app.updateBlockAlign(${index}, this.value)"
                                    style="font-size: 0.75rem; padding: 2px 4px; border: 1px solid var(--border); border-radius: 4px; background: white; cursor: pointer;">
                                <option value="left" ${block.align === 'left' ? 'selected' : ''}>⬅ Left — text wraps</option>
                                <option value="center" ${!block.align || block.align === 'center' ? 'selected' : ''}>⏺ Centred</option>
                                <option value="right" ${block.align === 'right' ? 'selected' : ''}>➡ Right — text wraps</option>
                            </select>
                            <input type="file" id="imgUpload_${index}" accept="image/*" style="display:none"
                                   onchange="window.app.handleImageUpload(${index}, this)">
                        </div>
                    `;
                    break;
                case 'video':
                    container.innerHTML = `
                        <div style="background: #f1f3f5; padding: 0.75rem; border-radius: 8px; border: 1px dashed var(--primary);">
                            <div class="video-container" style="max-height: 200px; margin-bottom: 0.5rem;">
                                <iframe src="${block.src ? this.getVideoEmbedUrl(block.src) : ''}" style="width: 100%; height: 100%;"></iframe>
                            </div>
                            <div style="display: flex; flex-direction: column; gap: 0.4rem; text-align: left;">
                                <div style="display: flex; align-items: center; gap: 0.5rem;">
                                    <span style="font-size: 0.75rem; font-weight: bold; width: 60px; color: var(--text-light);">URL:</span>
                                    <input type="text" value="${block.src || ''}" oninput="window.app.updateBlockSrc(${index}, this.value); this.closest('.canvas-block').querySelector('iframe').src = window.app.getVideoEmbedUrl(this.value);"
                                           placeholder="YouTube, Google Drive link, or MP4 URL..." style="flex: 1; padding: 0.3rem; font-size: 0.8rem; border: 1px solid var(--border); border-radius: 4px;">
                                    <button class="btn-control" onclick="document.getElementById('videoUpload_${index}').click()" title="Upload video file">📤 Upload</button>
                                    <input type="file" id="videoUpload_${index}" accept="video/*" style="display:none"
                                           onchange="window.app.handleVideoUpload(${index}, this)">
                                </div>
                                <div style="display: flex; align-items: center; gap: 0.5rem;">
                                    <span style="font-size: 0.75rem; font-weight: bold; width: 60px; color: var(--text-light);">Caption:</span>
                                    <input type="text" value="${block.title || ''}" oninput="window.app.updateBlockTitle(${index}, this.value)"
                                           placeholder="Video Title..." style="flex: 1; padding: 0.3rem; font-size: 0.8rem; border: 1px solid var(--border); border-radius: 4px;">
                                </div>
                                <div style="font-size: 0.7rem; color: var(--text-light); padding-top: 0.25rem;">
                                    💡 Paste YouTube link, Google Drive share link, or MP4 URL
                                </div>
                            </div>
                        </div>
                    `;
                    break;
                case 'pptx':
                    container.innerHTML = `
                        <div style="background: #fff0f0; padding: 0.75rem; border-radius: 8px; border: 1px dashed #ffccd5;">
                            <div class="pptx-container" style="max-height: 200px; margin-bottom: 0.5rem;">
                                <iframe src="${block.src ? this.getPptxEmbedUrl(block.src) : ''}" style="width: 100%; height: 100%;"></iframe>
                            </div>
                            <div style="display: flex; flex-direction: column; gap: 0.4rem; text-align: left;">
                                <div style="display: flex; align-items: center; gap: 0.5rem;">
                                    <span style="font-size: 0.75rem; font-weight: bold; width: 60px; color: #a51d24;">Slides URL:</span>
                                    <input type="text" value="${block.src || ''}" oninput="window.app.updateBlockSrc(${index}, this.value); this.closest('.canvas-block').querySelector('iframe').src = window.app.getPptxEmbedUrl(this.value);" 
                                           placeholder="OneDrive embed link or public PPTX URL..." style="flex: 1; padding: 0.3rem; font-size: 0.8rem; border: 1px solid var(--border); border-radius: 4px;">
                                </div>
                                <div style="display: flex; align-items: center; gap: 0.5rem;">
                                    <span style="font-size: 0.75rem; font-weight: bold; width: 60px; color: var(--text-light);">Caption:</span>
                                    <input type="text" value="${block.title || ''}" oninput="window.app.updateBlockTitle(${index}, this.value)"
                                           placeholder="Slides Caption..." style="flex: 1; padding: 0.3rem; font-size: 0.8rem; border: 1px solid var(--border); border-radius: 4px;">
                                </div>
                            </div>
                        </div>
                    `;
                    break;
                case 'code':
                    const lang = block.language || 'python';
                    container.innerHTML = `
                        <div style="background: #1e1e1e; border-radius: 8px; border: 1px dashed var(--primary); overflow: hidden;">
                            <div style="background: #2d2d30; padding: 0.75rem 1rem; display: flex; gap: 0.5rem; align-items: center; justify-content: space-between; border-bottom: 1px solid #3e3e42;">
                                <div style="display: flex; gap: 0.5rem; align-items: center; flex: 1;">
                                    <select onchange="window.app.updateBlockCodeLanguage(${index}, this.value)"
                                            style="font-size: 0.75rem; padding: 4px 8px; border: 1px solid #3e3e42; border-radius: 4px; background: #1e1e1e; color: #d4d4d4; cursor: pointer;">
                                        <option value="python" ${lang === 'python' ? 'selected' : ''}>Python</option>
                                        <option value="javascript" ${lang === 'javascript' ? 'selected' : ''}>JavaScript</option>
                                        <option value="html" ${lang === 'html' ? 'selected' : ''}>HTML</option>
                                        <option value="css" ${lang === 'css' ? 'selected' : ''}>CSS</option>
                                        <option value="sql" ${lang === 'sql' ? 'selected' : ''}>SQL</option>
                                        <option value="bash" ${lang === 'bash' ? 'selected' : ''}>Bash</option>
                                        <option value="java" ${lang === 'java' ? 'selected' : ''}>Java</option>
                                    </select>
                                    <input type="text" value="${block.filename || ''}" oninput="window.app.updateBlockFilename(${index}, this.value)"
                                           placeholder="filename.py (optional)" style="flex: 1; padding: 4px 8px; font-size: 0.75rem; border: 1px solid #3e3e42; border-radius: 4px; background: #1e1e1e; color: #d4d4d4;">
                                </div>
                                <input type="text" value="${block.title || ''}" oninput="window.app.updateBlockTitle(${index}, this.value)"
                                       placeholder="Code title..." style="padding: 4px 8px; font-size: 0.75rem; border: 1px solid #3e3e42; border-radius: 4px; background: #1e1e1e; color: #d4d4d4;">
                            </div>
                            <textarea onblur="window.app.updateBlockCodeContent(${index}, this.value)"
                                      onfocus="window.app.pushUndo()"
                                      placeholder="Paste or type your code here..."
                                      style="width: 100%; min-height: 250px; padding: 1rem; background: #1e1e1e; color: #d4d4d4; border: none; border-radius: 0; font-family: 'Fira Code', 'Courier New', monospace; font-size: 0.9rem; outline: none; resize: vertical; line-height: 1.5;">${block.code || ''}</textarea>
                        </div>
                    `;
                    break;
            }
        } else {
            // Render read-only standard textbook view
            switch (block.type) {
                case 'heading':
                    const lvl = block.level || 1;
                    container.innerHTML = `<h${lvl} style="color: var(--primary); margin: 1.5rem 0 0.75rem 0;">${block.text || ''}</h${lvl}>`;
                    break;
                case 'text':
                    container.innerHTML = `<div style="line-height: 1.8; color: var(--text-dark); margin-bottom: 1rem; font-size: 1rem;">${this.renderRich(block.text)}</div>`;
                    break;
                case 'sidebox':
                    const style = block.style || 'study';
                    container.innerHTML = `
                        <div class="sidebar-section ${style}" style="margin-bottom: 1.25rem;">
                            <h4 style="margin: 0 0 0.5rem 0; font-size: 1.1rem; font-weight: bold;">${block.title || 'Note'}</h4>
                            <div style="line-height: 1.6; font-size: 0.95rem;">${this.renderRich(block.text)}</div>
                        </div>
                    `;
                    break;
                case 'question':
                    container.innerHTML = `
                        <div class="question-block">
                            <div class="q-text">❓ ${this.renderRich(block.text)}</div>
                            <button class="reveal-btn"
                                    onclick="const a = this.nextElementSibling; a.classList.toggle('revealed'); this.textContent = a.classList.contains('revealed') ? '🙈 Hide Answer' : '💡 Show Answer';">💡 Show Answer</button>
                            <div class="q-answer">${this.renderRich(block.answer)}</div>
                        </div>
                    `;
                    break;
                case 'task':
                    container.innerHTML = `
                        <div class="task-block">
                            <span class="task-label">📋 Task</span>
                            <h4>${block.title || 'Task'}</h4>
                            <div class="task-body">${this.renderRich(block.text)}</div>
                        </div>
                    `;
                    break;
                case 'image':
                    container.innerHTML = `
                        <div class="img-frame" style="width: 100%;">
                            <img src="${block.src || ''}" alt="${block.alt || ''}"
                                 style="box-shadow: var(--shadow); max-width: 100%; border-radius: 8px;"
                                 onerror="this.src='/static/images/placeholder.png'">
                            ${block.caption ? `<div style="font-size: 0.85rem; color: var(--text-light); text-align: center; margin-top: 4px;">${block.caption}</div>` : ''}
                        </div>
                    `;
                    break;
                case 'video':
                    if (!block.src) {
                        container.innerHTML = `<p style="color: var(--text-light); text-align: center;">[Video block - No source link provided]</p>`;
                    } else if (block.src.includes('drive.google.com') || block.src.includes('youtube.com') || block.src.includes('youtu.be') || block.src.includes('embed')) {
                        container.innerHTML = `
                            <div style="margin: 1.5rem 0;">
                                <div class="video-container">
                                    <iframe src="${this.getVideoEmbedUrl(block.src)}" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen referrerpolicy="strict-origin-when-cross-origin"></iframe>
                                </div>
                                <div style="font-size: 0.85rem; color: var(--text-light); text-align: center; font-weight: bold; margin-top: 0.25rem;">🎥 ${block.title || 'Video Lecture'}</div>
                            </div>
                        `;
                    } else {
                        container.innerHTML = `
                            <div style="margin: 1.5rem 0;">
                                <div class="video-container">
                                    <video src="${block.src}" controls style="width: 100%; height: 100%;"></video>
                                </div>
                                <div style="font-size: 0.85rem; color: var(--text-light); text-align: center; font-weight: bold; margin-top: 0.25rem;">🎥 ${block.title || 'Video Lecture'}</div>
                            </div>
                        `;
                    }
                    break;
                case 'pptx':
                    if (!block.src) {
                        container.innerHTML = `<p style="color: var(--text-light); text-align: center;">[PowerPoint block - No presentation link provided]</p>`;
                    } else {
                        container.innerHTML = `
                            <div style="margin: 1.5rem 0;">
                                <div class="pptx-container">
                                    <iframe src="${this.getPptxEmbedUrl(block.src)}" allowfullscreen></iframe>
                                </div>
                                <div style="font-size: 0.85rem; color: var(--text-light); text-align: center; font-weight: bold; margin-top: 0.25rem;">📊 Presentation: ${block.title || 'PowerPoint Slides'}</div>
                            </div>
                        `;
                    }
                    break;
                case 'code':
                    const codeLang = block.language || 'python';
                    const escapedTitle = this.escapeHtml(block.title || '');
                    const escapedFilename = this.escapeHtml(block.filename || '');
                    const codeTitle = block.title ? `<div style="padding: 0.75rem 1rem; font-size: 0.85rem; font-weight: 600; color: #d4d4d4;">${escapedTitle}</div>` : '';
                    const codeHeader = block.filename ? `<div style="padding: 0.5rem 1rem; font-size: 0.75rem; color: #9cdcfe; font-family: 'Fira Code', monospace; background: #252526;">${escapedFilename}</div>` : '';
                    container.innerHTML = `
                        <div style="background: #1e1e1e; border-radius: 8px; overflow: hidden; margin: 1.5rem 0; box-shadow: var(--shadow);">
                            <div style="background: #2d2d30; padding: 0.75rem 1rem; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #3e3e42;">
                                <div style="display: flex; align-items: center; gap: 0.5rem;">
                                    <span style="font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.05em; color: #858585; font-weight: 600;">Code</span>
                                    <span style="font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.05em; color: #6a9955;">${codeLang}</span>
                                </div>
                                <div style="display: flex; gap: 0.5rem;" class="code-actions-${index}"></div>
                            </div>
                            ${codeTitle}
                            ${codeHeader}
                            <pre style="margin: 0; padding: 1rem; overflow-x: auto; font-family: 'Fira Code', 'Courier New', monospace; font-size: 0.9rem; line-height: 1.5; background: #1e1e1e;"><code class="language-${codeLang}" style="color: #d4d4d4;">${this.escapeHtml(block.code || '')}</code></pre>
                        </div>
                    `;
                    // Create buttons using DOM methods to avoid attribute breaking
                    const actionsDiv = container.querySelector(`.code-actions-${index}`);
                    if (actionsDiv) {
                        const btnStyle = "padding: 0.4rem 0.8rem; font-size: 0.75rem; border: 1px solid #3e3e42; border-radius: 4px; background: transparent; cursor: pointer; transition: all 0.2s;";

                        const fullscreenBtn = document.createElement('button');
                        fullscreenBtn.textContent = '⛶ Fullscreen';
                        fullscreenBtn.title = 'View fullscreen';
                        fullscreenBtn.style.cssText = btnStyle + "color: #d4d4d4;";
                        fullscreenBtn.onclick = () => window.app.openCodeInFullscreen(index);
                        actionsDiv.appendChild(fullscreenBtn);

                        const copyBtn = document.createElement('button');
                        copyBtn.textContent = '📋 Copy';
                        copyBtn.title = 'Copy code';
                        copyBtn.style.cssText = btnStyle + "color: #d4d4d4;";
                        copyBtn.onclick = () => window.app.copyCodeToClipboard(index, copyBtn);
                        actionsDiv.appendChild(copyBtn);

                        if (codeLang === 'python') {
                            const runBtn = document.createElement('button');
                            runBtn.textContent = '▶ Run';
                            runBtn.title = 'Run on Online Python';
                            runBtn.style.cssText = btnStyle + "color: #9cdcfe;";
                            runBtn.onclick = () => window.app.openInPythonAnywhere(index);
                            actionsDiv.appendChild(runBtn);
                        }
                    }
                    // Highlight the code block after rendering
                    setTimeout(() => {
                        const codeEl = container.querySelector('code');
                        if (codeEl && window.hljs) {
                            hljs.highlightElement(codeEl);
                        }
                    }, 0);
                    break;
            }
        }
    }

    // --- State Update Helpers ---
    updatePageTitle(val) {
        this.currentContent.title = val;
        const pageTitleText = document.getElementById('pageTitleText');
        if (pageTitleText) {
            pageTitleText.textContent = val;
        }
    }

    updateBlockText(idx, val) {
        this.currentContent.blocks[idx].text = val.trim();
        this.markDirty();
    }

    updateBlockTitle(idx, val) {
        this.currentContent.blocks[idx].title = val;
        this.markDirty();
    }

    updateBlockSrc(idx, val) {
        this.currentContent.blocks[idx].src = val;
        this.markDirty();
    }

    updateBlockAlt(idx, val) {
        this.currentContent.blocks[idx].alt = val;
        this.markDirty();
    }

    updateBlockAnswer(idx, val) {
        this.currentContent.blocks[idx].answer = val;
        this.markDirty();
    }

    updateBlockAlign(idx, val) {
        this.currentContent.blocks[idx].align = val;
        this.markDirty();
        this.rerender();
    }

    updateBlockSide(idx, val) {
        this.currentContent.blocks[idx].side = val;
        this.markDirty();
        this.rerender();
    }

    updateBlockCaption(idx, val) {
        this.currentContent.blocks[idx].caption = val;
        this.markDirty();
    }

    updateBlockCodeContent(idx, val) {
        this.currentContent.blocks[idx].code = val;
        this.markDirty();
    }

    updateBlockCodeLanguage(idx, val) {
        this.currentContent.blocks[idx].language = val;
        this.markDirty();
        this.rerender();
    }

    updateBlockFilename(idx, val) {
        this.currentContent.blocks[idx].filename = val;
        this.markDirty();
        this.rerender();
    }

    escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, m => map[m]);
    }

    copyCodeToClipboard(idx, btn) {
        const block = this.currentContent.blocks[idx];
        if (!block || !block.code) return;
        navigator.clipboard.writeText(block.code).then(() => {
            const originalText = btn.textContent;
            btn.textContent = '✓ Copied!';
            btn.style.borderColor = '#6a9955';
            btn.style.color = '#6a9955';
            setTimeout(() => {
                btn.textContent = originalText;
                btn.style.borderColor = '#3e3e42';
                btn.style.color = '#d4d4d4';
            }, 2000);
        }).catch(err => {
            console.error('Copy failed:', err);
            alert('Failed to copy code. Try using Ctrl+C instead.');
        });
    }

    openCodeInFullscreen(idx) {
        const block = this.currentContent.blocks[idx];
        if (!block) return;
        const codeLang = block.language || 'python';
        const html = `
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <title>${block.title || 'Code Snippet'}</title>
                <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/atom-one-dark.min.css">
                <style>
                    * { margin: 0; padding: 0; box-sizing: border-box; }
                    body { background: #1e1e1e; color: #d4d4d4; font-family: 'Fira Code', 'Courier New', monospace; }
                    .code-viewer { display: flex; flex-direction: column; height: 100vh; }
                    .code-header { background: #2d2d30; padding: 1rem; border-bottom: 1px solid #3e3e42; display: flex; justify-content: space-between; align-items: center; }
                    .code-header h1 { font-size: 1.2rem; margin: 0; }
                    .code-actions { display: flex; gap: 0.5rem; }
                    .code-actions button { padding: 0.5rem 1rem; border: 1px solid #3e3e42; border-radius: 4px; background: transparent; color: #d4d4d4; cursor: pointer; font-size: 0.9rem; transition: all 0.2s; }
                    .code-actions button:hover { background: #3e3e42; border-color: #6a9955; color: #6a9955; }
                    .code-content { flex: 1; overflow: auto; padding: 1rem; }
                    pre { margin: 0; font-size: 1rem; line-height: 1.6; background: #1e1e1e !important; }
                    code { font-family: 'Fira Code', 'Courier New', monospace; }
                </style>
            </head>
            <body>
                <div class="code-viewer">
                    <div class="code-header">
                        <div>
                            <h1>${block.title || 'Code Snippet'}</h1>
                            ${block.filename ? `<small style="color: #9cdcfe;">${block.filename}</small>` : ''}
                        </div>
                        <div class="code-actions">
                            <button onclick="copyCode(this)">📋 Copy</button>
                            <button onclick="window.close()">✕ Close</button>
                        </div>
                    </div>
                    <div class="code-content">
                        <pre><code class="language-${codeLang}" id="codeContent">${this.escapeHtml(block.code || '')}</code></pre>
                    </div>
                </div>
                <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"><\/script>
                <script>
                    function copyCode(btn) {
                        const code = document.getElementById('codeContent').textContent;
                        navigator.clipboard.writeText(code).then(() => {
                            const originalText = btn.textContent;
                            btn.textContent = '✓ Copied!';
                            btn.style.borderColor = '#6a9955';
                            btn.style.color = '#6a9955';
                            setTimeout(() => {
                                btn.textContent = originalText;
                                btn.style.borderColor = '#3e3e42';
                                btn.style.color = '#d4d4d4';
                            }, 2000);
                        }).catch(err => {
                            alert('Failed to copy code. Try Ctrl+A then Ctrl+C instead.');
                        });
                    }
                    if (window.hljs) {
                        document.querySelectorAll('code').forEach(block => {
                            hljs.highlightElement(block);
                        });
                    }
                </script>
            </body>
            </html>
        `;
        const blob = new Blob([html], { type: 'text/html' });
        const url = URL.createObjectURL(blob);
        window.open(url, 'code-viewer', 'width=900,height=600');
    }

    openInPythonAnywhere(idx) {
        const block = this.currentContent.blocks[idx];
        if (!block || !block.code) return;
        const encodedCode = encodeURIComponent(block.code);
        const onlinePython = `https://www.online-python.com/`;
        const win = window.open(onlinePython, 'online-python');
        if (win) {
            setTimeout(() => {
                win.focus();
                alert('Online Python opened. Paste your code in the editor to run it.');
            }, 1000);
        }
    }

    // --- Canva-style image resizing (drag the corner handle) ---
    startImageResize(e, index) {
        e.preventDefault();
        e.stopPropagation();

        this.pushUndo();

        const frame = document.getElementById(`imgFrame_${index}`);
        if (!frame) return;
        const wrapper = frame.closest('.canvas-block');
        const column = wrapper.parentElement;
        const startX = e.clientX;
        const startWidth = wrapper.getBoundingClientRect().width;
        const columnWidth = column.clientWidth;

        frame.classList.add('resizing');
        wrapper.draggable = false; // don't trigger block drag while resizing

        const onMove = (ev) => {
            const px = Math.max(60, startWidth + (ev.clientX - startX));
            const pct = Math.min(100, Math.max(10, Math.round((px / columnWidth) * 100)));
            this.currentContent.blocks[index].width = pct;
            wrapper.style.width = pct + '%';
        };
        const onUp = () => {
            document.removeEventListener('mousemove', onMove);
            document.removeEventListener('mouseup', onUp);
            frame.classList.remove('resizing');
            wrapper.draggable = true;
            this.markDirty();
        };
        document.addEventListener('mousemove', onMove);
        document.addEventListener('mouseup', onUp);
    }

    updateBlockLevel(idx, val) {
        this.pushUndo();
        this.currentContent.blocks[idx].level = val;
        this.markDirty();
        this.rerender();
    }

    updateBlockStyle(idx, val) {
        this.pushUndo();
        this.currentContent.blocks[idx].style = val;
        this.markDirty();
        this.rerender();
    }

    // --- Spec 18: Block selection and manipulation ---
    selectBlock(idx) {
        // Remove selection from previous block
        if (this.selectedBlockIndex !== null) {
            const prevBlock = document.querySelector(`[data-index="${this.selectedBlockIndex}"]`);
            if (prevBlock) {
                prevBlock.classList.remove('block-selected');
            }
        }

        this.selectedBlockIndex = idx;

        // Apply selection to new block
        if (idx !== null) {
            const block = document.querySelector(`[data-index="${idx}"]`);
            if (block) {
                block.classList.add('block-selected');
                block.scrollIntoView({ block: 'nearest' });
            }
        }
    }

    duplicateBlock(idx) {
        this.pushUndo();
        const block = JSON.parse(JSON.stringify(this.currentContent.blocks[idx]));
        this.currentContent.blocks.splice(idx + 1, 0, block);
        this.selectBlock(idx + 1);
        this.markDirty();
        this.rerender();
    }

    moveBlockUp(idx) {
        if (idx <= 0) return;
        this.pushUndo();
        const blocks = this.currentContent.blocks;
        [blocks[idx - 1], blocks[idx]] = [blocks[idx], blocks[idx - 1]];
        this.selectBlock(idx - 1);
        this.markDirty();
        this.rerender();
    }

    moveBlockDown(idx) {
        if (idx >= this.currentContent.blocks.length - 1) return;
        this.pushUndo();
        const blocks = this.currentContent.blocks;
        [blocks[idx], blocks[idx + 1]] = [blocks[idx + 1], blocks[idx]];
        this.selectBlock(idx + 1);
        this.markDirty();
        this.rerender();
    }

    // --- Spec 16: Insert block at specific index ---
    makeBlock(kind) {
        const templates = {
            heading: { type: 'heading', level: 3, text: 'Heading' },
            paragraph: { type: 'text', text: '' },
            study: { type: 'sidebox', style: 'study', title: '💡 Study Tip', text: '' },
            theory: { type: 'sidebox', style: 'theory', title: '🤔 Theory of Knowledge', text: '' },
            applied: { type: 'sidebox', style: 'applied', title: '🛠️ Applied Work', text: '' },
            vocab: { type: 'sidebox', style: 'vocab', title: '📖 Vocabulary', text: '' },
            funfact: { type: 'sidebox', style: 'funfact', title: '🎉 Fun Fact', text: '' },
            question: { type: 'question', text: '', answer: '' },
            task: { type: 'task', title: '', text: '' },
            image: { type: 'image', src: '', alt: '', width: 100, align: 'center' },
            video: { type: 'video', src: '', title: '', side: false },
            code: { type: 'code', language: 'python', title: 'Code Example', code: '', filename: '' }
        };
        return JSON.parse(JSON.stringify(templates[kind] || templates.paragraph));
    }

    insertBlockAt(index, block) {
        this.pushUndo();
        this.currentContent.blocks.splice(index, 0, block);
        this.markDirty();
        this.rerender();
        // Focus the new block after render
        setTimeout(() => {
            const blockEl = document.querySelector(`[data-index="${index}"]`);
            if (blockEl) {
                const editable = blockEl.querySelector('[contenteditable="true"]');
                if (editable) {
                    editable.focus();
                    const range = document.createRange();
                    range.setStart(editable, 0);
                    range.collapse(true);
                    const sel = window.getSelection();
                    sel.removeAllRanges();
                    sel.addRange(range);
                }
            }
        }, 0);
    }

    showInsertMenu(index) {
        this.insertAt = index;
        const insertMenu = document.getElementById('insertMenu');
        if (!insertMenu) return;

        const btn = document.querySelector(`.insert-btn[data-insert-at="${index}"]`);
        if (!btn) return;

        const rect = btn.getBoundingClientRect();
        insertMenu.style.left = rect.left + 'px';
        insertMenu.style.top = (rect.bottom + 5) + 'px';
        insertMenu.style.display = 'block';
    }

    hideInsertMenu() {
        const insertMenu = document.getElementById('insertMenu');
        if (insertMenu) {
            insertMenu.style.display = 'none';
        }
        this.insertAt = null;
    }

    insertBlockType(kind) {
        if (this.insertAt === null) return;
        const block = this.makeBlock(kind);
        this.insertBlockAt(this.insertAt, block);
        this.hideInsertMenu();
    }

    deleteBlockSilent(idx) {
        this.currentContent.blocks.splice(idx, 1);
    }

    // --- Reorder & Add/Delete Block Elements ---
    reorderBlocks(srcIdx, targetIdx) {
        this.pushUndo();
        const blocks = this.currentContent.blocks;
        const draggedBlock = blocks[srcIdx];

        // Remove from old position
        blocks.splice(srcIdx, 1);

        // Insert in new position
        blocks.splice(targetIdx, 0, draggedBlock);

        this.markDirty();
        this.rerender();
    }

    moveBlock(srcIdx, insertIdx) {
        this.pushUndo();
        const blocks = this.currentContent.blocks;
        const block = blocks[srcIdx];
        blocks.splice(srcIdx, 1);
        blocks.splice(insertIdx, 0, block);
        this.markDirty();
        this.rerender();
    }

    moveBlockToBottom(srcIdx) {
        this.pushUndo();
        const blocks = this.currentContent.blocks;
        const draggedBlock = blocks.splice(srcIdx, 1)[0];
        blocks.push(draggedBlock);
        this.markDirty();
        this.rerender();
    }

    deleteBlock(idx) {
        if (confirm("Are you sure you want to delete this block?")) {
            this.pushUndo();
            this.currentContent.blocks.splice(idx, 1);
            this.markDirty();
            this.rerender();
            this.selectBlock(null);
        }
    }

    addHeadingBlock(level) {
        const block = this.makeBlock('heading');
        block.level = level;
        block.text = `New Heading (Level ${level})`;
        this.pushUndo();
        this.currentContent.blocks.push(block);
        this.markDirty();
        this.rerender();
        this.scrollToBottom();
    }

    addParagraphBlock() {
        const block = this.makeBlock('paragraph');
        this.pushUndo();
        this.currentContent.blocks.push(block);
        this.markDirty();
        this.rerender();
        this.scrollToBottom();
    }

    addSideboxBlock(style) {
        const block = this.makeBlock(style);
        this.pushUndo();
        this.currentContent.blocks.push(block);
        this.markDirty();
        this.rerender();
        this.scrollToBottom();
    }

    addQuestionBlock() {
        const block = this.makeBlock('question');
        this.pushUndo();
        this.currentContent.blocks.push(block);
        this.markDirty();
        this.rerender();
        this.scrollToBottom();
    }

    addTaskBlock() {
        const block = this.makeBlock('task');
        this.pushUndo();
        this.currentContent.blocks.push(block);
        this.markDirty();
        this.rerender();
        this.scrollToBottom();
    }

    addImageBlock() {
        const block = this.makeBlock('image');
        this.pushUndo();
        this.currentContent.blocks.push(block);
        this.markDirty();
        this.rerender();
        this.scrollToBottom();
    }

    addVideoBlock() {
        const block = this.makeBlock('video');
        this.pushUndo();
        this.currentContent.blocks.push(block);
        this.markDirty();
        this.rerender();
        this.scrollToBottom();
    }

    addPptxBlock() {
        const block = { type: 'pptx', src: '', title: 'Presentation Slides Title' };
        this.pushUndo();
        this.currentContent.blocks.push(block);
        this.markDirty();
        this.rerender();
        this.scrollToBottom();
    }

    addCodeBlock() {
        const block = this.makeBlock('code');
        this.pushUndo();
        this.currentContent.blocks.push(block);
        this.markDirty();
        this.rerender();
        this.scrollToBottom();
    }

    handleImageUpload(index, input) {
        const file = input.files && input.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (e) => {
            const dataUri = e.target.result;
            // Update in-memory block
            if (this.currentContent && this.currentContent.blocks[index]) {
                this.currentContent.blocks[index].src = dataUri;
            }
            // Update the preview img immediately without re-rendering everything
            const preview = document.getElementById(`imgPreview_${index}`);
            if (preview) preview.src = dataUri;
        };
        reader.readAsDataURL(file);
    }

    handleVideoUpload(index, input) {
        const file = input.files && input.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (e) => {
            const dataUri = e.target.result;
            // Update in-memory block
            if (this.currentContent && this.currentContent.blocks[index]) {
                this.currentContent.blocks[index].src = dataUri;
            }
            // Update the video preview iframe
            const iframe = document.querySelector(`[data-index="${index}"] iframe`);
            if (iframe) {
                iframe.src = dataUri;
            }
            this.markDirty();
        };
        reader.readAsDataURL(file);
    }

    scrollToBottom() {
        setTimeout(() => {
            const panel = document.getElementById('contentView');
            if (panel) panel.scrollTop = panel.scrollHeight;
        }, 100);
    }

    // --- Action Button Toggle Controls ---
    toggleEditMode() {
        this.isEditMode = true;
        this.displayContent(this.currentContent);
    }

    // Return to the reading page this editor was opened from (bookFolder/pageId),
    // falling back to the editor's own view mode if the folder isn't a book page.
    returnToViewMode() {
        this.isDirty = false;
        const folder = this.currentFolder || '';
        const slash = folder.indexOf('/');
        if (slash > 0) {
            const bookFolder = folder.slice(0, slash);
            const pageId = folder.slice(slash + 1);
            window.location.href = `/book/${encodeURIComponent(bookFolder)}/page/${encodeURIComponent(pageId)}`;
            return;
        }
        // Not a book page — just drop back into the editor's read-only view
        if (window.history && window.history.replaceState) {
            window.history.replaceState(null, '', window.location.pathname);
        }
        this.loadContent(this.currentFolder, false);
    }

    cancelChanges() {
        if (confirm("Discard edits made since the last autosave?")) {
            this.returnToViewMode();
        }
    }

    async saveChanges() {
        if (!this.currentFolder) return;

        const saveBtn = document.getElementById('saveEditBtn');
        if (saveBtn) {
            saveBtn.disabled = true;
            saveBtn.textContent = 'Saving...';
        }

        try {
            const response = await fetch(`/api/content/${this.currentFolder}/save`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(this.currentContent)
            });

            const result = await response.json();

            if (result.success) {
                // Saved — head back to the reading page we came from
                this.returnToViewMode();
            } else {
                throw new Error(result.error || 'Failed to save changes');
            }
        } catch (err) {
            alert(`Error saving edits: ${err.message}`);
            if (saveBtn) {
                saveBtn.disabled = false;
                saveBtn.textContent = '💾 Save Changes';
            }
        }
    }

    async deletePage() {
        if (!this.currentFolder) return;

        const confirmed = confirm(`Are you sure you want to delete "${this.currentContent.title || 'this page'}"? This cannot be undone.`);
        if (!confirmed) return;

        try {
            const url = `/api/pages/${encodeURIComponent(this.currentFolder)}`;
            console.log('Deleting page. Folder:', this.currentFolder, 'URL:', url);

            const response = await fetch(url, {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' }
            });

            console.log('Delete response status:', response.status);
            const result = await response.json();
            console.log('Delete response:', result);

            if (result.success) {
                // Redirect to syllabus manager
                window.location.href = '/syllabus';
            } else {
                alert(`Error deleting page: ${result.error || 'Unknown error'}`);
            }
        } catch (err) {
            console.error('Delete error:', err);
            alert(`Error deleting page: ${err.message}`);
        }
    }

    // --- Embed Formatter Utilities ---
    getVideoEmbedUrl(url) {
        if (!url) return '';
        url = url.trim();

        // Google Drive: extract file ID and return embed URL
        if (url.includes('drive.google.com')) {
            const fileIdMatch = url.match(/\/d\/([a-zA-Z0-9-_]+)/);
            if (fileIdMatch) {
                const fileId = fileIdMatch[1];
                return `https://drive.google.com/file/d/${fileId}/preview`;
            }
        }

        // YouTube: extract video ID
        if (url.includes('youtube.com') || url.includes('youtu.be')) {
            let videoId = '';
            if (url.includes('youtube.com/watch')) {
                try {
                    const urlObj = new URL(url);
                    videoId = urlObj.searchParams.get('v');
                } catch (e) {
                    const parts = url.split('v=');
                    if (parts[1]) videoId = parts[1].split('&')[0];
                }
            } else if (url.includes('youtu.be/')) {
                videoId = url.split('youtu.be/')[1].split('?')[0];
            } else if (url.includes('youtube.com/embed/') || url.includes('youtube-nocookie.com/embed/')) {
                videoId = url.split('/embed/')[1].split(/[?&#]/)[0];
            } else if (url.includes('youtube.com/shorts/')) {
                videoId = url.split('/shorts/')[1].split(/[?&#]/)[0];
            }
            return videoId ? `https://www.youtube-nocookie.com/embed/${videoId}?rel=0&modestbranding=1&playsinline=1` : url;
        }

        // Direct video file (MP4, WebM, etc.) or data URI
        return url;
    }

    getYouTubeEmbedUrl(url) {
        // Legacy method - now uses getVideoEmbedUrl
        return this.getVideoEmbedUrl(url);
    }

    getPptxEmbedUrl(url) {
        url = url.trim();
        if (url.startsWith('<iframe')) {
            const match = url.match(/src="([^"]+)"/);
            if (match) return match[1];
        }
        if (url.includes('docs.google.com/presentation')) {
            if (!url.endsWith('/embed') && url.includes('/pub')) {
                return url.split('?')[0] + '/embed';
            }
            if (url.includes('/edit')) {
                return url.replace(/\/edit.*$/, '/embed');
            }
            return url;
        }
        if (url.includes('onedrive.live.com/embed') || url.includes('sharepoint.com')) {
            return url;
        }
        return `https://view.officeapps.live.com/op/embed.aspx?src=${encodeURIComponent(url)}`;
    }

    // --- Search Utility ---
    async performSearch() {
        const query = document.getElementById('searchInput').value.trim();
        const resultsDiv = document.getElementById('searchResults');

        if (!query) {
            if (resultsDiv) resultsDiv.innerHTML = '';
            return;
        }

        try {
            const response = await fetch('/api/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query })
            });

            const data = await response.json();
            if (resultsDiv) {
                resultsDiv.innerHTML = '';

                if (data.results.length === 0) {
                    resultsDiv.innerHTML = '<p style="color: #7f8c8d; text-align: center; padding: 1rem;">No results found</p>';
                    return;
                }

                data.results.forEach(result => {
                    const div = document.createElement('div');
                    div.className = 'search-result-item';
                    div.innerHTML = `
                        <h4>${this.truncate(result.title, 25)}</h4>
                        <p>${result.matched_fields.join(', ')}</p>
                    `;
                    div.addEventListener('click', () => {
                        window.location.href = `/editor/${result.folder}`;
                    });
                    resultsDiv.appendChild(div);
                });
            }
        } catch (error) {
            if (resultsDiv) {
                resultsDiv.innerHTML = `<p style="color: var(--danger);">Error: ${error.message}</p>`;
            }
        }
    }

    // --- Content Formatting Utilities ---
    // Blocks edited with the rich text toolbar store HTML; older scraped
    // blocks store plain text with markdown-ish markers ("- " bullets, blank-line
    // paragraph breaks). Render either the same way in both edit mode and the
    // read-only preview, so what you edit is what students see.
    renderRich(text) {
        if (!text) return '';
        return text.includes('<') ? text : this.linkifyText(text);
    }

    linkifyText(text) {
        if (!text) return '';
        const chunks = text.split(/\n\n+/);
        const htmlChunks = chunks.map(chunk => {
            const lines = chunk.split('\n');
            const bulletCount = lines.filter(l => l.trim().startsWith('- ')).length;
            if (bulletCount > 0 && bulletCount >= lines.length - 1) {
                let out = '';
                let items = '';
                lines.forEach(line => {
                    const t = line.trim();
                    if (t.startsWith('- ')) {
                        items += `<li>${t.slice(2)}</li>`;
                    } else if (t) {
                        out += `<p style="margin:0 0 0.5rem; font-weight:600;">${t}</p>`;
                    }
                });
                return out + (items ? `<ul style="margin:0 0 1rem 1.25rem; padding:0;">${items}</ul>` : '');
            }
            return `<p style="margin:0 0 1rem;">${lines.join('<br>')}</p>`;
        });
        return htmlChunks.join('')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/__(.*?)__/g, '<em>$1</em>');
    }

    showStatus(message, type, element) {
        if (!element) return;
        element.textContent = message;
        element.className = `status-message show ${type}`;

        if (type !== 'loading') {
            setTimeout(() => {
                element.classList.remove('show');
            }, 4000);
        }
    }

    truncate(text, length) {
        return text.length > length ? text.substring(0, length) + '...' : text;
    }
}

// Initialize application on document ready
document.addEventListener('DOMContentLoaded', () => {
    new ContentScraperApp();
});

// Export helper for inline onclick events
function performSearch() {
    if (window.app) window.app.performSearch();
}

// Force fresh reload without cache
function forceRefreshNoCache() {
    console.log('🔄 Clearing caches and reloading...');
    if (window.app) {
        window.app.clearCachesAndReload();
    } else {
        // Fallback if app isn't initialized yet
        localStorage.clear();
        sessionStorage.clear();
        window.location.reload(true);
    }
}
