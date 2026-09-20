"""Report card endpoints for viewing student performance summaries."""

from flask import Blueprint, render_template, request, jsonify, current_app, send_file
from flask_login import login_required, current_user
from auth import admin_required
from extensions import db
from safe_errors import server_error
from models import (
    User, Class, ClassEnrollment, ReadingActivity, ReadingDailyLog,
    StudentConfidence, QuizAnswer, QuizQuestion, FlashcardProgress, StudentFeedbackInsight,
    StudentReportCache
)
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta
import hashlib
import os
import re
from anthropic import Anthropic
import json
from io import BytesIO

# WeasyPrint needs the GTK runtime (Pango/GObject DLLs) on Windows; without it
# the import raises OSError. Degrade to "PDF export unavailable" instead of
# crashing the whole app at startup.
try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError) as _weasyprint_error:
    HTML = CSS = None
    WEASYPRINT_AVAILABLE = False
    print(f"WARNING: WeasyPrint unavailable, PDF export disabled: {_weasyprint_error}")

from quiz_routes import _compute_quiz_analytics

report_card_bp = Blueprint('report_card', __name__)


@report_card_bp.route('/report-card')
@login_required
@admin_required
def report_card():
    """Report card page - allows searching for students and viewing their summaries"""
    return render_template('report_card.html')


@report_card_bp.route('/api/students', methods=['GET'])
@login_required
@admin_required
def list_students():
    """Get all students with optional class filtering and search"""
    search_query = request.args.get('q', '').strip().lower()
    class_id = request.args.get('class_id')

    # Start with all students
    students = User.query.filter_by(role='student').all()

    # Filter by class if provided
    if class_id:
        try:
            class_id = int(class_id)
            enrollments = ClassEnrollment.query.filter_by(class_id=class_id).all()
            student_ids = {e.student_id for e in enrollments}
            students = [s for s in students if s.id in student_ids]
        except (ValueError, TypeError):
            pass

    # Filter by search query
    if search_query:
        students = [
            s for s in students
            if search_query in s.name.lower() or
               (s.username and search_query in s.username.lower()) or
               (s.email and search_query in s.email.lower())
        ]

    # Sort by name
    students.sort(key=lambda s: s.name)

    # Return paginated results
    page = request.args.get('page', 1, type=int)
    per_page = 20
    start = (page - 1) * per_page
    paginated = students[start:start + per_page]

    return jsonify({
        'students': [
            {
                'id': s.id,
                'name': s.name,
                'username': s.username or '',
                'email': s.email or '',
                'created_at': s.created_at.isoformat() if s.created_at else None,
            }
            for s in paginated
        ],
        'total': len(students),
        'page': page,
        'per_page': per_page,
    })


