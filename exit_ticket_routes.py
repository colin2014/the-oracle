"""Exit tickets: teacher editing, assigning and results; student attempts with automatic marking.

Students never receive correct answers before submitting, and match/order questions are shuffled
per attempt with opaque tokens (see exit_ticket_logic). Written answers are marked by AI in a
background thread so a student's page never waits on the API.
"""
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from types import SimpleNamespace

from flask import Blueprint, abort, current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_

import exit_ticket_logic as L
from auth import admin_required
from db_cleanup import purge_dependents
from extensions import db
from models import (Class, ClassEnrollment, ExitTicket, ExitTicketAnswer, ExitTicketAssignment, ExitTicketQuestion,
                    ExitTicketSubmission, UnitPlanTopic, User)
from safe_errors import server_error

exit_bp = Blueprint("exit_tickets", __name__, url_prefix="/exit-tickets")

MAX_ATTEMPTS = 10                      # per student per ticket; also bounds AI marking cost
LOW_CONFIDENCE = 0.7                   # AI marks below this are flagged for the teacher
_executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="exit-ticket-marking")
_in_flight = set()
_in_flight_lock = threading.Lock()


def _err(message, status=400):
    return jsonify({"success": False, "error": message}), status


# =========================================================================== marking machinery

def _make_snapshot(ticket):
    """The ticket's current questions (with their answers), as an attempt takes them."""
    return {"version": ticket.version, "questions": [
        {"id": q.id, "qtype": q.qtype, "prompt": q.prompt, "marks": q.marks, "data": q.data_dict()} for q in ticket.questions]}


def _snap_questions(sub):
    """The questions THIS attempt was taken on, as objects the logic module understands.

    Attempts always use their own copy, so editing or removing a question later never changes how an
    attempt was marked or how its review looks. (Attempts that predate snapshots fall back to the ticket.)
    """
    try:
        snap = json.loads(sub.snapshot) if sub.snapshot else None
    except ValueError:
        snap = None
    if not isinstance(snap, dict):
        snap = _make_snapshot(sub.ticket)
    out = []
    for q in snap.get("questions", []):
        data = q.get("data") if isinstance(q.get("data"), dict) else {}
        out.append(SimpleNamespace(id=q["id"], qtype=q["qtype"], prompt=q.get("prompt", ""), marks=float(q.get("marks") or 0),
                                   data=json.dumps(data), data_dict=(lambda d=data: d)))
    return out


def _fingerprint(questions):
    """A stable description of the questions, to tell whether a save actually changed anything."""
    return json.dumps([[q.qtype, q.prompt, float(q.marks), q.data_dict()] for q in questions], sort_keys=True)


def _finalise(sub):
    """Recompute an attempt's totals from its answers.

    The total is out of the questions this attempt actually contained, using the marks recorded when
    it was submitted (marks_possible). If the teacher later adds a question to the ticket, students who
    already finished are not suddenly marked out of a bigger number.
    """
    answers = list(sub.answers)
    sub.total_possible = round(sum(a.marks_possible or 0 for a in answers), 2) if answers else sub.ticket.total_marks
    sub.total_awarded = round(sum(a.marks_awarded or 0 for a in answers), 2)


def _written_pending(sub):
    return sum(1 for a in sub.answers if a.status == "pending")


def _run_ai_marking(app, submission_id, own_session=True):
    """Mark every pending written answer of one attempt. Runs in a worker thread (own_session) or inline."""
    def work():
        sub = db.session.get(ExitTicketSubmission, submission_id)
        if sub is None:
            return
        snap = {q.id: q for q in _snap_questions(sub)}
        for answer in list(sub.answers):
            if answer.status != "pending":
                continue
            q = snap.get(answer.question_id) or answer.question
            try:
                text = json.loads(answer.response) if answer.response else ""
            except ValueError:
                text = ""
            result = L.ai_mark(q.prompt, q.marks, q.data_dict(), text if isinstance(text, str) else "")
            answer.ai_tries = (answer.ai_tries or 0) + 1
            if result:
                answer.marks_awarded, answer.feedback = result["marks"], result["feedback"]
                answer.confidence, answer.status, answer.marked_by = result["confidence"], "marked", "ai"
            else:
                answer.status, answer.marked_by = "needs_review", None
                answer.feedback = "Your teacher will mark this answer."
            db.session.commit()
        _finalise(sub)
        db.session.commit()

    try:
        if own_session:
            with app.app_context():
                try:
                    work()
                finally:
                    db.session.remove()
        else:
            work()
    except Exception:  # noqa: BLE001
        app.logger.exception("Exit ticket AI marking failed for attempt %s", submission_id)
    finally:
        with _in_flight_lock:
            _in_flight.discard(submission_id)


