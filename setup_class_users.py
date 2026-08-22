#!/usr/bin/env python
"""Setup class structure with playful aliases and emoji avatars."""

import os
from app import app, db
from models import User, Class, ClassEnrollment

# Playful aliases with assigned emojis
CLASS_OF_27_HL = [
    ("🦊 Pixel Fox", "fox"),
    ("🐻 Code Bear", "bear"),
    ("🐼 Data Panda", "panda"),
]

CLASS_OF_28_HL = [
    ("🦁 Logic Lion", "lion"),
    ("🐯 Algorithm Tiger", "tiger"),
    ("🦉 Wise Owl", "owl"),
    ("🦊 Swift Fox", "fox"),
    ("🐰 Quick Bunny", "bunny"),
    ("🐬 Smart Dolphin", "dolphin"),
]

CLASS_OF_28_SL = [
    ("🐢 Steady Turtle", "turtle"),
    ("🐸 Leap Frog", "frog"),
]

def setup_classes():
    with app.app_context():
        # Get admin user
        admin = User.query.filter_by(username="admin").first()
        if not admin:
            print("[ERROR] Admin user not found. Create test users first with create_test_users.py")
            return

        # Get test user to preserve
        test_user = User.query.filter_by(username="user").first()
        preserved_usernames = {"admin", "user"}

        # Delete all other users (except admin and test user)
        users_to_delete = User.query.filter(
            ~User.username.in_(preserved_usernames)
        ).all()

        for user in users_to_delete:
            print(f"[DELETE] Deleting user: {user.username}")
            db.session.delete(user)

        db.session.commit()
        print(f"[OK] Deleted {len(users_to_delete)} users, preserved admin and test user\n")

        # Create Class of 27 with 3 HL students
        class_27 = Class.query.filter_by(name="Class of 27").first()
        if class_27:
            # Delete existing enrollments
            for enrollment in class_27.enrollments:
                db.session.delete(enrollment)
            db.session.delete(class_27)
            db.session.commit()

        class_27 = Class(name="Class of 27", created_by_id=admin.id)
        db.session.add(class_27)
        db.session.flush()

        for name, avatar_key in CLASS_OF_27_HL:
            user = User(
                username=name.lower().replace(" ", "_").replace("🦊", "").replace("🐻", "").replace("🐼", "").strip(),
                name=name,
                role="student",
                avatar=avatar_key,
                email=f"{avatar_key}_{class_27.id}@student.local"
            )
            user.set_password("student123")
            db.session.add(user)
            db.session.flush()

            enrollment = ClassEnrollment(
                class_id=class_27.id,
                student_id=user.id,
                level="HL"
            )
            db.session.add(enrollment)
            print(f"[OK] Created student: {name} (HL) - Avatar: {avatar_key}")

        db.session.commit()
        print(f"[OK] Class of 27 created with 3 HL students\n")

        # Create Class of 28 with 6 HL and 2 SL students
        class_28 = Class.query.filter_by(name="Class of 28").first()
        if class_28:
            # Delete existing enrollments
            for enrollment in class_28.enrollments:
                db.session.delete(enrollment)
            db.session.delete(class_28)
            db.session.commit()

        class_28 = Class(name="Class of 28", created_by_id=admin.id)
        db.session.add(class_28)
        db.session.flush()

        # Add HL students for Class of 28
        for name, avatar_key in CLASS_OF_28_HL:
            user = User(
                username=name.lower().replace(" ", "_").replace("🦁", "").replace("🐯", "").replace("🦉", "").replace("🦊", "").replace("🐰", "").replace("🐬", "").strip(),
                name=name,
                role="student",
                avatar=avatar_key,
                email=f"{avatar_key}_{class_28.id}_hl@student.local"
            )
            user.set_password("student123")
            db.session.add(user)
            db.session.flush()

            enrollment = ClassEnrollment(
                class_id=class_28.id,
                student_id=user.id,
                level="HL"
            )
            db.session.add(enrollment)
            print(f"[OK] Created student: {name} (HL) - Avatar: {avatar_key}")

        # Add SL students for Class of 28
        for name, avatar_key in CLASS_OF_28_SL:
            user = User(
                username=name.lower().replace(" ", "_").replace("🐢", "").replace("🐸", "").strip(),
                name=name,
                role="student",
                avatar=avatar_key,
                email=f"{avatar_key}_{class_28.id}_sl@student.local"
            )
            user.set_password("student123")
            db.session.add(user)
            db.session.flush()

            enrollment = ClassEnrollment(
                class_id=class_28.id,
                student_id=user.id,
                level="SL"
            )
            db.session.add(enrollment)
            print(f"[OK] Created student: {name} (SL) - Avatar: {avatar_key}")

        db.session.commit()
        print(f"[OK] Class of 28 created with 6 HL and 2 SL students\n")
        print("\n[OK] Class setup complete!")
        print("\nSummary:")
        print("- Admin and Test user preserved")
        print("- Class of 27: 3 HL students")
        print("- Class of 28: 6 HL + 2 SL students")
        print("- All students have playful aliases and emoji avatars")

if __name__ == "__main__":
    setup_classes()
