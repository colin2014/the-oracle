"""Vocabulary flashcards: teachers build a set from the vocabulary terms of
selected book pages, assign it to classes or individual students, and see
per-student performance. Students study assigned sets as flip cards and
self-mark each card ("knew it" / "still learning")."""

import re
from datetime import datetime, timedelta

from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required
from sqlalchemy import and_, or_

from auth import admin_required
from extensions import db
from models import (
    BookVocabulary,
    Class,
    ClassEnrollment,
    Flashcard,
    FlashcardAssignment,
    FlashcardProgress,
    FlashcardSet,
    FlashcardStudySession,
    User,
)
from quiz_routes import _book_meta, _load_page_content

flashcards_bp = Blueprint("flashcards", __name__)

_TAG_RE = re.compile(r"<[^>]+>")


# ---------------------------------------------------------------- helpers

def parse_vocab_terms(text):
    """Parse a page's Vocabulary sidebar text into [{term, definition}].

    Lines look like '<strong>Term</strong>: definition' (or <b>...</b>,
    or plain 'Term - definition'), separated by <br> or newlines."""
    if not text:
        return []
    entries = []
    for line in re.split(r"<br\s*/?>|\n", text):
        line = line.strip()
        if not line:
            continue
        m = re.match(
            r"\s*<(strong|b)>(?P<term>.*?)</\1>\s*:?\s*(?P<defn>.*)",
            line, re.IGNORECASE | re.DOTALL,
        )
        if m:
            term = _TAG_RE.sub("", m.group("term")).strip().rstrip(":").strip()
            defn = _TAG_RE.sub(" ", m.group("defn")).strip()
        else:
            stripped = _TAG_RE.sub("", line).strip()
            parts = None
            for sep in (" – ", " — ", " - ", ": ", " : "):
                if sep in stripped:
                    parts = stripped.split(sep, 1)
                    break
            if not parts:
                continue
            term, defn = parts[0].strip(), parts[1].strip()
        defn = re.sub(r"\s+", " ", defn).strip()
        if term and defn:
            entries.append({"term": term, "definition": defn})
    return entries


def normalize_term(term):
    """Normalize term for duplicate detection (lowercase, strip whitespace)."""
    return term.strip().lower()


def is_duplicate_term(new_term, existing_vocabs):
    """Check if a term already exists (case-insensitive).

    Args:
        new_term: Term to check
        existing_vocabs: List of existing vocabulary items

    Returns:
        (is_duplicate, first_occurrence_term) tuple
    """
    new_term_norm = normalize_term(new_term)

    for existing in existing_vocabs:
        existing_term_norm = normalize_term(existing.term)
        # Simple term match - if term is same (case-insensitive), it's a duplicate
        if new_term_norm == existing_term_norm:
            return True, existing.term

    return False, None


def page_vocab_terms(book_folder, page_id):
    """Vocabulary terms for one page, from sidebar_sections or vocab sidebox."""
    content = _load_page_content(book_folder, page_id)
    if not content:
        return []
    for name, text in (content.get("sidebar_sections") or {}).items():
        if "Vocab" in name:
            terms = parse_vocab_terms(text)
            if terms:
                return terms
    for block in content.get("blocks") or []:
        if block.get("type") == "sidebox" and (
            block.get("style") == "vocab" or "Vocab" in (block.get("title") or "")
        ):
            terms = parse_vocab_terms(block.get("text"))
            if terms:
                return terms
    return []


def _student_assignment_filter(student_id, class_ids):
    conditions = [FlashcardAssignment.student_id == student_id]
    if class_ids:
        conditions.append(and_(
            FlashcardAssignment.class_id.in_(class_ids),
            FlashcardAssignment.student_id.is_(None),
        ))
    return or_(*conditions)


def _student_can_access_set(student_id, set_id):
    class_ids = [e.class_id for e in ClassEnrollment.query.filter_by(student_id=student_id).all()]
    return db.session.query(FlashcardAssignment.id).filter(
        FlashcardAssignment.set_id == set_id,
        _student_assignment_filter(student_id, class_ids),
    ).first() is not None


def flashcard_tasks_for_student(student_id):
    """Serialized flashcard assignments for a student's dashboard."""
    class_ids = [e.class_id for e in ClassEnrollment.query.filter_by(student_id=student_id).all()]
    assignments = (
        FlashcardAssignment.query
        .filter(_student_assignment_filter(student_id, class_ids))
        .order_by(FlashcardAssignment.due_date.asc().nullslast())
        .all()
    )
    if not assignments:
        return []

    set_ids = {a.set_id for a in assignments}
    cards_by_set = {}
    for card in Flashcard.query.filter(Flashcard.set_id.in_(set_ids)).all():
        cards_by_set.setdefault(card.set_id, []).append(card.id)
    all_card_ids = [cid for ids in cards_by_set.values() for cid in ids]
    progress = {}
    if all_card_ids:
        for p in FlashcardProgress.query.filter(
            FlashcardProgress.student_id == student_id,
            FlashcardProgress.card_id.in_(all_card_ids),
        ).all():
            progress[p.card_id] = p

    tasks = []
    seen_sets = set()
    for a in assignments:
        if a.set_id in seen_sets:
            continue  # same set assigned via class and individually: show once
        seen_sets.add(a.set_id)
        card_ids = cards_by_set.get(a.set_id, [])
        reviewed = sum(1 for cid in card_ids if cid in progress)
        mastered = sum(1 for cid in card_ids if progress.get(cid) and progress[cid].last_correct)
        tasks.append({
            "assignment_id": a.id,
            "set_id": a.set_id,
            "title": a.set.title,
            "class_name": a.target_label(),
            "due_date": a.due_date.strftime("%b %d, %Y %I:%M %p") if a.due_date else None,
            "due_date_raw": a.due_date.isoformat() if a.due_date else None,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "card_count": len(card_ids),
            "reviewed": reviewed,
            "mastered": mastered,
            "completed": bool(card_ids) and reviewed >= len(card_ids),
            "link": f"/flashcards/{a.set_id}",
        })
    return tasks


