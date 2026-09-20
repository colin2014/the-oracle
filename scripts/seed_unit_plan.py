"""
One-off migration: import the standalone DP Computer Science unit planner
(C:\\Users\\Colin\\Desktop\\Comp Sci\\Unit Plan\\website\\) into the Oracle's database, so the
teacher can edit it from any device and students can view it read-only at /unit-plan/.

The standalone site's assets/data.js is `const NAME = <JSON.stringify output>;` for four
constants (COURSE_DATA, SCHOOL_CALENDAR, GRADE12_TOPICS, GRADE12_EXAM_PLAN) — valid JSON once
the `const NAME = ` prefix and trailing `;` are stripped.

Does NOT modify the original Unit Plan folder — this is a one-time read, not a sync.

Usage:
    python scripts/seed_unit_plan.py
"""
import json
import re
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

SOURCE_DIR = Path(r"C:\Users\Colin\Desktop\Comp Sci\Unit Plan\website")
DATA_JS = SOURCE_DIR / "assets" / "data.js"
SOURCE_RESOURCES = SOURCE_DIR / "resources"

RESOURCES_DIR = PROJECT_ROOT / "data" / "unit_plan_resources"
CALENDAR_FILE = PROJECT_ROOT / "data" / "unit_plan_calendar.json"

SEMESTER_KEYS = ["year1sem1", "year1sem2", "year2sem1", "year2sem2"]


def _extract_const(js_text, name):
    m = re.search(r"const\s+" + name + r"\s*=\s*(.*?);\s*(?:\n\nconst|\Z)", js_text, re.S)
    if not m:
        raise ValueError(f"Couldn't find const {name} in data.js")
    return json.loads(m.group(1))


def _rewrite_material_path(m, bucket_key):
    if m.get("kind") == "file" and m.get("path"):
        # old: "resources/<bucket>/<folder>/<file>" -> new servable URL
        rel = m["path"]
        if rel.startswith("resources/"):
            rel = rel[len("resources/"):]
        m["path"] = "/unit-plan/resources/" + rel
    return m


def main():
    from app import app
    from extensions import db
    from models import UnitPlanSemester, UnitPlanWeek, UnitPlanTopic

    with app.app_context():
        if UnitPlanSemester.query.count() > 0:
            print("UnitPlanSemester already has rows — skipping seed (already migrated).")
            return

        js_text = DATA_JS.read_text(encoding="utf-8")
        course_data = _extract_const(js_text, "COURSE_DATA")
        school_calendar = _extract_const(js_text, "SCHOOL_CALENDAR")
        grade12_topics = _extract_const(js_text, "GRADE12_TOPICS")
        grade12_plan = _extract_const(js_text, "GRADE12_EXAM_PLAN")

        # ---- semesters + weeks ----
        week_count = 0
        for position, key in enumerate(SEMESTER_KEYS):
            sem_data = course_data.get(key)
            if not sem_data:
                continue
            semester = UnitPlanSemester(
                key=key,
                title=sem_data.get("title", key),
                subtitle=sem_data.get("subtitle"),
                date_range=sem_data.get("dateRange"),
                position=position,
            )
            db.session.add(semester)
            db.session.flush()  # assign semester.id

            for i, w in enumerate(sem_data.get("weeks", [])):
                for m in w.get("materials") or []:
                    _rewrite_material_path(m, key)
                week = UnitPlanWeek(
                    semester_id=semester.id,
                    week_number=str(w.get("week")),
                    position=i,
                )
                week.update_from_dict(w)
                db.session.add(week)
                week_count += 1

        # ---- grade 12 syllabus tracker ----
        plan_position = {topic_id: idx for idx, topic_id in enumerate(grade12_plan)}
        for t in grade12_topics:
            for m in t.get("materials") or []:
                _rewrite_material_path(m, "grade12")
            topic = UnitPlanTopic(
                topic_id=t["id"],
                code=t.get("code", ""),
                statement=t.get("statement", ""),
                part=t.get("part", ""),
                part_label=t.get("partLabel"),
                hl_only=bool(t.get("hlOnly", False)),
                status=t.get("status", "not-done"),
                plan_position=plan_position.get(t["id"]),
                materials=json.dumps(t.get("materials") or []),
            )
            db.session.add(topic)

        db.session.commit()
        print(f"Seeded {len(SEMESTER_KEYS)} semesters, {week_count} weeks, {len(grade12_topics)} grade 12 topics.")

        # ---- static calendar reference data ----
        CALENDAR_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CALENDAR_FILE, "w", encoding="utf-8") as f:
            json.dump(school_calendar, f, indent=2, ensure_ascii=False)
        print(f"Wrote {CALENDAR_FILE}")

        # ---- copy uploaded resource files (same relative layout as source) ----
        if SOURCE_RESOURCES.exists():
            RESOURCES_DIR.mkdir(parents=True, exist_ok=True)
            copied = 0
            for src_file in SOURCE_RESOURCES.rglob("*"):
                if src_file.is_file():
                    rel = src_file.relative_to(SOURCE_RESOURCES)
                    dest = RESOURCES_DIR / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_file, dest)
                    copied += 1
            print(f"Copied {copied} resource file(s) to {RESOURCES_DIR}")


if __name__ == "__main__":
    main()
