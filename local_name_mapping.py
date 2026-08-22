"""Manage local-only student name mappings for teachers (GDPR-compliant).

Maps database aliases to real names stored only on the teacher's machine.
This keeps real names off the server entirely.
"""
import json
from pathlib import Path
from datetime import datetime


TEACHER_NAMES_DIR = Path("teacher_names")
TEACHER_NAMES_DIR.mkdir(exist_ok=True)


def _get_teacher_names_file(teacher_id):
    """Get the path to a teacher's name mapping file."""
    return TEACHER_NAMES_DIR / f"teacher_{teacher_id}_names.json"


def load_name_mappings(teacher_id):
    """Load all name mappings for a teacher. Returns dict of {student_id: real_name}."""
    file_path = _get_teacher_names_file(teacher_id)
    if not file_path.exists():
        return {}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("mappings", {})
    except (json.JSONDecodeError, OSError):
        return {}


def save_name_mapping(teacher_id, student_id, real_name):
    """Save or update a student's real name for a teacher.

    Args:
        teacher_id: The teacher's user ID
        student_id: The student's user ID (str or int, will be converted to str)
        real_name: The real name to store (or None/empty to delete)
    """
    student_id_str = str(student_id)
    file_path = _get_teacher_names_file(teacher_id)

    # Load existing data
    if file_path.exists():
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            data = {"mappings": {}}
    else:
        data = {"mappings": {}}

    # Update mapping
    if real_name and real_name.strip():
        data["mappings"][student_id_str] = real_name.strip()
    else:
        data["mappings"].pop(student_id_str, None)

    data["updated_at"] = datetime.utcnow().isoformat()

    # Write back
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except OSError as e:
        raise Exception(f"Failed to save name mapping: {e}")


def get_display_name(teacher_id, student_id, alias):
    """Get the display name for a student (real name if mapped, otherwise alias).

    Args:
        teacher_id: The teacher's user ID
        student_id: The student's user ID
        alias: The student's database alias/name

    Returns:
        The real name if mapped by this teacher, otherwise the alias.
    """
    mappings = load_name_mappings(teacher_id)
    return mappings.get(str(student_id), alias)


def delete_all_mappings(teacher_id):
    """Delete all name mappings for a teacher (e.g., when they leave)."""
    file_path = _get_teacher_names_file(teacher_id)
    if file_path.exists():
        file_path.unlink()
