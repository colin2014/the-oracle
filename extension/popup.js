// Default server URL
const DEFAULT_SERVER = 'http://localhost:5000';

let navigationItems = [];

// Load settings on popup open
document.addEventListener('DOMContentLoaded', async () => {
    const settings = await chrome.storage.local.get('serverUrl');
    const serverUrl = settings.serverUrl || DEFAULT_SERVER;
    document.getElementById('serverUrl').value = serverUrl;

    // Check if background queue is already running
    await checkQueueStatus();

    // Setup event listeners
    document.getElementById('saveSettings').addEventListener('click', saveSettings);
    document.getElementById('scrapeBtn').addEventListener('click', scrapePage);
    document.getElementById('scrapeBatchBtn').addEventListener('click', scrapeBatch);
    document.getElementById('stopScrapeBtn').addEventListener('click', stopScrape);
    document.getElementById('openDashboard').addEventListener('click', openDashboard);
    document.getElementById('selectAllNav').addEventListener('change', toggleSelectAll);

    // Setup background communication listener
    chrome.runtime.onMessage.addListener((message) => {
        if (message.action === 'queueProgress') {
            showProgress(message.current, message.total, message.text);
        } else if (message.action === 'queueFinished') {
            onQueueComplete();
        } else if (message.action === 'queueError') {
            onQueueError(message.message);
        }
    });
});

async function checkQueueStatus() {
    try {
        const response = await chrome.runtime.sendMessage({ action: 'getQueueStatus' });
        if (response && response.isRunning) {
            switchToProgressMode();
            showProgress(response.current, response.total, response.text);
        } else {
            // Analyze current page if no queue is running
            await analyzeCurrentPage();
        }
    } catch (e) {
        // Fallback
        await analyzeCurrentPage();
    }
}

async function analyzeCurrentPage() {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab || !tab.url || tab.url.startsWith('chrome://')) return;

    document.getElementById('pageTitle').value = tab.title || '';

    try {
        const results = await chrome.scripting.executeScript({
            target: { tabId: tab.id },
            func: analyzePageContent
        });

        if (results && results[0] && results[0].result) {
            const { textLength, imageCount, sectionCount, navigation } = results[0].result;
            document.getElementById('textCount').textContent = formatBytes(textLength);
            document.getElementById('imageCount').textContent = imageCount;
            document.getElementById('sectionCount').textContent = sectionCount;

            navigationItems = navigation || [];
            renderNavigationList(navigationItems);
        }
    } catch (err) {
        console.error("Analysis injection failed: ", err);
    }
}

function analyzePageContent() {
    const bodyText = document.body.innerText || '';
    const textLength = bodyText.length;
    const images = document.querySelectorAll('img');
    const imageCount = images.length;

    const headings = document.querySelectorAll('h1, h2, h3, h4');
    const regions = document.querySelectorAll('[role="region"], [role="contentinfo"]');
    const sectionCount = headings.length + regions.length;

    // Helper functions for DOM analysis
    function estimateLevel(element, text) {
        text = text.trim();
        if (text.startsWith('Theme')) return 1;
        if (text === 'Introduction') return 2;
        
        if (/^[A-Z]\.?\d+\.\d+\.\d+/.test(text)) return 4;
        if (/^[A-Z]\.?\d+\.\d+/.test(text)) return 3;
        if (/^[A-Z]\.?\d+/.test(text)) return 2;

        let level = 1;
        let parent = element.parentElement;
        while (parent && level < 5) {
            if (parent.classList.toString().includes('sub') ||
                parent.tagName === 'UL' ||
                parent.tagName === 'OL') {
                level++;
            }
            parent = parent.parentElement;
        }
        return level;
    }

    function extractNavigation() {
        const nav = [];
        
        // Robust detection of books listing page
        const bookIds = new Set();
        const matchPattern = /\/books\/(\d+)\/\d+/;
        document.querySelectorAll('a[href]').forEach(a => {
            const href = a.getAttribute('href') || '';
            const match = href.match(matchPattern);
            if (match) bookIds.add(match[1]);
        });
        
        const isBooksListing = bookIds.size > 1 || /^\/books\/?$/.test(location.pathname);
        
        if (isBooksListing) {
            const pattern = new RegExp('/books/\\d+/\\d+');
            const seen = new Set();
            document.querySelectorAll('a[href]').forEach(a => {
                let url;
                try { url = new URL(a.getAttribute('href'), location.href); } catch (e) { return; }
                if (url.protocol !== location.protocol) return;
                if (url.protocol !== 'file:' && url.origin !== location.origin) return;
                const path = url.pathname.replace(/\/+$/, '');
                if (!pattern.test(path)) return;
                const uOrigin = url.origin === 'null' ? url.protocol + '//' : url.origin;
                const clean = uOrigin + path;
                if (seen.has(clean)) return;

                let title = '';
                const headingEl = a.querySelector('h1,h2,h3,h4,[class*="title"],[class*="name"]');
                if (headingEl) title = (headingEl.textContent || '').trim();
                if (!title) title = (a.innerText || a.textContent || '').trim().split('\n')[0].trim();
                if (!title) return;

                seen.add(clean);
                nav.push({
                    text: title.replace(/\s+/g, ' ').slice(0, 120),
                    href: clean,
                    level: 1
                });
            });
            return nav.slice(0, 400);
        }

        const menuContainer = document.querySelector('.menu-wp, [class*="menu-wp"], [class*="sidebar-nav"], [class*="navigation"]');
        const navElements = menuContainer ? menuContainer.querySelectorAll('a') : document.querySelectorAll('nav a, [role="navigation"] a, .nav a, .menu a');

        navElements.forEach(link => {
            const text = link.textContent.trim();
            const href = link.href;
            if (text && href && !href.startsWith('javascript')) {
                if (!nav.some(item => item.text === text)) {
                    nav.push({
                        text,
                        href,
                        level: estimateLevel(link, text)
                    });
                }
            }
        });
        return nav.slice(0, 400);
    }

    return {
        textLength,
        imageCount,
        sectionCount,
        navigation: extractNavigation()
    };
}