def _set_payload(fset, include_cards=True):
    out = {
        "id": fset.id,
        "title": fset.title,
        "description": fset.description,
        "book_folder": fset.book_folder,
        "card_type": fset.card_type,
        "card_count": len(fset.cards),
        "created_at": fset.created_at.strftime("%b %d, %Y") if fset.created_at else "",
    }
    if include_cards:
        out["cards"] = [{
            "id": c.id, "term": c.term, "definition": c.definition,
            "page_id": c.page_id, "position": c.position,
        } for c in fset.cards]
    return out


def _session_stats(sessions):
    """Aggregate a student's study sessions for one set into a stats dict.

    `sessions` must be ordered by started_at ascending."""
    completed = [s for s in sessions if s.completed]
    total_seconds = sum(s.duration_seconds or 0 for s in sessions)
    best = min((s.duration_seconds for s in completed if s.duration_seconds), default=None)
    avg = (sum(s.duration_seconds or 0 for s in completed) / len(completed)) if completed else None
    last = max((s.started_at for s in sessions if s.started_at), default=None)

    # Improvement: first completed attempt vs the most recent one
    time_improvement = accuracy_improvement = None
    first_acc = last_acc = None
    if len(completed) >= 2:
        first, latest = completed[0], completed[-1]
        if first.duration_seconds and latest.duration_seconds:
            time_improvement = round(first.duration_seconds - latest.duration_seconds, 1)
        first_acc, last_acc = first.accuracy, latest.accuracy
        if first_acc is not None and last_acc is not None:
            accuracy_improvement = last_acc - first_acc
    elif completed:
        first_acc = last_acc = completed[0].accuracy

    return {
        "attempts": len(sessions),
        "completions": len(completed),
        "total_seconds": round(total_seconds),
        "avg_seconds": round(avg, 1) if avg is not None else None,
        "best_seconds": round(best, 1) if best is not None else None,
        "time_improvement": time_improvement,          # seconds faster than first completed try
        "first_accuracy": first_acc,
        "last_accuracy": last_acc,
        "accuracy_improvement": accuracy_improvement,  # percentage points vs first completed try
        "last_session_at": last.isoformat() if last else None,
        "history": [{
            "started_at": s.started_at.isoformat() if s.started_at else None,
            "mode": s.mode,
            "duration_seconds": round(s.duration_seconds or 0, 1),
            "completed": s.completed,
            "accuracy": s.accuracy,
        } for s in sessions[-20:]],
    }


def _sessions_by_student_set(student_ids=None, set_ids=None):
    """{(student_id, set_id): [sessions asc by started_at]}"""
    q = FlashcardStudySession.query
    if student_ids is not None:
        q = q.filter(FlashcardStudySession.student_id.in_(list(student_ids) or [0]))
    if set_ids is not None:
        q = q.filter(FlashcardStudySession.set_id.in_(list(set_ids) or [0]))
    grouped = {}
    for s in q.order_by(FlashcardStudySession.started_at.asc()).all():
        grouped.setdefault((s.student_id, s.set_id), []).append(s)
    return grouped


# ---------------------------------------------------------------- teacher pages

@flashcards_bp.route("/admin/vocabulary")
@login_required
@admin_required
def vocabulary_management():
    """Vocabulary management interface."""
    return render_template("admin_vocabulary.html")


@flashcards_bp.route("/admin/flashcards")
@login_required
@admin_required
def flashcards_home():
    sets = FlashcardSet.query.order_by(FlashcardSet.created_at.desc()).all()
    meta = {}
    rows = []
    for s in sets:
        book_title, _ = _book_meta(s.book_folder, meta)
        rows.append({
            "id": s.id,
            "title": s.title,
            "book_title": book_title,
            "card_type": s.card_type,
            "card_count": len(s.cards),
            "assignment_count": len(s.assignments),
            "created_at": s.created_at.strftime("%b %d, %Y") if s.created_at else "",
        })
    return render_template("admin_flashcards.html", sets=rows)


@flashcards_bp.route("/admin/flashcards/<int:set_id>")
@login_required
@admin_required
def flashcard_detail(set_id):
    fset = FlashcardSet.query.get_or_404(set_id)
    book_title, _ = _book_meta(fset.book_folder)
    classes = Class.query.filter_by(is_archived=False).order_by(Class.name).all()
    students = User.query.filter_by(role="student").order_by(User.name).all()
    return render_template(
        "admin_flashcard_detail.html",
        fset=fset, book_title=book_title, classes=classes, students=students,
    )


# ---------------------------------------------------------------- teacher APIs

@flashcards_bp.route("/admin/api/flashcards/vocab/<book_folder>")
@login_required
@admin_required
def vocab_for_book(book_folder):
    """Vocabulary terms per page of a book (for the page picker)."""
    _, page_titles = _book_meta(book_folder)
    pages = []
    for page_id, title in page_titles.items():
        terms = page_vocab_terms(book_folder, page_id)
        pages.append({"id": page_id, "title": title, "terms": terms})
    return jsonify({"pages": pages})


@flashcards_bp.route("/admin/api/flashcards/pages/<book_folder>")
@login_required
@admin_required
def pages_for_book(book_folder):
    """Lightweight page list for a book (id + title only, for pickers)."""
    _, page_titles = _book_meta(book_folder)
    return jsonify({"pages": [{"id": pid, "title": t} for pid, t in page_titles.items()]})


