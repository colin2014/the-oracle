# 🚀 Quick Start Guide

## Get Started in 3 Steps

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Start the Server
```bash
python app.py
```

You'll see:
```
 * Running on http://localhost:5000
```

### Step 3: Open in Browser
Visit: **http://localhost:5000**

---

## Try It Out!

### Example: Scrape the GrowHall CPU Page

1. **Copy this URL**: `https://app.growhall.com/books/93/5438`
2. **Paste into the "Scrape Content" box** on the left panel
3. **Click "Scrape URL"**
4. **Wait for completion** (should take 10-30 seconds depending on page size)
5. **View your scraped content** - it appears in the "All Scraped Content" list

### What You'll Get

✅ **Organized Content**
- All page sections organized by topic
- Study Tips, Theory of Knowledge, etc. highlighted separately
- Hierarchical navigation structure preserved

✅ **Embedded Images**
- All images downloaded and embedded
- Image gallery at the bottom
- Alt text preserved

✅ **Searchable**
- Search across all scraped content
- Find content by keywords
- Results show which section matched

---

## Understanding the Interface

### Left Panel
- **Scrape Content** - Enter URLs here
- **Search** - Find content across all scraped pages
- **All Scraped Content** - Your saved items (click to view)

### Right Panel
- **Navigation Structure** - Shows page hierarchy
- **Main Content** - Primary page content in sections
- **Sidebar Sections** - Study tips, theory, applied work, etc.
- **Images Gallery** - All embedded images

---

## File Storage

Your scraped content is saved locally in:
```
data/
├── scraped_abc123/
│   ├── content.json      ← Full content in JSON format
│   └── images/           ← Downloaded images
│       ├── image_0.jpg
│       ├── image_1.png
│       └── ...
└── scraped_def456/
    ├── content.json
    └── images/
```

**Why JSON?** Easy to parse, back up, or export to other formats!

---

## Tips & Tricks

### 💡 Scrape Multiple Pages
Keep scraping different URLs - they all get organized and searchable!

### 🔍 Use Search Effectively
- Search for "CPU" to find it in any scraped content
- Search for specific section names like "Study Tip"
- Results show you which section matched

### 💾 Backup Your Content
The `data/` folder contains everything. Back it up to keep your scraped content safe.

### 🖼️ Images are Local
Images are downloaded and stored locally, so they load instantly even offline!

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "ModuleNotFoundError" | Run `pip install -r requirements.txt` |
| Port 5000 already in use | Edit app.py and change `port=5000` to another port |
| Images not displaying | Check `data/scraped_*/images/` folder exists |
| Content incomplete | Some dynamic content requires JavaScript (browser scraper needed) |

---

## What Gets Scraped?

✅ **Extracts:**
- Page title and main heading
- Navigation structure and hierarchy
- All text content
- Special sections (Study Tips, Theory, etc.)
- All images and their alt text
- Sidebar content

❌ **Doesn't capture:**
- JavaScript-loaded content
- Videos
- Interactive elements
- Dynamic forms

---

## Next Steps

1. **Explore** - Scrape a few pages to see how it organizes them
2. **Search** - Try searching to find specific topics
3. **Customize** - Edit `scraper.py` to identify additional section types
4. **Export** - Use the JSON data to export to PDF, Word, etc.

---

## Questions?

Check the full `README.md` for:
- Detailed API documentation
- Advanced configuration
- Data format specification
- Integration examples

Enjoy! 🎉