def _get_student_stats(student_id):
    """Aggregate all student data for report generation"""

    # Reading activity stats
    reading_activities = ReadingActivity.query.filter_by(student_id=student_id).all()
    total_pages_started = len(reading_activities)
    total_pages_completed = sum(1 for r in reading_activities if r.completed)
    total_reading_seconds = sum(r.total_seconds or 0 for r in reading_activities)
    avg_reading_time = (total_reading_seconds / total_pages_started / 60) if total_pages_started > 0 else 0

    # Reading streak
    today = datetime.now().date()
    daily_logs = ReadingDailyLog.query.filter_by(student_id=student_id).order_by(
        ReadingDailyLog.date.desc()
    ).all()

    reading_streak = 0
    if daily_logs:
        dates = [log.date for log in daily_logs]
        for i, date in enumerate(dates):
            expected = today - timedelta(days=i)
            if date == expected:
                reading_streak += 1
            else:
                break

    # Confidence ratings
    confidence_ratings = StudentConfidence.query.filter_by(student_id=student_id).all()
    avg_confidence = (sum(c.confidence_level for c in confidence_ratings) / len(confidence_ratings)) if confidence_ratings else None
    low_confidence_pages = [c for c in confidence_ratings if c.confidence_level <= 2]

    # Quiz performance
    quiz_answers = QuizAnswer.query.filter_by(student_id=student_id).all()

    # Group by question to get latest attempt
    questions_answered = {}
    for answer in quiz_answers:
        if answer.question_id not in questions_answered:
            questions_answered[answer.question_id] = []
        questions_answered[answer.question_id].append(answer)

    # Sort each question's answers by attempt number to get the latest
    latest_answers = {}
    for q_id, answers in questions_answered.items():
        latest_answers[q_id] = max(answers, key=lambda a: a.attempt_number)

    quiz_correct = sum(1 for a in latest_answers.values() if a.final_correct or a.auto_correct)
    quiz_total = len(latest_answers)
    quiz_accuracy = (quiz_correct / quiz_total * 100) if quiz_total > 0 else 0

    # Count retakes
    retakes = sum(1 for answers in questions_answered.values() if len(answers) > 1)

    # Get feedback insights for struggling areas
    feedback_insights = StudentFeedbackInsight.query.filter_by(student_id=student_id).all()

    # Extract keywords that appear frequently (areas of struggle)
    keyword_counts = {}
    for insight in feedback_insights:
        for keyword in insight.keyword_list():
            keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1

    # Get top struggling areas (appear in 2+ pieces of feedback)
    struggling_areas = sorted(
        [k for k, count in keyword_counts.items() if count >= 2],
        key=lambda k: keyword_counts[k],
        reverse=True
    )[:5]

    # Flashcard performance
    flashcard_progress = FlashcardProgress.query.filter_by(student_id=student_id).all()
    flashcard_correct = sum(p.correct_count for p in flashcard_progress)
    flashcard_incorrect = sum(p.incorrect_count for p in flashcard_progress)
    flashcard_total = flashcard_correct + flashcard_incorrect
    flashcard_accuracy = (flashcard_correct / flashcard_total * 100) if flashcard_total > 0 else 0
    mastered_cards = sum(1 for p in flashcard_progress if p.is_mastered)

    # Curriculum-level strengths / focus areas from the shared quiz analytics
    # (same ranking the analytics pages show: per-section accuracy + themes)
    analytics = _compute_quiz_analytics(student_id)

    def _slim_sections(sections):
        return [
            {
                'section': s['code'],
                'title': s['title'] or s['code'],
                'book': s['book'],
                'accuracy': s['accuracy'],
                'answered': s['answered'],
                'retakes': s['retakes'],
                'feedback_themes': s['keywords'],
            }
            for s in sections
        ]

    strong_sections = _slim_sections(analytics['strengths'])
    focus_sections = _slim_sections(analytics['focus_areas'])

    # Get classes the student is enrolled in
    enrollments = ClassEnrollment.query.filter_by(student_id=student_id).all()
    classes = [e.class_.name for e in enrollments]

    return {
        'reading': {
            'pages_started': total_pages_started,
            'pages_completed': total_pages_completed,
            'total_seconds': int(total_reading_seconds),
            'avg_minutes': round(avg_reading_time, 1),
            'streak_days': reading_streak,
            'completion_rate': (total_pages_completed / total_pages_started * 100) if total_pages_started > 0 else 0,
            'avg_confidence': round(avg_confidence, 1) if avg_confidence else None,
            'low_confidence_count': len(low_confidence_pages),
        },
        'quiz': {
            'total': quiz_total,
            'correct': quiz_correct,
            'accuracy': round(quiz_accuracy, 1),
            'retakes': retakes,
            'struggling_areas': struggling_areas,
            'strong_sections': strong_sections,
            'focus_sections': focus_sections,
        },
        'flashcard': {
            'total_attempts': flashcard_total,
            'correct': flashcard_correct,
            'accuracy': round(flashcard_accuracy, 1),
            'mastered': mastered_cards,
        },
        'classes': classes,
    }


def _get_performance_level(accuracy):
    """Categorize performance level.

    The labels describe where the student is on the way to secure understanding,
    not a verdict on them: a student reading their own report should see a stage
    they can move out of ("Getting started") rather than a judgement they have to
    carry ("Needs Support"). The colours are unchanged — the bar still shows the
    truth of the score, the words just stop editorialising about it."""
    if accuracy >= 80:
        return {'level': 'Secure', 'color': 'success', 'icon': '✓'}
    elif accuracy >= 60:
        return {'level': 'Good progress', 'color': 'info', 'icon': '→'}
    elif accuracy >= 40:
        return {'level': 'Developing', 'color': 'warning', 'icon': '!'}
    else:
        return {'level': 'Getting started', 'color': 'danger', 'icon': '●'}


def _extract_bold_keywords(student_id):
    """Extract bold keywords from teacher feedback that indicate key concepts"""
    import re
    feedback_insights = StudentFeedbackInsight.query.filter_by(student_id=student_id).all()

    bold_keywords = []
    keyword_frequency = {}

    for insight in feedback_insights:
        # Extract text between ** (markdown bold)
        matches = re.findall(r'\*\*([^*]+)\*\*', insight.feedback_text)
        for match in matches:
            bold_keywords.append(match)
            keyword_frequency[match] = keyword_frequency.get(match, 0) + 1

    # Sort by frequency
    sorted_keywords = sorted(
        keyword_frequency.items(),
        key=lambda x: x[1],
        reverse=True
    )

    return {
        'keywords': [k[0] for k in sorted_keywords],
        'frequency': dict(sorted_keywords),
        'total_unique': len(set(bold_keywords)),
    }


