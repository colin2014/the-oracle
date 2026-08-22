"""
Import complete chapter structure from a saved GrowHall HTML file.
Parses the sidebar navigation to discover ALL pages and their hierarchy,
then updates book.json and creates chapters.json.
"""
import json
import re
from pathlib import Path
from bs4 import BeautifulSoup


def get_topic_level(title):
    """Determine the nesting level from a topic title prefix."""
    title = title.strip()
    if title.startswith('Theme '):
        return 0
    if title in ('Introduction', 'Internal Assessment'):
        return 0
    # Match A1, A1.1, A1.1.1, A.1.2.5, B2.3.4 etc.
    m = re.match(r'^[A-Z]\.?\s*(\d+(?:\.\d+)*)', title)
    if m:
        nums = m.group(1)
        return len(nums.split('.'))
    return 0


def import_chapters_from_html(html_path, book_dir):
    """Parse saved GrowHall HTML and extract complete chapter structure."""
    with open(html_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')

    # Find sidebar menu (GrowHall uses div.menu-wp)
    menu = soup.find('div', class_=lambda c: c and 'menu-wp' in c)
    if not menu:
        print("ERROR: Could not find sidebar menu (div.menu-wp) in HTML")
        return 0

    nav_entries = []
    all_pages = {}  # page_id -> {id, title, url}

    for a in menu.find_all('a', href=True):
        href = a['href']
        text = a.get_text().strip()
        if not text:
            continue
        m = re.match(r'https?://app\.growhall\.com/books/(\d+)/(\d+)', href)
        if not m:
            continue
        book_id, page_id = m.group(1), m.group(2)
        level = get_topic_level(text)

        nav_entries.append({
            'title': text,
            'page_id': page_id,
            'url': href,
            'level': level
        })

        # Keep the most specific (deepest/last) title for each page_id
        all_pages[page_id] = {
            'id': page_id,
            'title': text,
            'url': href
        }

    # Save chapters.json with full navigation hierarchy
    chapters_file = book_dir / 'chapters.json'
    with open(chapters_file, 'w', encoding='utf-8') as f:
        json.dump({'navigation': nav_entries}, f, indent=2, ensure_ascii=False)
    print(f"  Saved {len(nav_entries)} navigation entries to chapters.json")

    # Update book.json with all unique pages
    book_json = book_dir / 'book.json'
    with open(book_json, 'r', encoding='utf-8') as f:
        book = json.load(f)

    existing_ids = {p['id'] for p in book['pages']}
    added = 0
    for pid, pdata in all_pages.items():
        if pid not in existing_ids:
            book['pages'].append(pdata)
            added += 1

    # Sort pages by numeric ID
    book['pages'].sort(key=lambda p: int(p['id']))

    with open(book_json, 'w', encoding='utf-8') as f:
        json.dump(book, f, indent=2, ensure_ascii=False)

    print(f"  book.json: {len(book['pages'])} pages total ({added} new pages added)")
    return added


if __name__ == '__main__':
    html_path = Path('Books _ GrowHall.html')
    book_dir = Path('data/Book_93')

    if not html_path.exists():
        print(f"ERROR: {html_path} not found")
        exit(1)
    if not book_dir.exists():
        print(f"ERROR: {book_dir} not found")
        exit(1)

    print(f"Importing chapters from {html_path}...")
    import_chapters_from_html(html_path, book_dir)
    print("Done!")
