"""LLM generation for teacher content authoring (flashcards & quiz questions).

Uses Claude (Anthropic API). Reads the key from the
ANTHROPIC_API_KEY environment variable — never hardcode a key here.

Design constraints (agreed 2026-07-16):
- Teacher-triggered only. No student data (names, answers, essays) is ever sent.
- IA/EE draft feedback is deliberately NOT implemented, for academic-integrity
  reasons. Do not add it here.
- Single call site so the provider can be swapped later without touching the app.

Student-side answer feedback lives separately in quiz_routes.gemini_second_opinion.
"""
import json
import os
import re

import anthropic

MODEL = os.environ.get("AI_MODEL", "claude-opus-4-8")
MAX_PAGE_CHARS = 24000  # ~6k tokens of page text is plenty for card/question generation


class AIGenerationError(Exception):
    """Raised with a user-readable message when generation cannot run."""


QUESTIONS_PROMPT = """You are helping a teacher create a 9-question quiz for an IB Computer Science section.

**Difficulty distribution for 9 questions:**
- Easy (4 questions): Identify, Define, State — 1 mark each. Discrete answers, no explanation needed.
- Medium (3 questions): Outline, Describe, Explain — 2–3 marks each. Require brief explanation.
- Hard (2 questions): Compare, Contrast, Analyze, Evaluate, Justify, To What Extent — 4–5 marks each. Require synthesis or evaluation.

**Marks assignment rules:**
- Does the question require only recall? → 1 mark (easy)
- Does it require brief explanation or short comparison? → 2–3 marks (medium)
- Does it require analysis, evaluation, synthesis, or discussion of multiple perspectives/implications? → 4–5 marks (hard)
- Assign marks based on COMPLEXITY, not just the command term. A complex "Describe" can be 3 marks; a simple "Evaluate" can be 4 marks.

For each question:
- "command": the IB command term (e.g. "Define", "Explain")
- "summary": a brief phrase (e.g. "CPU Cache Levels", "Cache vs Main Memory")
- "text": the full question
- "marks": total marks for this question (1-2 for easy, 3-4 for medium, 5-7 for hard)
- "markscheme": detailed, with explicit [1 mark], [2 mark] tags for each point. e.g. "Cache is fast memory [1 mark]. Located near CPU [1 mark]. Stores frequently accessed data [1 mark]."
- "keywords": list of keyword groups; each group lists interchangeable phrases that, if one appears in the answer, count toward that point. Keep this aligned with the markscheme points. E.g. [["cache", "fast memory"], ["CPU", "processor"], ["frequently used data", "hot data"]]

Total marks across all 10 questions should be balanced: aim for ~30–40 total marks.

Rules:
- Only include concepts actually taught in this section.
- Vary the question types and topics to cover the section comprehensively.
- **CRITICAL: Follow the distribution EXACTLY** — 4 easy (1 mark), 3 medium (2-3 marks), 2 hard (4-5 marks). No more, no less.
- **CRITICAL: Marks must reflect actual complexity.** A question about implications/synthesis/evaluation should be 4-5 marks even if the command term is "Outline" or "Describe". A simple recall question should be 1 mark.
- Do NOT include any of these terms that already have cards: {existing}

Respond with ONLY valid JSON with exactly 9 questions (4 easy, 3 medium, 2 hard):
{{
  "questions": [
    {{
      "command": "Define",
      "summary": "Cache Memory",
      "text": "Define cache memory.",
      "marks": 1,
      "difficulty": "easy",
      "markscheme": "Small, fast memory located close to the CPU [1 mark].",
      "keywords": [["cache", "fast memory", "memory"], ["CPU", "processor", "close", "near"]]
    }},
    {{
      "command": "Analyze",
      "summary": "Environmental Impact of Memory",
      "text": "Analyze the environmental and social implications of manufacturing primary memory.",
      "marks": 4,
      "difficulty": "hard",
      "markscheme": "Requires mining/extraction of rare elements causing environmental damage [1 mark]. Social impact: poor labor conditions in developing countries [1 mark]. Scale/extent of impact [1 mark]. Connection to specification requirements [1 mark].",
      "keywords": [["mining", "extraction", "rare earth", "resources"], ["environmental", "pollution", "damage", "depletion"], ["labor", "social", "conditions", "ethical"], ["implications", "effects", "impact"]]
    }},
    ...
  ]
}}

SECTION TITLE: {title}

SECTION TEXT:
{text}"""


