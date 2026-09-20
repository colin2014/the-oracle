"""Automated batch quiz question generator using Google Gemini API.

Processes all unfinished pages in a book (e.g. Book_93), generating exactly 9
IB Computer Science short-answer questions per page with full markschemes,
explanations, and auto-marking keyword groups.

Usage:
    python scripts/auto_generate_quizzes.py --book Book_93
    python scripts/auto_generate_quizzes.py --book Book_93 --delay 6 --model gemini-flash-latest
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

# Ensure UTF-8 output in Windows cmd/powershell consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Ensure all print statements flush immediately for real-time background task logging
_builtin_print = print
def print(*args, **kwargs):
    kwargs.setdefault("flush", True)
    _builtin_print(*args, **kwargs)

# Add project root to sys.path so app/models/routes can be imported cleanly
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

try:
    from google import genai
    from google.genai import types
    from google.genai.errors import APIError
except ImportError:
    print("❌ Error: google-genai package not found. Run: python -m pip install google-genai")
    sys.exit(1)

from app import app
from extensions import db
from models import QuizQuestion
from quiz_routes import _load_page_content, _book_meta, _extract_page_text, _page_title, _save_questions_payload


# Ordered fallback pool: if one model hits its free tier daily quota (e.g. 20 RPD),
# the script automatically rotates to the next model and continues without stopping.
MODEL_POOL = [
    "gemini-flash-latest",       # gemini-3.5-flash
    "gemini-flash-lite-latest",  # gemini-3.1-flash-lite
    "gemma-4-31b-it",            # Gemma 4 31B instruction-tuned
    "gemma-4-26b-a4b-it",        # Gemma 4 26B MoE instruction-tuned
]


GEMINI_QUIZ_PROMPT = """You are helping an IB Computer Science teacher create a comprehensive 9-question section quiz for 17-year-old students based ONLY on the provided textbook section text.

**Difficulty & Marks Distribution for the exactly 9 questions:**
- Easy (4 questions): Identify, Define, State — 1 mark each. Discrete recall, no explanation needed.
- Medium (3 questions): Outline, Describe, Explain — 2-3 marks each. Require brief explanation of how/why.
- Hard (2 questions): Compare, Contrast, Analyze, Evaluate, Justify — 4-5 marks each. Require synthesis or discussion.

For EACH question, you must provide all 8 of these fields:
1. "command": The IB command term (e.g. "Define", "Explain", "Analyze").
2. "summary": A concise 2-4 word topic label for analytics (e.g. "CPU Cache Levels").
3. "text": The question shown to the student. If the question uses terminology introduced in this specific section, briefly define/contextualize the term inside the question so the student isn't left guessing.
4. "marks": Total marks for this question (int: 1 for easy, 2-3 for medium, 4-5 for hard).
5. "difficulty": String: "easy", "medium", or "hard" based on complexity.
6. "markscheme": Clear model answer with explicit [1 mark] tags for each scoring point (e.g. "Cache is fast memory [1 mark]. Located near CPU [1 mark].").
7. "explanation": Student-friendly explanation (2-3 sentences) in simple language explaining the underlying concept or what students often get wrong.
8. "keywords": A list of keyword groups used for auto-marking. Each group represents one essential point from the markscheme. Each group must list 6-12 lowercase synonyms/phrases/word-stems that express that point. E.g. [["cache", "fast memory", "memory buffer"], ["cpu", "processor", "chip", "core"]].

