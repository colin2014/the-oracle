import json
import re
import shutil
import subprocess
import uuid
from datetime import datetime
from pathlib import Path

from flask import Blueprint, jsonify, render_template, request, send_from_directory, abort
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from auth import admin_required
from extensions import db
from models import (
    UnitPlanSemester, UnitPlanWeek, UnitPlanTopic, QuizQuestion, BookVocabulary,
    FlashcardSet,
)

unit_plan_bp = Blueprint("unit_plan", __name__)

SEMESTER_KEYS = ["year1sem1", "year1sem2", "year2sem1", "year2sem2"]

RESOURCES_DIR = Path("data") / "unit_plan_resources"
CALENDAR_FILE = Path("data") / "unit_plan_calendar.json"

# ---------- "Relevant reading" — auto-linked from the Book_93 textbook by syllabus code ----------

BOOK93_FOLDER = "Book_93"
BOOK93_JSON = Path("data") / BOOK93_FOLDER / "book.json"
CODE_RE = re.compile(r"\b([AB])\.?(\d)\.(\d)\.(\d+)\b")

_book93_index_cache = None


def _normalize_code(code):
    return re.sub(r"^([AB])\.", r"\1", (code or "").strip().upper())


def _book93_reading_index():
    """code -> {folder, id, title, readingTimeMinutes}, built once from Book_93's book.json.
    `id` is the book's own stable numeric page id — the same key its existing quiz
    questions are addressed by (QuizQuestion.page_id), which is NOT the same as `folder`
    (folders are a human-readable, potentially-renamed on-disk name; see
    scraper.py:resolve_page_folder)."""
    global _book93_index_cache
    if _book93_index_cache is None:
        index = {}
        if BOOK93_JSON.exists():
            try:
                with open(BOOK93_JSON, "r", encoding="utf-8") as f:
                    book = json.load(f)
                for p in book.get("pages", []):
                    code = p.get("topic_number")
                    if code and p.get("folder") and p.get("id"):
                        index[_normalize_code(code)] = {
                            "folder": p["folder"],
                            "id": p["id"],
                            "title": p.get("title") or code,
                            "readingTimeMinutes": p.get("reading_time_minutes"),
                        }
            except (json.JSONDecodeError, OSError):
                pass
        _book93_index_cache = index
    return _book93_index_cache


def _extract_codes(text):
    if not text:
        return []
    seen = set()
    out = []
    for letter, n1, n2, n3 in CODE_RE.findall(text):
        code = f"{letter}{n1}.{n2}.{n3}"
        if code not in seen:
            seen.add(code)
            out.append(code)
    return out


def _reading_materials_for_codes(codes, quiz_counts=None, vocab_by_page=None, flashcards_by_page=None):
    index = _book93_reading_index()
    quiz_counts = quiz_counts or {}
    vocab_by_page = vocab_by_page or {}
    flashcards_by_page = flashcards_by_page or {}
    out = []
    seen_folders = set()
    for code in codes:
        entry = index.get(_normalize_code(code))
        if entry and entry["folder"] not in seen_folders:
            seen_folders.add(entry["folder"])
            material = {
                "id": "reading-" + entry["folder"],
                "kind": "reading",
                "label": entry["title"],
                "url": f"/book/{BOOK93_FOLDER}/page/{entry['folder']}",
                "code": code,
                "pageId": entry["id"],
                "bookFolder": BOOK93_FOLDER,
                "readingTimeMinutes": entry.get("readingTimeMinutes"),
                "auto": True,
                # Reuse the book's own existing quiz for this page rather than inventing a
                # second quiz system — many pages already have real questions written.
                "quizUrl": f"/book/{BOOK93_FOLDER}/quiz/{entry['id']}",
                "quizCount": quiz_counts.get(entry["id"], 0),
                "assignUrl": f"/admin/assign?book_folder={BOOK93_FOLDER}&page_id={entry['id']}",
            }
            vocab = vocab_by_page.get(entry["id"])
            if vocab:
                material["vocabTerms"] = vocab
            sets = flashcards_by_page.get(entry["id"])
            if sets:
                material["flashcardSets"] = sets
            out.append(material)
    return out


