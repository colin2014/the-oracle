"""
Consolidate a book's page blocks into one editable main text box.

Scraped pages arrived fragmented: the body of a page is spread across many
separate `text` blocks, and several side sections (International-Mindedness,
ATL, Study Tip...) were captured TWICE — once as a sidebox and again as a
plain text block sitting in the main column.

This does three things per page:

  1. DROP   main-column text blocks that duplicate an existing sidebox or
            sidebar_sections entry.
  2. MOVE   main-column text blocks that are clearly side content but have no
            matching sidebox — converted into a real sidebox so they render
            in the rail instead of the body.
  3. MERGE  every remaining main-column text block into a single text block.
            `heading` blocks that sat between them are inlined as <h3> so the
            document keeps its structure inside the one editable box.

Headings before the first body paragraph (the page title) and anything after
the last one are left alone. Images are never touched — a survey of Book_93
confirmed no image ever sits between two main text blocks.

Usage:
    python scripts/consolidate_page_blocks.py                 # dry run, Book_93
    python scripts/consolidate_page_blocks.py --apply
    python scripts/consolidate_page_blocks.py --book Book_93 --page A1.1.7 -v
"""

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

# Side sections that were duplicated into the body. Maps the opening words of
# such a block to the sidebox style/title used elsewhere in this book.
SIDE_SECTIONS = [
    ('international-mindedness', 'study',   'International-Mindedness'),
    ('approaches to learning',   'study',   'Approaches to Learning'),
    ('atl skills',               'atl',     'ATL Skills'),
    ('theory of knowledge',      'theory',  'Theory of Knowledge'),
    ('applied work',             'applied', 'Applied Work'),
    ('study tip',                'study',   'Study Tip'),
    ('fun fact',                 'funfact', 'Fun fact'),
    ('key concept',              'study',   'Key Concept'),
]

# Only these get folded into the merged body. Anything else inside the body
# range is preserved as its own block, in order.
INLINE_TYPES = {'text', 'heading'}


def plain(html):
    """Visible text of an HTML fragment."""
    text = re.sub(r'<[^>]+>', ' ', html or '')
    text = text.replace('&nbsp;', ' ')
    return re.sub(r'\s+', ' ', text).strip()


def norm(html):
    """Comparison key: letters and digits only."""
    return re.sub(r'[^a-z0-9]', '', plain(html).lower())


def is_duplicate(key, known):
    """
    True when this block repeats something already held as side content.

    Exact match, or one contains the other AND they are close in length — the
    length guard stops a long body paragraph being dropped merely because it
    happens to contain a short sidebox phrase.
    """
    if not key or len(key) < 40:
        return False
    for other in known:
        if not other:
            continue
        if key == other:
            return True
        if len(key) > 60 and (key in other or other in key):
            shorter, longer = sorted((len(key), len(other)))
            if shorter / longer > 0.8:
                return True
    return False


def side_section_for(html):
    """The (style, title) this block belongs to if it is really side content."""
    text = plain(html).lower()
    for prefix, style, title in SIDE_SECTIONS:
        if text.startswith(prefix):
            return style, title
    return None


def heading_html(block):
    level = block.get('level') or 3
    try:
        level = max(3, min(6, int(level)))
    except (TypeError, ValueError):
        level = 3
    text = (block.get('text') or '').strip()
    if not text:
        return ''
    return f'<h{level} style="margin:1.75rem 0 0.75rem;">{text}</h{level}>'


