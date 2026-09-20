// Service Worker for Chrome Extension Batch Scraping
let currentQueue = [];
let isQueueRunning = false;
let currentProgress = 0;
let totalProgress = 0;
let currentText = '';

chrome.runtime.onInstalled.addListener(() => {
    console.log('Content Scraper extension installed');
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.action === 'startScrapeQueue') {
        if (isQueueRunning) {
            sendResponse({ success: false, error: 'A scrape queue is already running.' });
            return;
        }
        sendResponse({ success: true });
        runScrapeQueue(message.tabId, message.queue, message.serverUrl, message.crawl === true);
    } else if (message.action === 'stopQueue') {
        isQueueRunning = false;
        sendResponse({ success: true });
    } else if (message.action === 'getQueueStatus') {
        sendResponse({ isRunning: isQueueRunning, current: currentProgress, total: totalProgress, text: currentText });
    }
    return true;
});

// Safety cap so a crawl can never run away on unexpected link structures
const MAX_CRAWL_PAGES = 2000;

function normalizeUrl(href) {
    try {
        const u = new URL(href);
        const origin = u.origin === 'null' ? u.protocol + '//' : u.origin;
        return origin + u.pathname.replace(/\/+$/, '');
    } catch (e) {
        return (href || '').split('#')[0].replace(/\/+$/, '');
    }
}

async function runScrapeQueue(tabId, queue, serverUrl, crawl = false) {
    isQueueRunning = true;
    currentQueue = queue;
    totalProgress = queue.length;
    const visited = new Set(queue.map(q => normalizeUrl(q.href)));

    try {
        for (let i = 0; i < queue.length; i++) {
            if (!isQueueRunning) {
                console.log('Scrape queue stopped by user.');
                break;
            }
            const item = queue[i];
            currentProgress = i + 1;
            currentText = item.text;
            
            // Broadcast progress to popup (if open)
            broadcastMessage({
                action: 'queueProgress',
                current: currentProgress,
                total: totalProgress,
                text: currentText,
                url: item.href
            });
            
            // Navigate the tab to the syllabus item link
            await chrome.tabs.update(tabId, { url: item.href });
            
            // Wait for tab load completion
            await waitForTabComplete(tabId);
            
            // Add static sleep delay (2 seconds) to allow client scripts (e.g. React/KaTeX) to load
            await sleep(2000);

            // Expand all collapsed markschemes so answers are present in the DOM
            await chrome.scripting.executeScript({
                target: { tabId },
                func: expandMarkschemes
            });
            await sleep(1000);

            // Inject and execute DOM scraper script on target page
            const results = await chrome.scripting.executeScript({
                target: { tabId },
                func: extractPageContent
            });
            
            if (results && results[0] && results[0].result) {
                const pageData = results[0].result;
                pageData.url = item.href;
                // Use sidebar navigation title if page heading is missing
                pageData.title = pageData.title || item.text;
                
                // Fetch images as base64 using browser's authenticated session
                broadcastMessage({ action: 'queueProgress', current: currentProgress, total: totalProgress, text: `Downloading images for: ${item.text}` });
                pageData.images = await fetchImagesAsBase64(pageData.images || []);
                
                // Submit DOM scraped data to server
                await sendScrapedData(serverUrl, pageData);
            } else {
                console.error(`Failed to extract content for: ${item.text}`);
            }

            // Crawl mode: the source site only renders a chapter's sub-links once you
            // are on that chapter, so re-scan every visited page and append any
            // newly revealed same-book links to the end of the queue.
            if (crawl && queue.length < MAX_CRAWL_PAGES) {
                try {
                    const found = await chrome.scripting.executeScript({
                        target: { tabId },
                        func: discoverBookLinks
                    });
                    const links = (found && found[0] && found[0].result) || [];
                    for (const link of links) {
                        const key = normalizeUrl(link.href);
                        if (!visited.has(key) && queue.length < MAX_CRAWL_PAGES) {
                            visited.add(key);
                            queue.push({ text: link.title, href: link.href });
                        }
                    }
                    totalProgress = queue.length;
                } catch (e) {
                    console.warn('Sub-link discovery failed on this page:', e);
                }
            }
        }
        
        // Scrape completed successfully
        broadcastMessage({ action: 'queueFinished' });
        
        // Open/Focus Flask dashboard tab
        chrome.tabs.create({ url: serverUrl });
        
    } catch (err) {
        console.error('Queue execution failed:', err);
        broadcastMessage({ action: 'queueError', message: err.message });
    } finally {
        isQueueRunning = false;
        currentQueue = [];
        currentProgress = 0;
        totalProgress = 0;
        currentText = '';
    }
}

