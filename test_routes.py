"""Test Builder: timed, single-attempt exams assembled from an imported question bank.

Deliberately parallel to quiz_routes.py (own models: TestQuestion/TestPaper/etc.) rather
than reusing QuizQuestion — see the approved plan for rationale. This module currently
covers Phase 1 (question-bank import); later phases add the builder UI, assignment,
taking, marking, and reporting routes on this same blueprint.
"""

import html
import json
import random
import re
import secrets
import string
from datetime import datetime, timedelta
from io import BytesIO

from flask import Blueprint, Response, current_app, jsonify, render_template, request, send_file, url_for
from flask_login import current_user, login_required

from auth import admin_required
from extensions import db
from report_icons import icon as _icon
from models import (
    Class, ClassEnrollment, SubtopicDescriptor, TestAnswer, TestAssignment, TestPaper,
    TestPaperQuestion, TestQuestion, TestSubmission, User, format_marks,
)

test_bp = Blueprint("test_builder", __name__)

# Unambiguous alphabet for spoken/written-on-the-board codes — no 0/O or 1/I.
_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _generate_access_code(length=6):
    for _ in range(20):
        code = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(length))
        if not TestAssignment.query.filter_by(access_code=code).first():
            return code
    raise RuntimeError("Could not generate a unique access code")


# ---------------------------------------------------------------- xlsx import

_SUBTOPIC_CODE_RE = re.compile(r"^([A-Za-z]\d+(?:\.\d+)*)")
_UNIT_CODE_RE = re.compile(r"^([A-Za-z]\d+)")
_MCQ_LETTER_RE = re.compile(r"^\s*([A-Da-d])\b[\s–—\-:]*")

# Every MCQ is worth this, regardless of what the question bank says: at 1 mark each
# they crowded out the written questions and skewed the picture of a student.
MCQ_MARKS = 0.5


def _find_header_row(ws, first_col_value):
    """Scan down column A for the row whose first cell equals first_col_value
    (the sheets have a title/metadata block above the real header)."""
    for r in range(1, min(ws.max_row, 50) + 1):
        if ws.cell(row=r, column=1).value == first_col_value:
            return r
    return None


def _parse_bank_sheet(ws):
    """The curated "Question Answer Bank" sheet: one row per question carrying both
    the question and its answer, replacing the old split Questions/Answers pair.

    Columns are located by header name rather than by position — this sheet dropped
    "Visual search terms" and moved the icon columns when the banks were merged, and
    fixed indices would silently read the wrong column after the next such edit.

    Returns (questions, answers) in the same shape the two-sheet parsers produced,
    so the upsert below doesn't care which layout the workbook uses."""
    header_row = _find_header_row(ws, "QID")
    if header_row is None:
        raise ValueError('Could not find the "QID" header row in the Question Answer Bank sheet')

    cols = {}
    for c in range(1, ws.max_column + 1):
        name = str(ws.cell(row=header_row, column=c).value or "").strip().lower()
        if name:
            cols[name] = c

    def cell(r, name):
        c = cols.get(name)
        return ws.cell(row=r, column=c).value if c else None

    def text(r, name):
        return str(cell(r, name) or "").strip() or None

    questions, answers = {}, {}
    for r in range(header_row + 1, ws.max_row + 1):
        qid = cell(r, "qid")
        if not qid:
            continue
        qid = str(qid).strip()
        questions[qid] = {
            "qid": qid,
            "subtopic": text(r, "subtopic") or "",
            "type": (text(r, "type") or "").lower(),
            "difficulty": (text(r, "difficulty") or "").lower(),
            "command_term": text(r, "command term"),
            "text": text(r, "question") or "",
            "option_a": cell(r, "option a"),
            "option_b": cell(r, "option b"),
            "option_c": cell(r, "option c"),
            "option_d": cell(r, "option d"),
            "marks": cell(r, "marks"),
            "icon_library": text(r, "icon library"),
            "icon_name": text(r, "icon name"),
            "icon_source_url": text(r, "icon source url"),
            "visual_search_terms": text(r, "visual search terms"),
        }
        answers[qid] = {
            "correct_raw": text(r, "correct answer / key points") or "",
            "marking_guidance": text(r, "marking guidance"),
            "common_mistakes": text(r, "common mistakes"),
            "ai_checklist": text(r, "ai marking checklist"),
            "if_wrong_explainer": text(r, "if wrong explainer"),
        }
    return questions, answers


def _parse_questions_sheet(ws):
    header_row = _find_header_row(ws, "QID")
    if header_row is None:
        raise ValueError('Could not find the "QID" header row in the Questions sheet')
    rows = {}
    for r in range(header_row + 1, ws.max_row + 1):
        qid = ws.cell(row=r, column=1).value
        if not qid:
            continue
        rows[str(qid).strip()] = {
            "qid": str(qid).strip(),
            "subtopic": (ws.cell(row=r, column=2).value or "").strip(),
            "type": (ws.cell(row=r, column=3).value or "").strip().lower(),
            "difficulty": (ws.cell(row=r, column=4).value or "").strip().lower(),
            "command_term": (ws.cell(row=r, column=5).value or "").strip() or None,
            "text": (ws.cell(row=r, column=6).value or "").strip(),
            "option_a": ws.cell(row=r, column=7).value,
            "option_b": ws.cell(row=r, column=8).value,
            "option_c": ws.cell(row=r, column=9).value,
            "option_d": ws.cell(row=r, column=10).value,
            "marks": ws.cell(row=r, column=11).value,
            "icon_library": (str(ws.cell(row=r, column=12).value or "").strip() or None),
            "icon_name": (str(ws.cell(row=r, column=13).value or "").strip() or None),
            "icon_source_url": (str(ws.cell(row=r, column=14).value or "").strip() or None),
            "visual_search_terms": (str(ws.cell(row=r, column=15).value or "").strip() or None),
        }
    return rows


def _parse_descriptors_sheet(ws):
    """The "Subtopic Descriptors" sheet: Code | Subtopic | Brief descriptor |
    Question count | MCQ count | Written count | Total marks."""
    header_row = _find_header_row(ws, "Code")
    if header_row is None:
        raise ValueError('Could not find the "Code" header row in the Subtopic Descriptors sheet')

    def num(value):
        return int(value) if isinstance(value, (int, float)) else None

    rows = {}
    for r in range(header_row + 1, ws.max_row + 1):
        code = ws.cell(row=r, column=1).value
        if not code:
            continue
        rows[str(code).strip()] = {
            "title": str(ws.cell(row=r, column=2).value or "").strip(),
            "descriptor": str(ws.cell(row=r, column=3).value or "").strip() or None,
            "question_count": num(ws.cell(row=r, column=4).value),
            "total_marks": num(ws.cell(row=r, column=7).value),
        }
    return rows


def _parse_answers_sheet(ws):
    header_row = _find_header_row(ws, "QID")
    if header_row is None:
        raise ValueError('Could not find the "QID" header row in the Answers sheet')
    rows = {}
    for r in range(header_row + 1, ws.max_row + 1):
        qid = ws.cell(row=r, column=1).value
        if not qid:
            continue
        rows[str(qid).strip()] = {
            "correct_raw": (ws.cell(row=r, column=4).value or "").strip(),
            "marking_guidance": (ws.cell(row=r, column=5).value or "").strip() or None,
            "common_mistakes": (ws.cell(row=r, column=6).value or "").strip() or None,
            "ai_checklist": (ws.cell(row=r, column=7).value or "").strip() or None,
            "if_wrong_explainer": (str(ws.cell(row=r, column=8).value or "")).strip() or None,
        }
    return rows


def _split_subtopic(subtopic_text):
    """'A1.1.1 Describe the functions...' -> ('A1.1.1', 'A1', 'A', 'Describe the functions...', is_hl_only)"""
    m = _SUBTOPIC_CODE_RE.match(subtopic_text)
    code = m.group(1).upper() if m else ""
    title = subtopic_text[m.end():].strip() if m else subtopic_text
    um = _UNIT_CODE_RE.match(code) if code else None
    unit = um.group(1).upper() if um else code
    theme = code[0].upper() if code else ""
    is_hl_only = "(hl only)" in subtopic_text.lower()
    return code, unit, theme, title, is_hl_only


def _parse_mcq_answer(correct_raw, options):
    """'B — Arithmetic logic unit' -> ([1], mismatch_warning_or_None)."""
    m = _MCQ_LETTER_RE.match(correct_raw)
    if not m:
        return [], f'Could not parse an option letter from "{correct_raw}"'
    idx = ord(m.group(1).upper()) - ord("A")
    if idx < 0 or idx >= len(options):
        return [], f'Option letter out of range in "{correct_raw}"'
    trailing = correct_raw[m.end():].strip().lower()
    option_text = (options[idx] or "").strip().lower()
    if trailing and option_text and trailing not in option_text and option_text not in trailing:
        return [idx], f'"{correct_raw}" doesn\'t clearly match option {chr(65+idx)} ("{options[idx]}")'
    return [idx], None


def _upsert_subtopic_descriptors(parsed):
    """Upsert by code, like the question bank — safe to re-run when the workbook
    is refreshed. Returns the number of rows written."""
    existing = {d.code: d for d in SubtopicDescriptor.query.all()}
    for code, values in parsed.items():
        row = existing.get(code)
        if row is None:
            row = SubtopicDescriptor(code=code)
            db.session.add(row)
        row.title = values["title"]
        row.descriptor = values["descriptor"]
        row.question_count = values["question_count"]
        row.total_marks = values["total_marks"]
    return len(parsed)


def _prune_missing_questions(current_qids):
    """Drop bank questions the workbook no longer contains.

    The curated workbook removes rejected questions (e.g. the templated
    "Which response would be strongest...?" MCQs), and a pure upsert would leave
    them sitting in the builder forever. Questions already used in a paper are
    kept regardless — deleting one would rewrite a paper a class has sat — and
    reported back as warnings instead.

    Matched on source_qid for the same reason import is: a renumbered question
    still belongs to the workbook, and comparing its moved qid would delete it."""
    if not current_qids:
        return 0, []
    keys = set(current_qids)
    stale = [q for q in TestQuestion.query.all() if (q.source_qid or q.qid) not in keys]
    if not stale:
        return 0, []

    used_ids = {
        pq.question_id for pq in
        TestPaperQuestion.query.filter(TestPaperQuestion.question_id.in_([q.id for q in stale])).all()
    }
    removed, kept = 0, []
    for question in stale:
        if question.id in used_ids:
            kept.append(question.qid)
            continue
        db.session.delete(question)
        removed += 1
    warnings = (
        [f"{len(kept)} question(s) dropped from the workbook are still used in existing "
         f"papers and were kept: {', '.join(sorted(kept)[:10])}"
         + ("..." if len(kept) > 10 else "")]
        if kept else []
    )
    return removed, warnings


def import_test_bank(file_stream):
    """Parse questions.xlsx and upsert into TestQuestion. Returns a summary dict;
    safe to re-run to refresh the bank later (upsert by qid, not a destructive
    replace), and questions the workbook has dropped are pruned.

    Accepts either the current single "Question Answer Bank" sheet or the older
    Questions + Answers pair joined on qid, so an archived workbook still imports."""
    import openpyxl

    wb = openpyxl.load_workbook(file_stream, data_only=True)
    if "Question Answer Bank" in wb.sheetnames:
        questions, answers = _parse_bank_sheet(wb["Question Answer Bank"])
    elif "Questions" in wb.sheetnames and "Answers" in wb.sheetnames:
        questions = _parse_questions_sheet(wb["Questions"])
        answers = _parse_answers_sheet(wb["Answers"])
    else:
        raise ValueError(
            'Workbook must have a "Question Answer Bank" sheet (or the older '
            '"Questions" and "Answers" pair)'
        )

    # Optional sheet — older workbooks predate it, so a missing sheet is not an
    # import failure; the reports just fall back to subtopic titles alone.
    descriptors_imported = 0
    if "Subtopic Descriptors" in wb.sheetnames:
        descriptors_imported = _upsert_subtopic_descriptors(
            _parse_descriptors_sheet(wb["Subtopic Descriptors"])
        )

    # Keyed on source_qid, not qid: qid is a display label that moves when a
    # subtopic is renumbered after a deletion, so matching on it would write a
    # workbook row's content over whichever question now carries that number.
    # (source_qid is backfilled from qid for rows imported before it existed.)
    existing = {(q.source_qid or q.qid): q for q in TestQuestion.query.all()}
    created, updated, warnings = 0, 0, []

    for qid, q in questions.items():
        a = answers.get(qid, {})
        if not a:
            warnings.append(f"{qid}: no matching row in the Answers sheet — skipped")
            continue

        options = [q["option_a"], q["option_b"], q["option_c"], q["option_d"]]
        is_mcq = q["type"] == "mcq"
        options_list = [str(o) for o in options if o is not None] if is_mcq else []

        correct_options = []
        if is_mcq:
            correct_options, warn = _parse_mcq_answer(a["correct_raw"], options_list)
            if warn:
                warnings.append(f"{qid}: {warn}")

        subtopic_code, unit_code, theme, subtopic_title, is_hl_only = _split_subtopic(q["subtopic"])
        if not subtopic_code:
            warnings.append(f"{qid}: could not parse a subtopic code from \"{q['subtopic']}\" — skipped")
            continue

        # MCQs are fixed at half a mark whatever the spreadsheet says — a paper with
        # a dozen recall MCQs shouldn't outweigh its written questions.
        marks = MCQ_MARKS if is_mcq else (
            q["marks"] if isinstance(q["marks"], (int, float)) else 1
        )

        row = existing.get(qid)
        if row is None:
            row = TestQuestion(qid=qid, source_qid=qid)
            db.session.add(row)
            created += 1
        else:
            # An existing row keeps whatever number it has been renumbered to;
            # only its content is refreshed from the workbook.
            row.source_qid = qid
            updated += 1

        row.subtopic_code = subtopic_code
        row.unit_code = unit_code
        row.theme = theme
        row.subtopic_title = subtopic_title
        row.is_hl_only = is_hl_only
        row.question_type = q["type"]
        row.difficulty = q["difficulty"]
        row.command_term = q["command_term"]
        row.text = q["text"]
        row.options = json.dumps(options_list) if is_mcq else None
        row.correct_options = json.dumps(correct_options) if is_mcq else None
        row.marks = float(marks)
        # For written questions, the bank's "Correct answer / key points" column is the
        # model answer — worth keeping alongside marking_guidance rather than dropped.
        row.marking_guidance = (
            a["correct_raw"] + ("\n\n" + a["marking_guidance"] if a["marking_guidance"] else "")
            if not is_mcq else a["marking_guidance"]
        )
        row.common_mistakes = a["common_mistakes"]
        row.ai_checklist = a["ai_checklist"]
        row.if_wrong_explainer = a["if_wrong_explainer"]
        row.icon_library = q["icon_library"]
        row.icon_name = q["icon_name"]
        row.icon_source_url = q["icon_source_url"]
        row.visual_search_terms = q["visual_search_terms"]
        row.updated_at = datetime.utcnow()

    removed, prune_warnings = _prune_missing_questions(list(questions.keys()))
    warnings.extend(prune_warnings)
    db.session.flush()

    # The workbook's own numbering has gaps (curation dropped rejected questions),
    # and rows deleted in the audit page leave more. Numbering is ours to own now,
    # so every subtopic is renormalised to Q01..Qnn after the content lands.
    renumbered = 0
    for (code,) in db.session.query(TestQuestion.subtopic_code).distinct().all():
        renumbered += len(_renumber_subtopic(code))

    db.session.commit()
    return {
        "created": created,
        "updated": updated,
        "removed": removed,
        "renumbered": renumbered,
        "descriptors": descriptors_imported,
        "total_in_file": len(questions),
        "warnings": warnings,
    }


