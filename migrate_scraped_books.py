import os
import json
import re
import shutil
from pathlib import Path
from datetime import datetime

def migrate_data():
    data_dir = Path("data")
    if not data_dir.exists():
        print("No data directory found.")
        return

    # Identify directories that contain content.json but do not have book.json and are not inside a book folder
    folders_to_migrate = []
    for folder in data_dir.iterdir():
        if folder.is_dir() and not folder.name.startswith("book_"):
            # Check if it has a content.json
            content_file = folder / "content.json"
            if content_file.exists():
                # Check if it has book.json
                if not (folder / "book.json").exists():
                    folders_to_migrate.append(folder)

    if not folders_to_migrate:
        print("No legacy single-chapter folders found to migrate.")
        return

    print(f"Found {len(folders_to_migrate)} folder(s) to check/migrate.")

    # GrowHall book ID to book title mapping
    book_titles_map = {
        "73": "Theory of Knowledge",
        "72": "Geography",
        "93": "Computer Science (2027)",
        "60": "Mathematics: Applications and Interpretation",
        "50": "Chemistry",
        "81": "Global politics",
        "55": "Mathematics: Analysis and Approaches",
        "90": "Psychology (2027)",
        "347": "History - The Cold War",
        "343": "History - Prescribed Subject 3",
        "41": "Economics",
        "48": "Business Management",
        "70": "Environmental systems and societies (ESS)",
        "205": "English A: Language & Literature",
        "340": "Philosophy",
        "51": "Physics",
        "52": "Biology"
    }

    books_updated = set()

    for folder in folders_to_migrate:
        content_file = folder / "content.json"
        try:
            with open(content_file, 'r', encoding='utf-8') as f:
                content_data = json.load(f)
                
            url = content_data.get('url', '')
            title = content_data.get('title', '')
            
            # Check if it's a book page
            book_match = re.search(r'/books/(\d+)/(\d+)', url)
            if book_match:
                book_id = book_match.group(1)
                page_id = book_match.group(2)
                
                # Retrieve book title
                book_title = content_data.get('bookTitle')
                if not book_title or book_title == 'Untitled Book':
                    if book_id in book_titles_map:
                        book_title = book_titles_map[book_id]
                    else:
                        book_title = f"Book {book_id}"
                    
                sanitized_book_title = "".join(c for c in book_title if c not in r'\/:*?"<>|').strip()
                book_folder = re.sub(r'\s+', '_', sanitized_book_title)
                
                target_book_dir = data_dir / book_folder
                target_page_dir = target_book_dir / page_id
                
                print(f"Migrating '{folder.name}' -> '{book_folder}/{page_id}'")
                
                # Create directories
                target_page_dir.mkdir(parents=True, exist_ok=True)
                
                # Move content.json
                shutil.move(str(content_file), str(target_page_dir / "content.json"))
                
                # Move images folder if it exists
                images_dir = folder / "images"
                if images_dir.exists():
                    target_images_dir = target_page_dir / "images"
                    if target_images_dir.exists():
                        shutil.rmtree(str(target_images_dir))
                    shutil.move(str(images_dir), str(target_images_dir))
                    
                # Remove original folder if empty
                try:
                    folder.rmdir()
                except Exception as e:
                    print(f"Could not remove original folder {folder}: {e}")
                    
                # Update book.json
                book_meta_file = target_book_dir / "book.json"
                book_meta = {
                    'id': book_id,
                    'title': book_title,
                    'url': f"https://app.growhall.com/books/{book_id}",
                    'created_at': datetime.now().isoformat(),
                    'pages': []
                }
                if book_meta_file.exists():
                    try:
                        with open(book_meta_file, 'r', encoding='utf-8') as mf:
                            book_meta = json.load(mf)
                    except:
                        pass
                        
                page_entry = {
                    'id': page_id,
                    'title': title,
                    'url': url
                }
                if not any(p.get('id') == page_id for p in book_meta.get('pages', [])):
                    book_meta.setdefault('pages', []).append(page_entry)
                    
                with open(book_meta_file, 'w', encoding='utf-8') as mf:
                    json.dump(book_meta, mf, indent=2, ensure_ascii=False)
                    
                books_updated.add(book_folder)
                
        except Exception as e:
            print(f"Error migrating {folder.name}: {e}")

    # Regenerate catalog if any books were updated
    if books_updated:
        print("Regenerating books catalogue...")
        books = []
        for folder in data_dir.iterdir():
            if folder.is_dir():
                book_file = folder / "book.json"
                if book_file.exists():
                    try:
                        with open(book_file, 'r', encoding='utf-8') as f:
                            book_data = json.load(f)
                            books.append({
                                'id': book_data.get('id'),
                                'title': book_data.get('title'),
                                'url': book_data.get('url'),
                                'pages_count': len(book_data.get('pages', [])),
                                'folder': folder.name,
                                'created_at': book_data.get('created_at')
                            })
                    except Exception as e:
                        print(f"Error loading {book_file}: {e}")

        catalogue_file = data_dir / "books.json"
        with open(catalogue_file, 'w', encoding='utf-8') as f:
            json.dump({'books': books, 'last_updated': datetime.now().isoformat()}, f, indent=2, ensure_ascii=False)
            
        print("Migration and catalog update complete!")

if __name__ == '__main__':
    migrate_data()
