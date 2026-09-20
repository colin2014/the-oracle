import json
from datetime import datetime, timedelta
from pathlib import Path

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for, session, current_app
from flask_login import login_required, current_user
from functools import wraps
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from auth import admin_required
from auth_routes import PASSWORD_MIN_LENGTH
from db_cleanup import purge_dependents
from safe_errors import server_error
from extensions import db
from email_utils import generate_assignment_email
from local_name_mapping import load_name_mappings, save_name_mapping, get_display_name
from models import (
    Class, ClassEnrollment, ReadingActivity, ReadingAssignment, StudentConfidence, User,
    QuizAnswer, StudentFeedbackInsight, ReadingDailyLog, FlashcardProgress, FlashcardStudySession,
    QuizQuestion, TestAssignment, TestSubmission, TestPaper
)

admin_bp = Blueprint("admin", __name__)

BOOKS_FILE = Path("data") / "books.json"
EE_EXEMPLARS_METADATA_FILE = Path("data") / "ee_exemplars" / "metadata.json"


def _load_books():
    if BOOKS_FILE.exists():
        try:
            with open(BOOKS_FILE, "r", encoding="utf-8") as f:
                return json.load(f).get("books", [])
        except (json.JSONDecodeError, OSError):
            return []
    return []


def _load_exemplars():
    if EE_EXEMPLARS_METADATA_FILE.exists():
        try:
            with open(EE_EXEMPLARS_METADATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return []
    return []


@admin_bp.route("/students/<int:student_id>/reset-data")
@login_required
@admin_required
def reset_student_data(student_id):
    """View for resetting/managing student data (quiz, reading, confidence, flashcards)."""
    student = User.query.filter_by(id=student_id, role="student").first_or_404()
    return render_template("admin_reset_student_data.html", student=student)


@admin_bp.route("/")
@login_required
@admin_required
def admin_home():
    classes = Class.query.filter_by(is_archived=False).order_by(Class.created_at.desc()).all()
    stats = {
        c.id: {
            "student_count": len(c.enrollments),
            "assignment_count": len(c.assignments),
        }
        for c in classes
    }
    archived_classes = Class.query.filter_by(is_archived=True).order_by(Class.name).all()
    return render_template(
        "admin_classes.html", classes=classes, stats=stats, archived_classes=archived_classes
    )


@admin_bp.route("/students")
@login_required
@admin_required
def students():
    all_students = User.query.filter_by(role="student").order_by(User.name).all()
    all_classes = Class.query.filter_by(is_archived=False).order_by(Class.name).all()
    archived_classes = Class.query.filter_by(is_archived=True).order_by(Class.name).all()
    student_ids = [s.id for s in all_students]

    classes_by_student = {sid: [] for sid in student_ids}
    for e in ClassEnrollment.query.filter(ClassEnrollment.student_id.in_(student_ids)).all() if student_ids else []:
        classes_by_student.setdefault(e.student_id, []).append(e)

    usage_by_student = {}
    if student_ids:
        rows = ReadingActivity.query.filter(ReadingActivity.student_id.in_(student_ids)).all()
        for sid in student_ids:
            usage_by_student[sid] = {"pages_opened": 0, "pages_completed": 0, "total_seconds": 0, "last_active": None}
        for row in rows:
            u = usage_by_student[row.student_id]
            u["pages_opened"] += 1
            if row.completed:
                u["pages_completed"] += 1
            u["total_seconds"] += row.total_seconds or 0
            if not u["last_active"] or row.last_opened_at > u["last_active"]:
                u["last_active"] = row.last_opened_at

    # The code the running app actually accepts (read at startup from SIGNUP_CODE).
    from auth_routes import SIGNUP_CODE

    return render_template(
        "admin_students.html",
        students=all_students,
        classes=all_classes,
        archived_classes=archived_classes,
        classes_by_student=classes_by_student,
        usage_by_student=usage_by_student,
        signup_code=SIGNUP_CODE,
    )


def _generate_password(length=12):
    """Readable temporary password: no look-alike characters (0/O, 1/l/I)."""
    import secrets
    alphabet = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


@admin_bp.route("/students/<int:student_id>/reset-password", methods=["POST"])
@login_required
@admin_required
def reset_student_password(student_id):
    """Set a student's password to a generated or admin-typed value.

    Passwords are stored only as one-way hashes, so an existing password can never
    be shown; resetting is the supported way to help a student who is locked out.
    The new password is returned once, in this response, and is never stored or logged.
    """
    student = User.query.filter_by(id=student_id, role="student").first_or_404()
    data = request.get_json(silent=True) or {}

    if data.get("mode") == "custom":
        password = data.get("password") or ""
        if len(password) < PASSWORD_MIN_LENGTH:
            return jsonify({"success": False, "error": f"Password must be at least {PASSWORD_MIN_LENGTH} characters."}), 400
    else:
        password = _generate_password()

    student.set_password(password)
    db.session.commit()
    current_app.logger.info("admin id=%s reset the password of student id=%s", current_user.id, student.id)

    resp = jsonify({"success": True, "username": student.username, "password": password})
    resp.headers["Cache-Control"] = "no-store"
    return resp


@admin_bp.route("/students/<int:student_id>/assign-class", methods=["POST"])
@login_required
@admin_required
def assign_student_to_class(student_id):
    student = User.query.filter_by(id=student_id, role="student").first_or_404()
    class_id = request.form.get("class_id", "").strip()
    class_obj = Class.query.filter_by(id=class_id).first() if class_id else None

    if not class_obj:
        flash("Please select a class.", "error")
    elif ClassEnrollment.query.filter_by(class_id=class_obj.id, student_id=student.id).first():
        flash(f"{student.name} is already in {class_obj.name}.", "error")
    else:
        db.session.add(ClassEnrollment(class_id=class_obj.id, student_id=student.id))
        db.session.commit()
        flash(f"Added {student.name} to {class_obj.name}.", "success")

    return redirect(url_for("admin.students"))


@admin_bp.route("/students/<int:student_id>/remove-class/<int:class_id>", methods=["POST"])
@login_required
@admin_required
def remove_student_from_class(student_id, class_id):
    enrollment = ClassEnrollment.query.filter_by(class_id=class_id, student_id=student_id).first()
    if enrollment:
        db.session.delete(enrollment)
        db.session.commit()
        flash("Removed from class.", "success")
    return redirect(url_for("admin.students"))


@admin_bp.route("/students/<int:student_id>/class/<int:class_id>/set-level", methods=["POST"])
@login_required
@admin_required
def set_student_level(student_id, class_id):
    enrollment = ClassEnrollment.query.filter_by(
        class_id=class_id, student_id=student_id
    ).first_or_404()
    level = request.form.get("level", "").strip().upper()
    if level not in ("HL", "SL", ""):
        return jsonify({"success": False, "error": "Level must be HL, SL, or blank."}), 400
    enrollment.level = level if level else None
    db.session.commit()
    return jsonify({"success": True, "level": enrollment.level})


@admin_bp.route("/students/bulk-assign", methods=["POST"])
@login_required
@admin_required
def bulk_assign_students():
    data = request.get_json()
    student_ids = data.get("student_ids", [])
    class_id = data.get("class_id")

    if not student_ids or not class_id:
        return jsonify({"success": False, "error": "Missing student_ids or class_id"}), 400

    class_obj = Class.query.get_or_404(class_id)
    assigned_count = 0

    for student_id in student_ids:
        student = User.query.filter_by(id=student_id, role="student").first()
        if student and not ClassEnrollment.query.filter_by(class_id=class_obj.id, student_id=student.id).first():
            db.session.add(ClassEnrollment(class_id=class_obj.id, student_id=student.id))
            assigned_count += 1

    db.session.commit()
    return jsonify({"success": True, "assigned": assigned_count})


@admin_bp.route("/classes", methods=["GET", "POST"])
@login_required
@admin_required
def classes():
    from flask_login import current_user

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Class name is required.", "error")
        else:
            db.session.add(Class(name=name, created_by_id=current_user.id))
            db.session.commit()
            flash(f"Class '{name}' created.", "success")
        return redirect(url_for("admin.admin_home"))

    return redirect(url_for("admin.admin_home"))


@admin_bp.route("/classes/<int:class_id>")
@login_required
@admin_required
def class_detail(class_id):
    class_obj = Class.query.get_or_404(class_id)
    student_ids = [e.student_id for e in class_obj.enrollments]

    activity_by_key = {}
    student_analytics = {}
    if student_ids:
        rows = ReadingActivity.query.filter(ReadingActivity.student_id.in_(student_ids)).all()
        for row in rows:
            activity_by_key[(row.student_id, row.book_folder, row.page_id)] = row

        # Build per-student analytics
        for sid in student_ids:
            student_analytics[sid] = {
                "pages_opened": 0,
                "pages_completed": 0,
                "total_seconds": 0,
                "last_active": None
            }
        for row in rows:
            u = student_analytics[row.student_id]
            u["pages_opened"] += 1
            if row.completed:
                u["pages_completed"] += 1
            u["total_seconds"] += row.total_seconds or 0
            if not u["last_active"] or row.last_opened_at > u["last_active"]:
                u["last_active"] = row.last_opened_at

    unenrolled_students = User.query.filter(
        User.role == "student", ~User.id.in_(student_ids) if student_ids else True
    ).order_by(User.name).all()

    return render_template(
        "admin_class_detail.html",
        class_obj=class_obj,
        activity_by_key=activity_by_key,
        student_analytics=student_analytics,
        unenrolled_students=unenrolled_students,
    )


@admin_bp.route("/classes/<int:class_id>/enroll", methods=["POST"])
@login_required
@admin_required
def enroll_student(class_id):
    class_obj = Class.query.get_or_404(class_id)
    student_id = request.form.get("student_id", "").strip()

    student = User.query.filter_by(id=student_id, role="student").first() if student_id else None
    if not student:
        flash("Please select a student to enroll.", "error")
    elif ClassEnrollment.query.filter_by(class_id=class_id, student_id=student.id).first():
        flash(f"{student.name} is already enrolled.", "error")
    else:
        db.session.add(ClassEnrollment(class_id=class_id, student_id=student.id))
        db.session.commit()
        flash(f"Enrolled {student.name}.", "success")

    return redirect(url_for("admin.class_detail", class_id=class_id))


@admin_bp.route("/classes/<int:class_id>/unenroll/<int:student_id>", methods=["POST"])
@login_required
@admin_required
def unenroll_student(class_id, student_id):
    enrollment = ClassEnrollment.query.filter_by(class_id=class_id, student_id=student_id).first()
    if enrollment:
        db.session.delete(enrollment)
        db.session.commit()
        flash("Student removed from class.", "success")
    return redirect(url_for("admin.class_detail", class_id=class_id))


@admin_bp.route("/api/classes/<int:class_id>/students")
@login_required
@admin_required
def api_class_students(class_id):
    class_obj = Class.query.get_or_404(class_id)
    students = sorted(
        (e.student for e in class_obj.enrollments if e.student),
        key=lambda s: s.name or "",
    )
    return jsonify({
        "students": [{"id": s.id, "name": s.name, "email": s.email} for s in students]
    })


def _assignment_return_url(assignment):
    """Where to send an admin after acting on an assignment."""
    if assignment.class_id:
        return url_for("admin.class_detail", class_id=assignment.class_id)
    if assignment.student_id:
        return url_for("admin_view_student_resources", student_id=assignment.student_id)
    return url_for("admin.assign")


def _build_assignments_from_form(form, *, assigned_by_id, class_id=None, student_id=None):
    """Turn the resource picker form into ReadingAssignment rows.

    Exactly one of ``class_id`` / ``student_id`` identifies the target. Returns
    a list of unsaved ReadingAssignment instances (possibly empty).
    """
    due_date_raw = form.get("due_date", "").strip()
    due_date = None
    if due_date_raw:
        try:
            due_date = datetime.fromisoformat(due_date_raw)
        except ValueError:
            due_date = None

    # Book pages: "book_folder|page_id|title"
    page_picks = form.getlist("page_picks")
    # Exemplars: "filename|title"
    exemplar_picks = form.getlist("exemplar_picks")
    # Exemplar collection (entire library)
    exemplar_collection = form.get("exemplar_collection") in ("on", "true")
    # Unit Plan weeks/topics: "bucket|ref|title" — bucket/ref match the addressing
    # unit_plan_routes.py already uses for quizzes (semester key or "grade12").
    unit_plan_picks = form.getlist("unit_plan_picks")

    def _make(**kwargs):
        return ReadingAssignment(
            class_id=class_id,
            student_id=student_id,
            due_date=due_date,
            assigned_by_id=assigned_by_id,
            **kwargs,
        )

    new_assignments = []
    for pick in page_picks:
        parts = pick.split("|", 2)
        if len(parts) < 2:
            continue
        book_folder, page_id = parts[0], parts[1]
        title = parts[2] if len(parts) > 2 else page_id
        if not book_folder or not page_id:
            continue
        new_assignments.append(_make(
            resource_type="book_page",
            book_folder=book_folder,
            page_id=page_id,
            title=title or page_id,
        ))

    for pick in exemplar_picks:
        parts = pick.split("|", 1)
        filename = parts[0]
        title = parts[1] if len(parts) > 1 else filename
        if not filename:
            continue
        new_assignments.append(_make(
            resource_type="exemplar",
            book_folder="__exemplar__",
            page_id=filename,
            title=title or filename,
        ))

    if exemplar_collection:
        new_assignments.append(_make(
            resource_type="exemplar_collection",
            book_folder="__exemplar_collection__",
            page_id="collection",
            title="EE / IA Exemplars",
        ))

    for pick in unit_plan_picks:
        parts = pick.split("|", 2)
        if len(parts) < 2:
            continue
        bucket, ref = parts[0], parts[1]
        title = parts[2] if len(parts) > 2 else ref
        if not bucket or not ref:
            continue
        new_assignments.append(_make(
            resource_type="unit_plan_week",
            book_folder=bucket,
            page_id=ref,
            title=title or ref,
        ))

    return new_assignments


@admin_bp.route("/assign", methods=["GET", "POST"])
@login_required
@admin_required
def assign(class_id=None):
    """General assign page: target a whole class or an individual student."""
    from flask_login import current_user

    # class_id may be pre-set when reached via /classes/<id>/assign.
    preselect_class_id = class_id or request.args.get("class_id", type=int)
    preselect_student_id = request.args.get("student_id", type=int)
    # Reached via a "🎯 Assign to class" shortcut (e.g. from the Unit Plan's linked
    # textbook quizzes) — preselects the book + page in the Book Pages tab.
    preselect_book_folder = request.args.get("book_folder")
    preselect_page_id = request.args.get("page_id")

    if request.method == "POST":
        target_type = request.form.get("target_type", "class")

        # Determine the set of (class_id, student_id) targets to build for.
        targets = []  # list of (class_id, student_id)
        if target_type == "student":
            # Students are picked by first choosing a class, then drilling down
            # to one or more students within it.
            student_ids = request.form.getlist("student_ids", type=int)
            valid_ids = [
                s.id for s in User.query.filter(
                    User.id.in_(student_ids), User.role == "student"
                ).all()
            ] if student_ids else []
            if not valid_ids:
                flash("Select at least one student to assign to.", "error")
                return redirect(url_for("admin.assign"))
            targets = [(None, sid) for sid in valid_ids]
        else:
            target_class_id = request.form.get("class_id", type=int)
            if not target_class_id or not Class.query.get(target_class_id):
                flash("Select a class to assign to.", "error")
                return redirect(url_for("admin.assign"))
            targets = [(target_class_id, None)]

        new_assignments = []
        for t_class_id, t_student_id in targets:
            new_assignments.extend(_build_assignments_from_form(
                request.form,
                assigned_by_id=current_user.id,
                class_id=t_class_id,
                student_id=t_student_id,
            ))

        if not new_assignments:
            flash("Select at least one resource to assign.", "error")
            return redirect(url_for("admin.assign"))

        db.session.add_all(new_assignments)
        db.session.commit()

        if target_type == "student":
            n_students = len(targets)
            per = len(new_assignments) // n_students if n_students else 0
            who = new_assignments[0].target_label() if n_students == 1 else f"{n_students} students"
            flash(f"Assigned {per} resource(s) to {who}. Use 'Show Email' to copy and send to students.", "success")
            return redirect(url_for("admin.assign"))

        assign_class_id = targets[0][0]
        target_name = new_assignments[0].target_label()
        flash(f"Assigned {len(new_assignments)} resource(s) to {target_name}. Use 'Show Email' to copy and send to students.", "success")
        return redirect(url_for("admin.class_detail", class_id=assign_class_id))

    books = _load_books()
    exemplars = _load_exemplars()
    classes = Class.query.filter_by(is_archived=False).order_by(Class.name).all()
    students = User.query.filter_by(role="student").order_by(User.name).all()
    return render_template(
        "admin_assign_reading.html",
        books=books,
        exemplars=exemplars,
        classes=classes,
        students=students,
        preselect_class_id=preselect_class_id,
        preselect_student_id=preselect_student_id,
        preselect_book_folder=preselect_book_folder,
        preselect_page_id=preselect_page_id,
    )


@admin_bp.route("/classes/<int:class_id>/assign", methods=["GET", "POST"])
@login_required
@admin_required
def assign_reading(class_id):
    # Preserve the old per-class entry point; the general page handles both.
    Class.query.get_or_404(class_id)
    if request.method == "POST":
        return assign(class_id=class_id)
    return redirect(url_for("admin.assign", class_id=class_id))


@admin_bp.route("/assignments/<int:assignment_id>/email-preview", methods=["GET"])
@login_required
@admin_required
def email_preview(assignment_id):
    assignment = ReadingAssignment.query.get_or_404(assignment_id)
    class_obj = assignment.class_
    if assignment.student_id:
        students = [assignment.student] if assignment.student else []
    else:
        students = [e.student for e in class_obj.enrollments] if class_obj else []

    emails = []
    for student in students:
        subject, body = generate_assignment_email(assignment, class_obj, student)
        emails.append({
            "student_id": student.id,
            "student_name": student.name,
            "student_email": student.email,
            "subject": subject,
            "body": body,
        })

    return jsonify({
        "assignment_id": assignment.id,
        "assignment_title": assignment.title,
        "class_name": class_obj.name if class_obj else assignment.target_label(),
        "students": emails,
    })


@admin_bp.route("/assignments/<int:assignment_id>/mark-sent", methods=["POST"])
@login_required
@admin_required
def mark_assignment_sent(assignment_id):
    assignment = ReadingAssignment.query.get_or_404(assignment_id)
    assignment.email_sent_at = datetime.utcnow()
    db.session.commit()
    flash(f"Marked '{assignment.title}' as sent.", "success")
    return redirect(_assignment_return_url(assignment))


@admin_bp.route("/assignments/<int:assignment_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_assignment(assignment_id):
    assignment = ReadingAssignment.query.get_or_404(assignment_id)
    class_id = assignment.class_id
    title = assignment.title
    return_url = _assignment_return_url(assignment)
    db.session.delete(assignment)
    db.session.commit()
    flash(f"Deleted assignment '{title}'.", "success")
    return redirect(return_url)


@admin_bp.route("/classes/<int:class_id>/archive", methods=["POST"])
@login_required
@admin_required
def archive_class(class_id):
    class_obj = Class.query.get_or_404(class_id)
    class_obj.is_archived = True
    db.session.commit()
    flash(f"Archived class '{class_obj.name}'. You can restore it from the archived list.", "success")
    return redirect(request.referrer or url_for("admin.admin_home"))


@admin_bp.route("/classes/<int:class_id>/unarchive", methods=["POST"])
@login_required
@admin_required
def unarchive_class(class_id):
    class_obj = Class.query.get_or_404(class_id)
    class_obj.is_archived = False
    db.session.commit()
    flash(f"Restored class '{class_obj.name}'.", "success")
    return redirect(request.referrer or url_for("admin.admin_home"))


@admin_bp.route("/classes/<int:class_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_class(class_id):
    """Classes are never destroyed — 'delete' archives them so they can be restored."""
    return archive_class(class_id)


@admin_bp.route("/students/<int:student_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_student(student_id):
    student = User.query.filter_by(id=student_id, role="student").first_or_404()
    student_name = student.name
    try:
        # The User model has no cascades and SQLite doesn't enforce foreign keys, so remove
        # the student's dependent rows explicitly. Otherwise their progress, answers and
        # reports would stay behind and be inherited by whoever next gets this id.
        purge_dependents(db.session, "users", [student.id])
        db.session.delete(student)
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Could not delete student id=%s", student_id)
        flash("Could not delete that student. Nothing was changed.", "error")
        return redirect(url_for("admin.students"))
    flash(f"Deleted student '{student_name}' and all of their data.", "success")
    return redirect(url_for("admin.students"))


@admin_bp.route("/analytics/hub")
@login_required
@admin_required
def analytics_hub():
    """Unified analytics: reading, confidence, and quiz sections on one page."""
    return render_template("admin_analytics_hub.html")


@admin_bp.route("/analytics")
@login_required
@admin_required
def analytics():
    classes = Class.query.filter_by(is_archived=False).order_by(Class.name).all()
    summary = []
    for c in classes:
        assignments = c.assignments
        students = [e.student for e in c.enrollments]
        total_cells = len(assignments) * len(students)
        completed_cells = 0
        total_seconds = 0
        if assignments and students:
            student_ids = [s.id for s in students]
            rows = ReadingActivity.query.filter(ReadingActivity.student_id.in_(student_ids)).all()
            activity_by_key = {(r.student_id, r.book_folder, r.page_id): r for r in rows}
            for s in students:
                for a in assignments:
                    row = activity_by_key.get((s.id, a.book_folder, a.page_id))
                    if row:
                        total_seconds += row.total_seconds or 0
                        if row.completed:
                            completed_cells += 1
        avg_completion = (completed_cells / total_cells * 100) if total_cells else 0
        summary.append({
            "class_obj": c,
            "student_count": len(students),
            "assignment_count": len(assignments),
            "avg_completion": round(avg_completion, 1),
            "total_seconds": total_seconds,
        })

    return render_template("admin_analytics.html", summary=summary)


@admin_bp.route("/analytics/class/<int:class_id>")
@login_required
@admin_required
def analytics_class(class_id):
    class_obj = Class.query.get_or_404(class_id)
    students = [e.student for e in class_obj.enrollments]
    assignments = class_obj.assignments

    activity_by_key = {}
    confidence_by_key = {}
    if students:
        student_ids = [s.id for s in students]
        rows = ReadingActivity.query.filter(ReadingActivity.student_id.in_(student_ids)).all()
        activity_by_key = {(r.student_id, r.book_folder, r.page_id): r for r in rows}

        confidence_rows = StudentConfidence.query.filter(StudentConfidence.student_id.in_(student_ids)).all()
        confidence_by_key = {(r.student_id, r.book_folder, r.page_id): r for r in confidence_rows}

    return render_template(
        "admin_analytics_class.html",
        class_obj=class_obj,
        students=students,
        assignments=assignments,
        activity_by_key=activity_by_key,
        confidence_by_key=confidence_by_key,
    )


@admin_bp.route("/analytics/student/<int:student_id>")
@login_required
@admin_required
def analytics_student(student_id):
    student = User.query.get_or_404(student_id)
    enrollments = ClassEnrollment.query.filter_by(student_id=student_id).all()
    classes = [e.class_ for e in enrollments]

    assignments = []
    for c in classes:
        assignments.extend(c.assignments)

    activity_rows = ReadingActivity.query.filter_by(student_id=student_id).all()
    activity_by_key = {(r.book_folder, r.page_id): r for r in activity_rows}

    confidence_rows = StudentConfidence.query.filter_by(student_id=student_id).all()
    confidence_by_key = {(r.book_folder, r.page_id): r for r in confidence_rows}

    # Quiz analytics (the same per-student drill-down students see), with the
    # per-page links pointing back into this teacher view.
    from quiz_routes import _compute_quiz_analytics
    quiz = _compute_quiz_analytics(student_id, link_student_id=student_id)

    return render_template(
        "admin_analytics_student.html",
        student=student,
        classes=classes,
        assignments=assignments,
        activity_by_key=activity_by_key,
        confidence_by_key=confidence_by_key,
        quiz=quiz,
        teacher_view=True,
    )


@admin_bp.route("/analytics/confidence/matrix")
@login_required
@admin_required
def confidence_matrix():
    """Confidence per assignment: assignments as rows, students as columns."""
    class_filter = request.args.get("class", "").strip()
    all_classes = Class.query.filter_by(is_archived=False).order_by(Class.name).all()

    selected_class = None
    if class_filter:
        try:
            selected_class = Class.query.get(int(class_filter))
        except (ValueError, TypeError):
            selected_class = None

    if selected_class:
        students = sorted((e.student for e in selected_class.enrollments), key=lambda s: s.name or "")
        assignments = selected_class.assignments
    else:
        students = User.query.filter_by(role="student").order_by(User.name).all()
        assignments = ReadingAssignment.query.order_by(ReadingAssignment.title).all()

    # Deduplicate assignments pointing at the same resource (keep first title)
    seen = set()
    unique_assignments = []
    for a in assignments:
        key = (a.book_folder, a.page_id)
        if key not in seen:
            seen.add(key)
            unique_assignments.append(a)

    confidence_by_key = {}
    if students:
        student_ids = [s.id for s in students]
        rows = StudentConfidence.query.filter(StudentConfidence.student_id.in_(student_ids)).all()
        confidence_by_key = {(r.student_id, r.book_folder, r.page_id): r for r in rows}

    # Per-assignment averages
    avg_by_assignment = {}
    for a in unique_assignments:
        levels = [
            confidence_by_key[(s.id, a.book_folder, a.page_id)].confidence_level
            for s in students
            if (s.id, a.book_folder, a.page_id) in confidence_by_key
        ]
        avg_by_assignment[(a.book_folder, a.page_id)] = (
            round(sum(levels) / len(levels), 2) if levels else None
        )

    return render_template(
        "admin_confidence_matrix.html",
        all_classes=all_classes,
        selected_class=selected_class,
        students=students,
        assignments=unique_assignments,
        confidence_by_key=confidence_by_key,
        avg_by_assignment=avg_by_assignment,
    )


@admin_bp.route("/analytics/confidence")
@login_required
@admin_required
def confidence_analytics():
    """Confidence analytics page filterable by student or class."""
    student_filter = request.args.get("student", "").strip()
    class_filter = request.args.get("class", "").strip()

    # Get all students and classes for filter dropdowns
    all_students = User.query.filter_by(role="student").order_by(User.name).all()
    all_classes = Class.query.filter_by(is_archived=False).order_by(Class.name).all()

    # Query confidence data
    query = StudentConfidence.query

    if student_filter:
        try:
            student_id = int(student_filter)
            query = query.filter_by(student_id=student_id)
            selected_student = User.query.get(student_id)
        except (ValueError, TypeError):
            selected_student = None
    else:
        selected_student = None

    if class_filter:
        try:
            class_id = int(class_filter)
            selected_class = Class.query.get(class_id)
            if selected_class:
                student_ids = [e.student_id for e in selected_class.enrollments]
                query = query.filter(StudentConfidence.student_id.in_(student_ids)) if student_ids else query.filter(False)
        except (ValueError, TypeError):
            selected_class = None
    else:
        selected_class = None

    confidence_records = query.order_by(StudentConfidence.recorded_at.desc()).all()

    # Build resource title lookup map
    resource_titles = {}
    if confidence_records:
        # Get unique (book_folder, page_id) pairs
        unique_resources = set()
        for record in confidence_records:
            unique_resources.add((record.book_folder, record.page_id))

        # Query assignments to get titles
        assignments = ReadingAssignment.query.filter(
            db.or_(*[
                db.and_(ReadingAssignment.book_folder == bf, ReadingAssignment.page_id == pid)
                for bf, pid in unique_resources
            ])
        ).all() if unique_resources else []

        for assignment in assignments:
            resource_titles[(assignment.book_folder, assignment.page_id)] = assignment.title

    # Calculate statistics
    stats = {
        "total_records": len(confidence_records),
        "avg_confidence": 0,
        "confidence_distribution": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
        "by_student": {},
        "by_class": {},
    }

    if confidence_records:
        stats["avg_confidence"] = sum(r.confidence_level for r in confidence_records) / len(confidence_records)

        for record in confidence_records:
            # Distribution
            stats["confidence_distribution"][record.confidence_level] += 1

            # By student
            if record.student_id not in stats["by_student"]:
                stats["by_student"][record.student_id] = {
                    "name": record.student.name,
                    "count": 0,
                    "avg": 0,
                    "levels": []
                }
            stats["by_student"][record.student_id]["count"] += 1
            stats["by_student"][record.student_id]["levels"].append(record.confidence_level)

        # Calculate averages for students
        for sid, data in stats["by_student"].items():
            data["avg"] = sum(data["levels"]) / len(data["levels"])

        # Sort students by average confidence (descending)
        stats["by_student_sorted"] = sorted(
            stats["by_student"].items(),
            key=lambda x: x[1]["avg"],
            reverse=True
        )
    else:
        stats["by_student_sorted"] = []

    return render_template(
        "admin_confidence_analytics.html",
        all_students=all_students,
        all_classes=all_classes,
        selected_student=selected_student,
        selected_class=selected_class,
        confidence_records=confidence_records,
        resource_titles=resource_titles,
        stats=stats,
    )


@admin_bp.route("/view-as-student")
@login_required
@admin_required
def view_as_student():
    """Admin page to view the app as any student (testing/demo)."""
    # Loading (or refreshing) this page always ends any leftover impersonation,
    # e.g. if the modal was closed without the clear request completing.
    session.pop("impersonating_student_id", None)
    session.pop("impersonation_token", None)

    all_students = User.query.filter_by(role="student").order_by(User.name).all()
    all_classes = Class.query.filter_by(is_archived=False).order_by(Class.name).all()

    # Group students by class
    students_by_class = {}
    for cls in all_classes:
        students_by_class[cls.id] = {
            "class": cls,
            "students": sorted((e.student for e in cls.enrollments), key=lambda s: s.name or "")
        }

    # Add unenrolled students to a special group
    enrolled_student_ids = set()
    for cls_data in students_by_class.values():
        enrolled_student_ids.update(s.id for s in cls_data["students"])

    unenrolled = [s for s in all_students if s.id not in enrolled_student_ids]
    if unenrolled:
        students_by_class[0] = {
            "class": type('obj', (object,), {'id': 0, 'name': 'Unenrolled Students'})(),
            "students": unenrolled
        }

    return render_template("admin_view_as_student.html", students_by_class=students_by_class)


@admin_bp.route("/clear-impersonation", methods=["POST"])
@login_required
def clear_impersonation():
    """Clear impersonation session variables."""
    session.pop("impersonating_student_id", None)
    session.pop("impersonation_token", None)
    session.modified = True
    return jsonify({"success": True})


@admin_bp.route("/view-as-student/token", methods=["POST"])
@login_required
@admin_required
def generate_student_token():
    """Generate a temporary token to view as a student."""
    data = request.get_json() or {}
    try:
        student_id = int(data.get("student_id"))
    except (TypeError, ValueError):
        student_id = None

    if not student_id:
        return jsonify({"success": False, "error": "Student ID required"}), 400

    student = User.query.filter_by(id=student_id, role="student").first()
    if not student:
        return jsonify({"success": False, "error": "Student not found"}), 404

    # Generate a signed token with student ID, valid for 1 hour
    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    token = serializer.dumps({
        "student_id": student_id,
        "admin_id": current_user.id,
        "created_at": datetime.utcnow().isoformat(),
    })

    return jsonify({
        "success": True,
        "token": token,
    })


@admin_bp.route("/view-as-student/embed/<int:student_id>")
def view_as_student_embed(student_id):
    """Embedded view of student dashboard. Requires valid token."""
    from flask import current_app

    token = request.args.get("token", "").strip()

    if not token:
        return render_template(
            "admin_student_embed_error.html",
            error="No token provided"
        ), 401

    # Verify token
    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    try:
        data = serializer.loads(token, max_age=3600)  # Valid for 1 hour
    except SignatureExpired:
        return render_template(
            "admin_student_embed_error.html",
            error="Token expired. Please try again."
        ), 401
    except BadSignature:
        return render_template(
            "admin_student_embed_error.html",
            error="Invalid token"
        ), 401

    # Verify student ID matches
    if data.get("student_id") != student_id:
        return render_template(
            "admin_student_embed_error.html",
            error="Student ID mismatch"
        ), 401

    # Fetch the student
    student = User.query.filter_by(id=student_id, role="student").first()
    if not student:
        return render_template(
            "admin_student_embed_error.html",
            error="Student not found"
        ), 404

    # Log in as the student in a session for this embedded view
    # We use a special impersonation session flag
    session["impersonating_student_id"] = student_id
    session["impersonation_token"] = token

    # Redirect to the dashboard
    return redirect(url_for("dashboard"))


# ============================================================================
# Data Reset / Student Data Management
# ============================================================================

@admin_bp.route("/api/students/<int:student_id>/quiz-data")
@login_required
@admin_required
def api_student_quiz_data(student_id):
    """Get all quiz answers for a student, grouped by question."""
    student = User.query.filter_by(id=student_id, role="student").first_or_404()

    answers = (QuizAnswer.query
               .filter_by(student_id=student_id)
               .order_by(QuizAnswer.submitted_at.desc())
               .all())

    result = []
    for answer in answers:
        question = answer.question
        result.append({
            "answer_id": answer.id,
            "question_id": question.id,
            "question_text": question.text[:100] + "..." if len(question.text) > 100 else question.text,
            "book_folder": question.book_folder,
            "page_id": question.page_id,
            "attempt_number": answer.attempt_number,
            "answer_text": answer.answer_text[:100] + "..." if len(answer.answer_text) > 100 else answer.answer_text,
            "auto_correct": answer.auto_correct,
            "final_correct": answer.final_correct,
            "submitted_at": answer.submitted_at.isoformat() if answer.submitted_at else None,
            "status": answer.status,
        })

    return jsonify({
        "student_id": student_id,
        "student_name": student.name,
        "quiz_answers_count": len(result),
        "quiz_answers": result,
    })


@admin_bp.route("/api/students/<int:student_id>/reading-data")
@login_required
@admin_required
def api_student_reading_data(student_id):
    """Get all reading activity for a student."""
    student = User.query.filter_by(id=student_id, role="student").first_or_404()

    activities = (ReadingActivity.query
                  .filter_by(student_id=student_id)
                  .order_by(ReadingActivity.last_opened_at.desc())
                  .all())

    result = []
    for activity in activities:
        result.append({
            "activity_id": activity.id,
            "book_folder": activity.book_folder,
            "page_id": activity.page_id,
            "total_seconds": activity.total_seconds,
            "completed": activity.completed,
            "first_opened_at": activity.first_opened_at.isoformat() if activity.first_opened_at else None,
            "last_opened_at": activity.last_opened_at.isoformat() if activity.last_opened_at else None,
            "completed_at": activity.completed_at.isoformat() if activity.completed_at else None,
        })

    return jsonify({
        "student_id": student_id,
        "student_name": student.name,
        "reading_activities_count": len(result),
        "reading_activities": result,
    })


@admin_bp.route("/api/students/<int:student_id>/confidence-data")
@login_required
@admin_required
def api_student_confidence_data(student_id):
    """Get all confidence ratings for a student."""
    student = User.query.filter_by(id=student_id, role="student").first_or_404()

    confidences = (StudentConfidence.query
                   .filter_by(student_id=student_id)
                   .order_by(StudentConfidence.recorded_at.desc())
                   .all())

    result = []
    for conf in confidences:
        result.append({
            "confidence_id": conf.id,
            "book_folder": conf.book_folder,
            "page_id": conf.page_id,
            "confidence_level": conf.confidence_level,
            "recorded_at": conf.recorded_at.isoformat() if conf.recorded_at else None,
            "updated_at": conf.updated_at.isoformat() if conf.updated_at else None,
        })

    return jsonify({
        "student_id": student_id,
        "student_name": student.name,
        "confidence_records_count": len(result),
        "confidence_records": result,
    })


@admin_bp.route("/api/students/<int:student_id>/quiz-answer/<int:answer_id>", methods=["DELETE"])
@login_required
@admin_required
def api_delete_quiz_answer(student_id, answer_id):
    """Delete a single quiz answer and its feedback insights."""
    student = User.query.filter_by(id=student_id, role="student").first_or_404()
    answer = QuizAnswer.query.filter_by(id=answer_id, student_id=student_id).first_or_404()

    question_text = answer.question.text[:50] if answer.question else "Unknown"

    # Cascade delete via relationship will handle StudentFeedbackInsight
    db.session.delete(answer)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": f"Deleted quiz answer for: {question_text}...",
    })


@admin_bp.route("/api/students/<int:student_id>/quiz-answers/all", methods=["DELETE"])
@login_required
@admin_required
def api_delete_all_quiz_answers(student_id):
    """Delete all quiz answers for a student."""
    student = User.query.filter_by(id=student_id, role="student").first_or_404()

    answers = QuizAnswer.query.filter_by(student_id=student_id).all()
    count = len(answers)

    for answer in answers:
        db.session.delete(answer)

    db.session.commit()

    return jsonify({
        "success": True,
        "count_deleted": count,
        "message": f"Deleted {count} quiz answer(s) for {student.name}",
    })


@admin_bp.route("/api/students/<int:student_id>/reading-activity/<int:activity_id>", methods=["DELETE"])
@login_required
@admin_required
def api_delete_reading_activity(student_id, activity_id):
    """Delete a single reading activity entry."""
    student = User.query.filter_by(id=student_id, role="student").first_or_404()
    activity = ReadingActivity.query.filter_by(id=activity_id, student_id=student_id).first_or_404()

    page_ref = f"{activity.book_folder}/{activity.page_id}"

    db.session.delete(activity)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": f"Deleted reading activity for: {page_ref}",
    })