def _with_reading_materials(item_dict, codes, quiz_counts=None, vocab_by_page=None, flashcards_by_page=None):
    """Prepend auto-derived 'relevant reading' entries (never persisted) to an item's materials."""
    reading = _reading_materials_for_codes(codes, quiz_counts, vocab_by_page, flashcards_by_page)
    if reading:
        item_dict["materials"] = reading + (item_dict.get("materials") or [])
    return item_dict


# ---------- convert uploaded slide decks to PDF so they're viewable inline, not just downloadable ----------

CONVERTIBLE_EXTS = {"ppt", "pptx"}
_soffice_path_cache = None


def _find_soffice():
    global _soffice_path_cache
    if _soffice_path_cache is None:
        candidates = [
            shutil.which("soffice"),
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
            "/usr/bin/soffice",
        ]
        _soffice_path_cache = next((c for c in candidates if c and Path(c).exists()), "")
    return _soffice_path_cache


def _convert_to_pdf(src_path, out_dir):
    """Best-effort pptx/ppt -> pdf conversion via headless LibreOffice. Returns the pdf Path,
    or None if conversion isn't available or fails (upload still succeeds either way)."""
    soffice = _find_soffice()
    if not soffice:
        return None
    try:
        subprocess.run(
            [soffice, "--headless", "--norestore", "--convert-to", "pdf", "--outdir", str(out_dir), str(src_path)],
            capture_output=True, timeout=90,
        )
    except (subprocess.SubprocessError, OSError):
        return None
    pdf_path = out_dir / (src_path.stem + ".pdf")
    return pdf_path if pdf_path.exists() else None


def _rasterize_slides(pdf_path, out_dir):
    """Render each page of a converted deck to its own PNG, for a real slide-by-slide
    presentation viewer (rather than an embedded PDF reader). Returns the slide count, or
    None if PyMuPDF isn't available or rendering fails."""
    try:
        import fitz
    except ImportError:
        return None
    slides_dir = out_dir / "slides"
    try:
        slides_dir.mkdir(exist_ok=True)
        doc = fitz.open(str(pdf_path))
        matrix = fitz.Matrix(3, 3)  # ~216 DPI — crisp full-screen on large/4K displays
        count = doc.page_count
        for i in range(count):
            pix = doc.load_page(i).get_pixmap(matrix=matrix)
            pix.save(str(slides_dir / f"{i + 1}.png"))
        doc.close()
        return count
    except Exception:
        shutil.rmtree(slides_dir, ignore_errors=True)
        return None


# ---------- quiz question counts (reuses quiz_routes.py's existing QuizQuestion data) ----------

def _quiz_counts(book_folder):
    """page_id -> question count, for every page under one book_folder (one query)."""
    rows = (
        db.session.query(QuizQuestion.page_id, db.func.count(QuizQuestion.id))
        .filter(QuizQuestion.book_folder == book_folder)
        .group_by(QuizQuestion.page_id)
        .all()
    )
    return {page_id: count for page_id, count in rows}


def _vocab_by_page(book_folder):
    """page_id -> [{term, definition}, ...], for every page under one book_folder
    (one query) — reuses the existing BookVocabulary data (flashcard_routes.py) rather
    than inventing a separate vocabulary store for the unit planner."""
    rows = (
        BookVocabulary.query.filter_by(book_folder=book_folder)
        .order_by(BookVocabulary.term)
        .all()
    )
    out = {}
    for v in rows:
        if v.page_id:
            out.setdefault(v.page_id, []).append({"term": v.term, "definition": v.definition})
    return out


def _flashcard_sets_by_page(book_folder):
    """page_id -> [{id, title, cardCount}, ...] for existing flashcard sets scoped to
    exactly one page. Sets whose cards span multiple pages (or none) are deliberately
    excluded — the unit planner shows one set per individual subtopic, not the book's
    broader mixed-page decks (which stay visible in the regular Flashcards admin area)."""
    sets = FlashcardSet.query.filter_by(book_folder=book_folder).all()
    out = {}
    for s in sets:
        pages = s.page_ids()
        if len(pages) == 1:
            out.setdefault(pages[0], []).append({
                "id": s.id,
                "title": s.title,
                "cardCount": len(s.cards),
            })
    return out


