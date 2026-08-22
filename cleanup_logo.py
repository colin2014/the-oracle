"""Remove the GrowHall logo image from all scraped pages.

The GrowHall site embeds its logo as a base64 SVG on every page, so it gets
picked up by the scraper. This script deletes it from every content.json in
data/ — both from the 'blocks' list (image blocks) and the 'images' list.

Run any time with:  python cleanup_logo.py
"""
import json
from pathlib import Path

# Distinctive start of the base64-encoded GrowHall logo SVG
LOGO_MARKER = 'PHN2ZyB3aWR0aD0iMzIiIGhlaWdodD0iMzIiIHZpZXdCb3g9IjAgMCAzMiAzMiI'


def is_logo(src, alt=''):
    src = src or ''
    return LOGO_MARKER in src or (alt == 'GrowHall' and src.startswith('data:image/svg'))


def clean_page(content_file):
    with open(content_file, 'r', encoding='utf-8') as f:
        content = json.load(f)

    removed = 0

    blocks = content.get('blocks')
    if blocks:
        kept = [b for b in blocks
                if not (b.get('type') == 'image' and is_logo(b.get('src'), b.get('alt', '')))]
        removed += len(blocks) - len(kept)
        content['blocks'] = kept

    images = content.get('images')
    if images:
        kept = [img for img in images
                if not is_logo(img.get('local_path', ''), img.get('alt_text', ''))
                and not is_logo(img.get('original_src', ''))]
        removed += len(images) - len(kept)
        content['images'] = kept

    if removed:
        with open(content_file, 'w', encoding='utf-8') as f:
            json.dump(content, f, indent=2, ensure_ascii=False)
    return removed


def main():
    data_dir = Path('data')
    total_removed = 0
    pages_touched = 0

    for content_file in sorted(data_dir.glob('*/content.json')):
        removed = clean_page(content_file)
        if removed:
            pages_touched += 1
            print(f'  {content_file.parent.name}: removed {removed} logo image(s)')
            total_removed += removed

    print(f'\nDone. Removed {total_removed} logo image(s) across {pages_touched} page(s).')


if __name__ == '__main__':
    main()