@admin_bp.route("/api/students/<int:student_id>/reading-activities/all", methods=["DELETE"])
@login_required
@admin_required
def api_delete_all_reading_activities(student_id):
    """Delete all reading activities for a student."""
    student = User.query.filter_by(id=student_id, role="student").first_or_404()

    activities = ReadingActivity.query.filter_by(student_id=student_id).all()
    count = len(activities)

    # Also delete daily logs
    daily_logs = ReadingDailyLog.query.filter_by(student_id=student_id).all()
    daily_log_count = len(daily_logs)

    for activity in activities:
        db.session.delete(activity)

    for log in daily_logs:
        db.session.delete(log)

    db.session.commit()

    return jsonify({
        "success": True,
        "count_activities_deleted": count,
        "count_daily_logs_deleted": daily_log_count,
        "message": f"Deleted {count} reading activity and {daily_log_count} daily log entries for {student.name}",
    })


@admin_bp.route("/api/students/<int:student_id>/confidence/<int:confidence_id>", methods=["DELETE"])
@login_required
@admin_required
def api_delete_confidence_entry(student_id, confidence_id):
    """Delete a single confidence rating."""
    student = User.query.filter_by(id=student_id, role="student").first_or_404()
    confidence = StudentConfidence.query.filter_by(id=confidence_id, student_id=student_id).first_or_404()

    page_ref = f"{confidence.book_folder}/{confidence.page_id}"

    db.session.delete(confidence)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": f"Deleted confidence rating for: {page_ref}",
    })