def _queue_ai_marking(sub):
    """Start marking this attempt's written answers (once), inline in tests and in a worker otherwise."""
    with _in_flight_lock:
        if sub.id in _in_flight:
            return
        _in_flight.add(sub.id)
    app = current_app._get_current_object()
    if app.config.get("EXIT_TICKET_MARK_SYNC"):
        db.session.commit()
        _run_ai_marking(app, sub.id, own_session=False)
    else:
        db.session.commit()
        _executor.submit(_run_ai_marking, app, sub.id)


def _mark_attempt(sub, responses):
    """Create an answer row for every question, mark the objective ones now, queue the written ones."""
    layout = sub.layout_dict()
    needs_ai = False
    for q in _snap_questions(sub):
        response = responses.get(str(q.id))
        row = ExitTicketAnswer(submission_id=sub.id, question_id=q.id, marks_possible=q.marks,
                               response=json.dumps(response) if response is not None else None)
        if q.qtype in L.AI_TYPES:
            text = response.strip() if isinstance(response, str) else ""
            if not text:
                row.marks_awarded, row.status, row.marked_by, row.feedback = 0.0, "marked", "auto", "No answer was given."
            else:
                row.status = "pending"
                needs_ai = True
        else:
            result = L.mark_objective(q.qtype, q.data_dict(), q.marks, response, layout.get(str(q.id)))
            row.marks_awarded, row.status, row.marked_by = result["marks"], "marked", "auto"
            row.detail = json.dumps(result["detail"])
            row.feedback = L.objective_feedback(q.qtype, result["marks"], q.marks)
        db.session.add(row)
    db.session.flush()
    _finalise(sub)
    return needs_ai


# =========================================================================== building JSON for the pages

def _reveal_allowed(sub, teacher):
    return teacher or sub.ticket.show_answers == "after"


def _question_result(a, q, layout, reveal):
    try:
        response = json.loads(a.response) if a.response else None
    except ValueError:
        response = None
    try:
        detail = json.loads(a.detail) if a.detail else []
    except ValueError:
        detail = []
    return {
        "id": q.id, "answer_id": a.id, "qtype": q.qtype, "prompt": q.prompt, "marks": L.as_whole(q.marks),
        "marks_awarded": L.as_whole(a.marks_awarded) if a.marks_awarded is not None else None,
        "status": a.status, "marked_by": a.marked_by, "feedback": a.feedback,
        "low_confidence": bool(a.marked_by == "ai" and a.confidence is not None and a.confidence < LOW_CONFIDENCE),
        "review": L.review_view(q, response, detail, layout.get(str(q.id)), reveal),
    }


def _attempt_payload(sub, teacher=False):
    t = sub.ticket
    head = {"ticket": {"id": t.id, "title": t.title, "code": t.code, "objective": t.objective,
                       "allow_retries": t.allow_retries, "version": t.version},
            "attempt": {"id": sub.id, "number": sub.attempt_number, "version": sub.ticket_version}}
    if sub.status == "in_progress":
        layout = sub.layout_dict()
        snapq = _snap_questions(sub)
        head.update(state="in_progress", total_marks=L.as_whole(sum(q.marks for q in snapq)),
                    questions=[L.student_view(q, layout.get(str(q.id))) for q in snapq])
        return head
    reveal = _reveal_allowed(sub, teacher)
    layout = sub.layout_dict()
    answers = {a.question_id: a for a in sub.answers}
    head.update(
        state="submitted", reveal=reveal, written_pending=_written_pending(sub),
        total_awarded=L.as_whole(sub.total_awarded or 0), total_possible=L.as_whole(sub.total_possible or t.total_marks),
        confidence=sub.confidence, reflection_note=sub.reflection_note,
        questions=[_question_result(answers[q.id], q, layout, reveal) for q in _snap_questions(sub) if q.id in answers],
    )
    return head


