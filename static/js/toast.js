// Toast Notification System - Unified Error Handling (Improvement #6)
class Toast {
    constructor() {
        this.container = null;
        this.toastCount = 0;
    }

    init() {
        if (this.container) return;
        this.container = document.getElementById('toast-container');
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.id = 'toast-container';
            this.container.className = 'toast-container';
            document.body.appendChild(this.container);
        }
    }

    show(message, type = 'info', title = '', duration = 4000) {
        this.init();
        const toastId = `toast-${++this.toastCount}`;
        const icons = {
            success: '✓',
            error: '✕',
            warning: '⚠',
            info: 'ℹ'
        };

        const toastEl = document.createElement('div');
        toastEl.className = `toast ${type}`;
        toastEl.id = toastId;

        toastEl.innerHTML = `
            <span class="toast-icon">${icons[type] || '•'}</span>
            <div class="toast-content">
                ${title ? `<div class="toast-title">${escapeHtml(title)}</div>` : ''}
                <div class="toast-message">${escapeHtml(message)}</div>
            </div>
            <button class="toast-close" type="button" aria-label="Close toast">×</button>
        `;

        this.container.appendChild(toastEl);

        const closeBtn = toastEl.querySelector('.toast-close');
        closeBtn.addEventListener('click', () => this.dismiss(toastId));

        if (duration > 0) {
            setTimeout(() => this.dismiss(toastId), duration);
        }

        return toastId;
    }

    dismiss(toastId) {
        const toast = document.getElementById(toastId);
        if (toast) {
            toast.classList.add('removing');
            setTimeout(() => {
                if (toast.parentNode) toast.parentNode.removeChild(toast);
            }, 200);
        }
    }

    success(message, title = 'Success') {
        return this.show(message, 'success', title, 4000);
    }

    error(message, title = 'Error') {
        return this.show(message, 'error', title, 5000);
    }

    warning(message, title = 'Warning') {
        return this.show(message, 'warning', title, 4000);
    }

    info(message, title = 'Info') {
        return this.show(message, 'info', title, 3000);
    }
}

function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

const toast = new Toast();