@flashcards_bp.route("/admin/api/flashcards/ai-generate", methods=["POST"])
@login_required
@admin_required
def ai_generate_cards():
    """Generate flashcard candidates from a page with AI.

    Returns a preview — nothing is saved until the teacher reviews and saves."""
    from ai_generation import generate_flashcards, AIGenerationError
    from quiz_routes import _extract_page_text, _page_title

    data = request.get_json(force=True, silent=True) or {}
    book_folder = (data.get("book_folder") or "").strip()
    page_id = (data.get("page_id") or "").strip()
    if not book_folder or not page_id:
        return jsonify({"error": "book_folder and page_id are required"}), 400

    content = _load_page_content(book_folder, page_id)
    if not content:
        return jsonify({"error": "Page not found"}), 404
    page_text = _extract_page_text(content)
    if not page_text or len(page_text) < 100:
        return jsonify({"error": "This page has too little text to generate cards from"}), 400

    existing_terms = set(data.get("existing_terms") or [])
    try:
        cards = generate_flashcards(
            _page_title(content, page_id), page_text,
            n=data.get("count") or 10,
            existing_terms=existing_terms,
        )
    except AIGenerationError as e:
        return jsonify({"error": str(e)}), 502

    # Drop anything colliding with terms already in the editor (case-insensitive)
    existing_norm = {t.strip().lower() for t in existing_terms}
    cards = [c for c in cards if c["term"].strip().lower() not in existing_norm]
    return jsonify({"ok": True, "cards": [{**c, "page_id": page_id} for c in cards]})


def _clean_cards(raw_cards):
    """Validate a cards payload -> [(page_id, term, definition)] or error str."""
    if not isinstance(raw_cards, list):
        return None, "cards must be a list"
    cleaned = []
    for i, c in enumerate(raw_cards):
        if not isinstance(c, dict):
            return None, f"Card {i + 1} is invalid"
        term = (c.get("term") or "").strip()
        definition = (c.get("definition") or "").strip()
        if not term or not definition:
            return None, f"Card {i + 1} needs both a term and a definition"
        page_id = (c.get("page_id") or "").strip() or None
        cleaned.append((page_id, term, definition, c.get("id")))
    return cleaned, None


@flashcards_bp.route("/admin/api/flashcards", methods=["POST"])
@login_required
@admin_required
def create_set():
    data = request.get_json(force=True, silent=True) or {}
    title = (data.get("title") or "").strip()
    book_folder = (data.get("book_folder") or "").strip()
    card_type = (data.get("card_type") or "flashcard").strip()
    if card_type not in ("flashcard", "matching", "learn"):
        card_type = "flashcard"
    if not title or not book_folder:
        return jsonify({"error": "title and book_folder are required"}), 400
    cards, err = _clean_cards(data.get("cards") or [])
    if err:
        return jsonify({"error": err}), 400
    if not cards:
        return jsonify({"error": "Add at least one card"}), 400

    fset = FlashcardSet(
        title=title,
        book_folder=book_folder,
        card_type=card_type,
        description=(data.get("description") or "").strip() or None,
        created_by_id=current_user.id,
    )
    db.session.add(fset)
    db.session.flush()
    for i, (page_id, term, definition, _) in enumerate(cards):
        db.session.add(Flashcard(
            set_id=fset.id, page_id=page_id, term=term, definition=definition, position=i,
        ))
    db.session.commit()
    return jsonify({"ok": True, "set_id": fset.id})


@flashcards_bp.route("/admin/api/flashcards/<int:set_id>", methods=["PUT"])
@login_required
@admin_required
def update_set(set_id):
    fset = FlashcardSet.query.get(set_id)
    if not fset:
        return jsonify({"error": "Set not found"}), 404
    data = request.get_json(force=True, silent=True) or {}

    title = (data.get("title") or "").strip()
    if title:
        fset.title = title
    if "description" in data:
        fset.description = (data.get("description") or "").strip() or None
    if "card_type" in data:
        card_type = (data.get("card_type") or "flashcard").strip()
        if card_type in ("flashcard", "matching", "learn"):
            fset.card_type = card_type

    if "cards" in data:
        cards, err = _clean_cards(data.get("cards") or [])
        if err:
            return jsonify({"error": err}), 400
        if not cards:
            return jsonify({"error": "A set must keep at least one card"}), 400
        existing = {c.id: c for c in fset.cards}
        kept_ids = set()
        for i, (page_id, term, definition, card_id) in enumerate(cards):
            card = existing.get(card_id) if card_id else None
            if card:  # update in place so student progress is preserved
                card.page_id, card.term, card.definition, card.position = page_id, term, definition, i
                kept_ids.add(card.id)
            else:
                db.session.add(Flashcard(
                    set_id=fset.id, page_id=page_id, term=term, definition=definition, position=i,
                ))
        for card_id, card in existing.items():
            if card_id not in kept_ids:
                db.session.delete(card)  # ORM delete so progress cascades
    db.session.commit()
    return jsonify({"ok": True})


@flashcards_bp.route("/admin/api/flashcards/<int:set_id>", methods=["DELETE"])
@login_required
@admin_required
def delete_set(set_id):
    fset = FlashcardSet.query.get(set_id)
    if not fset:
        return jsonify({"error": "Set not found"}), 404
    db.session.delete(fset)
    db.session.commit()
    return jsonify({"ok": True})


@flashcards_bp.route("/admin/api/flashcards/<int:set_id>/assign", methods=["POST"])
@login_required
@admin_required
def assign_set(set_id):
    fset = FlashcardSet.query.get(set_id)
    if not fset:
        return jsonify({"error": "Set not found"}), 404
    data = request.get_json(force=True, silent=True) or {}
    class_id = data.get("class_id")
    student_id = data.get("student_id")
    if bool(class_id) == bool(student_id):
        return jsonify({"error": "Choose a class or a student"}), 400
    if class_id and not Class.query.get(class_id):
        return jsonify({"error": "Class not found"}), 404
    if student_id and not User.query.get(student_id):
        return jsonify({"error": "Student not found"}), 404

    due_date = None
    if data.get("due_date"):
        try:
            due_date = datetime.fromisoformat(data["due_date"])
        except ValueError:
            return jsonify({"error": "Invalid due date"}), 400

    existing = FlashcardAssignment.query.filter_by(
        set_id=set_id,
        class_id=class_id or None,
        student_id=student_id or None,
    ).first()
    if existing:
        return jsonify({"error": "Already assigned to that target"}), 409

    a = FlashcardAssignment(
        set_id=set_id, class_id=class_id or None, student_id=student_id or None,
        due_date=due_date, assigned_by_id=current_user.id,
    )
    db.session.add(a)
    db.session.commit()
    return jsonify({"ok": True, "assignment_id": a.id})


