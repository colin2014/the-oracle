"""
Pull base64-embedded images out of a book's content.json files.

The scraper inlined every image twice: once as a data: URI on the image block's
`src`, and again on the matching `images[].local_path` entry. A1.1.1 alone is
8.8MB, split evenly between the two, and the whole file is sent to the browser
on every page view.

This writes each image once to static/book_images/<book>/, deduplicated by
content hash, and rewrites both references to point at the file. Pages become
small, and the images become browser-cacheable and lazy-loadable.

`images[]` metadata (alt_text, original_src) is kept — only the payload moves.

Usage:
    python scripts/extract_embedded_images.py                 # dry run, Book_93
    python scripts/extract_embedded_images.py --apply
    python scripts/extract_embedded_images.py --book Book_93 --page A1.1.7
"""

import argparse
import base64
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

DATA_URI = re.compile(r'^data:(image/([a-zA-Z0-9.+-]+))?;base64,(.*)$', re.S)

EXT = {
    'png': 'png', 'jpeg': 'jpg', 'jpg': 'jpg', 'gif': 'gif',
    'webp': 'webp', 'svg+xml': 'svg', 'bmp': 'bmp', 'x-icon': 'ico',
}


def decode(src):
    """(bytes, extension) for a data: URI, or None if it isn't one."""
    if not isinstance(src, str) or not src.startswith('data:'):
        return None
    m = DATA_URI.match(src)
    if not m:
        return None
    try:
        raw = base64.b64decode(m.group(3), validate=False)
    except Exception:
        return None
    if not raw:
        return None
    return raw, EXT.get((m.group(2) or 'png').lower(), 'png')


class Store:
    """Writes each distinct image once, named by content hash."""

    def __init__(self, out_dir, apply_changes):
        self.out_dir = out_dir
        self.apply = apply_changes
        self.seen = {}      # digest -> url
        self.bytes_written = 0

    def put(self, raw, ext):
        digest = hashlib.sha1(raw).hexdigest()[:16]
        if digest in self.seen:
            return self.seen[digest], False
        name = f'{digest}.{ext}'
        if self.apply:
            self.out_dir.mkdir(parents=True, exist_ok=True)
            target = self.out_dir / name
            if not target.exists():
                target.write_bytes(raw)
        self.bytes_written += len(raw)
        url = f'/static/book_images/{self.out_dir.name}/{name}'
        self.seen[digest] = url
        return url, True


IMG_TAG = re.compile(r'<img\b[^>]*>', re.I)
SRC_ATTR = re.compile(r'src\s*=\s*(["\'])(.*?)\1', re.I | re.S)
EMPTY_P = re.compile(r'<p[^>]*>\s*(?:&nbsp;|\s)*</p>', re.I)


def digest_of(raw):
    return hashlib.sha1(raw).hexdigest()[:16]


def figure_hashes(data):
    """Content hashes of the page's real image blocks, however they're stored."""
    out = set()
    for block in data.get('blocks') or []:
        if block.get('type') != 'image':
            continue
        src = block.get('src') or ''
        if src.startswith('/static/book_images/'):
            out.add(Path(src).name.split('.')[0])
        else:
            decoded = decode(src)
            if decoded:
                out.add(digest_of(decoded[0]))
    return out


def rewrite_inline(data, store):
    """
    Handle <img> tags sitting inside block HTML.

    These have no block of their own, so the editor offers no way to remove or
    replace them. When one is byte-identical to a real image block on the same
    page it is redundant chrome and gets dropped; otherwise it is kept but its
    payload moves to a file like every other image.
    """
    figures = figure_hashes(data)
    dropped = moved = 0

    for block in data.get('blocks') or []:
        text = block.get('text')
        if not isinstance(text, str) or '<img' not in text.lower():
            continue

        def replace(match):
            nonlocal dropped, moved
            tag = match.group(0)
            src_match = SRC_ATTR.search(tag)
            if not src_match:
                return tag
            decoded = decode(src_match.group(2))
            if not decoded:
                return tag
            raw, ext = decoded
            if digest_of(raw) in figures:
                dropped += 1
                return ''
            url, _ = store.put(raw, ext)
            moved += 1
            return tag[:src_match.start(2)] + url + tag[src_match.end(2):]

        new_text = IMG_TAG.sub(replace, text)
        if new_text != text:
            block['text'] = EMPTY_P.sub('', new_text)

    return dropped, moved


def process(data, store):
    """Rewrite a page in place. Returns (moved, freed_bytes)."""
    moved = 0
    freed = 0

    for block in data.get('blocks') or []:
        if block.get('type') != 'image':
            continue
        decoded = decode(block.get('src'))
        if not decoded:
            continue
        raw, ext = decoded
        freed += len(block['src'])
        block['src'], _ = store.put(raw, ext)
        moved += 1

    for entry in data.get('images') or []:
        decoded = decode(entry.get('local_path'))
        if not decoded:
            continue
        raw, ext = decoded
        freed += len(entry['local_path'])
        entry['local_path'], _ = store.put(raw, ext)
        moved += 1

    dropped, inline = rewrite_inline(data, store)
    process.last_dropped = dropped
    moved += inline + dropped

    return moved, freed


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--book', default='Book_93')
    ap.add_argument('--page')
    ap.add_argument('--apply', action='store_true',
                    help='write the changes (default is a dry run)')
    args = ap.parse_args()

    root = Path('data') / args.book
    if not root.is_dir():
        sys.exit(f'No such book: {root}')

    store = Store(Path('static') / 'book_images' / args.book, args.apply)
    folders = [root / args.page] if args.page else sorted(
        p for p in root.iterdir() if (p / 'content.json').is_file())

    total_before = total_after = total_moved = total_dropped = 0
    pages = 0

    for folder in folders:
        path = folder / 'content.json'
        if not path.is_file():
            continue
        before = path.stat().st_size
        data = json.loads(path.read_text(encoding='utf-8'))
        moved, _ = process(data, store)
        if not moved:
            total_before += before
            total_after += before
            continue

        pages += 1
        total_moved += moved
        blob = json.dumps(data, indent=2, ensure_ascii=False)
        after = len(blob.encode('utf-8'))
        total_before += before
        total_after += after
        dropped = getattr(process, 'last_dropped', 0)
        total_dropped += dropped
        note = f'   (dropped {dropped} duplicate inline <img>)' if dropped else ''
        print(f'{folder.name:12} {moved:2} image(s)   '
              f'{before / 1e6:6.2f}MB -> {after / 1e6:5.2f}MB{note}')

        if args.apply:
            backup = path.with_suffix('.json.preimages')
            if not backup.exists():
                shutil.copy2(path, backup)
            path.write_text(blob, encoding='utf-8')

    print()
    print(f'pages rewritten     : {pages}')
    print(f'image refs moved    : {total_moved}')
    print(f'duplicate inline    : {total_dropped} dropped')
    print(f'distinct files      : {len(store.seen)}')
    print(f'image bytes on disk : {store.bytes_written / 1e6:.1f}MB')
    print(f'content.json total  : {total_before / 1e6:.1f}MB -> {total_after / 1e6:.1f}MB '
          f'({100 * (1 - total_after / total_before):.0f}% smaller)')
    print()
    print(f'APPLIED (backups: content.json.preimages, files in {store.out_dir})'
          if args.apply else 'DRY RUN — nothing written. Re-run with --apply to save.')


if __name__ == '__main__':
    main()