def _analyze_writing_patterns(student_id):
    """Analyze writing patterns from stored feedback"""
    feedback_insights = StudentFeedbackInsight.query.filter_by(student_id=student_id).all()

    if not feedback_insights:
        return {
            'patterns': [],
            'sample_feedback': [],
            'common_issues': []
        }

    # Analyze feedback text for common patterns
    all_feedback = []

    pattern_keywords = {
        'too_vague': ['vague', 'unclear', 'not specific', 'too general', 'too vague and', 'unclear what', 'doesn\'t explain', 'doesn\'t describe'],
        'missing_detail': ['needs more detail', 'be more specific', 'more specific', 'strengthen', 'add detail', 'add more', 'lacking detail'],
        'incomplete': ['incomplete', 'incomplete answer', 'doesn\'t address', 'misses', 'missing', 'left out'],
        'missing_steps': ['missing steps', 'steps', 'mention', 'next time mention', 'next time'],
        'unclear_expression': ['unclear expression', 'express your ideas', 'organizing your thoughts', 'more clearly', 'more concisely'],
        'good_work': ['great work', 'great job', 'well done', 'good work', 'nailed it', 'correct', 'well captured'],
        'good_understanding': ['demonstrates understanding', 'understanding of', 'correctly identified', 'good understanding', 'key idea'],
    }

    # Initialize counters for each pattern
    writing_patterns = {pattern: 0 for pattern in pattern_keywords.keys()}

    for insight in feedback_insights:
        feedback_lower = insight.feedback_text.lower()
        all_feedback.append(insight.feedback_text[:300])

        for pattern, keywords in pattern_keywords.items():
            if any(kw in feedback_lower for kw in keywords):
                writing_patterns[pattern] += 1

    # Determine dominant patterns
    dominant = sorted(
        [(k, v) for k, v in writing_patterns.items() if v > 0],
        key=lambda x: x[1],
        reverse=True
    )[:3]

    return {
        'patterns': [{'issue': p[0].replace('_', ' ').title(), 'count': p[1]} for p in dominant],
        'sample_feedback': all_feedback[:3],
        'writing_assessment': dominant,
        'total_feedback_entries': len(feedback_insights),
    }


def _extract_specific_topics(student_id):
    """Extract specific topics student has been working on from quiz feedback"""
    feedback_insights = StudentFeedbackInsight.query.filter_by(student_id=student_id).all()

    # Group feedback by topic/keyword with actual feedback text
    topics_struggling = {}
    all_feedback_by_topic = {}

    for insight in feedback_insights:
        answer = insight.answer
        if answer and answer.question:
            question_text = answer.question.text
            topic = answer.question.summary or question_text[:100]

            if topic not in all_feedback_by_topic:
                all_feedback_by_topic[topic] = []

            all_feedback_by_topic[topic].append({
                'feedback': insight.feedback_text,
                'correct': answer.final_correct or answer.auto_correct,
                'keywords': insight.keyword_list(),
                'attempt': answer.attempt_number,
            })

            keywords = insight.keyword_list()
            for keyword in keywords:
                if keyword not in topics_struggling:
                    topics_struggling[keyword] = []
                topics_struggling[keyword].append({
                    'topic': topic,
                    'correct': answer.final_correct or answer.auto_correct,
                    'feedback': insight.feedback_text[:300],
                    'attempt_number': answer.attempt_number,
                })

    # Get recent quiz activity with actual feedback
    recent_quizzes = QuizAnswer.query.filter_by(student_id=student_id).order_by(
        QuizAnswer.submitted_at.desc()
    ).limit(10).all()

    topics_attempted = []
    for qa in recent_quizzes:
        if qa.question:
            topic = qa.question.summary or qa.question.text[:100]
            correct = qa.final_correct or qa.auto_correct

            # Get associated feedback for this quiz answer
            feedback_for_qa = StudentFeedbackInsight.query.filter_by(answer_id=qa.id).first()
            feedback_text = feedback_for_qa.feedback_text if feedback_for_qa else ""

            topics_attempted.append({
                'topic': topic,
                'correct': correct,
                'date': qa.submitted_at.isoformat() if qa.submitted_at else None,
                'feedback': feedback_text[:300],
            })

    return {
        'feedback_topics': topics_struggling,
        'recent_quizzes': topics_attempted,
        'total_unique_topics': len(set(t['topic'] for t in topics_attempted)),
        'all_feedback_by_topic': all_feedback_by_topic,
    }


# Enforced server-side via output_config.format so the model cannot return prose,
# markdown fences, or a truncated object. Field-by-field writing guidance lives in
# the prompt; this is purely the shape.
_REPORT_SCHEMA = {
    "type": "object",
    "properties": {
        "overall_summary": {"type": "string"},
        "what_went_well": {"type": "string"},
        "what_youre_learning": {"type": "string"},
        "your_strengths": {"type": "array", "items": {"type": "string"}},
        "where_to_focus": {"type": "array", "items": {"type": "string"}},
        "feedback_patterns": {"type": "string"},
        "your_action_plan": {"type": "array", "items": {"type": "string"}},
        "next_steps": {"type": "string"},
    },
    "required": [
        "overall_summary", "what_went_well", "what_youre_learning", "your_strengths",
        "where_to_focus", "feedback_patterns", "your_action_plan", "next_steps",
    ],
    "additionalProperties": False,
}


