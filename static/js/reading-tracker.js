(function () {
    const cfg = window.__READING__;
    if (!cfg || !cfg.bookFolder || !cfg.pageId) return;

    let accumulatedSeconds = 0;
    let lastTick = Date.now();
    let visible = document.visibilityState === 'visible';
    let currentPageId = cfg.pageId;

    function tick() {
        if (visible) {
            const now = Date.now();
            accumulatedSeconds += (now - lastTick) / 1000;
            lastTick = now;
        }
    }

    function flush(completed, pageIdOverride) {
        tick();
        const seconds = Math.round(accumulatedSeconds);
        accumulatedSeconds = 0;
        if (seconds <= 0 && completed === undefined) return;

        const pageId = pageIdOverride || currentPageId;
        const payload = JSON.stringify({
            book_folder: cfg.bookFolder,
            page_id: pageId,
            seconds: seconds,
            completed: completed === undefined ? null : completed,
        });

        if (document.visibilityState === 'hidden' && navigator.sendBeacon) {
            navigator.sendBeacon('/api/activity/ping', new Blob([payload], { type: 'application/json' }));
        } else {
            fetch('/api/activity/ping', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: payload,
                keepalive: true,
            }).catch(function () {});
        }
    }

    window.__sectionChanged = function (newPageId) {
        if (newPageId && newPageId !== currentPageId) {
            flush(undefined, currentPageId);
            currentPageId = newPageId;
            lastTick = Date.now();
            resetTimerDisplay();
        }
    };

    window.__getElapsedSeconds = function () {
        tick();
        return Math.round(accumulatedSeconds);
    };

    function formatTime(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }

    function resetTimerDisplay() {
        const timerEl = document.getElementById('sectionTimer');
        if (timerEl) {
            timerEl.textContent = '⏱ 0:00';
        }
    }

    setInterval(function () {
        const timerEl = document.getElementById('sectionTimer');
        if (timerEl && timerEl.style.display !== 'none') {
            const elapsed = window.__getElapsedSeconds();
            timerEl.textContent = '⏱ ' + formatTime(elapsed);
        }
    }, 1000);

    setInterval(function () {
        tick();
        if (accumulatedSeconds >= 15) flush();
    }, 15000);

    document.addEventListener('visibilitychange', function () {
        visible = document.visibilityState === 'visible';
        if (!visible) {
            flush();
        } else {
            lastTick = Date.now();
        }
    });

    window.addEventListener('pagehide', function () {
        flush();
    });

    window.__reportComplete = function (isComplete) {
        flush(isComplete);
    };
})();