@flashcards_bp.route("/admin/api/flashcards/assignment/<int:assignment_id>", methods=["DELETE"])
@login_required
@admin_required
def delete_assignment(assignment_id):
    a = FlashcardAssignment.query.get(assignment_id)
    if not a:
        return jsonify({"error": "Assignment not found"}), 404
    db.session.delete(a)
    db.session.commit()
    return jsonify({"ok": True})


@flashcards_bp.route("/admin/api/flashcards/<int:set_id>/assignments")
@login_required
@admin_required
def list_assignments(set_id):
    rows = FlashcardAssignment.query.filter_by(set_id=set_id).order_by(FlashcardAssignment.created_at.desc()).all()
    return jsonify({"assignments": [{
        "id": a.id,
        "target": a.target_label(),
        "target_type": "student" if a.student_id else "class",
        "due_date": a.due_date.strftime("%b %d, %Y %H:%M") if a.due_date else None,
        "created_at": a.created_at.strftime("%b %d, %Y") if a.created_at else "",
    } for a in rows]})


@flashcards_bp.route("/admin/api/flashcards/<int:set_id>/performance")
@login_required
@admin_required
def set_performance(set_id):
    """Per-student performance for everyone the set is assigned to."""
    fset = FlashcardSet.query.get(set_id)
    if not fset:
        return jsonify({"error": "Set not found"}), 404
    card_ids = [c.id for c in fset.cards]

    # Audience = students of assigned classes + individually assigned students
    students = {}
    for a in fset.assignments:
        if a.student_id and a.student:
            students[a.student_id] = a.student
        elif a.class_id:
            for enr in ClassEnrollment.query.filter_by(class_id=a.class_id).all():
                students[enr.student_id] = enr.student

    progress_by_student = {}
    if card_ids and students:
        rows = FlashcardProgress.query.filter(
            FlashcardProgress.card_id.in_(card_ids),
            FlashcardProgress.student_id.in_(list(students)),
        ).all()
        for p in rows:
            progress_by_student.setdefault(p.student_id, []).append(p)

    session_groups = _sessions_by_student_set(student_ids=list(students) or None, set_ids=[set_id]) if students else {}

    card_lookup = {c.id: c for c in fset.cards}
    out = []
    for sid, student in sorted(students.items(), key=lambda kv: kv[1].name.lower()):
        rows = progress_by_student.get(sid, [])
        session_stats = _session_stats(session_groups.get((sid, set_id), []))
        correct = sum(p.correct_count for p in rows)
        incorrect = sum(p.incorrect_count for p in rows)
        attempts = correct + incorrect
        last = max((p.last_reviewed_at for p in rows if p.last_reviewed_at), default=None)
        struggling = [
            card_lookup[p.card_id].term for p in rows
            if p.card_id in card_lookup and p.last_correct is False
        ]
        out.append({
            "student_id": sid,
            "name": student.name,
            "cards_total": len(card_ids),
            "cards_seen": len(rows),
            "cards_mastered": sum(1 for p in rows if p.last_correct),
            "attempts": attempts,
            "accuracy": round(correct * 100 / attempts) if attempts else None,
            "last_studied": last.strftime("%b %d, %Y %H:%M") if last else None,
            "struggling_terms": sorted(struggling)[:10],
            "sessions": session_stats,
        })
    return jsonify({"set": _set_payload(fset, include_cards=False), "students": out})


# ---------------------------------------------------------------- student pages

@flashcards_bp.route("/flashcards/<int:set_id>")
@login_required
def study_page(set_id):
    fset = FlashcardSet.query.get_or_404(set_id)
    if not current_user.is_admin() and not _student_can_access_set(current_user.id, set_id):
        from flask import abort
        abort(403)
    book_title, _ = _book_meta(fset.book_folder)
    return render_template("flashcards_study.html", fset=fset, book_title=book_title, card_type=fset.card_type)


@flashcards_bp.route("/flashcards/<int:set_id>/difficulty")
@login_required
def study_difficulty(set_id):
    """Student's difficulty view for a flashcard set."""
    fset = FlashcardSet.query.get_or_404(set_id)
    if not current_user.is_admin() and not _student_can_access_set(current_user.id, set_id):
        from flask import abort
        abort(403)
    book_title, _ = _book_meta(fset.book_folder)
    return render_template("flashcard_difficulty.html", fset=fset, book_title=book_title)


@flashcards_bp.route("/my-difficulty")
@login_required
def my_difficulty_dashboard():
    """Student's difficulty dashboard across all their flashcard sets."""
    if current_user.is_admin():
        from flask import redirect, url_for
        return redirect(url_for("admin.analytics_hub"))
    return render_template("my_flashcard_difficulty.html")


@flashcards_bp.route("/api/flashcards/<int:set_id>/cards")
@login_required
def study_cards(set_id):
    fset = FlashcardSet.query.get(set_id)
    if not fset:
        return jsonify({"error": "Set not found"}), 404
    if not current_user.is_admin() and not _student_can_access_set(current_user.id, set_id):
        return jsonify({"error": "Not assigned to you"}), 403

    progress = {}
    if not current_user.is_admin():
        rows = FlashcardProgress.query.filter(
            FlashcardProgress.student_id == current_user.id,
            FlashcardProgress.card_id.in_([c.id for c in fset.cards] or [0]),
        ).all()
        progress = {p.card_id: p for p in rows}

    cards = []
    for c in fset.cards:
        p = progress.get(c.id)
        cards.append({
            "id": c.id,
            "term": c.term,
            "definition": c.definition,
            "correct_count": p.correct_count if p else 0,
            "incorrect_count": p.incorrect_count if p else 0,
            "last_correct": p.last_correct if p else None,
        })
    return jsonify({"set": _set_payload(fset, include_cards=False), "cards": cards})