@test_bp.route("/admin/api/test-bank/import", methods=["POST"])
@login_required
@admin_required
def test_bank_import():
    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"error": "No file uploaded"}), 400
    if not file.filename.lower().endswith(".xlsx"):
        return jsonify({"error": "Expected an .xlsx file"}), 400
    try:
        result = import_test_bank(file.stream)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Import failed: {e}"}), 500
    return jsonify({"ok": True, **result})


def _bucket_of(q):
    """Builder bucket key for a question. Written buckets are keyed by whole mark
    value ("written_2") — format_marks keeps the float column from turning that
    into "written_2.0", which the builder UI wouldn't match."""
    return "mcq" if q.is_mcq() else f"written_{format_marks(q.marks)}"


@test_bp.route("/admin/api/test-bank/summary")
@login_required
@admin_required
def test_bank_summary():
    """Counts by theme/unit/subtopic, for the builder UI's subtopic browser."""
    rows = TestQuestion.query.all()
    themes = {}
    for q in rows:
        theme = themes.setdefault(q.theme, {"units": {}})
        unit = theme["units"].setdefault(q.unit_code, {"subtopics": {}})
        subtopic = unit["subtopics"].setdefault(q.subtopic_code, {
            "title": q.subtopic_title,
            "is_hl_only": q.is_hl_only,
            "buckets": {},
        })
        bucket_key = _bucket_of(q)
        subtopic["buckets"][bucket_key] = subtopic["buckets"].get(bucket_key, 0) + 1

    return jsonify({"total_questions": len(rows), "themes": themes})


@test_bp.route("/admin/api/test-bank/subtopic/<subtopic_code>/questions")
@login_required
@admin_required
def subtopic_questions(subtopic_code):
    """Every question in one subtopic, for the builder's browse/manual-pick view.
    Pass ?paper_id= to flag which ones are already in that paper."""
    paper_id = request.args.get("paper_id", type=int)
    already_in = set()
    if paper_id:
        already_in = {
            pq.question_id for pq in
            TestPaperQuestion.query.filter_by(test_paper_id=paper_id).all()
        }
    rows = (
        TestQuestion.query.filter_by(subtopic_code=subtopic_code)
        .order_by(TestQuestion.marks, TestQuestion.question_type.desc(), TestQuestion.id)
        .all()
    )
    return jsonify({"questions": [_question_summary(q, in_paper=q.id in already_in) for q in rows]})


def _question_summary(q, in_paper=None):
    d = {
        "id": q.id,
        "qid": q.qid,
        "subtopic_code": q.subtopic_code,
        "unit_code": q.unit_code,
        "theme": q.theme,
        "is_hl_only": q.is_hl_only,
        "question_type": q.question_type,
        "difficulty": q.difficulty,
        "command_term": q.command_term,
        "text": q.text,
        "marks": q.marks,
        "bucket": _bucket_of(q),
        "icon_name": q.icon_name,
        "icon_source_url": q.icon_source_url,
    }
    if q.is_mcq():
        d["options"] = q.options_list()
    if in_paper is not None:
        d["in_paper"] = in_paper
    return d


# ------------------------------------------------------------- question bank audit

def _question_detail(q):
    """Every editable field of one bank question, for the audit editor. Distinct
    from _question_summary, which is the builder's browse payload and deliberately
    omits the mark-scheme prose."""
    return {
        "id": q.id,
        "qid": q.qid,
        "source_qid": q.source_qid,
        "subtopic_code": q.subtopic_code,
        "subtopic_title": q.subtopic_title,
        "unit_code": q.unit_code,
        "theme": q.theme,
        "is_hl_only": q.is_hl_only,
        "question_type": q.question_type,
        "difficulty": q.difficulty,
        "command_term": q.command_term,
        "text": q.text,
        "marks": q.marks,
        "marks_label": format_marks(q.marks),
        "options": q.options_list(),
        "correct_options": q.correct_indices(),
        "marking_guidance": q.marking_guidance,
        "common_mistakes": q.common_mistakes,
        "ai_checklist": q.ai_checklist,
        "if_wrong_explainer": q.if_wrong_explainer,
        "icon_library": q.icon_library,
        "icon_name": q.icon_name,
        "icon_source_url": q.icon_source_url,
        "updated_at": q.updated_at.strftime("%d %b %Y, %H:%M") if q.updated_at else None,
        # Papers already built from this question — edits reach students who sit
        # those papers, and a delete would change a paper that exists.
        "in_paper_count": TestPaperQuestion.query.filter_by(question_id=q.id).count(),
    }


@test_bp.route("/assessment/question-bank")
@login_required
@admin_required
def question_bank_page():
    return render_template("question_bank.html")


@test_bp.route("/admin/api/test-bank/subtopic/<subtopic_code>/audit")
@login_required
@admin_required
def subtopic_questions_audit(subtopic_code):
    rows = (
        TestQuestion.query.filter_by(subtopic_code=subtopic_code)
        .order_by(TestQuestion.qid)
        .all()
    )
    if not rows:
        return jsonify({"subtopic_code": subtopic_code, "subtopic_title": None, "questions": []})
    descriptor = SubtopicDescriptor.query.filter_by(code=subtopic_code).first()
    return jsonify({
        "subtopic_code": subtopic_code,
        "subtopic_title": rows[0].subtopic_title,
        "descriptor": descriptor.descriptor if descriptor else None,
        "questions": [_question_detail(q) for q in rows],
    })


@test_bp.route("/admin/api/test-bank/questions/<int:question_id>", methods=["PUT"])
@login_required
@admin_required
def update_bank_question(question_id):
    """Edit one bank question in place. Only keys present in the body are touched,
    so a client can save a single field without echoing the whole row back."""
    q = TestQuestion.query.get_or_404(question_id)
    data = request.get_json(force=True, silent=True) or {}

    text_fields = (
        "text", "command_term", "marking_guidance", "common_mistakes",
        "ai_checklist", "if_wrong_explainer", "icon_library", "icon_name",
        "icon_source_url", "difficulty", "question_type",
    )
    for field in text_fields:
        if field in data:
            value = (str(data[field]) if data[field] is not None else "").strip()
            setattr(q, field, value or None)

    if not (q.text or "").strip():
        return jsonify({"error": "Question text can't be empty"}), 400
    if q.question_type not in ("mcq", "written"):
        return jsonify({"error": 'question_type must be "mcq" or "written"'}), 400

    if "marks" in data:
        # Float, not int: the bank carries 0.5-mark questions and rounding them
        # to a whole mark would quietly change the paper's total.
        try:
            marks = float(data["marks"])
        except (TypeError, ValueError):
            return jsonify({"error": "marks must be a number"}), 400
        if marks <= 0:
            return jsonify({"error": "marks must be greater than zero"}), 400
        q.marks = marks

    if "is_hl_only" in data:
        q.is_hl_only = bool(data["is_hl_only"])

    if q.is_mcq():
        if "options" in data:
            options = [str(o).strip() for o in (data["options"] or []) if str(o).strip()]
            if len(options) < 2:
                return jsonify({"error": "An MCQ needs at least two options"}), 400
            q.options = json.dumps(options)
        if "correct_options" in data:
            options = q.options_list()
            try:
                correct = sorted({int(i) for i in (data["correct_options"] or [])})
            except (TypeError, ValueError):
                return jsonify({"error": "correct_options must be a list of option indexes"}), 400
            if not correct:
                return jsonify({"error": "Mark which option is correct"}), 400
            if any(i < 0 or i >= len(options) for i in correct):
                return jsonify({"error": "A correct answer points at an option that doesn't exist"}), 400
            q.correct_options = json.dumps(correct)
    else:
        # Switching a question to written retires its MCQ-only columns rather than
        # leaving stale options behind for the marker to trip over.
        q.options = None
        q.correct_options = None

    q.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"ok": True, "question": _question_detail(q)})


_QID_NUMBER_RE = re.compile(r"-Q(\d+)\s*$", re.IGNORECASE)


def _renumber_subtopic(subtopic_code):
    """Close the gaps in one subtopic's question numbers after a deletion, so
    A1.3.1 reads Q01..Q29 rather than Q01..Q30 with Q17 missing.

    Existing order is preserved (sorted by current number); only the labels move.
    Renaming happens in two passes through a temporary qid because qid is unique —
    a straight rename would collide with the row it is about to overwrite.

    Returns {old_qid: new_qid} for the rows that actually changed.
    """
    rows = TestQuestion.query.filter_by(subtopic_code=subtopic_code).all()

    def sort_key(q):
        match = _QID_NUMBER_RE.search(q.qid or "")
        # Anything not matching the -Qnn convention sorts last, by id, rather than
        # being silently renumbered into the middle of the sequence.
        return (0, int(match.group(1))) if match else (1, q.id)

    rows.sort(key=sort_key)

    planned = {}
    for position, q in enumerate(rows, start=1):
        new_qid = f"{subtopic_code}-Q{position:02d}"
        if q.qid != new_qid:
            planned[q.id] = (q.qid, new_qid)

    if not planned:
        return {}

    for q in rows:
        if q.id in planned:
            q.qid = f"__renumber_{q.id}"
    db.session.flush()
    for q in rows:
        if q.id in planned:
            q.qid = planned[q.id][1]
    db.session.flush()

    return {old: new for old, new in planned.values()}


@test_bp.route("/admin/api/test-bank/subtopic/<subtopic_code>/renumber", methods=["POST"])
@login_required
@admin_required
def renumber_subtopic(subtopic_code):
    """Renumber a subtopic on demand — for tidying gaps left by earlier deletions."""
    renamed = _renumber_subtopic(subtopic_code)
    db.session.commit()
    return jsonify({"ok": True, "renamed": renamed, "renamed_count": len(renamed)})


@test_bp.route("/admin/api/test-bank/questions/<int:question_id>", methods=["DELETE"])
@login_required
@admin_required
def delete_bank_question(question_id):
    """Remove a question from the bank.

    A question sitting in an existing paper needs ?confirm_in_use=1: deleting it
    silently rewrites that paper (and any submission's view of it), so the caller
    has to say it means that."""
    q = TestQuestion.query.get_or_404(question_id)
    memberships = TestPaperQuestion.query.filter_by(question_id=q.id).all()

    if memberships and request.args.get("confirm_in_use") != "1":
        papers = TestPaper.query.filter(
            TestPaper.id.in_([m.test_paper_id for m in memberships])
        ).all()
        return jsonify({
            "error": "This question is used in existing papers.",
            "needs_confirmation": True,
            "qid": q.qid,
            "papers": [{"id": p.id, "title": p.title} for p in papers],
        }), 409

    answer_count = TestAnswer.query.filter_by(question_id=q.id).count()
    if answer_count:
        return jsonify({
            "error": (
                f"{q.qid} already has {answer_count} student answer(s) recorded, so it "
                "can't be deleted without destroying marked work. Edit it instead."
            ),
        }), 409

    for membership in memberships:
        db.session.delete(membership)
    current_app.logger.warning(
        "Deleting bank question %s (id=%s) by user=%s — removed from %d paper(s)",
        q.qid, q.id, getattr(current_user, "id", None), len(memberships),
    )
    subtopic_code = q.subtopic_code
    db.session.delete(q)
    db.session.flush()
    # Close the gap the deletion just left, so the subtopic stays Q01..Qnn.
    renamed = _renumber_subtopic(subtopic_code)
    db.session.commit()
    return jsonify({
        "ok": True,
        "removed_from_papers": len(memberships),
        "renamed": renamed,
        "renamed_count": len(renamed),
    })


# ---------------------------------------------------------------- test paper pages/CRUD

@test_bp.route("/assessment/test-builder")
@login_required
@admin_required
def test_builder_home():
    return render_template("test_builder.html", paper_id=None, debug=current_app.debug)


@test_bp.route("/assessment/test-builder/<int:paper_id>")
@login_required
@admin_required
def test_builder_edit(paper_id):
    return render_template("test_builder.html", paper_id=paper_id, debug=current_app.debug)


def _paper_summary(p):
    assigned_count = sum(_assignment_target_count(a) for a in p.assignments)
    submitted_count = sum(1 for s in p.submissions if s.status in ("submitted", "marked"))
    return {
        "id": p.id,
        "title": p.title,
        "description": p.description,
        "time_limit_minutes": p.time_limit_minutes,
        "question_count": len(p.paper_questions),
        "total_marks": p.total_marks,
        "has_hl_only_questions": p.has_hl_only_questions,
        "created_at": p.created_at.strftime("%b %d, %Y") if p.created_at else None,
        "assigned_count": assigned_count,
        "submitted_count": submitted_count,
    }


@test_bp.route("/admin/api/test-papers")
@login_required
@admin_required
def list_test_papers():
    papers = TestPaper.query.order_by(TestPaper.created_at.desc()).all()
    return jsonify({"papers": [_paper_summary(p) for p in papers]})


@test_bp.route("/admin/api/test-papers", methods=["POST"])
@login_required
@admin_required
def create_test_paper():
    data = request.get_json(force=True, silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "title is required"}), 400
    paper = TestPaper(
        title=title,
        description=(data.get("description") or "").strip() or None,
        owner_id=current_user.id,
        time_limit_minutes=int(data.get("time_limit_minutes") or 60),
        status="draft",
    )
    db.session.add(paper)
    db.session.commit()
    return jsonify({"ok": True, "paper": _paper_summary(paper)})


@test_bp.route("/admin/api/test-papers/<int:paper_id>")
@login_required
@admin_required
def get_test_paper(paper_id):
    paper = TestPaper.query.get_or_404(paper_id)
    return jsonify({
        "paper": _paper_summary(paper),
        "questions": [
            _question_summary(pq.question) for pq in paper.paper_questions
        ],
    })