function renderNavigationList(navItems) {
    const navSection = document.getElementById('navSection');
    const navList = document.getElementById('navList');
    const scrapeBatchBtn = document.getElementById('scrapeBatchBtn');

    if (!navItems || navItems.length === 0) {
        navSection.style.display = 'none';
        scrapeBatchBtn.style.display = 'none';
        return;
    }

    navSection.style.display = 'block';
    scrapeBatchBtn.style.display = 'block';
    navList.innerHTML = '';

    navItems.forEach((item, index) => {
        const div = document.createElement('div');
        div.className = `nav-list-item level-${item.level}`;
        
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.id = `nav_item_${index}`;
        checkbox.value = index;
        checkbox.checked = true;

        const label = document.createElement('span');
        label.textContent = item.text;
        label.addEventListener('click', () => {
            checkbox.checked = !checkbox.checked;
        });

        div.appendChild(checkbox);
        div.appendChild(label);
        navList.appendChild(div);
    });
}

function toggleSelectAll(e) {
    const checkboxes = document.querySelectorAll('#navList input[type="checkbox"]');
    checkboxes.forEach(cb => cb.checked = e.target.checked);
}

function formatBytes(bytes) {
    if (bytes === 0) return '0 bytes';
    const k = 1024;
    const sizes = ['bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

async function saveSettings() {
    const serverUrl = document.getElementById('serverUrl').value;
    if (!serverUrl) {
        showStatus('Please enter a server URL', 'error');
        return;
    }

    await chrome.storage.local.set({ serverUrl });
    showStatus('✓ Settings saved!', 'success');
}

async function scrapePage() {
    const serverUrl = document.getElementById('serverUrl').value;
    if (!serverUrl) {
        showStatus('Please configure server URL first', 'error');
        return;
    }

    const btn = document.getElementById('scrapeBtn');
    btn.disabled = true;
    showStatus('Analyzing page structure...', 'loading');

    try {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        if (!tab || !tab.url || tab.url.startsWith('chrome://')) {
            throw new Error('Cannot scrape internal chrome:// pages.');
        }

        // On a book page or books listing page, look for chapter/book links
        let chapterLinks = [];
        
        // Execute robust check on the tab
        const checkResult = await chrome.scripting.executeScript({
            target: { tabId: tab.id },
            func: () => {
                const bookIds = new Set();
                const matchPattern = /\/books\/(\d+)\/\d+/;
                document.querySelectorAll('a[href]').forEach(a => {
                    const href = a.getAttribute('href') || '';
                    const match = href.match(matchPattern);
                    if (match) bookIds.add(match[1]);
                });
                
                const isBookPage = bookIds.size === 1 || /\/books\/\d+\//.test(location.pathname);
                const isBooksListing = bookIds.size > 1 || /^\/books\/?$/.test(location.pathname);
                return { isBookPage, isBooksListing };
            }
        });
        
        const isBookOrListing = checkResult && checkResult[0] && checkResult[0].result;
        
        if (isBookOrListing && (isBookOrListing.isBookPage || isBookOrListing.isBooksListing)) {
            const chapterLinksResult = await chrome.scripting.executeScript({
                target: { tabId: tab.id },
                func: discoverBookLinks
            });
            chapterLinks = (chapterLinksResult && chapterLinksResult[0] && chapterLinksResult[0].result) || [];
        }

        if (chapterLinks.length > 0) {
            // Multi-page book or listing: hand the whole job to the background queue so it
            // survives the popup closing. crawl:true makes the queue re-scan each
            // visited page for newly revealed sub-links.
            const queue = [
                { text: tab.title || 'Start Page', href: tab.url },
                ...chapterLinks.map(l => ({ text: l.title, href: l.href }))
            ];
            switchToProgressMode();
            showProgress(0, queue.length, 'Starting book scrape...');

            const response = await chrome.runtime.sendMessage({
                action: 'startScrapeQueue',
                tabId: tab.id,
                queue: queue,
                serverUrl: serverUrl,
                crawl: true
            });
            if (!response || !response.success) {
                throw new Error((response && response.error) || 'Failed to start scraping queue');
            }
        } else {
            // Single page - use original logic
            showStatus('Extracting content...', 'loading');
            await scrapeSinglePage(tab, serverUrl);
        }
    } catch (error) {
        showStatus(`✗ Error: ${error.message}`, 'error');
        onQueueError(error.message);
    } finally {
        btn.disabled = false;
    }
}

/**
 * Injected into the page.
 * - Inside a book (/books/<bookId>/<pageId>): find every SAME-book page link.
 * - On the books listing (/books): find every book card's entry link.
 * Excludes the page we're on. Mirrored in background.js for crawl mode.
 */
function discoverBookLinks() {
    console.log("[Extension Debug] discoverBookLinks started on", location.pathname);
    const bookIds = new Set();
    const matchPattern = /\/books\/(\d+)\/\d+/;
    document.querySelectorAll('a[href]').forEach(a => {
        const href = a.getAttribute('href') || '';
        const match = href.match(matchPattern);
        if (match) bookIds.add(match[1]);
    });
    
    console.log("[Extension Debug] bookIds found on page:", Array.from(bookIds));
    
    let bookId = null;
    if (bookIds.size === 1) {
        bookId = Array.from(bookIds)[0];
    } else {
        const m = location.pathname.match(/\/books\/(\d+)\//);
        if (m) bookId = m[1];
    }
    
    console.log("[Extension Debug] bookId determined:", bookId);

    const origin = location.origin === 'null' ? location.protocol + '//' : location.origin;
    const here = origin + location.pathname.replace(/\/+$/, '');
    const pattern = bookId
        ? new RegExp('/books/' + bookId + '/\\d+')   // same-book pages only
        : new RegExp('/books/\\d+/\\d+');            // listing: any book entry

    const links = [];
    const seen = new Set();
    document.querySelectorAll('a[href]').forEach(a => {
        let url;
        try { url = new URL(a.getAttribute('href'), location.href); } catch (e) { return; }
        if (url.protocol !== location.protocol) return;
        if (url.protocol !== 'file:' && url.origin !== location.origin) return;
        const path = url.pathname.replace(/\/+$/, '');
        if (!pattern.test(path)) return;
        const uOrigin = url.origin === 'null' ? url.protocol + '//' : url.origin;
        const clean = uOrigin + path;
        if (clean === here || seen.has(clean)) return;

        // Prefer a heading inside the link (book cards wrap title + author +
        // artwork); fall back to the first text line.
        let title = '';
        const headingEl = a.querySelector('h1,h2,h3,h4,[class*="title"],[class*="name"]');
        if (headingEl) title = (headingEl.textContent || '').trim();
        if (!title) title = (a.innerText || a.textContent || '').trim().split('\n')[0].trim();
        if (!title) return;

        seen.add(clean);
        links.push({ title: title.replace(/\s+/g, ' ').slice(0, 120), href: clean });
    });
    console.log("[Extension Debug] returning links:", links.length);
    return links;
}

/**
 * Scrape a single page (original logic)
 */
async function scrapeSinglePage(tab, serverUrl) {
    // Expand collapsed markschemes
    await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        func: () => {
            document.querySelectorAll('.question .link, .question span.link, .question a').forEach(el => {
                if (/show\s*markscheme/i.test(el.textContent || '')) el.click();
            });
        }
    });
    await new Promise(r => setTimeout(r, 1000));

    const results = await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        func: extractPageContent
    });

    if (!results || !results[0] || !results[0].result) {
        throw new Error('Failed to extract content');
    }

    const pageData = results[0].result;
    pageData.url = tab.url;
    pageData.title = pageData.title || tab.title;

    showStatus('Downloading images...', 'loading');
    pageData.images = await fetchImagesAsBase64(pageData.images || []);

    const response = await fetch(`${serverUrl}/api/scrape-dom`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(pageData)
    });

    const result = await response.json();

    if (result.success) {
        showStatus('✓ Page scraped successfully!', 'success');
        setTimeout(() => {
            openDashboard();
        }, 1500);
    } else {
        throw new Error(result.error || 'Scraping failed');
    }
}

