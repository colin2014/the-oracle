// General Utilities - Accessibility, Search, etc. (Improvements #1, #7, #9)

class AccessibilityUtils {
    static enableKeyboardNavigation(container, items) {
        let selectedIndex = 0;

        items.forEach((item, index) => {
            item.addEventListener('keydown', (e) => {
                if (e.key === 'ArrowDown') {
                    e.preventDefault();
                    selectedIndex = (selectedIndex + 1) % items.length;
                    items[selectedIndex].focus();
                } else if (e.key === 'ArrowUp') {
                    e.preventDefault();
                    selectedIndex = (selectedIndex - 1 + items.length) % items.length;
                    items[selectedIndex].focus();
                } else if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    item.click();
                }
            });
        });
    }

    static addAriaLabels(element, label) {
        element.setAttribute('aria-label', label);
    }

    static setAriaExpanded(element, expanded) {
        element.setAttribute('aria-expanded', expanded ? 'true' : 'false');
    }

    static setAriaHidden(element, hidden) {
        element.setAttribute('aria-hidden', hidden ? 'true' : 'false');
    }

    static announceToScreenReader(message, priority = 'polite') {
        const announcement = document.createElement('div');
        announcement.setAttribute('role', 'status');
        announcement.setAttribute('aria-live', priority);
        announcement.className = 'sr-only';
        announcement.textContent = message;
        document.body.appendChild(announcement);

        setTimeout(() => announcement.remove(), 1000);
    }

    static enableGlobalKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Cmd/Ctrl + K for global search
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                const searchInput = document.querySelector('.global-search-input');
                if (searchInput) {
                    searchInput.focus();
                }
            }
        });
    }
}

class GlobalSearch {
    constructor(config = {}) {
        this.config = {
            inputSelector: '.global-search-input',
            dropdownSelector: '.search-results-dropdown',
            ...config
        };
        this.searchIndex = [];
        this.init();
    }

    init() {
        const input = document.querySelector(this.config.inputSelector);
        const dropdown = document.querySelector(this.config.dropdownSelector);

        if (!input) return;

        input.addEventListener('input', (e) => this.handleSearch(e));
        input.addEventListener('keydown', (e) => this.handleKeydown(e));

        // Close on outside click
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.global-search-wrapper')) {
                dropdown?.classList.remove('active');
            }
        });
    }

    addToIndex(items) {
        this.searchIndex = items;
    }

    handleSearch(event) {
        const query = event.target.value.toLowerCase().trim();
        const dropdown = document.querySelector(this.config.dropdownSelector);

        if (query.length === 0) {
            dropdown?.classList.remove('active');
            return;
        }

        const results = this.searchIndex.filter(item =>
            item.title.toLowerCase().includes(query) ||
            item.description?.toLowerCase().includes(query)
        ).slice(0, 8);

        this.renderResults(results);
    }

    handleKeydown(event) {
        const dropdown = document.querySelector(this.config.dropdownSelector);
        const items = dropdown?.querySelectorAll('.search-result');

        if (event.key === 'Escape') {
            dropdown?.classList.remove('active');
        } else if (event.key === 'ArrowDown' && items?.length > 0) {
            event.preventDefault();
            items[0].focus();
        }
    }

    renderResults(results) {
        const dropdown = document.querySelector(this.config.dropdownSelector);
        if (!dropdown) return;

        if (results.length === 0) {
            dropdown.innerHTML = '<div style="padding: 1rem; text-align: center; color: var(--text-light);">No results found</div>';
        } else {
            dropdown.innerHTML = results.map(result => `
                <a href="${result.url}" class="search-result">
                    <div class="search-result-title">${escapeHtml(result.title)}</div>
                    ${result.type ? `<span class="search-result-type">${result.type}</span>` : ''}
                </a>
            `).join('');

            dropdown.querySelectorAll('.search-result').forEach(el => {
                el.addEventListener('click', () => {
                    dropdown.classList.remove('active');
                });
            });
        }

        dropdown.classList.add('active');
    }
}

class NavigationHelper {
    static setActiveNav(selector, activeSelector = 'active') {
        const navItems = document.querySelectorAll(selector);
        const currentPath = window.location.pathname;

        navItems.forEach(item => {
            const href = item.getAttribute('href');
            if (href && currentPath.startsWith(href)) {
                item.classList.add(activeSelector);
            } else {
                item.classList.remove(activeSelector);
            }
        });
    }

    static addBreadcrumbs(items = []) {
        const breadcrumb = document.querySelector('.breadcrumb');
        if (!breadcrumb) {
            const nav = document.querySelector('.app-nav');
            if (nav) {
                const bc = document.createElement('div');
                bc.className = 'breadcrumb';
                nav.insertAdjacentElement('afterend', bc);
            }
        }

        const bcEl = document.querySelector('.breadcrumb');
        if (bcEl) {
            bcEl.innerHTML = items.map((item, index) => {
                if (index === items.length - 1) {
                    return `<span>${item.label}</span>`;
                }
                return `<a href="${item.url}">${item.label}</a>`;
            }).join(' / ');
        }
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

// Initialize utilities on document ready
document.addEventListener('DOMContentLoaded', () => {
    AccessibilityUtils.enableGlobalKeyboardShortcuts();
    NavigationHelper.setActiveNav('.nav-link');
});