@flashcards_bp.route("/api/flashcards/<int:set_id>/leaderboard")
@login_required
def matching_leaderboard(set_id):
    """Top 5 fastest completed matching times for a set (one entry per student)."""
    fset = FlashcardSet.query.get(set_id)
    if not fset:
        return jsonify({"error": "Set not found"}), 404
    if not current_user.is_admin() and not _student_can_access_set(current_user.id, set_id):
        return jsonify({"error": "Not assigned to you"}), 403

    sessions = FlashcardStudySession.query.filter_by(
        set_id=set_id, mode="matching", completed=True
    ).all()

    best_by_student = {}
    for s in sessions:
        if not s.duration_seconds:
            continue
        cur = best_by_student.get(s.student_id)
        if cur is None or s.duration_seconds < cur.duration_seconds:
            best_by_student[s.student_id] = s

    ranked = sorted(best_by_student.values(), key=lambda s: s.duration_seconds)
    your_best = best_by_student.get(current_user.id)
    return jsonify({
        "leaderboard": [{
            "name": s.student.name if s.student else "Unknown",
            "seconds": round(s.duration_seconds, 1),
            "is_you": s.student_id == current_user.id,
        } for s in ranked[:5]],
        "your_best": round(your_best.duration_seconds, 1) if your_best else None,
        "your_rank": (ranked.index(your_best) + 1) if your_best else None,
    })


@flashcards_bp.route("/api/flashcards/my-stats")
@login_required
def my_flashcard_stats():
    """Aggregated flashcard analytics for the current student's analytics page."""
    if current_user.is_admin():
        return jsonify({"error": "not available for admins"}), 403

    sessions_by_set = {}
    for (sid, set_id), sessions in _sessions_by_student_set(student_ids=[current_user.id]).items():
        sessions_by_set[set_id] = sessions

    # Assigned sets (title/card_count/mastered) plus any set the student has studied
    tasks = {t["set_id"]: t for t in flashcard_tasks_for_student(current_user.id)}
    extra_set_ids = [sid for sid in sessions_by_set if sid not in tasks]
    extra_sets = {s.id: s for s in FlashcardSet.query.filter(FlashcardSet.id.in_(extra_set_ids or [0])).all()}

    all_sessions = [s for sessions in sessions_by_set.values() for s in sessions]
    completed_sessions = [s for s in all_sessions if s.completed]
    total_correct = sum(s.cards_correct or 0 for s in completed_sessions)
    total_answered = sum((s.cards_correct or 0) + (s.cards_incorrect or 0) for s in completed_sessions)

    # Cards this student currently has right (last review correct)
    progress_rows = FlashcardProgress.query.filter_by(student_id=current_user.id).all()
    cards_known = sum(1 for p in progress_rows if p.last_correct)
    cards_seen = len(progress_rows)

    sets_out = []
    for set_id in set(tasks) | set(sessions_by_set):
        sessions = sessions_by_set.get(set_id, [])
        stats = _session_stats(sessions) if sessions else None
        task = tasks.get(set_id)
        fset = extra_sets.get(set_id)
        if not task and not fset:
            continue
        matching_best = min(
            (s.duration_seconds for s in sessions
             if s.completed and s.mode == "matching" and s.duration_seconds),
            default=None,
        )
        sets_out.append({
            "set_id": set_id,
            "title": task["title"] if task else fset.title,
            "link": f"/flashcards/{set_id}",
            "card_count": task["card_count"] if task else len(fset.cards),
            "mastered": task["mastered"] if task else None,
            "rounds": stats["completions"] if stats else 0,
            "total_seconds": stats["total_seconds"] if stats else 0,
            "last_accuracy": stats["last_accuracy"] if stats else None,
            "accuracy_improvement": stats["accuracy_improvement"] if stats else None,
            "best_match_seconds": round(matching_best, 1) if matching_best else None,
            "last_session_at": stats["last_session_at"] if stats else None,
        })
    sets_out.sort(key=lambda s: s["last_session_at"] or "", reverse=True)

    return jsonify({
        "totals": {
            "rounds_completed": len(completed_sessions),
            "total_seconds": round(sum(s.duration_seconds or 0 for s in all_sessions)),
            "cards_known": cards_known,
            "cards_seen": cards_seen,
            "accuracy": round(total_correct * 100 / total_answered) if total_answered else None,
        },
        "sets": sets_out,
    })


@flashcards_bp.route("/api/flashcards/<int:set_id>/review", methods=["POST"])
@login_required
def record_review(set_id):
    if current_user.is_admin():
        return jsonify({"ok": True, "skipped": "admin preview"})
    if not _student_can_access_set(current_user.id, set_id):
        return jsonify({"error": "Not assigned to you"}), 403

    data = request.get_json(force=True, silent=True) or {}
    card_id = data.get("card_id")
    correct = data.get("correct")
    if not card_id or not isinstance(correct, bool):
        return jsonify({"error": "card_id and correct (true/false) required"}), 400
    card = Flashcard.query.get(card_id)
    if not card or card.set_id != set_id:
        return jsonify({"error": "Card not found in this set"}), 404

    p = FlashcardProgress.query.filter_by(card_id=card_id, student_id=current_user.id).first()
    if not p:
        p = FlashcardProgress(card_id=card_id, student_id=current_user.id,
                              correct_count=0, incorrect_count=0)
        db.session.add(p)
    p.record_result(correct)
    db.session.commit()
    return jsonify({"ok": True})