@test_bp.route("/admin/api/test-papers/<int:paper_id>", methods=["PUT"])
@login_required
@admin_required
def update_test_paper(paper_id):
    paper = TestPaper.query.get_or_404(paper_id)
    data = request.get_json(force=True, silent=True) or {}
    if "title" in data:
        title = (data.get("title") or "").strip()
        if not title:
            return jsonify({"error": "title cannot be empty"}), 400
        paper.title = title
    if "description" in data:
        paper.description = (data.get("description") or "").strip() or None
    if "time_limit_minutes" in data:
        paper.time_limit_minutes = int(data.get("time_limit_minutes") or 60)
    paper.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"ok": True, "paper": _paper_summary(paper)})


@test_bp.route("/admin/api/test-papers/<int:paper_id>", methods=["DELETE"])
@login_required
@admin_required
def delete_test_paper(paper_id):
    """Delete one paper and only that paper.

    Deleting a paper cascades to its assignments, submissions and every answer
    inside them — a click here can destroy a class's completed work, and nothing
    about the old one-line confirm said so. Two guards now stand in the way:
    a paper carrying submissions needs an explicit ?confirm_submissions=1, and
    every deletion is logged with what it took with it, so if papers ever go
    missing again the log says exactly which request removed which id.
    """
    paper = TestPaper.query.get_or_404(paper_id)

    submissions = list(paper.submissions)
    answer_count = sum(len(s.answers) for s in submissions)
    assignment_count = len(paper.assignments)

    if submissions and request.args.get("confirm_submissions") != "1":
        return jsonify({
            "error": "This paper has student work attached.",
            "needs_confirmation": True,
            "paper_title": paper.title,
            "submission_count": len(submissions),
            "answer_count": answer_count,
            "student_names": sorted(
                s.student.name for s in submissions if s.student is not None
            )[:12],
        }), 409

    current_app.logger.warning(
        "Deleting test paper id=%s title=%r by user=%s — cascading to %d assignment(s), "
        "%d submission(s), %d answer(s). Papers remaining before delete: %s",
        paper.id, paper.title, getattr(current_user, "id", None),
        assignment_count, len(submissions), answer_count,
        [p.id for p in TestPaper.query.with_entities(TestPaper.id).all()],
    )

    db.session.delete(paper)
    db.session.commit()

    remaining = TestPaper.query.count()
    current_app.logger.warning("Deleted test paper id=%s. Papers remaining: %d", paper_id, remaining)
    return jsonify({
        "ok": True,
        "deleted_paper_id": paper_id,
        "papers_remaining": remaining,
        "deleted_submissions": len(submissions),
    })


@test_bp.route("/admin/api/test-papers/<int:paper_id>/duplicate", methods=["POST"])
@login_required
@admin_required
def duplicate_test_paper(paper_id):
    src = TestPaper.query.get_or_404(paper_id)
    copy = TestPaper(
        title=f"{src.title} (copy)",
        description=src.description,
        owner_id=current_user.id,
        time_limit_minutes=src.time_limit_minutes,
        status="draft",
    )
    db.session.add(copy)
    db.session.flush()
    for pq in src.paper_questions:
        db.session.add(TestPaperQuestion(test_paper_id=copy.id, question_id=pq.question_id, position=pq.position))
    db.session.commit()
    return jsonify({"ok": True, "paper": _paper_summary(copy)})


# ---------------------------------------------------------------- assembling a paper's questions

@test_bp.route("/admin/api/test-papers/<int:paper_id>/questions/auto-generate", methods=["POST"])
@login_required
@admin_required
def auto_generate_questions(paper_id):
    """Randomly sample N questions per mark-value bucket from one subtopic into
    the draft paper. body: {subtopic_code, buckets: {"mcq": 2, "written_2": 2, ...}}"""
    paper = TestPaper.query.get_or_404(paper_id)
    data = request.get_json(force=True, silent=True) or {}
    subtopic_code = (data.get("subtopic_code") or "").strip()
    buckets = data.get("buckets") or {}
    if not subtopic_code or not isinstance(buckets, dict):
        return jsonify({"error": "subtopic_code and buckets are required"}), 400

    already_in_ids = {pq.question_id for pq in paper.paper_questions}
    pool = TestQuestion.query.filter_by(subtopic_code=subtopic_code).all()

    bucket_of = _bucket_of

    added, shortfalls = [], []
    next_position = max([pq.position for pq in paper.paper_questions], default=-1) + 1

    for bucket_key, count in buckets.items():
        try:
            count = int(count)
        except (TypeError, ValueError):
            continue
        if count <= 0:
            continue
        candidates = [q for q in pool if bucket_of(q) == bucket_key and q.id not in already_in_ids]
        random.shuffle(candidates)
        picked = candidates[:count]
        if len(picked) < count:
            shortfalls.append(f'{bucket_key}: wanted {count}, only {len(picked)} available')
        for q in picked:
            db.session.add(TestPaperQuestion(test_paper_id=paper.id, question_id=q.id, position=next_position))
            already_in_ids.add(q.id)
            added.append(q.id)
            next_position += 1

    db.session.commit()
    return jsonify({
        "ok": True,
        "added": len(added),
        "shortfalls": shortfalls,
        "paper": _paper_summary(paper),
        "questions": [_question_summary(pq.question) for pq in paper.paper_questions],
    })


@test_bp.route("/admin/api/test-papers/<int:paper_id>/questions/add", methods=["POST"])
@login_required
@admin_required
def add_questions_manually(paper_id):
    paper = TestPaper.query.get_or_404(paper_id)
    data = request.get_json(force=True, silent=True) or {}
    question_ids = data.get("question_ids")
    if not isinstance(question_ids, list) or not question_ids:
        return jsonify({"error": "question_ids (a non-empty list) is required"}), 400

    already_in_ids = {pq.question_id for pq in paper.paper_questions}
    next_position = max([pq.position for pq in paper.paper_questions], default=-1) + 1
    added = 0
    for qid in question_ids:
        try:
            qid = int(qid)
        except (TypeError, ValueError):
            continue
        if qid in already_in_ids:
            continue
        if not TestQuestion.query.get(qid):
            continue
        db.session.add(TestPaperQuestion(test_paper_id=paper.id, question_id=qid, position=next_position))
        already_in_ids.add(qid)
        next_position += 1
        added += 1
    db.session.commit()
    return jsonify({
        "ok": True, "added": added, "paper": _paper_summary(paper),
        "questions": [_question_summary(pq.question) for pq in paper.paper_questions],
    })


@test_bp.route("/admin/api/test-papers/<int:paper_id>/questions/<int:question_id>", methods=["DELETE"])
@login_required
@admin_required
def remove_question(paper_id, question_id):
    pq = TestPaperQuestion.query.filter_by(test_paper_id=paper_id, question_id=question_id).first()
    if not pq:
        return jsonify({"error": "Question not in this paper"}), 404
    db.session.delete(pq)
    db.session.commit()
    return jsonify({"ok": True})


@test_bp.route("/admin/api/test-papers/<int:paper_id>/questions/reorder", methods=["PUT"])
@login_required
@admin_required
def reorder_questions(paper_id):
    data = request.get_json(force=True, silent=True) or {}
    question_ids = data.get("question_ids")
    if not isinstance(question_ids, list):
        return jsonify({"error": "question_ids (a list) is required"}), 400
    rows = {pq.question_id: pq for pq in TestPaperQuestion.query.filter_by(test_paper_id=paper_id).all()}
    for i, qid in enumerate(question_ids):
        pq = rows.get(int(qid))
        if pq:
            pq.position = i
    db.session.commit()
    return jsonify({"ok": True})


# ---------------------------------------------------------------- assigning a paper (with join code)

@test_bp.route("/assessment/test-builder/<int:paper_id>/assign")
@login_required
@admin_required
def assign_test_page(paper_id):
    paper = TestPaper.query.get_or_404(paper_id)
    classes = Class.query.filter_by(is_archived=False).order_by(Class.name).all()
    students = User.query.filter_by(role="student").order_by(User.name).all()
    return render_template("test_assign.html", paper=paper, classes=classes, students=students)


def _assignment_target_count(a):
    """How many students this assignment reaches — a class's enrollment
    (optionally narrowed to just HL or just SL), or 1 for a direct student
    assignment."""
    if a.class_id:
        query = ClassEnrollment.query.filter_by(class_id=a.class_id)
        if a.level_filter:
            query = query.filter_by(level=a.level_filter)
        return query.count()
    return 1 if a.student_id else 0


def _assignment_summary(a):
    submitted = sum(1 for s in a.submissions if s.status != "in_progress")
    return {
        "id": a.id,
        "target_label": a.target_label(),
        "access_code": a.access_code,
        "time_limit_minutes": a.time_limit_minutes,
        "submission_count": len(a.submissions),
        "submitted_count": submitted,
        "assigned_count": _assignment_target_count(a),
        "created_at": a.created_at.strftime("%b %d, %Y") if a.created_at else None,
    }


@test_bp.route("/admin/api/test-papers/<int:paper_id>/assignments")
@login_required
@admin_required
def list_assignments(paper_id):
    paper = TestPaper.query.get_or_404(paper_id)
    rows = TestAssignment.query.filter_by(test_paper_id=paper.id).order_by(TestAssignment.created_at.desc()).all()
    return jsonify({"assignments": [_assignment_summary(a) for a in rows]})


@test_bp.route("/admin/api/test-papers/<int:paper_id>/submissions")
@login_required
@admin_required
def list_submissions(paper_id):
    paper = TestPaper.query.get_or_404(paper_id)
    rows = TestSubmission.query.filter_by(test_paper_id=paper.id).order_by(TestSubmission.started_at.desc()).all()
    return jsonify({"submissions": [{
        "id": s.id,
        "student_name": s.student.name,
        "student_avatar": s.student.avatar,
        "status": s.status,
        "marks_awarded": s.total_marks_awarded,
        "marks_possible": s.total_marks_possible,
        "submitted_at": s.submitted_at.strftime("%b %d, %Y %I:%M %p") if s.submitted_at else None,
        "pending_answers": sum(1 for a in s.answers if a.status != "reviewed"),
    } for s in rows]})


@test_bp.route("/assessment/test-builder/<int:paper_id>/monitor")
@login_required
@admin_required
def monitor_test_page(paper_id):
    paper = TestPaper.query.get_or_404(paper_id)
    return render_template("test_monitor.html", paper=paper)


@test_bp.route("/admin/api/test-papers/<int:paper_id>/monitor")
@login_required
@admin_required
def monitor_test_data(paper_id):
    paper = TestPaper.query.get_or_404(paper_id)
    questions = paper.questions

    # Everyone the paper reaches, not just everyone who has started: a student who
    # hasn't joined yet is the one the teacher most needs to see. Rostered students
    # are unioned with anyone holding a submission (unenrolled after sitting it, or
    # joined by code from another class) so no real work is hidden.
    by_student = {}
    for assignment in paper.assignments:
        for row in _assignment_roster(assignment):
            by_student.setdefault(row["student_id"], row)

    submissions = [
        s for s in TestSubmission.query.filter_by(test_paper_id=paper.id).all()
        if s.student is not None and s.status in ("in_progress", "submitted", "marked")
    ]
    submissions_by_student = {s.student_id: s for s in submissions}
    for student_id, s in submissions_by_student.items():
        by_student.setdefault(student_id, {
            "student_id": student_id,
            "student_name": s.student.name,
            "student_avatar": s.student.avatar,
            "status": s.status,
            "submission_id": s.id,
        })

    students_payload = []
    for row in by_student.values():
        s = submissions_by_student.get(row["student_id"])
        answers_by_qid = {a.question_id: a for a in s.answers} if s else {}
        question_payloads = []
        answered = 0
        for q in questions:
            a = answers_by_qid.get(q.id)
            selected = a.selected_indices() if a else []
            response_text = a.response_text if (a and not q.is_mcq()) else None
            if selected or (response_text or "").strip():
                answered += 1
            question_payloads.append({
                "question_id": q.id,
                "marks": q.marks,
                "is_mcq": q.is_mcq(),
                "options": q.options_list() if q.is_mcq() else None,
                "selected_options": selected,
                "response_text": response_text,
                "word_count": len((response_text or "").split()),
                "last_saved_at": (a.submitted_at.isoformat() + "Z") if a and a.submitted_at else None,
            })
        students_payload.append({
            "student_id": row["student_id"],
            "submission_id": s.id if s else None,
            "student_name": row["student_name"],
            "student_avatar": row["student_avatar"],
            "status": s.status if s else "not_started",
            "started_at": s.started_at.strftime("%I:%M %p") if s else None,
            "deadline_iso": (s.deadline.isoformat() + "Z") if s and s.status == "in_progress" else None,
            "is_overdue": bool(s.is_overdue) if s else False,
            "answered_count": answered,
            "answers": question_payloads,
        })

    # Working students first — they are the ones whose answers are changing. Then
    # the ones who haven't started (and need chasing), then the ones who are done.
    order = {"in_progress": 0, "not_started": 1, "submitted": 2, "marked": 3}
    students_payload.sort(key=lambda r: (order.get(r["status"], 9), r["student_name"] or ""))

    return jsonify({
        "paper_title": paper.title,
        "question_count": len(questions),
        "questions": [{"id": q.id, "text": q.text, "marks": q.marks, "is_mcq": q.is_mcq()} for q in questions],
        "students": students_payload,
    })


@test_bp.route("/assessment/test-submissions/<int:submission_id>/live")
@login_required
@admin_required
def student_live_page(submission_id):
    """One student's paper, live, in its own window — opened from the invigilation
    panels so a teacher can watch a single student write without giving up the
    class-wide view in the tab they came from."""
    submission = TestSubmission.query.get_or_404(submission_id)
    return render_template("test_student_live.html", submission=submission)


@test_bp.route("/admin/api/test-submissions/<int:submission_id>/live")
@login_required
@admin_required
def student_live_data(submission_id):
    submission = TestSubmission.query.get_or_404(submission_id)
    answers_by_qid = {a.question_id: a for a in submission.answers}

    questions, answered = [], 0
    for position, question in enumerate(submission.paper.questions, start=1):
        answer = answers_by_qid.get(question.id)
        selected = answer.selected_indices() if answer else []
        response_text = answer.response_text if (answer and not question.is_mcq()) else None
        if selected or (response_text or "").strip():
            answered += 1
        questions.append({
            "number": position,
            "text": question.text,
            "marks": question.marks,
            "is_mcq": question.is_mcq(),
            "options": question.options_list() if question.is_mcq() else None,
            "selected_options": selected,
            "response_text": response_text,
            "word_count": len((response_text or "").split()),
            "last_saved_at": (answer.submitted_at.isoformat() + "Z") if answer and answer.submitted_at else None,
            # Only ever the teacher's view: the student's own report shows this
            # after submission, not while they are still working.
            "marks_awarded": answer.marks_awarded if answer else None,
        })

    return jsonify({
        "student_name": submission.student.name if submission.student else "Unknown student",
        "student_avatar": submission.student.avatar if submission.student else None,
        "paper_title": submission.paper.title,
        "paper_id": submission.paper.id,
        "status": submission.status,
        "started_at": submission.started_at.strftime("%I:%M %p") if submission.started_at else None,
        "deadline_iso": (submission.deadline.isoformat() + "Z") if submission.status == "in_progress" else None,
        "question_count": len(questions),
        "answered_count": answered,
        "questions": questions,
    })


