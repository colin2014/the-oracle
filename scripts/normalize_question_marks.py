"""Normalise every question block so the marks/level sit on their own line
directly under the question, e.g.

    Explain how images can be represented as binary data.
    [3 marks • SL]

Question blocks currently store the marks token in three inconsistent ways:

  * prefix, with level ...... "[3 marks • HL]  Explain ..."
  * prefix, number only ..... "[2] What is ..."          (level unknown)
  * HTML suffix (desired) .... "<p>...</p><p><span>[3 marks • SL]</span></p>"
  * inline suffix ........... "... text<br><br>[3 marks • SL]&nbsp;"

This script rewrites them all to one canonical shape: the question body,
followed by a separate line holding "[N marks • LEVEL]".

Level resolution, in order:
  1. a SL/HL found inside the marks token itself;
  2. else HL if the page is flagged "(HL only)";
  3. else the --default-level value (SL by default).

Only the question block's `text` is touched; answers/markschemes are left
alone. Runs are idempotent. A .bak copy of each changed file is written unless
--no-backup is given.

Usage:
    python scripts/normalize_question_marks.py --dry-run   # preview only
    python scripts/normalize_question_marks.py             # apply (+ .bak)
    python scripts/normalize_question_marks.py --default-level HL
    python scripts/normalize_question_marks.py --no-backup
"""
import argparse
import json
import re
import shutil
import sys
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / 'data'

# A full marks token anywhere in the text: "[3 marks • HL]", "[2 marks]", ...
FULL_TOKEN = re.compile(r'\[\s*(\d+)\s*marks?\b[^\]]*\]', re.IGNORECASE)
# A bare "[2] " token at the very start (older python-book style, no level).
NUM_ONLY = re.compile(r'^\s*(?:<p[^>]*>\s*)?\[\s*(\d+)\s*\]\s*')
LEVEL_IN_TOKEN = re.compile(r'\b(SL|HL)\b', re.IGNORECASE)
HTML_TAG = re.compile(r'<[a-z][^>]*>', re.IGNORECASE)
EMPTY_P = re.compile(r'<p[^>]*>\s*(?:&nbsp;|<br\s*/?>|\s)*</p>', re.IGNORECASE)
EMPTY_SPAN = re.compile(r'<span[^>]*>\s*(?:&nbsp;|<br\s*/?>|\s)*</span>', re.IGNORECASE)
TRAILING_JUNK = re.compile(r'(?:\s|&nbsp;|<br\s*/?>)+$', re.IGNORECASE)
LEADING_JUNK = re.compile(r'^(?:\s|&nbsp;|<br\s*/?>)+', re.IGNORECASE)


def infer_level_from_page(content):
    """HL if the page title/heading marks it HL-only, else None."""
    haystack = ' '.join(str(content.get(k, '')) for k in ('main_heading', 'title'))
    if re.search(r'HL\s*only', haystack, re.IGNORECASE):
        return 'HL'
    return None


def clean_body(body):
    """Strip the leftovers after the marks token is removed."""
    body = EMPTY_SPAN.sub('', body)
    body = EMPTY_P.sub('', body)
    body = TRAILING_JUNK.sub('', body)
    body = LEADING_JUNK.sub('', body)
    return body.strip()


def marks_line(n, level):
    unit = 'mark' if n == 1 else 'marks'
    return (f'<p style="margin: 0.75rem 0 0; color: #6b7280; '
            f'font-weight: 600; font-size: 0.9rem;">[{n} {unit} • {level}]</p>')


def wrap_body(body):
    """Ensure the question body is block-level HTML."""
    if not HTML_TAG.search(body):
        body = body.strip().replace('\n', '<br>')
        return f'<p style="margin: 0 0 0.5rem;">{body}</p>'
    return body


def normalise_text(text, content, default_level):
    """Return (new_text, level_source) or (None, reason) if no marks found."""
    marks = None
    level = None
    body = None

    m = FULL_TOKEN.search(text)
    if m:
        marks = int(m.group(1))
        lvl = LEVEL_IN_TOKEN.search(m.group(0))
        level = lvl.group(1).upper() if lvl else None
        body = text[:m.start()] + text[m.end():]
    else:
        m = NUM_ONLY.search(text)
        if m:
            marks = int(m.group(1))
            # NUM_ONLY may have swallowed an opening <p>; put it back.
            consumed = m.group(0)
            body = text[m.end():]
            if consumed.lstrip().lower().startswith('<p'):
                body = consumed[:consumed.lower().index('[')] + body
        else:
            return None, 'no-marks-token'

    level_source = 'token'
    if not level:
        level = infer_level_from_page(content)
        level_source = 'page'
    if not level:
        level = default_level
        level_source = 'default'

    body = clean_body(body)
    new_text = wrap_body(body) + marks_line(marks, level)
    return new_text, level_source


def process_file(path, default_level, apply, backup, report):
    try:
        content = json.loads(path.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError) as e:
        report['errors'].append(f'{path}: {e}')
        return

    blocks = content.get('blocks')
    if not isinstance(blocks, list):
        return

    changed = False
    for block in blocks:
        if not isinstance(block, dict) or block.get('type') != 'question':
            continue
        original = block.get('text', '') or ''
        new_text, source = normalise_text(original, content, default_level)
        report['questions'] += 1
        if new_text is None:
            report['no_marks'].append(f'{path.relative_to(DATA_DIR)}: {original[:70]!r}')
            continue
        if source == 'default':
            report['defaulted'] += 1
        if new_text != original:
            block['text'] = new_text
            changed = True
            report['changed'] += 1

    if changed and apply:
        if backup:
            shutil.copy2(path, path.with_suffix('.json.bak'))
        path.write_text(
            json.dumps(content, indent=2, ensure_ascii=False), encoding='utf-8')
    if changed:
        report['files'].add(str(path.relative_to(DATA_DIR)))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--dry-run', action='store_true',
                    help='Report what would change without writing files.')
    ap.add_argument('--default-level', default='SL', choices=['SL', 'HL'],
                    help='Level to use when none is found (default: SL).')
    ap.add_argument('--no-backup', action='store_true',
                    help='Do not write .bak copies of changed files.')
    args = ap.parse_args()

    if not DATA_DIR.exists():
        print(f'Data directory not found: {DATA_DIR}', file=sys.stderr)
        return 1

    report = {'questions': 0, 'changed': 0, 'defaulted': 0,
              'files': set(), 'no_marks': [], 'errors': []}

    for path in sorted(DATA_DIR.rglob('content.json')):
        process_file(path, args.default_level,
                     apply=not args.dry_run, backup=not args.no_backup,
                     report=report)

    mode = 'DRY RUN — nothing written' if args.dry_run else 'Applied'
    print(f'\n{mode}')
    print(f'  Question blocks scanned : {report["questions"]}')
    print(f'  Rewritten               : {report["changed"]}')
    print(f'  Files affected          : {len(report["files"])}')
    print(f'  Level defaulted to {args.default_level:<3}  : {report["defaulted"]}')
    if report['no_marks']:
        print(f'\n  {len(report["no_marks"])} question(s) had NO marks token (left unchanged):')
        for line in report['no_marks']:
            print(f'    - {line}')
    if report['errors']:
        print('\n  Errors:')
        for line in report['errors']:
            print(f'    - {line}')
    if report['files'] and not args.dry_run:
        print('\n  Changed files:')
        for f in sorted(report['files']):
            print(f'    - {f}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