@admin_bp.route("/api/students/<int:student_id>/confidence-ratings/all", methods=["DELETE"])
@login_required
@admin_required
def api_delete_all_confidence_ratings(student_id):
    """Delete all confidence ratings for a student."""
    student = User.query.filter_by(id=student_id, role="student").first_or_404()

    confidences = StudentConfidence.query.filter_by(student_id=student_id).all()
    count = len(confidences)

    for confidence in confidences:
        db.session.delete(confidence)

    db.session.commit()

    return jsonify({
        "success": True,
        "count_deleted": count,
        "message": f"Deleted {count} confidence rating(s) for {student.name}",
    })


@admin_bp.route("/api/students/<int:student_id>/flashcard-data")
@login_required
@admin_required
def api_student_flashcard_data(student_id):
    """Get all flashcard progress for a student."""
    student = User.query.filter_by(id=student_id, role="student").first_or_404()

    progress_list = (FlashcardProgress.query
                     .filter_by(student_id=student_id)
                     .all())

    sessions = (FlashcardStudySession.query
                .filter_by(student_id=student_id)
                .order_by(FlashcardStudySession.started_at.desc())
                .all())

    progress_result = []
    for progress in progress_list:
        progress_result.append({
            "progress_id": progress.id,
            "card_id": progress.card_id,
            "correct_count": progress.correct_count,
            "incorrect_count": progress.incorrect_count,
            "last_correct": progress.last_correct,
            "last_reviewed_at": progress.last_reviewed_at.isoformat() if progress.last_reviewed_at else None,
        })

    sessions_result = []
    for session in sessions:
        sessions_result.append({
            "session_id": session.id,
            "set_id": session.set_id,
            "set_title": session.set.title,
            "mode": session.mode,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "duration_seconds": session.duration_seconds,
            "completed": session.completed,
            "accuracy": session.accuracy,
        })

    return jsonify({
        "student_id": student_id,
        "student_name": student.name,
        "flashcard_progress_count": len(progress_result),
        "flashcard_sessions_count": len(sessions_result),
        "flashcard_progress": progress_result,
        "flashcard_sessions": sessions_result,
    })