def _slugify(s, default="item"):
    import re
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:50] or default


def _folder_name_for_week(week):
    return "week-" + str(week.week_number).zfill(2) + "-" + _slugify(week.topic, "week")


def _folder_name_for_topic(topic):
    return "syllabus-" + _slugify(topic.code, "topic") + "-" + _slugify(topic.statement, "topic")


def _resolve_item(bucket_key, item_ref):
    """Returns (row, folder_name) for a week (bucket_key = semester key) or a grade12 topic
    (bucket_key = "grade12"), or (None, None) if not found."""
    if bucket_key == "grade12":
        topic = UnitPlanTopic.query.filter_by(topic_id=item_ref).first()
        if not topic:
            return None, None
        return topic, _folder_name_for_topic(topic)
    if bucket_key not in SEMESTER_KEYS:
        return None, None
    semester = UnitPlanSemester.query.filter_by(key=bucket_key).first()
    if not semester:
        return None, None
    week = UnitPlanWeek.query.filter_by(semester_id=semester.id, week_number=item_ref).first()
    if not week:
        return None, None
    return week, _folder_name_for_week(week)


def _materials(row):
    try:
        materials = json.loads(row.materials or "[]")
        return materials if isinstance(materials, list) else []
    except ValueError:
        return []


def _save_materials(row, materials):
    row.materials = json.dumps(materials)


def _codes_for_row(row):
    if isinstance(row, UnitPlanTopic):
        return [row.code]
    codes = _extract_codes(row.syllabus)
    if row.detail:
        try:
            codes += _extract_codes(json.loads(row.detail).get("syllabusLinks"))
        except (ValueError, AttributeError):
            pass
    return codes


def _materials_response(row):
    quiz_counts = _quiz_counts(BOOK93_FOLDER)
    vocab_by_page = _vocab_by_page(BOOK93_FOLDER)
    flashcards_by_page = _flashcard_sets_by_page(BOOK93_FOLDER)
    reading = _reading_materials_for_codes(_codes_for_row(row), quiz_counts, vocab_by_page, flashcards_by_page)
    return jsonify({"materials": reading + _materials(row)})


# ---------- pages ----------

STATIC_DIR = Path(__file__).parent / "static" / "unit_plan"


def _asset_version():
    """Computed fresh per request (cheap — a handful of files) so a browser can never
    silently keep serving a stale cached copy of the JS/CSS after an edit — the query
    string this feeds into script/link tags changes the moment any file's mtime does."""
    mtimes = [f.stat().st_mtime for f in STATIC_DIR.glob("*") if f.is_file()]
    return str(int(max(mtimes))) if mtimes else "0"


@unit_plan_bp.route("/")
@login_required
def index():
    return render_template("unit_plan/index.html", can_edit=current_user.is_admin(), asset_v=_asset_version())


@unit_plan_bp.route("/semester/<key>")
@login_required
def semester_page(key):
    if key not in SEMESTER_KEYS:
        abort(404)
    return render_template("unit_plan/semester.html", semester_key=key, can_edit=current_user.is_admin(), asset_v=_asset_version())


@unit_plan_bp.route("/grade12")
@login_required
def grade12_page():
    return render_template("unit_plan/grade12.html", can_edit=current_user.is_admin(), asset_v=_asset_version())


@unit_plan_bp.route("/calendar")
@login_required
def calendar_page():
    return render_template("unit_plan/calendar.html", can_edit=current_user.is_admin(), asset_v=_asset_version())


@unit_plan_bp.route("/dashboard")
@login_required
@admin_required
def dashboard_page():
    return render_template("unit_plan/dashboard.html", can_edit=current_user.is_admin(), asset_v=_asset_version())


# ---------- JSON API ----------

def _week_codes(w):
    codes = _extract_codes(w.get("syllabus"))
    detail = w.get("detail") or {}
    codes += _extract_codes(detail.get("syllabusLinks"))
    return codes