def _class_has_sl_student(class_id, level_filter=None):
    query = ClassEnrollment.query.filter(ClassEnrollment.class_id == class_id)
    if level_filter:
        # Assignment is already narrowed to one level — only warn if that level is SL.
        return level_filter == "SL"
    return query.filter(ClassEnrollment.level == "SL").first() is not None


@test_bp.route("/admin/api/test-papers/<int:paper_id>/assignments", methods=["POST"])
@login_required
@admin_required
def create_assignment(paper_id):
    paper = TestPaper.query.get_or_404(paper_id)
    if not paper.paper_questions:
        return jsonify({"error": "Add at least one question before assigning"}), 400
    data = request.get_json(force=True, silent=True) or {}

    target_type = data.get("target_type")
    class_id = data.get("class_id")
    student_id = data.get("student_id")
    level_filter = data.get("level") or None
    if level_filter not in (None, "HL", "SL"):
        return jsonify({"error": "level must be 'HL', 'SL', or omitted"}), 400
    if target_type == "class":
        if not class_id or not Class.query.get(class_id):
            return jsonify({"error": "Please choose a class"}), 400
        student_id = None
    elif target_type == "student":
        if not student_id or not User.query.filter_by(id=student_id, role="student").first():
            return jsonify({"error": "Please choose a student"}), 400
        class_id = None
        level_filter = None  # only meaningful for a class target
    else:
        return jsonify({"error": "target_type must be 'class' or 'student'"}), 400

    # No opens_at/due_date: these are done in class, in one sitting — the time
    # limit (counted from the moment each student enters the code) is the only
    # window that matters.
    assignment = TestAssignment(
        test_paper_id=paper.id,
        class_id=class_id,
        student_id=student_id,
        level_filter=level_filter,
        assigned_by_id=current_user.id,
        time_limit_minutes=int(data.get("time_limit_minutes") or paper.time_limit_minutes),
        access_code=_generate_access_code(),
    )
    db.session.add(assignment)
    db.session.commit()

    warning = None
    if paper.has_hl_only_questions and class_id and _class_has_sl_student(class_id, level_filter):
        warning = ("This paper includes HL-only questions, and the selected class"
                   + (" is SL" if level_filter == "SL" else " has SL-enrolled students")
                   + " — double check that's intentional before sharing the code.")

    return jsonify({"ok": True, "assignment": _assignment_summary(assignment), "warning": warning})


@test_bp.route("/admin/api/test-assignments/<int:assignment_id>", methods=["DELETE"])
@login_required
@admin_required
def delete_assignment(assignment_id):
    a = TestAssignment.query.get_or_404(assignment_id)
    # Detach rather than cascade-delete: the paper (and any submitted work against it)
    # still exists, only the join-code/assignment link is going away.
    for submission in a.submissions:
        submission.test_assignment_id = None
    db.session.delete(a)
    db.session.commit()
    return jsonify({"ok": True})


@test_bp.route("/admin/api/test-assignments/<int:assignment_id>/regenerate-code", methods=["POST"])
@login_required
@admin_required
def regenerate_code(assignment_id):
    a = TestAssignment.query.get_or_404(assignment_id)
    a.access_code = _generate_access_code()
    db.session.commit()
    return jsonify({"ok": True, "assignment": _assignment_summary(a)})


@test_bp.route("/admin/api/test-assignments/<int:assignment_id>/close", methods=["POST"])
@login_required
@admin_required
def close_assignment(assignment_id):
    """Retire the join code so no further students can enter, while leaving the
    assignment and every submission intact for review.

    This is the manual counterpart to _maybe_close_assignment's automatic path.
    A teacher needs it whenever the automatic rule can't fire — most commonly a
    class whose enrolment is empty or has changed since assigning, where "every
    targeted student has submitted" is never satisfiable.

    Any student still mid-test keeps their session: their submission already
    exists, and take_test/save_answer resolve it by submission id, not by code.
    """
    a = TestAssignment.query.get_or_404(assignment_id)
    if a.access_code is None:
        return jsonify({"ok": False, "error": "This test is already closed."}), 400

    still_working = sum(1 for s in a.submissions if s.status == "in_progress")
    a.access_code = None
    db.session.commit()
    return jsonify({
        "ok": True,
        "still_in_progress": still_working,
        "assignment": _assignment_summary(a),
    })


def _assignment_roster(a):
    """Every student this assignment reaches, cross-referenced with their
    TestSubmission (if any) for that paper — so a teacher sees who hasn't
    even started, not just who has."""
    if a.class_id:
        enroll_query = ClassEnrollment.query.filter_by(class_id=a.class_id)
        if a.level_filter:
            enroll_query = enroll_query.filter_by(level=a.level_filter)
        students = [e.student for e in enroll_query.all()]
    elif a.student_id:
        students = [a.student]
    else:
        students = []
    # Guard against rows pointing at a deleted user — sorting on s.name would
    # otherwise raise and take down every caller of this helper.
    students = [s for s in students if s is not None]
    students.sort(key=lambda s: s.name or "")

    submissions_by_student = {
        s.student_id: s for s in TestSubmission.query.filter_by(test_paper_id=a.test_paper_id).all()
        if s.student_id in {st.id for st in students}
    }

    roster = []
    for student in students:
        submission = submissions_by_student.get(student.id)
        row = {
            "student_id": student.id,
            "student_name": student.name,
            "student_avatar": student.avatar,
            "status": submission.status if submission else "not_started",
            "submission_id": submission.id if submission else None,
            "marks_awarded": submission.total_marks_awarded if submission else None,
            "marks_possible": submission.total_marks_possible if submission else None,
        }
        if submission and submission.total_marks_possible:
            row["percentage"] = round(100 * (submission.total_marks_awarded or 0) / submission.total_marks_possible)
        else:
            row["percentage"] = None
        roster.append(row)
    return roster


def _maybe_close_assignment(assignment):
    """Once every student this assignment targets has submitted, the join code
    is no longer needed — clear it so it can't be reused, while leaving the
    assignment and its results fully intact for later review."""
    if assignment is None or assignment.access_code is None:
        return
    roster = _assignment_roster(assignment)
    if roster and all(r["status"] in ("submitted", "marked") for r in roster):
        assignment.access_code = None
        db.session.commit()


@test_bp.route("/assessment/test-assignments/<int:assignment_id>/results")
@login_required
@admin_required
def assignment_results_page(assignment_id):
    assignment = TestAssignment.query.get_or_404(assignment_id)
    return render_template("test_assignment_results.html", assignment=assignment, paper=assignment.paper)


@test_bp.route("/admin/api/test-assignments/<int:assignment_id>/results")
@login_required
@admin_required
def assignment_results_data(assignment_id):
    assignment = TestAssignment.query.get_or_404(assignment_id)
    roster = _assignment_roster(assignment)
    submitted_scores = [r["percentage"] for r in roster if r["percentage"] is not None]
    avg_percentage = round(sum(submitted_scores) / len(submitted_scores)) if submitted_scores else None
    return jsonify({
        "paper_title": assignment.paper.title,
        "target_label": assignment.target_label(),
        "access_code": assignment.access_code,
        "created_at": assignment.created_at.strftime("%b %d, %Y") if assignment.created_at else None,
        "avg_percentage": avg_percentage,
        "roster": roster,
    })


@test_bp.route("/admin/api/test-assignments/<int:assignment_id>/progress")
@login_required
@admin_required
def assignment_progress(assignment_id):
    """Live per-student, per-question state for one assignment — who has started,
    how far they've got, and who hasn't shown up at all.

    Rosters and submissions are unioned rather than intersected. A student can
    hold a submission without being on the roster (unenrolled after sitting the
    test, or the class emptied), and dropping them would silently hide real work
    from the teacher — which is exactly what made the orphaned live assignment
    look like it had no participants.
    """
    a = TestAssignment.query.get_or_404(assignment_id)
    questions = a.paper.questions

    roster = _assignment_roster(a)
    by_student = {r["student_id"]: dict(r, on_roster=True) for r in roster}

    # A submission can outlive the user row it points at (student deleted after
    # sitting the test), leaving s.student as None. Those are dropped rather than
    # rendered: there's no one left to chase, and dereferencing them crashes the
    # whole panel for every other student in the class.
    submissions = [
        s for s in TestSubmission.query.filter_by(test_paper_id=a.test_paper_id).all()
        if s.student is not None
    ]
    submissions_by_student = {s.student_id: s for s in submissions}

    for student_id, s in submissions_by_student.items():
        if student_id not in by_student:
            by_student[student_id] = {
                "student_id": student_id,
                "student_name": s.student.name,
                "student_avatar": s.student.avatar,
                "status": s.status,
                "submission_id": s.id,
                "marks_awarded": s.total_marks_awarded,
                "marks_possible": s.total_marks_possible,
                "percentage": None,
                "on_roster": False,
            }

    students_payload = []
    for row in by_student.values():
        s = submissions_by_student.get(row["student_id"])
        answered = 0
        per_question = []
        if s:
            answers_by_qid = {ans.question_id: ans for ans in s.answers}
            for q in questions:
                ans = answers_by_qid.get(q.id)
                has_content = bool(
                    ans and (ans.selected_indices() if q.is_mcq() else (ans.response_text or "").strip())
                )
                if has_content:
                    answered += 1
                per_question.append({
                    "question_id": q.id,
                    "text": q.text,
                    "marks": q.marks,
                    "is_mcq": q.is_mcq(),
                    "answered": has_content,
                    "word_count": len((ans.response_text or "").split()) if ans and not q.is_mcq() else 0,
                    # The answer itself, so the hub's progress panel can show what a
                    # student has actually written without a second round-trip per row.
                    "options": q.options_list() if q.is_mcq() else None,
                    "selected_options": ans.selected_indices() if (ans and q.is_mcq()) else [],
                    "response_text": ans.response_text if (ans and not q.is_mcq()) else None,
                })
        students_payload.append({
            **row,
            "is_simulated": bool(s.is_simulated) if s else False,
            "started_at": s.started_at.strftime("%I:%M %p") if s else None,
            "deadline_iso": (s.deadline.isoformat() + "Z") if s and s.status == "in_progress" else None,
            "answered_count": answered,
            "questions": per_question,
        })

    # Not-started first (they need chasing), then in-progress, then done.
    order = {"not_started": 0, "in_progress": 1, "submitted": 2, "marked": 3, "reviewed": 4}
    students_payload.sort(key=lambda r: (order.get(r["status"], 9), r["student_name"] or ""))

    return jsonify({
        "assignment_id": a.id,
        "paper_title": a.paper.title,
        "target_label": a.target_label(),
        "access_code": a.access_code,
        "question_count": len(questions),
        "total_marks": a.paper.total_marks,
        "students": students_payload,
    })


@test_bp.route("/admin/api/test-analytics")
@login_required
@admin_required
def test_analytics():
    """Feeds the Analytics hub's Tests tab: per-student history when a student
    is selected, otherwise a per-paper class-ability summary."""
    class_id = request.args.get("class_id", type=int)
    student_id = request.args.get("student_id", type=int)

    if student_id:
        submissions = (
            TestSubmission.query.filter_by(student_id=student_id)
            .order_by(TestSubmission.started_at.desc()).all()
        )
        rows = []
        for s in submissions:
            percentage = round(100 * (s.total_marks_awarded or 0) / s.total_marks_possible) if s.total_marks_possible and s.total_marks_awarded is not None else None
            rows.append({
                "paper_title": s.paper.title,
                "status": s.status,
                "marks_awarded": s.total_marks_awarded,
                "marks_possible": s.total_marks_possible,
                "percentage": percentage,
                "submitted_at": s.submitted_at.strftime("%b %d, %Y") if s.submitted_at else None,
                "submission_id": s.id,
            })
        return jsonify({"mode": "student", "submissions": rows})

    class_student_ids = None
    if class_id:
        class_student_ids = {e.student_id for e in ClassEnrollment.query.filter_by(class_id=class_id).all()}

    papers_out = []
    for p in TestPaper.query.order_by(TestPaper.updated_at.desc()).all():
        assignments = p.assignments
        if class_id:
            assignments = [a for a in assignments if a.class_id == class_id]
        if not assignments:
            continue
        assigned_count = sum(_assignment_target_count(a) for a in assignments)

        submissions = TestSubmission.query.filter_by(test_paper_id=p.id).all()
        if class_student_ids is not None:
            submissions = [s for s in submissions if s.student_id in class_student_ids]
        submitted = [s for s in submissions if s.status in ("submitted", "marked")]
        percentages = [
            round(100 * (s.total_marks_awarded or 0) / s.total_marks_possible)
            for s in submitted if s.total_marks_possible and s.total_marks_awarded is not None
        ]
        avg_percentage = round(sum(percentages) / len(percentages)) if percentages else None

        papers_out.append({
            "paper_id": p.id,
            "title": p.title,
            "assigned_count": assigned_count,
            "submitted_count": len(submitted),
            "avg_percentage": avg_percentage,
        })
    return jsonify({"mode": "class", "papers": papers_out})


@test_bp.route("/assessment/test-assignments/<int:assignment_id>/present")
@login_required
@admin_required
def present_assignment_code(assignment_id):
    assignment = TestAssignment.query.get_or_404(assignment_id)
    return render_template("test_present.html", assignment=assignment, paper=assignment.paper)


@test_bp.route("/admin/api/test-assignments/<int:assignment_id>/status")
@login_required
@admin_required
def assignment_status(assignment_id):
    assignment = TestAssignment.query.get_or_404(assignment_id)
    joined = len(assignment.submissions)
    in_progress_subs = [s for s in assignment.submissions if s.status == "in_progress"]
    in_progress = len(in_progress_subs)
    finished = joined - in_progress
    # The board's default countdown is anchored to whichever student started
    # first — they're the one whose time actually runs out soonest, which is
    # the moment that matters for pacing the room. Per-student timers (shown
    # on demand, not by default) use each submission's own deadline.
    earliest_deadline_iso = None
    students = []
    if in_progress_subs:
        ordered = sorted(in_progress_subs, key=lambda s: s.deadline)
        earliest_deadline_iso = ordered[0].deadline.isoformat() + "Z"
        # time_limit_minutes rides along so the board can show elapsed-vs-total
        # (a depletion dial), not just an absolute number counting down.
        students = [
            {
                "student_name": s.student.name,
                "student_avatar": s.student.avatar,
                "deadline_iso": s.deadline.isoformat() + "Z",
                "time_limit_minutes": s.time_limit_minutes,
            }
            for s in ordered
        ]
    return jsonify({
        "access_code": assignment.access_code,
        "joined": joined,
        "in_progress": in_progress,
        "finished": finished,
        "earliest_deadline_iso": earliest_deadline_iso,
        "students": students,
    })


