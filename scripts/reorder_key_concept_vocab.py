"""
Reorder sidebar blocks so "Key Concept" renders at the top of every page's
side column, with "Vocabulary" directly below it.

Sidebar order is the relative order of sidebar-bound blocks in the blocks
array, so we move Key Concept sidebox blocks to the front of the array and
any stored vocab sidebox right after them (sideboxes never render in the
main column, so main-content order is unaffected). Pages whose vocabulary
lives in sidebar_sections are handled at render time by app.py, which now
injects the vocab box straight after a Key Concept block.

Pages with neither a Key Concept box nor any vocabulary are left untouched.

Usage:
    python scripts/reorder_key_concept_vocab.py           # dry run, shows changes
    python scripts/reorder_key_concept_vocab.py --apply   # write changes (.bak backups)
"""
import json
import shutil
import sys
from pathlib import Path


def is_key_concept(block):
    return (block.get('type') == 'sidebox'
            and (block.get('title') or '').strip().lower().startswith('key concept'))


def is_vocab(block):
    return block.get('type') == 'sidebox' and block.get('style') == 'vocab'


def reorder(blocks):
    """Return reordered blocks list, or None if no change needed."""
    kc = [b for b in blocks if is_key_concept(b)]
    vocab = [b for b in blocks if is_vocab(b) and not is_key_concept(b)]
    if not kc and not vocab:
        return None
    rest = [b for b in blocks if not is_key_concept(b) and not is_vocab(b)]
    new = kc + vocab + rest
    return new if new != blocks else None


def main():
    apply = '--apply' in sys.argv
    changed = skipped = 0
    for f in sorted(Path('data').rglob('content.json')):
        try:
            data = json.loads(f.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, OSError) as e:
            print(f'!! {f}: unreadable ({e})')
            continue
        blocks = data.get('blocks')
        if not isinstance(blocks, list):
            skipped += 1
            continue
        new = reorder(blocks)
        if new is None:
            skipped += 1
            continue
        changed += 1
        titles = [(b.get('title') or b.get('style') or '?') for b in new[:3]]
        print(f'{"APPLY" if apply else "would"} {f}  -> top blocks: {titles}')
        if apply:
            shutil.copy2(f, f.with_suffix('.json.bak'))
            data['blocks'] = new
            f.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'\n{changed} file(s) {"updated" if apply else "would change"}, {skipped} skipped.')


if __name__ == '__main__':
    main()
