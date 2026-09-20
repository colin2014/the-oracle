/**
 * Navigation Renderer
 *
 * Renders page navigation from JSON data with CSS-based hierarchy styling
 *
 * Usage:
 *   const renderer = new NavigationRenderer();
 *   renderer.render(navigationData, currentPageId, containerElement);
 */

class NavigationRenderer {
  constructor(options = {}) {
    this.options = {
      activeClass: 'active',
      containerClass: 'navigation-tree',
      itemClass: 'nav-item',
      ...options
    };
  }

  /**
   * Render navigation tree from JSON data
   * @param {Array} navigationData - Array of navigation items from content.json
   * @param {string} currentPageId - ID of currently active page
   * @param {HTMLElement} container - Element to render into
   */
  render(navigationData, currentPageId, container) {
    // Clear existing content
    container.innerHTML = '';

    // Create nav tree
    const navTree = document.createElement('nav');
    navTree.className = this.options.containerClass;

    // Group by hierarchy level for better rendering
    const groups = this.groupByLevel(navigationData);

    // Render items
    navigationData.forEach((item, index) => {
      const navItem = this.createNavItem(item, currentPageId, navigationData, index);
      navTree.appendChild(navItem);
    });

    container.appendChild(navTree);
  }

  /**
   * Create a single navigation item element
   */
  createNavItem(item, currentPageId, allItems, index) {
    const navItem = document.createElement('div');
    navItem.className = this.options.itemClass;
    navItem.setAttribute('data-hierarchy-level', item.hierarchy_level || item.level);

    // Extract page ID from href if available
    const isActive = this.isCurrentPage(item, currentPageId);

    // Create link
    const link = document.createElement('a');
    link.href = item.href || '#';
    link.textContent = item.text;

    if (isActive) {
      link.classList.add(this.options.activeClass);
      link.setAttribute('aria-current', 'page');
    }

    // Add visual hierarchy attributes
    if (item.topic_number) {
      link.setAttribute('data-topic-number', item.topic_number);
    }

    if (item.is_last_in_section !== undefined) {
      navItem.setAttribute('data-is-last-in-section', item.is_last_in_section.toString());
    }

    navItem.appendChild(link);
    return navItem;
  }

  /**
   * Check if item is current page
   */
  isCurrentPage(item, currentPageId) {
    if (!currentPageId) return false;

    // Try matching by href
    if (item.href && item.href.includes(currentPageId)) {
      return true;
    }

    // Try matching by ID
    if (item.id === currentPageId) {
      return true;
    }

    return false;
  }

  /**
   * Group navigation items by hierarchy level
   */
  groupByLevel(items) {
    const groups = {};

    items.forEach(item => {
      const level = item.hierarchy_level || item.level;
      if (!groups[level]) {
        groups[level] = [];
      }
      groups[level].push(item);
    });

    return groups;
  }

  /**
   * Render breadcrumb navigation (flat view)
   */
  renderBreadcrumb(navigationData, currentPageId, container) {
    container.innerHTML = '';

    const breadcrumb = document.createElement('div');
    breadcrumb.className = 'nav-breadcrumb';

    // Find current page
    const currentItem = navigationData.find(item => this.isCurrentPage(item, currentPageId));

    // Build breadcrumb up to current item
    const breadcrumbItems = [];
    navigationData.forEach((item, index) => {
      breadcrumbItems.push(item);
      if (this.isCurrentPage(item, currentPageId)) {
        return; // Stop at current page
      }
    });

    // Render items
    breadcrumbItems.forEach((item, index) => {
      const isLast = index === breadcrumbItems.length - 1;

      if (!isLast) {
        const link = document.createElement('a');
        link.href = item.href || '#';
        link.textContent = this.truncateText(item.text, 40);
        breadcrumb.appendChild(link);

        const separator = document.createElement('span');
        separator.className = 'separator';
        separator.textContent = '›';
        breadcrumb.appendChild(separator);
      } else {
        const current = document.createElement('span');
        current.className = 'current';
        current.textContent = this.truncateText(item.text, 50);
        breadcrumb.appendChild(current);
      }
    });

    container.appendChild(breadcrumb);
  }

  /**
   * Truncate long text
   */
  truncateText(text, maxLength) {
    if (text.length > maxLength) {
      return text.substring(0, maxLength) + '...';
    }
    return text;
  }

  /**
   * Get hierarchy statistics
   */
  getStats(navigationData) {
    const levels = {};
    navigationData.forEach(item => {
      const level = item.hierarchy_level || item.level;
      levels[level] = (levels[level] || 0) + 1;
    });

    return {
      total: navigationData.length,
      byLevel: levels,
      levels: Object.keys(levels).map(Number).sort()
    };
  }

  /**
   * Highlight current section
   */
  highlightCurrentSection(navigationData, currentPageId, container) {
    const links = container.querySelectorAll('a');

    links.forEach(link => {
      link.classList.remove(this.options.activeClass);
      link.removeAttribute('aria-current');
    });

    // Find and highlight current
    const currentItem = navigationData.find(item => this.isCurrentPage(item, currentPageId));
    if (currentItem) {
      const currentLink = Array.from(links).find(link => link.textContent === currentItem.text);
      if (currentLink) {
        currentLink.classList.add(this.options.activeClass);
        currentLink.setAttribute('aria-current', 'page');
      }
    }
  }
}

/**
 * Helper function to load and render navigation from JSON
 */
async function loadAndRenderNavigation(contentJsonUrl, currentPageId, containerSelector) {
  try {
    // Load JSON
    const response = await fetch(contentJsonUrl);
    const contentData = await response.json();

    // Create renderer
    const renderer = new NavigationRenderer();

    // Get container
    const container = document.querySelector(containerSelector);
    if (!container) {
      console.error(`Container not found: ${containerSelector}`);
      return;
    }

    // Render navigation
    renderer.render(contentData.navigation, currentPageId, container);

    // Log stats
    const stats = renderer.getStats(contentData.navigation);
    console.log('Navigation rendered:', stats);

  } catch (error) {
    console.error('Error loading navigation:', error);
  }
}

/**
 * Example usage in HTML:
 *
 * <script>
 *   // When page loads, render navigation
 *   document.addEventListener('DOMContentLoaded', () => {
 *     loadAndRenderNavigation(
 *       '/data/Book_93/A1.1.6/content.json',  // Path to content.json
 *       '5444',                                 // Current page ID
 *       '.sidebar-nav'                          // Container selector
 *     );
 *   });
 * </script>
 */

// Export for use in modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = NavigationRenderer;
}