# =========================================================================== student side

def _my_class_ids(user):
    return [cid for (cid,) in db.session.query(ClassEnrollment.class_id)
            .join(Class, Class.id == ClassEnrollment.class_id)
            .filter(ClassEnrollment.student_id == user.id, Class.is_archived.is_(False)).all()]


def _assignments_for(user, ticket_id=None):
    conds = [ExitTicketAssignment.student_id == user.id]
    class_ids = _my_class_ids(user)
    if class_ids:
        conds.append(ExitTicketAssignment.class_id.in_(class_ids))
    q = ExitTicketAssignment.query.join(ExitTicket).filter(or_(*conds), ExitTicket.status == "published")
    if ticket_id is not None:
        q = q.filter(ExitTicketAssignment.ticket_id == ticket_id)
    return q.all()


@exit_bp.route("/")
@login_required
def student_home():
    if current_user.is_admin():
        return redirect(url_for("exit_tickets.admin_list"))
    by_ticket = {}
    for a in _assignments_for(current_user):
        cur = by_ticket.get(a.ticket_id)
        if cur is None or (a.due_date and (cur.due_date is None or a.due_date < cur.due_date)):
            by_ticket[a.ticket_id] = a
    rows = []
    for a in by_ticket.values():
        subs = (ExitTicketSubmission.query.filter_by(ticket_id=a.ticket_id, student_id=current_user.id)
                .order_by(ExitTicketSubmission.attempt_number).all())
        done = [s for s in subs if s.status == "submitted"]
        best = max(done, key=lambda s: (s.total_awarded or 0), default=None)
        open_attempt = next((s for s in subs if s.status == "in_progress"), None)
        rows.append({"ticket": a.ticket, "due": a.due_date, "attempts": len(done), "open": open_attempt,
                     "best": best, "last": done[-1] if done else None,
                     "can_start": bool(open_attempt) or not done or a.ticket.allow_retries and len(subs) < MAX_ATTEMPTS})
    rows.sort(key=lambda r: (r["due"] is None, r["due"] or datetime.max, r["ticket"].code or ""))
    return render_template("exit_tickets_student.html", rows=rows, now=datetime.utcnow())


@exit_bp.route("/start/<int:ticket_id>", methods=["POST"])
@login_required
def start_attempt(ticket_id):
    if current_user.is_admin():
        abort(403)
    ticket = ExitTicket.query.filter_by(id=ticket_id, status="published").first_or_404()
    assignment = next(iter(_assignments_for(current_user, ticket.id)), None)
    if assignment is None:
        abort(404)                                    # not assigned to you: same answer as "doesn't exist"
    subs = ExitTicketSubmission.query.filter_by(ticket_id=ticket.id, student_id=current_user.id).all()
    open_attempt = next((s for s in subs if s.status == "in_progress"), None)
    if open_attempt:
        return redirect(url_for("exit_tickets.attempt_page", submission_id=open_attempt.id))
    done = [s for s in subs if s.status == "submitted"]
    if done and not ticket.allow_retries:
        flash("You've already completed this exit ticket.", "info")
        return redirect(url_for("exit_tickets.attempt_page", submission_id=done[-1].id))
    if len(subs) >= MAX_ATTEMPTS:
        flash("You've used all your attempts on this exit ticket.", "info")
        return redirect(url_for("exit_tickets.student_home"))
    layout = {str(q.id): L.build_layout(q.qtype, q.data_dict()) for q in ticket.questions if q.qtype in ("match", "order")}
    sub = ExitTicketSubmission(ticket_id=ticket.id, assignment_id=assignment.id, student_id=current_user.id,
                               attempt_number=max([s.attempt_number for s in subs], default=0) + 1,
                               total_possible=ticket.total_marks, layout=json.dumps(layout),
                               snapshot=json.dumps(_make_snapshot(ticket)), ticket_version=ticket.version)
    db.session.add(sub)
    db.session.commit()
    return redirect(url_for("exit_tickets.attempt_page", submission_id=sub.id))


