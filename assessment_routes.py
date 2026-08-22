"""Assessment hub: the single operational page for Test Builder, Quizzes and Flashcards.

Tests are run from here — live join codes, closing a test, and click-through to
per-student progress all live on this page. Only the *authoring* of a paper (the
question-bank tree, auto-generate, reordering) stays at its own URL in
test_routes.py / test_builder.html; that UI is substantial and inlining it would
put a heavyweight editor in the same viewport as live invigilation.

Flashcards and Quizzes keep the summarize-and-deep-link treatment — they have
full-featured pages elsewhere and no live-session concept to surface.
"""

from flask import Blueprint, jsonify, render_template
from flask_login import login_required

from auth import admin_required
from models import FlashcardSet, QuizQuestion, TestAnswer, TestAssignment, TestPaper

assessment_bp = Blueprint("assessment", __name__)


@assessment_bp.route("/assessment")
@login_required
@admin_required
def assessment_hub():
    return render_template("assessment_hub.html")


@assessment_bp.route("/admin/api/assessment/summary")
@login_required
@admin_required
def assessment_summary():
    # Imported here rather than at module scope purely to keep the blueprint's
    # import surface to models — the helper is test-domain logic that lives with
    # the routes that own it.
    from test_routes import _assignment_target_count

    papers = TestPaper.query.order_by(TestPaper.updated_at.desc()).all()
    pending_review_count = TestAnswer.query.filter_by(status="pending").count()

    assignments_by_paper = {}
    for a in TestAssignment.query.order_by(TestAssignment.created_at.desc()).all():
        assigned = _assignment_target_count(a)
        submitted = sum(1 for s in a.submissions if s.status != "in_progress")
        in_progress = sum(1 for s in a.submissions if s.status == "in_progress")
        assignments_by_paper.setdefault(a.test_paper_id, []).append({
            "id": a.id,
            "target_label": a.target_label(),
            "access_code": a.access_code,
            "is_live": a.access_code is not None,
            "assigned_count": assigned,
            "submitted_count": submitted,
            "in_progress_count": in_progress,
            # A live assignment nobody is targeted by can never auto-retire, so the
            # UI flags it and offers Close rather than leaving it stuck.
            "is_orphaned": a.access_code is not None and assigned == 0,
            "created_at": a.created_at.strftime("%b %d, %Y") if a.created_at else None,
        })

    return jsonify({
        "flashcards": {
            "set_count": FlashcardSet.query.count(),
        },
        "quiz": {
            "question_count": QuizQuestion.query.count(),
        },
        "test_builder": {
            "pending_review_count": pending_review_count,
            "papers": [{
                "id": p.id,
                "title": p.title,
                "status": p.status,
                "question_count": len(p.paper_questions),
                "total_marks": p.total_marks,
                "has_hl_only_questions": p.has_hl_only_questions,
                "assignments": assignments_by_paper.get(p.id, []),
            } for p in papers],
        },
    })