function broadcastMessage(msg) {
    chrome.runtime.sendMessage(msg).catch(err => {
        // Suppress message failure logs when popup is closed
    });
}

function waitForTabComplete(tabId) {
    return new Promise((resolve) => {
        let resolved = false;
        const listener = (id, info) => {
            if (id === tabId && info.status === 'complete') {
                if (!resolved) {
                    resolved = true;
                    chrome.tabs.onUpdated.removeListener(listener);
                    resolve();
                }
            }
        };
        chrome.tabs.onUpdated.addListener(listener);
        
        // Timeout safeguard
        setTimeout(() => {
            if (!resolved) {
                resolved = true;
                chrome.tabs.onUpdated.removeListener(listener);
                resolve();
            }
        }, 12000);
    });
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// Injected into the page during crawl mode: find every link belonging to the
// SAME book as the current page (/books/<bookId>/<pageId>), excluding the page
// we're on. Mirrors popup.js discoverBookLinks (injected functions must be
// defined in the file that injects them).
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
    if (!bookId) return [];

    const origin = location.origin === 'null' ? location.protocol + '//' : location.origin;
    const here = origin + location.pathname.replace(/\/+$/, '');
    const pattern = new RegExp('^/books/' + bookId + '/\\d+');

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
        const title = (a.textContent || '').trim().replace(/\s+/g, ' ');
        if (!title) return;
        seen.add(clean);
        links.push({ title: title.slice(0, 120), href: clean });
    });
    console.log("[Extension Debug] returning links:", links.length);
    return links;
}

// Injected before extraction: clicks every "Show markscheme" link so the
// answer content gets rendered into the DOM
function expandMarkschemes() {
    document.querySelectorAll('.question .link, .question span.link, .question a').forEach(el => {
        if (/show\s*markscheme/i.test(el.textContent || '')) el.click();
    });
}

/**
 * Fetch each image URL using the browser's authenticated session and convert to base64 data URI.
 * This works because the service worker shares the same cookie jar as the user's browser session.
 */
async function fetchImagesAsBase64(images) {
    const enriched = [];
    for (const img of images) {
        const src = img.src || img.original_src || '';
        if (!src || src.startsWith('data:')) {
            // Already base64 or no src — keep as-is
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
            console.warn(`Could not fetch image as base64: ${src}`, err);
            // Keep original src as fallback
            enriched.push(img);
        }
    }
    return enriched;
}

async function sendScrapedData(serverUrl, data) {
    const response = await fetch(`${serverUrl}/api/scrape-dom`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    const res = await response.json();
    if (!res.success) {
        throw new Error(res.error || 'Failed to save to server');
    }
}

// Scraper function injected dynamically into target tab's active DOM
function extractPageContent() {
    
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
            // Skip if a parent rich-text already captured this text
            if (el.closest('.rich-text')?.parentElement !== el.parentElement &&
                el.matches('.rich-text') && el.querySelector('.rich-text')) return;

            const text = el.innerText || el.textContent || '';
            if (!text.trim()) return;

            // Determine label based on context
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

        // Fallback: if nothing found, grab all paragraph text
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
            if (src && !seen.has(src)) {
                seen.add(src);
                images.push({
                    src: src,
                    original_src: src,
                    alt: img.alt || img.title || `Image ${index}`
                });
            }
        });

        // Also capture any <picture> source elements
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

    // Structured practice questions: question text + markscheme answer.
    // Markschemes must already be expanded (see expandMarkschemes) or the
    // answer falls back to empty.
    function extractPracticeQuestions() {
        const questions = [];
        document.querySelectorAll('.question').forEach(q => {
            const chunks = q.querySelectorAll('.rich-text');
            if (chunks.length === 0) return;

            // Meta badges: "3 marks", "SL" / "HL"
            const meta = Array.from(q.querySelectorAll('span.color-gray'))
                .map(s => (s.textContent || '').trim())
                .filter(Boolean)
                .join(' • ');

            const questionText = (chunks[0].innerText || '').trim();
            if (!questionText) return;

            // Everything after the first rich-text chunk is markscheme content
            let answerText = Array.from(chunks).slice(1)
                .map(c => (c.innerText || '').trim())
                .filter(Boolean)
                .join('\n\n');

            // Fallback: pull text between "Answer:" and "Hide markscheme"
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