@unit_plan_bp.route("/api/course-data")
@login_required
def api_course_data():
    data = {}
    quiz_counts = _quiz_counts(BOOK93_FOLDER)
    vocab_by_page = _vocab_by_page(BOOK93_FOLDER)
    flashcards_by_page = _flashcard_sets_by_page(BOOK93_FOLDER)
    for sem in UnitPlanSemester.query.order_by(UnitPlanSemester.position).all():
        weeks = []
        for w in sem.weeks:
            wd = w.to_dict()
            _with_reading_materials(wd, _week_codes(wd), quiz_counts, vocab_by_page, flashcards_by_page)
            weeks.append(wd)
        data[sem.key] = {
            "title": sem.title,
            "subtitle": sem.subtitle,
            "dateRange": sem.date_range,
            "weeks": weeks,
        }
    return jsonify(data)


@unit_plan_bp.route("/api/semester/<key>", methods=["PUT"])
@login_required
@admin_required
def api_update_semester(key):
    semester = UnitPlanSemester.query.filter_by(key=key).first_or_404()
    payload = request.get_json(force=True) or {}
    weeks = payload.get("weeks") or []
    existing = {w.week_number: w for w in semester.weeks}
    for i, w in enumerate(weeks):
        week_number = str(w.get("week"))
        row = existing.get(week_number)
        if not row:
            row = UnitPlanWeek(semester_id=semester.id, week_number=week_number)
            db.session.add(row)
        row.position = i
        row.update_from_dict(w)
    db.session.commit()
    return jsonify({"ok": True})


@unit_plan_bp.route("/api/week/<bucket_key>/<week_number>/taught", methods=["PUT"])
@login_required
@admin_required
def api_toggle_taught(bucket_key, week_number):
    row, _ = _resolve_item(bucket_key, week_number)
    if not row or not isinstance(row, UnitPlanWeek):
        abort(404)
    payload = request.get_json(force=True) or {}
    row.taught = bool(payload.get("taught"))
    db.session.commit()
    return jsonify({"taught": row.taught})


@unit_plan_bp.route("/api/grade12")
@login_required
def api_grade12():
    topics = UnitPlanTopic.query.order_by(UnitPlanTopic.id).all()
    plan = [
        t.topic_id for t in
        UnitPlanTopic.query.filter(UnitPlanTopic.plan_position.isnot(None))
        .order_by(UnitPlanTopic.plan_position).all()
    ]
    quiz_counts = _quiz_counts(BOOK93_FOLDER)
    vocab_by_page = _vocab_by_page(BOOK93_FOLDER)
    flashcards_by_page = _flashcard_sets_by_page(BOOK93_FOLDER)
    topic_dicts = []
    for t in topics:
        td = t.to_dict()
        _with_reading_materials(td, [t.code], quiz_counts, vocab_by_page, flashcards_by_page)
        topic_dicts.append(td)
    return jsonify({"topics": topic_dicts, "plan": plan})


@unit_plan_bp.route("/api/grade12", methods=["PUT"])
@login_required
@admin_required
def api_update_grade12():
    payload = request.get_json(force=True) or {}
    topics_by_id = {t.topic_id: t for t in UnitPlanTopic.query.all()}

    for t in payload.get("topics") or []:
        row = topics_by_id.get(t.get("id"))
        if row and "status" in t:
            row.status = t["status"]

    plan = payload.get("plan") or []
    for row in topics_by_id.values():
        row.plan_position = None
    for i, topic_id in enumerate(plan):
        row = topics_by_id.get(topic_id)
        if row:
            row.plan_position = i

    db.session.commit()
    return jsonify({"ok": True})


@unit_plan_bp.route("/api/calendar")
@login_required
def api_calendar():
    if CALENDAR_FILE.exists():
        try:
            with open(CALENDAR_FILE, "r", encoding="utf-8") as f:
                return jsonify(json.load(f))
        except (json.JSONDecodeError, OSError):
            pass
    return jsonify([])


@unit_plan_bp.route("/api/dashboard-stats")
@login_required
def api_dashboard_stats():
    semesters = []
    for sem in UnitPlanSemester.query.order_by(UnitPlanSemester.position).all():
        weeks = [w for w in sem.weeks if not w.is_break]
        semesters.append({
            "key": sem.key,
            "title": sem.title,
            "taught": sum(1 for w in weeks if w.taught),
            "total": len(weeks),
            "noResources": sum(1 for w in weeks if not _materials(w)),
        })

    topics = UnitPlanTopic.query.all()
    grade12 = {
        "done": sum(1 for t in topics if t.status == "done"),
        "total": len(topics),
        "inPlan": sum(1 for t in topics if t.plan_position is not None),
        "noResources": sum(1 for t in topics if not _materials(t)),
    }

    return jsonify({"semesters": semesters, "grade12": grade12})