@admin_bp.route("/api/students/<int:student_id>/flashcard-progress/all", methods=["DELETE"])
@login_required
@admin_required
def api_delete_all_flashcard_progress(student_id):
    """Delete all flashcard progress for a student."""
    student = User.query.filter_by(id=student_id, role="student").first_or_404()

    progress_list = FlashcardProgress.query.filter_by(student_id=student_id).all()
    sessions = FlashcardStudySession.query.filter_by(student_id=student_id).all()

    progress_count = len(progress_list)
    sessions_count = len(sessions)

    for progress in progress_list:
        db.session.delete(progress)

    for session in sessions:
        db.session.delete(session)

    db.session.commit()

    return jsonify({
        "success": True,
        "count_progress_deleted": progress_count,
        "count_sessions_deleted": sessions_count,
        "message": f"Deleted {progress_count} flashcard progress and {sessions_count} study session(s) for {student.name}",
    })


@admin_bp.route("/assignments")
@login_required
@admin_required
def view_assignments():
    """Reading assignments across all classes.

    Tests deliberately are not listed here — they live on the Assessment hub,
    which owns join codes, closing, and live per-student progress. Showing them
    in two places meant two half-features and two places to keep in sync.
    """
    return render_template("admin_assignments.html")


@admin_bp.route("/api/assignments")
@login_required
@admin_required
def api_get_all_assignments():
    """Reading assignments across all non-archived classes, with live status."""
    classes = Class.query.filter_by(is_archived=False).all()
    class_ids = [c.id for c in classes]

    assignments = []

    reading_assignments = ReadingAssignment.query.filter(
        ReadingAssignment.class_id.in_(class_ids)
    ).order_by(ReadingAssignment.created_at.desc()).all()

    for ra in reading_assignments:
        # Check if it's "live" (has a due date in the future or no due date yet)
        is_live = not ra.due_date or ra.due_date > datetime.utcnow()
        assignments.append({
            "id": f"reading-{ra.id}",
            "type": "reading",
            "title": ra.title,
            "class_name": ra.class_.name if ra.class_ else "Individual",
            "resource_type": ra.resource_label(),
            "target": ra.target_label(),
            "due_date": ra.due_date.strftime("%b %d, %Y %I:%M %p") if ra.due_date else "No due date",
            "due_date_raw": ra.due_date.isoformat() if ra.due_date else None,
            "is_live": is_live,
            "created_at": ra.created_at.strftime("%b %d, %Y"),
            "model_id": ra.id,
        })

    return jsonify({
        "assignments": assignments,
        "total_count": len(assignments),
        "live_count": sum(1 for a in assignments if a.get("is_live")),
    })


