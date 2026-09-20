"""
Drop heading blocks that just repeat the page title.

Every page carries its own title twice: once in `title` (which the reading
page renders as the sticky page header) and again as a `heading` block at the
top of the body. The second one is pure duplication on screen.

Only headings whose text matches the page title are removed. Genuine
subsection headings are left alone.

Usage:
    python scripts/remove_duplicate_title_headings.py                 # dry run
    python scripts/remove_duplicate_title_headings.py --apply
    python scripts/remove_duplicate_title_headings.py --page A1.3.1 -v
"""

import argparse
import json
import re
import shutil
import sys
from pathlib import Path


def plain(html):
    text = re.sub(r'<[^>]+>', ' ', html or '').replace('&nbsp;', ' ')
    return re.sub(r'\s+', ' ', text).strip()


def key(html):
    return re.sub(r'[^a-z0-9]', '', plain(html).lower())


def is_title_echo(heading_html, title_key):
    """
    True when this heading says the same thing as the page title.

    Substring either way catches the common variants — a trailing &nbsp;, the
    topic number present in one and not the other — while the length floor
    stops a short heading like "Overview" matching by accident.
    """
    head = key(heading_html)
    if not head or not title_key:
        return False
    if head == title_key:
        return True
    return len(head) > 15 and (head in title_key or title_key in head)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--book', default='Book_93')
    ap.add_argument('--page')
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('-v', '--verbose', action='store_true')
    args = ap.parse_args()

    root = Path('data') / args.book
    if not root.is_dir():
        sys.exit(f'No such book: {root}')

    folders = [root / args.page] if args.page else sorted(
        p for p in root.iterdir() if (p / 'content.json').is_file())

    pages = removed = kept = 0

    for folder in folders:
        path = folder / 'content.json'
        if not path.is_file():
            continue
        data = json.loads(path.read_text(encoding='utf-8'))
        blocks = data.get('blocks') or []
        title_key = key(data.get('title') or data.get('main_heading') or '')

        out, dropped = [], []
        for block in blocks:
            if block.get('type') == 'heading' and is_title_echo(block.get('text'), title_key):
                dropped.append(plain(block.get('text'))[:60])
            else:
                out.append(block)
                if block.get('type') == 'heading':
                    kept += 1

        if not dropped:
            continue

        pages += 1
        removed += len(dropped)
        print(f'{folder.name:12} removed {len(dropped)} title heading(s)')
        if args.verbose:
            for d in dropped:
                print(f'               - {d}')

        if args.apply:
            backup = path.with_suffix('.json.pretitle')
            if not backup.exists():
                shutil.copy2(path, backup)
            data['blocks'] = out
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False),
                            encoding='utf-8')

    print()
    print(f'pages changed              : {pages}')
    print(f'title headings removed     : {removed}')
    print(f'other headings left intact : {kept}')
    print()
    print('APPLIED (backups: content.json.pretitle)' if args.apply
          else 'DRY RUN — nothing written. Re-run with --apply to save.')


if __name__ == '__main__':
    main()