def plan_page(data):
    """
    Work out what to do with one page. Returns (new_blocks, report) or
    (None, report) when nothing needs changing.
    """
    blocks = data.get('blocks') or []
    report = {'dropped': [], 'moved': [], 'merged': 0, 'inlined_headings': 0}
    if not blocks:
        return None, report

    known = {norm(b.get('text', '')) for b in blocks if b.get('type') == 'sidebox'}
    known |= {norm(v) for v in (data.get('sidebar_sections') or {}).values()}

    drop_idx, move_idx, body_idx = set(), {}, []
    for i, block in enumerate(blocks):
        if block.get('type') != 'text':
            continue
        key = norm(block.get('text', ''))
        if is_duplicate(key, known):
            drop_idx.add(i)
            report['dropped'].append(plain(block.get('text', ''))[:60])
            continue
        section = side_section_for(block.get('text', ''))
        if section:
            move_idx[i] = section
            report['moved'].append(f'{section[1]}: ' + plain(block.get('text', ''))[:50])
            continue
        body_idx.append(i)

    if not body_idx:
        # Nothing to merge, but there may still be duplicates to clear out.
        if not drop_idx and not move_idx:
            return None, report
        first = last = None
    else:
        first, last = body_idx[0], body_idx[-1]

    merged_html, tail, new_sideboxes = [], [], []
    out = []

    for i, block in enumerate(blocks):
        if i in drop_idx:
            continue
        if i in move_idx:
            style, title = move_idx[i]
            new_sideboxes.append({
                'type': 'sidebox', 'style': style, 'title': title,
                'text': block.get('text', ''),
            })
            continue

        inside_body = first is not None and first <= i <= last
        if not inside_body:
            out.append(block)
            continue

        btype = block.get('type')
        if btype == 'text':
            html = (block.get('text') or '').strip()
            if html:
                merged_html.append(html)
        elif btype == 'heading':
            html = heading_html(block)
            if html:
                merged_html.append(html)
                report['inlined_headings'] += 1
        else:
            # rare: a question/sidebox/video sat inside the body range
            tail.append(block)

        if i == last:
            if merged_html:
                out.append({'type': 'text', 'text': ''.join(merged_html)})
                report['merged'] = len([j for j in body_idx])
            out.extend(tail)

    out.extend(new_sideboxes)

    if out == blocks:
        return None, report
    return out, report


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--book', default='Book_93', help='book folder under data/')
    ap.add_argument('--page', help='only this page folder (e.g. A1.1.7)')
    ap.add_argument('--apply', action='store_true',
                    help='write the changes (default is a dry run)')
    ap.add_argument('-v', '--verbose', action='store_true')
    args = ap.parse_args()

    root = Path('data') / args.book
    if not root.is_dir():
        sys.exit(f'No such book: {root}')

    folders = [root / args.page] if args.page else sorted(
        p for p in root.iterdir() if (p / 'content.json').is_file())

    totals = {'pages': 0, 'changed': 0, 'dropped': 0, 'moved': 0,
              'text_before': 0, 'text_after': 0, 'inlined': 0}

    for folder in folders:
        path = folder / 'content.json'
        if not path.is_file():
            continue
        data = json.loads(path.read_text(encoding='utf-8'))
        before = sum(1 for b in (data.get('blocks') or []) if b.get('type') == 'text')
        totals['pages'] += 1
        totals['text_before'] += before

        new_blocks, report = plan_page(data)
        if new_blocks is None:
            totals['text_after'] += before
            continue

        after = sum(1 for b in new_blocks if b.get('type') == 'text')
        totals['changed'] += 1
        totals['text_after'] += after
        totals['dropped'] += len(report['dropped'])
        totals['moved'] += len(report['moved'])
        totals['inlined'] += report['inlined_headings']

        print(f'{folder.name:12} text {before:2} -> {after:2}'
              f'   dropped {len(report["dropped"])}'
              f'   moved-to-side {len(report["moved"])}'
              f'   headings inlined {report["inlined_headings"]}')
        if args.verbose:
            for d in report['dropped']:
                print(f'               - drop  {d}…')
            for m in report['moved']:
                print(f'               → side  {m}…')

        if args.apply:
            backup = path.with_suffix('.json.preconsolidate')
            if not backup.exists():
                shutil.copy2(path, backup)
            data['blocks'] = new_blocks
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False),
                            encoding='utf-8')

    print()
    print(f'pages scanned            : {totals["pages"]}')
    print(f'pages changed            : {totals["changed"]}')
    print(f'main text blocks         : {totals["text_before"]} -> {totals["text_after"]}')
    print(f'duplicates dropped       : {totals["dropped"]}')
    print(f'moved into the side rail : {totals["moved"]}')
    print(f'headings inlined         : {totals["inlined"]}')
    print()
    print('APPLIED (backups: content.json.preconsolidate)' if args.apply
          else 'DRY RUN — nothing written. Re-run with --apply to save.')


if __name__ == '__main__':
    main()
