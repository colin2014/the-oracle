"""Rename Book_93 page folders to their syllabus code (e.g. 5438 -> A1.1.1).

The code is taken from each page's title in book.json ("A1.1.1 Describe the
functions..." -> "A1.1.1"). Pages without a code (Introduction, Internal
Assessment) are left untouched. Page ids in book.json, the database and
syllabus.json are NOT changed — the app resolves id -> folder via book.json.

Reversible: writes folder_rename_map.json and book.json.bak next to book.json.

Usage:
    python scripts/rename_book93_folders.py           # rename
    python scripts/rename_book93_folders.py --revert  # undo using the map
"""
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

BOOK_DIR = Path(__file__).resolve().parent.parent / 'data' / 'Book_93'
BOOK_JSON = BOOK_DIR / 'book.json'
MAP_FILE = BOOK_DIR / 'folder_rename_map.json'
CODE_RE = re.compile(r'^([A-Z]\.?\d+(?:\.\d+)+)\s')


def load_book():
    with open(BOOK_JSON, encoding='utf-8') as f:
        return json.load(f)


def save_book(book):
    with open(BOOK_JSON, 'w', encoding='utf-8') as f:
        json.dump(book, f, indent=2, ensure_ascii=False)


def rename():
    if MAP_FILE.exists():
        sys.exit(f"{MAP_FILE} already exists — folders appear to be renamed. "
                 "Run with --revert first if you want to redo.")
    book = load_book()
    shutil.copy2(BOOK_JSON, BOOK_JSON.with_suffix('.json.bak'))

    mapping = {}
    for page in book['pages']:
        m = CODE_RE.match(page.get('title', ''))
        old = page.get('folder')
        if not m or not old:
            continue
        new = m.group(1)
        if new == old:
            continue
        src, dst = BOOK_DIR / old, BOOK_DIR / new
        if not src.is_dir():
            print(f"skip {old}: folder missing")
            continue
        if dst.exists():
            print(f"skip {old}: target {new} already exists")
            continue
        src.rename(dst)
        page['folder'] = new
        mapping[old] = new
        print(f"{old} -> {new}")

    save_book(book)
    with open(MAP_FILE, 'w', encoding='utf-8') as f:
        json.dump({'renamed_at': datetime.now().isoformat(), 'map': mapping},
                  f, indent=2, ensure_ascii=False)
    print(f"\nRenamed {len(mapping)} folders. Map saved to {MAP_FILE}")


def revert():
    if not MAP_FILE.exists():
        sys.exit(f"{MAP_FILE} not found — nothing to revert.")
    with open(MAP_FILE, encoding='utf-8') as f:
        mapping = json.load(f)['map']
    book = load_book()
    by_folder = {p.get('folder'): p for p in book['pages']}

    reverted = 0
    for old, new in mapping.items():
        src, dst = BOOK_DIR / new, BOOK_DIR / old
        if not src.is_dir():
            print(f"skip {new}: folder missing")
            continue
        if dst.exists():
            print(f"skip {new}: target {old} already exists")
            continue
        src.rename(dst)
        if new in by_folder:
            by_folder[new]['folder'] = old
        reverted += 1
        print(f"{new} -> {old}")

    save_book(book)
    MAP_FILE.unlink()
    print(f"\nReverted {reverted} folders. Map file removed.")


if __name__ == '__main__':
    revert() if '--revert' in sys.argv else rename()
