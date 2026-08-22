// ee-exemplars.js - IB EE/IA exemplar library dashboard

let allExemplars = [];
let filteredExemplars = [];

const searchInput = document.getElementById('search-input');
const clearSearchBtn = document.getElementById('clear-search-btn');

const filterSubject = document.getElementById('filter-subject');
const filterLevel = document.getElementById('filter-level');
const filterGrade = document.getElementById('filter-grade');
const filterLanguage = document.getElementById('filter-language');
const filterSession = document.getElementById('filter-session');
const sortBy = document.getElementById('sort-by');

const resultsCounter = document.getElementById('results-counter');
const resetFiltersBtn = document.getElementById('reset-filters-btn');
const exemplarsGrid = document.getElementById('exemplars-grid');

const statTotal = document.getElementById('stat-total');
const statAvgMark = document.getElementById('stat-avg-mark');
const statTopGrade = document.getElementById('stat-top-grade');

const viewerModal = document.getElementById('viewer-modal');
const closeModalBtn = document.getElementById('close-modal-btn');
const pdfIframe = document.getElementById('pdf-iframe');
const modalTitle = document.getElementById('modal-title');
const modalSubject = document.getElementById('modal-subject');
const modalGrade = document.getElementById('modal-grade');
const modalRawMark = document.getElementById('modal-raw-mark');
const modalSession = document.getElementById('modal-session');
const modalLanguage = document.getElementById('modal-language');
const modalComments = document.getElementById('modal-comments');
const modalDownloadLink = document.getElementById('modal-download-link');
const modalOriginalLink = document.getElementById('modal-original-link');
const modalBadgeLevel = document.getElementById('modal-badge-level');

window.addEventListener('DOMContentLoaded', async () => {
    document.addEventListener('keydown', (e) => {
        if (e.key === '/' && document.activeElement !== searchInput) {
            e.preventDefault();
            searchInput.focus();
            searchInput.select();
        }
    });

    searchInput.addEventListener('input', handleFilterChange);
    clearSearchBtn.addEventListener('click', () => {
        searchInput.value = '';
        clearSearchBtn.style.display = 'none';
        handleFilterChange();
    });

    filterSubject.addEventListener('change', handleFilterChange);
    filterLevel.addEventListener('change', handleFilterChange);
    filterGrade.addEventListener('change', handleFilterChange);
    filterLanguage.addEventListener('change', handleFilterChange);
    filterSession.addEventListener('change', handleFilterChange);
    sortBy.addEventListener('change', handleFilterChange);
    resetFiltersBtn.addEventListener('click', resetFilters);

    closeModalBtn.addEventListener('click', closeModal);
    viewerModal.addEventListener('click', (e) => {
        if (e.target === viewerModal) closeModal();
    });
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeModal();
    });

    await loadData();
});

