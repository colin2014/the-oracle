"""Automated batch MULTIPLE-CHOICE question generator using Google Gemini API.

A variant of auto_generate_quizzes.py. For every page in a book that already has
a quiz but no multiple-choice questions yet, this generates up to 5 auto-marked
MCQs (single- and occasional multi-answer) and PREPENDS them to the top of that
page's existing question list.

Usage:
    python scripts/auto_generate_mcq.py --book Book_93
    python scripts/auto_generate_mcq.py --book Book_93 --delay 6 --limit 5 --n 5
"""

import argparse
import json
import os
import re
import sys
import time
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
from models import QuizQuestion
from quiz_routes import _load_page_content, _book_meta, _extract_page_text, _save_questions_payload


# Ordered fallback pool: if one model hits its free tier daily quota, the script
# automatically rotates to the next model and continues without stopping.
MODEL_POOL = [
    "gemini-flash-latest",       # gemini-3.5-flash
    "gemini-flash-lite-latest",  # gemini-3.1-flash-lite
    "gemma-4-31b-it",            # Gemma 4 31B instruction-tuned
    "gemma-4-26b-a4b-it",        # Gemma 4 26B MoE instruction-tuned
]


GEMINI_MCQ_PROMPT = """You are helping an IB Computer Science teacher create multiple-choice questions for 17-year-old students based ONLY on the provided textbook section text.

Produce up to {n} multiple-choice questions. For EACH question provide these fields:
1. "question_type": always the exact string "multiple_choice".
2. "summary": a concise 2-4 word topic label for analytics (e.g. "CPU Cache Levels").
3. "text": the question shown to the student.
4. "options": a list of 3-5 answer choices (plain strings, NO "A)"/"B)" prefixes).
5. "correct_options": a list of the 0-based indices (into "options") that are correct. Usually ONE index. Occasionally make a question multi-answer (2+ correct indices) where the concept genuinely has several correct facts — clearly signal this in the question text (e.g. "Select all that apply").
6. "difficulty": "easy", "medium", or "hard".
7. "marks": 1 for easy, 2 for medium, 2-3 for hard.
8. "explanation": 1-2 sentences explaining why the correct option(s) are right and a common misconception, shown after the student answers.

Rules:
- Only test concepts actually taught in the SECTION TEXT below. No outside trivia.
- Distractors must be plausible but clearly wrong to someone who understood the section.
- Vary the position of the correct option; do not always make it the first choice.
- Respond with ONLY valid JSON inside a fenced ```json code block.
- At most {n} questions inside the "questions" list.

Shape:
```json
{{
  "questions": [
    {{
      "question_type": "multiple_choice",
      "summary": "Cache Purpose",
      "text": "Why does a CPU use cache memory?",
      "options": ["To store data closer and faster than main memory", "To permanently save files", "To connect to the internet", "To increase screen resolution"],
      "correct_options": [0],
      "difficulty": "easy",
      "marks": 1,
      "explanation": "Cache is small, fast memory near the CPU, so frequently used data is fetched in fewer clock cycles than RAM. It is volatile, not permanent storage."
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


def generate_for_page(client, model_pool, current_model_idx, book_folder, page_id, page_title, page_text, n):
    """Call Gemini/Gemma with automatic fallback rotation across model_pool.

    Prepends the generated MCQs to the top of the page's existing questions."""
    prompt = GEMINI_MCQ_PROMPT.format(n=n, title=page_title, text=page_text[:24000])

    max_retries = 3
    attempt = 1
    response = None
    while attempt <= max_retries:
        model_name = model_pool[current_model_idx]
        try:
            print(f"       🧠 Sending request (`{model_name}`)... (Attempt {attempt}/{max_retries})")
            start_time = time.time()
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.4,
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

    if response is None:
        raise ValueError("No response from any model")

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

    # Force question_type and cap at n so a chatty model can't over-generate.
    questions = payload.get("questions") if isinstance(payload, dict) else None
    if not isinstance(questions, list) or not questions:
        raise ValueError("Response contained no questions")
    for q in questions:
        if isinstance(q, dict):
            q["question_type"] = "multiple_choice"
    payload["questions"] = questions[:n]

    # Validate and PREPEND to the top of the page's existing questions.
    count, err = _save_questions_payload(book_folder, page_id, payload, prepend=True)
    if err:
        raise ValueError(f"Validation failed during DB import: {err}")

    return count, current_model_idx