def _my_attempt(submission_id):
    return ExitTicketSubmission.query.filter_by(id=submission_id, student_id=current_user.id).first_or_404()


@exit_bp.route("/attempt/<int:submission_id>")
@login_required
def attempt_page(submission_id):
    sub = _my_attempt(submission_id)
    return render_template("exit_ticket_attempt.html", sub=sub, mode="student", types=L.TYPE_INFO,
                           api_url=url_for("exit_tickets.api_attempt", submission_id=sub.id),
                           submit_url=url_for("exit_tickets.api_submit", submission_id=sub.id))


@exit_bp.route("/api/attempts/<int:submission_id>")
@login_required
def api_attempt(submission_id):
    sub = _my_attempt(submission_id)
    if sub.status == "submitted" and _written_pending(sub) and sub.id not in _in_flight:
        # e.g. the app restarted while marking; pick it up again
        if any((a.ai_tries or 0) == 0 for a in sub.answers if a.status == "pending"):
            _queue_ai_marking(sub)
    return jsonify(_attempt_payload(sub))


@exit_bp.route("/api/attempts/<int:submission_id>/submit", methods=["POST"])
@login_required
def api_submit(submission_id):
    sub = _my_attempt(submission_id)
    if sub.status != "in_progress":
        return _err("This attempt has already been submitted.", 409)
    if (request.content_length or 0) > 200_000:
        return _err("That submission is too large.", 413)
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get("answers", {}), dict):
        return _err("Send your answers as JSON.")
    confidence = data.get("confidence")
    sub.confidence = confidence if isinstance(confidence, int) and not isinstance(confidence, bool) and 1 <= confidence <= 5 else None
    note = data.get("note")
    sub.reflection_note = note.strip()[:500] if isinstance(note, str) and note.strip() else None
    sub.status, sub.submitted_at = "submitted", datetime.utcnow()      # first, so a double click can't submit twice
    try:
        needs_ai = _mark_attempt(sub, data.get("answers", {}))
        db.session.commit()
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        return server_error(exc, "We couldn't save your answers. Please try again.")
    if needs_ai:
        _queue_ai_marking(sub)
    return jsonify(_attempt_payload(db.session.get(ExitTicketSubmission, sub.id)))


# =========================================================================== teacher side

def _topics():
    return [{"topic_id": t.topic_id, "code": t.code, "statement": t.statement}
            for t in UnitPlanTopic.query.order_by(UnitPlanTopic.part, UnitPlanTopic.code).all()]


def _ticket_json(t):
    return {"id": t.id, "title": t.title, "code": t.code, "topic_id": t.topic_id, "objective": t.objective,
            "status": t.status, "allow_retries": t.allow_retries, "show_answers": t.show_answers, "version": t.version,
            "questions": [{"id": q.id, "qtype": q.qtype, "prompt": q.prompt, "marks": L.as_whole(q.marks), "data": q.data_dict()}
                          for q in t.questions]}


@exit_bp.route("/admin")
@login_required
@admin_required
def admin_list():
    tickets = ExitTicket.query.order_by(ExitTicket.code, ExitTicket.title).all()
    counts = dict(db.session.query(ExitTicketSubmission.ticket_id, db.func.count(ExitTicketSubmission.id))
                  .filter(ExitTicketSubmission.status == "submitted").group_by(ExitTicketSubmission.ticket_id).all())
    return render_template("exit_tickets_admin.html", tickets=tickets, counts=counts, topics=_topics())


