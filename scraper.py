import requests
from bs4 import BeautifulSoup
import json
import os
import shutil
import re
from urllib.parse import urlparse, urljoin
from datetime import datetime
import hashlib
from pathlib import Path

class ContentScraper:
    def __init__(self, data_dir="data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.should_stop = False  # Flag to stop scraping

    def scrape_url(self, url):
        """Scrape content from URL (or local file) and organize by sections"""
        try:
            is_local = False
            file_path = None
            
            if url.startswith('file://'):
                is_local = True
                file_path = url[7:]
                # Under Windows, file:///C:/path/to/file needs to have the leading slash removed
                if file_path.startswith('/') and file_path[2] == ':':
                    file_path = file_path[1:]
            elif os.path.exists(url):
                is_local = True
                file_path = url
            elif ':' in url and not url.startswith('http'):
                # Handle Windows paths like C:\path\to\file
                is_local = True
                file_path = url

            if is_local:
                with open(file_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                soup = BeautifulSoup(html_content, 'html.parser')
            else:
                response = requests.get(url, headers=self.headers, timeout=10)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')

            # Extract title first to determine folder name
            title = self._extract_title(soup)
            sanitized_title = "".join(c for c in title if c not in r'\/:*?"<>|').strip()
            if not sanitized_title or sanitized_title.lower() == 'untitled' or len(sanitized_title) < 3:
                url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
                folder_name = f"scraped_{url_hash}"
            else:
                # Replace consecutive whitespace/spaces with single space
                folder_name = re.sub(r'\s+', ' ', sanitized_title).strip()

            content_dir = self.data_dir / folder_name
            content_dir.mkdir(exist_ok=True)
            images_dir = content_dir / "images"
            images_dir.mkdir(exist_ok=True)

            # Extract content
            topic_number, section_title = self._parse_topic_title(title)
            content_data = {
                'url': url,
                'scraped_at': datetime.now().isoformat(),
                'title': title,
                'topic_number': topic_number,
                'section_title': section_title,
                'main_heading': self._extract_main_heading(soup),
                'navigation': self._extract_navigation(soup),
                'main_content': self._extract_main_content(soup),
                'sidebar_sections': self._extract_sidebar_sections(soup),
                'images': []
            }

            # Download images
            images = soup.find_all('img')
            for idx, img in enumerate(images):
                src = img.get('src')
                if src:
                    image_path = self._download_image(src, url, images_dir, idx)
                    if image_path:
                        local_path = str(image_path.relative_to(self.data_dir)).replace('\\', '/')
                    else:
                        local_path = src  # fallback to original URL if download fails
                    
                    content_data['images'].append({
                        'original_src': src,
                        'local_path': local_path,
                        'alt_text': img.get('alt', '') or img.get('title', '') or ''
                    })

            # Save content
            content_file = content_dir / "content.json"
            with open(content_file, 'w', encoding='utf-8') as f:
                json.dump(content_data, f, indent=2, ensure_ascii=False)

            # Save metadata
            metadata = {
                'url': url,
                'folder': str(content_dir.relative_to(self.data_dir)),
                'scraped_at': datetime.now().isoformat(),
                'status': 'success'
            }

            return {
                'success': True,
                'folder': str(content_dir.relative_to(self.data_dir)),
                'content': content_data,
                'message': f'Successfully scraped {url}'
            }
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'message': f'Failed to scrape URL: {str(e)}'
            }

    def _extract_title(self, soup):
        title_tag = soup.find('title')
        return title_tag.get_text().strip() if title_tag else 'Untitled'

    def _extract_main_heading(self, soup):
        # Look for tag h1 or elements with class h1
        h1_el = soup.find(lambda tag: tag.name == 'h1' or (tag.get('class') and 'h1' in tag.get('class')))
        if h1_el:
            return h1_el.get_text().strip()
        
        # Fallback to h2
        h2_el = soup.find(lambda tag: tag.name == 'h2' or (tag.get('class') and 'h2' in tag.get('class')))
        if h2_el:
            return h2_el.get_text().strip()
            
        return ''

    def _extract_navigation(self, soup):
        """Extract the left sidebar navigation structure"""
        nav_items = []
        
        # First try to find sidebar menu container
        menu_container = soup.find(class_=lambda c: c and any(x in c for x in ['menu-wp', 'sidebar-nav', 'navigation']))
        if menu_container:
            links = menu_container.find_all('a', href=True)
        else:
            links = soup.find_all('a', href=True)

        for link in links:
            text = link.get_text().strip()
            href = link.get('href')
            if text and href and not href.startswith('javascript'):
                # Avoid duplicates
                if not any(item['text'] == text for item in nav_items):
                    nav_items.append({
                        'text': text,
                        'href': href,
                        'level': self._estimate_hierarchy_level(text)
                    })

        # Keep the full book menu — a 100-item cap used to cut off later units
        # (e.g. everything after B1.1.1), losing their section titles.
        return nav_items[:500]

    def _extract_sidebar_sections(self, soup):
        """Extract special sections like Study Tip, Theory of Knowledge, etc."""
        sidebar_sections = {}
        
        # 1. Look for div elements with class containing 'side-box'
        side_boxes = soup.find_all('div', class_=lambda c: c and 'side-box' in c)
        for sb in side_boxes:
            title_div = sb.find(class_=lambda c: c and 'title' in c)
            content_div = sb.find(class_=lambda c: c and 'content' in c)
            if title_div and content_div:
                title = title_div.get_text().strip()
                content = content_div.get_text().strip()
                if title and content:
                    sidebar_sections[title] = content
                    
        # 2. Look for other elements that might represent sections if we didn't find any side-boxes
        if not sidebar_sections:
            section_keywords = [
                'Study Tip', 'Theory of Knowledge', 'Applied Work', 'Fun Fact',
                'International-Mindedness', 'Approaches to Learning', 'Key Concept',
                'Vocabulary', 'Practice Questions', 'Activity'
            ]
            for keyword in section_keywords:
                el = soup.find(string=lambda s: s and keyword.lower() in s.lower())
                if el:
                    parent = el.parent
                    content_text = ""
                    sibling = parent.find_next_sibling()
                    if sibling:
                        content_text = sibling.get_text().strip()
                    if not content_text and parent.parent:
                        sib2 = parent.parent.find_next_sibling()
                        if sib2:
                            content_text = sib2.get_text().strip()
                    if content_text:
                        sidebar_sections[keyword] = content_text

        return sidebar_sections

    def _extract_main_content(self, soup):
        """Extract main content organized by subsections"""
        content = {}
        
        # Find the main content container
        main_container = None
        main_divs = soup.find_all('div', class_=lambda c: c and 'main' in c)
        for m in main_divs:
            classes = m.get('class', [])
            if any(x in classes for x in ['main-flex', 'main-grid']):
                continue
            children = list(m.find_all(recursive=False))
            if len(children) >= 3:
                main_container = m
                break
                
        if not main_container:
            main_container = soup.find('body') or soup

        blocks = list(main_container.find_all(recursive=False)) if main_container else []
        if not blocks:
            blocks = [main_container]
            
        block_idx = 1
        for block in blocks:
            classes = block.get('class', [])
            classes_str = ' '.join(classes) if classes else ''
            if any(x in classes_str for x in ['sidebar', 'header', 'menu', 'nav']):
                continue
                
            section_title = None
            
            # 1. Look for headings with specific class or tag
            h_el = block.find(lambda tag: tag.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6'] or 
                             (tag.get('class') and any(c in ' '.join(tag.get('class')).lower() for c in ['strong', 'bold', 'h1', 'h2', 'h3', 'h4', 'color-label'])))
            
            if h_el:
                section_title = h_el.get_text().strip()
                if len(section_title) > 100:
                    section_title = None
            
            # 2. If no heading element, check prefix text
            block_text = block.get_text().strip()
            if not section_title:
                prefixes = [
                    'Guiding Questions', 'Vocabulary', 'Practice Questions',
                    'International-Mindedness', 'Approaches to Learning'
                ]
                for prefix in prefixes:
                    if block_text.lower().startswith(prefix.lower()):
                        section_title = prefix
                        break
            
            # 3. Fallback
            if not section_title:
                if block_idx == 1:
                    section_title = "Introduction"
                else:
                    section_title = f"Section {block_idx}"
            
            # Extract text (excluding title text if found)
            paragraphs = block.find_all('p')
            if paragraphs:
                text_content = '\n\n'.join(p.get_text().strip() for p in paragraphs if p.get_text().strip())
            else:
                text_content = block_text
                if h_el and section_title and text_content.startswith(section_title):
                    text_content = text_content[len(section_title):].strip()
                    
            if text_content:
                text_content = text_content.replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'")
                text_content = text_content.replace('\ufffd', "'")
                content[section_title] = text_content
                block_idx += 1
                
        return content

    def _estimate_hierarchy_level(self, text):
        """Estimate hierarchy level based on academic text patterns"""
        text = text.strip()
        if text.startswith('Theme'):
            return 1
        if text == 'Introduction':
            return 2
            
        if re.match(r'^[A-Z]\.?\d+\.\d+\.\d+', text):
            return 4
        if re.match(r'^[A-Z]\.?\d+\.\d+', text):
            return 3
        if re.match(r'^[A-Z]\.?\d+', text):
            return 2
            
        return 4

    def _download_image(self, src, base_url, save_dir, idx):
        """Download or copy image, saving it locally"""
        try:
            # Check if base_url is a local path or file:// URL
            is_local_base = False
            base_path = None
            if base_url.startswith('file://'):
                is_local_base = True
                base_path = base_url[7:]
                if base_path.startswith('/') and base_path[2] == ':':
                    base_path = base_path[1:]
                base_path = os.path.dirname(base_path)
            elif os.path.exists(base_url):
                is_local_base = True
                base_path = os.path.dirname(base_url)
            else:
                if ':' in base_url and not base_url.startswith('http'):
                    is_local_base = True
                    base_path = os.path.dirname(base_url)

            if is_local_base:
                # Resolve local image path
                clean_src = src.split('?')[0].split('#')[0]
                clean_src = clean_src.replace('/', os.sep).replace('\\', os.sep)
                if clean_src.startswith('.' + os.sep):
                    clean_src = clean_src[2:]
                elif clean_src.startswith(os.sep):
                    clean_src = clean_src[1:]

                potential_paths = [
                    os.path.join(base_path, clean_src),
                    os.path.join(base_path, 'exampleWebpage', os.path.basename(clean_src)),
                    os.path.join(os.getcwd(), 'exampleWebpage', os.path.basename(clean_src))
                ]
                
                resolved_path = None
                for path in potential_paths:
                    if os.path.exists(path):
                        resolved_path = path
                        break
                        
                if resolved_path:
                    _, ext = os.path.splitext(resolved_path)
                    ext = ext.lstrip('.').lower() or 'png'
                    filename = f"image_{idx}.{ext}"
                    filepath = save_dir / filename
                    
                    shutil.copy2(resolved_path, filepath)
                    return filepath
                else:
                    print(f"Could not find local image: {src}")
                    return None
            else:
                # Convert relative URL to absolute
                if src.startswith('/'):
                    parsed_url = urlparse(base_url)
                    img_url = f"{parsed_url.scheme}://{parsed_url.netloc}{src}"
                elif src.startswith('http'):
                    img_url = src
                else:
                    img_url = urljoin(base_url, src)

                response = requests.get(img_url, headers=self.headers, timeout=5)
                response.raise_for_status()

                # Determine file extension
                content_type = response.headers.get('content-type', 'image/jpeg')
                ext = 'jpg' if 'jpeg' in content_type else content_type.split('/')[-1]
                ext = ext.split(';')[0]

                filename = f"image_{idx}.{ext}"
                filepath = save_dir / filename

                with open(filepath, 'wb') as f:
                    f.write(response.content)

                return filepath
        except Exception as e:
            print(f"Failed to download/copy image {src}: {e}")
            return None

    def get_all_scraped_content(self):
        """Get list of all scraped content: root-level folders plus pages
        nested inside book folders (e.g. Book_93/6840/content.json)."""
        items = []

        def add_item(content_file, folder_name):
            try:
                with open(content_file, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                items.append({
                    'folder': folder_name,
                    'url': content.get('url'),
                    'title': content.get('title'),
                    'scraped_at': content.get('scraped_at'),
                    'image_count': len(content.get('images', []))
                })
            except Exception as e:
                print(f"Error loading {content_file}: {e}")

        for folder in self.data_dir.iterdir():
            if not folder.is_dir():
                continue
            content_file = folder / "content.json"
            if content_file.exists():
                add_item(content_file, folder.name)
            # Book folders: each page lives in its own subfolder
            for sub in folder.iterdir():
                if sub.is_dir() and (sub / "content.json").exists():
                    add_item(sub / "content.json", sub.name)

        return items

    def resolve_content_path(self, folder_name):
        """Return the Path to folder_name's content.json.
        Searches data/folder_name first, then one level inside book folders
        (e.g. data/Book_93/6840/content.json). Returns None if not found."""
        direct = self.data_dir / folder_name / "content.json"
        if direct.exists():
            return direct
        # "Book_X/<page_id>" where the page's folder was renamed
        if '/' in folder_name:
            parent, pid = folder_name.split('/', 1)
            resolved = self.data_dir / parent / self.resolve_page_folder(parent, pid) / "content.json"
            if resolved.exists():
                return resolved
        for book_dir in self.data_dir.iterdir():
            if book_dir.is_dir():
                nested = book_dir / folder_name / "content.json"
                if nested.exists():
                    return nested
        # Bare page id whose folder was renamed — resolve via each book's book.json
        for book_dir in self.data_dir.iterdir():
            if book_dir.is_dir() and (book_dir / "book.json").exists():
                resolved = book_dir / self.resolve_page_folder(book_dir.name, folder_name) / "content.json"
                if resolved.exists():
                    return resolved
        return None

    def get_content_details(self, folder_name):
        """Get detailed content from a specific folder (root or nested in a book)"""
        content_file = self.resolve_content_path(folder_name)
        if content_file:
            with open(content_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def search_content(self, query):
        """Search across all scraped content, including nested book folders"""
        results = []
        query_lower = query.lower()

        # Search root-level folders
        for folder in self.data_dir.iterdir():
            if not folder.is_dir():
                continue

            content_file = folder / "content.json"
            if content_file.exists():
                self._search_content_in_folder(content_file, folder.name, query_lower, results)

            # Also search nested folders (e.g., Book_93/6840/content.json)
            for subfolder in folder.iterdir():
                if subfolder.is_dir():
                    content_file = subfolder / "content.json"
                    if content_file.exists():
                        self._search_content_in_folder(content_file, subfolder.name, query_lower, results)

        return results

    def _search_content_in_folder(self, content_file, folder_name, query_lower, results):
        """Helper to search a single content file"""
        try:
            with open(content_file, 'r', encoding='utf-8') as f:
                content = json.load(f)

            # Search in various fields
            matches = []
            for field in ['title', 'main_heading', 'main_content']:
                if field in content:
                    text = str(content[field]).lower()
                    if query_lower in text:
                        matches.append(field)

            # Search in sidebar sections
            for section_name, section_text in content.get('sidebar_sections', {}).items():
                if query_lower in section_text.lower():
                    matches.append(f"sidebar: {section_name}")

            if matches:
                results.append({
                    'folder': folder_name,
                    'url': content.get('url'),
                    'title': content.get('title'),
                    'matched_fields': matches
                })
        except Exception as e:
            print(f"Error searching {content_file}: {e}")

    def discover_books(self, base_url):
        """Discover all available books listed at the given site's /books index."""
        try:
            books = []
            # Fetch the main books page to discover all books
            response = requests.get(f"{base_url}/books", headers=self.headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for book links - pattern: /books/<book_id>
            links = soup.find_all('a', href=re.compile(r'/books/\d+'))
            seen_ids = set()

            for link in links:
                href = link.get('href')
                match = re.search(r'/books/(\d+)', href)
                if match:
                    book_id = match.group(1)
                    if book_id not in seen_ids:
                        title = link.get_text().strip()
                        if title and len(title) > 2:
                            books.append({
                                'id': book_id,
                                'title': title,
                                'url': f"{base_url}/books/{book_id}"
                            })
                            seen_ids.add(book_id)

            return books
        except Exception as e:
            print(f"Failed to discover books: {e}")
            return []

    def scrape_book(self, book_id, base_url):
        """Scrape all pages in a book"""
        self.should_stop = False
        try:
            book_url = f"{base_url}/books/{book_id}"
            response = requests.get(book_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract book title
            title_tag = soup.find('title')
            book_title = title_tag.get_text().strip() if title_tag else f"Book {book_id}"

            # Sanitize folder name
            folder_name = "".join(c for c in book_title if c not in r'\/:*?"<>|').strip()
            if not folder_name or len(folder_name) < 3:
                folder_name = f"book_{book_id}"
            else:
                folder_name = re.sub(r'\s+', '_', folder_name)

            book_dir = self.data_dir / folder_name
            book_dir.mkdir(exist_ok=True)

            # Discover all pages in this book
            pages = self._discover_book_pages(soup, base_url, book_id)

            # Save book metadata
            book_meta = {
                'id': book_id,
                'title': book_title,
                'url': book_url,
                'created_at': datetime.now().isoformat(),
                'pages': []
            }

            # Scrape each page
            for idx, page in enumerate(pages):
                if self.should_stop:
                    return {'success': False, 'message': 'Scraping stopped by user', 'partial': True, 'folder': folder_name}

                page_id = page['id']
                page_url = f"{base_url}/books/{book_id}/{page_id}"

                print(f"Scraping page {idx+1}/{len(pages)}: {page_id}")

                result = self.scrape_book_page(book_id, page_id, page_url, book_dir)
                if result['success']:
                    book_meta['pages'].append({
                        'id': page_id,
                        'title': page['title'],
                        'url': page_url
                    })

            # Save book metadata
            book_meta_file = book_dir / "book.json"
            with open(book_meta_file, 'w', encoding='utf-8') as f:
                json.dump(book_meta, f, indent=2, ensure_ascii=False)

            # Update books catalogue
            self._update_books_catalogue()

            return {
                'success': True,
                'folder': folder_name,
                'book_id': book_id,
                'pages_scraped': len(book_meta['pages']),
                'message': f'Successfully scraped {len(book_meta["pages"])} pages'
            }
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e)}

    def _discover_book_pages(self, soup, base_url, book_id):
        """Discover all page IDs in a book"""
        pages = []
        seen_ids = set()

        # Look for links to pages: /books/<book_id>/<page_id>
        pattern = rf'/books/{book_id}/(\d+)'
        links = soup.find_all('a', href=re.compile(pattern))

        for link in links:
            href = link.get('href')
            match = re.search(pattern, href)
            if match:
                page_id = match.group(1)
                if page_id not in seen_ids:
                    title = link.get_text().strip()
                    if title and len(title) > 1:
                        pages.append({'id': page_id, 'title': title})
                        seen_ids.add(page_id)

        return pages

    def scrape_book_page(self, book_id, page_id, page_url, book_dir):
        """Scrape a single page within a book"""
        try:
            response = requests.get(page_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            title = self._extract_title(soup)

            # Create page directory
            page_dir = book_dir / page_id
            page_dir.mkdir(exist_ok=True)
            images_dir = page_dir / "images"
            images_dir.mkdir(exist_ok=True)

            # Extract content
            topic_number, section_title = self._parse_topic_title(title)
            content_data = {
                'book_id': book_id,
                'page_id': page_id,
                'url': page_url,
                'scraped_at': datetime.now().isoformat(),
                'title': title,
                'topic_number': topic_number,
                'section_title': section_title,
                'main_heading': self._extract_main_heading(soup),
                'navigation': self._extract_navigation(soup),
                'main_content': self._extract_main_content(soup),
                'sidebar_sections': self._extract_sidebar_sections(soup),
                'images': []
            }

            # Download images
            images = soup.find_all('img')
            for idx, img in enumerate(images):
                src = img.get('src')
                if src:
                    image_path = self._download_image(src, page_url, images_dir, idx)
                    if image_path:
                        local_path = str(image_path.relative_to(self.data_dir)).replace('\\', '/')
                    else:
                        local_path = src

                    content_data['images'].append({
                        'original_src': src,
                        'local_path': local_path,
                        'alt_text': img.get('alt', '') or img.get('title', '') or ''
                    })

            # Save content
            content_file = page_dir / "content.json"
            with open(content_file, 'w', encoding='utf-8') as f:
                json.dump(content_data, f, indent=2, ensure_ascii=False)

            return {'success': True, 'page_id': page_id}
        except Exception as e:
            print(f"Failed to scrape page {page_id}: {e}")
            return {'success': False, 'error': str(e)}

    def _update_books_catalogue(self):
        """Update books catalogue"""
        books = []
        for folder in self.data_dir.iterdir():
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
                                'created_at': book_data.get('created_at'),
                                'cover_image': book_data.get('cover_image')
                            })
                    except Exception as e:
                        print(f"Error loading {book_file}: {e}")

        # Save catalogue
        catalogue_file = self.data_dir / "books.json"
        with open(catalogue_file, 'w', encoding='utf-8') as f:
            json.dump({'books': books, 'last_updated': datetime.now().isoformat()}, f, indent=2, ensure_ascii=False)

    def get_books_catalogue(self):
        """Get list of all books"""
        catalogue_file = self.data_dir / "books.json"
        if catalogue_file.exists():
            try:
                with open(catalogue_file, 'r', encoding='utf-8') as f:
                    return json.load(f).get('books', [])
            except:
                return []
        return []

    def get_book_pages(self, book_folder):
        """Get all pages in a book"""
        book_file = self.data_dir / book_folder / "book.json"
        if book_file.exists():
            try:
                with open(book_file, 'r', encoding='utf-8') as f:
                    book_data = json.load(f)
                    return book_data.get('pages', [])
            except:
                return []
        return []

    def resolve_page_folder(self, book_folder, page_id):
        """Map a page id to its on-disk folder via book.json (folders may be
        renamed to human-readable names while ids stay stable)."""
        if (self.data_dir / book_folder / page_id).is_dir():
            return page_id
        for page in self.get_book_pages(book_folder):
            if page.get('id') == page_id and page.get('folder'):
                return page['folder']
        return page_id

    def get_page_content(self, book_folder, page_id):
        """Get content for a specific page"""
        folder = self.resolve_page_folder(book_folder, page_id)
        content_file = self.data_dir / book_folder / folder / "content.json"
        if content_file.exists():
            try:
                with open(content_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return None
        return None

    def stop_scraping(self):
        """Stop the current scraping operation"""
        self.should_stop = True

    def _parse_topic_title(self, title):
        # Match patterns like:
        # "Theme A Concepts of computer science" -> Group 1: "Theme A", Group 2: "Concepts of computer science"
        # "A1.1 Computer hardware and operation" -> Group 1: "A1.1", Group 2: "Computer hardware and operation"
        # "A1.1.1 Describe the functions..." -> Group 1: "A1.1.1", Group 2: "Describe the functions..."
        # "A 1.2 Networks" -> Group 1: "A 1.2", Group 2: "Networks"
        match = re.match(r'^((?:Theme\s+[A-Z])|(?:[A-Z]\s*\d*(?:\.\d+)*))\.?\s*(.*)$', title, re.IGNORECASE)
        if match:
            topic_number = match.group(1).strip()
            section_title = match.group(2).strip()
        else:
            topic_number = ""
            section_title = title
        return topic_number, section_title


# ---------------------------------------------------------------------------
# YouTube scanner for Chrome "Webpage, Complete" saved files
# ---------------------------------------------------------------------------

def extract_youtube_from_saved_files(page_url: str) -> list:
    """Scan the _files/ directory that Chrome creates when saving a page as
    'Webpage, Complete' and extract YouTube video IDs from the
    ``<!-- saved from url=(...)https://www.youtube.com/embed/VIDEO_ID -->``
    comment that Chrome writes at the top of every saved iframe HTML.

    Returns a list of video dicts compatible with the blocks system:
        [{'src': 'https://www.youtube.com/embed/VIDEO_ID',
          'title': 'Video', 'side': True}, ...]

    Works for both file:// URLs and plain local paths passed via the extension.
    """
    from urllib.parse import unquote

    videos: list = []
    seen: set = set()

    # ── 1. Resolve the local path ──────────────────────────────────────────
    local_path: str | None = None

    if page_url.startswith('file:///'):
        # file:///C:/path/to/page.html  (Windows)
        local_path = unquote(page_url[8:])          # strip  file:///
    elif page_url.startswith('file://'):
        local_path = unquote(page_url[7:])          # strip  file://
        if local_path.startswith('/') and len(local_path) > 2 and local_path[2] == ':':
            local_path = local_path[1:]             # /C:/…  →  C:/…
    elif os.path.isabs(page_url) or (len(page_url) > 2 and page_url[1] == ':'):
        local_path = page_url                        # plain Windows path

    if local_path is None:
        return videos   # live URL – nothing to scan

    html_file = Path(local_path)
    if not html_file.exists():
        return videos

    # ── 2. Locate the _files/ directory ───────────────────────────────────
    files_dir = html_file.parent / f"{html_file.stem}_files"
    if not files_dir.is_dir():
        return videos

    # ── 3. Scan every .html file in the _files/ directory ─────────────────
    for saved_html in files_dir.glob('*.html'):
        try:
            # Chrome writes the saved-from comment in the first ~200 bytes.
            with open(saved_html, 'r', encoding='utf-8', errors='ignore') as fh:
                head = fh.read(512)

            # Match:  <!-- saved from url=(NNN)https://www.youtube.com/embed/VIDEO_ID... -->
            m = re.search(
                r'saved from url=\(\d+\)(https?://(?:www\.)?youtube(?:-nocookie)?\.com/embed/([\w-]{11}))',
                head, re.I
            )
            if not m:
                continue

            embed_url = m.group(1).split('?')[0]   # strip ?si=… query params
            vid_id    = m.group(2)

            if vid_id in seen:
                continue
            seen.add(vid_id)

            videos.append({
                'src':   embed_url,          # https://www.youtube.com/embed/clCPQo0-quo
                'title': 'Video',
                'side':  True
            })
        except Exception:
            continue

    return videos