// NOTE: chapter scraping is handled by the background service worker queue
// (background.js runScrapeQueue with crawl:true) — a loop in the popup dies
// the moment the popup closes, which is why per-chapter scraping used to stop
// after the first page.

/**
 * Fetch images as base64 data URIs using the extension's authenticated browser session.
 * The extension popup runs with full cookie access, so it can fetch CDN-protected images.
 */
async function fetchImagesAsBase64(images) {
    const enriched = [];
    for (const img of images) {
        const src = img.src || img.original_src || '';
        if (!src || src.startsWith('data:') || src.startsWith('blob:')) {
            enriched.push(img);
            continue;
        }
        try {
            const response = await fetch(src, { credentials: 'include' });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const contentType = response.headers.get('content-type') || 'image/png';
            const buffer = await response.arrayBuffer();
            const bytes = new Uint8Array(buffer);
            let binary = '';
            for (let i = 0; i < bytes.byteLength; i++) {
                binary += String.fromCharCode(bytes[i]);
            }
            const base64 = btoa(binary);
            enriched.push({
                ...img,
                src: `data:${contentType};base64,${base64}`,
                original_src: src
            });
        } catch (err) {
            console.warn(`Could not fetch image as base64: ${src}`, err.message);
            enriched.push(img); // keep original src as fallback
        }
    }
    return enriched;
}

