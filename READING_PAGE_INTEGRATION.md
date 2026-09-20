# Reading Page Navigation Integration Guide

## Overview

This guide shows how to integrate the CSS-styled navigation hierarchy into your reading/learning pages where students view individual chapters.

## Architecture

```
┌─────────────────────────────────────────┐
│        Reading Page (HTML)              │
├──────────────┬──────────────────────────┤
│              │                          │
│   Sidebar    │   Main Content Area      │
│ Navigation   │   - Page Title           │
│   (styled    │   - Breadcrumb           │
│    with      │   - Article Content      │
│    CSS)      │   - Navigation Links     │
│              │                          │
└──────────────┴──────────────────────────┘
```

## Files Included

| File | Purpose |
|------|---------|
| `styles/page-navigation.css` | Navigation styling (hierarchy, colors, responsive) |
| `scripts/navigation-renderer.js` | JavaScript to render navigation from JSON |
| `templates/reading-page-example.html` | Complete working example |
| `READING_PAGE_INTEGRATION.md` | This file |

## Quick Start

### 1. Include CSS and JS

```html
<!DOCTYPE html>
<html>
<head>
    <link rel="stylesheet" href="styles/page-navigation.css">
</head>
<body>
    <div class="reading-container">
        <!-- Navigation sidebar -->
        <aside class="sidebar-nav">
            <h3>📚 Navigation</h3>
            <div id="nav-container"></div>
        </aside>

        <!-- Main content -->
        <main class="content-area">
            <!-- Your page content here -->
        </main>
    </div>

    <script src="scripts/navigation-renderer.js"></script>
    <script>
        // Load and render navigation when page loads
        document.addEventListener('DOMContentLoaded', () => {
            loadAndRenderNavigation(
                '/data/Book_93/A1.1.6/content.json',  // JSON file path
                '5444',                                 // Current page ID
                '#nav-container'                        // Container element
            );
        });
    </script>
</body>
</html>
```

### 2. HTML Structure

```html
<!-- Sidebar Navigation Container -->
<aside class="sidebar-nav">
    <h3>📚 Navigation</h3>
    <div id="nav-container"></div>
</aside>

<!-- Main Content -->
<main class="content-area">
    <div class="page-header">
        <h1>A1.1.6 Pipelining in Multi-core Architectures</h1>
        <div class="breadcrumb">
            <!-- Breadcrumb here -->
        </div>
    </div>

    <article class="content">
        <!-- Your article content -->
    </article>
</main>
```

## Manual Rendering (Without JavaScript)

If you prefer to render HTML directly in your backend:

```html
<!-- Navigation tree from JSON -->
<nav class="navigation-tree">
    <!-- Introduction -->
    <div class="nav-item" data-hierarchy-level="0">
        <a href="/books/93/6840">Introduction</a>
    </div>

    <!-- Level 1: Theme -->
    <div class="nav-item" data-hierarchy-level="1">
        <a href="/books/93/5438">Theme A Concepts of computer science</a>
    </div>

    <!-- Level 2: Section -->
    <div class="nav-item" data-hierarchy-level="2">
        <a href="/books/93/5438">A1 Computer fundamentals</a>
    </div>

    <!-- Level 3: Subsection -->
    <div class="nav-item" data-hierarchy-level="3">
        <a href="/books/93/5438">A1.1 Computer hardware and operation</a>
    </div>

    <!-- Level 4: Topic Pages -->
    <div class="nav-item" data-hierarchy-level="4">
        <a href="/books/93/5438">A1.1.1 Describe CPU components</a>
    </div>
    <div class="nav-item" data-hierarchy-level="4">
        <a href="/books/93/5439">A1.1.2 Describe GPU role</a>
    </div>
    <div class="nav-item" data-hierarchy-level="4" data-is-last-in-section="false">
        <a href="/books/93/5444" class="active" aria-current="page">
            A1.1.6 Pipelining in multi-core
        </a>
    </div>
    <div class="nav-item" data-hierarchy-level="4" data-is-last-in-section="true">
        <a href="/books/93/5447">A1.1.9 Cloud computing services</a>
    </div>
</nav>
```

## Data Attributes

Each navigation item uses these attributes for styling:

| Attribute | Values | Purpose |
|-----------|--------|---------|
| `data-hierarchy-level` | 0,1,2,3,4 | Indentation and styling |
| `data-topic-number` | "A1.1.1" | (Optional) Display topic ID |
| `data-is-last-in-section` | "true"/"false" | Add bottom border separator |
| `class="active"` | - | Highlight current page |
| `aria-current="page"` | - | Accessibility: current page |

## CSS Classes

### Container Classes

- `.navigation-tree` - Main navigation container
- `.nav-tree` - Alternative container class
- `.sidebar-nav` - Sidebar specific styling
- `.nav-breadcrumb` - Breadcrumb navigation (flat view)

### Item Classes

- `.nav-item` - Individual navigation item
- `.nav-item[data-hierarchy-level="1"]` - Level 1 styling
- `.nav-item[data-hierarchy-level="2"]` - Level 2 styling
- `.nav-item[data-hierarchy-level="3"]` - Level 3 styling
- `.nav-item[data-hierarchy-level="4"]` - Level 4 styling