def _build_report_prompt(student, stats):
    """Assemble the prompt. Split out from generation so the cache can fingerprint
    the exact string that determines the output — see StudentReportCache."""

    reading_data = stats['reading']
    quiz_data = stats['quiz']
    flashcard_data = stats['flashcard']

    # Extract specific topics from database
    topics_data = _extract_specific_topics(student.id)

    # Format recent quiz topics for the prompt
    recent_topics_str = ""
    if topics_data['recent_quizzes']:
        recent_topics_str = "Recently studied topics:\n"
        for qt in topics_data['recent_quizzes'][:5]:
            status = "✓" if qt['correct'] else "✗"
            recent_topics_str += f"- {status} {qt['topic']}\n"

    # Format struggling areas with context
    struggling_context = ""
    if quiz_data['struggling_areas']:
        struggling_context = "Areas needing improvement based on feedback:\n"
        for area in quiz_data['struggling_areas'][:5]:
            struggling_context += f"- {area}\n"

    # Analyze writing patterns from feedback
    writing_patterns = _analyze_writing_patterns(student.id)
    writing_patterns_str = ""
    if writing_patterns['patterns']:
        writing_patterns_str = "Writing and response patterns identified in teacher feedback:\n"
        for pattern in writing_patterns['patterns']:
            writing_patterns_str += f"- {pattern['issue']}: Mentioned in {pattern['count']} feedback comments\n"

    # Extract bold keywords (key concepts teacher emphasized)
    bold_keywords_data = _extract_bold_keywords(student.id)
    bold_keywords_str = ""
    if bold_keywords_data['keywords']:
        bold_keywords_str = "Key concepts emphasized in teacher feedback:\n"
        for keyword in bold_keywords_data['keywords'][:10]:
            count = bold_keywords_data['frequency'].get(keyword, 0)
            bold_keywords_str += f"- {keyword}\n"

    # Curriculum sections from quiz analytics: strongest and weakest, with
    # accuracy, retake effort, and the feedback themes attached to each
    def _section_lines(sections):
        lines = []
        for s in sections:
            line = f"- {s['section']} {s['title']} ({s['book']}): {s['accuracy']}% accuracy over {s['answered']} questions"
            if s['retakes']:
                line += f", {s['retakes']} retaken"
            if s['feedback_themes']:
                line += f" — feedback themes: {', '.join(s['feedback_themes'])}"
            lines.append(line)
        return "\n".join(lines)

    strong_sections_str = _section_lines(quiz_data['strong_sections'])
    focus_sections_str = _section_lines(quiz_data['focus_sections'])

    # Build comprehensive data summary for Claude
    report_data = {
        'student_name': student.name,
        'reading': {
            'completion_rate': reading_data['completion_rate'],
            'pages_completed': reading_data['pages_completed'],
            'pages_started': reading_data['pages_started'],
            'streak_days': reading_data['streak_days'],
            'avg_confidence': reading_data['avg_confidence'],
            'low_confidence_count': reading_data['low_confidence_count'],
        },
        'quiz': {
            'accuracy': quiz_data['accuracy'],
            'total_questions': quiz_data['total'],
            'correct': quiz_data['correct'],
            'retakes': quiz_data['retakes'],
            'struggling_areas': quiz_data['struggling_areas'][:5],
            'total_unique_topics': topics_data['total_unique_topics'],
        },
        'vocabulary': {
            'accuracy': flashcard_data['accuracy'],
            'mastered_cards': flashcard_data['mastered'],
            'total_attempts': flashcard_data['total_attempts'],
        },
        'recent_topics': recent_topics_str,
        'struggling_feedback': struggling_context,
        'writing_patterns': writing_patterns_str,
        'key_concepts_emphasized': bold_keywords_str,
        'strongest_curriculum_sections': strong_sections_str,
        'weakest_curriculum_sections': focus_sections_str,
    }

    prompt = f"""Write a progress report for {student.name}, a secondary-school student, addressed directly to them as "you".

STUDENT DATA:
{json.dumps(report_data, indent=2)}

WHO READS THIS
Three people may read these exact words, and it has to work for all of them:
- The student. They may be anxious about school and will read this as a judgement of themselves as a person.
- A parent or guardian, who wants to know honestly how their child is doing and how to help at home.
- A senior teacher or head of school, who needs it to be accurate, specific and evidence-based.
Write so all three come away informed rather than alarmed.

TONE
- Warm, calm and respectful, the way a teacher who likes this student and believes in them would write.
- Lead with what is going well and give it real space. It should not be one line of praise before a list of problems.
- Difficulty belongs to the work, not to the person. Write "this topic hasn't clicked yet" or "these questions are catching you out", never "you are weak at this" or "you struggle with".
- Prefer "not yet" over "can't". Everything here describes where they are right now, not a verdict on what they are capable of.
- No sarcasm, no disappointment, no guilt, no pressure, and no comparison to other students.
- Plain language a fifteen-year-old will understand. Explain a term the first time you use it.

ACCURACY MATTERS AS MUCH AS KINDNESS
- Kind never means overstated. A report a head of school cannot trust is worthless, and a student praised for work they did not do learns nothing.
- Every claim comes from the data above: name real sections (e.g. "A2.3 Loops"), real percentages, and real feedback themes. Never state a number, topic or achievement that is not in the data.
- If the numbers are low, do not invent achievements to soften it. Find what is genuinely true — effort, retakes, a topic that improved, something answered correctly — say that plainly, then be straightforward about what needs attention. Honest and gentle at the same time is the goal.
- Draw strengths from strongest_curriculum_sections and focus areas from weakest_curriculum_sections whenever those are non-empty.
- Retakes are evidence of someone choosing to improve. Treat them that way, never as failures.

WHAT GOES IN EACH FIELD
- overall_summary: 3-4 sentences on how the period has gone overall. Open with something real that went well. Reference specific metrics and topics.
- what_went_well: 4-5 sentences summarising specifically what they got right — the sections they scored well in, topics they completed, questions they answered correctly, concepts that are clearly landing. This is the part the student will reread, so make it concrete and generous with detail. Name the actual work. Do not repeat the list in your_strengths: this is about what they produced, that is about the abilities behind it.
- what_youre_learning: 2-3 sentences on the concepts they have been studying and how they fit together.
- your_strengths: 2-3 items, 2-3 sentences each, on the durable abilities they are showing and the evidence for each.
- where_to_focus: 2-3 items, 2-3 sentences each. Name the topic, say plainly what is not working yet and why it matters, and pair each one with the encouraging fact that it is learnable. Frame it as the next thing to work on, not as a shortfall.
- feedback_patterns: 2-3 sentences on what comes naturally in their work and what still needs attention, using the feedback themes in the data.
- your_action_plan: 4 items, 1-2 sentences each. Concrete things they can do this week — a study technique, a practice strategy, a specific concept to review. Each should feel achievable, not like a punishment.
- next_steps: 4-5 sentences of forward-looking guidance. Close the report warmly and with genuine confidence in them.

Ensure every field is complete and fully formed.
Address them as "you" throughout and do not write their name anywhere in the report text — the name is added by the page around it, and a teacher may substitute the student's real name when exporting."""

    return prompt


