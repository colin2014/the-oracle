# 🔌 Chrome Extension - Content Scraper

A Chrome extension that lets you scrape any web page you're viewing—even if it requires authentication—and send it to the Content Scraper dashboard.

## Why a Chrome Extension?

✅ **Access Authenticated Pages** - Scrapes pages you're logged into
✅ **JavaScript Content** - Captures dynamically loaded content
✅ **One-Click Scraping** - Click the extension icon to scrape
✅ **No Rate Limiting** - Works without hitting server rate limits
✅ **Local Processing** - Extracts content in your browser first

## Installation

### Step 1: Load the Extension

1. Open Chrome and go to `chrome://extensions/`
2. Enable **Developer Mode** (top right toggle)
3. Click **Load unpacked**
4. Navigate to the `extension/` folder in this project
5. Select it and click **Open**

You should now see the "Content Scraper" extension in your toolbar!

### Step 2: Configure Server URL

1. Click the extension icon in your toolbar
2. Enter your server URL (default: `http://localhost:5000`)
3. Click **Save Settings**

The extension will remember this for future use.

### Step 3: Start Scraping!

1. Navigate to any web page you want to scrape
2. Click the extension icon
3. Review the page stats (content size, images, sections)
4. Click **🔍 Scrape This Page**
5. Wait for confirmation
6. The dashboard opens automatically with your scraped content!

---

## What Gets Extracted?

The extension extracts:

✅ **Page Title** - The page's title attribute
✅ **Main Content** - Organized by headings
✅ **Images** - All visible images on the page
✅ **Navigation** - Links and menu structure
✅ **Special Sections** - Study Tips, Theory, Applied Work, etc.

---

## How It Works

### The Flow:

```
You click extension icon
    ↓
Extension analyzes current page
Shows: Text size, Image count, Section count
    ↓
You click "Scrape This Page"
    ↓
Content script extracts:
  - Headings & text
  - Images & alt text
  - Links & navigation
  - Special sections
    ↓
Sends to Flask backend (/api/scrape-dom)
    ↓
Backend downloads images
Saves as JSON in data/scraped_*/
    ↓
Dashboard opens automatically
You see organized content!
```

---

## Extension Files

```
extension/
├── manifest.json        # Extension configuration
├── popup.html          # Extension UI popup
├── popup.css           # Popup styling
├── popup.js            # Popup logic & content extraction
├── background.js       # Service worker
└── images/
    ├── icon16.png      # Extension icons (create these)
    ├── icon48.png
    └── icon128.png
```

---

## Features

### 📊 Page Analysis

Before scraping, see:
- **Content Size** - How much text will be extracted
- **Images Count** - How many images are on the page
- **Sections Count** - How many structured sections found

### ⚙️ Settings

- **Server URL** - Configure where to send scraped content
- **Save Settings** - Settings persist across sessions
- **Open Dashboard** - Quick link to the dashboard

### 🔍 Content Extraction

Intelligently identifies and extracts:
- Main content organized by headings
- Navigation structure with hierarchy levels
- Special sections (Study Tips, Theory of Knowledge, etc.)
- All images with alt text preserved

---

## Creating Extension Icons

The extension needs three icon files. You can:

**Option 1: Use simple generated icons**
```bash
# Windows: Create solid color PNGs named:
# extension/images/icon16.png  (16x16px - Blue background)
# extension/images/icon48.png  (48x48px - Blue background)
# extension/images/icon128.png (128x128px - Blue background)
```

**Option 2: Download ready-made icons**
- Make a simple 128x128 PNG with a blue background
- Duplicate and resize to 48x48 and 16x16

**Option 3: Quick online generator**
Visit: https://www.favicon-generator.org/
- Create a simple icon (or use the blue circle)
- Export as PNG in all three sizes

---

## Troubleshooting

### "Extension not loading"
1. Make sure Developer Mode is enabled (`chrome://extensions/`)
2. Check the manifest.json file is valid (no syntax errors)
3. Try removing and re-adding the extension

### "Content extraction fails"
1. Check browser console for errors (F12 → Console)
2. Make sure the page has fully loaded before clicking
3. Some pages with complex JavaScript may need special handling

### "Can't connect to server"
1. Make sure Flask app is running (`python app.py`)
2. Check server URL is correct in extension settings
3. Verify port 5000 is not blocked by firewall

### "Images not downloading"
1. Check the `data/scraped_*/images/` folder exists
2. Some images may be blocked by CORS - these are skipped
3. Make sure you have write permissions to the data folder

---

## Advanced Usage

### Modify Content Extraction

Edit `popup.js` → `extractSidebarSections()` to add more section keywords:

```javascript
const keywords = [
    'Study Tip', 'Theory of Knowledge', 'Applied Work',
    'Your Custom Section',  // ← Add here
];
```

### Change Default Server URL

Edit `popup.js`:
```javascript
const DEFAULT_SERVER = 'http://localhost:5000';
// Change to:
const DEFAULT_SERVER = 'http://your-server.com:5000';
```

---

## Security & Privacy

🔒 **What the extension does:**
- Runs only when you click it
- Processes content locally in your browser
- Sends data to your own server
- Never phones home or tracks you

🔐 **Your data:**
- Stays on your computer (in `data/` folder)
- Only sent to your configured server
- Never stored in the cloud
- You have full control

---

## Performance Tips

- **Faster scraping** - Simpler pages with less JavaScript
- **Slow pages** - Wait for full load before clicking
- **Large images** - May take longer to download
- **Many images** - Extension handles all, but takes time

---

## Limitations

❌ **Can't scrape:**
- Videos (only metadata)
- Interactive elements (forms, buttons)
- Real-time content (live chat)
- Content loaded after page render

✅ **Can scrape:**
- Any page you can view in browser
- Authenticated/protected pages
- PDF viewers
- Single-page apps
- JavaScript-heavy sites

---

## FAQ

**Q: Can I scrape any website?**
A: Any page you can view in your browser. Some sites may have terms of service restrictions—always check before scraping.

**Q: Will my password be sent to the server?**
A: No. The extension only extracts page content, not cookies or credentials.

**Q: Can I run the server remotely?**
A: Yes! Just enter the remote URL in extension settings (e.g., `http://192.168.1.100:5000`)

**Q: What about JavaScript-loaded content?**
A: The extension runs in the browser, so it captures JavaScript-rendered content. It only misses content that loads after you click the extension button.

**Q: Can I scrape multiple pages at once?**
A: Currently one at a time, but you can click the extension on multiple tabs and all get sent to your dashboard.

---

## Updates & Future Features

Planned enhancements:
- [ ] Batch scraping (multiple tabs at once)
- [ ] Custom CSS selectors for extraction
- [ ] Automatic periodic scraping
- [ ] Export to PDF/Word
- [ ] Share scraped content
- [ ] Browser sidebar panel

---

## Support

Issues? Check:
1. **Browser Console** - F12 → Console tab for error messages
2. **Flask Console** - Check server logs for API errors
3. **Manifest Validation** - JSON syntax must be valid
4. **Permissions** - File write permissions in data folder

---

Made with ❤️ for content creators and researchers
