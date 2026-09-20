from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, request, jsonify, send_file, send_from_directory, abort
from scraper import ContentScraper, extract_youtube_from_saved_files
import os
from pathlib import Path
import json
from datetime import datetime
import hashlib
import uuid
import shutil
import re

from flask_login import login_required, current_user
from flask_migrate import Migrate
from flask_wtf import CSRFProtect
from datetime import timedelta

from extensions import db, login_manager, mail, limiter
from auth import admin_required
from safe_errors import server_error
from file_guard import is_servable
from request_log import init_request_logging

app = Flask(__name__)
scraper = ContentScraper(data_dir="data")

# Ensure templates and static dirs exist
Path("templates").mkdir(exist_ok=True)
Path("static").mkdir(exist_ok=True)
Path("static/css").mkdir(exist_ok=True)
Path("static/js").mkdir(exist_ok=True)

def _is_dev_environment():
    """True only when FLASK_DEBUG is explicitly switched on."""
    return os.environ.get("FLASK_DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}


def _load_secret_key():
    """Fail closed: outside dev a missing SECRET_KEY is an auth bypass, not a warning.

    The old fallback was a fixed public string, so anyone could forge a session
    cookie for any user if the variable was ever left unset.
    """
    key = os.environ.get("SECRET_KEY", "").strip()
    if key:
        return key
    if _is_dev_environment():
        return "dev-insecure-change-me"
    raise RuntimeError(
        "SECRET_KEY is not set. Generate one with "
        "`python -c \"import secrets; print(secrets.token_hex(32))\"` and set it in the "
        "environment. Refusing to start with a known fallback key."
    )


app.config["SECRET_KEY"] = _load_secret_key()
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + str(Path("data/app.db").resolve())
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0  # don't let browsers cache stale static JS/CSS
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
# Secure cookies by default; only relaxed in dev mode, where plain-http is normal.
app.config["SESSION_COOKIE_SECURE"] = not _is_dev_environment()
app.config["REMEMBER_COOKIE_SECURE"] = not _is_dev_environment()
app.config["REMEMBER_COOKIE_HTTPONLY"] = True

app.config["MAIL_SERVER"] = os.environ.get("MAIL_SERVER")
app.config["MAIL_PORT"] = int(os.environ.get("MAIL_PORT", 587))
app.config["MAIL_USE_TLS"] = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD")
app.config["MAIL_DEFAULT_SENDER"] = os.environ.get("MAIL_FROM_ADDRESS", os.environ.get("MAIL_USERNAME"))

db.init_app(app)
migrate = Migrate(app, db)
login_manager.init_app(app)
login_manager.login_view = "auth.login"
mail.init_app(app)
limiter.init_app(app)
csrf = CSRFProtect(app)
init_request_logging(app)

import models  # noqa: E402  (register models with SQLAlchemy metadata)

from auth_routes import auth_bp
from admin_routes import admin_bp
from quiz_routes import quiz_bp
from flashcard_routes import flashcards_bp
from concept_chains_routes import concept_chains_bp, init_concept_chains
from report_card_routes import report_card_bp
from unit_plan_routes import unit_plan_bp
from test_routes import test_bp
from assessment_routes import assessment_bp
from slides_routes import slides_bp
from games_routes import games_bp

app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp, url_prefix="/admin")
app.register_blueprint(quiz_bp)
app.register_blueprint(flashcards_bp)
app.register_blueprint(concept_chains_bp)
app.register_blueprint(report_card_bp)
app.register_blueprint(unit_plan_bp, url_prefix="/unit-plan")
app.register_blueprint(test_bp)
app.register_blueprint(assessment_bp)
app.register_blueprint(slides_bp)
app.register_blueprint(games_bp)
csrf.exempt(quiz_bp)  # JSON APIs, same as the other fetch()-driven endpoints
csrf.exempt(flashcards_bp)
csrf.exempt(concept_chains_bp)
csrf.exempt(report_card_bp)
csrf.exempt(unit_plan_bp)
csrf.exempt(test_bp)
csrf.exempt(assessment_bp)
csrf.exempt(slides_bp)
csrf.exempt(games_bp)

# Background task scheduler for cleanup jobs
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    scheduler = BackgroundScheduler()

    def run_test_cleanup():
        """Cleanup expired test submissions (live tests auto-submit, unstarted deleted)"""
        try:
            from test_cleanup import cleanup_expired_tests
            result = cleanup_expired_tests(hours=3)
            print(f"Test cleanup completed: {result['total_cleaned']} tests cleaned "
                  f"({result['auto_submitted']} submitted, {result['deleted_unstarted']} deleted)")
        except Exception as e:
            print(f"Test cleanup failed: {e}")

    # Run cleanup every hour
    scheduler.add_job(run_test_cleanup, 'interval', hours=1, id='test_cleanup')
    scheduler.start()
except ImportError:
    print("Warning: APScheduler not installed. Scheduled cleanup disabled.")
except Exception as e:
    print(f"Warning: Could not start scheduler: {e}")


@app.route("/__dev/last-modified")
def dev_last_modified():
    # Dev-only: lets the auto-reload script (injected below) poll for the
    # newest mtime across templates/static and refresh the tab when it moves —
    # this app has no build step/HMR, so this is the closest practical
    # equivalent for a Flask+Jinja app.
    if not app.debug:
        abort(404)
    latest = 0.0
    for watched_dir in ("templates", "static"):
        for dirpath, _dirnames, filenames in os.walk(watched_dir):
            for filename in filenames:
                try:
                    mtime = os.path.getmtime(os.path.join(dirpath, filename))
                except OSError:
                    continue
                if mtime > latest:
                    latest = mtime
    return jsonify({"mtime": latest})


_DEV_RELOAD_SCRIPT = b"""
<script>
(function () {
  var lastMtime = null;
  function poll() {
    fetch('/__dev/last-modified').then(function (r) { return r.json(); }).then(function (data) {
      if (lastMtime === null) { lastMtime = data.mtime; }
      else if (data.mtime > lastMtime) { location.reload(); return; }
      setTimeout(poll, 1000);
    }).catch(function () { setTimeout(poll, 1000); });
  }
  poll();
})();
</script>
"""


@app.after_request
def _inject_dev_reload_script(response):
    # Dev-only auto-reload: since templates auto-reload on save (TEMPLATES_AUTO_RELOAD
    # under debug=True) but nothing tells the open browser tab to refresh, every edit
    # otherwise needs a manual F5. Never runs outside debug mode.
    if app.debug and (response.content_type or "").startswith("text/html"):
        body = response.get_data()
        if b"</body>" in body:
            response.set_data(body.replace(b"</body>", _DEV_RELOAD_SCRIPT + b"</body>", 1))
    return response


@app.before_request
def _init_concept_chains():
    """Initialize concept chains on first run."""
    try:
        init_concept_chains()
    except Exception:
        pass


@login_manager.user_loader
def load_user(user_id):
    from flask import request, session
    from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

    # Check if there's an active impersonation session. Impersonation only
    # applies to student-facing pages (the iframe) — /admin/* requests always
    # resolve to the real logged-in user so the admin UI is never hijacked.
    if (
        "impersonating_student_id" in session
        and "impersonation_token" in session
        and not request.path.startswith("/admin")
    ):
        try:
            serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"])
            token_data = serializer.loads(session["impersonation_token"], max_age=3600)
            if token_data.get("student_id") == session.get("impersonating_student_id"):
                # Token is valid, return the student
                student = db.session.get(models.User, session["impersonating_student_id"])
                if student and student.role == "student":
                    return student
        except (SignatureExpired, BadSignature):
            # Token expired or invalid, clear impersonation
            session.pop("impersonating_student_id", None)
            session.pop("impersonation_token", None)

    # Normal user loading
    return db.session.get(models.User, int(user_id))

@app.context_processor
def inject_now():
    return {'get_now': datetime.now}

@app.context_processor
def inject_format_marks():
    # Test marks are floats (MCQs are worth 0.5) — templates use this so whole
    # values don't render as "7.0 marks".
    from models import format_marks
    return {'format_marks': format_marks}

@app.context_processor
def inject_avatar_catalog():
    from avatars import AVATAR_CATALOG, AVATAR_BY_KEY
    return {'AVATAR_CATALOG': AVATAR_CATALOG, 'AVATAR_BY_KEY': AVATAR_BY_KEY}

@app.route('/profile')
@login_required
def profile():
    from avatars import AVATAR_CATALOG
    taken = {
        row[0] for row in
        db.session.query(models.User.avatar).filter(
            models.User.avatar.isnot(None), models.User.id != current_user.id
        ).all()
    }
    return render_template('profile.html', avatar_catalog=AVATAR_CATALOG, taken_avatars=taken)


@app.route('/api/profile/avatar', methods=['POST'])
@login_required
@csrf.exempt
def update_avatar():
    from avatars import AVATAR_KEYS
    data = request.get_json(force=True, silent=True) or {}
    key = data.get('avatar')
    # Whitelist-only: reject anything that isn't one of the fixed built-in
    # keys, so this can never become a path for a URL, uploaded file, or
    # arbitrary text — no personal information can enter through this field.
    if key not in AVATAR_KEYS:
        return jsonify({"error": "Not a valid avatar"}), 400
    # One avatar per person — picking your own current one again is a no-op,
    # but taking someone else's is rejected rather than silently duplicating.
    if key != current_user.avatar:
        holder = models.User.query.filter_by(avatar=key).first()
        if holder and holder.id != current_user.id:
            return jsonify({"error": "That avatar is already taken by someone else"}), 409
    current_user.avatar = key
    db.session.commit()
    return jsonify({"ok": True, "avatar": key})


@app.route("/service-worker.js")
def service_worker():
    # Served from the site root so the PWA service worker's scope covers "/".
    return send_from_directory(Path(app.root_path) / "static", "service-worker.js",
                               mimetype="application/javascript")


@app.route("/favicon.ico")
def favicon():
    return send_from_directory(
        Path(app.root_path) / "static" / "images",
        "favicon.ico",
        mimetype="image/vnd.microsoft.icon",
    )


@app.cli.command("create-admin")
def create_admin_command():
    """Create an admin user: flask create-admin"""
    import getpass

    username = input("Admin username: ").strip().lower()
    name = input("Admin name: ").strip()
    email = input("Admin email (optional): ").strip().lower()
    password = getpass.getpass("Admin password: ")

    if models.User.query.filter_by(username=username).first():
        print(f"A user with username {username} already exists.")
        return
    if email and models.User.query.filter_by(email=email).first():
        print(f"A user with email {email} already exists.")
        return

    user = models.User(username=username, email=email or None, name=name, role="admin")
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    print(f"Admin account created for {username}.")

@app.cli.command("setup-test-class")
def setup_test_class_command():
    """Set up a test class with the test user: flask setup-test-class"""
    admin = models.User.query.filter_by(role="admin").first()
    if not admin:
        print("No admin user found. Create an admin first with: flask create-admin")
        return

    test_user = models.User.query.filter_by(email="user@test.com").first()
    if not test_user:
        print("Test user (user@test.com) not found. Check TEST_USER_EMAIL in .env")
        return

    existing_class = models.Class.query.filter_by(name="Test class").first()
    if existing_class:
        print("Test class already exists.")
        return

    test_class = models.Class(name="Test class", created_by_id=admin.id)
    db.session.add(test_class)
    db.session.flush()

    enrollment = models.ClassEnrollment(class_id=test_class.id, student_id=test_user.id)
    db.session.add(enrollment)
    db.session.commit()

    print("✓ Test class created and test user enrolled.")

@app.errorhandler(400)
def error_400(e):
    if request.path.startswith('/api/'):
        print(f'[DEBUG] 400 error on API path: {request.path}')
        print(f'[DEBUG] Error: {e}')
        return jsonify({'success': False, 'error': 'Bad request'}), 400
    return render_template('error.html', code=400, title='Bad Request', message='The request was invalid.'), 400

@app.errorhandler(404)
def error_404(e):
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'error': 'Not found'}), 404
    return render_template('error.html', code=404, title='Page Not Found', message='The page you\'re looking for doesn\'t exist or has been moved.'), 404

@app.errorhandler(403)
def error_403(e):
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'error': 'Forbidden'}), 403
    return render_template('error.html', code=403, title='Access Forbidden', message='You don\'t have permission to access this resource.'), 403

@app.errorhandler(500)
def error_500(e):
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'error': 'Internal server error'}), 500
    return render_template('error.html', code=500, title='Server Error', message='Something went wrong on our end. Please try again later.'), 500

