#!/usr/bin/env python
"""Debug script to show assignments and their reading times."""

import json
import sys
from pathlib import Path
from app import app, db
from models import User, ReadingAssignment, ClassEnrollment

# Fix encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def debug_assignments():
    with app.app_context():
        # Find the test student
        test_user = User.query.filter_by(email='user@test.com').first()
        if not test_user:
            print("Test user (user@test.com) not found")
            return

        print(f"Test user: {test_user.name} ({test_user.email})\n")

        # Get their classes
        enrollments = ClassEnrollment.query.filter_by(student_id=test_user.id).all()
        class_ids = [e.class_id for e in enrollments]

        if not class_ids:
            print("No class enrollments found for this student\n")
            return

        print(f"Enrolled in {len(class_ids)} class(es)\n")

        # Get assignments
        assignments = ReadingAssignment.query.filter(
            ReadingAssignment.class_id.in_(class_ids)
        ).order_by(ReadingAssignment.due_date.asc().nullslast()).all()

        if not assignments:
            print("No assignments found for this student\n")
            return

        print(f"Found {len(assignments)} assignment(s):\n")

        for a in assignments:
            print(f"  Title: {a.title}")
            print(f"  Type: {a.resource_type}")
            print(f"  Book/Folder: {a.book_folder}")
            print(f"  Page ID: {a.page_id}")

            # Try to find reading time
            book_json_path = Path('data') / a.book_folder / 'book.json'
            estimated_minutes = None

            if book_json_path.exists():
                try:
                    with open(book_json_path, 'r', encoding='utf-8') as f:
                        book_data = json.load(f)
                        for page in book_data.get('pages', []):
                            if page.get('id') == a.page_id or page.get('folder') == a.page_id:
                                estimated_minutes = page.get('reading_time_minutes')
                                print(f"  ✓ Reading time found: {estimated_minutes} min")
                                break
                except Exception as e:
                    print(f"  ✗ Error reading book.json: {e}")

            if not estimated_minutes:
                print(f"  ✗ No reading time found")

            print()

if __name__ == '__main__':
    debug_assignments()