@test_bp.route("/admin/api/dev/simulate-test-starts", methods=["POST"])
@login_required
@admin_required
def simulate_test_starts():
    """Dev-only convenience for testing the Present board's per-student timers:
    auto-picks a currently-live assignment and fakes 3 real students starting it
    seconds/minutes apart. Never touches a student who already has a genuine
    submission for that paper, and every row it creates is flagged is_simulated
    so it's always identifiable and safe to clear (see clear_simulated_test_starts)."""
    if not current_app.debug:
        return jsonify({"error": "Not available"}), 404

    # Prefer the most recent live assignment that actually targets more than
    # one student — a stray single-student assignment (e.g. a direct-to-one-
    # student test left live from earlier testing) would otherwise "win" just
    # for being newer, and the simulation would only ever be able to show 1
    # timer no matter how many students exist elsewhere. Fall back to the
    # most recent live assignment of any size if nothing bigger is live.
    live_assignments = (
        TestAssignment.query.filter(TestAssignment.access_code.isnot(None))
        .order_by(TestAssignment.created_at.desc()).all()
    )
    if not live_assignments:
        return jsonify({"error": "No live test found — assign a test with an active code first"}), 400
    assignment = next((a for a in live_assignments if _assignment_target_count(a) > 1), live_assignments[0])

    # Re-running should be idempotent: drop this assignment's previous simulated
    # rows first so the same students are free to be picked again.
    TestSubmission.query.filter_by(test_assignment_id=assignment.id, is_simulated=True).delete()

    roster = _assignment_roster(assignment)
    eligible = [r for r in roster if r["status"] == "not_started"]
    if not eligible:
        return jsonify({"error": "Everyone this test reaches already has a real submission — nothing left to simulate"}), 400

    picked = eligible[:3]
    stagger_seconds = [0, 45, 150]  # "slightly different" start times
    now = datetime.utcnow()
    created = []
    for row, offset in zip(picked, stagger_seconds):
        submission = TestSubmission(
            test_paper_id=assignment.test_paper_id,
            test_assignment_id=assignment.id,
            student_id=row["student_id"],
            started_at=now - timedelta(seconds=offset),
            time_limit_minutes=assignment.time_limit_minutes,
            total_marks_possible=assignment.paper.total_marks,
            is_simulated=True,
        )
        db.session.add(submission)
        created.append({"student_name": row["student_name"], "started_seconds_ago": offset})
    db.session.commit()

    return jsonify({
        "ok": True,
        "assignment_id": assignment.id,
        "paper_title": assignment.paper.title,
        "present_url": f"/assessment/test-assignments/{assignment.id}/present",
        "students": created,
    })


@test_bp.route("/admin/api/dev/clear-simulated-test-starts", methods=["POST"])
@login_required
@admin_required
def clear_simulated_test_starts():
    """Removes every simulated submission app-wide — real student data is
    never touched since only is_simulated=True rows are ever deleted here."""
    if not current_app.debug:
        return jsonify({"error": "Not available"}), 404
    deleted = TestSubmission.query.filter_by(is_simulated=True).delete()
    db.session.commit()
    return jsonify({"ok": True, "deleted": deleted})


@test_bp.route("/admin/api/assessment/live-tests")
@login_required
@admin_required
def live_tests():
    """Every assignment that's still live (has an active join code) — feeds the
    always-visible teacher banner and the Assessment hub's Live now section."""
    assignments = (
        TestAssignment.query.filter(TestAssignment.access_code.isnot(None))
        .order_by(TestAssignment.created_at.desc()).all()
    )
    out = []
    for a in assignments:
        # A zero-target assignment (class emptied or never enrolled) is still shown.
        # Hiding it was how a live test became unclosable: invisible here, and
        # _maybe_close_assignment can't auto-retire it either, so its code stayed
        # valid forever with no surface offering a Close button.
        assigned_count = _assignment_target_count(a)
        in_progress_subs = [s for s in a.submissions if s.status == "in_progress"]
        finished_count = sum(1 for s in a.submissions if s.status in ("submitted", "marked"))
        latest_deadline_iso = None
        if in_progress_subs:
            latest_deadline_iso = max(s.deadline for s in in_progress_subs).isoformat() + "Z"
        out.append({
            "assignment_id": a.id,
            "test_paper_id": a.test_paper_id,
            "paper_title": a.paper.title,
            "target_label": a.target_label(),
            "access_code": a.access_code,
            "assigned_count": assigned_count,
            "in_progress_count": len(in_progress_subs),
            "finished_count": finished_count,
            "latest_deadline_iso": latest_deadline_iso,
        })
    return jsonify({"live_tests": out})


# ---------------------------------------------------------------- student: join by code

@test_bp.route("/api/assessment/my-status")
@login_required
def my_test_status():
    """Tests currently relevant to the logged-in student — assigned to them
    directly or to a class they're enrolled in — so they can see a test is
    waiting without already knowing a code. The code is still required to
    actually start; this only surfaces that one exists (or lets them resume
    one already in progress)."""
    if current_user.is_admin():
        return jsonify({"tests": []})

    class_ids = [e.class_id for e in ClassEnrollment.query.filter_by(student_id=current_user.id).all()]
    conditions = [TestAssignment.student_id == current_user.id]
    if class_ids:
        conditions.append(TestAssignment.class_id.in_(class_ids))
    assignments = (
        TestAssignment.query.filter(db.or_(*conditions))
        .order_by(TestAssignment.created_at.desc())
        .all()
    )

    tests = []
    seen_papers = set()
    for a in assignments:
        if a.test_paper_id in seen_papers:
            continue  # same paper reachable two ways (direct + class) — show once
        seen_papers.add(a.test_paper_id)
        submission = TestSubmission.query.filter_by(
            test_paper_id=a.test_paper_id, student_id=current_user.id
        ).first()
        if submission and submission.status != "in_progress":
            continue  # already finished — nothing to surface
        tests.append({
            "paper_title": a.paper.title,
            "in_progress": submission is not None,
            "submission_id": submission.id if submission else None,
        })
    return jsonify({"tests": tests})


@test_bp.route("/api/assessment/join", methods=["POST"])
@login_required
def join_by_code():
    if current_user.is_admin():
        return jsonify({"error": "Admins can't take tests"}), 403

    data = request.get_json(force=True, silent=True) or {}
    code = (data.get("code") or "").strip().upper()
    if not code:
        return jsonify({"error": "Please enter a code"}), 400

    assignment = TestAssignment.query.filter_by(access_code=code).first()
    if not assignment:
        return jsonify({"error": "That code doesn't match any test. Double-check and try again."}), 404

    # Eligibility: assigned directly, or enrolled in the assigned class at the
    # matching HL/SL level (if the assignment was narrowed to one level).
    eligible = False
    if assignment.student_id:
        eligible = assignment.student_id == current_user.id
    elif assignment.class_id:
        enrollment = ClassEnrollment.query.filter_by(
            class_id=assignment.class_id, student_id=current_user.id
        ).first()
        eligible = enrollment is not None and (
            not assignment.level_filter or enrollment.level == assignment.level_filter
        )
    if not eligible:
        return jsonify({"error": "This code isn't assigned to you. Check with your teacher."}), 403

    existing = TestSubmission.query.filter_by(
        test_paper_id=assignment.test_paper_id, student_id=current_user.id
    ).first()
    if existing:
        if existing.status != "in_progress":
            return jsonify({"error": "You've already completed this test — it can only be taken once."}), 409
        # Resume an in-progress attempt rather than starting a new one.
        return jsonify({"ok": True, "redirect": f"/assessment/test/{existing.id}/take"})

    submission = TestSubmission(
        test_paper_id=assignment.test_paper_id,
        test_assignment_id=assignment.id,
        student_id=current_user.id,
        time_limit_minutes=assignment.time_limit_minutes,
        total_marks_possible=assignment.paper.total_marks,
    )
    db.session.add(submission)
    db.session.commit()
    return jsonify({"ok": True, "redirect": f"/assessment/test/{submission.id}/take"})


# ---------------------------------------------------------------- taking the test

def _mcq_feedback(question, is_correct, selected):
    """The line a student reads under an MCQ, built from the workbook's answer
    columns rather than from a model call — MCQ marking is deterministic, so its
    feedback should be too.

    Always names the option the student actually chose: "the correct answer was
    X" on its own leaves them to work out what they picked and why it was wrong,
    which is the whole job of the workbook's "If wrong explainer"."""
    options = question.options_list()

    def label(indices):
        return ", ".join(options[i] for i in indices if 0 <= i < len(options))

    correct_text = label(question.correct_indices())
    chosen_text = label(sorted(selected))

    if is_correct:
        # The workbook's marking guidance is teacher-facing ("Award 1 mark for
        # ..."), so it isn't reused here — just confirm the answer.
        return f"Correct — {correct_text}." if correct_text else "Correct."

    parts = [f"You chose {chosen_text}." if chosen_text else "No answer was selected."]
    explainer = question.if_wrong_explainer or question.common_mistakes
    # The workbook's explainer already opens with "Correct: <letter>: <option>",
    # so naming the right answer again here would just repeat it back.
    if not explainer and correct_text:
        parts.append(f"The correct answer was {correct_text}.")
    if explainer:
        parts.append(explainer)
    return " ".join(parts)


def _mark_mcq_answers(submission):
    """Instant, deterministic MCQ marking. Written answers are left for Phase 5's
    AI marking pass — this only ever touches question_type == 'mcq' rows."""
    for answer in submission.answers:
        if not answer.question.is_mcq():
            continue
        correct = set(answer.question.correct_indices())
        selected = set(answer.selected_indices())
        is_correct = bool(correct) and correct == selected
        answer.auto_correct = is_correct
        answer.marks_awarded = answer.question.marks if is_correct else 0
        answer.ai_feedback = _mcq_feedback(answer.question, is_correct, selected)
        answer.status = "reviewed"


def _backfill_skipped_answers(submission):
    """A question the student never touched at all gets no TestAnswer row from
    save_answer — which means marking never runs on it and the report has
    nothing to show. Create a blank row for each so marking (and its
    mark-scheme-based feedback) covers every question, MCQ and written alike,
    not just the ones typed into and cleared."""
    answered_qids = {a.question_id for a in submission.answers}
    for question in submission.paper.questions:
        if question.id not in answered_qids:
            db.session.add(TestAnswer(
                submission_id=submission.id,
                question_id=question.id,
                response_text="" if not question.is_mcq() else None,
            ))
    db.session.commit()


def _finalize_submission(submission):
    if submission.status != "in_progress":
        return
    # Backfill first: rows created here still need MCQ marking and feedback.
    _backfill_skipped_answers(submission)
    _mark_mcq_answers(submission)
    submission.submitted_at = datetime.utcnow()
    # Recorded here rather than derived on read. Clamped to the time limit so an
    # auto-submit that fires late (tab asleep, slow marking queue) still reports
    # the time the student actually had, not the wall-clock gap.
    elapsed = int((submission.submitted_at - submission.started_at).total_seconds())
    submission.time_taken_seconds = max(0, min(elapsed, submission.time_limit_minutes * 60))
    submission.status = "submitted"
    db.session.commit()

    from test_marking import mark_submission
    mark_submission(submission)

    _maybe_close_assignment(submission.assignment)


@test_bp.route("/assessment/test/<int:submission_id>/take")
@login_required
def take_test(submission_id):
    submission = TestSubmission.query.get_or_404(submission_id)
    if submission.student_id != current_user.id:
        return "Not found", 404

    if submission.status == "in_progress" and submission.is_overdue:
        _finalize_submission(submission)

    paper = submission.paper
    questions = paper.questions
    answers_by_qid = {a.question_id: a for a in submission.answers}

    questions_payload = []
    for q in questions:
        a = answers_by_qid.get(q.id)
        questions_payload.append({
            "id": q.id,
            "subtopic_title": q.subtopic_title,
            "is_hl_only": q.is_hl_only,
            "question_type": q.question_type,
            "text": q.text,
            "options": q.options_list(),
            "marks": q.marks,
            "response_text": a.response_text if a else "",
            "selected_options": a.selected_indices() if a else [],
            "icon_name": q.icon_name,
            "icon_source_url": q.icon_source_url,
        })

    pending_count = sum(1 for a in submission.answers if a.status != "reviewed")

    return render_template(
        "test_take.html",
        submission=submission,
        paper=paper,
        questions_json=questions_payload,
        deadline_iso=submission.deadline.isoformat() + "Z",
        is_in_progress=(submission.status == "in_progress"),
        pending_count=pending_count,
    )


@test_bp.route("/api/assessment/test/<int:submission_id>/answer", methods=["POST"])
@login_required
def save_answer(submission_id):
    submission = TestSubmission.query.get_or_404(submission_id)
    if submission.student_id != current_user.id:
        return jsonify({"error": "Not found"}), 404
    if submission.status != "in_progress":
        return jsonify({"error": "This test has already been submitted"}), 409
    if submission.is_overdue:
        _finalize_submission(submission)
        return jsonify({"error": "Time's up — this test has been auto-submitted"}), 409

    data = request.get_json(force=True, silent=True) or {}
    question_id = data.get("question_id")
    question = TestQuestion.query.get(question_id)
    if not question or question not in submission.paper.questions:
        return jsonify({"error": "Question not in this test"}), 400

    answer = TestAnswer.query.filter_by(submission_id=submission.id, question_id=question_id).first()
    if not answer:
        answer = TestAnswer(submission_id=submission.id, question_id=question_id)
        db.session.add(answer)

    if question.is_mcq():
        answer.selected_options = json.dumps(data.get("selected_options") or [])
    else:
        answer.response_text = data.get("response_text") or ""
    answer.submitted_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"ok": True})


@test_bp.route("/api/assessment/test/<int:submission_id>/submit", methods=["POST"])
@login_required
def submit_test(submission_id):
    submission = TestSubmission.query.get_or_404(submission_id)
    if submission.student_id != current_user.id:
        return jsonify({"error": "Not found"}), 404
    if submission.status != "in_progress":
        return jsonify({"error": "This test has already been submitted"}), 409

    _finalize_submission(submission)
    return jsonify({"ok": True, "redirect": f"/assessment/test/{submission.id}/take"})