def parse_topic_title(title):
    import re
    # Match patterns like:
    # "Theme A Concepts of computer science" -> Group 1: "Theme A", Group 2: "Concepts of computer science"
    # "A1.1 Computer hardware and operation" -> Group 1: "A1.1", Group 2: "Computer hardware and operation"
    # "A1.1.1 Describe the functions..." -> Group 1: "A1.1.1", Group 2: "Describe the functions..."
    # "A 1.2 Networks" -> Group 1: "A 1.2", Group 2: "Networks"
    match = re.match(r'^((?:Theme\s+[A-Z])|(?:[A-Z]\s*\d*(?:\.\d+)*))\.?\s*(.*)$', title, re.IGNORECASE)
    if match:
        topic_number = match.group(1).strip()
        section_title = match.group(2).strip()
    else:
        topic_number = ""
        section_title = title
    return topic_number, section_title

def format_vocabulary_text(text):
    if not text:
        return ""
    formatted_lines = []
    for line in text.split('\n'):
        stripped = line.strip()
        if not stripped:
            formatted_lines.append('')
            continue
        if '<strong>' in line or '<b>' in line:
            formatted_lines.append(line)
            continue
        # Try common separators
        parts = None
        for sep in (' – ', ' - ', ' — ', ' : ', ': '):
            if sep in stripped:
                parts = stripped.split(sep, 1)
                break
        if parts:
            formatted_lines.append(f"<strong>{parts[0].strip()}</strong>: {parts[1].strip()}")
        else:
            formatted_lines.append(line)
    return '\n'.join(formatted_lines)

def merge_consecutive_headings(blocks):
    merged = []
    for b in blocks:
        if b.get('type') == 'heading':
            if merged and merged[-1].get('type') == 'heading':
                h1_text = merged[-1].get('text', '').strip()
                h2_text = b.get('text', '').strip()
                if h1_text and h2_text:
                    merged[-1]['text'] = f"{h1_text} - {h2_text}"
                elif h2_text:
                    merged[-1]['text'] = h2_text
                # Retain the higher header level
                merged[-1]['level'] = min(merged[-1].get('level', 3), b.get('level', 3))
            else:
                merged.append(b)
        else:
            merged.append(b)
    return merged

@app.route('/')
def index():
    """Public landing page - first thing anyone sees"""
    if current_user.is_authenticated:
        from flask import redirect, url_for
        return redirect(url_for('admin.admin_home') if current_user.is_admin() else url_for('dashboard'))
    return render_template('landing.html')

@app.route('/admin/scraper-hub')
@login_required
@admin_required
def scraper_hub():
    """Scraper control hub (legacy homepage) - admin only"""
    return render_template('homepage.html')

@app.route('/books')
@login_required
def books_catalogue():
    """Redirect to resources page - books are now shown there"""
    from flask import redirect, url_for
    return redirect(url_for('resources_hub'))

EE_EXEMPLARS_DIR = Path('data') / 'ee_exemplars'
EE_EXEMPLARS_METADATA_FILE = EE_EXEMPLARS_DIR / 'metadata.json'
EE_EXEMPLARS_PDF_DIR = EE_EXEMPLARS_DIR / 'pdfs'

@app.route('/resources')
@login_required
def resources_hub():
    """Landing page listing available resource types (course books, exemplar library, ...)"""
    from models import Resource
    return render_template('resources.html', resource_count=Resource.query.count())

@app.route('/resources/exemplars')
@login_required
def ee_exemplars():
    """IB EE / IA exemplar library - searchable/filterable grid of past student papers"""
    return render_template('ee_exemplars.html')

@app.route('/api/ee-exemplars', methods=['GET'])
@login_required
def get_ee_exemplars():
    """Return the exemplar metadata list"""
    if not EE_EXEMPLARS_METADATA_FILE.exists():
        return jsonify({'exemplars': []})
    with open(EE_EXEMPLARS_METADATA_FILE, 'r', encoding='utf-8') as f:
        exemplars = json.load(f)
    return jsonify({'exemplars': exemplars})

@app.route('/resources/exemplars/pdf/<path:filename>')
@login_required
def ee_exemplar_pdf(filename):
    """Serve one exemplar PDF"""
    if '..' in filename:
        abort(404)
    return send_from_directory(EE_EXEMPLARS_PDF_DIR, filename)

@app.route('/reading-analytics')
@login_required
def reading_analytics():
    """Student reading analytics dashboard"""
    if current_user.is_admin():
        from flask import redirect, url_for
        return redirect(url_for('admin.admin_home'))

    return render_template('reading_analytics.html')

@app.route('/dashboard')
@login_required
def dashboard():
    """Student facing learning dashboard"""
    if current_user.is_admin():
        from flask import redirect, url_for
        return redirect(url_for('admin.admin_home'))

    from models import ClassEnrollment, ReadingAssignment, ReadingActivity

    class_ids = [e.class_id for e in ClassEnrollment.query.filter_by(student_id=current_user.id).all()]
    assignments = _assignments_for_student(current_user.id, class_ids)

    activity_rows = ReadingActivity.query.filter_by(student_id=current_user.id).all()
    activity_by_key = {(r.book_folder, r.page_id): r for r in activity_rows}
    completed_page_ids = [r.page_id for r in activity_rows if r.completed]

    assignments_data = [_serialize_assignment(a, activity_by_key) for a in assignments]

    # Get most recent reading activity for "Continue reading" card
    continue_reading = None
    if activity_rows:
        most_recent = max(activity_rows, key=lambda r: r.last_opened_at or datetime.min)
        book_json_path = Path('data') / most_recent.book_folder / 'book.json'
        try:
            if book_json_path.exists():
                with open(book_json_path, 'r', encoding='utf-8') as f:
                    book_data = json.load(f)
                    book_title = book_data.get('title', 'Unknown Book')
                    page_title = 'Unknown Page'
                    for page in book_data.get('pages', []):
                        if page.get('id') == most_recent.page_id or page.get('folder') == most_recent.page_id:
                            page_title = page.get('title', 'Unknown Page')
                            break
                    continue_reading = {
                        'book_folder': most_recent.book_folder,
                        'page_id': most_recent.page_id,
                        'book_title': book_title,
                        'page_title': page_title,
                        'last_opened': most_recent.last_opened_at.strftime('%b %d') if most_recent.last_opened_at else None,
                        'url': f'/book/{most_recent.book_folder}/page/{most_recent.page_id}'
                    }
        except:
            pass

    # Compute reading streak and weekly stats
    streak_days = 0
    weekly_minutes = 0
    if activity_rows:
        today = datetime.now().date()
        dates_active = sorted(set(r.last_opened_at.date() for r in activity_rows if r.last_opened_at), reverse=True)

        for i, date in enumerate(dates_active):
            expected_date = today - timedelta(days=i)
            if date == expected_date:
                streak_days += 1
            else:
                break

        week_ago = datetime.now() - timedelta(days=7)
        weekly_minutes = round(sum(r.total_seconds or 0 for r in activity_rows if r.last_opened_at and r.last_opened_at >= week_ago) / 60, 1)

    from flashcard_routes import flashcard_tasks_for_student
    flashcard_tasks = flashcard_tasks_for_student(current_user.id)

    # Get active games in student's classes
    from models import GameSession
    active_games = GameSession.query.filter(
        GameSession.class_id.in_(class_ids),
        GameSession.status.in_(['lobby', 'active'])
    ).order_by(GameSession.created_at.desc()).all()

    return render_template('dashboard.html', assignments=assignments_data, assignments_data=assignments_data, completed_page_ids=completed_page_ids, continue_reading=continue_reading, streak_days=streak_days, weekly_minutes=weekly_minutes, flashcard_tasks=flashcard_tasks, active_games=active_games)


@app.route('/student/reading')
@login_required
def student_reading():
    """Student reading assignments page"""
    if current_user.is_admin():
        from flask import redirect, url_for
        return redirect(url_for('admin.admin_home'))

    from models import ClassEnrollment, ReadingActivity
    from flashcard_routes import flashcard_tasks_for_student

    class_ids = [e.class_id for e in ClassEnrollment.query.filter_by(student_id=current_user.id).all()]
    assignments = _assignments_for_student(current_user.id, class_ids)

    activity_rows = ReadingActivity.query.filter_by(student_id=current_user.id).all()
    activity_by_key = {(r.book_folder, r.page_id): r for r in activity_rows}

    assignments_data = [_serialize_assignment(a, activity_by_key) for a in assignments]
    flashcard_tasks = flashcard_tasks_for_student(current_user.id)

    return render_template('student_reading.html', assignments=assignments_data, flashcard_tasks=flashcard_tasks)


@app.route('/student/flashcards')
@login_required
def student_flashcards():
    """Student flashcard assignments page"""
    if current_user.is_admin():
        from flask import redirect, url_for
        return redirect(url_for('admin.admin_home'))

    from flashcard_routes import flashcard_tasks_for_student

    flashcard_tasks = flashcard_tasks_for_student(current_user.id)
    return render_template('student_flashcards.html', flashcard_tasks=flashcard_tasks)


def _assignments_for_student(student_id, class_ids):
    """All assignments visible to a student: their class assignments plus any
    assignments targeted directly at them individually."""
    from models import ReadingAssignment
    from sqlalchemy import or_, and_

    conditions = [ReadingAssignment.student_id == student_id]
    if class_ids:
        conditions.append(
            and_(
                ReadingAssignment.class_id.in_(class_ids),
                ReadingAssignment.student_id.is_(None),
            )
        )
    return (
        ReadingAssignment.query.filter(or_(*conditions))
        .order_by(ReadingAssignment.due_date.asc().nullslast())
        .all()
    )


def _serialize_assignment(a, activity_by_key):
    row = activity_by_key.get((a.book_folder, a.page_id))

    # Get estimated reading time from book.json
    estimated_minutes = None
    book_json_path = Path('data') / a.book_folder / 'book.json'
    if book_json_path.exists():
        try:
            with open(book_json_path, 'r', encoding='utf-8') as f:
                book_data = json.load(f)
                for page in book_data.get('pages', []):
                    if page.get('id') == a.page_id or page.get('folder') == a.page_id:
                        estimated_minutes = page.get('reading_time_minutes')
                        break
        except:
            pass

    return {
        'title': a.title,
        'resource_type': a.resource_type,
        'resource_label': a.resource_label(),
        'link': a.resource_url(),
        'due_date': a.due_date.strftime('%b %d, %Y %I:%M %p') if a.due_date else None,
        'due_date_raw': a.due_date.isoformat() if a.due_date else None,
        'class_name': a.class_.name if a.class_ else 'Individual',
        'completed': bool(row and row.completed),
        'total_minutes': round((row.total_seconds or 0) / 60, 1) if row else 0,
        'estimated_minutes': estimated_minutes,
        'created_at': a.created_at.isoformat() if a.created_at else None,
    }

@app.route('/my-resources')
@login_required
def my_resources():
    """Dedicated page listing everything assigned to the current student, across all their classes"""
    if current_user.is_admin():
        from flask import redirect, url_for
        return redirect(url_for('admin.admin_home'))

    from models import ClassEnrollment, ReadingAssignment, ReadingActivity

    enrollments = ClassEnrollment.query.filter_by(student_id=current_user.id).all()
    class_ids = [e.class_id for e in enrollments]

    assignments = _assignments_for_student(current_user.id, class_ids)

    activity_rows = ReadingActivity.query.filter_by(student_id=current_user.id).all()
    activity_by_key = {(r.book_folder, r.page_id): r for r in activity_rows}

    assignments_data = [_serialize_assignment(a, activity_by_key) for a in assignments]
    classes = [e.class_ for e in enrollments]

    return render_template('my_resources.html', assignments=assignments_data, classes=classes)

@app.route('/book/<book_folder>/learn')
@login_required
def book_learn(book_folder):
    """Per-book course home page"""
    return render_template('book_learn.html', book_folder=book_folder)

@app.route('/book/<book_folder>/page/<page_id>')
@login_required
def book_page(book_folder, page_id):
    """View a page in a book"""
    # Redirect exemplar collection resources to the exemplars page
    if book_folder == "EE_Marxify":
        from flask import redirect, url_for
        return redirect(url_for("ee_exemplars"))

    initial_completed = False
    completed_page_ids = []
    if not current_user.is_admin():
        from models import ReadingActivity
        now = datetime.now()
        activity = ReadingActivity.query.filter_by(
            student_id=current_user.id, book_folder=book_folder, page_id=page_id
        ).first()
        if not activity:
            activity = ReadingActivity(
                student_id=current_user.id, book_folder=book_folder, page_id=page_id,
                first_opened_at=now, last_opened_at=now,
            )
            db.session.add(activity)
        else:
            activity.last_opened_at = now
        db.session.commit()
        initial_completed = activity.completed

        book_activity = ReadingActivity.query.filter_by(
            student_id=current_user.id, book_folder=book_folder
        ).all()
        completed_page_ids = [r.page_id for r in book_activity if r.completed]

    return render_template(
        'book_page.html', book_folder=book_folder, page_id=page_id,
        initial_completed=initial_completed, completed_page_ids=completed_page_ids,
    )