async function loadData() {
    try {
        exemplarsGrid.innerHTML = '<div class="empty-state"><h3>Loading exemplars database...</h3></div>';

        const response = await fetch('/api/ee-exemplars');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        allExemplars = data.exemplars || [];

        filteredExemplars = [...allExemplars];

        populateFilterDropdowns();
        updateStats(allExemplars);
        renderExemplars();
    } catch (error) {
        console.error('Failed to load exemplars:', error);
        exemplarsGrid.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">warning</div>
                <h3>Failed to load exemplars</h3>
                <p>Something went wrong loading the exemplar library. Try refreshing the page.</p>
            </div>
        `;
    }
}

function populateFilterDropdowns() {
    const subjects = new Set();
    const languages = new Set();
    const sessions = new Set();

    allExemplars.forEach(item => {
        if (item.subject) subjects.add(item.subject);
        if (item.language) languages.add(item.language);
        if (item.session) sessions.add(item.session);
    });

    Array.from(subjects).sort().forEach(sub => {
        const opt = document.createElement('option');
        opt.value = sub;
        opt.textContent = sub;
        filterSubject.appendChild(opt);
    });

    Array.from(languages).sort().forEach(lang => {
        const opt = document.createElement('option');
        opt.value = lang;
        opt.textContent = lang.toUpperCase();
        filterLanguage.appendChild(opt);
    });

    const sortedSessions = Array.from(sessions).sort((a, b) => getSessionWeight(b) - getSessionWeight(a));
    sortedSessions.forEach(sess => {
        const opt = document.createElement('option');
        opt.value = sess;
        opt.textContent = sess;
        filterSession.appendChild(opt);
    });
}

function getSessionWeight(sessionStr) {
    if (!sessionStr) return 0;
    const match = sessionStr.match(/\d{4}/);
    const year = match ? parseInt(match[0]) : 0;
    const isNov = sessionStr.toLowerCase().includes('nov');
    return year * 12 + (isNov ? 11 : 5);
}

function updateStats(items) {
    statTotal.textContent = items.length;

    const marks = items.map(i => i.raw_mark).filter(m => m !== null && !isNaN(m));
    if (marks.length > 0) {
        const sum = marks.reduce((a, b) => a + b, 0);
        statAvgMark.textContent = (sum / marks.length).toFixed(1);
    } else {
        statAvgMark.textContent = 'N/A';
    }

    const topGrades = items.filter(i => {
        const g = i.grade ? i.grade.toUpperCase() : '';
        return g === '7' || g === 'A';
    });
    statTopGrade.textContent = topGrades.length;
}

function resetFilters() {
    searchInput.value = '';
    clearSearchBtn.style.display = 'none';
    filterSubject.value = '';
    filterLevel.value = '';
    filterGrade.value = '';
    filterLanguage.value = '';
    filterSession.value = '';
    sortBy.value = 'subject-asc';
    handleFilterChange();
}

function handleFilterChange() {
    const query = searchInput.value.toLowerCase().trim();
    clearSearchBtn.style.display = query.length > 0 ? 'block' : 'none';

    const sub = filterSubject.value;
    const lvl = filterLevel.value;
    const grd = filterGrade.value;
    const lang = filterLanguage.value;
    const sess = filterSession.value;

    filteredExemplars = allExemplars.filter(item => {
        if (query) {
            const matchComment = item.comments ? item.comments.toLowerCase().includes(query) : false;
            const matchSub = item.subject ? item.subject.toLowerCase().includes(query) : false;
            if (!matchComment && !matchSub) return false;
        }
        if (sub && item.subject !== sub) return false;
        if (lvl && item.level !== lvl) return false;
        if (grd && item.grade !== grd) return false;
        if (lang && item.language !== lang) return false;
        if (sess && item.session !== sess) return false;
        return true;
    });

    const sortVal = sortBy.value;
    if (sortVal === 'subject-asc') {
        filteredExemplars.sort((a, b) => a.subject.localeCompare(b.subject));
    } else if (sortVal === 'mark-desc') {
        filteredExemplars.sort((a, b) => {
            if (a.raw_mark === null) return 1;
            if (b.raw_mark === null) return -1;
            return b.raw_mark - a.raw_mark;
        });
    } else if (sortVal === 'mark-asc') {
        filteredExemplars.sort((a, b) => {
            if (a.raw_mark === null) return 1;
            if (b.raw_mark === null) return -1;
            return a.raw_mark - b.raw_mark;
        });
    } else if (sortVal === 'session-desc') {
        filteredExemplars.sort((a, b) => getSessionWeight(b) - getSessionWeight(a));
    }

    resultsCounter.textContent = `Showing ${filteredExemplars.length} of ${allExemplars.length} matching records`;
    renderExemplars();
}

function renderExemplars() {
    exemplarsGrid.innerHTML = '';

    if (filteredExemplars.length === 0) {
        exemplarsGrid.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">🔍</div>
                <h3>No Exemplars Found</h3>
                <p>Try modifying your search text or resetting the selection dropdowns.</p>
            </div>
        `;
        return;
    }

    filteredExemplars.forEach(item => {
        const card = document.createElement('div');
        card.className = 'exemplar-card';

        let gradeClass = 'grade-low';
        const g = item.grade ? item.grade.toUpperCase() : '';
        if (g === '7' || g === 'A') gradeClass = 'grade-a';
        else if (g === '6' || g === 'B') gradeClass = 'grade-b';
        else if (g === '5' || g === 'C') gradeClass = 'grade-c';

        let levelClass = 'level-core';
        if (item.level === 'HL') levelClass = 'level-hl';
        else if (item.level === 'SL') levelClass = 'level-sl';

        const shortComments = item.comments ? item.comments : 'No topic/research question notes provided.';
        const rawMarkDisplay = item.raw_mark !== null ? `Score: ${item.raw_mark}` : 'Score: N/A';

        card.innerHTML = `
            <div class="card-header-meta">
                <div class="badge-group">
                    <span class="badge ${levelClass}">${item.level}</span>
                    <span class="badge" style="background: rgba(255,255,255,0.05); color: var(--text-secondary); border: 1px solid var(--border-light)">${(item.language || '').toUpperCase()}</span>
                </div>
                <div class="badge-grade ${gradeClass}">${item.grade || '?'}</div>
            </div>

            <div class="card-content-area">
                <div class="subject-title">${item.subject}</div>
                <h3 class="card-topic-title" title="${shortComments}">${shortComments}</h3>
            </div>

            <div class="card-footer-data">
                <span class="footer-marks">${rawMarkDisplay}</span>
                <span class="footer-session">${item.session || ''}</span>
            </div>
        `;

        card.addEventListener('click', () => openModal(item));
        exemplarsGrid.appendChild(card);
    });
}

function pdfUrlFor(item) {
    return `/resources/exemplars/pdf/${encodeURIComponent(item.filename)}`;
}

function openModal(item) {
    modalTitle.textContent = item.comments || `${item.subject} Exemplar (${item.level})`;
    modalSubject.textContent = item.subject;
    modalGrade.textContent = item.grade || 'N/A';
    modalRawMark.textContent = item.raw_mark !== null ? `${item.raw_mark} points` : 'N/A';
    modalSession.textContent = item.session || 'Unknown Session';
    modalLanguage.textContent = (item.language || '').toUpperCase();
    modalComments.textContent = item.comments || 'No comment provided by candidate.';

    modalBadgeLevel.textContent = item.level;
    modalBadgeLevel.className = 'detail-badge';
    if (item.level === 'HL') modalBadgeLevel.classList.add('level-hl');
    else if (item.level === 'SL') modalBadgeLevel.classList.add('level-sl');
    else modalBadgeLevel.classList.add('level-core');

    const pdfUrl = pdfUrlFor(item);
    modalDownloadLink.href = pdfUrl;
    modalDownloadLink.setAttribute('download', item.filename);
    modalOriginalLink.href = item.pdf_url;
    pdfIframe.src = pdfUrl;

    viewerModal.classList.add('active');
    document.body.style.overflow = 'hidden';
}

function closeModal() {
    viewerModal.classList.remove('active');
    document.body.style.overflow = '';
    pdfIframe.src = '';
}
