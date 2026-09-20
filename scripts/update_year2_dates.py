"""
One-off migration: rebuild Year 2 (Grade 11's second-year DP plan, stored under the
year2sem1/year2sem2 keys) week rows from the teacher's updated CSV schedule
(C:\\Users\\Colin\\Desktop\\Comp Sci\\Unit Plan\\dates\\Year2_Sem*.csv).

Same approach as scripts/update_year1_dates.py: the CSV is the new source of truth for
week numbering, dates, topics, content focus, syllabus tags, and notes. Rich lesson-plan
detail already written for each week is carried over from whichever old week now covers
that same content, via an explicit mapping built by comparing topics/dates by hand — see
YEAR2SEM1_MAP / YEAR2SEM2_MAP below. Weeks with no old counterpart (genuinely new/inserted
weeks) are left without that detail for the teacher to fill in.

No existing uploaded resources or taught flags existed on year2sem1/year2sem2 at the time
of this migration (confirmed via DB query first), so there was nothing to discard/preserve
beyond the detail carry-over.

Usage:
    python scripts/update_year2_dates.py
"""
import csv
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

CSV_DIR = Path(r"C:\Users\Colin\Desktop\Comp Sci\Unit Plan\dates")

# new_week_number -> old_week_number ("None" = no matching old week; genuinely new/merged
# with nothing distinct to preserve).
YEAR2SEM1_MAP = {
    "1": "1", "2": "2", "3": "3", "4": "4", "5": "5", "6": "6",
    "8": "9",    # OOP unit examination <- old OOP exam week
    "7": None,   # October Break — merge of old breaks 7+8, no detail to preserve
    "9": "10",   # IA Final check <- old IA Final Check
    "10": "11",  # IA Final Submission & Mock Feedback <- old
    "11": "12", "12": "13",  # Abstract Data Types
    "13": None,  # newly inserted 3rd Abstract Data Types week — no old counterpart
    "14": "14", "15": "15",
    "16": "16", "17": "17",
    "18": None,  # newly inserted 3rd Revision & Mock Exams week — no old counterpart
}

YEAR2SEM2_MAP = {
    "22": "20", "23": "21",
    "24": None,   # February Break — no detail on old break week to preserve
    "25": "22", "26": "23", "27": "24", "28": "25",
    "29": "27",   # ML Advanced (5th week) <- old week after its Feb break
    "30": "28",   # ML Ethics
    "30.5": None,  # Spring Break — no detail on old break weeks to preserve
    "31": "29",   # ML unit test <- old "ML" week
    "32": "30", "33": "31",  # Case Study Intensive
    "35": "34", "36": "35", "37": "36",  # Intensive Revision & Exam Prep
    "38": "37",   # IB Exams Begin
}

# Rows whose "Week" column has no number at all (a plain description instead) — assign a
# stable placeholder between the surrounding numbered weeks, and move the description into
# `topic` where it belongs.
UNNUMBERED_WEEK_LABELS = {
    "year2sem1": {},
    "year2sem2": {
        "February Break": "24",
        "Spring Break": "30.5",
    },
}


def parse_csv(filename, sem_key):
    path = CSV_DIR / filename
    unnumbered = UNNUMBERED_WEEK_LABELS[sem_key]
    rows = []
    with open(path, encoding="utf-8-sig") as f:
        for raw in csv.DictReader(f):
            week_label = raw["Week"].strip()
            if week_label in unnumbered:
                week_number = unnumbered[week_label]
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


def rebuild_semester(db, UnitPlanSemester, UnitPlanWeek, sem_key, csv_filename, week_map):
    semester = UnitPlanSemester.query.filter_by(key=sem_key).first()
    if not semester:
        print(f"  ! semester {sem_key} not found, skipping")
        return

    old_weeks = {w.week_number: w for w in semester.weeks}
    rows = parse_csv(csv_filename, sem_key)

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
        print("Rebuilding Year 2 (Grade 11's second-year plan) schedule from updated CSVs...")
        rebuild_semester(db, UnitPlanSemester, UnitPlanWeek, "year2sem1", "Year2_Sem1.csv", YEAR2SEM1_MAP)
        rebuild_semester(db, UnitPlanSemester, UnitPlanWeek, "year2sem2", "Year2_Sem2.csv", YEAR2SEM2_MAP)
        print("Done.")


if __name__ == "__main__":
    main()