@app.route('/editor/<path:folder_name>')
@login_required
@admin_required
def editor(folder_name):
    """Standalone textbook page editor (legacy)"""
    # Validate that the folder actually exists; if not, try to find it
    data_dir = Path('data')
    folder_path = data_dir / folder_name

    # If the folder doesn't exist, try to find a matching folder
    if not folder_path.exists():
        # "Book_X/<page_id>" where the page's folder was renamed — resolve via book.json
        if '/' in folder_name:
            parent, pid = folder_name.split('/', 1)
            resolved = scraper.resolve_page_folder(parent, pid)
            if (data_dir / parent / resolved).is_dir():
                folder_name = f"{parent}/{resolved}"
                return render_template('editor.html', folder_name=folder_name)

        # Check if there's a folder with this name but different suffix (collision case)
        for candidate in sorted(data_dir.iterdir()):
            if candidate.is_dir() and candidate.name.startswith(folder_name + '_'):
                # Found a collision version, use that instead
                folder_name = candidate.name
                break
            elif candidate.is_dir() and folder_name.startswith(candidate.name + '_'):
                # The requested name is a collision version but the base exists
                break

        # If still not found, search in subdirectories (e.g., criterion_a might be in Internal_Assessment/criterion_a)
        if not (data_dir / folder_name).exists():
            for parent_dir in sorted(data_dir.iterdir()):
                if parent_dir.is_dir():
                    potential_path = parent_dir / folder_name
                    if potential_path.exists() and potential_path.is_dir():
                        folder_name = f"{parent_dir.name}/{folder_name}"
                        break

    return render_template('editor.html', folder_name=folder_name)

@app.route('/syllabus')
@login_required
@admin_required
def syllabus_manager():
    """Syllabus structure manager page"""
    return render_template('syllabus.html')

@app.route('/api/scrape', methods=['POST'])
@login_required
@admin_required
def scrape():
    """Scrape a URL via HTTP or local file"""
    data = request.get_json()
    url = data.get('url', '').strip()

    if not url:
        return jsonify({'success': False, 'error': 'URL is required'}), 400

    if not (url.startswith('http') or url.startswith('file://') or os.path.exists(url) or (':' in url and not url.startswith('http'))):
        url = 'https://' + url

    result = scraper.scrape_url(url)
    return jsonify(result)

@app.route('/api/scrape-dom', methods=['POST'])
@login_required
@admin_required
def scrape_dom():
    """Scrape content extracted from DOM (via Chrome Extension) - single page or multi-chapter book"""
    try:
        data = request.get_json()
        url = data.get('url', '')
        title = data.get('title', 'Untitled')
        is_book = data.get('is_book', False)
        chapters = data.get('chapters', [])

        if not url:
            return jsonify({'success': False, 'error': 'URL is required'}), 400

        # Check if URL belongs to a book page (e.g. /books/<book_id>/<page_id>)
        # matches both http/https and local file:// URL structures
        book_match = re.search(r'/books/(\d+)/(\d+)', url)
        if book_match:
            book_id = book_match.group(1)
            page_id = book_match.group(2)
            
            # Get book title from payload
            book_title = data.get('bookTitle')
            if not book_title or book_title == 'Untitled Book':
                book_title = f"Book {book_id}"
                
            # Determine book folder name (matching scraper.py's scrape_book)
            sanitized_book_title = "".join(c for c in book_title if c not in r'\/:*?"<>|').strip()
            if not sanitized_book_title or len(sanitized_book_title) < 3:
                book_folder = f"book_{book_id}"
            else:
                book_folder = re.sub(r'\s+', '_', sanitized_book_title)
                
            book_dir = Path("data") / book_folder
            book_dir.mkdir(parents=True, exist_ok=True)
            
            # Handle cover image if provided in payload
            cover_img_src = data.get('coverImg')
            cover_local_path = None
            if cover_img_src:
                ext = 'png'
                if '.jpg' in cover_img_src or '.jpeg' in cover_img_src:
                    ext = 'jpg'
                elif '.webp' in cover_img_src:
                    ext = 'webp'
                elif '.svg' in cover_img_src:
                    ext = 'svg'
                
                if cover_img_src.startswith('data:'):
                    try:
                        header, encoded = cover_img_src.split(",", 1)
                        import base64
                        data_bytes = base64.b64decode(encoded)
                        cover_file = book_dir / f"cover.{ext}"
                        with open(cover_file, 'wb') as img_f:
                            img_f.write(data_bytes)
                        cover_local_path = f"{book_folder}/cover.{ext}"
                    except Exception as e:
                        print(f"Failed to save base64 cover: {e}")
                else:
                    try:
                        cover_file = scraper._download_image(cover_img_src, url, book_dir, "cover")
                        if cover_file:
                            cover_local_path = str(cover_file.relative_to(Path("data"))).replace('\\', '/')
                    except Exception as e:
                        print(f"Failed to download cover image: {e}")
            
            # Save the page content inside the book directory under the page's
            # folder (folders may be renamed; falls back to page_id for new pages)
            content_dir = book_dir / scraper.resolve_page_folder(book_folder, page_id)
            content_dir.mkdir(parents=True, exist_ok=True)
            
            res = _scrape_single_page(book_folder + "/" + page_id, content_dir, title, url, data)
            
            # Update book metadata (book.json)
            book_meta_file = book_dir / "book.json"
            book_meta = {
                'id': book_id,
                'title': book_title,
                'url': url,
                'created_at': datetime.now().isoformat(),
                'pages': []
            }
            if book_meta_file.exists():
                try:
                    with open(book_meta_file, 'r', encoding='utf-8') as f:
                        book_meta = json.load(f)
                except:
                    pass
            
            if cover_local_path:
                book_meta['cover_image'] = cover_local_path
                    
            # Check if page is already in book_meta['pages']
            page_entry = {
                'id': page_id,
                'title': title,
                'url': url
            }
            if not any(p.get('id') == page_id for p in book_meta.get('pages', [])):
                book_meta.setdefault('pages', []).append(page_entry)
                
            with open(book_meta_file, 'w', encoding='utf-8') as f:
                json.dump(book_meta, f, indent=2, ensure_ascii=False)
                
            # Update books catalogue
            scraper._update_books_catalogue()
            
            return res

        # Fallback for standard non-book pages
        # Generate folder name from sanitized title
        sanitized_title = "".join(c for c in title if c not in r'\/:*?"<>|').strip()
        generic_titles = {'untitled', 'books'}
        if not sanitized_title or sanitized_title.lower().strip() in generic_titles or len(sanitized_title) < 3:
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            folder_name = f"scraped_{url_hash}"
        else:
            folder_name = re.sub(r'\s+', ' ', sanitized_title).strip()

        content_dir = Path("data") / folder_name
        content_dir.mkdir(parents=True, exist_ok=True)

        # Handle multi-chapter books
        if is_book and chapters:
            return _scrape_book(folder_name, content_dir, title, url, chapters)
        else:
            # Single page scrape (original logic)
            return _scrape_single_page(folder_name, content_dir, title, url, data)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return server_error(e)


def _scrape_single_page(folder_name, content_dir, title, url, data):
    """Save a single page/chapter"""
    images_dir = content_dir / "images"
    images_dir.mkdir(exist_ok=True)

    topic_number, section_title = parse_topic_title(title)

    # Merge videos from extension with any found in locally-saved _files/ HTML
    ext_videos = data.get('videos', [])
    saved_videos = extract_youtube_from_saved_files(url)
    # Deduplicate by video ID
    seen_ids = {v.get('src', '').split('/')[-1].split('?')[0] for v in ext_videos}
    for v in saved_videos:
        vid_id = v.get('src', '').split('/')[-1].split('?')[0]
        if vid_id and vid_id not in seen_ids:
            ext_videos.append(v)
            seen_ids.add(vid_id)

    sidebar_data = {}
    for name, text in data.get('sidebarSections', {}).items():
        if 'Vocab' in name:
            sidebar_data[name] = format_vocabulary_text(text)
        else:
            sidebar_data[name] = text

    content_data = {
        'url': url,
        'scraped_at': datetime.now().isoformat(),
        'title': title,
        'topic_number': topic_number,
        'section_title': section_title,
        'main_heading': title,
        'navigation': data.get('navigation', []),
        'main_content': data.get('mainContent', {}),
        'sidebar_sections': sidebar_data,
        'practice_questions': data.get('practiceQuestions', []),
        'videos': ext_videos,
        'images': []
    }

    # Handle images
    LOGO_MARKER = 'PHN2ZyB3aWR0aD0iMzIiIGhlaWdodD0iMzIiIHZpZXdCb3g9IjAgMCAzMiAzMiI'
    images = data.get('images', [])
    for idx, img in enumerate(images):
        src = img.get('src', '')
        original_src = img.get('original_src', src)
        alt_text = img.get('alt', '') or img.get('title', '') or ''

        if LOGO_MARKER in src:
            continue

        if src.startswith('data:'):
            content_data['images'].append({
                'original_src': original_src,
                'local_path': src,
                'alt_text': alt_text
            })
        elif src and not src.startswith('data:'):
            image_path = scraper._download_image(src, url, images_dir, idx)
            if image_path:
                local_path = str(image_path.relative_to(Path("data"))).replace('\\', '/')
            else:
                local_path = original_src
            content_data['images'].append({
                'original_src': original_src,
                'local_path': local_path,
                'alt_text': alt_text
            })

    content_file = content_dir / "content.json"
    with open(content_file, 'w', encoding='utf-8') as f:
        json.dump(content_data, f, indent=2, ensure_ascii=False)

    return jsonify({
        'success': True,
        'folder': folder_name,
        'message': f'Successfully scraped {title}'
    })


def _scrape_book(folder_name, content_dir, book_title, book_url, chapters):
    """Save a multi-chapter book"""
    # Create syllabus structure
    syllabus_items = []

    for chapter_idx, chapter in enumerate(chapters):
        chapter_title = chapter.get('title', f'Chapter {chapter_idx + 1}')
        chapter_content = chapter.get('content', {})

        # Create a folder for each chapter
        chapter_folder = f"{folder_name}_ch{chapter_idx + 1}"
        chapter_dir = Path("data") / chapter_folder
        chapter_dir.mkdir(parents=True, exist_ok=True)
        images_dir = chapter_dir / "images"
        images_dir.mkdir(exist_ok=True)

        # Prepare chapter content
        topic_number, section_title = parse_topic_title(chapter_title)

        # Merge videos from extension with any found in locally-saved _files/ HTML
        chapter_url = chapter.get('url', book_url)
        ch_ext_videos = chapter_content.get('videos', [])
        ch_saved_videos = extract_youtube_from_saved_files(chapter_url)
        ch_seen_ids = {v.get('src', '').split('/')[-1].split('?')[0] for v in ch_ext_videos}
        for v in ch_saved_videos:
            vid_id = v.get('src', '').split('/')[-1].split('?')[0]
            if vid_id and vid_id not in ch_seen_ids:
                ch_ext_videos.append(v)
                ch_seen_ids.add(vid_id)

        ch_sidebar_data = {}
        for name, text in chapter_content.get('sidebarSections', {}).items():
            if 'Vocab' in name:
                ch_sidebar_data[name] = format_vocabulary_text(text)
            else:
                ch_sidebar_data[name] = text

        content_data = {
            'url': chapter_url,
            'scraped_at': datetime.now().isoformat(),
            'title': chapter_title,
            'topic_number': topic_number,
            'section_title': section_title,
            'main_heading': chapter_title,
            'navigation': chapter_content.get('navigation', []),
            'main_content': chapter_content.get('mainContent', {}),
            'sidebar_sections': ch_sidebar_data,
            'practice_questions': chapter_content.get('practiceQuestions', []),
            'videos': ch_ext_videos,
            'images': []
        }

        # Handle images
        LOGO_MARKER = 'PHN2ZyB3aWR0aD0iMzIiIGhlaWdodD0iMzIiIHZpZXdCb3g9IjAgMCAzMiAzMiI'
        images = chapter_content.get('images', [])
        for img_idx, img in enumerate(images):
            src = img.get('src', '')
            original_src = img.get('original_src', src)
            alt_text = img.get('alt', '') or img.get('title', '') or ''

            if LOGO_MARKER in src:
                continue

            if src.startswith('data:'):
                content_data['images'].append({
                    'original_src': original_src,
                    'local_path': src,
                    'alt_text': alt_text
                })
            elif src and not src.startswith('data:'):
                image_path = scraper._download_image(src, chapter.get('url', book_url), images_dir, img_idx)
                if image_path:
                    local_path = str(image_path.relative_to(Path("data"))).replace('\\', '/')
                else:
                    local_path = original_src
                content_data['images'].append({
                    'original_src': original_src,
                    'local_path': local_path,
                    'alt_text': alt_text
                })

        # Save chapter content
        content_file = chapter_dir / "content.json"
        with open(content_file, 'w', encoding='utf-8') as f:
            json.dump(content_data, f, indent=2, ensure_ascii=False)

        # Add to syllabus
        syllabus_items.append({
            'id': str(uuid.uuid4())[:8],
            'title': chapter_title,
            'folder': chapter_folder,
            'children': []
        })

    # Create book-level syllabus
    data_dir = Path("data")
    syllabus_path = data_dir / "syllabus.json"

    syllabus = {}
    if syllabus_path.exists():
        try:
            with open(syllabus_path, 'r', encoding='utf-8') as f:
                syllabus = json.load(f)
        except:
            syllabus = {}

    # Add book section with chapters as children
    if 'items' not in syllabus:
        syllabus['items'] = []

    book_item = {
        'id': str(uuid.uuid4())[:8],
        'title': book_title,
        'children': syllabus_items
    }
    syllabus['items'].append(book_item)

    with open(syllabus_path, 'w', encoding='utf-8') as f:
        json.dump(syllabus, f, indent=2, ensure_ascii=False)

    return jsonify({
        'success': True,
        'folder': folder_name,
        'chapters': len(chapters),
        'message': f'Successfully scraped {book_title} ({len(chapters)} chapters)'
    })

