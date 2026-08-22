"""AI marking for written Test Builder answers, with confidence-tiered review routing.

MCQ marking is instant/deterministic and handled in test_routes.py — nothing here
touches it. This module only marks question_type == "written" answers, one Claude
call each, using the question's marking_guidance/common_mistakes/ai_checklist as
free text (this bank's prose markschemes don't match quiz_routes.py's "[1 mark]"
tag format, so _parse_markscheme_points-style point extraction doesn't apply here).

Confidence tiers (self-reported by the model, not calibrated/guaranteed):
  >= 0.90            auto-accepted, no teacher action needed
  0.70 - 0.89         teacher review queue
  <  0.69             teacher review queue, higher priority (surfaced first)
"""

import json
import os
import re

from extensions import db

_CONFIDENCE_AUTO_ACCEPT = 0.90


def _subtopic_descriptor(question):
    """The workbook's student-friendly description of what this subtopic covers.
    Given to the marker as context so its feedback can name the capability the
    answer does (or doesn't) demonstrate, rather than only the mark."""
    from models import SubtopicDescriptor

    row = SubtopicDescriptor.query.filter_by(code=question.subtopic_code).first()
    return row.descriptor if row else None


def _call_claude_marker(question, answer_text):
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    prompt = (
        "You are marking a written answer for an IB DP Computer Science exam question "
        f"worth {question.marks} mark{'s' if question.marks != 1 else ''}. Both the "
        "student and the teacher will read your feedback directly, and the teacher will "
        "review your mark before it's finalized.\n\n"
        f"SUBTOPIC: {question.subtopic_title}\n"
        f"WHAT THIS SUBTOPIC COVERS: {_subtopic_descriptor(question) or 'Not provided.'}\n"
        f"QUESTION: {question.text}\n"
        f"MARKING GUIDANCE: {question.marking_guidance or 'None provided.'}\n"
        f"COMMON MISTAKES TO WATCH FOR: {question.common_mistakes or 'None provided.'}\n"
        f"AI MARKING CHECKLIST: {question.ai_checklist or 'None provided.'}\n"
        f"IF WRONG, SUGGEST: {question.if_wrong_explainer or 'None provided.'}\n\n"
        f"STUDENT ANSWER: {answer_text}\n\n"
        f"Award marks out of {question.marks} based on how well the answer satisfies the "
        "marking guidance. Be fair but rigorous — this is a formal, single-attempt exam, "
        "not a practice quiz.\n\n"
        "Write feedback that is SPECIFIC to what this student actually wrote — quote or "
        "closely paraphrase the exact word or phrase from their answer that earned or lost "
        "a mark, name precisely which required point (from the marking guidance) is "
        "missing or wrong, and say what one thing they'd need to add for full marks. "
        "When the answer is wrong, partial, or missing a point, base your suggestion of what "
        "they should have said on the IF WRONG, SUGGEST field above rather than inventing your "
        "own correction — but tie it back to their own words rather than pasting it in: say "
        "what they wrote, then what that field says was needed instead. "
        "When the answer earns full or near-full marks, use WHAT THIS "
        "SUBTOPIC COVERS to name the specific capability they have shown ('you're secure on "
        "how instructions move through the CPU'), so the report can say what they are "
        "confident at and not just that they were right. Never write a generic comment that could apply to any answer — if you "
        "can't point to something specific in THIS answer, say what specific fact is missing "
        "instead. Keep it to 2-3 sentences, plain language a student can act on.\n\n"
        "Also report your own confidence (0.0-1.0) in this mark. Use a LOWER confidence "
        "when the answer is borderline, ambiguously worded, unusually phrased, or not "
        "clearly covered by the marking guidance. Use HIGH confidence (0.90+) only when "
        "the mark is unambiguous.\n\n"
        "Respond with ONLY valid JSON: "
        '{"marks_awarded": <integer 0-' + str(question.marks) + '>, '
        '"feedback": "2-3 sentences, specific to this answer, for both student and teacher", '
        '"confidence": <float 0.0-1.0>}'
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

        marks_awarded = verdict.get("marks_awarded")
        if not isinstance(marks_awarded, int) or marks_awarded < 0 or marks_awarded > question.marks:
            return None
        confidence = verdict.get("confidence")
        if not isinstance(confidence, (int, float)) or not (0.0 <= confidence <= 1.0):
            confidence = 0.5
        feedback = str(verdict.get("feedback", ""))[:1000]
        return {"marks_awarded": marks_awarded, "feedback": feedback, "confidence": float(confidence)}
    except Exception:
        return None


def mark_written_answer(answer):
    """Marks one TestAnswer in place (question_type must be 'written'). Sets
    marks_awarded/ai_feedback/confidence/status. Leaves status='pending' (with no
    marks/confidence) if the AI call is unavailable or fails — the teacher then
    marks it from scratch in the review queue, same as if AI had never existed."""
    question = answer.question

    if not (answer.response_text or "").strip():
        hint = question.if_wrong_explainer or question.marking_guidance
        answer.marks_awarded = 0
        answer.ai_feedback = f"No answer was provided. {hint}" if hint else "No answer was provided."
        answer.confidence = 1.0
        answer.status = "reviewed"
        return

    result = _call_claude_marker(question, answer.response_text)
    if result is None:
        answer.status = "pending"
        return

    answer.marks_awarded = result["marks_awarded"]
    answer.ai_feedback = result["feedback"]
    answer.confidence = result["confidence"]
    answer.status = "reviewed" if result["confidence"] >= _CONFIDENCE_AUTO_ACCEPT else "pending"


def mark_submission(submission):
    """Runs AI marking over every written TestAnswer in a submission that hasn't
    been marked yet. MCQ answers are untouched (already handled deterministically
    at submit time in test_routes.py)."""
    for answer in submission.answers:
        if not answer.question.is_mcq() and answer.marks_awarded is None:
            mark_written_answer(answer)
    db.session.commit()
    maybe_finalize_submission(submission)


def maybe_finalize_submission(submission):
    """Keeps total_marks_awarded current every time marking touches a submission —
    this is what lets students see a preliminary AI-marked score right away rather
    than waiting on the teacher. Once every answer has been reviewed (auto-accepted
    or teacher-confirmed), the same total also becomes final and status flips to
    'marked'. Skipped questions never get a TestAnswer row, so they don't block
    finalization — they simply contribute 0."""
    if submission.status not in ("submitted", "marked"):
        return
    submission.total_marks_awarded = sum(a.marks_awarded or 0 for a in submission.answers)
    if submission.answers and any(a.status != "reviewed" for a in submission.answers):
        db.session.commit()
        return
    submission.status = "marked"
    db.session.commit()