@exit_bp.route("/admin/new", methods=["POST"])
@login_required
@admin_required
def admin_new():
    title = (request.form.get("title") or "").strip()[:200]
    if not title:
        flash("Give the exit ticket a title.", "error")
        return redirect(url_for("exit_tickets.admin_list"))
    topic = UnitPlanTopic.query.filter_by(topic_id=request.form.get("topic_id") or "").first()
    ticket = ExitTicket(title=title, created_by_id=current_user.id, code=topic.code if topic else None,
                        topic_id=topic.topic_id if topic else None, objective=topic.statement if topic else None)
    db.session.add(ticket)
    db.session.commit()
    return redirect(url_for("exit_tickets.admin_edit", ticket_id=ticket.id))


@exit_bp.route("/admin/<int:ticket_id>/edit")
@login_required
@admin_required
def admin_edit(ticket_id):
    ticket = db.get_or_404(ExitTicket, ticket_id)
    return render_template("exit_ticket_edit.html", ticket=ticket, ticket_json=_ticket_json(ticket),
                           topics=_topics(), types=L.TYPE_INFO)


@exit_bp.route("/api/tickets/<int:ticket_id>", methods=["PUT"])
@login_required
@admin_required
def api_save_ticket(ticket_id):
    ticket = db.get_or_404(ExitTicket, ticket_id)
    raw = request.get_json(silent=True)
    try:
        clean = L.clean_ticket(raw)
    except L.ValidationError as exc:
        return _err(str(exc))
    existing = {q.id: q for q in ticket.questions}            # the questions students get now
    before = _fingerprint(ticket.questions)
    try:
        for field in ("title", "code", "topic_id", "objective", "status", "allow_retries", "show_answers"):
            setattr(ticket, field, clean[field])
        # A removed (or retyped) question is hidden, not deleted: attempts that included it keep their history.
        removed = [qid for qid, q in existing.items()
                   if not any(r.get("id") == qid and r.get("qtype") == q.qtype for r in raw["questions"])]
        for qid in removed:
            existing[qid].active = False
        kept = {qid: q for qid, q in existing.items() if qid not in removed}
        for position, (cq, rq) in enumerate(zip(clean["questions"], raw["questions"])):
            row = kept.get(rq.get("id")) if isinstance(rq.get("id"), int) else None
            if row is None or row.qtype != cq["qtype"]:
                row = ExitTicketQuestion(ticket_id=ticket.id, qtype=cq["qtype"], active=True)
                db.session.add(row)
            row.position, row.prompt, row.marks, row.data = position, cq["prompt"], cq["marks"], json.dumps(cq["data"])
        db.session.flush()
        db.session.expire(ticket, ["all_questions"])
        if _fingerprint(ticket.questions) != before:
            ticket.version = (ticket.version or 1) + 1
        db.session.commit()
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        return server_error(exc, "The ticket couldn't be saved.")
    return jsonify({"success": True, "ticket": _ticket_json(db.session.get(ExitTicket, ticket_id))})


@exit_bp.route("/api/tickets/<int:ticket_id>/duplicate", methods=["POST"])
@login_required
@admin_required
def api_duplicate(ticket_id):
    src = db.get_or_404(ExitTicket, ticket_id)
    copy = ExitTicket(title=f"{src.title} (copy)"[:200], code=src.code, topic_id=src.topic_id, objective=src.objective,
                      status="draft", allow_retries=src.allow_retries, show_answers=src.show_answers, created_by_id=current_user.id)
    db.session.add(copy)
    db.session.flush()
    for q in src.questions:
        db.session.add(ExitTicketQuestion(ticket_id=copy.id, position=q.position, qtype=q.qtype, prompt=q.prompt, marks=q.marks, data=q.data))
    db.session.commit()
    return jsonify({"success": True, "id": copy.id, "edit_url": url_for("exit_tickets.admin_edit", ticket_id=copy.id)})