@unit_plan_bp.route("/api/materials/link", methods=["POST"])
@login_required
@admin_required
def api_add_link_material():
    payload = request.get_json(force=True) or {}
    row, _ = _resolve_item(payload.get("bucketKey"), payload.get("itemRef"))
    if not row:
        abort(404)
    materials = _materials(row)
    materials.append({
        "id": uuid.uuid4().hex[:10],
        "kind": "link",
        "label": payload.get("label") or payload.get("url"),
        "url": payload.get("url"),
        "linkType": payload.get("linkType") or "link",
        "addedAt": datetime.utcnow().isoformat(),
    })
    _save_materials(row, materials)
    db.session.commit()
    return _materials_response(row)


@unit_plan_bp.route("/api/materials/file", methods=["POST"])
@login_required
@admin_required
def api_add_file_material():
    bucket_key = request.form.get("bucketKey")
    item_ref = request.form.get("itemRef")
    row, folder_name = _resolve_item(bucket_key, item_ref)
    if not row:
        abort(404)
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "No file selected"}), 400

    filename = secure_filename(file.filename) or "file"
    item_dir = RESOURCES_DIR / bucket_key / folder_name
    item_dir.mkdir(parents=True, exist_ok=True)

    name, ext = (filename.rsplit(".", 1) + [""])[:2]
    candidate = filename
    n = 1
    while (item_dir / candidate).exists():
        candidate = f"{name} ({n}).{ext}" if ext else f"{name} ({n})"
        n += 1
    file.save(item_dir / candidate)

    material = {
        "id": uuid.uuid4().hex[:10],
        "kind": "file",
        "label": file.filename,
        "fileName": candidate,
        "path": f"/unit-plan/resources/{bucket_key}/{folder_name}/{candidate}",
        "mimeType": file.mimetype or "",
        "sizeBytes": (item_dir / candidate).stat().st_size,
        "addedAt": datetime.utcnow().isoformat(),
    }

    if ext.lower() in CONVERTIBLE_EXTS:
        pdf_path = _convert_to_pdf(item_dir / candidate, item_dir)
        if pdf_path:
            material["previewPath"] = f"/unit-plan/resources/{bucket_key}/{folder_name}/{pdf_path.name}"
            slide_count = _rasterize_slides(pdf_path, item_dir)
            if slide_count:
                material["slides"] = {
                    "count": slide_count,
                    "urlPattern": f"/unit-plan/resources/{bucket_key}/{folder_name}/slides/{{n}}.png",
                }

    materials = _materials(row)
    materials.append(material)
    _save_materials(row, materials)
    db.session.commit()
    return _materials_response(row)


@unit_plan_bp.route("/api/materials/<bucket_key>/<item_ref>/<material_id>", methods=["DELETE"])
@login_required
@admin_required
def api_remove_material(bucket_key, item_ref, material_id):
    row, folder_name = _resolve_item(bucket_key, item_ref)
    if not row:
        abort(404)
    materials = _materials(row)
    idx = next((i for i, m in enumerate(materials) if m.get("id") == material_id), None)
    if idx is None:
        abort(404)
    m = materials.pop(idx)
    if m.get("kind") == "file" and m.get("fileName"):
        try:
            (RESOURCES_DIR / bucket_key / folder_name / m["fileName"]).unlink()
        except OSError:
            pass
        if m.get("previewPath"):
            try:
                (RESOURCES_DIR / bucket_key / folder_name / Path(m["previewPath"]).name).unlink()
            except OSError:
                pass
        if m.get("slides"):
            shutil.rmtree(RESOURCES_DIR / bucket_key / folder_name / "slides", ignore_errors=True)
    _save_materials(row, materials)
    db.session.commit()
    return _materials_response(row)


@unit_plan_bp.route("/resources/<path:filepath>")
@login_required
def serve_resource(filepath):
    return send_from_directory(RESOURCES_DIR, filepath)
