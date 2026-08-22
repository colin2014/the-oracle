"""Lesson library: the course's decks, videos, PDFs and worksheets, linked
from OneDrive/YouTube/wherever they already live, organised against the IB DP
CS syllabus tree plus teacher-made folders.

Resources are *linked*, not uploaded — the teacher keeps authoring in
PowerPoint Online (or wherever) and pastes the share link here. Appending
`action=embedview` to a OneDrive share link renders it inline, anonymously,
with slide navigation and fullscreen; that is the only reliable embed form (a
bare share link is X-Frame-Options blocked, and the Office web viewer cannot
resolve a 1drv.ms redirect), so it is what _to_embed_url produces. YouTube and
Vimeo links get their own player-embed rewrite.
"""

import re
from urllib.parse import parse_qs, urlparse

from flask import Blueprint, jsonify, render_template, request
from flask_login import login_required

from auth import admin_required
from extensions import db
from models import Resource, ResourceFolder, TopicGradeFocus, UnitPlanTopic

slides_bp = Blueprint("slides", __name__)

GRADES = (11, 12)
KINDS = ("deck", "video", "pdf", "worksheet", "exit_ticket", "exit_ticket_answers")
# Kinds that are always PowerPoint files this workflow generates, so "edit in
# PowerPoint" (the pencil icon) makes sense for them the same way it does for
# a deck. Plain "worksheet"/"pdf" might not be a .pptx at all.
POWERPOINT_KINDS = {"deck", "exit_ticket", "exit_ticket_answers"}

# Theme grouping for the top level of the tree. UnitPlanTopic.part is "A1".."B4"
# or "assessment"; the first character gives the theme.
THEMES = [
    {"key": "A", "label": "Theme A", "blurb": "Concepts and challenges"},
    {"key": "B", "label": "Theme B", "blurb": "Computational thinking and programming"},
    {"key": "assessment", "label": "Assessment", "blurb": ""},
]

UNIT_LABELS = {
    "A1": "Computer Fundamentals",
    "A2": "Networking",
    "A3": "Databases",
    "A4": "Machine Learning",
    "B1": "Approaches to Computational Thinking",
    "B2": "Programming",
    "B3": "Object-Oriented Programming",
    "B4": "Abstract Data Types",
    "IA": "Internal Assessment",
    "Case Study": "Case Study",
}


def _extract_url(raw):
    """Accept either a bare link or a full <iframe …> embed snippet.

    PowerPoint Online's "Embed" option hands you the whole element, so pasting
    that in is at least as likely as pasting the plain share link."""
    raw = (raw or "").strip()
    if "<iframe" in raw.lower():
        m = re.search(r"""\bsrc\s*=\s*["']([^"']+)["']""", raw, re.I)
        if m:
            return m.group(1).strip()
    return raw


def _default_title(topic_id):
    """Decks inherit their name from the syllabus statement they hang off, so the
    teacher doesn't retype something the subtopic table already says."""
    if not topic_id:
        return ""
    topic = UnitPlanTopic.query.filter_by(topic_id=topic_id).first()
    return f"{topic.code} {topic.statement}" if topic else ""


# Exit tickets/answer keys don't borrow the syllabus statement like a deck
# does -- "Describe the functions and interactions of the main CPU
# components" is a confusing thing for a screen reader (or the delete
# confirm dialog) to read out for what's actually a 2-page quiz handout.
_ROLE_TITLES = {"exit_ticket": "Exit Ticket", "exit_ticket_answers": "Exit Ticket Answers"}


def _display_title(resource):
    """Stored title if the teacher gave one, otherwise a sensible default:
    the syllabus statement for a deck, a fixed role name for exit tickets."""
    explicit = (resource.title or "").strip()
    if explicit:
        return explicit
    if resource.kind in _ROLE_TITLES:
        return _ROLE_TITLES[resource.kind]
    return _default_title(resource.topic_id) or "Untitled"


YOUTUBE_RE = re.compile(r"(?:youtube\.com/embed/|youtu\.be/)([\w-]{6,})")


def _youtube_embed(url):
    host = (urlparse(url).netloc or "").lower()
    if "youtube.com" not in host and "youtu.be" not in host:
        return None
    if "youtube.com" in host:
        qs = parse_qs(urlparse(url).query)
        if qs.get("v"):
            return f"https://www.youtube.com/embed/{qs['v'][0]}"
    m = YOUTUBE_RE.search(url)
    return f"https://www.youtube.com/embed/{m.group(1)}" if m else None