@exit_bp.route("/api/tickets/<int:ticket_id>", methods=["DELETE"])
@login_required
@admin_required
def api_delete_ticket(ticket_id):
    ticket = db.get_or_404(ExitTicket, ticket_id)
    try:
        purge_dependents(db.session, "exit_tickets", [ticket.id])
        db.session.expire(ticket)
        db.session.delete(ticket)
        db.session.commit()
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        return server_error(exc, "The ticket couldn't be deleted.")
    return jsonify({"success": True})


@exit_bp.route("/admin/<int:ticket_id>/preview")
@login_required
@admin_required
def admin_preview(ticket_id):
    ticket = db.get_or_404(ExitTicket, ticket_id)
    layout = {str(q.id): L.build_layout(q.qtype, q.data_dict()) for q in ticket.questions if q.qtype in ("match", "order")}
    payload = {"ticket": {"id": ticket.id, "title": ticket.title, "code": ticket.code, "objective": ticket.objective, "allow_retries": True},
               "attempt": {"id": 0, "number": 1}, "state": "in_progress", "total_marks": L.as_whole(ticket.total_marks),
               "questions": [L.student_view(q, layout.get(str(q.id))) for q in ticket.questions]}
    return render_template("exit_ticket_attempt.html", sub=None, mode="preview", types=L.TYPE_INFO, preview_payload=payload,
                           ticket=ticket, api_url="", submit_url="")


def _date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").replace(hour=23, minute=59)
    except ValueError:
        raise L.ValidationError("Use a date like 2026-10-31.")


@exit_bp.route("/api/tickets/<int:ticket_id>/assign", methods=["POST"])
@login_required
@admin_required
def api_assign(ticket_id):
    ticket = db.get_or_404(ExitTicket, ticket_id)
    if ticket.status != "published":
        return _err("Publish the exit ticket before assigning it.")
    data = request.get_json(silent=True) or {}
    try:
        due = _date(data.get("due_date"))
    except L.ValidationError as exc:
        return _err(str(exc))
    class_id, student_id = data.get("class_id"), data.get("student_id")
    if bool(class_id) == bool(student_id):
        return _err("Choose a class or a student.")
    if class_id:
        target = Class.query.filter_by(id=class_id, is_archived=False).first()
        if not target:
            return _err("That class doesn't exist.", 404)
        existing = ExitTicketAssignment.query.filter_by(ticket_id=ticket.id, class_id=target.id).first()
    else:
        target = User.query.filter_by(id=student_id, role="student").first()
        if not target:
            return _err("That student doesn't exist.", 404)
        existing = ExitTicketAssignment.query.filter_by(ticket_id=ticket.id, student_id=target.id).first()
    if existing:
        existing.due_date = due
        db.session.commit()
        return jsonify({"success": True, "id": existing.id, "updated": True})
    a = ExitTicketAssignment(ticket_id=ticket.id, class_id=target.id if class_id else None,
                             student_id=target.id if student_id else None, assigned_by_id=current_user.id, due_date=due)
    db.session.add(a)
    db.session.commit()
    return jsonify({"success": True, "id": a.id})


@exit_bp.route("/api/assignments/<int:assignment_id>", methods=["DELETE"])
@login_required
@admin_required
def api_unassign(assignment_id):
    a = db.get_or_404(ExitTicketAssignment, assignment_id)
    ExitTicketSubmission.query.filter_by(assignment_id=a.id).update({"assignment_id": None})   # keep the students' attempts
    db.session.delete(a)
    db.session.commit()
    return jsonify({"success": True})