def main():
    parser = argparse.ArgumentParser(description="Batch auto-generate MULTIPLE-CHOICE quiz questions with Gemini API.")
    parser.add_argument("--book", default="Book_93", help="Book folder name in data/ (default: Book_93)")
    parser.add_argument("--model", default="gemini-flash-latest", help="Gemini model to use (default: gemini-flash-latest)")
    parser.add_argument("--delay", type=float, default=6.0, help="Delay in seconds between requests to throttle usage (default: 6.0s)")
    parser.add_argument("--n", type=int, default=5, help="Max MCQs to generate per page (default: 5)")
    parser.add_argument("--limit", type=int, default=0, help="Stop after generating for this many pages (0 = no limit)")
    args = parser.parse_args()

    n_per_page = max(1, min(args.n, 5))

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("❌ Error: GEMINI_API_KEY not found in .env file.")
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    print_header(f"BATCH MCQ GENERATOR: {args.book}")
    print(f" ⚙️  Model:      {args.model}")
    print(f" ⚙️  Throttle:   {args.delay}s delay between requests")
    print(f" ⚙️  Per page:   up to {n_per_page} MCQs (prepended to existing questions)")
    print_divider()

    with app.app_context():
        book_title, pages_dict = _book_meta(args.book)
        if not pages_dict:
            print(f"❌ Error: Could not find or read pages for book '{args.book}' in data/{args.book}/book.json")
            sys.exit(1)

        total_pages = len(pages_dict)
        print(f" 📖 Book Title: {book_title}")
        print(f" 📄 Total Pages in Book: {total_pages}")

        # Pre-scan which pages already have any question, and which already have MCQ.
        any_counts = {}
        mcq_counts = {}
        for q in QuizQuestion.query.filter_by(book_folder=args.book).all():
            any_counts[q.page_id] = any_counts.get(q.page_id, 0) + 1
            if q.question_type == "multiple_choice":
                mcq_counts[q.page_id] = mcq_counts.get(q.page_id, 0) + 1

        print(f" ✓  Pages with a quiz:        {len(any_counts)}")
        print(f" 🔘 Pages already with MCQ:   {len(mcq_counts)}")
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

            # Skip pages that already have MCQ.
            if mcq_counts.get(page_id, 0) > 0:
                print(f"          Status:  ⏭️  Already has {mcq_counts[page_id]} MCQ. Skipping!")
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
                    n=n_per_page,
                )
                print(f"          Status:  ✅ SUCCESS! Prepended {count} MCQ.")
                generated_count += 1

                if args.limit > 0 and generated_count >= args.limit:
                    print(f"\n🎯 Reached requested limit of {args.limit} pages.")
                    break

                # Throttle delay
                if idx < total_pages:
                    print(f"          ⏱️  Throttling: sleeping {args.delay}s before next page to respect API quotas...")
                    time.sleep(args.delay)

            except Exception as e:
                print(f"          Status:  ❌ ERROR generating MCQ: {e}")
                error_count += 1
                time.sleep(2)  # brief pause after error

        print_header("MCQ GENERATION SUMMARY")
        print(f" ✅ Pages Generated Now: {generated_count}")
        print(f" ⏭️  Pages Skipped:       {skipped_count}")
        print(f" ❌ Pages Errored:       {error_count}")
        print_divider()
        print("Done!")


if __name__ == "__main__":
    main()