async function scrapeBatch() {
    const serverUrl = document.getElementById('serverUrl').value.trim();
    if (!serverUrl) {
        showStatus('Please configure server URL first', 'error');
        return;
    }

    // Get checked indices
    const checkedCheckboxes = document.querySelectorAll('#navList input[type="checkbox"]:checked');
    if (checkedCheckboxes.length === 0) {
        showStatus('Please select at least one page to scrape', 'error');
        return;
    }

    const selectedQueue = Array.from(checkedCheckboxes).map(cb => {
        const idx = parseInt(cb.value, 10);
        return navigationItems[idx];
    });

    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab || !tab.id) {
        showStatus('Active tab not found', 'error');
        return;
    }

    switchToProgressMode();
    showProgress(0, selectedQueue.length, 'Initializing queue...');

    try {
        // Robust check to see if we are on listing page
        const checkResult = await chrome.scripting.executeScript({
            target: { tabId: tab.id },
            func: () => {
                const bookIds = new Set();
                const matchPattern = /\/books\/(\d+)\/\d+/;
                document.querySelectorAll('a[href]').forEach(a => {
                    const href = a.getAttribute('href') || '';
                    const match = href.match(matchPattern);
                    if (match) bookIds.add(match[1]);
                });
                return bookIds.size > 1 || /^\/books\/?$/.test(location.pathname);
            }
        });
        const isBooksListing = checkResult && checkResult[0] && checkResult[0].result;

        const response = await chrome.runtime.sendMessage({
            action: 'startScrapeQueue',
            tabId: tab.id,
            queue: selectedQueue,
            serverUrl: serverUrl,
            crawl: isBooksListing ? true : false
        });

        if (!response.success) {
            throw new Error(response.error || 'Failed to start scraping queue');
        }
    } catch (err) {
        onQueueError(err.message);
    }
}

async function stopScrape() {
    try {
        await chrome.runtime.sendMessage({ action: 'stopQueue' });
        showStatus('Stopping scraping queue...', 'loading');
        // Restore controls
        document.getElementById('navSection').style.display = 'block';
        document.getElementById('scrapeBtn').style.display = 'block';
        document.getElementById('scrapeBatchBtn').style.display = 'block';
        document.getElementById('progressSection').style.display = 'none';
    } catch (e) {
        console.error(e);
    }
}

function switchToProgressMode() {
    document.getElementById('navSection').style.display = 'none';
    document.getElementById('scrapeBtn').style.display = 'none';
    document.getElementById('scrapeBatchBtn').style.display = 'none';
    document.getElementById('progressSection').style.display = 'block';
}

function showProgress(current, total, text) {
    const percent = total > 0 ? (current / total) * 100 : 0;
    document.getElementById('progressBar').style.width = `${percent}%`;
    document.getElementById('progressDetails').textContent = `${current} / ${total} pages scraped`;
    document.getElementById('progressTitle').textContent = `Scraping: ${text}`;
}

function onQueueComplete() {
    showStatus('✓ Batch scraping completed!', 'success');
    setTimeout(() => {
        window.close();
    }, 2000);
}

function onQueueError(errMsg) {
    showStatus(`✗ Error: ${errMsg}`, 'error');
    // Restore buttons after error
    document.getElementById('navSection').style.display = 'block';
    document.getElementById('scrapeBtn').style.display = 'block';
    document.getElementById('scrapeBatchBtn').style.display = 'block';
    document.getElementById('progressSection').style.display = 'none';
}

