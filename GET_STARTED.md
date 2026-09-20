# 🚀 Complete Setup Guide - Content Scraper & Organizer

Welcome! This guide will get you up and running in 10 minutes.

## What You're Getting

A complete content scraping system with:
- 🌐 **Web Dashboard** - Beautiful interface to view and search content
- 🔌 **Chrome Extension** - One-click scraping from any page
- 💾 **Local Storage** - All content saved on your computer
- 🔍 **Full-Text Search** - Search across all scraped pages
- 🖼️ **Embedded Images** - Automatic image download and display

---

## Prerequisites

- **Python 3.12+** installed
- **Chrome browser** (for the extension)
- **Administrator access** (for installing Python packages)

---

## Part 1: Setup Backend & Dashboard (10 minutes)

### Step 1.1: Install Python Dependencies

```bash
pip install -r requirements.txt
```

Wait for all packages to install:
- Flask (web server)
- BeautifulSoup4 (HTML parsing)
- Requests (HTTP fetching)
- Pillow (image processing)

### Step 1.2: Start the Flask Server

```bash
python app.py
```

You should see:
```
 * Running on http://localhost:5000
```

**Leave this running!** (Don't close the terminal)

### Step 1.3: Open Dashboard

Visit in your browser: **http://localhost:5000**

You should see a beautiful dashboard with:
- "Scrape Content" panel on the left
- "Search" box
- Empty "All Scraped Content" area
- Welcome message in the main area

✅ **Backend is ready!**

---

## Part 2: Setup Chrome Extension (5 minutes)

### Step 2.1: Create Extension Icons

In a **new terminal** (keep the Flask server running), run:

```bash
python extension/create_icons.py
```

You should see:
```
✓ Created extension/images/icon16.png
✓ Created extension/images/icon48.png
✓ Created extension/images/icon128.png
✓ All icons created successfully!
```

### Step 2.2: Load Extension in Chrome

1. **Open Chrome**
2. Go to: `chrome://extensions/`
3. Enable **Developer Mode** (toggle in top right)
4. Click **Load unpacked**
5. Navigate to the `extension/` folder in this project
6. Click **Open**

You should now see "Content Scraper" in your Chrome toolbar!

### Step 2.3: Configure Extension

1. **Click the extension icon** in your toolbar
2. You'll see the popup with settings
3. Enter server URL: `http://localhost:5000`
4. Click **Save Settings**

✅ **Extension is ready!**

---

## Part 3: Try It Out! (5 minutes)

### Option A: Scrape from the Dashboard

1. Visit: **http://localhost:5000**
2. Paste a URL in the "Scrape Content" box
   - Example: `https://example.com`
3. Click **"Scrape URL"**
4. Wait 10-30 seconds
5. See your content appear!

### Option B: Scrape with the Extension (Better!)

1. **Navigate to any webpage** (even authenticated ones!)
   - Example: A course page, blog post, documentation
2. **Click the extension icon** in toolbar
3. You'll see stats:
   - Content size
   - Number of images
   - Number of sections
4. Click **"🔍 Scrape This Page"**
5. Wait for success message
6. Dashboard opens automatically with your content!

### What You'll See

After scraping, the dashboard shows:
- ✅ **Navigation Structure** - Hierarchical menu
- ✅ **Main Content** - Organized by headings
- ✅ **Sidebar Sections** - Study Tips, Theory, etc. (highlighted)
- ✅ **Image Gallery** - All images from the page
- ✅ **Search** - Works across all scraped content

---

## Part 4: Understanding the Interface

### Left Panel

**🔗 Scrape Content**
- Paste URL and click scrape
- Shows success/error status

**🔍 Search**
- Type to search all content
- Click "Search" to find matches
- Results show which fields matched

**📚 All Scraped Content**
- List of everything you've scraped
- Click any item to view
- Shows date and image count

### Right Panel

**Navigation Structure**
- Shows page hierarchy
- Usually matches the page's table of contents

**Main Content**
- Content organized by section headings
- Color-coded for readability

**Sidebar Sections**
- Special sections highlighted with colors:
  - 🟡 Study Tips (yellow)
  - 🔵 Theory of Knowledge (blue)
  - 🔴 Applied Work (red)
  - 🟢 Vocabulary (green)

**Image Gallery**
- All images from the page
- Thumbnails with alt text

---

## File Structure

```
airplay/
├── app.py                    # Flask server (KEEP RUNNING)
├── scraper.py                # Scraping logic
├── requirements.txt          # Python packages
│
├── templates/index.html      # Dashboard webpage
├── static/
│   ├── css/style.css         # Styling
│   └── js/app.js             # Frontend logic
│
├── extension/                # Chrome extension
│   ├── manifest.json         # Extension config
│   ├── popup.html            # Extension popup UI
│   ├── popup.css             # Popup styling
│   ├── popup.js              # Extraction logic
│   ├── background.js         # Service worker
│   ├── create_icons.py       # Icon generator
│   └── images/               # Extension icons
│       ├── icon16.png
│       ├── icon48.png
│       └── icon128.png
│
├── data/                     # Generated scraped content
│   ├── scraped_abc123/
│   │   ├── content.json      # Structured content
│   │   └── images/           # Downloaded images
│   └── scraped_def456/
│       ├── content.json
│       └── images/
│
└── docs/
    ├── README.md             # Full documentation
    ├── QUICKSTART.md         # Quick reference
    ├── EXTENSION_README.md   # Extension guide
    └── SYSTEM_OVERVIEW.md    # Technical details
```

---

## Troubleshooting

### Dashboard Won't Load

**Problem:** Can't access http://localhost:5000

**Solution:**
1. Make sure Flask server is running (`python app.py`)
2. Check terminal doesn't show errors
3. Try port 5001 instead: Edit app.py line `app.run(debug=True, port=5001)`

### Extension Not Loading

**Problem:** Extension doesn't appear in chrome://extensions/

**Solution:**
1. Make sure Developer Mode is ON (top right toggle)
2. Delete and reload: Remove extension, then Load unpacked again
3. Check manifest.json for syntax errors

### Extension Can't Connect

**Problem:** Error when clicking "Scrape This Page"

**Solution:**
1. Make sure Flask server is running
2. Check server URL in extension (should be http://localhost:5000)
3. Click "Save Settings" after changing URL

### Images Not Showing

**Problem:** Image icons but no images display

**Solution:**
1. Check `data/scraped_*/images/` folder has files
2. Some images may be blocked by CORS
3. Verify file permissions (Windows may need admin)

### Extension Icons Look Wrong

**Problem:** Icon is blank or wrong color

**Solution:**
1. Run: `python extension/create_icons.py`
2. Reload extension (F5 on extensions page)
3. Restart Chrome

---

## Common Tasks

### Scrape Multiple Pages

1. Keep Flask server running
2. Use extension to scrape different pages
3. Each appears in the content list
4. Click any to view

### Search Content

1. Type in search box
2. Press Enter or click Search
3. Results show which page matched
4. Click result to view full content

### Backup Scraped Content

**Your data is in:** `data/`

To backup:
1. Copy the `data/` folder somewhere safe
2. To restore: Paste it back in the project folder

### Export Content

Content is stored as JSON:
- Open `data/scraped_abc123/content.json`
- Use online JSON tools to convert to other formats
- Or write a Python script to convert to PDF/Word

---

## Tips & Tricks

💡 **Best Sites to Scrape**
- Course pages (GrowHall, Coursera, etc.)
- Documentation sites
- Blog posts
- Wikipedia articles
- News articles
- Research papers

💡 **Extension vs Dashboard**
- Use **Extension** for authenticated pages (you're logged in)
- Use **Dashboard** for public URLs you just want to save

💡 **Search Strategy**
- Search for specific topics (e.g., "CPU", "evolution")
- Search for section names (e.g., "Study Tip", "Vocabulary")
- Short searches are usually better

💡 **Organize Your Content**
- Scrape related pages together
- Use dashboard search to group by topic
- Content stays local—you can move/backup anytime

---

## Next Steps

1. ✅ Follow the setup above
2. ✅ Try scraping one page with the extension
3. ✅ Explore the dashboard
4. ✅ Search your content
5. ✅ Read full docs in README.md

---

## Getting Help

- **Questions?** Check the README.md in project root
- **Extension issues?** See EXTENSION_README.md
- **Technical details?** Read SYSTEM_OVERVIEW.md
- **Errors?** Check browser console (F12 → Console)

---

## What To Do Next

**Once Setup Works:**

### Try These Examples

1. **Public page scraping**
   - Visit: https://example.com
   - Click extension
   - Scrape it

2. **Authenticated page scraping**
   - Login to any service
   - Navigate to a page
   - Click extension
   - Scrape it (dashboard URL version won't work for this)

3. **Search test**
   - Scrape 3+ pages
   - Search for a common word
   - See results across pages

4. **Multi-page learning**
   - Scrape chapters from a course
   - Search for key concepts
   - Build your personal knowledge base

---

## Important Notes

⚠️ **Keep Server Running**
The Flask server must be running for the extension to work. Keep that terminal open!

⚠️ **Respect Terms of Service**
Only scrape pages you have permission to scrape. Check the website's ToS.

⚠️ **Copyright & Attribution**
You own the local copies, but respect original authors' copyright.

---

## System Requirements

- Python 3.12+
- 200MB free disk space (for dependencies and data)
- Chrome/Chromium browser
- 2GB RAM minimum
- Stable internet connection (for scraping)

---

## Performance

| Task | Time |
|------|------|
| Scrape simple page | 5-10 seconds |
| Scrape page + 20 images | 20-40 seconds |
| Search 100 pages | <1 second |
| Load dashboard | <1 second |

---

**Ready?** Let's go!

1. Open terminal
2. Run: `python app.py`
3. Create icons: `python extension/create_icons.py`
4. Load extension: `chrome://extensions/`
5. Navigate to any page
6. Click extension → Scrape!

Enjoy! 🎉