def _empty_report(message):
    """Failure shape. Uses the same keys the renderers read, so a failed
    generation degrades to a single clear sentence instead of a half-rendered
    card — the old fallback returned 'strengths'/'areas_for_growth', which no
    renderer reads, so nothing appeared at all."""
    return {
        'overall_summary': message,
        'what_went_well': '',
        'what_youre_learning': '',
        'your_strengths': [],
        'where_to_focus': [],
        'feedback_patterns': '',
        'your_action_plan': [],
        'next_steps': '',
        '_generation_failed': True,
    }


def _generate_parent_friendly_report(student, stats, prompt=None):
    """Generate a detailed, parent-friendly report using Claude Haiku."""

    prompt = prompt or _build_report_prompt(student, stats)

    try:
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")

        client = Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            # The report is 8 fields of multi-sentence prose plus a 4-item action
            # plan; 2048 truncated it mid-JSON, which is what the parse-failure
            # branch below was catching.
            max_tokens=4096,
            # Structured outputs: the API constrains the response to the schema,
            # so the markdown-fence stripping below is now belt-and-braces rather
            # than load-bearing.
            output_config={"format": {"type": "json_schema", "schema": _REPORT_SCHEMA}},
            messages=[{'role': 'user', 'content': prompt}]
        )

        response_text = next((b.text for b in message.content if b.type == 'text'), '{}')

        # Strip markdown code fences if present
        response_text = response_text.strip()
        if response_text.startswith('```'):
            # Remove opening fence (```json or ```)
            response_text = response_text.split('\n', 1)[1] if '\n' in response_text else response_text
            # Remove closing fence (```)
            if response_text.endswith('```'):
                response_text = response_text[:-3]
        response_text = response_text.strip()

        # Parse JSON response
        try:
            report_content = json.loads(response_text)
            return report_content
        except json.JSONDecodeError as json_err:
            # Should no longer happen — output_config.format constrains the
            # response to _REPORT_SCHEMA — but keep the branch rather than let a
            # parse error escape as a 500.
            print(f"JSON Decode Error: {json_err}")
            print(f"Response was: {response_text[:500]}")
            return _empty_report(
                "This report couldn't be generated just now. Please try again in a moment."
            )

    except Exception as e:
        # Technical detail stays in the server log; the teacher sees a sentence
        # they can act on rather than an exception string in the report body.
        print(f"Error generating report: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return _empty_report(
            "This report couldn't be generated just now. Please try again in a moment."
        )


def _get_or_generate_report(student, stats, force_refresh=False):
    """Return (report, cache_state) where cache_state is 'hit' | 'generated' | 'failed'.

    Both the on-screen view and the PDF export go through here so a view plus an
    export costs one Anthropic call, and the PDF contains the same prose the
    teacher just read. Generation is non-deterministic, so calling the model
    twice would produce two different reports for the same student."""
    prompt = _build_report_prompt(student, stats)
    fingerprint = hashlib.sha256(prompt.encode('utf-8')).hexdigest()

    cached = StudentReportCache.query.filter_by(student_id=student.id).first()
    if not force_refresh and cached and cached.prompt_fingerprint == fingerprint:
        try:
            return json.loads(cached.report_json), 'hit'
        except json.JSONDecodeError:
            pass  # corrupt row — fall through and regenerate over it

    report = _generate_parent_friendly_report(student, stats, prompt=prompt)

    # Never cache a failure: the next request should retry, not serve the error
    # sentence back for as long as the student's data happens not to change.
    if report.get('_generation_failed'):
        return report, 'failed'

    if cached is None:
        cached = StudentReportCache(student_id=student.id)
        db.session.add(cached)
    cached.prompt_fingerprint = fingerprint
    cached.report_json = json.dumps(report)
    cached.generated_at = datetime.now()
    try:
        db.session.commit()
    except IntegrityError:
        # student_id is unique; a concurrent request inserted the row first.
        # Its report is as valid as ours, so keep ours for this response and
        # let the next read pick up whichever landed.
        db.session.rollback()
    return report, 'generated'