@exit_bp.route("/admin/<int:ticket_id>/results")
@login_required
@admin_required
def admin_results(ticket_id):
    ticket = db.get_or_404(ExitTicket, ticket_id)
    assignments = ExitTicketAssignment.query.filter_by(ticket_id=ticket.id).all()
    class_ids = [a.class_id for a in assignments if a.class_id]
    student_ids = {a.student_id for a in assignments if a.student_id}
    if class_ids:
        student_ids |= {sid for (sid,) in db.session.query(ClassEnrollment.student_id)
                        .filter(ClassEnrollment.class_id.in_(class_ids)).all()}
    students = User.query.filter(User.id.in_(student_ids), User.role == "student").order_by(User.name).all() if student_ids else []
    subs = ExitTicketSubmission.query.filter_by(ticket_id=ticket.id).order_by(ExitTicketSubmission.attempt_number).all()
    by_student = {}
    for s in subs:
        by_student.setdefault(s.student_id, []).append(s)
    rows = []
    for st in students:
        mine = by_student.get(st.id, [])
        done = [s for s in mine if s.status == "submitted"]
        best = max(done, key=lambda s: (s.total_awarded or 0), default=None)
        pending = any(a.status in ("pending", "needs_review") for s in done for a in s.answers)
        low = any(a.marked_by == "ai" and a.confidence is not None and a.confidence < LOW_CONFIDENCE for s in done for a in s.answers)
        rows.append({"student": st, "attempts": done, "best": best, "last": done[-1] if done else None,
                     "review": pending or low, "pending": pending})
    scores = [r["best"].total_awarded or 0 for r in rows if r["best"]]
    summary = {"assigned": len(rows), "done": len(scores),
               "average": round(sum(scores) / len(scores), 1) if scores else None}
    return render_template("exit_ticket_results.html", ticket=ticket, rows=rows, summary=summary, assignments=assignments,
                           classes=Class.query.filter_by(is_archived=False).order_by(Class.name).all(),
                           all_students=User.query.filter_by(role="student").order_by(User.name).all(),
                           total=L.as_whole(ticket.total_marks))


@exit_bp.route("/admin/attempts/<int:submission_id>")
@login_required
@admin_required
def admin_attempt(submission_id):
    sub = db.get_or_404(ExitTicketSubmission, submission_id)
    return render_template("exit_ticket_attempt.html", sub=sub, mode="teacher", types=L.TYPE_INFO,
                           api_url=url_for("exit_tickets.api_admin_attempt", submission_id=sub.id), submit_url="")


@exit_bp.route("/api/admin/attempts/<int:submission_id>")
@login_required
@admin_required
def api_admin_attempt(submission_id):
    sub = db.get_or_404(ExitTicketSubmission, submission_id)
    if sub.status != "submitted":
        return _err("This attempt hasn't been submitted yet.", 409)
    payload = _attempt_payload(sub, teacher=True)
    payload["student"] = sub.student.name
    return jsonify(payload)


@exit_bp.route("/api/answers/<int:answer_id>/override", methods=["POST"])
@login_required
@admin_required
def api_override(answer_id):
    a = db.get_or_404(ExitTicketAnswer, answer_id)
    data = request.get_json(silent=True) or {}
    marks = data.get("marks")
    if isinstance(marks, bool) or not isinstance(marks, (int, float)) or not 0 <= marks <= a.marks_possible or (marks * 2) % 1:
        return _err(f"Marks must be between 0 and {L.as_whole(a.marks_possible)} (halves allowed).")
    feedback = data.get("feedback")
    a.marks_awarded, a.status, a.marked_by = float(marks), "marked", "teacher"
    if isinstance(feedback, str):
        a.feedback = feedback.strip()[:800] or a.feedback
    sub = a.submission
    _finalise(sub)
    db.session.commit()
    return jsonify({"success": True, "total_awarded": L.as_whole(sub.total_awarded or 0)})


@exit_bp.route("/api/attempts/<int:submission_id>/remark", methods=["POST"])
@login_required
@admin_required
def api_remark(submission_id):
    sub = db.get_or_404(ExitTicketSubmission, submission_id)
    changed = 0
    snap = {q.id: q for q in _snap_questions(sub)}
    for a in sub.answers:
        if getattr(snap.get(a.question_id), "qtype", None) in L.AI_TYPES and a.marked_by != "teacher" and a.response and json.loads(a.response or '""'):
            a.status, a.ai_tries = "pending", 0
            changed += 1
    db.session.commit()
    if changed:
        _queue_ai_marking(sub)
    return jsonify({"success": True, "queued": changed})