def generate_json(prompt, max_output_tokens=8192):
    """Run one Claude generation call and return the parsed JSON object."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise AIGenerationError(
            "ANTHROPIC_API_KEY is not set. Add your Anthropic API key to the server "
            "environment to enable AI generation."
        )

    try:
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model=MODEL,
            max_tokens=max_output_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.APIStatusError as e:
        if e.status_code == 401:
            raise AIGenerationError("The Anthropic API key was rejected — check ANTHROPIC_API_KEY.")
        if e.status_code == 429:
            raise AIGenerationError("Rate limited by Claude — wait a minute and try again.")
        raise AIGenerationError(f"Claude API error ({e.status_code}): {str(e)[:200]}")
    except anthropic.APIConnectionError:
        raise AIGenerationError("Could not reach Claude — check the server's internet connection.")

    try:
        text = resp.content[0].text
    except (IndexError, AttributeError):
        raise AIGenerationError("Claude returned an unexpected response — try again.")

    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except ValueError:
        raise AIGenerationError("Claude returned malformed JSON — try again.")


FLASHCARD_PROMPT = """You are helping a teacher create flashcards for a section of an IB Computer Science textbook.

Read the section text below and produce {n} flashcards covering its key terms and concepts. For each card:
- "term": the concept name as a student would need to recall it — short (1-5 words).
- "definition": a precise, student-friendly definition in 1-3 sentences. It must be understandable on its own, without the section in front of the student.

Rules:
- Only include concepts actually taught in this section — no background trivia.
- Definitions must be accurate for IB Computer Science; prefer the section's own wording where it is precise.
- Do NOT include any of these terms that already have cards: {existing}

Respond with ONLY valid JSON, exactly this shape:
{{
  "cards": [
    {{"term": "Cache", "definition": "Small, very fast memory located on or near the CPU that stores frequently used data and instructions so they can be accessed in fewer clock cycles than main memory."}}
  ]
}}

SECTION TITLE: {title}

SECTION TEXT:
{text}"""


SUMMARY_PROMPT = """You are helping a teacher write a short overview of one section of an IB Computer Science textbook, shown to 17-year-old students in their progress dashboard.

Read the section text below and write a summary of what this page teaches in 30-50 words. Rules:
- Plain, friendly language a busy student can skim — no bullet points, one short paragraph.
- Say what the page covers and why it matters, not "this page describes...". Start straight in, e.g. "The CPU's control unit, ALU and registers work together to..."
- Only include what the section actually teaches.

Respond with ONLY valid JSON, exactly this shape:
{{"summary": "..."}}

SECTION TITLE: {title}

SECTION TEXT:
{text}"""


def generate_page_summary(page_title, page_text):
    """Generate a 30-50 word student-facing overview of one page."""
    prompt = SUMMARY_PROMPT.format(
        title=page_title or "Untitled section",
        text=(page_text or "")[:MAX_PAGE_CHARS],
    )
    data = generate_json(prompt, max_output_tokens=300)
    summary = str(data.get("summary") or "").strip() if isinstance(data, dict) else ""
    if not summary:
        raise AIGenerationError("The AI did not return a usable summary — try again.")
    return summary[:600]


def generate_questions(page_title, page_text, existing_terms=None):
    """Generate 10 questions of varying difficulty with marks and summaries."""
    existing = ", ".join(sorted(existing_terms)) if existing_terms else "(none)"
    prompt = QUESTIONS_PROMPT.format(
        title=page_title or "Untitled section",
        text=(page_text or "")[:MAX_PAGE_CHARS],
        existing=existing,
    )
    data = generate_json(prompt)
    questions = []
    for q in data.get("questions", []) if isinstance(data, dict) else []:
        text = str(q.get("text") or "").strip()
        markscheme = str(q.get("markscheme") or "").strip()
        summary = str(q.get("summary") or "").strip()
        marks = q.get("marks")
        command = str(q.get("command") or "").strip()
        keywords = q.get("keywords", [])
        if text and markscheme and marks:
            difficulty = "easy" if marks <= 2 else "medium" if marks <= 4 else "hard"
            questions.append({
                "text": text,
                "markscheme": markscheme,
                "summary": summary,
                "marks": int(marks),
                "difficulty": difficulty,
                "command": command,
                "keywords": keywords if isinstance(keywords, list) else [],
            })
    if not questions:
        raise AIGenerationError("Claude did not return any usable questions — try again.")
    return questions


MCQ_PROMPT = """You are helping an IB Computer Science teacher create multiple-choice questions for a section, for 17-year-old students, based ONLY on the provided textbook section text.