@admin_bp.route("/api/assignments/reading/<int:assignment_id>/close", methods=["POST"])
@login_required
@admin_required
def close_reading_assignment(assignment_id):
    """Close/retire a reading assignment."""
    assignment = ReadingAssignment.query.get_or_404(assignment_id)

    # Set due date to now, making it expired
    assignment.due_date = datetime.utcnow()
    db.session.commit()

    return jsonify({
        "success": True,
        "message": f"Reading assignment '{assignment.title}' has been closed.",
        "assignment_id": assignment_id,
    })


@admin_bp.route("/api/test-papers/published")
@login_required
@admin_required
def api_get_test_papers():
    """Get all published test papers for quick assignment.

    Deliberately NOT at /api/test-papers: admin_bp mounts at /admin, so that path
    collides exactly with the Test Builder's own paper list, and admin_bp is
    registered first — this route silently answered every builder request with
    only *published* papers, i.e. an empty list for a workspace of drafts, which
    read as "every test has been deleted".
    """
    papers = TestPaper.query.filter_by(status="published").order_by(TestPaper.created_at.desc()).all()

    return jsonify({
        "papers": [{
            "id": p.id,
            "title": p.title,
            "description": p.description,
            "question_count": len(p.paper_questions),
            "total_marks": p.total_marks,
            "has_hl_only": p.has_hl_only_questions,
            "created_at": p.created_at.strftime("%b %d, %Y"),
        } for p in papers],
        "total_count": len(papers),
    })


