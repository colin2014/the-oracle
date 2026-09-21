# 📚 Content Scraper & Organizer

A web-based tool to scrape, organize, and search educational content with embedded images. Perfect for downloading course materials, study guides, and organizing them by topic.

## Features

✨ **Web-based Dashboard**
- Clean, responsive interface
- Real-time scraping
- Instant preview of scraped content

📚 **Intelligent Content Organization**
- Extracts hierarchical navigation structure
- Identifies and separates special sections:
  - Study Tips
  - Theory of Knowledge
  - Applied Work
  - Practice Questions
  - Vocabulary
  - And more...

🖼️ **Image Management**
- Automatically downloads all images from the page
- Embeds images directly in the dashboard
- Organized image gallery view
- Preserves alt text and captions

🔍 **Full-Text Search**
- Search across all scraped content
- Finds matches in titles, headings, body text, and sidebar sections
- Quick navigation to results

💾 **Local File Storage**
- Stores all content in organized folder structure
- One folder per URL
- Images stored in subfolders
- Content saved as JSON for easy parsing

## Installation

Requires Python 3.12+ (`test_routes.py` uses nested triple-quoted f-strings, which are a syntax error on 3.11).

### 1. Clone and install dependencies

```bash
git clone https://github.com/colin2014/the-oracle.git
cd the-oracle
python -m venv .venv
# Windows:  .venv/Scripts/activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
```

On Windows, `weasyprint` (PDF export) also needs the GTK runtime. If
`import weasyprint` fails, install GTK or skip it — the rest of the app runs
without it.

### 2. Configure the environment

```bash
cp .env.example .env
```

Then edit `.env`. `SECRET_KEY` is **required** — the app refuses to start
without it. Generate one with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Use a *different* `SECRET_KEY` on each machine and never commit `.env`.

### 3. Create the database

The database lives in `data/` and is not in version control.

```bash
mkdir -p data
flask --app app db upgrade
```

This builds the full schema from the migrations. To carry over existing
content instead, copy `data/` across from the other machine (see
"Moving between machines" below).

### 4. Create an admin account

```bash
# set TEST_ADMIN_PASSWORD and TEST_USER_PASSWORD in .env first
python create_test_users.py
```

### 5. Run the application

```bash
python app.py
```

The app will be available at `http://localhost:5000`

By default this runs under waitress on `127.0.0.1` only, with Secure cookies, so
it is meant to sit behind an HTTPS tunnel or proxy (Tailscale Serve/Funnel or
Cloudflare Tunnel). For local development over plain http, set `FLASK_DEBUG=true`
in `.env` to get the Flask debug server and non-Secure cookies.

New accounts need the `SIGNUP_CODE` from `.env` and only ever store a username;
no name or email is collected. Login and signup are rate limited per client IP.

## Exit Tickets

Web versions of the printed exit tickets, one per syllabus subtopic: multiple choice, true/false,
fill the gap, match the pairs (click or drag), put in order, short answer and explain. Teachers edit
questions in the browser (**Exit Tickets** in the sidebar), publish a ticket, and assign it to a class
or a student. Multiple choice, true/false, fill, match and order are marked instantly; written answers
are marked by Claude Haiku in the background, with feedback the teacher can override.

- Needs the tables from migration `s4t5u6v7w8x9`: `flask --app app db upgrade`
- Import the printed tickets (PowerPoint) as **drafts**: `python exit_ticket_import.py "<Subtopics folder>"`
  is a dry run that reports what it read; add `--apply` to create them. Running it again skips tickets
  that already exist. It needs `python-pptx` (in `requirements.txt`).
- Correct answers are never sent to the student's browser before they submit, and match/order questions
  are shuffled per attempt.

## Moving Between Machines

The code is in git; your **content and database are not**. To move them:

- `data/app.db` — the database (~8 MB). Copy this to keep accounts and
  progress. Omit it to start fresh with `flask --app app db upgrade`.
- `data/` — scraped books and resources (~780 MB of live content).
- `teacher_names/` — real student names, stored only on the teacher's
  machine by design. Copy it **only** over a private channel, never git.