VIMEO_RE = re.compile(r"vimeo\.com/(\d+)")


def _vimeo_embed(url):
    m = VIMEO_RE.search(url)
    return f"https://player.vimeo.com/video/{m.group(1)}" if m else None


def _to_embed_url(url, kind="deck"):
    """Share link -> inline-viewer URL, or None if nothing can embed it (the
    UI then falls back to a plain link rather than an iframe that'll be
    blocked)."""
    url = (url or "").strip()
    if not url:
        return None
    lowered = url.lower()
    if "action=embedview" in lowered or "/embed" in lowered or "player.vimeo.com" in lowered:
        return url
    if kind == "video":
        return _youtube_embed(url) or _vimeo_embed(url)
    host = (urlparse(url).netloc or "").lower()
    if any(h in host for h in ("1drv.ms", "onedrive.live.com", "sharepoint.com")):
        return url + ("&" if "?" in url else "?") + "action=embedview"
    return None


def _edit_url(resource):
    """Deck's OneDrive link, rewritten to open straight in the PowerPoint Online
    editor (`action=edit`) instead of the read-only viewer. None for anything
    that isn't a OneDrive-hosted PowerPoint — there's no editor to jump to."""
    if resource.kind not in POWERPOINT_KINDS:
        return None
    url = (resource.url or "").strip()
    if not url:
        return None
    host = (urlparse(url).netloc or "").lower()
    if not any(h in host for h in ("1drv.ms", "onedrive.live.com", "sharepoint.com")):
        return None
    lowered = url.lower()
    if "action=edit" in lowered:
        return url
    if "action=" in lowered:
        return re.sub(r"action=[^&]*", "action=edit", url, flags=re.I)
    return url + ("&" if "?" in url else "?") + "action=edit"


def _theme_of(part):
    return "assessment" if part == "assessment" else (part or "?")[0]


def _unit_key(part, code):
    # The two assessment statements ("IA", "Case Study") are each their own
    # category rather than being lumped together under one "Assessment" unit.
    return code if part == "assessment" else part


def _subsection_of(code):
    """"A1.1.1" -> "A1.1" — the middle grouping level inside a unit."""
    bits = (code or "").split(".")
    return ".".join(bits[:2]) if len(bits) >= 2 else (code or "")


def _folder_tree(scope):
    return ResourceFolder.query.filter_by(scope=scope).order_by(ResourceFolder.position, ResourceFolder.id).all()


def _folder_dict(folder, resources_by_folder):
    entries = resources_by_folder.get(folder.id, [])
    return {
        "id": folder.id, "parent_id": folder.parent_id, "name": folder.name,
        "resources": entries,
    }


def _resource_entry(resource):
    return {
        "id": resource.id,
        "kind": resource.kind,
        "title": _display_title(resource),
        "auto_title": not (resource.title or "").strip() and bool(resource.topic_id),
        "url": resource.url,
        "embed_url": resource.embed_url,
        "edit_url": _edit_url(resource),
    }


def _collect_folder_ids(folder_id):
    ids = [folder_id]
    for child in ResourceFolder.query.filter_by(parent_id=folder_id).all():
        ids.extend(_collect_folder_ids(child.id))
    return ids


KIND_META = [
    {"value": "deck", "label": "Slides"},
    {"value": "video", "label": "Video"},
    {"value": "pdf", "label": "PDF"},
    {"value": "worksheet", "label": "Worksheet"},
    {"value": "exit_ticket", "label": "Exit Ticket"},
    {"value": "exit_ticket_answers", "label": "Exit Ticket Answers"},
]


@slides_bp.route("/slides")
@login_required
@admin_required
def slide_library():
    return render_template("slide_library.html", grades=GRADES, kinds=KIND_META)


