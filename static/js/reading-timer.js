/**
 * Reading Timer - Tracks active reading time on a page
 * Only counts time when user is actively engaged (cursor moving, scrolling, typing)
 */

class ReadingTimer {
    constructor(pageId, bookFolder) {
        this.pageId = pageId;
        this.bookFolder = bookFolder;
        this.sessionStartTime = Date.now();
        this.elapsedSeconds = 0;
        this.cumulativeSeconds = 0; // Total time ever spent on this page
        this.sessionSeconds = 0; // Time added in this session only
        this.isActive = false;
        this.inactivityTimeout = null;
        this.INACTIVITY_THRESHOLD = 30000; // 30 seconds of inactivity = paused
        this.SAVE_INTERVAL = 10000; // Save to server every 10 seconds
        this.saveTimer = null;

        // Save current page as last read
        this.saveLastReadPage();

        // Load session data from localStorage
        this.loadSessionData();

        // Load cumulative data from server
        this.loadCumulativeData().then(() => {
            // Initialize timer display after loading cumulative data
            this.initTimerDisplay();
        });

        // Also initialize display immediately in case server is slow
        this.initTimerDisplay();

        // Set up activity detection
        this.setupActivityDetection();

        // Set up periodic save to server
        this.startAutoSave();

        // Save on page unload
        window.addEventListener('beforeunload', () => this.saveToServer());
    }

    loadSessionData() {
        const storageKey = `reading_session_${this.bookFolder}_${this.pageId}`;
        const stored = localStorage.getItem(storageKey);

        if (stored) {
            const data = JSON.parse(stored);
            this.elapsedSeconds = data.elapsedSeconds || 0;
            this.sessionStartTime = Date.now();
            console.log('Reading Timer: Loaded session data from localStorage:', this.elapsedSeconds, 'seconds');
        }
    }

    async loadCumulativeData() {
        // Fetch total time spent on this page from the server
        try {
            const response = await fetch(`/api/reading-activity?book_folder=${this.bookFolder}&page_id=${this.pageId}`);
            if (response.ok) {
                const data = await response.json();
                const totalSeconds = data.total_seconds || 0;
                this.cumulativeSeconds = totalSeconds;
                this.elapsedSeconds = totalSeconds; // Display shows cumulative
                this.sessionSeconds = 0; // Nothing added yet this session
                console.log('Reading Timer: Loaded cumulative data from server:', totalSeconds, 'seconds');
                this.updateDisplay(); // Update display immediately
            }
        } catch (error) {
            console.error('Reading Timer: Failed to load cumulative data:', error);
        }
    }

    saveSessionData() {
        const storageKey = `reading_session_${this.bookFolder}_${this.pageId}`;
        localStorage.setItem(storageKey, JSON.stringify({
            elapsedSeconds: this.elapsedSeconds,
            lastUpdated: new Date().toISOString()
        }));
    }

    initTimerDisplay() {
        console.log('Reading Timer: Initializing display in header...');

        // Add CSS if not already present
        if (!document.querySelector('style[data-reading-timer]')) {
            console.log('Reading Timer: Adding CSS styles');
            const style = document.createElement('style');
            style.setAttribute('data-reading-timer', 'true');
            style.textContent = `
                .header-timer-display {
                    font-size: 0.75rem;
                    font-family: 'Monaco', 'Courier New', monospace;
                    color: rgba(255, 255, 255, 0.6);
                    white-space: nowrap;
                    display: flex;
                    align-items: center;
                    gap: 0.3rem;
                    margin-right: auto;
                    order: -1;
                }

                .header-timer-display.active {
                    color: rgba(255, 255, 255, 0.8);
                }

                .timer-status-indicator {
                    display: inline-block;
                    width: 6px;
                    height: 6px;
                    border-radius: 50%;
                    margin-left: 0.2rem;
                }

                .timer-status-indicator.active {
                    background: #4ade80;
                    animation: pulse 2s infinite;
                }

                .timer-status-indicator.paused {
                    background: rgba(255, 255, 255, 0.3);
                }

                @keyframes pulse {
                    0%, 100% { opacity: 1; }
                    50% { opacity: 0.5; }
                }
            `;
            document.head.appendChild(style);
        }

        // Find or create timer in header-nav
        const headerNav = document.querySelector('.header-nav');
        if (headerNav) {
            let timerElement = headerNav.querySelector('.header-timer-display');

            if (!timerElement) {
                timerElement = document.createElement('div');
                timerElement.className = 'header-timer-display';
                timerElement.innerHTML = `
                    <span class="timer-time">0:00</span>
                    <span class="timer-status-indicator paused"></span>
                `;
                // Insert before the enter reading mode button
                const enterBtn = headerNav.querySelector('#enterReadingModeBtn');
                if (enterBtn) {
                    enterBtn.parentNode.insertBefore(timerElement, enterBtn);
                } else {
                    headerNav.appendChild(timerElement);
                }
            }

            this.timerDisplay = timerElement.querySelector('.timer-time');
            this.timerStatus = timerElement.querySelector('.timer-status-indicator');
            this.timerElement = timerElement;
        }

        // Start updating display
        setInterval(() => this.updateDisplay(), 1000);
    }