Files matching `*.bak`, `*.preconsolidate`, `*.preimages` and `*.vocabbak`
inside `data/` are regenerable backups (~2.7 GB) and do not need copying.

Do not copy `.env` between machines — create a fresh one with its own
`SECRET_KEY`.

## Usage

### Scraping Content

1. **Enter URL**: Paste a URL in the "Scrape Content" section on the left
2. **Click Scrape**: The tool will:
   - Download all content from the page
   - Extract images and embed them
   - Organize content by sections and topics
   - Save everything locally
3. **View Results**: Your scraped content appears in the content list

### Viewing Scraped Content

1. **Browse**: Select any item from "All Scraped Content" on the left
2. **Sections Display**: Content is organized into:
   - Navigation Structure (hierarchy of topics)
   - Main Content sections
   - Sidebar sections (Study Tips, Theory, etc.)
   - Embedded Images gallery

### Searching

1. **Enter Query**: Type in the search box
2. **Find Matches**: Results show which fields contain your search term
3. **Navigate**: Click a result to view that content

## File Structure

```
airplay/
├── app.py                 # Flask backend
├── scraper.py             # Web scraping logic
├── requirements.txt       # Python dependencies
├── data/                  # Scraped content storage
│   ├── scraped_abc123/
│   │   ├── content.json   # Full content data
│   │   └── images/        # Downloaded images
│   └── scraped_def456/
│       ├── content.json
│       └── images/
├── templates/
│   └── index.html         # Main dashboard
└── static/
    ├── css/
    │   └── style.css      # Styling
    └── js/
        └── app.js         # Frontend logic
```

## Usage Examples

### Example 1: Scrape a Course Page
1. Visit https://app.growhall.com/books/93/5438 in a browser
2. Copy the URL
3. Paste in the app and click "Scrape URL"
4. Content, images, and organization will be saved locally

### Example 2: Search Across Content
1. Type "CPU" in the search box
2. View results from all scraped pages
3. Click a result to view full content

## Data Format

Each scraped page is stored as `content.json` with this structure:

```json
{
  "url": "https://...",
  "scraped_at": "2024-01-01T12:00:00",
  "title": "Page Title",
  "main_heading": "Main Heading",
  "navigation": [
    {"text": "Topic 1", "href": "/path", "level": 1},
    {"text": "Subtopic 1.1", "href": "/path", "level": 2}
  ],
  "main_content": {
    "Section Name": "Content text..."
  },
  "sidebar_sections": {
    "Study Tip": "Tip text...",
    "Theory of Knowledge": "Theory text...",
    "Applied Work": "Work text..."
  },
  "images": [
    {
      "original_src": "https://...",
      "local_path": "images/image_0.jpg",
      "alt_text": "Description"
    }
  ]
}
```

## API Endpoints

### POST `/api/scrape`
Scrape a URL
```json
{
  "url": "https://example.com/page"
}
```

### GET `/api/content`
Get list of all scraped content

### GET `/api/content/<folder_name>`
Get detailed content from a specific folder

### POST `/api/search`
Search across all scraped content
```json
{
  "query": "search term"
}
```

### GET `/data/<path>`
Serve static files (images, etc.)

## Supported Content Types

Works best with:
- Educational websites
- Course materials
- Study guides
- Documentation with hierarchical structure
- Pages with embedded images

## Troubleshooting

**Images not showing?**
- Check that images downloaded to the `data/scraped_*/images/` folder
- Verify file permissions

**Content looks incomplete?**
- Some dynamic content loaded via JavaScript won't be captured
- Try a simpler URL first to test

**Search not finding results?**
- Search is case-insensitive but requires exact phrase matching
- Try shorter search terms

## Performance Tips

- Smaller pages scrape faster
- Images take most of the time - pages with many images will take longer
- Search gets faster as you filter to specific content items

## Privacy & Legal

- Respect website terms of service and `robots.txt`
- Only scrape content you have permission to download
- Be mindful of copyright when storing and sharing scraped content