@slides_bp.route("/api/slides/library")
@login_required
@admin_required
def library_data():
    """The whole tree in one payload — small enough that paginating or
    lazy-loading per unit would cost more in round trips than it saves."""
    grade = request.args.get("grade", type=int)
    if grade not in GRADES:
        grade = GRADES[0]

    resources_by_topic = {}
    resources_by_folder = {}
    course_wide = []
    for r in Resource.query.order_by(Resource.position, Resource.id).all():
        entry = _resource_entry(r)
        if r.folder_id:
            resources_by_folder.setdefault(r.folder_id, []).append(entry)
        elif r.topic_id:
            resources_by_topic.setdefault(r.topic_id, []).append(entry)
        else:
            course_wide.append(entry)

    def folders_for(scope):
        return [_folder_dict(f, resources_by_folder) for f in _folder_tree(scope)]

    focus = {
        f.topic_id: f.focused
        for f in TopicGradeFocus.query.filter_by(grade=grade).all()
    }

    themes = {t["key"]: {**t, "units": {}} for t in THEMES}
    for topic in UnitPlanTopic.query.order_by(UnitPlanTopic.part, UnitPlanTopic.code).all():
        theme_key = _theme_of(topic.part)
        theme = themes.get(theme_key)
        if theme is None:
            continue
        unit_key = _unit_key(topic.part, topic.code)
        unit = theme["units"].setdefault(unit_key, {
            "code": unit_key,
            "label": UNIT_LABELS.get(unit_key, topic.part_label or unit_key),
            "subsections": {},
        })
        sub_key = _subsection_of(topic.code)
        sub = unit["subsections"].setdefault(sub_key, {"code": sub_key, "topics": []})
        sub["topics"].append({
            "id": topic.topic_id,
            "code": topic.code,
            "statement": topic.statement,
            "hl_only": topic.hl_only,
            "focused": bool(focus.get(topic.topic_id)),
            "resources": resources_by_topic.get(topic.topic_id, []),
        })

    # Dicts -> ordered lists, and roll up counts the UI shows on collapsed rows.
    out_themes = []
    for meta in THEMES:
        theme = themes[meta["key"]]
        units = []
        for unit in theme["units"].values():
            subs = list(unit["subsections"].values())
            topics = [t for s in subs for t in s["topics"]]
            unit_folders = folders_for(unit["code"])
            folder_resource_count = sum(len(f["resources"]) for f in unit_folders)
            units.append({
                **unit,
                "subsections": subs,
                "folders": unit_folders,
                "total": len(topics),
                "focused_count": sum(1 for t in topics if t["focused"]),
                "resource_count": sum(len(t["resources"]) for t in topics) + folder_resource_count,
            })
        if not units:
            continue
        all_topics = [t for u in units for s in u["subsections"] for t in s["topics"]]
        out_themes.append({
            "key": meta["key"], "label": meta["label"], "blurb": meta["blurb"],
            "units": units,
            "total": len(all_topics),
            "focused_count": sum(1 for t in all_topics if t["focused"]),
            "resource_count": sum(u["resource_count"] for u in units),
        })

    course_wide_folders = folders_for("course-wide")
    return jsonify({
        "grade": grade,
        "themes": out_themes,
        "course_wide": {
            "resources": course_wide,
            "folders": course_wide_folders,
            "resource_count": len(course_wide) + sum(len(f["resources"]) for f in course_wide_folders),
        },
    })


@slides_bp.route("/api/slides/resources", methods=["POST"])
@login_required
@admin_required
def create_resource():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    url = _extract_url(data.get("url"))
    kind = (data.get("kind") or "deck").strip()
    topic_id = (data.get("topic_id") or "").strip() or None
    folder_id = data.get("folder_id")
    folder_id = int(folder_id) if folder_id else None

    if kind not in KINDS:
        return jsonify({"error": "Unknown resource type."}), 400
    if not url:
        return jsonify({"error": "Paste the share link (or the embed code)."}), 400
    if topic_id and folder_id:
        return jsonify({"error": "Attach to a syllabus statement or a folder, not both."}), 400
    if not title and not topic_id:
        return jsonify({"error": "Give it a title — only decks attached to a statement can borrow its name."}), 400
    if not urlparse(url).scheme.startswith("http"):
        return jsonify({"error": "That doesn't look like a link — paste the full https:// share URL."}), 400
    if topic_id and not UnitPlanTopic.query.filter_by(topic_id=topic_id).first():
        return jsonify({"error": "Unknown syllabus statement."}), 404
    if folder_id and not ResourceFolder.query.get(folder_id):
        return jsonify({"error": "Unknown folder."}), 404

    resource = Resource(
        kind=kind, topic_id=topic_id, folder_id=folder_id, title=title, url=url,
        embed_url=_to_embed_url(url, kind),
        position=Resource.query.filter_by(topic_id=topic_id, folder_id=folder_id).count(),
    )
    db.session.add(resource)
    db.session.commit()
    return jsonify({"ok": True, "resource": _resource_entry(resource)})