@flashcards_bp.route("/api/flashcards/<int:set_id>/matching-review", methods=["POST"])
@login_required
def record_matching_review(set_id):
    """Record results for a complete matching round."""
    if current_user.is_admin():
        return jsonify({"ok": True, "skipped": "admin preview"})
    if not _student_can_access_set(current_user.id, set_id):
        return jsonify({"error": "Not assigned to you"}), 403

    data = request.get_json(force=True, silent=True) or {}
    results = data.get("results", [])  # [{card_id, correct}, ...]
    if not results:
        return jsonify({"error": "No results provided"}), 400

    fset = FlashcardSet.query.get(set_id)
    if not fset:
        return jsonify({"error": "Set not found"}), 404

    card_ids = {c.id for c in fset.cards}
    for result in results:
        card_id = result.get("card_id")
        correct = result.get("correct")
        dwell_ms = result.get("dwell_ms", 0)
        if not card_id or not isinstance(correct, bool) or card_id not in card_ids:
            continue

        p = FlashcardProgress.query.filter_by(card_id=card_id, student_id=current_user.id).first()
        if not p:
            p = FlashcardProgress(card_id=card_id, student_id=current_user.id,
                                  correct_count=0, incorrect_count=0, total_dwell_seconds=0.0)
            db.session.add(p)
        p.record_result(correct)
        p.total_dwell_seconds += (dwell_ms or 0) / 1000.0

    db.session.commit()
    return jsonify({"ok": True})


@flashcards_bp.route("/api/flashcards/<int:set_id>/learn-answer", methods=["POST"])
@login_required
def record_learn_answer(set_id):
    """Record a single learn mode answer."""
    if current_user.is_admin():
        return jsonify({"ok": True, "skipped": "admin preview"})
    if not _student_can_access_set(current_user.id, set_id):
        return jsonify({"error": "Not assigned to you"}), 403

    data = request.get_json(force=True, silent=True) or {}
    card_id = data.get("card_id")
    selected_card_id = data.get("selected_card_id")

    if not card_id or not selected_card_id:
        return jsonify({"error": "card_id and selected_card_id required"}), 400

    card = Flashcard.query.get(card_id)
    if not card or card.set_id != set_id:
        return jsonify({"error": "Card not found in this set"}), 404

    correct = (card_id == selected_card_id)

    p = FlashcardProgress.query.filter_by(card_id=card_id, student_id=current_user.id).first()
    if not p:
        p = FlashcardProgress(card_id=card_id, student_id=current_user.id,
                              correct_count=0, incorrect_count=0)
        db.session.add(p)

    p.record_result(correct)
    db.session.commit()

    return jsonify({"ok": True, "correct": correct})


# ---------------------------------------------------------------- study sessions & analytics

@flashcards_bp.route("/api/flashcards/<int:set_id>/session", methods=["POST"])
@login_required
def record_session(set_id):
    """Record one study attempt (also accepts navigator.sendBeacon payloads)."""
    if current_user.is_admin():
        return jsonify({"ok": True, "skipped": "admin preview"})
    if not _student_can_access_set(current_user.id, set_id):
        return jsonify({"error": "Not assigned to you"}), 403

    data = request.get_json(force=True, silent=True) or {}
    mode = data.get("mode") if data.get("mode") in ("flashcard", "matching", "learn") else "flashcard"
    try:
        duration = max(0.0, float(data.get("duration_ms") or 0) / 1000.0)
    except (TypeError, ValueError):
        duration = 0.0
    if duration < 1:  # ignore accidental instant opens
        return jsonify({"ok": True, "skipped": "too short"})

    def _int(v):
        try:
            return max(0, int(v))
        except (TypeError, ValueError):
            return 0

    s = FlashcardStudySession(
        set_id=set_id,
        student_id=current_user.id,
        mode=mode,
        started_at=datetime.now() - timedelta(seconds=duration),
        duration_seconds=round(duration, 1),
        completed=bool(data.get("completed")),
        cards_total=_int(data.get("cards_total")),
        cards_correct=_int(data.get("cards_correct")),
        cards_incorrect=_int(data.get("cards_incorrect")),
    )
    db.session.add(s)
    db.session.commit()
    return jsonify({"ok": True})


@flashcards_bp.route("/api/flashcards/my-analytics")
@login_required
def my_analytics():
    """Per-set study analytics for the logged-in student's dashboard."""
    tasks = flashcard_tasks_for_student(current_user.id)
    set_ids = [t["set_id"] for t in tasks]
    grouped = _sessions_by_student_set(student_ids=[current_user.id], set_ids=set_ids)

    out = []
    for t in tasks:
        sessions = grouped.get((current_user.id, t["set_id"]), [])
        stats = _session_stats(sessions)
        out.append({
            "set_id": t["set_id"],
            "title": t["title"],
            "card_count": t["card_count"],
            "mastered": t["mastered"],
            "reviewed": t["reviewed"],
            **stats,
        })
    return jsonify({"sets": out})


@flashcards_bp.route("/admin/api/flashcards/student/<int:student_id>/analytics")
@login_required
@admin_required
def student_flashcard_analytics(student_id):
    """One student's analytics across every flashcard set assigned to them."""
    student = User.query.get(student_id)
    if not student:
        return jsonify({"error": "Student not found"}), 404
    tasks = flashcard_tasks_for_student(student_id)
    set_ids = [t["set_id"] for t in tasks]
    grouped = _sessions_by_student_set(student_ids=[student_id], set_ids=set_ids)

    out = []
    for t in tasks:
        sessions = grouped.get((student_id, t["set_id"]), [])
        stats = _session_stats(sessions)
        out.append({
            "set_id": t["set_id"],
            "title": t["title"],
            "card_count": t["card_count"],
            "mastered": t["mastered"],
            "reviewed": t["reviewed"],
            **stats,
        })
    return jsonify({"student": {"id": student.id, "name": student.name}, "sets": out})


