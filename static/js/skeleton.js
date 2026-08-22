// Skeleton Loader Utilities - Visual Loading States (Improvement #2)

class SkeletonLoader {
    static createTextSkeleton(lines = 3, large = false) {
        let html = '';
        for (let i = 0; i < lines; i++) {
            const isLast = i === lines - 1;
            const width = isLast ? '70%' : '100%';
            const className = large ? 'skeleton-text large' : 'skeleton-text';
            html += `<div class="${className}" style="width: ${width};"></div>`;
        }
        return html;
    }

    static createCardSkeleton() {
        return `
            <div class="skeleton-card">
                <div class="skeleton-heading"></div>
                ${this.createTextSkeleton(2)}
            </div>
        `;
    }

    static createItemSkeleton() {
        return `
            <div class="skeleton-item">
                <div class="skeleton-avatar skeleton"></div>
                <div class="skeleton-content">
                    <div class="skeleton-text large" style="width: 80%;"></div>
                    <div class="skeleton-text" style="width: 60%;"></div>
                </div>
            </div>
        `;
    }

    static createListSkeleton(count = 3) {
        let html = '';
        for (let i = 0; i < count; i++) {
            html += this.createItemSkeleton();
        }
        return html;
    }

    static createGridSkeleton(cols = 3, count = 6) {
        let html = `<div style="display: grid; grid-template-columns: repeat(${cols}, 1fr); gap: 1rem;">`;
        for (let i = 0; i < count; i++) {
            html += this.createCardSkeleton();
        }
        html += '</div>';
        return html;
    }

    static showLoadingState(container, type = 'card') {
        if (typeof container === 'string') {
            container = document.querySelector(container);
        }
        if (!container) return;

        let html;
        switch (type) {
            case 'text':
                html = this.createTextSkeleton();
                break;
            case 'item':
                html = this.createItemSkeleton();
                break;
            case 'list':
                html = this.createListSkeleton();
                break;
            case 'grid':
                html = this.createGridSkeleton();
                break;
            case 'card':
            default:
                html = this.createCardSkeleton();
        }

        container.innerHTML = html;
        container.querySelectorAll('.skeleton').forEach(el => {
            el.classList.add('skeleton');
        });
    }

    static hideLoadingState(container) {
        if (typeof container === 'string') {
            container = document.querySelector(container);
        }
        if (container) {
            container.innerHTML = '';
        }
    }
}