### Link Classes

- `a.active` - Current page styling
- `a[aria-current="page"]` - Accessible current page indicator

## Visual Appearance

### Light Mode

```
▶ Level 1: Theme (Purple, thick border)
  📁 Level 2: Section (Green, medium border)
    ├ Level 3: Subsection (Gray, thin border)
      └ Level 4: Topic (Gray, dotted border)
          [current page highlighted in blue]
```

### Dark Mode

CSS automatically adjusts colors based on system preference:
- Dark text becomes light
- Backgrounds become darker
- Colors shift to dark-appropriate palette

## Responsive Behavior

### Desktop (> 1024px)
- Sidebar: 280px fixed width, sticky position
- Content: Full remaining width
- Navigation: Scrollable independently

### Tablet (768px - 1024px)
- Sidebar converts to horizontal layout
- Reduced indentation
- Same navigation structure

### Mobile (< 768px)
- Single column layout
- Navigation above content
- Adjusted padding and font sizes
- Easier touch targets

## Customization

### Change Colors

Edit `styles/page-navigation.css`:

```css
/* Level 1 Theme Color */
.nav-item[data-hierarchy-level="1"] a {
  color: #581c87;              /* Text color */
  background-color: #faf5ff;   /* Background */
  border-left: 3px solid #6b21a8;  /* Left border */
}
```

### Change Icons

Modify the `::before` pseudo-elements:

```css
.nav-item[data-hierarchy-level="1"] a::before {
  content: "📘";  /* Change icon here */
}
```

### Adjust Indentation

```css
.nav-item[data-hierarchy-level="2"] a {
  padding: 11px 12px 11px 32px;  /* Left padding controls indent */
}

.nav-item[data-hierarchy-level="3"] a {
  padding: 9px 12px 9px 48px;    /* Increase for more indent */
}
```

## JavaScript API

### NavigationRenderer Class

```javascript
const renderer = new NavigationRenderer({
  activeClass: 'active',          // Class for active item
  containerClass: 'navigation-tree', // Container class
  itemClass: 'nav-item'           // Item class
});

// Render navigation
renderer.render(
  navigationData,    // Array from content.json
  currentPageId,     // Current page ID
  containerElement   // DOM element to render into
);

// Get statistics
const stats = renderer.getStats(navigationData);
console.log(stats);
// Output: {
//   total: 114,
//   byLevel: {1: 4, 2: 15, 3: 45, 4: 50},
//   levels: [1, 2, 3, 4]
// }

// Render breadcrumb
renderer.renderBreadcrumb(
  navigationData,
  currentPageId,
  breadcrumbContainer
);

// Update active page
renderer.highlightCurrentSection(
  navigationData,
  newPageId,
  container
);
```

### Helper Function

```javascript
// Load JSON and render automatically
loadAndRenderNavigation(
  '/data/Book_93/A1.1.6/content.json',  // Content JSON path
  '5444',                                 // Current page ID
  '.sidebar-nav'                          // Container selector
);
```

## Example Integration

See `templates/reading-page-example.html` for a complete working example with:
- Sidebar navigation
- Main content area
- Breadcrumb navigation
- Responsive layout
- Dark mode support

## Accessibility

The implementation includes:

- ✅ Semantic HTML (`<nav>`, `<a>`, `<aside>`, `<main>`)
- ✅ `aria-current="page"` for current page
- ✅ Proper heading hierarchy
- ✅ Color not the only visual indicator
- ✅ Sufficient color contrast
- ✅ Keyboard navigable links
- ✅ Mobile touch-friendly targets

## Browser Support

| Browser | Support |
|---------|---------|
| Chrome | ✅ Full |
| Firefox | ✅ Full |
| Safari | ✅ Full |
| Edge | ✅ Full |
| Mobile browsers | ✅ Full |

## Performance

- **CSS-only styling** - No runtime performance impact
- **Lightweight JS** - Optional, only ~3KB
- **Responsive design** - No breakpoint switching delays
- **Dark mode** - Uses CSS media query, no JS needed

## Troubleshooting

### Navigation not showing

```javascript
// Check if data loaded correctly
console.log(navigationData);

// Verify container exists
console.log(document.querySelector('#nav-container'));

// Check browser console for errors
```

### Wrong styling applied

```css
/* Ensure CSS is loaded before JS runs */
/* Check that data attributes match CSS selectors */
/* data-hierarchy-level="1" must have CSS for [data-hierarchy-level="1"] */
```

### Not responsive

```css
/* Verify viewport meta tag in <head> */
<meta name="viewport" content="width=device-width, initial-scale=1.0">

/* Check media queries are applied */
@media (max-width: 768px) { ... }
```

## Production Checklist

- [ ] Include CSS file in `<head>`
- [ ] Include JS file before `</body>`
- [ ] Verify data attributes in HTML
- [ ] Test on mobile/tablet/desktop
- [ ] Test in light and dark mode
- [ ] Test keyboard navigation
- [ ] Verify links work correctly
- [ ] Check accessibility with screen reader
- [ ] Test with no JavaScript enabled