@flashcards_bp.route("/admin/api/flashcards/analytics")
@login_required
@admin_required
def flashcards_analytics_overview():
    """Flashcard performance rows (one per student+set) for the analytics hub.

    Optional filters: ?class_id=&student_id="""
    class_id = request.args.get("class_id", type=int)
    student_id = request.args.get("student_id", type=int)

    if student_id:
        u = User.query.get(student_id)
        students = [u] if u else []
    elif class_id:
        students = sorted(
            (e.student for e in ClassEnrollment.query.filter_by(class_id=class_id).all() if e.student),
            key=lambda s: (s.name or "").lower(),
        )
    else:
        students = User.query.filter_by(role="student").order_by(User.name).all()

    grouped = _sessions_by_student_set(student_ids=[s.id for s in students]) if students else {}

    rows = []
    for student in students:
        for t in flashcard_tasks_for_student(student.id):
            sessions = grouped.get((student.id, t["set_id"]), [])
            stats = _session_stats(sessions)
            rows.append({
                "student_id": student.id,
                "student_name": student.name,
                "student_avatar": student.avatar,
                "set_id": t["set_id"],
                "title": t["title"],
                "card_count": t["card_count"],
                "mastered": t["mastered"],
                "reviewed": t["reviewed"],
                **stats,
            })
    return jsonify({"rows": rows})


# ── Card difficulty heatmap ──

@flashcards_bp.route("/admin/api/flashcards/card-difficulty")
@login_required
@admin_required
def card_difficulty_admin():
    """Card difficulty heatmap data for admin analytics.

    Query params (all optional):
    - class_id: Filter to one class
    - student_id: Filter to one student
    - set_id: Filter to one flashcard set
    """
    class_id = request.args.get("class_id", type=int)
    student_id = request.args.get("student_id", type=int)
    set_id = request.args.get("set_id", type=int)

    # Determine which students to include
    if student_id:
        students = [User.query.get(student_id)] if User.query.get(student_id) else []
    elif class_id:
        students = [e.student for e in ClassEnrollment.query.filter_by(class_id=class_id).all() if e.student]
    else:
        students = User.query.filter_by(role="student").all()

    student_ids = [s.id for s in students]
    if not student_ids:
        return jsonify({"cards": [], "meta": {"total_students": 0, "total_attempts": 0}})

    # Filter to specific set if provided
    if set_id:
        fset = FlashcardSet.query.get(set_id)
        if not fset:
            return jsonify({"error": "Set not found"}), 404
        card_ids = [c.id for c in fset.cards]
        set_filter = [set_id]
    else:
        card_ids = None  # all cards
        set_filter = None

    # Get progress records for these students
    q = FlashcardProgress.query.filter(FlashcardProgress.student_id.in_(student_ids))
    if card_ids:
        q = q.filter(FlashcardProgress.card_id.in_(card_ids))
    progress_records = q.all()

    # Aggregate by card
    card_stats = {}
    for p in progress_records:
        if p.card_id not in card_stats:
            card_stats[p.card_id] = {
                "correct_count": 0,
                "incorrect_count": 0,
                "total_dwell_seconds": 0.0,
                "studied_by_count": set(),
            }
        card_stats[p.card_id]["correct_count"] += p.correct_count
        card_stats[p.card_id]["incorrect_count"] += p.incorrect_count
        card_stats[p.card_id]["total_dwell_seconds"] += p.total_dwell_seconds
        card_stats[p.card_id]["studied_by_count"].add(p.student_id)

    # Build card list with difficulty scores
    cards_to_fetch = list(card_stats.keys())
    if not cards_to_fetch:
        return jsonify({"cards": [], "meta": {"total_students": len(students), "total_attempts": 0}})

    all_cards = Flashcard.query.filter(Flashcard.id.in_(cards_to_fetch)).all()
    card_lookup = {c.id: c for c in all_cards}

    result_cards = []
    total_attempts = 0
    for card_id, stats in card_stats.items():
        card = card_lookup.get(card_id)
        if not card:
            continue

        correct = stats["correct_count"]
        incorrect = stats["incorrect_count"]
        total = correct + incorrect
        difficulty = round(incorrect / total * 100, 1) if total > 0 else 0
        avg_dwell_seconds = round(stats["total_dwell_seconds"] / total, 2) if total > 0 else 0

        total_attempts += total
        result_cards.append({
            "id": card_id,
            "term": card.term,
            "definition": card.definition,
            "page_id": card.page_id,
            "difficulty": difficulty,
            "correct_count": correct,
            "incorrect_count": incorrect,
            "total_attempts": total,
            "total_dwell_seconds": round(stats["total_dwell_seconds"], 2),
            "avg_dwell_seconds": avg_dwell_seconds,
            "studied_by_count": len(stats["studied_by_count"]),
        })

    # Sort by difficulty (hardest first)
    result_cards.sort(key=lambda x: -x["difficulty"])

    return jsonify({
        "cards": result_cards,
        "meta": {
            "total_students": len(students),
            "total_attempts": total_attempts,
        }
    })


@flashcards_bp.route("/api/flashcards/my-difficulty")
@login_required
def my_difficulty():
    """Card difficulty data for the logged-in student across their assigned sets."""
    # Get all sets assigned to this student
    class_ids = [e.class_id for e in ClassEnrollment.query.filter_by(student_id=current_user.id).all()]
    assignments = (
        FlashcardAssignment.query
        .filter(_student_assignment_filter(current_user.id, class_ids))
        .all()
    )

    if not assignments:
        return jsonify({"sets": []})

    set_ids = [a.set_id for a in assignments]

    # Get cards for these sets
    all_cards = Flashcard.query.filter(Flashcard.set_id.in_(set_ids)).all()
    card_ids = [c.id for c in all_cards]

    if not card_ids:
        return jsonify({"sets": []})

    # Get progress for this student on these cards
    progress_records = FlashcardProgress.query.filter(
        FlashcardProgress.student_id == current_user.id,
        FlashcardProgress.card_id.in_(card_ids),
    ).all()

    progress_by_card = {p.card_id: p for p in progress_records}
    card_lookup = {c.id: c for c in all_cards}

    # Group by set
    set_data = {}
    for set_id in set_ids:
        set_cards = [c for c in all_cards if c.set_id == set_id]
        card_difficulty = []

        for card in set_cards:
            p = progress_by_card.get(card.id)
            if p:
                correct = p.correct_count
                incorrect = p.incorrect_count
                total = correct + incorrect
                difficulty = round(incorrect / total * 100, 1) if total > 0 else 0
                card_difficulty.append({
                    "id": card.id,
                    "term": card.term,
                    "definition": card.definition,
                    "difficulty": difficulty,
                    "correct_count": correct,
                    "incorrect_count": incorrect,
                    "total_attempts": total,
                    "last_correct": p.last_correct,
                    "mastered": p.is_mastered,
                    "correct_streak": p.correct_streak or 0,
                    "avg_dwell_seconds": p.avg_dwell_seconds,
                })

        if card_difficulty:
            # Sort by difficulty (hardest first)
            card_difficulty.sort(key=lambda x: -x["difficulty"])
            fset = FlashcardSet.query.get(set_id)
            set_data[set_id] = {
                "set_id": set_id,
                "title": fset.title if fset else "Unknown",
                "cards": card_difficulty,
            }

    return jsonify({"sets": list(set_data.values())})


