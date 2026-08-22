"""Section quizzes: AI-assisted question authoring, student short answers,
provisional auto-marking (keyword match + optional Gemini second opinion),
and a teacher review queue."""

import json
import os
import re
from datetime import datetime
from pathlib import Path

from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from auth import admin_required
from extensions import db
from models import Class, ClassEnrollment, QuizAnswer, QuizQuestion, User

quiz_bp = Blueprint("quiz", __name__)


# ---------------------------------------------------------------- helpers

def _load_page_content(book_folder, page_id):
    """Load a page's content.json (standard book page or single-page folder)."""
    for candidate in (
        Path("data") / book_folder / page_id / "content.json",
        Path("data") / book_folder / "content.json" if page_id == "content" else None,
    ):
        if candidate and candidate.exists():
            try:
                with open(candidate, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (ValueError, OSError):
                pass
    # Renamed page folders: resolve via the scraper's lookup
    try:
        from scraper import ContentScraper
        content = ContentScraper(data_dir="data").get_page_content(book_folder, page_id)
        if content:
            return content
    except Exception:
        pass
    return None


def _book_meta(book_folder, memo=None):
    """(book_title, {page_id: page_title}) from the book's book.json.
    Pass a dict as memo to avoid re-reading within one request."""
    if memo is not None and book_folder in memo:
        return memo[book_folder]
    title, pages = book_folder, {}
    book_file = Path("data") / book_folder / "book.json"
    if book_file.exists():
        try:
            with open(book_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            title = data.get("title") or book_folder
            pages = {p["id"]: p.get("title") or p["id"] for p in data.get("pages", []) if p.get("id")}
        except (ValueError, OSError):
            pass
    result = (title, pages)
    if memo is not None:
        memo[book_folder] = result
    return result


def _effective_mark(ans):
    """The mark that currently counts: teacher's if reviewed, else provisional."""
    return ans.final_correct if ans.status == "reviewed" else ans.auto_correct


def _page_title(content, page_id):
    if not content:
        return page_id
    return content.get("main_heading") or content.get("title") or page_id


def _extract_page_text(content):
    """Flatten a page's readable text for pasting into an AI."""
    parts = []
    for block in content.get("blocks", []):
        btype = block.get("type")
        if btype in ("heading", "text"):
            parts.append(block.get("text", ""))
        elif btype == "sidebox":
            title = block.get("title", "")
            parts.append(f"[{title}] {block.get('text', '')}" if title else block.get("text", ""))
    if not parts:
        if content.get("main_heading"):
            parts.append(content["main_heading"])
        for title, text in content.get("main_content", {}).items():
            parts.append(text if title.startswith(("Main Content", "__heading_")) else f"{title}\n{text}")
        for name, text in content.get("sidebar_sections", {}).items():
            parts.append(f"[{name}] {text}")
    # Strip any HTML tags that survived scraping
    text = "\n\n".join(p for p in parts if p)
    return re.sub(r"<[^>]+>", " ", text)


AI_PROMPT_TEMPLATE = """You are helping a teacher write short-answer quiz questions for a section of an IB course textbook.

Read the section text below, then produce {n} short-answer questions that test understanding of its key ideas (not trivia). For each question provide:
- "text": the question as shown to the student. If a question uses terminology that is new in this section (introduced here rather than assumed prior knowledge), include a brief explanation of the term in the question itself, e.g. "The ALU (the component that performs arithmetic and logic operations) ..." — the question must be answerable without the student having to guess what a term means.
- "summary": a brief phrase (1-3 words) that appears in quiz analytics to label what this question tests (e.g. "Database Schema", "ALU Function"). Should be readable at a glance.
- "marks": the total marks for this question (1-7). Award more marks for questions requiring complex reasoning or detailed explanations.
- "markscheme": a clear model answer / marking notes for the teacher and student. This should be detailed enough that an AI can use it to evaluate student answers and explain feedback. Include the key ideas that must be present in a correct answer. Use [1 mark], [2 mark] tags to show point breakdown (e.g. "Schema defines structure [1 mark]. Ensures consistency [1 mark].").
- "explanation": a simple, student-friendly explanation (2-3 sentences for IB beginners). Use simple language and focus on ONE key idea—why this matters or what students often get wrong. Avoid technical jargon beyond what was introduced in the section. Keep it concise and memorable.
- "keywords": keyword groups used for provisional auto-marking. This is a list of groups; each group is a list of interchangeable phrases. An answer is provisionally marked correct only if it contains at least one phrase from EVERY group.

Keyword rules — these matter, because a correct answer that misses a keyword gets provisionally marked wrong:
- Use as FEW groups as possible: one group per idea that is genuinely essential to the mark, usually only 1-2 groups. Everything else should be omitted.
- Each group must be EXHAUSTIVE: 6-12 alternatives covering every way a student might express the idea — synonyms, informal wording, comparatives and their stems. E.g. for speed: "faster", "fast", "quicker", "quick", "speedier", "rapid", "less time", "reduce delay", "lower latency", "more quickly".
- Prefer single words or word stems over phrases: "quick" matches "quicker" and "quickly" would not — so include each inflection you want matched, or the shortest common stem that is itself a word.
- All lowercase, no punctuation inside phrases.

Respond with a single fenced ```json code block and nothing else — no commentary before or after the block. The JSON must be exactly this shape:
{{
  "questions": [
    {{
      "text": "Why is cache faster to access than RAM?",
      "summary": "Cache vs RAM Speed",
      "marks": 2,
      "markscheme": "Cache is physically located on or close to the CPU core [1 mark], which means data retrieval takes fewer clock cycles compared to main memory [1 mark].",
      "explanation": "Cache is like a tiny, super-fast notebook the CPU keeps next to itself. Because it's so close and small, the CPU can grab information from it much faster than reaching all the way to RAM. That's why computers need it.",
      "keywords": [["closer", "close", "near", "nearer", "on the cpu", "on chip", "proximity", "next to the cpu", "inside the cpu"], ["faster", "fast", "quicker", "quick", "quickly", "speed", "speedier", "less time", "fewer cycles", "lower latency", "rapid"]]
    }}
  ]
}}

SECTION TITLE: {title}

SECTION TEXT:
{text}"""


def _normalise(text):
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _phrase_in(phrase, norm_answer):
    """Match a phrase against a normalised answer. The final word of the phrase
    matches as a stem (>=4 chars), so "quick" also matches "quicker"/"quickly"."""
    if not phrase:
        return False
    if " " + phrase + " " in norm_answer:
        return True
    if len(phrase.split()[-1]) >= 4:
        return bool(re.search(r"(?:^| )" + re.escape(phrase) + r"[a-z]*(?: |$)", norm_answer.strip()))
    return False


def keyword_match(answer_text, keyword_groups):
    """True if every keyword group has at least one phrase in the answer.
    Returns None when there are no usable keyword groups."""
    norm = " " + _normalise(answer_text) + " "
    usable = [g for g in keyword_groups if isinstance(g, list) and g]
    if not usable:
        return None
    for group in usable:
        if not any(_phrase_in(_normalise(p), norm) for p in group):
            return False
    return True


def gemini_second_opinion(question_text, markscheme, answer_text):
    """Ask Claude whether the answer deserves the mark. Returns (correct, reason, explanation)
    or None if unavailable/failed.

    When correct=false, explanation provides detailed feedback on what the student missed."""
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    prompt = (
        "You are marking a 17-year-old student's short answer. The teacher will review your decision.\n\n"
        f"QUESTION: {question_text}\n"
        f"MARKSCHEME: {markscheme}\n"
        f"STUDENT ANSWER: {answer_text}\n\n"
        "Award the mark if the answer shows they understand the key idea, even if worded differently. "
        "Do not award it if they're just restating the question or being vague.\n\n"
        "If INCORRECT: Give friendly, simple feedback (1-2 sentences) about what they missed. "
        "Use simple words and focus on ONE thing they should remember next time. "
        "Wrap the key term or concept they missed in **double asterisks**, e.g. **cache memory**.\n"
        "If CORRECT: Just say 'well done' or briefly explain why it's good.\n\n"
        'Respond with ONLY valid JSON: {"correct": true/false, "reason": "one short sentence", '
        '"explanation": "simple, friendly feedback for a 17-year-old"}'
    )
    try:
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text
        raw = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
        verdict = json.loads(raw)
        if isinstance(verdict.get("correct"), bool):
            return (
                verdict["correct"],
                str(verdict.get("reason", ""))[:500],
                str(verdict.get("explanation", ""))[:1000]
            )
    except Exception:
        pass
    return None


def claude_improvement_feedback(question_text, markscheme, answer_text):
    """For an answer that earned the mark, ask Claude how the student could
    strengthen it. Returns markdown with **bold** improvement points, or None.

    Uses prompt caching to reduce token usage across multiple student answers.
    Cache stats are logged for monitoring efficiency."""
    from student_feedback import get_improvement_feedback

    feedback, cache_stats = get_improvement_feedback(
        question_text=question_text,
        markscheme=markscheme,
        answer_text=answer_text,
        log_cache_stats=True
    )
    return feedback


def _parse_markscheme_points(markscheme):
    """Extract mark points from markscheme text.
    Looks for patterns like "[1 mark]", "[2 marks]", etc.
    Handles both line-based and inline formats.
    Returns list of (point_text, mark_value) tuples."""
    points = []
    if not markscheme:
        return points

    # Try splitting by period + [n mark] pattern (sentence-based format)
    # E.g. "Defines structure [1 mark]. Explains function [2 marks]."
    sentence_pattern = r'([^.\[\]]+)\s*\[\s*(\d+)\s+marks?\s*\]\.?\s*'
    matches = re.findall(sentence_pattern, markscheme, re.IGNORECASE)
    if matches:
        for text, mark_val in matches:
            point_text = text.strip()
            if point_text:
                points.append((point_text, int(mark_val)))
        return points

    # Fallback: split by lines and extract marks
    lines = markscheme.split('\n')
    for line in lines:
        match = re.search(r'\[(\d+)\s+marks?\]', line, re.IGNORECASE)
        if match:
            mark_val = int(match.group(1))
            point_text = re.sub(r'\s*\[\d+\s+marks?\]\s*', '', line, flags=re.IGNORECASE).strip()
            if point_text:
                points.append((point_text, mark_val))

    return points


def claude_partial_mark(question_text, markscheme, answer_text, max_marks):
    """Ask Claude to evaluate the answer against mark points in the markscheme.
    Returns (marks_awarded, formatted_feedback) or (None, None) if unavailable.

    Feedback includes "[1 Mark]" tags (in green) next to earned points."""
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None, None

    mark_points = _parse_markscheme_points(markscheme)
    if not mark_points:
        # Fallback: if no mark points found in markscheme, use binary marking
        return None, None

    points_str = "\n".join(f"- [{pt[1]} mark{'s' if pt[1] > 1 else ''}] {pt[0]}"
                           for pt in mark_points)
    total = sum(pt[1] for pt in mark_points)

    prompt = (
        "You are marking a 17-year-old student's short answer for a quiz. "
        "Evaluate which mark points they have earned based on their answer.\n\n"
        f"QUESTION: {question_text}\n\n"
        f"MARK POINTS (total {total} marks):\n{points_str}\n\n"
        f"STUDENT ANSWER: {answer_text}\n\n"
        "For each mark point, decide if the student's answer adequately addresses it. "
        "Award the mark only if they show understanding of that specific point. "
        "Be generous but fair — they don't need to use exact words, just show they understand.\n\n"
        "Respond with ONLY valid JSON in this format:\n"
        "{\n"
        '  "points_earned": [{"point_index": 0, "earned": true, "reason": "brief explanation"}, ...],\n'
        '  "total_marks_awarded": 3,\n'
        '  "overall_feedback": "1-2 sentence summary of what they did well and what to improve"\n'
        "}"
    )
    try:
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text
        raw = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
        verdict = json.loads(raw)

        marks_awarded = verdict.get("total_marks_awarded")
        if not isinstance(marks_awarded, int) or marks_awarded < 0 or marks_awarded > total:
            marks_awarded = None

        # Build formatted feedback with [1 Mark] tags
        points_earned = verdict.get("points_earned", [])
        feedback_lines = []
        for i, (pt_text, pt_marks) in enumerate(mark_points):
            earned = any(pe.get("point_index") == i and pe.get("earned")
                        for pe in points_earned if isinstance(pe, dict))
            mark_tag = f" [1 Mark]" if earned else ""
            feedback_lines.append(f"• {pt_text}{mark_tag}")

        overall = str(verdict.get("overall_feedback", ""))[:500]
        formatted_feedback = "\n".join(feedback_lines)
        if overall:
            formatted_feedback += f"\n\n{overall}"

        return marks_awarded, formatted_feedback

    except Exception:
        pass
    return None, None


def _answer_payload(ans, question):
    payload = {
        "answer_id": ans.id,
        "attempt_number": ans.attempt_number,
        "answer_text": ans.answer_text,
        "auto_correct": ans.auto_correct,
        "auto_method": ans.auto_method,
        "auto_note": ans.auto_note,
        "final_correct": ans.final_correct,
        "status": ans.status,
        "markscheme": question.markscheme,
        "feedback": ans.auto_note or ans.feedback,  # AI-generated feedback for incorrect answers
        "marks_awarded": ans.marks_awarded,
        "question_marks": question.marks,
    }
    if question.is_multiple_choice():
        # Safe to reveal the correct options — only returned after the student answered.
        payload["question_type"] = "multiple_choice"
        payload["options"] = question.options_list()
        payload["correct_options"] = question.correct_indices()
        payload["selected_options"] = _selected_indices(ans.answer_text, question.options_list())
        payload["explanation"] = question.explanation
    return payload


def _selected_indices(answer_text, options):
    """Recover the option indices a student picked from the stored readable answer.

    MCQ answers are stored as the chosen option texts joined by ' | '. Map each
    back to its index in the question's options."""
    if not answer_text:
        return []
    chosen = [seg.strip() for seg in answer_text.split(" | ") if seg.strip()]
    indices = []
    for i, opt in enumerate(options):
        if opt in chosen:
            indices.append(i)
    return indices


# ---------------------------------------------------------------- student pages

@quiz_bp.route("/book/<book_folder>/quiz/<page_id>")
@login_required
def quiz_page(book_folder, page_id):
    if current_user.is_admin():
        return redirect(url_for("quiz.quiz_manage", book_folder=book_folder, page_id=page_id))
    content = _load_page_content(book_folder, page_id)
    return render_template(
        "quiz.html",
        book_folder=book_folder,
        page_id=page_id,
        page_title=_page_title(content, page_id),
    )


@quiz_bp.route("/api/quiz/<book_folder>/<page_id>/questions")
@login_required
def quiz_questions(book_folder, page_id):
    """Questions for a page. Students also get their own answers; the
    markscheme is only included once the student has answered."""
    questions = (
        QuizQuestion.query.filter_by(book_folder=book_folder, page_id=page_id)
        .order_by(QuizQuestion.position, QuizQuestion.id)
        .all()
    )
    is_admin = current_user.is_admin()
    answers = {}
    if not is_admin and questions:
        # Ascending attempt order so the dict keeps each question's LATEST attempt
        rows = (
            QuizAnswer.query.filter(
                QuizAnswer.student_id == current_user.id,
                QuizAnswer.question_id.in_([q.id for q in questions]),
            )
            .order_by(QuizAnswer.attempt_number)
            .all()
        )
        answers = {r.question_id: r for r in rows}

    out = []
    for q in questions:
        item = {"id": q.id, "text": q.text, "question_type": q.question_type, "marks": q.marks}
        if q.is_multiple_choice():
            # Options are needed to render the choices; multi_select drives
            # radios vs checkboxes. The correct answers are NOT sent until the
            # student has answered (below) or to admins.
            item["options"] = q.options_list()
            item["multi_select"] = q.is_multi_select()
        if is_admin:
            item["markscheme"] = q.markscheme
            item["explanation"] = q.explanation
            item["summary"] = q.summary
            item["difficulty"] = q.difficulty
            item["keywords"] = q.keyword_groups()
            if q.is_multiple_choice():
                item["correct_options"] = q.correct_indices()
        ans = answers.get(q.id)
        if ans:
            item["answer"] = _answer_payload(ans, q)
        out.append(item)
    return jsonify({"questions": out})


@quiz_bp.route("/api/quiz/answer", methods=["POST"])
@login_required
def submit_answer():
    if current_user.is_admin():
        return jsonify({"error": "Admins cannot submit answers"}), 403

    data = request.get_json(force=True, silent=True) or {}
    question_id = data.get("question_id")
    if not question_id:
        return jsonify({"error": "question_id required"}), 400

    question = QuizQuestion.query.get(question_id)
    if not question:
        return jsonify({"error": "Question not found"}), 404

    # Multiple-choice is auto-marked instantly and finally — no AI/teacher review.
    if question.is_multiple_choice():
        return _submit_mcq_answer(question, data)

    answer_text = (data.get("answer_text") or "").strip()
    if not answer_text:
        return jsonify({"error": "answer_text required"}), 400
    if len(answer_text) > 5000:
        return jsonify({"error": "Answer too long"}), 400

    # Get highest attempt number for this student+question to allow retakes
    highest_attempt = db.session.query(db.func.max(QuizAnswer.attempt_number)).filter_by(
        question_id=question.id, student_id=current_user.id
    ).scalar()
    attempt_number = (highest_attempt or 0) + 1

    # 1. Keyword match
    matched = keyword_match(answer_text, question.keyword_groups())
    auto_correct, auto_method, auto_note = matched, "keyword", None
    marks_awarded = None
    feedback_text = None

    # 2. AI partial marking when keywords give no definitive answer —
    #    evaluates answer against mark points in the markscheme and allocates partial marks.
    if matched is not True:
        marks_awarded, feedback_text = claude_partial_mark(
            question.text, question.markscheme, answer_text, question.marks
        )
        if feedback_text is not None:
            auto_note = feedback_text
            auto_method = "partial_mark"
            # Determine auto_correct based on marks awarded
            if marks_awarded is not None:
                auto_correct = marks_awarded == question.marks
            else:
                auto_correct = None
        else:
            # Fallback to gemini_second_opinion if partial_mark unavailable
            opinion = gemini_second_opinion(question.text, question.markscheme, answer_text)
            if opinion is not None:
                auto_correct, reason, explanation = opinion
                auto_note = f"{reason}\n\n{explanation}" if explanation else reason
                auto_method = "gemini"
                # For binary marking, award full marks if correct
                if auto_correct is True:
                    marks_awarded = question.marks
            elif matched is None:
                auto_correct, auto_method = None, "none"

    # 3. If keyword match was true, still use partial marking to get mark breakdown
    elif matched is True and auto_correct is True:
        marks_awarded, feedback_text = claude_partial_mark(
            question.text, question.markscheme, answer_text, question.marks
        )
        if feedback_text is not None:
            auto_note = feedback_text
        else:
            # Fallback: if partial mark fails, award full marks for keyword match
            marks_awarded = question.marks

    # 4. If no marks awarded yet but auto_correct is True, award full marks
    if auto_correct is True and marks_awarded is None:
        marks_awarded = question.marks

    ans = QuizAnswer(
        question_id=question.id,
        student_id=current_user.id,
        attempt_number=attempt_number,
        answer_text=answer_text,
        auto_correct=auto_correct,
        auto_method=auto_method,
        auto_note=auto_note,
        marks_awarded=marks_awarded,
        status="pending",
    )
    db.session.add(ans)
    db.session.commit()

    # Record weakness themes from the AI feedback on every attempt (retakes
    # included) — even a provisionally-correct answer can reveal gaps, via
    # the bold phrases in its "how to improve" note.
    if ans.auto_note:
        from feedback_utils import store_feedback_insight
        store_feedback_insight(ans, source_text=ans.auto_note)

    return jsonify({"ok": True, "answer": _answer_payload(ans, question)})


def _submit_mcq_answer(question, data):
    """Auto-mark a multiple-choice answer instantly and finally (no AI/teacher review).
    Supports partial credit for multi-select questions: credit per correct option selected.

    The topic of a wrong answer is still fed into the learner-profile pipeline so
    the AI can build a picture of how the student is doing."""
    selected = data.get("selected_options")
    if not isinstance(selected, list):
        return jsonify({"error": "selected_options (a list) is required"}), 400
    options = question.options_list()
    try:
        selected = sorted({int(i) for i in selected})
    except (ValueError, TypeError):
        return jsonify({"error": "selected_options must be a list of integers"}), 400
    if not selected or any(i < 0 or i >= len(options) for i in selected):
        return jsonify({"error": "Please choose a valid option"}), 400

    correct_indices = question.correct_indices()
    correct = (selected == correct_indices)

    # For multi-select, award partial credit: marks per correct option selected.
    # For single-select, it's all-or-nothing.
    if question.is_multi_select() and not correct:
        # Count how many correct options the student selected
        correct_selected = len([i for i in selected if i in correct_indices])
        # Award marks proportionally: (correct_selected / total_correct) * total_marks
        if correct_selected > 0:
            marks_awarded = int((correct_selected / len(correct_indices)) * question.marks)
        else:
            marks_awarded = 0
    else:
        # Single-select or fully correct: all or nothing
        marks_awarded = question.marks if correct else 0

    highest_attempt = db.session.query(db.func.max(QuizAnswer.attempt_number)).filter_by(
        question_id=question.id, student_id=current_user.id
    ).scalar()
    attempt_number = (highest_attempt or 0) + 1

    # Store the chosen option texts (readable for teacher/analytics views).
    answer_text = " | ".join(options[i] for i in selected)

    ans = QuizAnswer(
        question_id=question.id,
        student_id=current_user.id,
        attempt_number=attempt_number,
        answer_text=answer_text,
        auto_correct=correct,
        auto_method="mcq",
        auto_note=None,
        final_correct=correct,
        marks_awarded=marks_awarded,
        status="reviewed",
        reviewed_at=datetime.utcnow(),
    )
    db.session.add(ans)
    db.session.commit()

    # On a wrong answer, log the question's topic as a focus area so the existing
    # profile pipeline surfaces it — the bold phrase becomes an extracted keyword.
    if not correct:
        from feedback_utils import store_feedback_insight
        topic = question.summary or "this concept"
        store_feedback_insight(ans, source_text=f"Review needed: **{topic}**")

    return jsonify({"ok": True, "answer": _answer_payload(ans, question)})


# ---------------------------------------------------------------- teacher: authoring

@quiz_bp.route("/book/<book_folder>/quiz/<page_id>/manage")
@login_required
@admin_required
def quiz_manage(book_folder, page_id):
    content = _load_page_content(book_folder, page_id)
    return render_template(
        "quiz_manage.html",
        book_folder=book_folder,
        page_id=page_id,
        page_title=_page_title(content, page_id),
    )


@quiz_bp.route("/api/quiz/<book_folder>/<page_id>/export-prompt")
@login_required
@admin_required
def export_prompt(book_folder, page_id):
    content = _load_page_content(book_folder, page_id)
    if not content:
        return jsonify({"error": "Page not found"}), 404
    n = request.args.get("n", 5, type=int)
    prompt = AI_PROMPT_TEMPLATE.format(
        n=max(1, min(n, 20)),
        title=_page_title(content, page_id),
        text=_extract_page_text(content),
    )
    return jsonify({"prompt": prompt})


@quiz_bp.route("/api/quiz/<book_folder>/<page_id>/import", methods=["POST"])
@login_required
@admin_required
def import_questions(book_folder, page_id):
    data = request.get_json(force=True, silent=True) or {}
    payload = data.get("json_text")
    if isinstance(payload, str):
        # Tolerate fenced/annotated AI output
        payload = re.sub(r"^```(?:json)?|```$", "", payload.strip(), flags=re.MULTILINE).strip()
        try:
            payload = json.loads(payload)
        except ValueError as e:
            return jsonify({"error": f"Invalid JSON: {e}"}), 400
    count, err = _save_questions_payload(book_folder, page_id, payload, replace=bool(data.get("replace")))
    if err:
        return jsonify({"error": err}), 400
    return jsonify({"ok": True, "imported": count})


def _clean_mcq(i, q):
    """Validate one multiple-choice question dict. Returns (cleaned, error)."""
    options = q.get("options")
    if not isinstance(options, list) or len(options) < 2:
        return None, f'Question {i + 1} (multiple choice) must have an "options" list of at least 2 choices'
    options = [str(o) for o in options]

    correct = q.get("correct_options")
    if not isinstance(correct, list) or not correct:
        return None, f'Question {i + 1} (multiple choice) must have a non-empty "correct_options" index list'
    try:
        correct = sorted({int(c) for c in correct})
    except (ValueError, TypeError):
        return None, f'Question {i + 1} "correct_options" must be a list of integers'
    if any(c < 0 or c >= len(options) for c in correct):
        return None, f'Question {i + 1} has a "correct_options" index outside its options range'

    # Synthesize a readable markscheme so teacher/analytics views that read
    # markscheme keep working for MCQ too.
    markscheme = q.get("markscheme") or "Correct: " + "; ".join(options[c] for c in correct)
    explanation = q.get("explanation", "")
    summary = q.get("summary", "")
    marks = q.get("marks", 1)
    difficulty = q.get("difficulty", "medium")
    return {
        "question_type": "multiple_choice",
        "text": str(q["text"]),
        "markscheme": str(markscheme),
        "explanation": str(explanation) if explanation else None,
        "summary": str(summary) if summary else None,
        "marks": int(marks) if marks else 1,
        "difficulty": str(difficulty) if difficulty else "medium",
        "keywords": [],
        "options": options,
        "correct_options": correct,
    }, None


def _save_questions_payload(book_folder, page_id, payload, replace=False, prepend=False):
    """Validate a {"questions": [...]} payload and save it. Returns (count, error).

    Supports both short-answer and multiple-choice (question_type == "multiple_choice")
    questions. When prepend=True the new questions are inserted at the top of the
    page's list (existing questions shift down); otherwise they are appended."""
    if not isinstance(payload, dict) or not isinstance(payload.get("questions"), list):
        return None, 'JSON must be an object with a "questions" list'

    cleaned = []
    for i, q in enumerate(payload["questions"]):
        if not isinstance(q, dict) or not q.get("text"):
            return None, f'Question {i + 1} must have "text"'

        if q.get("question_type") == "multiple_choice":
            item, err = _clean_mcq(i, q)
            if err:
                return None, err
            cleaned.append(item)
            continue

        if not q.get("markscheme"):
            return None, f'Question {i + 1} must have "text" and "markscheme"'
        keywords = q.get("keywords", [])
        if not isinstance(keywords, list):
            keywords = []
        keywords = [[str(p) for p in g] for g in keywords if isinstance(g, list)]
        explanation = q.get("explanation", "")
        summary = q.get("summary", "")
        marks = q.get("marks", 1)
        difficulty = q.get("difficulty", "medium")
        cleaned.append({
            "question_type": "short_answer",
            "text": str(q["text"]),
            "markscheme": str(q["markscheme"]),
            "explanation": str(explanation) if explanation else None,
            "summary": str(summary) if summary else None,
            "marks": int(marks) if marks else 1,
            "difficulty": str(difficulty) if difficulty else "medium",
            "keywords": keywords,
            "options": None,
            "correct_options": None,
        })

    if replace:
        for q in QuizQuestion.query.filter_by(book_folder=book_folder, page_id=page_id).all():
            db.session.delete(q)  # ORM delete so student answers cascade
        db.session.flush()

    if prepend and not replace:
        # Shift existing questions down so the new ones can take positions 0..n-1.
        n = len(cleaned)
        for q in QuizQuestion.query.filter_by(book_folder=book_folder, page_id=page_id).all():
            q.position = (q.position or 0) + n
        db.session.flush()
        base = 0
    else:
        base = QuizQuestion.query.filter_by(book_folder=book_folder, page_id=page_id).count()

    for i, q in enumerate(cleaned):
        db.session.add(QuizQuestion(
            book_folder=book_folder, page_id=page_id, position=base + i,
            question_type=q["question_type"],
            text=q["text"], markscheme=q["markscheme"], explanation=q["explanation"],
            summary=q["summary"], marks=q["marks"], difficulty=q["difficulty"],
            keywords=json.dumps(q["keywords"]),
            options=json.dumps(q["options"]) if q["options"] is not None else None,
            correct_options=json.dumps(q["correct_options"]) if q["correct_options"] is not None else None,
        ))
    db.session.commit()
    return len(cleaned), None


@quiz_bp.route("/api/quiz/<book_folder>/<page_id>/ai-generate", methods=["POST"])
@login_required
@admin_required
def ai_generate_questions(book_folder, page_id):
    """Generate 10 quiz questions with varying difficulty, marks, and summaries.
    Questions use IB command terms and are automatically graded by marks."""
    from ai_generation import generate_questions, AIGenerationError

    data = request.get_json(force=True, silent=True) or {}
    content = _load_page_content(book_folder, page_id)
    if not content:
        return jsonify({"error": "Page not found"}), 404
    page_text = _extract_page_text(content)
    if not page_text or len(page_text) < 100:
        return jsonify({"error": "This page has too little text to generate questions from"}), 400

    try:
        questions = generate_questions(_page_title(content, page_id), page_text)
    except AIGenerationError as e:
        return jsonify({"error": str(e)}), 502

    # Convert to payload format and save
    payload = {"questions": questions}
    count, err = _save_questions_payload(book_folder, page_id, payload, replace=bool(data.get("replace")))
    if err:
        return jsonify({"error": f"AI output invalid: {err}"}), 502
    return jsonify({"ok": True, "imported": count})


@quiz_bp.route("/api/quiz/question/<int:question_id>", methods=["PUT"])
@login_required
@admin_required
def update_question(question_id):
    question = QuizQuestion.query.get(question_id)
    if not question:
        return jsonify({"error": "Question not found"}), 404
    data = request.get_json(force=True, silent=True) or {}

    text = (data.get("text") or "").strip()
    markscheme = (data.get("markscheme") or "").strip()
    explanation = (data.get("explanation") or "").strip()
    summary = (data.get("summary") or "").strip()
    marks = data.get("marks", 1)
    if not text or not markscheme:
        return jsonify({"error": "text and markscheme are required"}), 400

    keywords = data.get("keywords", [])
    if isinstance(keywords, str):
        try:
            keywords = json.loads(keywords) if keywords.strip() else []
        except ValueError as e:
            return jsonify({"error": f"Invalid keywords JSON: {e}"}), 400
    if not isinstance(keywords, list) or not all(isinstance(g, list) for g in keywords):
        return jsonify({"error": "keywords must be a list of lists of phrases"}), 400
    keywords = [[str(p) for p in g] for g in keywords]

    question.text = text
    question.markscheme = markscheme
    question.explanation = explanation if explanation else None
    question.summary = summary if summary else None
    question.marks = int(marks) if marks else 1
    question.keywords = json.dumps(keywords)
    db.session.commit()
    return jsonify({"ok": True})


@quiz_bp.route("/api/quiz/question/<int:question_id>", methods=["DELETE"])
@login_required
@admin_required
def delete_question(question_id):
    question = QuizQuestion.query.get(question_id)
    if not question:
        return jsonify({"error": "Question not found"}), 404
    db.session.delete(question)
    db.session.commit()
    return jsonify({"ok": True})


@quiz_bp.route("/api/quiz/<book_folder>/questions", methods=["DELETE"])
@login_required
@admin_required
def delete_book_questions(book_folder):
    """Delete every quiz question for a book (or one page via ?page_id=),
    cascading to student answers."""
    query = QuizQuestion.query.filter_by(book_folder=book_folder)
    page_id = request.args.get("page_id")
    if page_id:
        query = query.filter_by(page_id=page_id)
    questions = query.all()
    for q in questions:  # ORM delete so answers cascade
        db.session.delete(q)
    db.session.commit()
    return jsonify({"ok": True, "deleted": len(questions)})


@quiz_bp.route("/student/quizzes")
@login_required
def student_quizzes():
    """Student quiz hub: every quiz available to the student (pages with
    questions in books they have assignments for), with answer progress."""
    if current_user.is_admin():
        return redirect(url_for("quiz.quiz_review"))

    book_folders = _student_book_folders(current_user.id)

    q = db.session.query(
        QuizQuestion.book_folder, QuizQuestion.page_id, db.func.count(QuizQuestion.id)
    )
    # No assignments yet → show every book that has quizzes
    if book_folders:
        q = q.filter(QuizQuestion.book_folder.in_(book_folders))
    counts = q.group_by(QuizQuestion.book_folder, QuizQuestion.page_id).all()

    # The student's answers, keyed by (book, page)
    answer_rows = (
        db.session.query(QuizAnswer, QuizQuestion.book_folder, QuizQuestion.page_id)
        .join(QuizQuestion, QuizAnswer.question_id == QuizQuestion.id)
        .filter(QuizAnswer.student_id == current_user.id)
        .all()
    )
    # With retakes a question has several answer rows — each question counts
    # once, marked by its latest attempt.
    latest_by_question = {}
    for ans, folder, page_id in answer_rows:
        cur = latest_by_question.get(ans.question_id)
        if cur is None or ans.attempt_number > cur[0].attempt_number:
            latest_by_question[ans.question_id] = (ans, folder, page_id)

    answered, correct = {}, {}
    for ans, folder, page_id in latest_by_question.values():
        key = (folder, page_id)
        answered[key] = answered.get(key, 0) + 1
        if _effective_mark(ans):
            correct[key] = correct.get(key, 0) + 1

    memo = {}
    books = {}
    for folder, page_id, n_questions in counts:
        book_title, page_titles = _book_meta(folder, memo)
        if folder not in books:
            page_order = {pid: i for i, pid in enumerate(page_titles)}
            books[folder] = {"title": book_title, "quizzes": [], "_order": page_order}
        key = (folder, page_id)
        books[folder]["quizzes"].append({
            "page_id": page_id,
            "page_title": page_titles.get(page_id, page_id),
            "url": url_for("quiz.quiz_page", book_folder=folder, page_id=page_id),
            "questions": n_questions,
            "answered": answered.get(key, 0),
            "correct": correct.get(key, 0),
        })
    for folder, book in books.items():
        order = book.pop("_order")
        book["quizzes"].sort(key=lambda item: order.get(item["page_id"], 10**6))

    book_list = sorted(books.values(), key=lambda b: b["title"].lower())
    return render_template("student_quizzes.html", books=book_list)


# Section codes in page titles, e.g. "A1.1.1 Describe…" or "A.1.2.5 Construct…"
# → unit "A1", section "A1.1". Tolerates a stray dot after the letter.
_SECTION_RE = re.compile(r"^([A-Za-z])\.?(\d+)\.(\d+)")

# "A1 Computer fundamentals" / "A1.1 Computer hardware and operation".
# Deliberately does NOT match page-level codes like "A1.1.1 ..." (no space
# after the two-part code there), so only unit/section entries are captured.
_NAV_TITLE_RE = re.compile(r"^([A-Za-z]\d+(?:\.\d+)?)\s+(.+)$")


def _section_titles(book_folder, memo=None):
    """{code: readable title} for units ("A1") and sections ("A1.1"), read
    from the pages' navigation menus. Each page's navigation only expands its
    own branch, so titles are aggregated across all pages and cached to
    section_titles.json in the book folder (rebuilt when book.json changes)."""
    key = f"nav:{book_folder}"
    if memo is not None and key in memo:
        return memo[key]

    book_dir = Path("data") / book_folder
    book_file = book_dir / "book.json"
    cache_file = book_dir / "section_titles.json"
    titles = None
    if cache_file.exists() and book_file.exists() and cache_file.stat().st_mtime >= book_file.stat().st_mtime:
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cached = json.load(f)
            if isinstance(cached, dict):
                titles = cached
        except (ValueError, OSError):
            pass

    if titles is None:
        titles = {}
        folders = []
        if book_file.exists():
            try:
                with open(book_file, "r", encoding="utf-8") as f:
                    folders = [p.get("folder") for p in json.load(f).get("pages", []) if p.get("folder")]
            except (ValueError, OSError):
                folders = []
        for folder in folders:
            page_file = book_dir / folder / "content.json"
            if not page_file.exists():
                continue
            try:
                with open(page_file, "r", encoding="utf-8") as f:
                    nav = json.load(f).get("navigation") or []
            except (ValueError, OSError):
                continue
            for entry in nav:
                m = _NAV_TITLE_RE.match((entry.get("text") or "").strip())
                if m:
                    titles.setdefault(m.group(1).upper(), m.group(2).strip())
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(titles, f, ensure_ascii=False, indent=1)
        except OSError:
            pass

    if memo is not None:
        memo[key] = titles
    return titles


def _student_book_folders(student_id):
    """Book folders the student can see (from their assignments)."""
    from sqlalchemy import and_, or_
    from models import ReadingAssignment

    class_ids = [e.class_id for e in ClassEnrollment.query.filter_by(student_id=student_id).all()]
    conditions = [ReadingAssignment.student_id == student_id]
    if class_ids:
        conditions.append(
            and_(
                ReadingAssignment.class_id.in_(class_ids),
                ReadingAssignment.student_id.is_(None),
            )
        )
    return {
        a.book_folder
        for a in ReadingAssignment.query.filter(or_(*conditions)).all()
        if a.book_folder
    }


def _compute_quiz_analytics(student_id, link_student_id=None):
    """Build the per-student quiz-analytics context (books drill-down, totals,
    strengths, focus areas). Shared by the student's own page, the admin
    student page, and the analytics hub. When link_student_id is given, the
    per-page detail links carry ?student_id= so a teacher stays in context."""
    from models import StudentFeedbackInsight

    detail_extra = {"student_id": link_student_id} if link_student_id else {}

    book_folders = _student_book_folders(student_id)
    q_query = QuizQuestion.query
    if book_folders:
        q_query = q_query.filter(QuizQuestion.book_folder.in_(book_folders))
    questions = q_query.all()
    question_ids = [q.id for q in questions]

    # Latest attempt per question + how many attempts were made
    answer_rows = []
    insights = []
    if question_ids:
        answer_rows = (
            QuizAnswer.query.filter(
                QuizAnswer.student_id == student_id,
                QuizAnswer.question_id.in_(question_ids),
            )
            .order_by(QuizAnswer.attempt_number)
            .all()
        )
        # Feedback themes: bold keywords extracted from marking feedback
        insights = StudentFeedbackInsight.query.filter(
            StudentFeedbackInsight.student_id == student_id,
            StudentFeedbackInsight.question_id.in_(question_ids),
        ).all()

    latest = {}
    attempts_per_question = {}
    for ans in answer_rows:
        latest[ans.question_id] = ans
        attempts_per_question[ans.question_id] = max(
            attempts_per_question.get(ans.question_id, 0), ans.attempt_number
        )
    keywords_by_question = {}
    for ins in insights:
        keywords_by_question.setdefault(ins.question_id, []).extend(ins.keyword_list())


    memo = {}
    books = {}
    for q in questions:
        book_title, page_titles = _book_meta(q.book_folder, memo)
        nav_titles = _section_titles(q.book_folder, memo)
        page_title = page_titles.get(q.page_id, q.page_id)
        m = _SECTION_RE.match(page_title)
        if m:
            unit_code = f"{m.group(1).upper()}{m.group(2)}"
            section_code = f"{unit_code}.{m.group(3)}"
        else:
            unit_code, section_code = "Other", "Other"

        book = books.setdefault(q.book_folder, {
            "title": book_title, "units": {},
            "_page_order": {pid: i for i, pid in enumerate(page_titles)},
        })
        unit = book["units"].setdefault(unit_code, {
            "code": unit_code, "title": nav_titles.get(unit_code), "sections": {},
        })
        section = unit["sections"].setdefault(section_code, {
            "code": section_code, "title": nav_titles.get(section_code), "pages": {}, "keywords": [],
        })
        # Build URL if in request context, otherwise skip
        try:
            url = url_for("quiz.student_page_detail", book_folder=q.book_folder, page_id=q.page_id, **detail_extra)
        except (RuntimeError, AttributeError):
            url = None

        page = section["pages"].setdefault(q.page_id, {
            "page_id": q.page_id,
            "title": page_title,
            "url": url,
            "questions": 0, "answered": 0, "correct": 0, "retakes": 0,
        })

        page["questions"] += 1
        ans = latest.get(q.id)
        if ans:
            page["answered"] += 1
            if _effective_mark(ans):
                page["correct"] += 1
            if attempts_per_question.get(q.id, 1) > 1:
                page["retakes"] += 1
        section["keywords"].extend(keywords_by_question.get(q.id, []))

    # Roll page numbers up to sections/units/books, flatten dicts into
    # sorted lists, and rank sections for strengths / focus areas.
    def _pct(correct, answered):
        return round(correct / answered * 100) if answered else None

    all_sections = []
    book_list = []
    totals = {"questions": 0, "answered": 0, "correct": 0, "retakes": 0}
    for folder, book in sorted(books.items(), key=lambda kv: kv[1]["title"].lower()):
        page_order = book["_page_order"]
        unit_list = []
        for unit in sorted(book["units"].values(), key=lambda u: (u["code"] == "Other", u["code"])):
            section_list = []
            for section in sorted(unit["sections"].values(), key=lambda s: (s["code"] == "Other", s["code"])):
                pages = sorted(section["pages"].values(), key=lambda p: page_order.get(p["page_id"], 10**6))
                s_questions = sum(p["questions"] for p in pages)
                s_answered = sum(p["answered"] for p in pages)
                s_correct = sum(p["correct"] for p in pages)
                s_retakes = sum(p["retakes"] for p in pages)
                for p in pages:
                    p["accuracy"] = _pct(p["correct"], p["answered"])
                # Most common feedback themes for this section
                counts = {}
                for kw in section["keywords"]:
                    kw = kw.strip()
                    if kw:
                        counts[kw] = counts.get(kw, 0) + 1
                top_keywords = [k for k, _ in sorted(counts.items(), key=lambda kv: -kv[1])[:5]]
                sec = {
                    "code": section["code"],
                    "title": section["title"],
                    "pages": pages,
                    "questions": s_questions,
                    "answered": s_answered,
                    "correct": s_correct,
                    "retakes": s_retakes,
                    "accuracy": _pct(s_correct, s_answered),
                    "keywords": top_keywords,
                    "book": book["title"],
                }
                section_list.append(sec)
                if s_answered:
                    all_sections.append(sec)
            u_questions = sum(s["questions"] for s in section_list)
            u_answered = sum(s["answered"] for s in section_list)
            u_correct = sum(s["correct"] for s in section_list)
            unit_list.append({
                "code": unit["code"],
                "title": unit["title"],
                "sections": section_list,
                "questions": u_questions,
                "answered": u_answered,
                "correct": u_correct,
                "accuracy": _pct(u_correct, u_answered),
            })
        b_questions = sum(u["questions"] for u in unit_list)
        b_answered = sum(u["answered"] for u in unit_list)
        b_correct = sum(u["correct"] for u in unit_list)
        b_retakes = sum(s["retakes"] for u in unit_list for s in u["sections"])
        totals["questions"] += b_questions
        totals["answered"] += b_answered
        totals["correct"] += b_correct
        totals["retakes"] += b_retakes
        book_list.append({
            "title": book["title"],
            "units": unit_list,
            "questions": b_questions,
            "answered": b_answered,
            "correct": b_correct,
            "accuracy": _pct(b_correct, b_answered),
        })

    ranked = sorted(all_sections, key=lambda s: (s["accuracy"], s["answered"]))
    focus_areas = [s for s in ranked if s["accuracy"] < 70][:3]
    strengths = [s for s in reversed(ranked) if s["accuracy"] >= 70][:3]
    totals["accuracy"] = _pct(totals["correct"], totals["answered"])

    return {
        "books": book_list,
        "totals": totals,
        "strengths": strengths,
        "focus_areas": focus_areas,
    }


@quiz_bp.route("/student/quiz-analytics")
@login_required
def student_quiz_analytics():
    """Student drill-down: quiz performance per unit (A1) → section (A1.1) →
    page (A1.1.1), with strengths, focus areas and feedback themes.

    Students see their own; a teacher (admin) views a specific student's — the
    exact same view — via ?student_id= from the admin pages."""
    from models import User

    teacher_view = current_user.is_admin()
    if teacher_view:
        sid = request.args.get("student_id", type=int)
        if not sid:
            return redirect(url_for("quiz.quiz_analytics"))
        student = User.query.get_or_404(sid)
    else:
        student = current_user

    data = _compute_quiz_analytics(student.id, link_student_id=student.id if teacher_view else None)
    return render_template(
        "student_quiz_analytics.html",
        teacher_view=teacher_view,
        student=student,
        base_template="admin_base.html" if teacher_view else "student_base.html",
        **data,
    )


def _render_feedback(text):
    """Feedback for display: escape any HTML, then restore simple bold
    (<b>/<strong> tags or markdown **...**) and line breaks."""
    from markupsafe import Markup, escape

    if not text:
        return None
    s = str(escape(text))
    s = re.sub(r"&lt;(/?)(b|strong)&gt;", r"<\1\2>", s)
    s = re.sub(r"\*\*([^*\n]+?)\*\*", r"<b>\1</b>", s)
    s = s.replace("\n", "<br>")
    return Markup(s)


@quiz_bp.route("/student/quiz-analytics/<book_folder>/<page_id>")
@login_required
def student_page_detail(book_folder, page_id):
    """Full breakdown of one subtopic page: the overview summary, then every
    question with the student's latest answer and complete (uncapped) feedback."""
    from models import PageSummary, StudentFeedbackInsight, User

    # Teachers reach this from a student's quiz analytics (?student_id=…); an
    # admin arriving without that context still goes to the manage view.
    teacher_view = current_user.is_admin()
    if teacher_view:
        sid = request.args.get("student_id", type=int)
        if not sid:
            return redirect(url_for("quiz.quiz_manage", book_folder=book_folder, page_id=page_id))
        student = User.query.get_or_404(sid)
    else:
        student = current_user
    student_id = student.id
    detail_extra = {"student_id": student_id} if teacher_view else {}

    questions = (
        QuizQuestion.query.filter_by(book_folder=book_folder, page_id=page_id)
        .order_by(QuizQuestion.position, QuizQuestion.id)
        .all()
    )
    book_title, page_titles = _book_meta(book_folder)
    page_title = page_titles.get(page_id, page_id)

    m = _SECTION_RE.match(page_title)
    section_code = f"{m.group(1).upper()}{m.group(2)}.{m.group(3)}" if m else None
    section_title = _section_titles(book_folder, memo={}).get(section_code) if section_code else None

    summary_row = PageSummary.query.filter_by(book_folder=book_folder, page_id=page_id).first()

    q_ids = [q.id for q in questions]
    answer_rows, insights = [], []
    if q_ids:
        answer_rows = (
            QuizAnswer.query.filter(
                QuizAnswer.student_id == student_id,
                QuizAnswer.question_id.in_(q_ids),
            )
            .order_by(QuizAnswer.attempt_number)
            .all()
        )
        insights = StudentFeedbackInsight.query.filter(
            StudentFeedbackInsight.student_id == student_id,
            StudentFeedbackInsight.question_id.in_(q_ids),
        ).all()

    latest, attempts = {}, {}
    for a in answer_rows:
        latest[a.question_id] = a
        attempts[a.question_id] = max(attempts.get(a.question_id, 0), a.attempt_number)
    kw_by_q = {}
    for ins in insights:
        seen = kw_by_q.setdefault(ins.question_id, [])
        for kw in ins.keyword_list():
            kw = kw.strip()
            if kw and kw.lower() not in {k.lower() for k in seen}:
                seen.append(kw)

    mastered, partial, unanswered = [], [], []
    total_marks = sum(q.marks for q in questions)
    marks_earned = 0

    for q in questions:
        ans = latest.get(q.id)
        item = {
            "question_id": q.id,
            "summary": q.summary or q.text[:60],
            "command": q.difficulty.upper() if q.difficulty else "QUESTION",
            "marks": q.marks,
            "keywords": kw_by_q.get(q.id, []),
            "attempts": attempts.get(q.id, 0),
        }

        if not ans:
            unanswered.append(item)
            continue

        item["answer_text"] = ans.answer_text
        item["pending"] = _effective_mark(ans) is None

        if _effective_mark(ans) is True:
            item["marks_awarded"] = q.marks
            marks_earned += q.marks
        elif _effective_mark(ans) is False:
            item["marks_awarded"] = 0
        else:
            item["marks_awarded"] = None

        raw_feedback = ans.feedback if (ans.status == "reviewed" and ans.feedback) else ans.auto_note
        item["feedback"] = _render_feedback(raw_feedback)
        item["what_you_know"] = ans.what_you_know
        item["improving_understanding"] = ans.improving_understanding

        if item.get("marks_awarded") == q.marks:
            mastered.append(item)
        else:
            partial.append(item)

    # Prev/next subtopic for swipe navigation: pages of this book that have
    # quiz questions, in book.json order.
    quiz_pages = {
        pid for (pid,) in
        db.session.query(QuizQuestion.page_id).filter_by(book_folder=book_folder).distinct()
    }
    ordered = [pid for pid in page_titles if pid in quiz_pages]
    prev_id = next_id = None
    if page_id in ordered:
        i = ordered.index(page_id)
        prev_id = ordered[i - 1] if i > 0 else None
        next_id = ordered[i + 1] if i < len(ordered) - 1 else None

    def _detail_link(pid):
        if not pid:
            return None
        return {
            "url": url_for("quiz.student_page_detail", book_folder=book_folder, page_id=pid, **detail_extra),
            "title": page_titles.get(pid, pid),
        }

    answered = len(mastered) + len(partial)
    accuracy = round(marks_earned / total_marks * 100) if total_marks else None

    return render_template(
        "student_page_detail.html",
        prev_page=_detail_link(prev_id),
        next_page=_detail_link(next_id),
        book_folder=book_folder,
        book_title=book_title,
        page_id=page_id,
        page_title=page_title,
        section_code=section_code,
        section_title=section_title,
        summary=summary_row.summary if summary_row else None,
        mastered=mastered,
        partial=partial,
        unanswered=unanswered,
        marks_earned=marks_earned,
        total_marks=total_marks,
        answered=answered,
        accuracy=accuracy,
        quiz_url=url_for("quiz.quiz_page", book_folder=book_folder, page_id=page_id),
        teacher_view=teacher_view,
        student=student,
        back_url=url_for("quiz.student_quiz_analytics", **detail_extra),
        base_template="admin_base.html" if teacher_view else "student_base.html",
    )


@quiz_bp.route("/book/<book_folder>/quizzes")
@login_required
@admin_required
def quiz_index(book_folder):
    """Book-level overview: every page with its question count and manage link."""
    book_title, _ = _book_meta(book_folder)
    return render_template("quiz_index.html", book_folder=book_folder, book_title=book_title)


# ---------------------------------------------------------------- teacher: page summaries

@quiz_bp.route("/book/<book_folder>/summaries")
@login_required
@admin_required
def summary_index(book_folder):
    """Book-level page-summary generator: every page with its AI overview,
    generate/regenerate per page or in bulk, edit inline."""
    book_title, _ = _book_meta(book_folder)
    return render_template("summary_index.html", book_folder=book_folder, book_title=book_title)


@quiz_bp.route("/api/summaries/<book_folder>")
@login_required
@admin_required
def summaries_list(book_folder):
    from models import PageSummary

    rows = PageSummary.query.filter_by(book_folder=book_folder).all()
    return jsonify({"summaries": {r.page_id: r.summary for r in rows}})


def _upsert_summary(book_folder, page_id, text):
    from models import PageSummary

    row = PageSummary.query.filter_by(book_folder=book_folder, page_id=page_id).first()
    if not text:
        if row:
            db.session.delete(row)
            db.session.commit()
        return None
    if row:
        row.summary = text
    else:
        row = PageSummary(book_folder=book_folder, page_id=page_id, summary=text)
        db.session.add(row)
    db.session.commit()
    return row


@quiz_bp.route("/api/summaries/<book_folder>/<page_id>", methods=["PUT"])
@login_required
@admin_required
def save_summary(book_folder, page_id):
    data = request.get_json(force=True, silent=True) or {}
    text = (data.get("summary") or "").strip()
    if len(text) > 600:
        return jsonify({"error": "Summary too long (600 characters max)"}), 400
    _upsert_summary(book_folder, page_id, text)
    return jsonify({"ok": True, "summary": text or None})


@quiz_bp.route("/api/summaries/<book_folder>/<page_id>/ai-generate", methods=["POST"])
@login_required
@admin_required
def ai_generate_summary(book_folder, page_id):
    from ai_generation import generate_page_summary, AIGenerationError

    content = _load_page_content(book_folder, page_id)
    if not content:
        return jsonify({"error": "Page not found"}), 404
    page_text = _extract_page_text(content)
    if not page_text or len(page_text) < 100:
        return jsonify({"error": "This page has too little text to summarise"}), 400
    try:
        summary = generate_page_summary(_page_title(content, page_id), page_text)
    except AIGenerationError as e:
        return jsonify({"error": str(e)}), 502
    _upsert_summary(book_folder, page_id, summary)
    return jsonify({"ok": True, "summary": summary})


@quiz_bp.route("/api/quiz/<book_folder>/counts")
@login_required
def quiz_counts(book_folder):
    """Question count per page of a book: {page_id: count}. Students use this
    to know which pages offer a quiz (e.g. reading mode's per-page buttons)."""
    rows = (
        db.session.query(QuizQuestion.page_id, db.func.count(QuizQuestion.id))
        .filter(QuizQuestion.book_folder == book_folder)
        .group_by(QuizQuestion.page_id)
        .all()
    )
    return jsonify({"counts": {page_id: count for page_id, count in rows}})


# ---------------------------------------------------------------- teacher: review queue

@quiz_bp.route("/admin/quiz-review")
@login_required
@admin_required
def quiz_review():
    return render_template("admin_quiz_review.html")


@quiz_bp.route("/admin/api/quiz-review")
@login_required
@admin_required
def quiz_review_list():
    status = request.args.get("status", "pending")
    class_id = request.args.get("class_id", type=int)
    query = QuizAnswer.query.join(QuizQuestion).join(User, QuizAnswer.student_id == User.id)
    if status in ("pending", "reviewed"):
        query = query.filter(QuizAnswer.status == status)
    if class_id:
        query = query.join(
            ClassEnrollment, ClassEnrollment.student_id == QuizAnswer.student_id
        ).filter(ClassEnrollment.class_id == class_id)
    rows = query.order_by(QuizAnswer.submitted_at.desc()).limit(500).all()

    # Friendly names: book/page titles and each student's classes
    meta = {}
    student_ids = {a.student_id for a in rows}
    classes_by_student = {}
    if student_ids:
        for enr in ClassEnrollment.query.filter(ClassEnrollment.student_id.in_(student_ids)).all():
            classes_by_student.setdefault(enr.student_id, []).append(enr.class_.name)

    def titles(a):
        book_title, pages = _book_meta(a.question.book_folder, meta)
        return book_title, pages.get(a.question.page_id, a.question.page_id)

    return jsonify({"answers": [{
        "answer_id": a.id,
        "student": a.student.name,
        "student_classes": ", ".join(sorted(classes_by_student.get(a.student_id, []))),
        "book_folder": a.question.book_folder,
        "page_id": a.question.page_id,
        "book_title": titles(a)[0],
        "page_title": titles(a)[1],
        "question": a.question.text,
        "summary": a.question.summary,
        "marks": a.question.marks,
        "markscheme": a.question.markscheme,
        "answer_text": a.answer_text,
        "auto_correct": a.auto_correct,
        "auto_method": a.auto_method,
        "auto_note": a.auto_note,
        "final_correct": a.final_correct,
        "status": a.status,
        "submitted_at": a.submitted_at.strftime("%Y-%m-%d %H:%M") if a.submitted_at else "",
    } for a in rows]})


@quiz_bp.route("/admin/api/quiz-review/<int:answer_id>", methods=["POST"])
@login_required
@admin_required
def quiz_review_mark(answer_id):
    from feedback_utils import store_feedback_insight

    ans = QuizAnswer.query.get(answer_id)
    if not ans:
        return jsonify({"error": "Answer not found"}), 404
    data = request.get_json(force=True, silent=True) or {}
    correct = data.get("correct")
    feedback = data.get("feedback", "").strip()
    if not isinstance(correct, bool):
        return jsonify({"error": "correct must be true or false"}), 400
    ans.final_correct = correct
    ans.feedback = feedback or None
    ans.status = "reviewed"
    ans.reviewed_at = datetime.now()
    ans.reviewed_by_id = current_user.id

    # A review changes this attempt's correctness/feedback, which feeds the
    # cross-attempt improvement analysis — invalidate the cache so it regenerates.
    QuizAnswer.query.filter_by(
        student_id=ans.student_id, question_id=ans.question_id
    ).update({"improvement_analysis": None})

    db.session.commit()

    # Extract and store feedback keywords if feedback was provided
    if ans.feedback:
        store_feedback_insight(ans)

    return jsonify({"ok": True})


# ---------------------------------------------------------------- teacher: class ability analytics

@quiz_bp.route("/api/quiz/<int:question_id>/improvement")
@login_required
def question_improvement(question_id):
    """Student sees their improvement on a single question across all attempts."""
    from improvement_analyzer import analyze_improvement

    result = analyze_improvement(current_user.id, question_id)
    if not result:
        return jsonify({"error": "No attempts found"}), 404

    return jsonify(result)


@quiz_bp.route("/admin/api/student/<int:student_id>/question/<int:question_id>/improvement")
@login_required
@admin_required
def teacher_view_question_improvement(student_id, question_id):
    """Teachers see a student's improvement on a question."""
    from improvement_analyzer import analyze_improvement

    result = analyze_improvement(student_id, question_id)
    if not result:
        return jsonify({"error": "No attempts found"}), 404

    return jsonify(result)


@quiz_bp.route("/api/student/feedback-summary")
@login_required
def student_feedback_summary():
    """Get feedback insights for the current student (patterns of what they're missing)."""
    from models import StudentFeedbackInsight
    from collections import Counter

    if current_user.is_admin():
        return jsonify({"error": "Admins cannot view as student"}), 403

    insights = StudentFeedbackInsight.query.filter_by(
        student_id=current_user.id
    ).order_by(StudentFeedbackInsight.created_at.desc()).all()

    # Aggregate keyword frequency
    all_keywords = []
    for insight in insights:
        all_keywords.extend(insight.keyword_list())

    keyword_freq = Counter(all_keywords)
    top_keywords = keyword_freq.most_common(15)

    return jsonify({
        "total_feedback_items": len(insights),
        "top_missing_concepts": [{"keyword": kw, "count": count} for kw, count in top_keywords],
        "recent_feedback": [
            {
                "question_text": i.question.text,
                "feedback": i.feedback_text,
                "keywords": i.keyword_list(),
                "created_at": i.created_at.isoformat(),
            }
            for i in insights[:10]
        ],
    })


@quiz_bp.route("/admin/api/student/<int:student_id>/feedback-summary")
@login_required
@admin_required
def teacher_view_student_feedback(student_id):
    """Teachers can view a student's feedback summary for coaching."""
    from models import StudentFeedbackInsight
    from collections import Counter

    student = User.query.get_or_404(student_id)
    insights = StudentFeedbackInsight.query.filter_by(
        student_id=student_id
    ).order_by(StudentFeedbackInsight.created_at.desc()).all()

    all_keywords = []
    for insight in insights:
        all_keywords.extend(insight.keyword_list())

    keyword_freq = Counter(all_keywords)
    top_keywords = keyword_freq.most_common(15)

    return jsonify({
        "student_name": student.name,
        "total_feedback_items": len(insights),
        "top_missing_concepts": [{"keyword": kw, "count": count} for kw, count in top_keywords],
        "recent_feedback": [
            {
                "question_text": i.question.text,
                "feedback": i.feedback_text,
                "keywords": i.keyword_list(),
                "created_at": i.created_at.isoformat(),
            }
            for i in insights[:20]
        ],
    })


@quiz_bp.route("/admin/quiz-analytics")
@login_required
@admin_required
def quiz_analytics():
    return render_template("admin_quiz_analytics.html")


@quiz_bp.route("/admin/api/student-quiz-analytics/<int:student_id>")
@login_required
@admin_required
def student_quiz_analytics_fragment(student_id):
    """HTML fragment of one student's quiz-analytics drill-down, for embedding
    in the analytics hub when a single student is selected in the filter."""
    student = User.query.get_or_404(student_id)
    data = _compute_quiz_analytics(student_id, link_student_id=student_id)
    return render_template(
        "_quiz_analytics_body.html",
        teacher_view=True,
        student=student,
        **data,
    )


@quiz_bp.route("/admin/api/quiz-analytics")
@login_required
@admin_required
def quiz_analytics_data():
    """Class ability matrix: per student, per topic (page), correct/answered."""
    class_id = request.args.get("class_id", type=int)
    student_id = request.args.get("student_id", type=int)

    if student_id:
        u = User.query.get(student_id)
        students = [u] if u else []
    elif class_id:
        enrollments = ClassEnrollment.query.filter_by(class_id=class_id).all()
        students = sorted((e.student for e in enrollments), key=lambda u: u.name.lower())
    else:
        students = User.query.filter_by(role="student").order_by(User.name).all()
    student_ids = [s.id for s in students]

    # Topics = pages that have quiz questions
    questions = QuizQuestion.query.all()
    question_count = {}
    question_page = {}
    for q in questions:
        key = f"{q.book_folder}|{q.page_id}"
        question_count[key] = question_count.get(key, 0) + 1
        question_page[q.id] = key

    answers = []
    if student_ids and questions:
        answers = QuizAnswer.query.filter(QuizAnswer.student_id.in_(student_ids)).all()

    # cells[student][page_key] = {answered, correct, pending}
    cells = {sid: {} for sid in student_ids}
    pages_with_data = set()
    for a in answers:
        key = question_page.get(a.question_id)
        if key is None:
            continue
        pages_with_data.add(key)
        cell = cells[a.student_id].setdefault(key, {"answered": 0, "correct": 0, "pending": 0})
        cell["answered"] += 1
        mark = _effective_mark(a)
        if mark:
            cell["correct"] += 1
        if a.status == "pending":
            cell["pending"] += 1

    meta = {}
    pages = []
    for key in pages_with_data:
        book_folder, page_id = key.split("|", 1)
        book_title, page_titles = _book_meta(book_folder, meta)
        pages.append({
            "key": key,
            "book_folder": book_folder,
            "page_id": page_id,
            "book_title": book_title,
            "page_title": page_titles.get(page_id, page_id),
            "question_count": question_count.get(key, 0),
        })
    pages.sort(key=lambda p: (p["book_title"].lower(), p["page_title"].lower()))

    out_students = []
    for s in students:
        row_cells = cells.get(s.id, {})
        answered = sum(c["answered"] for c in row_cells.values())
        correct = sum(c["correct"] for c in row_cells.values())
        out_students.append({
            "id": s.id,
            "name": s.name,
            "cells": row_cells,
            "answered": answered,
            "correct": correct,
        })

    return jsonify({"pages": pages, "students": out_students})


@quiz_bp.route("/admin/api/quiz-review/bulk-confirm", methods=["POST"])
@login_required
@admin_required
def quiz_review_bulk_confirm():
    """Confirm the auto-mark for a set of pending answers in one click."""
    data = request.get_json(force=True, silent=True) or {}
    ids = data.get("answer_ids")
    if not isinstance(ids, list) or not ids:
        return jsonify({"error": "answer_ids required"}), 400
    now = datetime.now()
    confirmed = 0
    for ans in QuizAnswer.query.filter(QuizAnswer.id.in_(ids), QuizAnswer.status == "pending").all():
        if ans.auto_correct is None:
            continue  # nothing to confirm — needs a human decision
        ans.final_correct = ans.auto_correct
        ans.status = "reviewed"
        ans.reviewed_at = now
        ans.reviewed_by_id = current_user.id
        confirmed += 1
    db.session.commit()
    return jsonify({"ok": True, "confirmed": confirmed})
