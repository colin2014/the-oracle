#!/usr/bin/env python
"""Remove content_html field from all content.json files since it's not used by the frontend."""

import json
from pathlib import Path

data_dir = Path(r"C:\Users\Colin\webscraper\data")
removed_count = 0
error_count = 0

for json_file in data_dir.rglob("content.json"):
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if 'content_html' in data:
            del data['content_html']

            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            removed_count += 1
            print(f"[OK] Cleaned: {json_file.relative_to(data_dir)}")
    except Exception as e:
        error_count += 1
        print(f"[ERR] Error processing {json_file}: {e}")

print(f"\nCompleted: {removed_count} files cleaned, {error_count} errors")