# ---------------------------------------------------------------- teacher: written-answer review queue

@test_bp.route("/admin/test-review")
@login_required
@admin_required
def test_review_page():
    return render_template("admin_test_review.html")


@test_bp.route("/admin/api/test-review")
@login_required
@admin_required
def test_review_list():
    status = request.args.get("status", "pending")
    class_id = request.args.get("class_id", type=int)
    student_id = request.args.get("student_id", type=int)

    query = (
        TestAnswer.query
        .join(TestQuestion, TestAnswer.question_id == TestQuestion.id)
        .filter(TestQuestion.question_type == "written")
        .join(TestSubmission, TestAnswer.submission_id == TestSubmission.id)
        .join(User, TestSubmission.student_id == User.id)
    )
    if status in ("pending", "reviewed"):
        query = query.filter(TestAnswer.status == status)
    if student_id:
        query = query.filter(TestSubmission.student_id == student_id)
    elif class_id:
        query = query.join(
            ClassEnrollment, ClassEnrollment.student_id == TestSubmission.student_id
        ).filter(ClassEnrollment.class_id == class_id)

    rows = query.order_by(
        db.case((TestAnswer.confidence.is_(None), 0), else_=TestAnswer.confidence).asc(),
        TestAnswer.submitted_at.desc(),
    ).limit(500).all()

    return jsonify({"answers": [{
        "answer_id": a.id,
        "student": a.submission.student.name,
        "paper_title": a.submission.paper.title,
        "subtopic_title": a.question.subtopic_title,
        "question": a.question.text,
        "marks": a.question.marks,
        "marking_guidance": a.question.marking_guidance,
        "common_mistakes": a.question.common_mistakes,
        "answer_text": a.response_text,
        "marks_awarded": a.marks_awarded,
        "ai_feedback": a.ai_feedback,
        "confidence": a.confidence,
        "status": a.status,
        "submitted_at": a.submitted_at.strftime("%Y-%m-%d %H:%M") if a.submitted_at else "",
    } for a in rows]})


@test_bp.route("/admin/api/test-review/<int:answer_id>", methods=["POST"])
@login_required
@admin_required
def test_review_mark(answer_id):
    answer = TestAnswer.query.get_or_404(answer_id)
    data = request.get_json(force=True, silent=True) or {}
    marks_awarded = data.get("marks_awarded")
    feedback = (data.get("feedback") or "").strip()

    # Halves are legitimate now that MCQs are worth 0.5, so this takes any number in
    # range rather than insisting on an int.
    max_marks = answer.question.marks
    if (
        not isinstance(marks_awarded, (int, float))
        or isinstance(marks_awarded, bool)
        or marks_awarded < 0
        or marks_awarded > max_marks
    ):
        return jsonify({"error": f"marks_awarded must be a number from 0 to {format_marks(max_marks)}"}), 400

    answer.marks_awarded = float(marks_awarded)
    if feedback:
        answer.ai_feedback = feedback
    answer.status = "reviewed"
    answer.reviewed_by_id = current_user.id
    answer.reviewed_at = datetime.utcnow()
    db.session.commit()

    from test_marking import maybe_finalize_submission
    maybe_finalize_submission(answer.submission)

    return jsonify({"ok": True})


# ---------------------------------------------------------------- test-scoped report

def _format_duration(seconds):
    """"3 min 18 s" / "48 min" / "1 hr 12 min" — precise without being fussy."""
    if seconds is None:
        return None
    if seconds < 60:
        return f"{seconds} s"
    minutes, secs = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours} hr {minutes} min" if minutes else f"{hours} hr"
    # Seconds only matter on short attempts; past an hour they are noise.
    return f"{minutes} min {secs} s" if secs else f"{minutes} min"


_BARE_CODE_RE = re.compile(r"^[A-Z]\d(?:\.\d+){0,2}$")


def _presentable_paper_title(raw_title, subtopic_list):
    """Papers are often named after the subtopic code they were built from, so the
    report header reads "A1.1.1" and tells the reader nothing. When the title is
    nothing but a code, pair it with the subtopic's actual name."""
    title = (raw_title or "").strip()
    if not _BARE_CODE_RE.match(title):
        return title
    match = next(
        (s for s in subtopic_list if s.get("subtopic_code") == title),
        subtopic_list[0] if len(subtopic_list) == 1 else None,
    )
    if match and match.get("subtopic_title"):
        return f"{title} — {match['subtopic_title']}"
    return title


def _summarise_assessment_focus(subtopic_list):
    """One short paragraph saying what the paper actually assessed, built from the
    workbook's subtopic descriptors.

    Deliberately deterministic rather than an AI call: the descriptors are already
    written prose, so summarising them is arrangement, not generation — and a
    report export should not depend on (or pay for) a model round-trip.

    Descriptors repeat across related subtopics in the workbook, so they are
    de-duplicated; without that, a four-subtopic paper reads as the same sentence
    four times."""
    if not subtopic_list:
        return None

    titles = [s["subtopic_title"] for s in subtopic_list if s.get("subtopic_title")]
    seen, lines = set(), []
    for entry in subtopic_list:
        text = (entry.get("descriptor") or "").strip()
        if text and text not in seen:
            seen.add(text)
            lines.append(text)

    if len(titles) == 1:
        # The header already names the single subtopic, so restating it here just
        # reads as duplication — lead straight with what it covers.
        lead = None
    elif titles:
        lead = (
            f"This paper assessed {len(titles)} subtopics: "
            + "; ".join(titles[:-1]) + f"; and {titles[-1]}."
        )
    else:
        lead = None

    parts = [p for p in ([lead] + lines) if p]
    return " ".join(parts) or None


def _strength_lines(strong_subtopics):
    """Turn each strong subtopic into a sentence saying what the student is
    confident *at*, using the workbook descriptor rather than the bare syllabus
    title — "82% in A1.1.1" tells a student nothing they can act on, whereas the
    descriptor names the actual capability. Falls back to the title when the
    descriptor is missing (older workbooks)."""
    lines = []
    for s in strong_subtopics:
        label = f"{s['subtopic_title']} ({s['percentage']}%)"
        descriptor = (s.get("descriptor") or "").strip()
        # Appended verbatim rather than reworded into a "confident with ..."
        # clause: the descriptors are already written prose and start with a
        # verb ("Covers ...", "Introduces ..."), so splicing them mid-sentence
        # reads badly.
        lines.append(f"{label} — {descriptor}" if descriptor else label)
    return lines


