// Onboarding Tour System - Interactive First-Time User Guide (Improvement #10)

class OnboardingTour {
    constructor(steps = []) {
        this.steps = steps;
        this.currentStep = 0;
        this.isActive = false;
        this.overlay = null;
        this.spotlight = null;
        this.tooltip = null;
        this.skipBtn = null;
    }

    addStep(element, title, description, position = 'bottom') {
        this.steps.push({
            element,
            title,
            description,
            position
        });
        return this;
    }

    start() {
        if (this.steps.length === 0) return;

        this.isActive = true;
        this.currentStep = 0;
        this.createOverlay();
        this.createSkipButton();
        this.showStep(0);

        document.addEventListener('keydown', (e) => {
            if (!this.isActive) return;
            if (e.key === 'Escape') this.end();
            if (e.key === 'ArrowRight') this.next();
            if (e.key === 'ArrowLeft') this.prev();
        });
    }

    createOverlay() {
        if (this.overlay) return;

        this.overlay = document.createElement('div');
        this.overlay.className = 'tour-overlay active';
        document.body.appendChild(this.overlay);

        this.spotlight = document.createElement('div');
        this.spotlight.className = 'tour-spotlight';
        document.body.appendChild(this.spotlight);
    }

    createSkipButton() {
        if (this.skipBtn) return;

        this.skipBtn = document.createElement('button');
        this.skipBtn.className = 'skip-tour-btn active';
        this.skipBtn.textContent = '✕ Skip Tour';
        this.skipBtn.addEventListener('click', () => this.end());
        document.body.appendChild(this.skipBtn);
    }

    showStep(index) {
        if (index < 0 || index >= this.steps.length) return;

        this.currentStep = index;
        const step = this.steps[index];
        const element = typeof step.element === 'string'
            ? document.querySelector(step.element)
            : step.element;

        if (!element) {
            this.next();
            return;
        }

        // Position spotlight
        const rect = element.getBoundingClientRect();
        const padding = 8;

        this.spotlight.style.top = (rect.top - padding) + 'px';
        this.spotlight.style.left = (rect.left - padding) + 'px';
        this.spotlight.style.width = (rect.width + padding * 2) + 'px';
        this.spotlight.style.height = (rect.height + padding * 2) + 'px';

        // Create/update tooltip
        this.createTooltip(step, element);

        // Scroll element into view
        element.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    createTooltip(step, element) {
        // Remove old tooltip
        if (this.tooltip) {
            this.tooltip.remove();
        }

        this.tooltip = document.createElement('div');
        this.tooltip.className = 'tour-tooltip';

        const rect = element.getBoundingClientRect();
        const padding = 16;

        let top, left;
        const position = step.position || 'bottom';

        switch (position) {
            case 'top':
                top = rect.top - this.tooltip.offsetHeight - padding;
                left = rect.left + rect.width / 2;
                break;
            case 'left':
                top = rect.top + rect.height / 2;
                left = rect.left - 350 - padding;
                break;
            case 'right':
                top = rect.top + rect.height / 2;
                left = rect.right + padding;
                break;
            case 'bottom':
            default:
                top = rect.bottom + padding;
                left = rect.left + rect.width / 2;
        }

        this.tooltip.innerHTML = `
            <h3>${step.title}</h3>
            <p>${step.description}</p>
            <div class="tour-controls">
                <span class="tour-progress">${this.currentStep + 1} / ${this.steps.length}</span>
                <div class="tour-buttons">
                    ${this.currentStep > 0 ? '<button class="tour-btn" id="prev-btn">← Prev</button>' : ''}
                    <button class="tour-btn primary" id="next-btn">
                        ${this.currentStep === this.steps.length - 1 ? 'Finish' : 'Next →'}
                    </button>
                </div>
            </div>
        `;

        document.body.appendChild(this.tooltip);

        // Position tooltip
        this.tooltip.style.top = top + 'px';
        this.tooltip.style.left = left + 'px';
        this.tooltip.style.transform = 'translate(-50%, -50%)';

        // Event listeners
        const nextBtn = this.tooltip.querySelector('#next-btn');
        const prevBtn = this.tooltip.querySelector('#prev-btn');

        nextBtn.addEventListener('click', () => this.next());
        if (prevBtn) prevBtn.addEventListener('click', () => this.prev());

        // Adjust if tooltip goes off-screen
        setTimeout(() => this.adjustTooltipPosition(), 0);
    }

    adjustTooltipPosition() {
        if (!this.tooltip) return;

        const rect = this.tooltip.getBoundingClientRect();
        let top = parseInt(this.tooltip.style.top);
        let left = parseInt(this.tooltip.style.left);

        if (rect.right > window.innerWidth) {
            left -= rect.right - window.innerWidth + 20;
        }
        if (rect.left < 0) {
            left -= rect.left - 20;
        }
        if (rect.bottom > window.innerHeight) {
            top -= rect.bottom - window.innerHeight + 20;
        }

        this.tooltip.style.top = top + 'px';
        this.tooltip.style.left = left + 'px';
    }

    next() {
        if (this.currentStep < this.steps.length - 1) {
            this.showStep(this.currentStep + 1);
        } else {
            this.end();
        }
    }

    prev() {
        if (this.currentStep > 0) {
            this.showStep(this.currentStep - 1);
        }
    }

    end() {
        this.isActive = false;

        if (this.overlay) this.overlay.remove();
        if (this.spotlight) this.spotlight.remove();
        if (this.tooltip) this.tooltip.remove();
        if (this.skipBtn) this.skipBtn.remove();

        this.overlay = null;
        this.spotlight = null;
        this.tooltip = null;
        this.skipBtn = null;

        // Mark as completed in localStorage
        localStorage.setItem('tour-completed', 'true');
    }

    static hasCompletedTour() {
        return localStorage.getItem('tour-completed') === 'true';
    }

    static resetTour() {
        localStorage.removeItem('tour-completed');
    }
}