Produce up to {n} multiple-choice questions. For EACH question provide:
- "summary": a concise 2-4 word topic label for analytics (e.g. "CPU Cache Levels").
- "text": the question shown to the student.
- "options": a list of 3-5 answer choices (plain strings, no "A)"/"B)" prefixes).
- "correct_options": a list of the indices (0-based, into "options") that are correct. Usually ONE index. Occasionally make a question multi-answer (2+ correct indices) where the concept genuinely has several correct facts — clearly signal this in the question text (e.g. "Select all that apply").
- "difficulty": "easy", "medium", or "hard".
- "marks": 1 for easy, 2 for medium, 2-3 for hard.
- "explanation": 1-2 sentences explaining why the correct option(s) are right and a common misconception, shown to the student after they answer.

Rules:
- Only test concepts actually taught in the SECTION TEXT below.
- Distractors must be plausible but clearly wrong to someone who understood the section.
- Vary the position of the correct option; don't always make it the first choice.
- Respond with ONLY valid JSON, exactly this shape:
{{
  "questions": [
    {{
      "summary": "Cache Purpose",
      "text": "Why does a CPU use cache memory?",
      "options": ["To store data closer and faster than main memory", "To permanently save files", "To connect to the internet", "To increase screen resolution"],
      "correct_options": [0],
      "difficulty": "easy",
      "marks": 1,
      "explanation": "Cache is small, fast memory near the CPU, so frequently used data is fetched in fewer clock cycles than from RAM. It is volatile, not permanent storage."
    }}
  ]
}}

SECTION TITLE: {title}

SECTION TEXT:
{text}"""


def generate_mcq_questions(page_title, page_text, n=5):
    """Generate up to n multiple-choice questions (single- and multi-answer) from page text.

    Returns payload items already shaped for _save_questions_payload
    (question_type == "multiple_choice")."""
    prompt = MCQ_PROMPT.format(
        n=max(1, min(int(n or 5), 10)),
        title=page_title or "Untitled section",
        text=(page_text or "")[:MAX_PAGE_CHARS],
    )
    data = generate_json(prompt)
    questions = []
    for q in data.get("questions", []) if isinstance(data, dict) else []:
        text = str(q.get("text") or "").strip()
        options = q.get("options")
        correct = q.get("correct_options")
        if not text or not isinstance(options, list) or len(options) < 2:
            continue
        options = [str(o).strip() for o in options if str(o).strip()]
        if len(options) < 2 or not isinstance(correct, list) or not correct:
            continue
        try:
            correct = sorted({int(c) for c in correct})
        except (ValueError, TypeError):
            continue
        if any(c < 0 or c >= len(options) for c in correct):
            continue
        marks = q.get("marks")
        try:
            marks = max(1, min(int(marks), 5))
        except (ValueError, TypeError):
            marks = 1
        difficulty = str(q.get("difficulty") or "medium").strip().lower()
        if difficulty not in ("easy", "medium", "hard"):
            difficulty = "medium"
        questions.append({
            "question_type": "multiple_choice",
            "text": text,
            "options": options,
            "correct_options": correct,
            "summary": str(q.get("summary") or "").strip(),
            "difficulty": difficulty,
            "marks": marks,
            "explanation": str(q.get("explanation") or "").strip(),
        })
    if not questions:
        raise AIGenerationError("Claude did not return any usable multiple-choice questions — try again.")
    return questions[:max(1, min(int(n or 5), 10))]


def generate_flashcards(page_title, page_text, n=10, existing_terms=None):
    """Generate flashcard candidates from page text. Returns [{term, definition}]."""
    existing = ", ".join(sorted(existing_terms)) if existing_terms else "(none)"
    prompt = FLASHCARD_PROMPT.format(
        n=max(1, min(int(n or 10), 30)),
        existing=existing,
        title=page_title or "Untitled section",
        text=(page_text or "")[:MAX_PAGE_CHARS],
    )
    data = generate_json(prompt)
    cards = []
    for c in data.get("cards", []) if isinstance(data, dict) else []:
        term = str(c.get("term") or "").strip()
        definition = str(c.get("definition") or "").strip()
        if term and definition:
            cards.append({"term": term, "definition": definition})
    if not cards:
        raise AIGenerationError("Gemini did not return any usable cards — try again.")
    return cards