@app.route('/api/books', methods=['GET'])
@login_required
def get_books():
    """Get list of all books"""
    books = scraper.get_books_catalogue()
    return jsonify({'books': books})

@app.route('/api/books/edit', methods=['POST'])
@csrf.exempt
def edit_book():
    """Edit book title and color"""
    try:
        if not current_user.is_authenticated or not current_user.is_admin():
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403

        data = request.get_json()
        book_id = data.get('id')
        new_title = data.get('title', '').strip()
        color_from = data.get('colorFrom')
        color_to = data.get('colorTo')

        if not book_id or not new_title:
            return jsonify({'success': False, 'error': 'Book ID and title required'}), 400

        # Load books catalogue
        books_file = Path('data') / 'books.json'
        if not books_file.exists():
            return jsonify({'success': False, 'error': 'Books file not found'}), 404

        with open(books_file, 'r', encoding='utf-8') as f:
            books_data = json.load(f)

        # Find and update the book
        found = False
        for book in books_data.get('books', []):
            if book.get('id') == book_id:
                book['title'] = new_title
                if color_from:
                    book['color_from'] = color_from
                if color_to:
                    book['color_to'] = color_to
                found = True
                break

        if not found:
            return jsonify({'success': False, 'error': 'Book not found'}), 404

        # Save updated books catalogue
        with open(books_file, 'w', encoding='utf-8') as f:
            json.dump(books_data, f, indent=2, ensure_ascii=False)

        return jsonify({'success': True})
    except Exception as e:
        return server_error(e)

@app.route('/api/books/<book_id>/scrape', methods=['POST'])
@csrf.exempt
@login_required
@admin_required
def scrape_book(book_id):
    """Scrape all pages in a book from the given source site."""
    data = request.get_json(silent=True) or {}
    base_url = (data.get('base_url') or '').strip().rstrip('/')
    if not base_url:
        return jsonify({'success': False, 'error': 'base_url is required'}), 400
    try:
        result = scraper.scrape_book(book_id, base_url)
        return jsonify(result)
    except Exception as e:
        return server_error(e)

@app.route('/api/scrape/stop', methods=['POST'])
@login_required
@admin_required
def stop_scraping():
    """Stop current scraping operation"""
    scraper.stop_scraping()
    return jsonify({'success': True, 'message': 'Scraping stopped'})

@app.route('/api/book/<book_folder>/pages', methods=['GET'])
@login_required
def get_book_pages(book_folder):
    """Get all pages in a book (supports book folders and single page folders)"""
    # If it is a book folder (has book.json)
    pages = scraper.get_book_pages(book_folder)
    if pages:
        # Include the book's own title so pages can show it in headers
        book_title = book_folder
        book_meta = Path('data') / book_folder / 'book.json'
        if book_meta.exists():
            try:
                with open(book_meta, 'r', encoding='utf-8') as f:
                    book_title = json.load(f).get('title', book_folder)
            except (json.JSONDecodeError, OSError):
                pass

        # Include this book's subtree from syllabus.json so the contents page
        # shows the SAME curated hierarchy as the editor's sidebar navigation
        tree = []
        if SYLLABUS_FILE.exists():
            try:
                with open(SYLLABUS_FILE, 'r', encoding='utf-8') as f:
                    syllabus = json.load(f)
                page_ids = {p.get('id') for p in pages}

                def contains_book_page(node):
                    if node.get('folder') in page_ids:
                        return True
                    return any(contains_book_page(c) for c in node.get('children', []))

                matching = [item for item in syllabus.get('items', [])
                            if contains_book_page(item)]
                if len(matching) == 1 and matching[0].get('children') and not matching[0].get('folder'):
                    # Single wrapper node for the whole book — unwrap it
                    tree = matching[0]['children']
                else:
                    tree = matching
            except (json.JSONDecodeError, OSError):
                tree = []

        return jsonify({'pages': pages, 'book_title': book_title, 'tree': tree})
        
    # If it is a single-page folder (has content.json directly)
    content_file = Path('data') / book_folder / 'content.json'
    if content_file.exists():
        try:
            with open(content_file, 'r', encoding='utf-8') as f:
                c = json.load(f)
            return jsonify({'pages': [{
                'id': 'content',
                'title': c.get('title', book_folder),
                'url': c.get('url', '')
            }]})
        except:
            pass
            
    # Check if book_folder contains a slash (e.g. Book_93/5438)
    if '/' in book_folder:
        parts = book_folder.split('/')
        parent_book = parts[0]
        # Get pages of the parent book
        pages = scraper.get_book_pages(parent_book)
        if pages:
            return jsonify({'pages': pages})
            
    return jsonify({'pages': []})

@app.route('/api/book/<book_folder>/page/<page_id>', methods=['GET'])
@login_required
def get_book_page(book_folder, page_id):
    """Get content for a specific page in a book (supports legacy/single-page structures)"""
    content = None
    
    # 1. Standard book page: data/book_folder/page_id/content.json
    content = scraper.get_page_content(book_folder, page_id)
    
    # 2. Single-page folder: data/book_folder/content.json
    if not content and page_id == 'content':
        content_file = Path('data') / book_folder / 'content.json'
        if content_file.exists():
            try:
                with open(content_file, 'r', encoding='utf-8') as f:
                    content = json.load(f)
            except:
                pass
                
    # 3. Path contains slash in book_folder (e.g., folder="Book_93/5438")
    if not content and '/' in book_folder:
        parts = book_folder.split('/')
        content = scraper.get_page_content(parts[0], parts[1])
        
    if content:
        # Migrate to blocks format if needed (same as legacy editor)
        if 'blocks' not in content:
            # Build blocks from raw content
            import re as _re
            SIDEBAR_ONLY = (
                'Vocabulary', 'Practice Questions', 'TOK / Ethics', 'TOK', 'ATL Skills',
                'Sidebar Note', 'Guiding Questions', 'Fun Fact', 'Fun Facts',
                'Theory of Knowledge', 'Study Tip', 'Study Tips',
                'Applied Work', 'Applied', 'Key Point', 'Key Points',
            )
            blocks = []
            if content.get('main_heading'):
                blocks.append({'type': 'heading', 'level': 1, 'text': content['main_heading']})
            for title, text in content.get('main_content', {}).items():
                hm = _re.match(r'^__heading_(\d+)__', title)
                if hm:
                    blocks.append({'type': 'heading', 'level': int(hm.group(1)), 'text': text})
                elif title.startswith('Main Content'):
                    blocks.append({'type': 'text', 'text': text})
                elif any(title.startswith(s) for s in SIDEBAR_ONLY):
                    continue  # handled by sidebar_sections
                else:
                    if not title.startswith('Section'):
                        blocks.append({'type': 'heading', 'level': 3, 'text': title})
                    blocks.append({'type': 'text', 'text': text})
            for name, text in content.get('sidebar_sections', {}).items():
                style = 'study'
                if 'Theory' in name:
                    style = 'theory'
                elif 'Applied' in name:
                    style = 'applied'
                elif 'Vocab' in name:
                    style = 'vocab'
                    text = format_vocabulary_text(text)
                elif 'Fun' in name:
                    style = 'funfact'
                blocks.append({'type': 'sidebox', 'style': style, 'title': name, 'text': text})
            # Videos – must come before images so they appear in the sidebar
            for v in content.get('videos', []):
                src = v.get('src', '')
                if src:
                    blocks.append({
                        'type': 'video',
                        'src': src,
                        'title': v.get('title', '') or 'Video',
                        'side': True
                    })
            for img in content.get('images', []):
                src_val = img['local_path']
                if not (src_val.startswith('data:') or src_val.startswith('http')):
                    src_val = f"/data/{src_val}"
                blocks.append({'type': 'image', 'src': src_val, 'alt': img.get('alt_text', '')})
            content['blocks'] = blocks

        # Vocabulary is canonical in sidebar_sections: render exactly one vocab
        # sidebox built from it, regardless of what a stored blocks array holds.
        # Guarded on sidebar vocab existing, so pages whose vocab lives only in
        # blocks are left untouched.
        vocab_name = next((n for n in content.get('sidebar_sections', {}) if 'Vocab' in n), None)
        if vocab_name and content.get('blocks') is not None:
            content['blocks'] = [b for b in content['blocks']
                                 if not (b.get('type') == 'sidebox' and b.get('style') == 'vocab')]
            vocab_block = {'type': 'sidebox', 'style': 'vocab', 'title': vocab_name,
                           'text': format_vocabulary_text(content['sidebar_sections'][vocab_name])}
            # Sidebar order: Key Concept first, Vocabulary right after it. If
            # there's no Key Concept box, vocab goes ahead of every other
            # sidebar-bound block (other sideboxes, side media) instead.
            blocks_list = content['blocks']
            kc_idx = next((i for i, b in enumerate(blocks_list)
                           if b.get('type') == 'sidebox'
                           and (b.get('title') or '').strip().lower().startswith('key concept')), None)
            if kc_idx is not None:
                insert_at = kc_idx + 1
            else:
                insert_at = next((i for i, b in enumerate(blocks_list)
                                  if b.get('type') == 'sidebox'
                                  or (b.get('type') in ('video', 'image', 'pptx', 'slide') and b.get('side'))
                                  or b.get('type') in ('video', 'image')), len(blocks_list))
            blocks_list.insert(insert_at, vocab_block)

        return jsonify(content)
    return jsonify({'error': 'Page not found'}), 404

@app.route('/api/content', methods=['GET'])
@login_required
@admin_required
def get_all_content():
    """Get all scraped content (legacy)"""
    items = scraper.get_all_scraped_content()
    return jsonify({'items': items})

@app.route('/api/folders', methods=['GET'])
@login_required
@admin_required
def get_folders():
    """Return all scraped folder names for linking in syllabus (supports book subfolders)"""
    data_dir = Path('data')
    folders = []
    if data_dir.exists():
        for d in sorted(data_dir.iterdir()):
            if d.is_dir():
                if (d / 'content.json').exists():
                    folders.append(d.name)
                # Check for book directories containing subfolders with content.json
                for sub in sorted(d.iterdir()):
                    if sub.is_dir() and (sub / 'content.json').exists():
                        folders.append(f"{d.name}/{sub.name}")
    return jsonify({'folders': folders})

SYLLABUS_FILE = Path('data') / 'syllabus.json'

@app.route('/api/syllabus', methods=['GET'])
@login_required
def get_syllabus():
    """Return the syllabus tree structure"""
    if SYLLABUS_FILE.exists():
        with open(SYLLABUS_FILE, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))

    # Auto-generate structure from existing folders and book.json files
    data_dir = Path('data')
    items = []
    if data_dir.exists():
        for d in sorted(data_dir.iterdir()):
            if not d.is_dir():
                continue

            # Check if this is a multi-page book (has book.json)
            book_json = d / 'book.json'
            if book_json.exists():
                try:
                    with open(book_json, 'r', encoding='utf-8') as f:
                        book_data = json.load(f)
                        # Create a section for each book with its pages as children
                        book_item = {
                            'id': book_data.get('id', d.name),
                            'title': book_data.get('title', d.name),
                            'children': book_data.get('pages', [])
                        }
                        items.append(book_item)
                except:
                    pass
            # Single-page folders (regular content.json)
            elif (d / 'content.json').exists():
                import uuid
                items.append({
                    'id': str(uuid.uuid4())[:8],
                    'title': d.name,
                    'folder': d.name,
                    'children': []
                })

    tree = {'items': items}
    return jsonify(tree)

