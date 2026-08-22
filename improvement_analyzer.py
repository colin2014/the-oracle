"""AI-powered analysis of quiz answer improvements across attempts."""

from anthropic import Anthropic
from extensions import db
from models import QuizAnswer, StudentFeedbackInsight


def _build_result(question_id, question, all_attempts, latest, analysis):
    """Assemble the response dict from (cheap) DB data plus the analysis text."""
    attempts_summary = [
        {
            "attempt": i,
            "answer": attempt.answer_text[:500],  # truncate for context
            "correct": attempt.final_correct if attempt.status == "reviewed" else attempt.auto_correct,
            "submitted_at": attempt.submitted_at.isoformat(),
        }
        for i, attempt in enumerate(all_attempts, 1)
    ]
    return {
        "question_id": question_id,
        "question_text": question.text,
        "total_attempts": len(all_attempts),
        "latest_correct": latest.final_correct if latest.status == "reviewed" else latest.auto_correct,
        "analysis": analysis,
        "attempts": attempts_summary,
    }


def analyze_improvement(student_id, question_id):
    """Compare all attempts for a question and generate AI feedback on improvement.

    The generated analysis is cached on the latest attempt row
    (QuizAnswer.improvement_analysis). It is regenerated only when a new
    attempt is submitted (a new latest row with no cache) or when a teacher
    review clears the cache (see quiz_review_mark)."""
    all_attempts = QuizAnswer.query.filter_by(
        student_id=student_id, question_id=question_id
    ).order_by(QuizAnswer.attempt_number).all()

    if not all_attempts:
        return None

    question = all_attempts[0].question
    latest = all_attempts[-1]
    previous = all_attempts[-2] if len(all_attempts) > 1 else None

    # Serve the cached analysis if we already generated one for this attempt.
    if latest.improvement_analysis:
        return _build_result(question_id, question, all_attempts, latest, latest.improvement_analysis)

    # Get feedback keywords from all previous attempts
    previous_insights = StudentFeedbackInsight.query.filter(
        StudentFeedbackInsight.student_id == student_id,
        StudentFeedbackInsight.question_id == question_id,
        StudentFeedbackInsight.answer_id.in_([a.id for a in all_attempts[:-1]]),
    ).all()

    previous_keywords = []
    for insight in previous_insights:
        previous_keywords.extend(insight.keyword_list())

    # Build comparison data
    attempts_summary = []
    for i, attempt in enumerate(all_attempts, 1):
        attempts_summary.append({
            "attempt": i,
            "answer": attempt.answer_text[:500],  # truncate for context
            "correct": attempt.final_correct if attempt.status == "reviewed" else attempt.auto_correct,
            "submitted_at": attempt.submitted_at.isoformat(),
        })

    # Use Claude to analyze improvement
    client = Anthropic()
    prompt = f"""You are analyzing a student's quiz answer improvements across multiple attempts.

Question: {question.text}

Marking scheme: {question.markscheme}

Student's attempts:
{chr(10).join([f"Attempt {a['attempt']} ({a['submitted_at']}): {a['answer'][:300]}... (marked: {a['correct']})" for a in attempts_summary])}

Previous feedback highlighted these gaps: {', '.join(set(previous_keywords)) if previous_keywords else 'None yet'}

Analyze:
1. What specifically improved (answer text changes)?
2. Was this question MASTERED (correct now after being wrong before)?
3. Did the student REGRESS (was correct before, wrong now)?
4. Did previous feedback get addressed?
5. Summary verdict on this question's progress.

Keep response concise and actionable for a 17-year-old."""

    message = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    analysis = next((b.text for b in message.content if b.type == "text"), "")

    # Cache on the latest attempt so we don't re-call Claude on every view.
    if analysis:
        latest.improvement_analysis = analysis
        db.session.commit()

    return _build_result(question_id, question, all_attempts, latest, analysis)


def generate_quiz_summary(student_id, questions):
    """Generate overall improvement summary for a quiz."""
    analyses = []
    mastered = 0
    regressed = 0
    still_struggling = 0

    for question_id in questions:
        result = analyze_improvement(student_id, question_id)
        if result:
            analyses.append(result)
            if "mastered" in result["analysis"].lower():
                mastered += 1
            elif "regress" in result["analysis"].lower():
                regressed += 1
            else:
                still_struggling += 1

    return {
        "mastered_count": mastered,
        "regressed_count": regressed,
        "still_struggling_count": still_struggling,
        "question_analyses": analyses,
    }