@report_card_bp.route('/api/students/<int:student_id>/report-summary', methods=['GET'])
@login_required
@admin_required
def get_report_summary(student_id):
    """Generate a parent-friendly report for a student"""

    try:
        student = User.query.get(student_id)
        if not student or student.role != 'student':
            return jsonify({'error': 'Student not found'}), 404

        # Get all student data
        stats = _get_student_stats(student_id)

        # Served from cache unless the student's data changed or the teacher
        # asked for a fresh one. ?refresh=1 is the regenerate control.
        force = request.args.get('refresh') in ('1', 'true', 'yes')
        report_content, cache_state = _get_or_generate_report(student, stats, force_refresh=force)
    except Exception as e:
        print(f"Error in get_report_summary: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return server_error(e, 'The report could not be generated.')

    # Add performance levels
    reading_level = _get_performance_level(stats['reading']['completion_rate'])
    quiz_level = _get_performance_level(stats['quiz']['accuracy'])
    vocab_level = _get_performance_level(stats['flashcard']['accuracy'])

    return jsonify({
        'success': True,
        'student_id': student_id,
        'student_name': student.name,
        'student_avatar': student.avatar,
        'report': report_content,
        'stats': stats,
        'performance_levels': {
            'reading': reading_level,
            'quiz': quiz_level,
            'vocabulary': vocab_level,
        },
        # 'hit' | 'generated' | 'failed' — lets the UI distinguish a cached
        # report from a fresh one, and show a retry when generation failed.
        'cache_state': cache_state,
        'generated_at': datetime.now().isoformat(),
    })


@report_card_bp.route('/api/students/<int:student_id>/full-report', methods=['GET'])
@login_required
@admin_required
def get_full_report(student_id):
    """Get detailed report data for a student (without AI summary)"""

    student = User.query.get(student_id)
    if not student or student.role != 'student':
        return jsonify({'error': 'Student not found'}), 404

    stats = _get_student_stats(student_id)

    return jsonify({
        'student_id': student.id,
        'student_name': student.name,
        'stats': stats,
    })


def _render_report_html(student, report, stats, performance_levels, generated_at,
                        display_name=None):
    """Render report as HTML string for PDF generation.

    Icons come from report_icons — never emoji. See that module: emoji glyphs
    make WeasyPrint search the whole system font set and cost tens of seconds
    per PDF.

    `display_name` overrides the name printed on this one document. It is passed
    as an argument rather than assigned onto `student` on purpose: `student` is a
    live SQLAlchemy row, and mutating it would mark the session dirty and could
    write the override back to the database on the next flush."""
    from report_icons import icon, ICON_CSS
    name = display_name or student.name
    reading = stats['reading']
    quiz = stats['quiz']
    flashcard = stats['flashcard']

    now = datetime.fromisoformat(generated_at) if isinstance(generated_at, str) else generated_at
    date_str = now.strftime('%B %d, %Y')

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Report Card - {name}</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #333; line-height: 1.6; }}
            .report-container {{ max-width: 8.5in; margin: 0 auto; padding: 0.5in; }}
            .report-header {{ margin-bottom: 1.5rem; padding-bottom: 1rem; border-bottom: 3px solid #e3f2fd; }}
            .student-name-large {{ font-size: 28pt; font-weight: 700; margin: 0 0 0.25rem 0; color: #333; }}
            .report-date {{ font-size: 10pt; color: #999; }}
            .summary-section {{ background: linear-gradient(135deg, #f5f7fa 0%, #e9ecef 100%); border-left: 5px solid #2196F3; padding: 1rem; border-radius: 4px; margin-bottom: 1.5rem; }}
            .summary-title {{ font-size: 9pt; font-weight: 700; text-transform: uppercase; color: #2196F3; margin-bottom: 0.5rem; letter-spacing: 0.5px; }}
            .summary-text {{ font-size: 11pt; line-height: 1.7; color: #333; }}
            .performance-grid {{ display: flex; gap: 1rem; margin-bottom: 1.5rem; page-break-inside: avoid; }}
            .performance-card {{ flex: 1; border: 2px solid #e0e0e0; border-radius: 4px; padding: 1rem; }}
            .performance-card.success {{ border-left: 5px solid #4CAF50; }}
            .performance-card.info {{ border-left: 5px solid #2196F3; }}
            .performance-card.warning {{ border-left: 5px solid #FF9800; }}
            .performance-card.danger {{ border-left: 5px solid #f44336; }}
            .performance-label {{ font-size: 9pt; font-weight: 600; color: #666; text-transform: uppercase; margin-bottom: 0.5rem; letter-spacing: 0.3px; }}
            .performance-value {{ font-size: 24pt; font-weight: 700; margin: 0.5rem 0; }}
            .performance-value.success {{ color: #4CAF50; }}
            .performance-value.info {{ color: #2196F3; }}
            .performance-value.warning {{ color: #FF9800; }}
            .performance-value.danger {{ color: #f44336; }}
            .performance-status {{ font-size: 9pt; color: #999; margin-top: 0.5rem; }}
            /* No page-break-inside: these sections hold unbounded lists and
               "avoid" strands a header alone on an otherwise blank page. */
            .report-section {{ margin-bottom: 1.5rem; }}
            @page {{ size: A4; margin: 0.5in; }}
            @media print {{
                .report-container {{ max-width: none; padding: 0; }}
                .performance-grid, .action-item, .achievement-item, .growth-item {{
                    page-break-inside: avoid; break-inside: avoid;
                }}
                .section-header, .summary-title {{ page-break-after: avoid; break-after: avoid; }}
            }}
            .section-header {{ display: flex; align-items: center; gap: 0.4rem; font-size: 14pt; font-weight: 700; margin: 0 0 0.75rem 0; padding-bottom: 0.5rem; border-bottom: 3px solid #e3f2fd; color: #333; }}
            .summary-title, .performance-label {{ display: flex; align-items: center; gap: 0.35rem; }}
            .section-header > .rpt-icon, .summary-title > .rpt-icon, .performance-label > .rpt-icon {{ margin-right: 0; }}
            {ICON_CSS}
            .achievement-list, .growth-list {{ list-style: none; margin: 0; padding: 0; }}
            /* Hanging indent rather than flex: WeasyPrint does not honour
               break-inside on flex containers, so an item straddling a page
               boundary gets torn in half (icon on one page, text on the next). */
            .achievement-item, .growth-item {{ padding: 0.75rem 0.75rem 0.75rem 2.1rem; text-indent: -1.55rem; background: white; border: 1px solid #e0e0e0; border-left: 4px solid #4CAF50; margin-bottom: 0.5rem; border-radius: 4px; line-height: 1.6; color: #333; font-size: 10pt; }}
            .growth-item {{ border-left-color: #FF9800; }}
            .achievement-item > .rpt-icon {{ color: #4CAF50; }}
            .growth-item > .rpt-icon {{ color: #FF9800; }}
            .action-list {{ list-style: none; margin: 0; padding: 0; }}
            .action-item {{ background: #f0f7ff; border-left: 4px solid #2196F3; padding: 0.75rem; margin-bottom: 0.5rem; border-radius: 4px; line-height: 1.6; color: #333; font-size: 10pt; }}
            .action-number {{ display: inline-block; background: #2196F3; color: white; width: 20px; height: 20px; line-height: 20px; text-align: center; border-radius: 50%; font-size: 8pt; font-weight: 700; margin-right: 0.5rem; }}
            .info-box {{ background: #f8f9fa; border: 1px solid #e9ecef; border-left: 4px solid #2196F3; padding: 1rem; border-radius: 4px; margin: 0; }}
            /* Green rather than the neutral info blue: this is the section the
               student is most likely to reread, so it should read as good news. */
            .went-well-box {{ background: #f2faf3; border: 1px solid #d9ecdb; border-left: 4px solid #4CAF50; padding: 1rem; border-radius: 4px; margin: 0; }}
            .info-text {{ margin: 0; line-height: 1.7; color: #333; font-size: 10pt; }}
            .teacher-note {{ background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%); border-left: 5px solid #FF9800; padding: 1rem; border-radius: 4px; line-height: 1.7; color: #333; margin-top: 1.5rem; }}
            .teacher-note-label {{ font-weight: 700; color: #FF9800; margin-bottom: 0.5rem; font-size: 9pt; text-transform: uppercase; letter-spacing: 0.3px; }}
            .teacher-note-text {{ margin: 0; color: #333; font-size: 10pt; }}
        </style>
    </head>
    <body>
        <div class="report-container">
            <div class="report-header">
                <h1 class="student-name-large">{name}</h1>
                <p class="report-date">Progress Report • {date_str}</p>
            </div>

            <div class="summary-section">
                <div class="summary-title">{icon("chart", 14)} Overall Summary</div>
                <p class="summary-text">{report.get('overall_summary', '')}</p>
            </div>

            <div class="performance-grid">
                <div class="performance-card {performance_levels['reading']['color']}">
                    <div class="performance-label">{icon("book", 13)} Reading</div>
                    <div class="performance-value {performance_levels['reading']['color']}">{reading['completion_rate']:.0f}%</div>
                    <div class="performance-status">{performance_levels['reading']['level']}</div>
                    <div class="performance-status">{reading['pages_completed']}/{reading['pages_started']} pages</div>
                </div>
                <div class="performance-card {performance_levels['quiz']['color']}">
                    <div class="performance-label">{icon("pencil", 13)} Quizzes</div>
                    <div class="performance-value {performance_levels['quiz']['color']}">{quiz['accuracy']:.0f}%</div>
                    <div class="performance-status">{performance_levels['quiz']['level']}</div>
                    <div class="performance-status">{quiz['correct']}/{quiz['total']} correct</div>
                </div>
                <div class="performance-card {performance_levels['vocabulary']['color']}">
                    <div class="performance-label">{icon("award", 13)} Vocabulary</div>
                    <div class="performance-value {performance_levels['vocabulary']['color']}">{flashcard['accuracy']:.0f}%</div>
                    <div class="performance-status">{performance_levels['vocabulary']['level']}</div>
                    <div class="performance-status">{flashcard['mastered']} cards mastered</div>
                </div>
            </div>

            {"<div class='report-section'><h2 class='section-header'>" + icon("check", 17) + " What Went Well</h2><div class='went-well-box'><p class='info-text'>" + report.get('what_went_well', '') + "</p></div></div>" if report.get('what_went_well') else ''}

            {"<div class='report-section'><h2 class='section-header'>" + icon("book-open", 17) + " Current Topics & Concepts</h2><div class='info-box'><p class='info-text'>" + report.get('what_youre_learning', '') + "</p></div></div>" if report.get('what_youre_learning') else ''}

            {"<div class='report-section'><h2 class='section-header'>" + icon("search", 17) + " Learning Patterns</h2><div class='info-box'><p class='info-text'>" + report.get('feedback_patterns', '') + "</p></div></div>" if report.get('feedback_patterns') else ''}

            <div class="report-section">
                <h2 class="section-header">{icon("check", 17)} Strengths</h2>
                <ul class="achievement-list">
                    {"".join(f"<li class='achievement-item'>{icon('check', 14)}<span>{s}</span></li>" for s in report.get('your_strengths', []))}
                </ul>
            </div>

            <div class="report-section">
                <h2 class="section-header">{icon("arrow", 17)} Areas for Growth</h2>
                <ul class="growth-list">
                    {"".join(f"<li class='growth-item'>{icon('arrow', 14)}<span>{a}</span></li>" for a in report.get('where_to_focus', []))}
                </ul>
            </div>

            <div class="report-section">
                <h2 class="section-header">{icon("steps", 17)} Action Plan</h2>
                <ol class="action-list">
                    {"".join(f"<li class='action-item'><span class='action-number'>{i+1}</span>{a}</li>" for i, a in enumerate(report.get('your_action_plan', [])))}
                </ol>
            </div>

            <div class="report-section">
                <h2 class="section-header">{icon("target", 17)} Next Steps</h2>
                <div class="info-box">
                    <p class="info-text">{report.get('next_steps', '')}</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return html_content


@report_card_bp.route('/api/students/<int:student_id>/report-summary/pdf', methods=['GET'])
@login_required
@admin_required
def get_report_pdf(student_id):
    """Generate and download report as PDF"""

    if not WEASYPRINT_AVAILABLE:
        return jsonify({
            'error': 'PDF export is unavailable on this server: WeasyPrint requires '
                     'the GTK runtime, which is not installed.'
        }), 503

    try:
        student = User.query.get(student_id)
        if not student or student.role != 'student':
            return jsonify({'error': 'Student not found'}), 404

        # Get all student data
        stats = _get_student_stats(student_id)

        # Shares the cached report with the on-screen view. Before this, the two
        # routes generated independently, so the exported PDF contained different
        # prose from the report the teacher had just been reading.
        report_content, _ = _get_or_generate_report(student, stats)
        if report_content.get('_generation_failed'):
            return jsonify({
                'error': "This report couldn't be generated just now. Please try again in a moment."
            }), 503

        # Get performance levels
        reading_level = _get_performance_level(stats['reading']['completion_rate'])
        quiz_level = _get_performance_level(stats['quiz']['accuracy'])
        vocab_level = _get_performance_level(stats['flashcard']['accuracy'])

        performance_levels = {
            'reading': reading_level,
            'quiz': quiz_level,
            'vocabulary': vocab_level,
        }

        # The roster stores an alias; a teacher sending this home may need the
        # student's real name on it. Request-scoped only — used for this render
        # and never written back to the student record (see _render_report_html
        # on why it is passed as an argument rather than assigned onto `student`).
        name_override = (request.args.get('name') or '').strip()[:120]
        display_name = name_override or student.name

        # Render HTML
        html_content = _render_report_html(student, report_content, stats, performance_levels,
                                           datetime.now().isoformat(), display_name=display_name)

        # Convert to PDF
        pdf_bytes = BytesIO()
        HTML(string=html_content).write_pdf(pdf_bytes)
        pdf_bytes.seek(0)

        # Return PDF file
        safe_name = re.sub(r'[^A-Za-z0-9_-]+', '_', display_name).strip('_') or 'Student'
        filename = f"Report_Card_{safe_name}_{datetime.now().strftime('%Y%m%d')}.pdf"
        return send_file(
            pdf_bytes,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        print(f"Error generating PDF: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return server_error(e, 'The report could not be generated.')
