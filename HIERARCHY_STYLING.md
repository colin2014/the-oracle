# Book Hierarchy Styling Guide

## Overview

The book hierarchy is now implemented with **clean data + CSS styling** instead of text-based visual characters.

### Benefits
✅ Clean JSON data (no visual pollution)  
✅ Semantic metadata for all pages  
✅ Beautiful CSS styling (fully customizable)  
✅ Dark mode support  
✅ Mobile responsive  
✅ Easy to maintain and update  

---

## Data Structure

Each page now contains hierarchy metadata:

```json
{
  "id": "5438",
  "title": "A1.1.1 Describe the functions and interactions of the main CPU components",
  "hierarchy_level": 3,
  "topic_number": "A1.1.1",
  "is_last_in_section": false
}
```

### Hierarchy Levels

- **Level 0**: Introduction pages
- **Level 1**: Top-level themes (e.g., A1, A2, A3, A4, B1, B2, B3, B4)
- **Level 2**: Subsections (e.g., A1.1, A1.2, A2.1, A2.2)
- **Level 3**: Topic pages (e.g., A1.1.1, A1.1.2, A1.1.3)
- **Level 4**: (if needed) Sub-topics or specialized content

---

## HTML Implementation

### Attributes

Add these data attributes to your page elements:

```html
<!-- Introduction -->
<div class="book-page" 
     data-hierarchy-type="introduction"
     data-hierarchy-level="0">
  Introduction
</div>

<!-- Level 1: Theme -->
<div class="book-page"
     data-hierarchy-level="1"
     data-topic-number="A1">
  A1 Computer fundamentals
</div>

<!-- Level 2: Section -->
<div class="book-page"
     data-hierarchy-level="2"
     data-topic-number="A1.1">
  A1.1 Computer hardware and operation
</div>

<!-- Level 3: Topic -->
<div class="book-page"
     data-hierarchy-level="3"
     data-topic-number="A1.1.1"
     data-is-last-in-section="false">
  <span class="topic-number">A1.1.1</span>
  Describe the functions and interactions of the main CPU components
</div>

<!-- Last topic in section -->
<div class="book-page"
     data-hierarchy-level="3"
     data-topic-number="A1.1.9"
     data-is-last-in-section="true">
  <span class="topic-number">A1.1.9</span>
  Describe different types of services in cloud computing
</div>

<!-- Current/Active page -->
<div class="book-page"
     data-hierarchy-level="3"
     data-topic-number="A2.1.5"
     class="active">
  <span class="topic-number">A2.1.5</span>
  Describe the function of the TCP/IP model (HL only)
</div>
```

---

## CSS Styling Features

### Color Scheme

| Level | Color | Style |
|-------|-------|-------|
| Intro | Blue (#3b82f6) | Highlight background |
| Level 1 | Purple (#6b21a8) | Bold, thick border |
| Level 2 | Green (#059669) | Medium weight, subtle background |
| Level 3 | Gray (#6b7280) | Normal weight, light border |
| Active | Blue (#3b82f6) | Highlight + checkmark |

### Visual Indicators

- **Level 1** (Themes): `▶` arrow + left border
- **Level 2** (Sections): 📁 folder icon
- **Level 3** (Topics): 📄 page icon  
- **Active Page**: ✓ checkmark indicator
- **Section Breaks**: Bottom border on last item

### Responsive Behavior

- Padding adjusts on mobile devices
- Icons remain visible at all sizes
- Text remains readable

### Dark Mode

CSS automatically adapts for dark mode using `@media (prefers-color-scheme: dark)`

---

## Quick Template

```html
<!DOCTYPE html>
<html>
<head>
    <link rel="stylesheet" href="styles/book-hierarchy.css">
</head>
<body>
    <!-- Use data attributes based on your JSON -->
    <div class="book-pages">
        <!-- Your pages here -->
    </div>
</body>
</html>
```

---

## Customization

### Modify Colors

Edit `styles/book-hierarchy.css`:

```css
/* Level 1 - Themes */
.book-page[data-hierarchy-level="1"] {
  border-left: 4px solid #YOUR_COLOR;
  color: #YOUR_TEXT_COLOR;
  background: linear-gradient(to right, #YOUR_BG, transparent);
}
```

### Add More Levels

If you need level 4 or 5:

```css
.book-page[data-hierarchy-level="4"] {
  padding: 8px 0 8px 64px;
  border-left: 1px dashed #d1d5db;
  font-size: 11px;
  opacity: 0.8;
}
```

### Change Icons

Replace the `::before` pseudo-elements:

```css
.book-page[data-hierarchy-level="1"]::before {
  content: "📘";  /* Change this */
}
```

---

## JSON Generation

Your data already has the required fields:

```python
{
  "title": str,
  "hierarchy_level": int,      # 0, 1, 2, 3, 4
  "topic_number": str,         # "A1.1.1"
  "hierarchy_type": str,       # "introduction" or null
  "is_last_in_section": bool   # true/false
}
```

---

## Files Included

- `styles/book-hierarchy.css` - Main stylesheet
- `templates/book-hierarchy-example.html` - Example HTML
- `HIERARCHY_STYLING.md` - This file
- JSON files updated with metadata

---

## Browser Support

- Chrome/Edge: ✅ Full support
- Firefox: ✅ Full support
- Safari: ✅ Full support
- Mobile browsers: ✅ Full support

---

## Next Steps

1. ✅ Data cleaned and metadata added
2. ✅ CSS stylesheet created
3. 📝 Integrate into your frontend template
4. 📝 Update your book display component
5. 📝 Test on different screen sizes