_NARRATIVE_SCHEMA = {
    "type": "object",
    "properties": {
        "what_you_did_well": {"type": "string"},
        "strengths": {"type": "array", "items": {"type": "string"}},
        "where_to_go_next": {"type": "string"},
        "revision_steps": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["what_you_did_well", "strengths", "where_to_go_next", "revision_steps"],
    "additionalProperties": False,
}


def _build_narrative_prompt(stats):
    """Everything the model needs to write about *this* paper specifically.

    The question-level detail matters more than the totals: a report that says
    "revise processor components" is the same sentence every low scorer gets,
    whereas one that names the definition they half-remembered is worth reading."""
    lines = [
        f"Student: {stats['student_name']}",
        f"Paper: {stats['paper_title']}",
        f"Score: {format_marks(stats['total_marks_awarded'])}/"
        f"{format_marks(stats['total_marks_possible'])} ({stats['percentage']}%)",
    ]
    if stats.get("assessment_focus"):
        lines.append(f"What the paper covered: {stats['assessment_focus']}")

    lines.append("\nSubtopic breakdown:")
    for s in stats["subtopics"]:
        lines.append(
            f"- {s['subtopic_title']}: {format_marks(s['marks_awarded'])}/"
            f"{format_marks(s['marks_possible'])} ({s['percentage']}%)"
            + (f" — {s['descriptor']}" if s.get("descriptor") else "")
        )

    lines.append("\nQuestion by question:")
    for s in stats["subtopics"]:
        for q in s["questions"]:
            lines.append(
                f"- [{s['subtopic_title']}] {q['text']}\n"
                f"  Marks: {format_marks(q['marks_awarded'])}/{format_marks(q['marks'])}\n"
                f"  Their answer: {q['student_answer'][:400]}"
                + (f"\n  Marker feedback: {q['ai_feedback']}" if q.get("ai_feedback") else "")
                + (f"\n  Common mistake on this question: {q['common_mistakes']}" if q.get("common_mistakes") else "")
            )

    lines.append("""
You are the student's teacher, writing the closing comments on their test report.
They will read this themselves, so write to them as "you". Be warm, specific and
honest — encouraging without pretending they did better than they did.

- what_you_did_well: one paragraph of 4-5 sentences. Find the real evidence of
  understanding in what they wrote, even if the score is low: partial marks,
  correct terminology, a right idea expressed loosely, a question they clearly
  reasoned through, sitting the whole paper. Name the actual questions and
  answers. Never say there was nothing to praise, and never open by referring to
  the score.
- strengths: 2-4 items, one sentence each, naming a specific thing they can do
  and the evidence for it from this paper.
- where_to_go_next: one flowing paragraph of 4-6 sentences — NOT a list — that
  explains what to revise and why those particular things are the ones that will
  move the score. Say what the gap actually is (a definition not yet secure, a
  role confused with another, detail missing from an explanation), connect the
  gaps to each other where they share a root cause, and end with a confident,
  concrete sentence about what improvement will look like next time.
- revision_steps: 2-4 items, one sentence each, each a specific action they can
  do this week ("write out what the ALU does in your own words, then check it
  against page X"), not a topic name.

Never use the words "weak", "failed", "poor", or "needs support".""")
    return "\n".join(lines)


def _fallback_narrative(stats):
    """Used when the model is unavailable. Deterministic, but still written from
    what the student actually earned — the point of this section is that a
    struggling student is never handed an empty or discouraging report."""
    pct = stats["percentage"]
    attempted = sum(
        1 for s in stats["subtopics"] for q in s["questions"]
        if q["student_answer"] != "No answer provided"
    )
    total_q = sum(len(s["questions"]) for s in stats["subtopics"])
    scoring = [s for s in stats["subtopics"] if s["marks_awarded"] > 0]
    best = max(stats["subtopics"], key=lambda s: s["percentage"], default=None)

    well = [f"You sat the whole paper and gave {attempted} of {total_q} questions a go, which is the part that makes the rest of this useful."]
    if scoring:
        well.append(
            "You picked up marks in " + ", ".join(s["subtopic_title"] for s in scoring)
            + ", so those ideas are already starting to land."
        )
    # Only meaningful when there is something to be strongest *among* — on a
    # single-subtopic paper it just restates the overall score.
    if best and best["percentage"] > 0 and len(stats["subtopics"]) > 1:
        well.append(f"Your strongest area here was {best['subtopic_title']} at {best['percentage']}%.")
    well.append("Everything below is about turning what you have started into marks.")

    focus = [s["subtopic_title"] for s in stats["weak_subtopics"]] or \
            [s["subtopic_title"] for s in stats["subtopics"]]
    nxt = (
        f"The clearest way forward is {focus[0]}"
        + (f", followed by {' and '.join(focus[1:3])}" if len(focus) > 1 else "")
        + ". Most of the marks that got away went on detail rather than on the whole idea, "
        "so the aim is not to learn these topics again from scratch but to say them more "
        "precisely — what each part is, what it does, and how it connects to the others. "
        "Work through them one at a time, writing your own definition first and only then "
        "checking it, so you find out what you actually know rather than what you recognise. "
        f"At {pct}% there is plenty of room to move, and this is exactly the kind of gap that "
        "closes quickly with a few focused sessions."
    )

    return {
        "what_you_did_well": " ".join(well),
        "strengths": stats["strength_lines"] or [
            f"You are attempting questions across every subtopic on the paper, including {best['subtopic_title']}."
            if best else "You attempted the paper in full."
        ],
        "where_to_go_next": nxt,
        "revision_steps": stats["recommendations"][:4] or [
            f"Write your own one-sentence definition for each key term in {t}, then check it against your notes."
            for t in focus[:3]
        ],
    }


def _narrative_fingerprint(stats):
    """Marks-derived cache key, so re-marking an answer rewrites the prose but
    simply reopening the report does not."""
    import hashlib
    payload = json.dumps([
        stats["total_marks_awarded"], stats["total_marks_possible"],
        [[q["marks_awarded"], q["is_provisional"]] for s in stats["subtopics"] for q in s["questions"]],
    ], sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


def _report_narrative(submission, stats):
    """Cached-or-generated closing comments for the report."""
    import os

    key = _narrative_fingerprint(stats)
    if submission.report_narrative and submission.report_narrative_key == key:
        try:
            return json.loads(submission.report_narrative)
        except json.JSONDecodeError:
            pass  # Corrupt cache: fall through and regenerate.

    narrative = None
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        try:
            import anthropic
            message = anthropic.Anthropic(api_key=api_key).messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=2048,
                output_config={"format": {"type": "json_schema", "schema": _NARRATIVE_SCHEMA}},
                messages=[{"role": "user", "content": _build_narrative_prompt(stats)}],
            )
            text = next((b.text for b in message.content if b.type == "text"), "")
            narrative = json.loads(text)
        except Exception as e:
            current_app.logger.warning("Test report narrative generation failed: %s", e)
            narrative = None

    if not narrative:
        # Not cached: a fallback written because the model was unavailable should
        # be replaced by the real thing on the next view, not frozen in.
        return _fallback_narrative(stats)

    submission.report_narrative = json.dumps(narrative)
    submission.report_narrative_key = key
    db.session.commit()
    return narrative


def _get_test_submission_stats(submission):
    """Roll one submission's TestAnswers up by subtopic. Skipped questions get a
    blank row backfilled at submit time (see _backfill_skipped_answers) so they
    still carry mark-scheme-based feedback rather than nothing at all."""
    answers_by_qid = {a.question_id: a for a in submission.answers}

    subtopics = {}
    for question in submission.paper.questions:
        code = question.subtopic_code
        if code not in subtopics:
            subtopics[code] = {
                "subtopic_code": code,
                "subtopic_title": question.subtopic_title,
                "marks_awarded": 0,
                "marks_possible": 0,
                "questions": [],
            }
        entry = subtopics[code]
        answer = answers_by_qid.get(question.id)
        marks_awarded = (answer.marks_awarded if answer else 0) or 0
        entry["marks_possible"] += question.marks
        entry["marks_awarded"] += marks_awarded

        if question.is_mcq():
            options = question.options_list()
            selected = answer.selected_indices() if answer else []
            student_answer = ", ".join(options[i] for i in selected if 0 <= i < len(options)) or "No answer provided"
            is_correct = answer.auto_correct if answer else False
            is_provisional = False
        else:
            student_answer = (answer.response_text if answer else "") or "No answer provided"
            is_correct = None
            is_provisional = bool(answer and answer.status != "reviewed")

        entry["questions"].append({
            "answer_id": answer.id if answer else None,
            "text": question.text,
            "marks": question.marks,
            "marks_awarded": marks_awarded,
            "is_mcq": question.is_mcq(),
            "common_mistakes": question.common_mistakes,
            "ai_feedback": answer.ai_feedback if answer else None,
            "student_answer": student_answer,
            "is_correct": is_correct,
            "is_provisional": is_provisional,
        })

    for entry in subtopics.values():
        entry["percentage"] = (
            round(100 * entry["marks_awarded"] / entry["marks_possible"]) if entry["marks_possible"] else 0
        )

    subtopic_list = list(subtopics.values())
    strong = [s for s in subtopic_list if s["marks_possible"] and s["percentage"] >= 80]
    weak = [s for s in subtopic_list if s["marks_possible"] and s["percentage"] < 60]

    recommendations = []
    seen_notes = set()
    for entry in weak:
        for q in entry["questions"]:
            if q["marks_awarded"] < q["marks"] and q["common_mistakes"] and q["common_mistakes"] not in seen_notes:
                seen_notes.add(q["common_mistakes"])
                recommendations.append(f"{entry['subtopic_title']}: {q['common_mistakes']}")

    total_possible = submission.total_marks_possible or 0
    total_awarded = submission.total_marks_awarded or 0
    percentage = round(100 * total_awarded / total_possible) if total_possible else 0
    pending_count = sum(1 for a in submission.answers if a.status != "reviewed")

    # Duration comes from the stored value now, falling back to the timestamps
    # for rows written before the column existed.
    time_taken_seconds = submission.time_taken_seconds_effective
    time_taken_minutes = (
        round(time_taken_seconds / 60) if time_taken_seconds is not None else None
    )

    # Descriptors are keyed by subtopic code and imported from the workbook's
    # "Subtopic Descriptors" sheet; absent until the bank is re-imported, in
    # which case the report simply falls back to the subtopic titles.
    codes = [s["subtopic_code"] for s in subtopic_list]
    descriptors = {
        d.code: d for d in
        SubtopicDescriptor.query.filter(SubtopicDescriptor.code.in_(codes)).all()
    } if codes else {}
    for entry in subtopic_list:
        found = descriptors.get(entry["subtopic_code"])
        entry["descriptor"] = found.descriptor if found else None

    stats = {
        "submission_id": submission.id,
        "student_name": submission.student.name,
        "student_avatar": submission.student.avatar,
        "paper_title": _presentable_paper_title(submission.paper.title, subtopic_list),
        "paper_description": submission.paper.description,
        "assessment_focus": _summarise_assessment_focus(subtopic_list),
        "time_taken_seconds": time_taken_seconds,
        "total_marks_awarded": total_awarded,
        "total_marks_possible": total_possible,
        "percentage": percentage,
        "subtopics": subtopic_list,
        "strong_subtopics": strong,
        "strength_lines": _strength_lines(strong),
        "weak_subtopics": weak,
        "recommendations": recommendations,
        "submitted_at": submission.submitted_at,
        "time_taken_minutes": time_taken_minutes,
        "time_limit_minutes": submission.time_limit_minutes,
        "is_preliminary": submission.status != "marked",
        "pending_count": pending_count,
    }

    # Written last, because the narrative is generated from the finished stats.
    stats["narrative"] = _report_narrative(submission, stats)
    return stats


def _render_test_report_html(stats, editable=False, pdf_url=None):
    """Renders the report body. `pdf_url` adds the on-screen export toolbar and is
    passed only by the view route — the PDF generator calls this without it, so the
    toolbar can never end up inside the exported document."""
    from report_card_routes import _get_performance_level

    esc = html.escape
    level = _get_performance_level(stats["percentage"])
    date_str = stats["submitted_at"].strftime("%d %B %Y") if stats["submitted_at"] else ""
    duration_str = _format_duration(stats.get("time_taken_seconds"))

    subtopic_rows = "".join(f"""
        <div class="subtopic-row">
            <div class="subtopic-name">{esc(s['subtopic_title'])}</div>
            <div class="subtopic-bar-track"><div class="subtopic-bar-fill {_get_performance_level(s['percentage'])['color']}" style="width:{s['percentage']}%;"></div></div>
            <div class="subtopic-score">{format_marks(s['marks_awarded'])}/{format_marks(s['marks_possible'])}</div>
        </div>
    """ for s in stats["subtopics"])

    # The narrative paragraphs carry the message; these lists are the evidence
    # under them. The AI's own strengths/steps are preferred over the raw
    # subtopic and common-mistake lines because they are written about this
    # student's answers rather than about the paper.
    narrative = stats.get("narrative") or _fallback_narrative(stats)

    strengths_html = "".join(
        f"<li class='achievement-item'>{_icon('check', 14)}<span>{esc(line)}</span></li>"
        for line in (narrative.get("strengths") or stats["strength_lines"])
    )

    revision_html = "".join(
        f"<li class='growth-item'>{_icon('arrow', 14)}<span>{esc(r)}</span></li>"
        for r in (narrative.get("revision_steps") or stats["recommendations"])
    )

    def render_question(q):
        if q["is_mcq"]:
            result_tag = (
                f'<span class="q-tag correct">{_icon("check", 13)} Correct</span>' if q["is_correct"]
                else f'<span class="q-tag incorrect">{_icon("cross", 13)} Not awarded</span>'
            )
        else:
            result_tag = (
                f'<span class="q-tag provisional">{_icon("clock", 13)} Provisional — awaiting teacher approval</span>'
                if q["is_provisional"] else ""
            )
        feedback_html = (
            f'<div class="q-feedback">{_icon("comment", 14)}<span>{esc(q["ai_feedback"])}</span></div>'
            if q.get("ai_feedback") else ""
        )
        marks_max = format_marks(q["marks"])
        marks_got = format_marks(q["marks_awarded"])
        marks_label = f"{marks_got}/{marks_max} mark{'s' if q['marks'] != 1 else ''}"
        if editable and q["answer_id"]:
            marks_html = f"""
            <div class="q-marks" data-answer-id="{q['answer_id']}" data-max="{marks_max}">
                <span class="q-marks-display">{marks_label}</span>
                <button type="button" class="q-edit-btn" onclick="qStartEdit(this)">{_icon("edit", 12)} Edit</button>
                <span class="q-marks-edit" style="display:none;">
                    <input type="number" step="0.5" class="q-marks-input" min="0" max="{marks_max}" value="{marks_got}">
                    <button type="button" class="q-save-btn" onclick="qSaveMarks(this)">Save</button>
                    <button type="button" class="q-cancel-btn" onclick="qCancelEdit(this)" aria-label="Cancel">{_icon("cross", 12)}</button>
                </span>
            </div>"""
        else:
            marks_html = f'<div class="q-marks">{marks_label}</div>'
        return f"""
        <div class="q-block">
            <div class="q-head">
                <div class="q-text">{esc(q['text'])}</div>
                {marks_html}
            </div>
            <div class="q-answer-label">Answer given:</div>
            <div class="q-answer">{esc(q['student_answer'])}</div>
            {result_tag}
            {feedback_html}
        </div>"""

    questions_html = "".join(f"""
        <div class="subtopic-questions">
            <h3 class="subtopic-questions-title">{esc(s['subtopic_title'])}</h3>
            {"".join(render_question(q) for q in s['questions'])}
        </div>
    """ for s in stats["subtopics"])

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Test Report - {stats['student_name']}</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #333; line-height: 1.6; }}
            .report-container {{ max-width: 8.5in; margin: 0 auto; padding: 0.5in; }}
            /* Title block: a document masthead rather than a bare name. The
               eyebrow says what this is, the student leads (these get filed
               per student), the paper is named properly underneath, and the
               facts that were previously buried in the score card — when it
               was sat, how long it took — sit in a scannable meta row. */
            .report-header {{ margin-bottom: 1.5rem; padding-bottom: 1rem; border-bottom: 3px solid #e3f2fd; }}
            .report-eyebrow {{
                font-size: 8pt; font-weight: 700; letter-spacing: 0.16em;
                text-transform: uppercase; color: #8366e8; margin-bottom: 0.35rem;
            }}
            .student-name-large {{ font-size: 24pt; font-weight: 700; margin: 0 0 0.1rem 0; color: #333; }}
            .paper-title {{ font-size: 13pt; font-weight: 600; color: #444; margin: 0; }}
            .paper-subtitle {{ font-size: 10.5pt; color: #666; margin: 0.15rem 0 0 0; }}
            .report-meta {{
                display: flex; flex-wrap: wrap; gap: 0.4rem 1.4rem;
                margin-top: 0.75rem; font-size: 9pt; color: #777;
            }}
            .report-meta b {{ color: #333; font-weight: 600; }}
            .report-date {{ font-size: 10pt; color: #999; }}
            /* Assessment focus: what the paper actually covered, so the report
               stands on its own when it leaves the app as a PDF. */
            .focus-box {{
                background: #f8f9fa; border: 1px solid #e9ecef; border-radius: 4px;
                padding: 0.85rem 1rem; margin-bottom: 1.5rem;
                font-size: 10pt; line-height: 1.65; color: #444;
            }}
            .focus-label {{
                font-size: 8pt; font-weight: 700; letter-spacing: 0.1em;
                text-transform: uppercase; color: #888; margin-bottom: 0.35rem;
            }}
            .score-card {{ display: flex; align-items: center; gap: 1.5rem; border: 2px solid #e0e0e0; border-radius: 8px; padding: 1.25rem; margin-bottom: 1.5rem; page-break-inside: avoid; }}
            .score-card.success {{ border-left: 6px solid #4CAF50; }}
            .score-card.info {{ border-left: 6px solid #2196F3; }}
            .score-card.warning {{ border-left: 6px solid #FF9800; }}
            .score-card.danger {{ border-left: 6px solid #f44336; }}
            .score-value {{ font-size: 32pt; font-weight: 700; }}
            .score-value.success {{ color: #4CAF50; }} .score-value.info {{ color: #2196F3; }}
            .score-value.warning {{ color: #FF9800; }} .score-value.danger {{ color: #f44336; }}
            .score-meta {{ font-size: 10pt; color: #666; }}
            .score-level {{ font-size: 12pt; font-weight: 700; margin-bottom: 0.2rem; }}
            /* No page-break-inside here: a section holds every question and is
               routinely taller than a page, so "avoid" just pushes the whole
               block to a fresh page where it still doesn't fit — which is what
               produced a stranded header on an otherwise blank page. Breaking
               is controlled per question block instead (see @media print). */
            .report-section {{ margin-bottom: 1.5rem; }}
            .section-header {{ font-size: 14pt; font-weight: 700; margin: 0 0 0.75rem 0; padding-bottom: 0.5rem; border-bottom: 3px solid #e3f2fd; color: #333; }}
            .subtopic-row {{ display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.5rem; font-size: 10pt; }}
            .subtopic-name {{ flex: 0 0 40%; }}
            .subtopic-bar-track {{ flex: 1; background: #eee; border-radius: 4px; height: 10px; overflow: hidden; }}
            .subtopic-bar-fill {{ height: 100%; }}
            .subtopic-bar-fill.success {{ background: #4CAF50; }} .subtopic-bar-fill.info {{ background: #2196F3; }}
            .subtopic-bar-fill.warning {{ background: #FF9800; }} .subtopic-bar-fill.danger {{ background: #f44336; }}
            .subtopic-score {{ flex: 0 0 3.5rem; text-align: right; font-weight: 600; }}
            /* The teacher's comment sits above its evidence list, set slightly
               larger than the bullets because it is the part meant to be read. */
            .report-narrative {{ font-size: 10.5pt; line-height: 1.65; color: #37474f; margin: 0 0 0.85rem 0; }}
            .achievement-list, .growth-list {{ list-style: none; margin: 0; padding: 0; }}
            /* Hanging indent rather than flex: WeasyPrint does not honour
               break-inside on flex containers, so a flex row that straddles a
               page boundary gets torn in half (icon on one page, text on the
               next). Block layout fragments correctly and looks the same. */
            .achievement-item, .growth-item, .prelim-banner, .q-feedback {{
                padding-left: 2.1rem; text-indent: -1.55rem;
            }}
            .achievement-item, .growth-item {{
                background: white; border: 1px solid #e0e0e0; border-left: 4px solid #4CAF50;
                padding-top: 0.75rem; padding-right: 0.75rem; padding-bottom: 0.75rem;
                margin-bottom: 0.5rem; border-radius: 4px;
                line-height: 1.6; color: #333; font-size: 10pt;
            }}
            .growth-item {{ border-left-color: #FF9800; }}
            .achievement-item > .rpt-icon {{ color: #4CAF50; }}
            .growth-item > .rpt-icon {{ color: #FF9800; }}
            .prelim-banner {{
                background: #fff3e0; border-left: 4px solid #FF9800; color: #7a4a00;
                padding-top: 0.75rem; padding-right: 1rem; padding-bottom: 0.75rem;
                border-radius: 4px; font-size: 10pt; margin-bottom: 1.25rem;
            }}
            /* Drawn icons (never emoji — see report_icons.py). The nudge keeps
               them optically centred against the cap height of adjacent text. */
            .rpt-icon {{ flex: 0 0 auto; vertical-align: -0.15em; margin-right: 0.4rem; }}
            .section-header, .q-tag, .q-edit-btn {{
                display: flex; align-items: center; gap: 0.4rem;
            }}
            .section-header > .rpt-icon, .q-tag > .rpt-icon, .q-edit-btn > .rpt-icon {{ margin-right: 0; }}
            .q-tag {{ display: inline-flex; }}
            .q-edit-btn {{ display: inline-flex; }}
            .subtopic-questions {{ margin-bottom: 1.25rem; }}
            .subtopic-questions-title {{ font-size: 11pt; font-weight: 700; color: #555; margin-bottom: 0.5rem; }}
            .q-block {{ background: #fafafa; border: 1px solid #e0e0e0; border-radius: 6px; padding: 0.9rem 1rem; margin-bottom: 0.6rem; }}
            .q-head {{ display: flex; justify-content: space-between; gap: 0.75rem; margin-bottom: 0.5rem; }}
            .q-text {{ font-size: 10pt; font-weight: 600; color: #333; }}
            .q-marks {{ font-size: 9pt; font-weight: 700; color: #666; white-space: nowrap; }}
            .q-answer-label {{ font-size: 8.5pt; font-weight: 700; text-transform: uppercase; letter-spacing: 0.03em; color: #888; margin-bottom: 0.2rem; }}
            .q-answer {{ font-size: 10pt; color: #333; background: white; border: 1px solid #eee; border-radius: 4px; padding: 0.5rem 0.65rem; margin-bottom: 0.5rem; white-space: pre-wrap; }}
            .q-tag {{ display: inline-block; font-size: 8.5pt; font-weight: 700; padding: 0.15rem 0.5rem; border-radius: 999px; margin-right: 0.4rem; }}
            .q-tag.correct {{ background: rgba(76,175,80,0.15); color: #2e7d32; }}
            .q-tag.incorrect {{ background: rgba(244,67,54,0.12); color: #c62828; }}
            .q-tag.provisional {{ background: rgba(255,152,0,0.15); color: #7a4a00; }}
            .q-feedback {{ font-size: 9.5pt; color: #555; margin-top: 0.5rem; font-style: italic; }}
            .q-edit-btn {{
                font-size: 8pt; font-weight: 700; color: #2196F3; background: none;
                border: 1px solid #90caf9; border-radius: 999px; padding: 0.1rem 0.5rem; margin-left: 0.5rem; cursor: pointer;
            }}
            .q-marks-edit input {{ width: 3.5rem; padding: 0.15rem 0.35rem; border: 1px solid #ccc; border-radius: 4px; font-size: 9pt; }}
            .q-save-btn, .q-cancel-btn {{
                font-size: 8pt; font-weight: 700; border-radius: 4px; padding: 0.15rem 0.5rem; margin-left: 0.3rem; cursor: pointer; border: none;
            }}
            .q-save-btn {{ background: #4CAF50; color: white; }}
            .q-cancel-btn {{ background: #eee; color: #555; }}

            /* Export toolbar — screen only. Sticky so it stays reachable on a
               long question-by-question report. */
            .report-toolbar {{
                position: sticky; top: 0; z-index: 10;
                display: flex; justify-content: flex-end; align-items: flex-end; gap: 0.75rem;
                max-width: 8.5in; margin: 0 auto; padding: 0.75rem 0.5in 0;
                background: linear-gradient(#fff 70%, rgba(255,255,255,0));
            }}
            .report-name-field {{ display: flex; flex-direction: column; gap: 0.2rem; }}
            .report-name-field span {{
                font-size: 8pt; font-weight: 700; text-transform: uppercase;
                letter-spacing: 0.04em; color: #888;
            }}
            .report-name-field input {{
                font: inherit; font-size: 10pt; color: #333;
                border: 1px solid #ccc; border-radius: 6px; padding: 0.45rem 0.6rem; min-width: 15rem;
            }}
            .report-name-field input:focus {{ outline: 2px solid #8366e8; outline-offset: -1px; border-color: #8366e8; }}
            .report-export-btn {{
                display: inline-flex; align-items: center; gap: 0.45rem;
                background: #8366e8; color: #fff; border: none; border-radius: 6px;
                padding: 0.55rem 1.1rem; font: inherit; font-size: 10pt; font-weight: 600;
                cursor: pointer;
            }}
            .report-export-btn:hover {{ background: #6b52cc; }}
            .report-export-btn:disabled {{ opacity: 0.6; cursor: default; }}
            .report-export-btn svg {{ width: 15px; height: 15px; }}
            .report-export-note {{
                max-width: 8.5in; margin: 0 auto; padding: 0.4rem 0.5in 0;
                font-size: 9pt; color: #7a4a00; text-align: right;
            }}

            /* Applies to the browser's own print/save-as-PDF and to the
               server-side WeasyPrint render, which reads the same rules. */
            @page {{ size: A4; margin: 0.5in; }}
            @media print {{
                .no-print {{ display: none !important; }}
                body {{ background: #fff; }}
                .report-container {{ max-width: none; padding: 0; }}
                .q-edit-btn, .q-marks-edit {{ display: none !important; }}
                /* Only things that genuinely fit on one page get "avoid" —
                   anything unbounded must be allowed to flow across pages. */
                .score-card, .q-block, .subtopic-row {{
                    page-break-inside: avoid; break-inside: avoid;
                }}
                /* Headings stay with the content they introduce, so nothing is
                   left alone at the foot of a page. */
                .section-header, .subtopic-questions-title {{
                    page-break-after: avoid; break-after: avoid;
                }}
                p, .q-answer, .q-feedback {{ orphans: 3; widows: 3; }}
            }}
        </style>
    </head>
    <body>
        {f'''
        <div class="report-toolbar no-print">
            {f"""
            <label class="report-name-field">
                <span>Name on PDF</span>
                <input type="text" id="pdfNameInput" maxlength="120"
                       value="{esc(stats['student_name'])}"
                       title="Used only for the exported PDF — never saved to the student's record.">
            </label>
            """ if editable else ""}
            <button type="button" class="report-export-btn" id="exportPdfBtn" data-pdf-url="{pdf_url}">
                {_icon("download", 15)}
                <span class="report-export-label">Export PDF</span>
            </button>
        </div>
        <p class="report-export-note no-print" id="exportPdfNote" style="display:none;"></p>
        ''' if pdf_url else ''}
        <div class="report-container">
            <div class="report-header">
                <div class="report-eyebrow">Test report</div>
                <h1 class="student-name-large">{esc(stats['student_name'])}</h1>
                <p class="paper-title">{esc(stats['paper_title'])}</p>
                {f'<p class="paper-subtitle">{esc(stats["paper_description"])}</p>' if stats.get('paper_description') else ''}
                <div class="report-meta">
                    {f'<span>Submitted <b>{date_str}</b></span>' if date_str else ''}
                    {f'<span>Time taken <b>{esc(duration_str)}</b> of {stats["time_limit_minutes"]} min</span>' if duration_str else ''}
                </div>
            </div>

            {f'''<div class="focus-box">
                <div class="focus-label">Assessment focus</div>
                {esc(stats['assessment_focus'])}
            </div>''' if stats.get('assessment_focus') else ''}

            {f'''<div class="prelim-banner">{_icon("clock", 15)}<span><b>Provisional result — awaiting teacher approval</b> — {stats['pending_count']} answer(s) still need your teacher's sign-off. This score may change.</span></div>''' if stats['is_preliminary'] else ''}

            <div class="score-card {level['color']}">
                <div class="score-value {level['color']}">{stats['percentage']}%</div>
                <div>
                    <div class="score-level">{level['level']}</div>
                    <div class="score-meta">{format_marks(stats['total_marks_awarded'])}/{format_marks(stats['total_marks_possible'])} marks</div>
                </div>
            </div>

            <div class="report-section">
                <h2 class="section-header">{_icon("chart", 17)} By subtopic</h2>
                {subtopic_rows}
            </div>

            <div class="report-section">
                <h2 class="section-header">{_icon("list", 17)} Question-by-question</h2>
                {questions_html}
            </div>

            <div class="report-section">
                <h2 class="section-header">{_icon("check", 17)} What you did well</h2>
                <p class="report-narrative">{esc(narrative['what_you_did_well'])}</p>
                <ul class="achievement-list">
                    {strengths_html}
                </ul>
            </div>

            <div class="report-section">
                <h2 class="section-header">{_icon("arrow", 17)} Where to go next</h2>
                <p class="report-narrative">{esc(narrative['where_to_go_next'])}</p>
                <ul class="growth-list">
                    {revision_html}
                </ul>
            </div>
        </div>
        {'''
        <script>
        function qStartEdit(btn) {
            const block = btn.closest('.q-marks');
            block.querySelector('.q-marks-display').style.display = 'none';
            btn.style.display = 'none';
            block.querySelector('.q-marks-edit').style.display = 'inline';
        }
        function qCancelEdit(btn) {
            const block = btn.closest('.q-marks');
            block.querySelector('.q-marks-edit').style.display = 'none';
            block.querySelector('.q-marks-display').style.display = 'inline';
            block.querySelector('.q-edit-btn').style.display = 'inline';
        }
        async function qSaveMarks(btn) {
            const block = btn.closest('.q-marks');
            const answerId = block.dataset.answerId;
            const input = block.querySelector('.q-marks-input');
            const marksAwarded = parseFloat(input.value);
            if (isNaN(marksAwarded)) return;
            btn.disabled = true;
            try {
                const res = await fetch(`/admin/api/test-review/${answerId}`, {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ marks_awarded: marksAwarded }),
                });
                if (!res.ok) {
                    const data = await res.json().catch(() => ({}));
                    alert(data.error || 'Could not save mark');
                    btn.disabled = false;
                    return;
                }
                window.location.reload();
            } catch (e) {
                alert('Connection issue — could not save.');
                btn.disabled = false;
            }
        }
        </script>
        ''' if editable else ''}
        {'''
        <script>
        // Prefer the server-rendered PDF (proper pagination and a real filename).
        // Where WeasyPrint's GTK runtime isn't installed the route answers 503,
        // and the browser's own print-to-PDF renders the same report from the
        // @media print rules above — so there is always a way to get a PDF.
        //
        // The build starts on page load rather than on click, so by the time the
        // teacher reaches for the button the file is usually already in hand.
        // Editing the name invalidates that build and quietly starts a new one
        // once typing settles, so the common case stays instant either way.
        (function () {
            const btn = document.getElementById('exportPdfBtn');
            const label = btn.querySelector('.report-export-label');
            const note = document.getElementById('exportPdfNote');
            const nameInput = document.getElementById('pdfNameInput');
            const baseUrl = btn.dataset.pdfUrl;
            const defaultName = nameInput ? nameInput.value : null;

            let pending = null;      // in-flight or settled build for `pendingKey`
            let pendingKey = null;
            let debounce = null;
            let ticker = null;

            function currentName() {
                return nameInput ? nameInput.value.trim() : '';
            }
            // A build is only reusable if it was made for the name now in the box.
            function keyFor(name) {
                return (!name || name === defaultName) ? '' : name;
            }
            function urlFor(key) {
                return key ? baseUrl + '?name=' + encodeURIComponent(key) : baseUrl;
            }

            function build(key) {
                return fetch(urlFor(key)).then(async (res) => {
                    if (res.status === 503) return { unavailable: true };
                    if (!res.ok) throw new Error('HTTP ' + res.status);
                    const match = (res.headers.get('Content-Disposition') || '').match(/filename="?([^"]+)"?/);
                    return { blob: await res.blob(), filename: match ? match[1] : 'test-report.pdf' };
                });
            }

            function startBuild(key) {
                pendingKey = key;
                pending = build(key);
                pending.catch(() => {});   // a background failure surfaces on click, not as noise
                return pending;
            }

            function fallbackToPrint(message) {
                note.textContent = message;
                note.style.display = 'block';
                window.print();
            }

            function setBusy(on) {
                btn.disabled = on;
                if (!on) {
                    clearInterval(ticker);
                    label.textContent = 'Export PDF';
                    return;
                }
                // Only surface a running count once the wait is long enough to
                // notice; below that it would just flicker.
                const started = Date.now();
                label.textContent = 'Preparing\\u2026';
                ticker = setInterval(() => {
                    const secs = (Date.now() - started) / 1000;
                    if (secs > 1.5) label.textContent = 'Preparing\\u2026 ' + secs.toFixed(0) + 's';
                }, 250);
            }

            btn.addEventListener('click', async function () {
                const key = keyFor(currentName());
                note.style.display = 'none';
                setBusy(true);
                try {
                    if (!pending || pendingKey !== key) startBuild(key);
                    const result = await pending;
                    if (result.unavailable) {
                        fallbackToPrint('Server-side PDF export is unavailable, so your browser\\'s print dialogue was opened instead — choose "Save as PDF".');
                        return;
                    }
                    const url = URL.createObjectURL(result.blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = result.filename;
                    document.body.appendChild(a);
                    a.click();
                    a.remove();
                    URL.revokeObjectURL(url);
                } catch (err) {
                    pending = null;   // don't cache a failure
                    fallbackToPrint('Could not build the PDF on the server, so your browser\\'s print dialogue was opened instead — choose "Save as PDF".');
                } finally {
                    setBusy(false);
                }
            });

            if (nameInput) {
                nameInput.addEventListener('input', () => {
                    pending = null;   // whatever was built no longer matches the name
                    clearTimeout(debounce);
                    debounce = setTimeout(() => startBuild(keyFor(currentName())), 700);
                });
            }

            startBuild('');
        })();
        </script>
        ''' if pdf_url else ''}
    </body>
    </html>
    """
    return html_content


@test_bp.route("/assessment/test-submissions/<int:submission_id>/report")
@login_required
def test_submission_report(submission_id):
    submission = TestSubmission.query.get_or_404(submission_id)
    if not current_user.is_admin() and submission.student_id != current_user.id:
        return "Not found", 404
    if submission.status not in ("submitted", "marked") or submission.total_marks_awarded is None:
        return (
            "<p style='font-family:sans-serif; padding:2rem; text-align:center; color:#666;'>"
            "This test hasn't been marked yet — check back shortly.</p>"
        )
    stats = _get_test_submission_stats(submission)
    pdf_url = url_for("test_builder.test_submission_report_pdf", submission_id=submission.id)
    return Response(
        _render_test_report_html(stats, editable=current_user.is_admin(), pdf_url=pdf_url),
        mimetype="text/html",
    )


@test_bp.route("/assessment/test-submissions/<int:submission_id>/report/pdf")
@login_required
def test_submission_report_pdf(submission_id):
    submission = TestSubmission.query.get_or_404(submission_id)
    if not current_user.is_admin() and submission.student_id != current_user.id:
        return jsonify({"error": "Not found"}), 404
    if submission.status not in ("submitted", "marked") or submission.total_marks_awarded is None:
        return jsonify({"error": "This test hasn't been marked yet."}), 409

    from report_card_routes import HTML, WEASYPRINT_AVAILABLE
    if not WEASYPRINT_AVAILABLE:
        return jsonify({
            "error": "PDF export is unavailable on this server: WeasyPrint requires "
                     "the GTK runtime, which is not installed.",
        }), 503

    stats = _get_test_submission_stats(submission)

    # The roster stores an alias; a teacher exporting a report for a parent or a
    # file may need the student's real name on it. Deliberately request-scoped:
    # it is read from the query string, used for this one render, and never
    # written back to the submission or the user record. Teacher-only, so a
    # student cannot relabel their own report.
    name_override = (request.args.get("name") or "").strip()
    if name_override and current_user.is_admin():
        stats["student_name"] = name_override[:120]

    html_content = _render_test_report_html(stats)
    pdf_bytes = BytesIO()
    HTML(string=html_content).write_pdf(pdf_bytes)
    pdf_bytes.seek(0)

    safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", stats["student_name"])
    filename = f"Test_Report_{safe_name}_{submission.id}.pdf"
    return send_file(pdf_bytes, mimetype="application/pdf", as_attachment=True, download_name=filename)