@app.route('/api/syllabus', methods=['POST'])
@csrf.exempt
def save_syllabus():
    """Save the syllabus tree structure"""
    try:
        if not current_user.is_authenticated:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        if not current_user.is_admin():
            return jsonify({'success': False, 'error': 'Forbidden: admin required'}), 403

        data = request.get_json()
        SYLLABUS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SYLLABUS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return jsonify({'success': True})
    except Exception as e:
        return server_error(e)


@app.route('/api/content/<path:folder_name>', methods=['GET'])
@login_required
@admin_required
def get_content_details(folder_name):
    """Get detailed content from a folder and migrate schema if needed"""
    content = scraper.get_content_details(folder_name)
    if content:
        # Migrate dynamically to blocks schema if it is absent
        if 'blocks' not in content:
            blocks = []
            
            # 1. Add main heading
            if content.get('main_heading'):
                blocks.append({ 'type': 'heading', 'level': 1, 'text': content['main_heading'] })
            
            # 2. Add main content sections — understand new __heading_N__ keys from DOM walker
            import re
            # Any main_content key whose label matches one of these is a sidebar section
            # and will be rendered by the sidebar_sections loop below — skip it here.
            SIDEBAR_ONLY = (
                'Vocabulary', 'Practice Questions', 'TOK / Ethics', 'TOK', 'ATL Skills',
                'Sidebar Note', 'Guiding Questions', 'Fun Fact', 'Fun Facts',
                'Theory of Knowledge', 'Study Tip', 'Study Tips',
                'Applied Work', 'Applied', 'Key Point', 'Key Points',
            )
            for title, text in content.get('main_content', {}).items():
                # Heading block marker from new single-pass extractor
                heading_match = re.match(r'^__heading_(\d+)__', title)
                if heading_match:
                    level = int(heading_match.group(1))
                    blocks.append({ 'type': 'heading', 'level': level, 'text': text })
                elif title.startswith('Main Content'):
                    # Plain body paragraph
                    blocks.append({ 'type': 'text', 'text': text })
                elif any(title.startswith(s) for s in SIDEBAR_ONLY):
                    # Sidebar-only content — skip; sidebar_sections loop handles it
                    continue
                else:
                    # Legacy heading→text format (old scraper stored section names as keys)
                    if not title.startswith('Section'):
                        blocks.append({ 'type': 'heading', 'level': 3, 'text': title })
                    blocks.append({ 'type': 'text', 'text': text })
                
            # 2.5. Add structured practice questions as reveal-answer blocks
            practice = content.get('practice_questions', [])
            if practice:
                blocks.append({ 'type': 'heading', 'level': 3, 'text': 'Practice Questions' })
                for q in practice:
                    q_text = q.get('question', '')
                    if q.get('marks'):
                        q_text = f"[{q['marks']}]  {q_text}"
                    blocks.append({ 'type': 'question', 'text': q_text, 'answer': q.get('answer', '') })

            # 2.6. Scraped YouTube videos → embedded players in the side panel
            for v in content.get('videos', []):
                blocks.append({
                    'type': 'video',
                    'src': v.get('src', ''),
                    'title': v.get('title', '') or 'Video',
                    'side': True
                })

            # 3. Add sidebar sections
            for name, text in content.get('sidebar_sections', {}).items():
                style = 'study'
                if 'Theory' in name:
                    style = 'theory'
                elif 'Applied' in name or 'Activity' in name:
                    style = 'applied'
                elif 'Vocab' in name:
                    style = 'vocab'
                    text = format_vocabulary_text(text)
                elif 'Fun' in name:
                    style = 'funfact'
                blocks.append({ 'type': 'sidebox', 'style': style, 'title': name, 'text': text })
                
            # 4. Add images
            for img in content.get('images', []):
                src_val = img['local_path']
                # Don't prefix data URIs or absolute URLs with /data/
                if src_val.startswith('data:') or src_val.startswith('http://') or src_val.startswith('https://') or src_val.startswith('/data/'):
                    pass  # use as-is
                else:
                    src_val = f"/data/{src_val}"
                blocks.append({ 'type': 'image', 'src': src_val, 'alt': img.get('alt_text', '') })
                
            content['blocks'] = merge_consecutive_headings(blocks)
            
            # Save the migrated structure immediately (page may live nested
            # inside a book folder, so resolve the real path)
            content_file = scraper.resolve_content_path(folder_name)
            if content_file:
                with open(content_file, 'w', encoding='utf-8') as f:
                    json.dump(content, f, indent=2, ensure_ascii=False)
        else:
            content['blocks'] = merge_consecutive_headings(content['blocks'])
                
        return jsonify(content)
    return jsonify({'error': 'Content not found'}), 404

