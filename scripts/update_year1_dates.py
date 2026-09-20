"""
One-off migration: rebuild Year 1 (Grade 11) Sem 1 + Sem 2 week rows from the teacher's
updated CSV schedule (C:\\Users\\Colin\\Desktop\\Comp Sci\\Unit Plan\\dates\\Year1_Sem*.csv).

The CSV is the new source of truth for week numbering, dates, topics, content focus,
syllabus tags, and notes — the school year start shifted by a week, several breaks were
merged into single rows, and a couple of weeks were inserted/renumbered.

What's preserved: the rich lesson-plan detail (big idea, objectives, full `detail` block —
key vocabulary, command terms, lesson-by-lesson breakdown, ATL, differentiation, IA/TOK
links) already written for each week is carried over from whichever old week now covers
that same content, via an explicit mapping built by comparing topics/dates by hand (not
fuzzy-matched) — see YEAR1SEM1_MAP / YEAR1SEM2_MAP below. Weeks with no old counterpart
(genuinely new/inserted weeks) are left without that detail for the teacher to fill in.

Existing uploaded resources on the old year1sem1 weeks (8, 11, 12, 13) were confirmed to be
test uploads and are discarded, not migrated.

Usage:
    python scripts/update_year1_dates.py
"""
import csv
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

CSV_DIR = Path(r"C:\Users\Colin\Desktop\Comp Sci\Unit Plan\dates")

# new_week_number -> old_week_number ("None" = no matching old week; genuinely new/merged
# with nothing distinct to preserve).
YEAR1SEM1_MAP = {
    "1": "1", "2": "2", "3": "3", "4": "4", "5": "5", "6": "6", "7": "7", "8": "8",
    "10": None,  # October Break — merge of old breaks 9+10, no detail to preserve
    "9": "11",   # Unit examination <- Unit Review & Assessment
    "11": "12", "12": "13", "13": "14", "14": "15", "15": "16", "16": "17",
    "17": "20", "18": "21",
}

YEAR1SEM2_MAP = {
    "22": "22", "23": "23", "24": "24",
    "24.5": "26",  # February Break — exact date match with old break week
    "25": "25", "26": "27",
    "27-28": "29",   # merged Databases revision+exam <- later of the two merged old weeks
    "29": "30", "31": "31",
    "31.5": None,    # Spring Break — merge of old breaks 32+33, no detail to preserve
    "32": "34", "33": "35",
    "34": None,      # newly inserted extra IA Development week — no old counterpart
    "35": "36",
    "36-37": "38",   # merged Revision & Exam Prep <- later of the two merged old weeks
    "39": "39", "40": "40", "41": "41", "42": "42",
    "43-44": "43",   # merged Networks revision+exam <- Network Revision (exact date match)
    "45": "44",      # Year-End Assessments <- Network Examination
}

# Rows whose "Week" column has no number at all (a plain description instead) — assign a
# stable decimal placeholder between the surrounding numbered weeks, and move the
# description into `topic` where it belongs.
UNNUMBERED_WEEK_LABELS = {
    "February Break": "24.5",
    "Spring Break": "31.5",
}


def parse_csv(filename):
    path = CSV_DIR / filename
    rows = []
    with open(path, encoding="utf-8-sig") as f:
        for raw in csv.DictReader(f):
            week_label = raw["Week"].strip()
            if week_label in UNNUMBERED_WEEK_LABELS:
                week_number = UNNUMBERED_WEEK_LABELS[week_label]
                topic = week_label
            else:
                week_number = week_label.replace("Week ", "").replace(" (merged)", "").strip()
                topic = raw["Topic"].strip()
            content_focus = raw["Weekly Focus / Content"].strip()
            syllabus = raw["Subtopic (Syllabus Code)"].strip()
            rows.append({
                "week_number": week_number,
                "calendar_dates": raw["Date Range"].strip(),
                "topic": topic,
                "content_focus": None if content_focus == "-" else content_focus,
                "syllabus": None if syllabus == "-" else syllabus,
                "note": raw["HL Notes / Extensions"].strip() or None,
                "merged_note": raw["Notes"].strip() or None,
                "is_break": content_focus == "-" or "break" in topic.lower(),
            })
    return rows


def rebuild_semester(app, db, UnitPlanSemester, UnitPlanWeek, sem_key, csv_filename, week_map):
    semester = UnitPlanSemester.query.filter_by(key=sem_key).first()
    if not semester:
        print(f"  ! semester {sem_key} not found, skipping")
        return

    old_weeks = {w.week_number: w for w in semester.weeks}
    rows = parse_csv(csv_filename)

    # Snapshot the rich detail we want to preserve before deleting anything.
    carried = {}
    for new_num, old_num in week_map.items():
        if old_num and old_num in old_weeks:
            old = old_weeks[old_num]
            carried[new_num] = {
                "big_idea": old.big_idea,
                "objectives": old.objectives,
                "assessment": old.assessment,
                "detail": old.detail,
            }

    for w in list(semester.weeks):
        db.session.delete(w)
    db.session.flush()

    for i, row in enumerate(rows):
        week = UnitPlanWeek(semester_id=semester.id, week_number=row["week_number"], position=i)
        week.topic = row["topic"]
        week.content_focus = row["content_focus"]
        week.calendar_dates = row["calendar_dates"]
        week.syllabus = row["syllabus"]
        week.note = row["note"]
        week.merged_note = row["merged_note"]
        week.is_break = row["is_break"]
        week.is_exam = False
        week.taught = False
        week.objectives = "[]"
        week.materials = "[]"

        prior = carried.get(row["week_number"])
        if prior:
            week.big_idea = prior["big_idea"]
            week.assessment = prior["assessment"]
            week.objectives = prior["objectives"] or "[]"
            week.detail = prior["detail"]

        db.session.add(week)

    db.session.commit()
    print(f"  {sem_key}: {len(rows)} weeks written, {len(carried)} carried rich detail from the old plan")


def main():
    from app import app
    from extensions import db
    from models import UnitPlanSemester, UnitPlanWeek

    with app.app_context():
        print("Rebuilding Year 1 (Grade 11) schedule from updated CSVs...")
        rebuild_semester(app, db, UnitPlanSemester, UnitPlanWeek, "year1sem1", "Year1_Sem1.csv", YEAR1SEM1_MAP)
        rebuild_semester(app, db, UnitPlanSemester, UnitPlanWeek, "year1sem2", "Year1_Sem2.csv", YEAR1SEM2_MAP)
        print("Done.")


if __name__ == "__main__":
    main()