    setupActivityDetection() {
        // Detect mouse movement
        document.addEventListener('mousemove', () => this.onActivity(), { passive: true });

        // Detect scrolling
        document.addEventListener('scroll', () => this.onActivity(), { passive: true });

        // Detect keyboard input
        document.addEventListener('keydown', () => this.onActivity(), { passive: true });

        // Detect page focus/blur
        window.addEventListener('focus', () => this.onPageFocus());
        window.addEventListener('blur', () => this.onPageBlur());
    }

    onActivity() {
        // Clear existing timeout
        if (this.inactivityTimeout) {
            clearTimeout(this.inactivityTimeout);
        }

        // Start timer if not already active
        if (!this.isActive) {
            this.isActive = true;
            this.updateTimerStatus();
        }

        // Set timeout to pause after inactivity
        this.inactivityTimeout = setTimeout(() => {
            this.isActive = false;
            this.updateTimerStatus();
        }, this.INACTIVITY_THRESHOLD);
    }

    onPageFocus() {
        if (this.isActive) return;
        // Don't auto-start on focus, wait for actual activity
    }

    onPageBlur() {
        // Pause timer when page loses focus
        this.isActive = false;
        this.updateTimerStatus();

        if (this.inactivityTimeout) {
            clearTimeout(this.inactivityTimeout);
        }
    }

    updateDisplay() {
        if (this.isActive) {
            this.elapsedSeconds++;
            this.sessionSeconds++;
            this.saveSessionData();
        }

        const minutes = Math.floor(this.elapsedSeconds / 60);
        const seconds = this.elapsedSeconds % 60;
        const display = `${minutes}:${seconds.toString().padStart(2, '0')}`;

        if (this.timerDisplay) {
            this.timerDisplay.textContent = display;
        }
    }

    updateTimerStatus() {
        if (this.timerStatus) {
            if (this.isActive) {
                this.timerStatus.classList.remove('paused');
                this.timerStatus.classList.add('active');
                if (this.timerElement) this.timerElement.classList.add('active');
            } else {
                this.timerStatus.classList.remove('active');
                this.timerStatus.classList.add('paused');
                if (this.timerElement) this.timerElement.classList.remove('active');
            }
        }
    }

    startAutoSave() {
        this.saveTimer = setInterval(() => {
            if (this.elapsedSeconds > 0) {
                this.saveToServer();
            }
        }, this.SAVE_INTERVAL);
    }

    async saveToServer() {
        if (this.sessionSeconds === 0) return;

        try {
            const response = await fetch('/api/reading-activity', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    book_folder: this.bookFolder,
                    page_id: this.pageId,
                    elapsed_seconds: this.sessionSeconds
                })
            });

            if (response.ok) {
                const data = await response.json();
                // Update cumulative total from server response
                this.cumulativeSeconds = data.total_seconds || this.cumulativeSeconds;

                // Clear the local session data after successful save
                const storageKey = `reading_session_${this.bookFolder}_${this.pageId}`;
                localStorage.removeItem(storageKey);
                this.sessionSeconds = 0;
            }
        } catch (error) {
            console.error('Failed to save reading activity:', error);
            // Will retry on next interval
        }
    }

    saveLastReadPage() {
        localStorage.setItem('last_read_page', JSON.stringify({
            bookFolder: this.bookFolder,
            pageId: this.pageId,
            timestamp: new Date().toISOString()
        }));
    }

    static getLastReadPage() {
        const stored = localStorage.getItem('last_read_page');
        return stored ? JSON.parse(stored) : null;
    }

    destroy() {
        if (this.saveTimer) clearInterval(this.saveTimer);
        if (this.inactivityTimeout) clearTimeout(this.inactivityTimeout);
        this.saveToServer();
    }
}

// Auto-initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    const pageId = document.body.getAttribute('data-page-id');
    const bookFolder = document.body.getAttribute('data-book-folder');

    console.log('Reading Timer: Checking for page data...', { pageId, bookFolder });

    if (pageId && bookFolder) {
        console.log('Reading Timer: Initializing with', { pageId, bookFolder });
        window.readingTimer = new ReadingTimer(pageId, bookFolder);
    } else {
        console.log('Reading Timer: Page data not found, skipping initialization');
    }
});