# ============================================================================
# Student Name Mapping (Local-only, GDPR-compliant)
# ============================================================================

@admin_bp.route("/api/student-names", methods=["GET"])
@login_required
@admin_required
def api_get_student_names():
    """Get all student name mappings for the current teacher."""
    mappings = load_name_mappings(current_user.id)
    return jsonify({"mappings": mappings})


@admin_bp.route("/api/student-names/<int:student_id>", methods=["POST"])
@login_required
@admin_required
def api_set_student_name(student_id):
    """Set or update a student's real name (stored locally only)."""
    student = User.query.filter_by(id=student_id, role="student").first_or_404()
    data = request.get_json() or {}
    real_name = data.get("real_name", "").strip()

    try:
        save_name_mapping(current_user.id, student_id, real_name)
        return jsonify({
            "success": True,
            "student_id": student_id,
            "real_name": real_name if real_name else None,
            "alias": student.name,
        })
    except Exception as e:
        return server_error(e)


@admin_bp.route("/api/student-names/<int:student_id>", methods=["DELETE"])
@login_required
@admin_required
def api_delete_student_name(student_id):
    """Delete a student's real name mapping (clears local override)."""
    student = User.query.filter_by(id=student_id, role="student").first_or_404()

    try:
        save_name_mapping(current_user.id, student_id, "")
        return jsonify({
            "success": True,
            "student_id": student_id,
            "alias": student.name,
        })
    except Exception as e:
        return server_error(e)