function extractPageContent() {
    // Keep exact same structure as background.js's extractPageContent
    // (Defining it here so single page Scrape Current Page continues to work perfectly)
    
    function extractMainContent() {
        function cleanText(t) {
            return (t || '')
                .replace(/[ \t]+/g, ' ')
                .replace(/\n +/g, '\n')
                .replace(/\n{3,}/g, '\n\n')
                .trim();
        }

        // Find vocabulary container (first paragraph is exactly "Vocabulary")
        let vocabContainer = null;
        document.querySelectorAll('.rich-text, div, section, article').forEach(el => {
            if (vocabContainer) return;
            const firstP = el.querySelector('p');
            if (firstP && firstP.textContent.trim().toLowerCase() === 'vocabulary') {
                vocabContainer = el;
            }
        });

        function isNoise(el) {
            if (vocabContainer && (el === vocabContainer || vocabContainer.contains(el))) return true;
            let p = el.parentElement;
            while (p && p !== document.body) {
                const cls = (p.className || '').toString();
                const tag = p.tagName ? p.tagName.toLowerCase() : '';
                if (tag === 'nav' || tag === 'header' || tag === 'footer' || tag === 'aside') return true;
                if (cls.includes('menu-wp') || cls.includes('chapter-nav') ||
                    cls.includes('left-panel') || cls.includes('right-panel') ||
                    cls.includes('breadcrumb') || cls.includes('page-heading')) return true;
                p = p.parentElement;
            }
            return false;
        }

        const result = {};
        const seen = new Set();
        let blockIndex = 0;

        // ── Single ordered walk ──────────────────────────────────────────────
        // Collect headings AND rich content elements together, then sort by
        // DOM position so headings appear above their associated paragraphs.

        const contentSelectors = [
            '.rich-text', '.formatted', '.markdown-wp',
            '.guide-box', '.side-box', '.note-box',
            '.book-section-hl', '[class*="book-section-light"]',
            '[class*="blockquote-"]',
            '.h1', '.h2', '.h3', '.h4', 'h1', 'h2', 'h3', 'h4'
        ];

        const allEls = Array.from(document.querySelectorAll(contentSelectors.join(', ')));

        // Sort by document order
        allEls.sort((a, b) => {
            const pos = a.compareDocumentPosition(b);
            if (pos & Node.DOCUMENT_POSITION_FOLLOWING) return -1;
            if (pos & Node.DOCUMENT_POSITION_PRECEDING) return 1;
            return 0;
        });

        allEls.forEach(el => {
            if (isNoise(el)) return;
            if (el.closest('.question')) return;

            const tag  = (el.tagName || '').toLowerCase();
            const cls  = (el.className || '').toString();
            const isHeading = /^h[1-4]$/.test(tag) || /\bh[1-4]\b/.test(cls);

            if (isHeading) {
                const text = (el.innerText || el.textContent || '').trim();
                if (!text || text.length > 200) return;
                const dupKey = text.slice(0, 100);
                if (seen.has(dupKey)) return;
                seen.add(dupKey);
                const level = /^h[1-4]$/.test(tag) ? parseInt(tag[1]) :
                              cls.includes('h1') ? 1 : cls.includes('h2') ? 2 :
                              cls.includes('h3') ? 3 : 4;
                result[`__heading_${level}__${text.slice(0, 40)}_${blockIndex}`] = text;
                blockIndex++;
                return;
            }

            // Rich-text / content block
            if (el.closest('.rich-text')?.parentElement !== el.parentElement &&
                el.matches('.rich-text') && el.querySelector('.rich-text')) return;

            const text = el.innerText || el.textContent || '';
            if (!text.trim()) return;

            let label = 'Main Content';
            const ancestorText = (() => {
                let p = el.parentElement;
                while (p && p !== document.body) {
                    const pcls = (p.className || '').toString();
                    if (pcls.includes('vocab')) return 'Vocabulary';
                    if (pcls.includes('practice') || pcls.includes('question')) return 'Practice Questions';
                    if (pcls.includes('atl')) return 'ATL Skills';
                    if (pcls.includes('tok') || pcls.includes('ethics')) return 'TOK / Ethics';
                    if (pcls.includes('guide-box') || pcls.includes('side-box')) {
                        const h = p.querySelector('[class*="h3"],[class*="h4"],[class*="head"],[class*="title"]');
                        return h ? cleanText(h.innerText || h.textContent || '') : 'Sidebar Note';
                    }
                    p = p.parentElement;
                }
                return null;
            })();

            if (ancestorText) {
                label = ancestorText;
            } else if (cls.includes('guide-box') || cls.includes('side-box') || cls.includes('note-box')) {
                const h = el.querySelector('[class*="h3"],[class*="h4"],[class*="head"],[class*="title"]');
                label = h ? cleanText(h.innerText || h.textContent || '') : 'Sidebar Note';
            } else if (cls.includes('blockquote-')) {
                label = 'Key Point';
            }

            // Sidebar-type blocks are captured by extractSidebarSections — skip here
            if (label !== 'Main Content') return;

            const clean = cleanText(text);
            if (clean.length < 10) return;
            const dupKey = clean.slice(0, 100);
            if (seen.has(dupKey)) return;
            seen.add(dupKey);
            const key = `Main Content (${++blockIndex})`;
            result[key] = clean.substring(0, 5000);
        });

        if (Object.keys(result).length === 0) {
            const paras = document.querySelectorAll('p');
            let all = '';
            paras.forEach(p => {
                if (!isNoise(p)) all += (p.innerText || p.textContent || '') + '\n\n';
            });
            if (all.trim().length > 20) {
                result['Main Content (1)'] = cleanText(all).substring(0, 8000);
            } else {
                result['Main Content (1)'] = cleanText(document.body.innerText || '').substring(0, 8000);
            }
        }

        return result;
    }

    function extractImages() {
        const images = [];
        const seen = new Set();
        const imgElements = document.querySelectorAll('img');

        imgElements.forEach((img, index) => {
            const src = img.src || img.getAttribute('src') || img.dataset.src || img.dataset.lazySrc || '';
            if (src && !src.startsWith('data:') && !seen.has(src)) {
                seen.add(src);
                images.push({
                    src: src,
                    original_src: src,
                    alt: img.alt || img.title || `Image ${index}`
                });
            }
        });

        // Also capture <picture> source elements for responsive images
        document.querySelectorAll('picture source').forEach(source => {
            const srcset = source.srcset || source.getAttribute('srcset') || '';
            const firstSrc = srcset.split(',')[0].trim().split(' ')[0];
            if (firstSrc && !seen.has(firstSrc)) {
                seen.add(firstSrc);
                images.push({ src: firstSrc, original_src: firstSrc, alt: '' });
            }
        });

        return images;
    }

    function estimateLevel(element, text) {
        text = text.trim();
        if (text.startsWith('Theme')) return 1;
        if (text === 'Introduction') return 2;
        
        if (/^[A-Z]\.?\d+\.\d+\.\d+/.test(text)) return 4;
        if (/^[A-Z]\.?\d+\.\d+/.test(text)) return 3;
        if (/^[A-Z]\.?\d+/.test(text)) return 2;

        let level = 1;
        let parent = element.parentElement;
        while (parent && level < 5) {
            if (parent.classList.toString().includes('sub') ||
                parent.tagName === 'UL' ||
                parent.tagName === 'OL') {
                level++;
            }
            parent = parent.parentElement;
        }
        return level;
    }

    function extractNavigation() {
        const nav = [];
        const menuContainer = document.querySelector('.menu-wp, [class*="menu-wp"], [class*="sidebar-nav"], [class*="navigation"]');
        const navElements = menuContainer ? menuContainer.querySelectorAll('a') : document.querySelectorAll('nav a, [role="navigation"] a, .nav a, .menu a');

        navElements.forEach(link => {
            const text = link.textContent.trim();
            const href = link.href;
            if (text && href && !href.startsWith('javascript')) {
                if (!nav.some(item => item.text === text)) {
                    nav.push({
                        text,
                        href,
                        level: estimateLevel(link, text)
                    });
                }
            }
        });
        return nav.slice(0, 400);
    }

    // YouTube videos: iframes (incl. lazy-loaded), lite-youtube elements,
    // and plain video links. Normalized to canonical watch URLs, deduped by id.
    function extractVideos() {
        const videos = [];
        const seen = new Set();

        function addVideo(url, title) {
            if (!url) return;
            try { url = decodeURIComponent(url); } catch(e) {}
            let m = url.match(/(?:youtube(?:-nocookie)?\.com\/(?:embed\/|watch\?.*?v=|shorts\/)|youtu\.be\/)([\w-]{11})/);
            if (!m) {
                // Detect local files saved by Chrome (e.g. "clCPQo0-quo.html")
                const localMatch = url.match(/\/([\w-]{11})\.html(?:\?|$)/) || url.match(/^([\w-]{11})\.html(?:\?|$)/);
                if (localMatch) {
                    m = [null, localMatch[1]];
                }
            }
            if (!m || seen.has(m[1])) return;
            seen.add(m[1]);
            videos.push({
                src: 'https://www.youtube.com/watch?v=' + m[1],
                title: (title || '').trim().substring(0, 150),
                side: true
            });
        }

        function queryAllIncludingShadows(selector, root = document) {
            let elements = Array.from(root.querySelectorAll(selector));
            root.querySelectorAll('*').forEach(el => {
                if (el.shadowRoot) {
                    elements = elements.concat(queryAllIncludingShadows(selector, el.shadowRoot));
                }
            });
            return elements;
        }

        function nearbyTitle(el) {
            const fig = el.closest('figure');
            if (fig) {
                const cap = fig.querySelector('figcaption');
                if (cap) return cap.innerText;
            }
            let p = el.parentElement, hops = 0;
            while (p && hops < 3) {
                const h = p.querySelector('.h3, .h4, h3, h4, [class*="title"], [class*="caption"]');
                if (h) {
                    const t = (h.innerText || '').trim();
                    if (t.length > 2 && t.length < 150) return t;
                }
                p = p.parentElement;
                hops++;
            }
            return '';
        }

        queryAllIncludingShadows('iframe').forEach(f => {
            const url = f.src || f.getAttribute('src') || f.getAttribute('data-src') || '';
            addVideo(url, f.title || nearbyTitle(f));
        });
        queryAllIncludingShadows('lite-youtube[videoid]').forEach(el => {
            addVideo('https://www.youtube.com/watch?v=' + el.getAttribute('videoid'),
                     el.getAttribute('playlabel') || nearbyTitle(el));
        });
        queryAllIncludingShadows('a[href*="youtube.com/watch"], a[href*="youtu.be/"], a[href*="youtube.com/embed"]').forEach(a => {
            if (a.closest('nav, header, footer')) return;
            addVideo(a.href, a.innerText);
        });
        return videos;
    }

    // Structured practice questions: question text + markscheme answer
    function extractPracticeQuestions() {
        const questions = [];
        document.querySelectorAll('.question').forEach(q => {
            const chunks = q.querySelectorAll('.rich-text');
            if (chunks.length === 0) return;

            const meta = Array.from(q.querySelectorAll('span.color-gray'))
                .map(s => (s.textContent || '').trim())
                .filter(Boolean)
                .join(' • ');

            const questionText = (chunks[0].innerText || '').trim();
            if (!questionText) return;

            let answerText = Array.from(chunks).slice(1)
                .map(c => (c.innerText || '').trim())
                .filter(Boolean)
                .join('\n\n');

            if (!answerText) {
                const full = q.innerText || '';
                const idx = full.indexOf('Answer:');
                if (idx !== -1) {
                    answerText = full.slice(idx)
                        .replace(/(Show|Hide)\s*markscheme[\s\S]*$/i, '')
                        .trim();
                }
            }

            questions.push({
                marks: meta,
                question: questionText.substring(0, 3000),
                answer: (answerText || '').substring(0, 5000)
            });
        });
        return questions;
    }

    function extractSidebarSections() {
        const sections = {};

        // Extract side-box class items
        const sideBoxes = document.querySelectorAll('.side-box, [class*="side-box"]');
        sideBoxes.forEach(sb => {
            const titleEl = sb.querySelector('.title, [class*="title"]');
            const contentEl = sb.querySelector('.content, [class*="content"]');
            if (titleEl && contentEl) {
                const titleText = titleEl.textContent.trim();
                const contentText = contentEl.textContent.trim();
                if (titleText && contentText) {
                    sections[titleText] = contentText;
                }
            }
        });

        // Find vocabulary container (first paragraph is exactly "Vocabulary")
        let vocabContainer = null;
        document.querySelectorAll('.rich-text, div, section, article').forEach(el => {
            if (vocabContainer) return;
            const firstP = el.querySelector('p');
            if (firstP && firstP.textContent.trim().toLowerCase() === 'vocabulary') {
                vocabContainer = el;
            }
        });

        if (vocabContainer) {
            const vocabParas = Array.from(vocabContainer.querySelectorAll('p')).slice(1);
            const vocabLines = vocabParas.map(p => {
                const fullText = p.innerText.trim();
                if (!fullText) return '';
                
                let term = '';
                let desc = '';
                
                // 1. Try strong element
                const strongEl = p.querySelector('strong, b');
                if (strongEl) {
                    term = strongEl.innerText.trim();
                    if (term && fullText.toLowerCase().startsWith(term.toLowerCase())) {
                        desc = fullText.substring(term.length).trim();
                        desc = desc.replace(/^[–\-:—\s•\uFFFD\u2013\u2014]+/g, '').trim();
                    }
                }
                
                // 2. Fallback to common separators
                if (!term || !desc) {
                    const separatorRegex = /\s*([–\-—•\uFFFD\u2013\u2014]|\s:\s)\s*/;
                    const match = fullText.match(separatorRegex);
                    if (match) {
                        const idx = fullText.indexOf(match[0]);
                        term = fullText.substring(0, idx).trim();
                        desc = fullText.substring(idx + match[0].length).trim();
                    } else {
                        // 3. Fallback to first colon
                        const colonIdx = fullText.indexOf(':');
                        if (colonIdx !== -1) {
                            term = fullText.substring(0, colonIdx).trim();
                            desc = fullText.substring(colonIdx + 1).trim();
                        }
                    }
                }
                
                if (term && desc) {
                    return `<strong>${term}</strong>: ${desc}`;
                }
                return fullText;
            }).filter(Boolean);
            
            if (vocabLines.length > 0) {
                sections['Vocabulary'] = vocabLines.join('\n\n');
            }
        }

        // Keywords fallback
        const keywords = [
            'Study Tip', 'Theory of Knowledge', 'Applied Work', 'Practice Questions',
            'Vocabulary', 'Key Concept', 'International-Mindedness', 'Approaches to Learning',
            'Fun Fact', 'Learning Objectives', 'Summary', 'Important'
        ];
        const textElements = document.querySelectorAll('div, section, aside, article');
        textElements.forEach(element => {
            if (vocabContainer && (element === vocabContainer || vocabContainer.contains(element))) return;
            const text = element.textContent.trim();
            keywords.forEach(keyword => {
                if (text.includes(keyword) && text.length < 500 && !sections[keyword]) {
                    sections[keyword] = text.substring(0, 500);
                }
            });
        });

        return sections;
    }

    // Extract main heading as title if available
    let pageTitle = '';
    
    // 1. Match main content heading text against sidebar menu links
    const headingEl = document.querySelector('.chapter-name span, .chapter-name, [class*="chapter-name"] span, [class*="chapter-name"]');
    const headingText = headingEl ? headingEl.textContent.trim() : '';

    if (headingText) {
        const navLinks = document.querySelectorAll('a, [role="navigation"] a, .nav a, .menu a, [class*="chapter"] a');
        for (const link of navLinks) {
            const linkText = link.textContent.trim();
            if (linkText.includes(headingText) && linkText.length > headingText.length) {
                pageTitle = linkText;
                break;
            }
        }
        if (!pageTitle) {
            for (const link of navLinks) {
                const linkText = link.textContent.trim();
                if (linkText.includes(headingText)) {
                    pageTitle = linkText;
                    break;
                }
            }
        }
    }

    // 2. Check navigation links for current active page URL
    if (!pageTitle) {
        const currentUrl = window.location.href;
        const currentPath = window.location.pathname;
        const navLinks = document.querySelectorAll('a, [role="navigation"] a, .nav a, .menu a');
        for (const link of navLinks) {
            if (link.href && (link.href === currentUrl || (link.pathname && link.pathname === currentPath && currentPath !== '/'))) {
                const txt = link.textContent.trim();
                if (txt && txt.length > 3 && txt.length < 150) {
                    pageTitle = txt;
                    break;
                }
            }
        }
    }

    // 3. Fallback to active classes
    if (!pageTitle) {
        const activeNav = document.querySelector('.active, [class*="active"], [class*="selected"]');
        if (activeNav) {
            const txt = activeNav.textContent.trim();
            if (txt && txt.length > 3 && txt.length < 150) {
                pageTitle = txt;
            }
        }
    }

    // 4. Fallback to main content headings
    if (!pageTitle) {
        const headingElFallback = document.querySelector('.main-heading, h1, .h1, span[class*="pl-1"], [class*="color-label"][class*="strong"]');
        if (headingElFallback) {
            const txt = headingElFallback.textContent.trim();
            if (txt && txt.length > 3 && txt.length < 150) {
                pageTitle = txt;
            }
        }
    }

    // 5. Ultimate fallback to document title
    if (!pageTitle || pageTitle.length < 3 || pageTitle.toLowerCase() === 'books') {
        pageTitle = document.title.split(' | ')[0].trim();
    }

    // Extract book title and book ID
    let bookTitle = '';
    const bookTitleEl = document.querySelector('title');
    if (bookTitleEl) {
        bookTitle = bookTitleEl.textContent.split('|')[0].trim();
    }
    if (!bookTitle || bookTitle.toLowerCase() === 'books') {
        bookTitle = 'Untitled Book';
    }
    const bookMatch = window.location.pathname.match(/\/books\/(\d+)/);
    const bookId = bookMatch ? bookMatch[1] : null;

    return {
        title: pageTitle,
        url: window.location.href,
        bookTitle: bookTitle,
        bookId: bookId,
        mainContent: extractMainContent(),
        images: extractImages(),
        navigation: extractNavigation(),
        sidebarSections: extractSidebarSections(),
        practiceQuestions: extractPracticeQuestions(),
        videos: extractVideos(),
        timestamp: new Date().toISOString()
    };
}

function showStatus(message, type) {
    const statusDiv = document.getElementById('status');
    if (!statusDiv) return;
    
    statusDiv.textContent = message;
    statusDiv.className = `status-message show ${type}`;

    if (type !== 'loading') {
        setTimeout(() => {
            statusDiv.classList.remove('show');
        }, 4000);
    }
}

function openDashboard() {
    const serverUrl = document.getElementById('serverUrl').value;
    chrome.tabs.create({ url: serverUrl });
}