@slides_bp.route("/api/slides/resources/<int:resource_id>", methods=["PATCH", "DELETE"])
@login_required
@admin_required
def update_resource(resource_id):
    resource = Resource.query.get_or_404(resource_id)
    if request.method == "DELETE":
        db.session.delete(resource)
        db.session.commit()
        return jsonify({"ok": True})

    data = request.get_json(silent=True) or {}
    if "title" in data:
        # Blank is meaningful: fall back to the syllabus statement's own wording.
        resource.title = (data["title"] or "").strip()
    if "kind" in data:
        kind = (data["kind"] or "").strip()
        if kind not in KINDS:
            return jsonify({"error": "Unknown resource type."}), 400
        resource.kind = kind
    if "url" in data:
        url = _extract_url(data["url"])
        if not url:
            return jsonify({"error": "Link cannot be empty."}), 400
        resource.url = url
    if "kind" in data or "url" in data:
        resource.embed_url = _to_embed_url(resource.url, resource.kind)
    if "topic_id" in data:
        topic_id = (data["topic_id"] or "").strip() or None
        if topic_id and not UnitPlanTopic.query.filter_by(topic_id=topic_id).first():
            return jsonify({"error": "Unknown syllabus statement."}), 404
        resource.topic_id = topic_id
        if topic_id:
            resource.folder_id = None
    if "folder_id" in data:
        folder_id = data["folder_id"]
        folder_id = int(folder_id) if folder_id else None
        if folder_id and not ResourceFolder.query.get(folder_id):
            return jsonify({"error": "Unknown folder."}), 404
        resource.folder_id = folder_id
        if folder_id:
            resource.topic_id = None
    if not (resource.title or "").strip() and not resource.topic_id:
        return jsonify({"error": "Give it a title — only decks attached to a statement can borrow its name."}), 400
    db.session.commit()
    return jsonify({"ok": True, "resource": _resource_entry(resource)})


@slides_bp.route("/api/slides/folders", methods=["POST"])
@login_required
@admin_required
def create_folder():
    data = request.get_json(silent=True) or {}
    scope = (data.get("scope") or "").strip()
    name = (data.get("name") or "").strip()
    parent_id = data.get("parent_id")
    parent_id = int(parent_id) if parent_id else None

    if not scope:
        return jsonify({"error": "Missing scope."}), 400
    if not name:
        return jsonify({"error": "Give the folder a name."}), 400
    if parent_id:
        parent = ResourceFolder.query.get(parent_id)
        if not parent or parent.scope != scope:
            return jsonify({"error": "Unknown parent folder."}), 404

    folder = ResourceFolder(
        scope=scope, parent_id=parent_id, name=name,
        position=ResourceFolder.query.filter_by(scope=scope, parent_id=parent_id).count(),
    )
    db.session.add(folder)
    db.session.commit()
    return jsonify({"ok": True, "folder": {"id": folder.id, "parent_id": folder.parent_id, "name": folder.name, "resources": []}})


@slides_bp.route("/api/slides/folders/<int:folder_id>", methods=["PATCH", "DELETE"])
@login_required
@admin_required
def update_folder(folder_id):
    folder = ResourceFolder.query.get_or_404(folder_id)
    if request.method == "DELETE":
        ids = _collect_folder_ids(folder.id)
        Resource.query.filter(Resource.folder_id.in_(ids)).delete(synchronize_session=False)
        ResourceFolder.query.filter(ResourceFolder.id.in_(ids)).delete(synchronize_session=False)
        db.session.commit()
        return jsonify({"ok": True})

    data = request.get_json(silent=True) or {}
    if "name" in data:
        name = (data["name"] or "").strip()
        if not name:
            return jsonify({"error": "Name cannot be empty."}), 400
        folder.name = name
    db.session.commit()
    return jsonify({"ok": True, "folder": {"id": folder.id, "parent_id": folder.parent_id, "name": folder.name}})


@slides_bp.route("/api/slides/focus", methods=["POST"])
@login_required
@admin_required
def set_focus():
    data = request.get_json(silent=True) or {}
    topic_id = (data.get("topic_id") or "").strip()
    grade = data.get("grade")
    focused = bool(data.get("focused"))

    if grade not in GRADES:
        return jsonify({"error": "Grade must be 11 or 12."}), 400
    if not UnitPlanTopic.query.filter_by(topic_id=topic_id).first():
        return jsonify({"error": "Unknown syllabus statement."}), 404

    row = TopicGradeFocus.query.filter_by(topic_id=topic_id, grade=grade).first()
    if row is None:
        row = TopicGradeFocus(topic_id=topic_id, grade=grade)
        db.session.add(row)
    row.focused = focused
    db.session.commit()
    return jsonify({"ok": True, "topic_id": topic_id, "grade": grade, "focused": focused})