@app.route('/api/content/<path:folder_name>/save', methods=['POST'])
@csrf.exempt
def save_content_details(folder_name):
    """Save modified content details back to content.json"""
    try:
        if not current_user.is_authenticated or not current_user.is_admin():
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403

        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
            
        # Resolve the real path — the page may live nested inside a book folder
        content_file = scraper.resolve_content_path(folder_name)

        if not content_file:
            return jsonify({'success': False, 'error': 'Content file not found'}), 404

        # Vocabulary stays canonical in sidebar_sections and is never persisted as
        # a blocks entry. If the (re-injected) vocab sidebox comes back in the
        # payload — possibly with admin edits — fold its text into sidebar_sections
        # and drop it from blocks before writing.
        if isinstance(data.get('blocks'), list):
            vocab_blocks = [b for b in data['blocks']
                            if b.get('type') == 'sidebox' and b.get('style') == 'vocab']
            if vocab_blocks:
                sections = data.setdefault('sidebar_sections', {})
                key = next((n for n in sections if 'Vocab' in n), None) \
                    or vocab_blocks[-1].get('title') or 'Vocabulary'
                sections[key] = vocab_blocks[-1].get('text', '')
                data['blocks'] = [b for b in data['blocks']
                                  if not (b.get('type') == 'sidebox' and b.get('style') == 'vocab')]

        with open(content_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        return jsonify({'success': True, 'message': 'Content saved successfully'})
    except Exception as e:
        return server_error(e)

@app.route('/api/book-pages/<path:folder_name>', methods=['GET'])
@login_required
@admin_required
def list_book_pages(folder_name):
    """Get list of pages in a book folder"""
    try:
        data_dir = Path('data')
        folder_path = data_dir / folder_name

        # If path doesn't exist, return empty
        if not folder_path.exists() or not folder_path.is_dir():
            return jsonify({'pages': []}), 200

        # Look for subfolders with content.json files
        pages = []
        for item in sorted(folder_path.iterdir()):
            if item.is_dir():
                content_file = item / 'content.json'
                if content_file.exists():
                    with open(content_file, 'r', encoding='utf-8') as f:
                        content = json.load(f)
                        pages.append({
                            'folder': f"{folder_name}/{item.name}",
                            'title': content.get('title', item.name)
                        })

        return jsonify({'pages': pages})
    except Exception as e:
        app.logger.error('Could not list pages', exc_info=e)
        return jsonify({'pages': [], 'error': 'Could not load pages.'}), 200

@app.route('/api/search', methods=['POST'])
@login_required
@admin_required
def search():
    """Search content"""
    data = request.get_json()
    query = data.get('query', '').strip()

    if not query:
        return jsonify({'error': 'Search query is required'}), 400

    results = scraper.search_content(query)
    return jsonify({'results': results, 'count': len(results)})

@app.route('/api/pages', methods=['POST'])
@csrf.exempt
def create_page():
    """Spec 19: Create a new blank page"""
    try:
        if not current_user.is_authenticated or not current_user.is_admin():
            return jsonify({'error': 'Unauthorized'}), 403

        data = request.get_json()
        title = data.get('title', '').strip()
        parent_id = data.get('parent_id')

        if not title:
            return jsonify({'error': 'Title is required'}), 400

        # Sanitize title into folder name
        folder = re.sub(r'[^a-zA-Z0-9_\-]', '_', title).lower()
        folder = re.sub(r'_+', '_', folder).strip('_')

        # Handle collisions
        base_folder = folder
        counter = 2
        data_dir = Path('data')
        while (data_dir / folder).exists():
            folder = f"{base_folder}_{counter}"
            counter += 1

        # Create folder and starter content
        folder_path = data_dir / folder
        folder_path.mkdir(parents=True, exist_ok=True)

        # Verify folder was created
        if not folder_path.exists():
            return jsonify({'success': False, 'error': 'Failed to create folder'}), 500

        starter_content = {
            'url': '',
            'scraped_at': datetime.now().isoformat(),
            'title': title,
            'main_heading': title,
            'blocks': [
                {'type': 'heading', 'level': 1, 'text': title},
                {'type': 'text', 'text': ''}
            ],
            'images': [],
            'main_content': {},
            'sidebar_sections': {}
        }

        with open(folder_path / 'content.json', 'w', encoding='utf-8') as f:
            json.dump(starter_content, f, indent=2, ensure_ascii=False)

        # Verify content.json was created
        if not (folder_path / 'content.json').exists():
            return jsonify({'success': False, 'error': 'Failed to create content file'}), 500

        # Insert into syllabus if it exists
        syllabus_path = data_dir / 'syllabus.json'
        if syllabus_path.exists():
            with open(syllabus_path, 'r', encoding='utf-8') as f:
                syllabus = json.load(f)

            new_item = {
                'id': str(uuid.uuid4())[:8],
                'title': title,
                'folder': folder,
                'children': []
            }

            if parent_id:
                # Find parent and add as child
                def add_to_parent(items, pid):
                    for item in items:
                        if item.get('id') == pid:
                            if 'children' not in item:
                                item['children'] = []
                            item['children'].append(new_item)
                            return True
                        if item.get('children'):
                            if add_to_parent(item['children'], pid):
                                return True
                    return False
                add_to_parent(syllabus.get('items', []), parent_id)
            else:
                # Add to top level
                if 'items' not in syllabus:
                    syllabus['items'] = []
                syllabus['items'].append(new_item)

            with open(syllabus_path, 'w', encoding='utf-8') as f:
                json.dump(syllabus, f, indent=2, ensure_ascii=False)

        return jsonify({'success': True, 'folder': folder})
    except Exception as e:
        return server_error(e)

@app.route('/api/sections', methods=['POST'])
@csrf.exempt
def create_section():
    """Spec 19: Create a new section (folder-less group)"""
    try:
        if not current_user.is_authenticated or not current_user.is_admin():
            return jsonify({'error': 'Unauthorized'}), 403

        data = request.get_json()
        title = data.get('title', '').strip()
        parent_id = data.get('parent_id')

        if not title:
            return jsonify({'error': 'Title is required'}), 400

        data_dir = Path('data')
        syllabus_path = data_dir / 'syllabus.json'

        if not syllabus_path.exists():
            return jsonify({'error': 'Syllabus not found'}), 400

        with open(syllabus_path, 'r', encoding='utf-8') as f:
            syllabus = json.load(f)

        new_item = {
            'id': str(uuid.uuid4())[:8],
            'title': title,
            'children': []
        }

        if parent_id:
            # Find parent and add as child
            def add_to_parent(items, pid):
                for item in items:
                    if item.get('id') == pid:
                        if 'children' not in item:
                            item['children'] = []
                        item['children'].append(new_item)
                        return True
                    if item.get('children'):
                        if add_to_parent(item['children'], pid):
                            return True
                return False
            add_to_parent(syllabus.get('items', []), parent_id)
        else:
            # Add to top level
            if 'items' not in syllabus:
                syllabus['items'] = []
            syllabus['items'].append(new_item)

        with open(syllabus_path, 'w', encoding='utf-8') as f:
            json.dump(syllabus, f, indent=2, ensure_ascii=False)

        return jsonify({'success': True, 'id': new_item['id']})
    except Exception as e:
        return server_error(e)

@app.route('/api/pages/<path:folder>/duplicate', methods=['POST'])
@login_required
@admin_required
def duplicate_page(folder):
    """Deep-copy a page's content folder and return the new folder + title"""
    try:
        if '..' in folder:
            return jsonify({'success': False, 'error': 'Invalid folder'}), 400

        data_dir = Path('data')
        src = data_dir / folder
        if not src.exists() or not src.is_dir() or not (src / 'content.json').exists():
            return jsonify({'success': False, 'error': 'Page not found'}), 404

        # Pick a collision-free sibling name
        base = src.name + '_copy'
        new_name = base
        counter = 2
        while (src.parent / new_name).exists():
            new_name = f"{base}_{counter}"
            counter += 1
        dst = src.parent / new_name
        shutil.copytree(src, dst)

        # Retitle the copy
        content_file = dst / 'content.json'
        with open(content_file, 'r', encoding='utf-8') as f:
            content = json.load(f)
        new_title = (content.get('title') or src.name) + ' (Copy)'
        content['title'] = new_title
        content['main_heading'] = new_title
        with open(content_file, 'w', encoding='utf-8') as f:
            json.dump(content, f, indent=2, ensure_ascii=False)

        rel_folder = str(dst.relative_to(data_dir)).replace('\\', '/')
        return jsonify({'success': True, 'folder': rel_folder, 'title': new_title})
    except Exception as e:
        return server_error(e)

@app.route('/api/pages/<folder>/rename', methods=['POST'])
@login_required
@admin_required
def rename_page(folder):
    """Spec 19: Rename a page"""
    # Validate folder name
    if '..' in folder or '/' in folder or '\\' in folder:
        return jsonify({'error': 'Invalid folder'}), 400

    data = request.get_json()
    new_title = data.get('title', '').strip()

    if not new_title:
        return jsonify({'error': 'Title is required'}), 400

    data_dir = Path('data')
    folder_path = data_dir / folder
    content_path = folder_path / 'content.json'

    if not content_path.exists():
        return jsonify({'error': 'Page not found'}), 404

    # Update content.json
    with open(content_path, 'r') as f:
        content = json.load(f)
    content['title'] = new_title
    content['main_heading'] = new_title
    with open(content_path, 'w') as f:
        json.dump(content, f, indent=2)

    # Update syllabus.json
    syllabus_path = data_dir / 'syllabus.json'
    if syllabus_path.exists():
        with open(syllabus_path, 'r') as f:
            syllabus = json.load(f)

        def update_title(items):
            for item in items:
                if item.get('folder') == folder:
                    item['title'] = new_title
                    return True
                if item.get('children'):
                    if update_title(item['children']):
                        return True
            return False

        update_title(syllabus.get('items', []))
        with open(syllabus_path, 'w') as f:
            json.dump(syllabus, f, indent=2)

    return jsonify({'success': True})

@app.route('/api/pages/<path:folder>', methods=['DELETE'])
@csrf.exempt
def delete_page(folder):
    """Spec 19: Delete a page"""
    try:
        # Check authentication manually
        if not current_user.is_authenticated:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401

        # Check admin status manually
        if not current_user.is_admin():
            return jsonify({'success': False, 'error': 'Forbidden: admin required'}), 403

        print(f'[DEBUG] Delete request for folder: {folder}')

        # Validate folder name
        if '..' in folder:
            return jsonify({'success': False, 'error': 'Invalid folder'}), 400

        data_dir = Path('data')
        folder_path = data_dir / folder

        print(f'[DEBUG] Folder path: {folder_path}')
        print(f'[DEBUG] Folder exists: {folder_path.exists()}')

        # Check if folder exists and is inside data/
        if not folder_path.exists() or not folder_path.is_dir():
            return jsonify({'success': False, 'error': 'Page not found'}), 404

        # Delete the folder
        print(f'[DEBUG] Deleting folder...')
        shutil.rmtree(folder_path)
        print(f'[DEBUG] Folder deleted successfully')

        # Remove from syllabus
        syllabus_path = data_dir / 'syllabus.json'
        if syllabus_path.exists():
            try:
                with open(syllabus_path, 'r', encoding='utf-8') as f:
                    syllabus = json.load(f)
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                print(f'[DEBUG] Error reading syllabus: {e}')
                app.logger.error('Failed to read syllabus', exc_info=e)
                return jsonify({'success': False, 'error': 'Failed to read syllabus.'}), 500

            def remove_item(items):
                for i, item in enumerate(items):
                    if item.get('folder') == folder:
                        # Promote children to current level
                        children = item.get('children', [])
                        items[i:i+1] = children
                        return True
                    if item.get('children'):
                        if remove_item(item['children']):
                            return True
                return False

            remove_item(syllabus.get('items', []))
            try:
                with open(syllabus_path, 'w', encoding='utf-8') as f:
                    json.dump(syllabus, f, indent=2, ensure_ascii=False)
                print(f'[DEBUG] Syllabus updated successfully')
            except (json.JSONEncodeError, OSError, UnicodeEncodeError) as e:
                print(f'[DEBUG] Error writing syllabus: {e}')
                app.logger.error('Failed to write syllabus', exc_info=e)
                return jsonify({'success': False, 'error': 'Failed to write syllabus.'}), 500

        print(f'[DEBUG] Delete completed successfully')
        return jsonify({'success': True})
    except Exception as e:
        print(f'[DEBUG] Unexpected error: {e}')
        import traceback
        traceback.print_exc()
        return server_error(e)

@app.route('/api/book/<book_folder>/cover', methods=['POST'])
@login_required
@admin_required
def upload_book_cover(book_folder):
    """Upload a cover image for a book"""
    try:
        if 'image' not in request.files:
            return jsonify({'success': False, 'error': 'No image file uploaded'}), 400
            
        file = request.files['image']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No image file selected'}), 400
            
        # Determine extension
        ext = file.filename.split('.')[-1].lower()
        if ext not in ['png', 'jpg', 'jpeg', 'webp', 'svg']:
            return jsonify({'success': False, 'error': 'Invalid image format'}), 400
            
        book_dir = Path("data") / book_folder
        if not book_dir.exists():
            return jsonify({'success': False, 'error': 'Book directory not found'}), 404
            
        cover_path = book_dir / f"cover.{ext}"
        file.save(cover_path)
        
        # Update book.json
        book_meta_file = book_dir / "book.json"
        if book_meta_file.exists():
            with open(book_meta_file, 'r', encoding='utf-8') as f:
                book_meta = json.load(f)
        else:
            book_meta = {
                'id': book_folder.split('_')[-1],
                'title': book_folder.replace('_', ' '),
                'url': '',
                'created_at': datetime.now().isoformat(),
                'pages': []
            }
            
        book_meta['cover_image'] = f"{book_folder}/cover.{ext}"
        with open(book_meta_file, 'w', encoding='utf-8') as f:
            json.dump(book_meta, f, indent=2, ensure_ascii=False)
            
        # Update catalog
        scraper._update_books_catalogue()
        
        return jsonify({'success': True, 'cover_image': book_meta['cover_image']})
    except Exception as e:
        return server_error(e)

@app.route('/api/book/<book_folder>/upload-image', methods=['POST'])
@csrf.exempt
def upload_page_image(book_folder):
    """Upload an image for use inside page content (inserted/pasted in edit mode)."""
    try:
        if not current_user.is_authenticated or not current_user.is_admin():
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403

        if 'image' not in request.files:
            return jsonify({'success': False, 'error': 'No image file uploaded'}), 400

        file = request.files['image']
        ext = (file.filename or '').rsplit('.', 1)[-1].lower()
        if ext not in ['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg']:
            # Pasted blobs arrive named "image.png" etc.; fall back to mimetype.
            mime_ext = (file.mimetype or '').split('/')[-1].lower()
            ext = 'jpg' if mime_ext == 'jpeg' else mime_ext
            if ext not in ['png', 'jpg', 'gif', 'webp', 'svg']:
                return jsonify({'success': False, 'error': 'Invalid image format'}), 400

        book_dir = Path("data") / book_folder
        if not book_dir.exists() or not book_dir.is_dir() or '..' in book_folder:
            return jsonify({'success': False, 'error': 'Book directory not found'}), 404

        images_dir = book_dir / 'images'
        images_dir.mkdir(exist_ok=True)
        filename = f"upload_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.{ext}"
        file.save(images_dir / filename)

        return jsonify({'success': True, 'src': f"/data/{book_folder}/images/{filename}"})
    except Exception as e:
        return server_error(e)

@app.route('/api/content-browser', methods=['GET', 'DELETE'])
@csrf.exempt
def content_browser():
    """Browse and manage content files"""
    try:
        if not current_user.is_authenticated or not current_user.is_admin():
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403

        path = request.args.get('path', '').strip('/')
        data_dir = Path('data')

        if path:
            target_dir = data_dir / path
        else:
            target_dir = data_dir

        # Security check
        if not target_dir.resolve().is_relative_to(data_dir.resolve()):
            return jsonify({'success': False, 'error': 'Invalid path'}), 400

        if request.method == 'DELETE':
            if not target_dir.exists():
                return jsonify({'success': False, 'error': 'Path not found'}), 404

            # Delete folder or file
            if target_dir.is_dir():
                shutil.rmtree(target_dir)
            else:
                target_dir.unlink()

            return jsonify({'success': True, 'message': 'Deleted successfully'})

        # GET - list contents
        if not target_dir.exists():
            return jsonify({'success': False, 'error': 'Path not found'}), 404

        items = []
        for entry in sorted(target_dir.iterdir()):
            if entry.is_dir():
                # Count items in folder
                try:
                    item_count = len(list(entry.iterdir()))
                except:
                    item_count = 0

                items.append({
                    'name': entry.name,
                    'type': 'folder',
                    'itemCount': item_count
                })
            elif entry.is_file():
                # Get file size
                try:
                    size = entry.stat().st_size
                    if size < 1024:
                        size_str = f"{size} B"
                    elif size < 1024 * 1024:
                        size_str = f"{size / 1024:.1f} KB"
                    else:
                        size_str = f"{size / (1024 * 1024):.1f} MB"
                except:
                    size_str = "Unknown"

                items.append({
                    'name': entry.name,
                    'type': 'file',
                    'size': size_str
                })

        return jsonify({'success': True, 'items': items})

    except Exception as e:
        return server_error(e)

@app.route('/api/move-folder', methods=['POST'])
@csrf.exempt
def move_folder():
    """Move a folder into another folder"""
    try:
        if not current_user.is_authenticated or not current_user.is_admin():
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403

        data = request.get_json()
        source_path = data.get('source', '').strip('/')
        target_path = data.get('target', '').strip('/')

        if not source_path or not target_path:
            return jsonify({'success': False, 'error': 'Source and target paths required'}), 400

        data_dir = Path('data')
        source_dir = data_dir / source_path
        target_dir = data_dir / target_path

        # Security checks
        if not source_dir.resolve().is_relative_to(data_dir.resolve()) or not target_dir.resolve().is_relative_to(data_dir.resolve()):
            return jsonify({'success': False, 'error': 'Invalid paths'}), 400

        if not source_dir.exists() or not source_dir.is_dir():
            return jsonify({'success': False, 'error': 'Source folder not found'}), 404

        if not target_dir.exists() or not target_dir.is_dir():
            return jsonify({'success': False, 'error': 'Target folder not found'}), 404

        # Can't move into itself or its own child
        if source_dir == target_dir or str(target_dir).startswith(str(source_dir) + '/'):
            return jsonify({'success': False, 'error': 'Cannot move a folder into itself'}), 400

        # Move the folder
        folder_name = source_dir.name
        new_location = target_dir / folder_name

        # Handle name collision
        if new_location.exists():
            counter = 2
            base_name = folder_name
            while (target_dir / f"{base_name}_{counter}").exists():
                counter += 1
            folder_name = f"{base_name}_{counter}"
            new_location = target_dir / folder_name

        shutil.move(str(source_dir), str(new_location))

        return jsonify({'success': True, 'message': f'Moved to {folder_name}'})

    except Exception as e:
        return server_error(e)

@app.route('/data/<path:filepath>')
@login_required
def serve_file(filepath):
    """Serve scraped content files and images"""
    if not is_servable(filepath, 'data', Path('data/app.db').resolve()):
        abort(404)
    return send_from_directory('data', filepath)

def _log_daily_reading(student_id, seconds):
    """Add seconds to today's row in the per-day reading log (caller commits)."""
    if not seconds or seconds <= 0:
        return
    from models import ReadingDailyLog
    today = datetime.now().date()
    row = ReadingDailyLog.query.filter_by(student_id=student_id, date=today).first()
    if not row:
        row = ReadingDailyLog(student_id=student_id, date=today, seconds=0)
        db.session.add(row)
    row.seconds = (row.seconds or 0) + int(seconds)


@app.route('/api/activity/ping', methods=['POST'])
@login_required
@csrf.exempt
def activity_ping():
    """Beacon endpoint for time-on-page tracking (keepalive/unload requests can't carry a CSRF token)"""
    if current_user.is_admin():
        return jsonify({'ok': True})

    from models import ReadingActivity

    data = request.get_json(force=True, silent=True) or {}
    book_folder = data.get('book_folder')
    page_id = data.get('page_id')
    seconds = data.get('seconds', 0)
    completed = data.get('completed')

    if not book_folder or not page_id or not isinstance(seconds, (int, float)) or seconds < 0:
        return jsonify({'error': 'invalid payload'}), 400

    seconds = min(int(seconds), 120)

    activity = ReadingActivity.query.filter_by(
        student_id=current_user.id, book_folder=book_folder, page_id=page_id
    ).first()
    now = datetime.now()
    if not activity:
        activity = ReadingActivity(
            student_id=current_user.id, book_folder=book_folder, page_id=page_id,
            first_opened_at=now, last_opened_at=now,
        )
        db.session.add(activity)

    activity.last_opened_at = now
    activity.total_seconds = (activity.total_seconds or 0) + seconds
    _log_daily_reading(current_user.id, seconds)
    if completed is True and not activity.completed:
        activity.completed = True
        activity.completed_at = now
    elif completed is False:
        activity.completed = False
        activity.completed_at = None

    db.session.commit()
    return jsonify({'ok': True, 'total_seconds': activity.total_seconds, 'completed': activity.completed})

@app.route('/api/reading-activity', methods=['GET', 'POST'])
@login_required
@csrf.exempt
def read_write_activity():
    """Get or save reading activity from the reading timer"""
    if current_user.is_admin():
        return jsonify({'ok': True})

    from models import ReadingActivity

    # GET: Fetch reading activity for a page
    if request.method == 'GET':
        book_folder = request.args.get('book_folder')
        page_id = request.args.get('page_id')

        if not book_folder or not page_id:
            return jsonify({'error': 'book_folder and page_id required'}), 400

        activity = ReadingActivity.query.filter_by(
            student_id=current_user.id, book_folder=book_folder, page_id=page_id
        ).first()

        if activity:
            return jsonify({
                'total_seconds': activity.total_seconds or 0,
                'completed': activity.completed,
                'first_opened_at': activity.first_opened_at.isoformat() if activity.first_opened_at else None,
                'last_opened_at': activity.last_opened_at.isoformat() if activity.last_opened_at else None,
            })
        else:
            return jsonify({'total_seconds': 0, 'completed': False})

    # POST: Save reading activity for a page
    data = request.get_json(force=True, silent=True) or {}
    book_folder = data.get('book_folder')
    page_id = data.get('page_id')
    elapsed_seconds = data.get('elapsed_seconds', 0)

    if not book_folder or not page_id or not isinstance(elapsed_seconds, (int, float)) or elapsed_seconds < 0:
        return jsonify({'error': 'invalid payload'}), 400

    elapsed_seconds = int(elapsed_seconds)
    if elapsed_seconds == 0:
        return jsonify({'ok': True})

    activity = ReadingActivity.query.filter_by(
        student_id=current_user.id, book_folder=book_folder, page_id=page_id
    ).first()

    now = datetime.now()
    if not activity:
        activity = ReadingActivity(
            student_id=current_user.id, book_folder=book_folder, page_id=page_id,
            first_opened_at=now, last_opened_at=now,
            total_seconds=elapsed_seconds
        )
        db.session.add(activity)
    else:
        activity.total_seconds = (activity.total_seconds or 0) + elapsed_seconds
        activity.last_opened_at = now

    _log_daily_reading(current_user.id, elapsed_seconds)
    db.session.commit()
    return jsonify({'ok': True, 'total_seconds': activity.total_seconds})

@app.route('/api/reading-stats', methods=['GET'])
@login_required
def get_reading_stats():
    """Get reading statistics for the current student"""
    if current_user.is_admin():
        return jsonify({'error': 'not available for admins'}), 403

    from models import ReadingActivity, ClassEnrollment, ReadingAssignment

    # Get all activities for this student
    activities = ReadingActivity.query.filter_by(student_id=current_user.id).all()

    # Organize by assignment
    stats = {
        'total_seconds': 0,
        'total_pages': len(activities),
        'completed_pages': sum(1 for a in activities if a.completed),
        'activities': [],
        'books': [],
    }

    for activity in activities:
        # Get assignment info
        assignment = ReadingAssignment.query.filter_by(
            book_folder=activity.book_folder,
            page_id=activity.page_id
        ).first()

        total_minutes = round((activity.total_seconds or 0) / 60, 1)
        stats['total_seconds'] += activity.total_seconds or 0

        activity_data = {
            'title': assignment.title if assignment else f"{activity.book_folder}/{activity.page_id}",
            'book_folder': activity.book_folder,
            'page_id': activity.page_id,
            'total_minutes': total_minutes,
            'total_seconds': activity.total_seconds or 0,
            'completed': activity.completed,
            'first_opened_at': activity.first_opened_at.isoformat() if activity.first_opened_at else None,
            'last_opened_at': activity.last_opened_at.isoformat() if activity.last_opened_at else None,
        }
        stats['activities'].append(activity_data)

    # Sort by most recent first
    stats['activities'].sort(key=lambda x: x['last_opened_at'] or '', reverse=True)

    # Per-book progress: group this student's activity by book and look up the
    # book's title and page count from data/<folder>/book.json
    by_book = {}
    for activity in activities:
        b = by_book.setdefault(activity.book_folder, {
            'folder': activity.book_folder,
            'title': activity.book_folder,
            'total_pages': 0,
            'opened_pages': 0,
            'completed_pages': 0,
            'total_seconds': 0,
        })
        b['opened_pages'] += 1
        if activity.completed:
            b['completed_pages'] += 1
        b['total_seconds'] += activity.total_seconds or 0

    for folder, b in by_book.items():
        book_json_path = Path('data') / folder / 'book.json'
        try:
            if book_json_path.exists():
                with open(book_json_path, 'r', encoding='utf-8') as f:
                    book_data = json.load(f)
                b['title'] = book_data.get('title') or folder
                b['total_pages'] = len(book_data.get('pages', []))
        except Exception:
            pass
        # If the book file is missing, fall back to pages the student has opened
        if not b['total_pages']:
            b['total_pages'] = b['opened_pages']

    stats['books'] = sorted(by_book.values(), key=lambda b: b['total_seconds'], reverse=True)

    # Accurate per-day seconds for the last 7 days from the daily log.
    # Students with no log rows yet (history predating the log) fall back to
    # approximating by each page's last-opened date.
    from models import ReadingDailyLog
    today = datetime.now().date()
    week_dates = [today - timedelta(days=i) for i in range(6, -1, -1)]
    log_rows = ReadingDailyLog.query.filter(
        ReadingDailyLog.student_id == current_user.id,
        ReadingDailyLog.date >= week_dates[0],
    ).all()
    if ReadingDailyLog.query.filter_by(student_id=current_user.id).first():
        log_by_date = {r.date: r.seconds or 0 for r in log_rows}
        stats['daily'] = {d.isoformat(): log_by_date.get(d, 0) for d in week_dates}
    else:
        daily = {d.isoformat(): 0 for d in week_dates}
        for activity in activities:
            if activity.last_opened_at:
                key = activity.last_opened_at.date().isoformat()
                if key in daily:
                    daily[key] += activity.total_seconds or 0
        stats['daily'] = daily

    return jsonify(stats)

@app.route('/api/confidence', methods=['GET', 'POST'])
@login_required
@csrf.exempt
def confidence_handler():
    """Handle student confidence ratings (GET to retrieve, POST to save)"""
    from models import StudentConfidence

    if request.method == 'POST':
        if current_user.is_admin():
            return jsonify({'ok': True})

        data = request.get_json(force=True, silent=True) or {}
        book_folder = data.get('book_folder')
        page_id = data.get('page_id')
        confidence_level = data.get('confidence_level')

        if not book_folder or not page_id or confidence_level is None:
            return jsonify({'error': 'book_folder, page_id, and confidence_level required'}), 400

        # Validate confidence level is 1-5
        try:
            confidence_level = int(confidence_level)
            if confidence_level < 1 or confidence_level > 5:
                return jsonify({'error': 'confidence_level must be between 1 and 5'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'confidence_level must be an integer'}), 400

        confidence = StudentConfidence.query.filter_by(
            student_id=current_user.id, book_folder=book_folder, page_id=page_id
        ).first()

        if confidence:
            confidence.confidence_level = confidence_level
            confidence.updated_at = datetime.now()
        else:
            confidence = StudentConfidence(
                student_id=current_user.id,
                book_folder=book_folder,
                page_id=page_id,
                confidence_level=confidence_level,
            )
            db.session.add(confidence)

        db.session.commit()
        return jsonify({'ok': True, 'confidence_level': confidence_level})

    # GET method
    if current_user.is_admin():
        return jsonify({'confidence': {}})

    book_folder = request.args.get('book_folder')
    page_id = request.args.get('page_id')

    if book_folder and page_id:
        # Get confidence for a specific page
        confidence = StudentConfidence.query.filter_by(
            student_id=current_user.id, book_folder=book_folder, page_id=page_id
        ).first()
        return jsonify({'confidence_level': confidence.confidence_level if confidence else None})

    # Get all confidence ratings for current student
    all_confidence = StudentConfidence.query.filter_by(student_id=current_user.id).all()
    confidence_dict = {
        f"{c.book_folder}/{c.page_id}": c.confidence_level for c in all_confidence
    }

    # Calculate distribution (count at each level 1-5)
    distribution = {i: 0 for i in range(1, 6)}
    for conf in all_confidence:
        distribution[conf.confidence_level] = distribution.get(conf.confidence_level, 0) + 1

    return jsonify({
        'confidence': confidence_dict,
        'distribution': distribution
    })

@app.route('/admin/reading-analytics')
@login_required
@admin_required
def admin_reading_analytics():
    """Admin reading analytics dashboard"""
    return render_template('admin_reading_analytics.html')

@app.route('/admin/analytics/student/<int:student_id>')
@login_required
@admin_required
def admin_student_analytics(student_id):
    """Admin detailed student analytics page"""
    from models import User
    student = User.query.get_or_404(student_id)
    return render_template('admin_student_analytics.html', student=student)

@app.route('/admin/student/<int:student_id>/resources')
@login_required
@admin_required
def admin_view_student_resources(student_id):
    """Admin view of a specific student's resources with analytics"""
    from models import User, ClassEnrollment, ReadingAssignment, ReadingActivity

    student = User.query.get_or_404(student_id)

    # Get student's classes and assignments
    class_ids = [e.class_id for e in ClassEnrollment.query.filter_by(student_id=student_id).all()]
    assignments = _assignments_for_student(student_id, class_ids)

    # Get student's activity
    activity_rows = ReadingActivity.query.filter_by(student_id=student_id).all()
    activity_by_key = {(r.book_folder, r.page_id): r for r in activity_rows}

    # Serialize assignments with reading activity and confidence
    from models import StudentConfidence

    def serialize_assignment_for_admin(a, activity_by_key):
        row = activity_by_key.get((a.book_folder, a.page_id))

        # Get estimated reading time
        estimated_minutes = None
        book_json_path = Path('data') / a.book_folder / 'book.json'
        if book_json_path.exists():
            try:
                with open(book_json_path, 'r', encoding='utf-8') as f:
                    book_data = json.load(f)
                    for page in book_data.get('pages', []):
                        if page.get('id') == a.page_id or page.get('folder') == a.page_id:
                            estimated_minutes = page.get('reading_time_minutes')
                            break
            except:
                pass

        # Get confidence rating
        confidence = StudentConfidence.query.filter_by(
            student_id=student_id,
            book_folder=a.book_folder,
            page_id=a.page_id
        ).first()

        return {
            'title': a.title,
            'resource_type': a.resource_type,
            'resource_label': a.resource_label(),
            'link': a.resource_url(),
            'due_date': a.due_date.strftime('%b %d, %Y %I:%M %p') if a.due_date else None,
            'due_date_raw': a.due_date.isoformat() if a.due_date else None,
            'class_name': a.class_.name if a.class_ else 'Individual',
            'completed': bool(row and row.completed),
            'total_minutes': round((row.total_seconds or 0) / 60, 1) if row else 0,
            'estimated_minutes': estimated_minutes,
            'confidence_level': confidence.confidence_level if confidence else None,
            'created_at': a.created_at.isoformat() if a.created_at else None,
        }

    assignments_data = [serialize_assignment_for_admin(a, activity_by_key) for a in assignments]
    classes = [e.class_ for e in ClassEnrollment.query.filter_by(student_id=student_id).all()]

    return render_template('admin_student_resources.html',
                         student=student,
                         assignments=assignments_data,
                         classes=classes)

@app.route('/admin/api/reading-analytics', methods=['GET'])
@login_required
@admin_required
def api_reading_analytics():
    """Get reading analytics data for admin dashboard"""
    from models import ReadingActivity, User, Class, ClassEnrollment, ReadingAssignment, StudentConfidence
    from collections import defaultdict

    class_id = request.args.get('class_id', '')
    student_id = request.args.get('student_id', '')
    days = request.args.get('days', '30')

    try:
        if days == 'all':
            start_date = None
        else:
            days = int(days)
            start_date = datetime.now() - timedelta(days=days)
    except ValueError:
        start_date = datetime.now() - timedelta(days=30)

    # Get students - either from class, specific student, or all
    student_ids = []

    if student_id:
        # Single student
        student_ids = [int(student_id)]
    elif class_id:
        # Students from a class
        enrollments = ClassEnrollment.query.filter_by(class_id=int(class_id)).all()
        student_ids = [e.student_id for e in enrollments]
    else:
        # All students
        enrollments = ClassEnrollment.query.all()
        student_ids = list(set([e.student_id for e in enrollments]))

    # Build query for activities
    query = ReadingActivity.query.filter(ReadingActivity.student_id.in_(student_ids))
    if start_date:
        query = query.filter(ReadingActivity.last_opened_at >= start_date)

    activities = query.all()

    # Get confidence data
    confidence_query = StudentConfidence.query.filter(StudentConfidence.student_id.in_(student_ids))
    confidence_ratings = confidence_query.all()

    # Aggregate data
    total_seconds = sum(a.total_seconds or 0 for a in activities)
    total_pages = len(set((a.book_folder, a.page_id) for a in activities))
    avg_seconds = total_seconds / len(student_ids) if student_ids else 0

    # Daily/day-of-week activity: prefer the accurate per-day log; fall back to
    # approximating by last-opened date for history predating the log table.
    from models import ReadingDailyLog
    log_query = ReadingDailyLog.query.filter(ReadingDailyLog.student_id.in_(student_ids))
    if start_date:
        log_query = log_query.filter(ReadingDailyLog.date >= start_date.date())
    log_rows = log_query.all()

    activity_by_day = defaultdict(int)
    activity_by_date = defaultdict(int)
    if log_rows:
        for row in log_rows:
            activity_by_day[row.date.weekday()] += row.seconds or 0
            activity_by_date[row.date.isoformat()] += row.seconds or 0
    else:
        for activity in activities:
            if activity.last_opened_at:
                activity_by_day[activity.last_opened_at.weekday()] += activity.total_seconds or 0
                activity_by_date[activity.last_opened_at.strftime('%Y-%m-%d')] += activity.total_seconds or 0

    # Activity by hour
    activity_by_hour = defaultdict(int)
    for activity in activities:
        if activity.last_opened_at:
            hour = activity.last_opened_at.hour
            day_of_week = activity.last_opened_at.weekday()
            key = f"{day_of_week}-{hour}"
            activity_by_hour[key] += activity.total_seconds or 0

    # Top pages - accumulate seconds first, then convert to minutes, add avg confidence
    top_pages_dict = defaultdict(lambda: {'title': '', 'total_seconds': 0, 'count': 0, 'confidence_ratings': []})
    for activity in activities:
        key = (activity.book_folder, activity.page_id)
        assignment = ReadingAssignment.query.filter_by(
            book_folder=activity.book_folder,
            page_id=activity.page_id
        ).first()
        top_pages_dict[key]['title'] = assignment.title if assignment else f"{activity.page_id}"
        top_pages_dict[key]['total_seconds'] += activity.total_seconds or 0
        top_pages_dict[key]['count'] += 1

    # Add confidence data to pages
    for confidence in confidence_ratings:
        key = (confidence.book_folder, confidence.page_id)
        top_pages_dict[key]['confidence_ratings'].append(confidence.confidence_level)

    # Convert seconds to minutes and sort
    top_pages = []
    for data in top_pages_dict.values():
        data['total_minutes'] = round(data['total_seconds'] / 60, 1)
        if data['confidence_ratings']:
            data['avg_confidence'] = round(sum(data['confidence_ratings']) / len(data['confidence_ratings']), 2)
        else:
            data['avg_confidence'] = None
        del data['confidence_ratings']  # Remove the list, keep only the average
        top_pages.append(data)

    top_pages = sorted(top_pages, key=lambda x: x['total_minutes'], reverse=True)

    # Confidence distribution across all pages
    all_confidence_levels = [c.confidence_level for c in confidence_ratings]
    confidence_distribution = defaultdict(int)
    for level in all_confidence_levels:
        confidence_distribution[level] += 1

    # Student stats
    students_data = []
    for student_id in student_ids:
        student = User.query.get(student_id)
        student_activities = [a for a in activities if a.student_id == student_id]
        student_confidence = [c for c in confidence_ratings if c.student_id == student_id]

        if student_activities or student_confidence:
            total_secs = sum(a.total_seconds or 0 for a in student_activities)
            pages = len(set((a.book_folder, a.page_id) for a in student_activities))
            last_active = max((a.last_opened_at for a in student_activities if a.last_opened_at), default=None)
            avg_confidence = round(sum(c.confidence_level for c in student_confidence) / len(student_confidence), 2) if student_confidence else None

            students_data.append({
                'id': student.id,
                'name': student.name,
                'total_seconds': total_secs,
                'pages_read': pages,
                'last_active': last_active.isoformat() if last_active else None,
                'avg_confidence': avg_confidence,
                'pages_rated': len(student_confidence),
            })

    students_data.sort(key=lambda x: x['total_seconds'], reverse=True)

    return jsonify({
        'total_students': len(student_ids),
        'total_seconds': total_seconds,
        'avg_seconds_per_student': avg_seconds,
        'total_pages': total_pages,
        'activity_by_day': dict(activity_by_day),
        'activity_by_date': dict(activity_by_date),
        'activity_by_hour': dict(activity_by_hour),
        'top_pages': top_pages,
        'students': students_data,
        'confidence_distribution': dict(confidence_distribution),
    })

@app.route('/admin/api/classes', methods=['GET'])
@login_required
@admin_required
def api_classes():
    """Get list of classes for filtering"""
    from models import Class

    classes = Class.query.all()
    return jsonify([{'id': c.id, 'name': c.name} for c in classes])

@app.route('/admin/api/students', methods=['GET'])
@login_required
@admin_required
def api_students():
    """Get list of students, optionally filtered by class"""
    from models import User, ClassEnrollment

    class_id = request.args.get('class_id', '')

    if class_id:
        # Students in a specific class
        enrollments = ClassEnrollment.query.filter_by(class_id=int(class_id)).all()
        student_ids = [e.student_id for e in enrollments]
        students = User.query.filter(User.id.in_(student_ids or [0])).all()
    else:
        # All students, enrolled or not
        students = User.query.filter_by(role='student').all()

    return jsonify([{'id': s.id, 'name': s.name or s.email, 'email': s.email, 'avatar': s.avatar}
                    for s in sorted(students, key=lambda s: (s.name or s.email or '').lower())])

# Book Page Folder Management APIs
@app.route('/api/book/<book_folder>/folders', methods=['GET'])
@login_required
def get_book_folders(book_folder):
    """Get all folders for a specific book with item counts"""
    from models import BookPageFolder, BookPageAssignment

    folders = BookPageFolder.query.filter_by(book_folder=book_folder, parent_id=None).all()

    # Map folder_id -> list of page_ids assigned to it (one query for the whole book)
    assignments = BookPageAssignment.query.filter_by(book_folder=book_folder).all()
    pages_by_folder = {}
    for a in assignments:
        pages_by_folder.setdefault(a.folder_id, []).append(a.page_id)

    def build_folder_tree(folder):
        page_ids = pages_by_folder.get(folder.id, [])
        return {
            'id': folder.id,
            'name': folder.name,
            'items': len(page_ids),
            'page_ids': page_ids,
            'subfolders': [build_folder_tree(sf) for sf in folder.subfolders]
        }

    return jsonify({'folders': [build_folder_tree(f) for f in folders]})

@app.route('/api/book/<book_folder>/folders', methods=['POST'])
@login_required
@admin_required
def create_book_folder(book_folder):
    """Create a new folder within a book"""
    from models import BookPageFolder

    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        parent_id = data.get('parent_id')

        if not name:
            return jsonify({'success': False, 'error': 'Folder name is required'}), 400

        # Validate parent folder exists and belongs to same book if provided
        if parent_id:
            parent = BookPageFolder.query.get(parent_id)
            if not parent or parent.book_folder != book_folder:
                return jsonify({'success': False, 'error': 'Parent folder not found'}), 404

        folder = BookPageFolder(book_folder=book_folder, name=name, parent_id=parent_id if parent_id else None)
        db.session.add(folder)
        db.session.commit()

        return jsonify({'success': True, 'folder_id': folder.id})
    except Exception as e:
        db.session.rollback()
        return server_error(e)

@app.route('/api/book/<book_folder>/folders/<int:folder_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_book_folder(book_folder, folder_id):
    """Delete a folder from a book (unassigns pages but doesn't delete them)"""
    from models import BookPageFolder, BookPageAssignment

    try:
        folder = BookPageFolder.query.get(folder_id)
        if not folder or folder.book_folder != book_folder:
            return jsonify({'success': False, 'error': 'Folder not found'}), 404

        # Unassign all pages in this folder
        BookPageAssignment.query.filter_by(folder_id=folder_id).update({'folder_id': None})

        # Recursively handle subfolders
        def unassign_subfolders(parent_folder):
            for subfolder in parent_folder.subfolders:
                BookPageAssignment.query.filter_by(folder_id=subfolder.id).update({'folder_id': None})
                unassign_subfolders(subfolder)

        unassign_subfolders(folder)

        db.session.delete(folder)
        db.session.commit()

        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return server_error(e)

@app.route('/api/book/<book_folder>/page-assignment', methods=['POST'])
@login_required
@admin_required
def assign_page_to_folder(book_folder):
    """Assign a page to a folder within a book"""
    from models import BookPageAssignment

    try:
        data = request.get_json()
        page_id = data.get('page_id')
        folder_id = data.get('folder_id')

        if not page_id:
            return jsonify({'success': False, 'error': 'Page ID is required'}), 400

        # Check if assignment already exists
        existing = BookPageAssignment.query.filter_by(book_folder=book_folder, page_id=page_id).first()
        if existing:
            existing.folder_id = folder_id if folder_id else None
        else:
            assignment = BookPageAssignment(book_folder=book_folder, page_id=page_id, folder_id=folder_id if folder_id else None)
            db.session.add(assignment)

        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return server_error(e)

@app.route('/api/heading-styles', methods=['GET'])
@login_required
def get_heading_styles():
    """Load user's custom heading styles from database"""
    from models import HeadingStyles

    try:
        styles = HeadingStyles.query.filter_by(user_id=current_user.id).all()
        styles_dict = {}
        for style in styles:
            styles_dict[style.heading_level] = {
                'fontSize': style.font_size,
                'color': style.color,
                'fontFamily': style.font_family
            }
        return jsonify(styles_dict)
    except Exception as e:
        return server_error(e)

@app.route('/api/heading-styles', methods=['POST'])
@csrf.exempt
@login_required
def save_heading_styles():
    """Save user's custom heading styles to database"""
    from models import HeadingStyles

    try:
        data = request.get_json()

        # Delete existing styles for this user
        HeadingStyles.query.filter_by(user_id=current_user.id).delete()

        # Save new styles
        for heading_level, style in data.items():
            heading_style = HeadingStyles(
                user_id=current_user.id,
                heading_level=heading_level,
                font_size=style.get('fontSize'),
                color=style.get('color'),
                font_family=style.get('fontFamily')
            )
            db.session.add(heading_style)

        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return server_error(e)

@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    if _is_dev_environment():
        # Werkzeug debugger allows remote code execution: dev only, loopback only.
        app.run(host='127.0.0.1', debug=True, port=port)
    else:
        from waitress import serve
        # Listens on loopback only, so the sole client is the local tunnel/proxy
        # (Tailscale Serve/Funnel or Cloudflare Tunnel). Trusting it lets waitress
        # apply X-Forwarded-For/Proto, so the rate limiter sees each visitor's real
        # IP and Flask knows the request was https (needed for Secure cookies).
        serve(
            app, host='127.0.0.1', port=port, threads=8,
            trusted_proxy='127.0.0.1',
            trusted_proxy_headers={'x-forwarded-for', 'x-forwarded-proto', 'x-forwarded-host'},
            clear_untrusted_proxy_headers=True,
        )