Rules:
- Only test concepts actually taught in the SECTION TEXT below. Do not test outside trivia.
- Respond with ONLY valid JSON inside a fenced ```json code block.
- Exactly 9 questions inside the "questions" list (4 easy, 3 medium, 2 hard).

Shape:
```json
{{
  "questions": [
    {{
      "command": "Define",
      "summary": "Cache Memory",
      "text": "Define cache memory.",
      "marks": 1,
      "difficulty": "easy",
      "markscheme": "Small, fast memory located close to the CPU [1 mark].",
      "explanation": "Cache is a tiny, super-fast memory right next to the CPU. Because it is so close and small, the CPU can grab data from it much faster than RAM.",
      "keywords": [["cache", "fast memory", "buffer"], ["cpu", "processor", "close", "near", "chip"]]
    }}
  ]
}}
```

SECTION TITLE: {title}

SECTION TEXT:
{text}"""


def print_header(text):
    print("\n" + "=" * 80)
    print(f" ✨ {text} ✨ ".center(80))
    print("=" * 80)


def print_divider():
    print("-" * 80)


def generate_for_page(client, model_pool, current_model_idx, book_folder, page_id, page_title, page_text, replace=False):
    """Call Gemini/Gemma with automatic fallback rotation across model_pool."""
    prompt = GEMINI_QUIZ_PROMPT.format(title=page_title, text=page_text[:24000])

    max_retries = 3
    attempt = 1
    while attempt <= max_retries:
        model_name = model_pool[current_model_idx]
        try:
            print(f"       🧠 Sending request (`{model_name}`)... (Attempt {attempt}/{max_retries})")
            start_time = time.time()
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=8192,
                )
            )
            elapsed = time.time() - start_time
            print(f"       ⏱️  Received response in {elapsed:.1f}s")
            break
        except APIError as e:
            err_str = str(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                if current_model_idx + 1 < len(model_pool):
                    current_model_idx += 1
                    new_model = model_pool[current_model_idx]
                    print(f"       🔄 Quota limit reached on `{model_name}`. Automatically switching to backup model `{new_model}`...")
                    attempt = 1  # reset attempt count for the new model
                    continue
                else:
                    wait_time = 45 * attempt
                    print(f"       ⚠️  Rate limit / Quota exceeded on all models. Throttling backoff for {wait_time}s...")
                    time.sleep(wait_time)
                    attempt += 1
            else:
                if attempt == max_retries:
                    raise
                print(f"       ⚠️  API error: {e}. Retrying in 10s...")
                time.sleep(10)
                attempt += 1
        except Exception as e:
            if attempt == max_retries:
                raise
            print(f"       ⚠️  Unexpected network error: {e}. Retrying in 10s...")
            time.sleep(10)
            attempt += 1

    # Clean and parse JSON response
    raw_text = response.text or ""
    cleaned_json = re.sub(r"^```(?:json)?|```$", "", raw_text.strip(), flags=re.MULTILINE).strip()
    
    try:
        payload = json.loads(cleaned_json)
    except ValueError as e:
        match = re.search(r"\{[\s\S]*\}", cleaned_json)
        if match:
            try:
                payload = json.loads(match.group(0))
            except ValueError:
                raise ValueError(f"Could not parse JSON from response: {e}")
        else:
            raise ValueError(f"Could not parse JSON from response: {e}")

    # Validate and save to database using existing app logic
    count, err = _save_questions_payload(book_folder, page_id, payload, replace=replace)
    if err:
        raise ValueError(f"Validation failed during DB import: {err}")

    return count, current_model_idx


def main():
    parser = argparse.ArgumentParser(description="Batch auto-generate quiz questions with Gemini API.")
    parser.add_argument("--book", default="Book_93", help="Book folder name in data/ (default: Book_93)")
    parser.add_argument("--model", default="gemini-flash-latest", help="Gemini model to use (default: gemini-flash-latest)")
    parser.add_argument("--delay", type=float, default=6.0, help="Delay in seconds between requests to throttle usage (default: 6.0s)")
    parser.add_argument("--replace", action="store_true", help="Overwrite existing questions if present")
    parser.add_argument("--limit", type=int, default=0, help="Stop after generating for this many pages (0 = no limit)")
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("❌ Error: GEMINI_API_KEY not found in .env file.")
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    print_header(f"BATCH QUIZ GENERATOR: {args.book}")
    print(f" ⚙️  Model:      {args.model}")
    print(f" ⚙️  Throttle:   {args.delay}s delay between requests")
    print(f" ⚙️  Replace:    {'YES (Overwrite existing)' if args.replace else 'NO (Skip completed pages)'}")
    print_divider()

    with app.app_context():
        book_title, pages_dict = _book_meta(args.book)
        if not pages_dict:
            print(f"❌ Error: Could not find or read pages for book '{args.book}' in data/{args.book}/book.json")
            sys.exit(1)

        total_pages = len(pages_dict)
        print(f" 📖 Book Title: {book_title}")
        print(f" 📄 Total Pages in Book: {total_pages}")

        # Pre-scan completed pages
        existing_counts = {}
        for q in QuizQuestion.query.filter_by(book_folder=args.book).all():
            existing_counts[q.page_id] = existing_counts.get(q.page_id, 0) + 1

        completed = len(existing_counts)
        print(f" ✓  Already Completed:   {completed} page(s)")
        print(f" ⌛ Remaining to Do:     {total_pages - completed if not args.replace else total_pages} page(s)")
        print_divider()

        generated_count = 0
        skipped_count = 0
        error_count = 0

        # Initialize model pool starting from requested or first model
        model_pool = list(MODEL_POOL)
        if args.model in model_pool:
            current_model_idx = model_pool.index(args.model)
        else:
            model_pool.insert(0, args.model)
            current_model_idx = 0

        for idx, (page_id, page_title_raw) in enumerate(pages_dict.items(), 1):
            print(f"\n[{idx:03d}/{total_pages:03d}] Page ID: {page_id}")
            print(f"          Title:   {page_title_raw}")

            # Check existing status
            if not args.replace and existing_counts.get(page_id, 0) > 0:
                print(f"          Status:  ⏭️  Already has {existing_counts[page_id]} questions. Skipping!")
                skipped_count += 1
                continue

            # Load page text
            content = _load_page_content(args.book, page_id)
            if not content:
                print(f"          Status:  ⚠️  Could not load content.json for {page_id}. Skipping!")
                skipped_count += 1
                continue

            page_text = _extract_page_text(content)
            if not page_text or len(page_text) < 100:
                print(f"          Status:  ⏭️  Section text too short (<100 chars: {len(page_text or '')}). Skipping!")
                skipped_count += 1
                continue

            # Generate via Gemini/Gemma fallback pool
            try:
                count, current_model_idx = generate_for_page(
                    client=client,
                    model_pool=model_pool,
                    current_model_idx=current_model_idx,
                    book_folder=args.book,
                    page_id=page_id,
                    page_title=page_title_raw,
                    page_text=page_text,
                    replace=args.replace
                )
                print(f"          Status:  ✅ SUCCESS! Imported {count} questions.")
                generated_count += 1

                if args.limit > 0 and generated_count >= args.limit:
                    print(f"\n🎯 Reached requested limit of {args.limit} pages.")
                    break

                # Throttle delay
                if idx < total_pages:
                    print(f"          ⏱️  Throttling: sleeping {args.delay}s before next page to respect API quotas...")
                    time.sleep(args.delay)

            except Exception as e:
                print(f"          Status:  ❌ ERROR generating questions: {e}")
                error_count += 1
                time.sleep(2)  # brief pause after error

        print_header("GENERATION SUMMARY")
        print(f" ✅ Pages Generated Now: {generated_count}")
        print(f" ⏭️  Pages Skipped:       {skipped_count}")
        print(f" ❌ Pages Errored:       {error_count}")
        print_divider()
        print("Done!")


if __name__ == "__main__":
    main()
