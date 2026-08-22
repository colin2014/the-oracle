#!/usr/bin/env python
"""Calculate reading time based on character count and update book.json files."""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List

# Force UTF-8 encoding for console output
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Reading speed: approximately 200-250 words per minute
# Average English word is ~5 characters, so ~1000-1250 characters per minute
# Using 1000 chars/min as conservative estimate
CHARS_PER_MINUTE = 1000

def extract_text_from_content(content_data: Dict[str, Any]) -> str:
    """Extract all text content from a content.json file."""
    text_parts = []

    # Extract from main content sections
    if 'main_content' in content_data and content_data['main_content']:
        for key, value in content_data['main_content'].items():
            if isinstance(value, str):
                text_parts.append(value)
            elif isinstance(value, dict):
                text_parts.append(str(value))

    # Extract from blocks
    if 'blocks' in content_data and isinstance(content_data['blocks'], list):
        for block in content_data['blocks']:
            if isinstance(block, dict):
                if 'text' in block:
                    text_parts.append(block['text'])
                if 'content' in block:
                    text_parts.append(block['content'])
                if 'code' in block:
                    text_parts.append(block['code'])

    # Extract from sidebar sections
    if 'sidebar_sections' in content_data and content_data['sidebar_sections']:
        for key, value in content_data['sidebar_sections'].items():
            if isinstance(value, str):
                text_parts.append(value)
            elif isinstance(value, dict):
                text_parts.append(str(value))

    # Extract from practice questions
    if 'practice_questions' in content_data and isinstance(content_data['practice_questions'], list):
        for question in content_data['practice_questions']:
            if isinstance(question, dict):
                if 'question' in question:
                    text_parts.append(question['question'])
                if 'content' in question:
                    text_parts.append(question['content'])

    return ' '.join(text_parts)

def calculate_reading_time(character_count: int) -> int:
    """Calculate reading time in minutes based on character count."""
    if character_count == 0:
        return 0
    minutes = max(1, round(character_count / CHARS_PER_MINUTE))
    return minutes

def process_book(book_path: Path) -> None:
    """Process a single book and update its book.json with reading times."""
    book_json_path = book_path / 'book.json'

    if not book_json_path.exists():
        print(f"[SKIP] No book.json found in {book_path.name}")
        return

    with open(book_json_path, 'r', encoding='utf-8') as f:
        book_data = json.load(f)

    if 'pages' not in book_data or not book_data['pages']:
        print(f"[SKIP] No pages found in {book_json_path}")
        return

    updated_count = 0
    total_pages = len(book_data['pages'])

    for page in book_data['pages']:
        page_id = page.get('id') or page.get('folder')

        # Skip redirect pages (exemplar collections)
        if 'type' in page and page['type'] == 'exemplar_collection_redirect':
            continue

        # Determine folder: use 'folder' field or fall back to page id
        folder = page.get('folder') or page.get('id')

        if not folder:
            continue

        content_path = book_path / folder / 'content.json'

        if not content_path.exists():
            print(f"  [SKIP] No content.json for page {page_id}")
            continue

        try:
            with open(content_path, 'r', encoding='utf-8') as f:
                content_data = json.load(f)

            # Extract text and count characters
            text = extract_text_from_content(content_data)
            char_count = len(text)
            reading_minutes = calculate_reading_time(char_count)

            # Update page data with reading time
            page['reading_time_minutes'] = reading_minutes
            page['character_count'] = char_count

            print(f"  [OK] {page.get('title', page_id)}: {char_count} chars → {reading_minutes} min")
            updated_count += 1

        except Exception as e:
            print(f"  [ERROR] Failed to process {page_id}: {str(e)}")

    # Write updated book.json back
    with open(book_json_path, 'w', encoding='utf-8') as f:
        json.dump(book_data, f, indent=2, ensure_ascii=False, default=str)

    print(f"[OK] Updated {book_path.name}: {updated_count}/{total_pages} pages\n")

def main():
    """Process all books in the data directory."""
    data_dir = Path('data')

    if not data_dir.exists():
        print(f"[ERROR] Data directory not found: {data_dir}")
        return

    print("=== Reading Time Calculator ===\n")
    print(f"Using {CHARS_PER_MINUTE} characters per minute as reading speed\n")

    books_processed = 0

    # Process each book folder
    for book_path in sorted(data_dir.iterdir()):
        if not book_path.is_dir():
            continue

        if (book_path / 'book.json').exists():
            print(f"Processing: {book_path.name}")
            process_book(book_path)
            books_processed += 1

    print(f"\n=== Complete! ===")
    print(f"Processed {books_processed} books")
    print(f"All reading times have been added to book.json files")

if __name__ == '__main__':
    main()