# ────────────────────────────────────────────────────────────────

# ---------------------------------------------------------------- book vocabulary management

@flashcards_bp.route("/admin/api/vocabulary/<book_folder>")
@login_required
@admin_required
def get_book_vocabulary(book_folder):
    """Get all vocabulary for a book."""
    book_title, _ = _book_meta(book_folder)
    if not book_title:
        return jsonify({"error": "Book not found"}), 404

    vocabs = BookVocabulary.query.filter_by(book_folder=book_folder).order_by(BookVocabulary.term).all()
    return jsonify({"book_title": book_title, "vocabulary": [{
        "id": v.id,
        "term": v.term,
        "definition": v.definition,
        "page_id": v.page_id,
        "updated_at": v.updated_at.isoformat() if v.updated_at else None,
    } for v in vocabs]})


@flashcards_bp.route("/admin/api/vocabulary/<book_folder>/scan", methods=["POST"])
@login_required
@admin_required
def scan_book_vocabulary(book_folder):
    """Scan book pages and extract new vocabulary terms.

    Skips any term that already exists (case-insensitive), keeping the first definition.
    """
    book_title, page_titles = _book_meta(book_folder)
    if not book_title:
        return jsonify({"error": "Book not found"}), 404

    # Get existing vocabulary for this book
    existing_vocabs = BookVocabulary.query.filter_by(book_folder=book_folder).all()

    extracted = []
    skipped_duplicates = []
    new_vocab_for_scan = []  # Track new terms found in this scan to catch duplicates within scan

    for page_id in page_titles.keys():
        terms = page_vocab_terms(book_folder, page_id)
        for term_data in terms:
            # Check against existing vocabulary
            is_dup, dup_term = is_duplicate_term(term_data["term"], existing_vocabs)

            # Also check against terms extracted in THIS scan
            if not is_dup:
                is_dup, dup_term = is_duplicate_term(term_data["term"], new_vocab_for_scan)

            if is_dup:
                skipped_duplicates.append({
                    "term": term_data["term"],
                    "duplicate_of": dup_term
                })
            else:
                # Create a temporary object to track for duplicate checking
                class TempVocab:
                    def __init__(self, term, definition):
                        self.term = term
                        self.definition = definition

                vocab = BookVocabulary(
                    book_folder=book_folder,
                    page_id=page_id,
                    term=term_data["term"],
                    definition=term_data["definition"]
                )
                db.session.add(vocab)
                extracted.append(term_data["term"])
                new_vocab_for_scan.append(TempVocab(term_data["term"], term_data["definition"]))

    db.session.commit()
    return jsonify({
        "ok": True,
        "new_terms_added": len(extracted),
        "terms": extracted,
        "duplicates_skipped": len(skipped_duplicates),
        "skipped_details": skipped_duplicates[:50]  # Return first 50 for display
    })


@flashcards_bp.route("/admin/api/vocabulary/<int:vocab_id>", methods=["PUT"])
@login_required
@admin_required
def update_vocabulary(vocab_id):
    """Update a vocabulary term."""
    vocab = BookVocabulary.query.get(vocab_id)
    if not vocab:
        return jsonify({"error": "Vocabulary not found"}), 404

    data = request.get_json(force=True, silent=True) or {}
    term = (data.get("term") or "").strip()
    definition = (data.get("definition") or "").strip()

    if not term or not definition:
        return jsonify({"error": "Term and definition are required"}), 400

    # Check for duplicates with other terms in the same book (excluding self)
    existing_vocabs = BookVocabulary.query.filter(
        BookVocabulary.book_folder == vocab.book_folder,
        BookVocabulary.id != vocab_id
    ).all()

    is_dup, dup_term = is_duplicate_term(term, existing_vocabs)
    if is_dup:
        return jsonify({
            "error": f"The term '{dup_term}' already exists in this book.",
            "duplicate_of": dup_term
        }), 409

    vocab.term = term
    vocab.definition = definition
    vocab.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"ok": True})


@flashcards_bp.route("/admin/api/vocabulary/<int:vocab_id>", methods=["DELETE"])
@login_required
@admin_required
def delete_vocabulary(vocab_id):
    """Delete a vocabulary term."""
    vocab = BookVocabulary.query.get(vocab_id)
    if not vocab:
        return jsonify({"error": "Vocabulary not found"}), 404

    db.session.delete(vocab)
    db.session.commit()
    return jsonify({"ok": True})


@flashcards_bp.route("/admin/api/vocabulary/<book_folder>/delete-all", methods=["DELETE"])
@login_required
@admin_required
def delete_all_vocabulary(book_folder):
    """Delete all vocabulary terms for a book."""
    book_title, _ = _book_meta(book_folder)
    if not book_title:
        return jsonify({"error": "Book not found"}), 404

    count = BookVocabulary.query.filter_by(book_folder=book_folder).delete()
    db.session.commit()
    return jsonify({"ok": True, "deleted": count})
