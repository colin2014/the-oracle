#!/usr/bin/env python
"""Create test user accounts for development/testing."""

import os
from app import app, db
from models import User, Class, ClassEnrollment

def create_test_users():
    with app.app_context():
        # Test Admin User
        admin_username = os.environ.get("TEST_ADMIN_USERNAME", "admin")
        admin_password = os.environ.get("TEST_ADMIN_PASSWORD", "adminpass123")

        admin_user = User.query.filter_by(username=admin_username).first()
        if not admin_user:
            admin_user = User(
                username=admin_username,
                email=os.environ.get("TEST_ADMIN_EMAIL", "admin@test.com"),
                name="Test Admin",
                role="admin"
            )
            admin_user.set_password(admin_password)
            db.session.add(admin_user)
            print(f"[OK] Created test admin: {admin_username} / {admin_password}")
        else:
            print(f"[OK] Test admin already exists: {admin_username}")

        # Test Student User
        user_username = os.environ.get("TEST_USER_USERNAME", "user")
        user_password = os.environ.get("TEST_USER_PASSWORD", "userpass123")

        test_user = User.query.filter_by(username=user_username).first()
        if not test_user:
            test_user = User(
                username=user_username,
                email=os.environ.get("TEST_USER_EMAIL", "user@test.com"),
                name="Test User",
                role="student"
            )
            test_user.set_password(user_password)
            db.session.add(test_user)
            print(f"[OK] Created test user: {user_username} / {user_password}")
        else:
            print(f"[OK] Test user already exists: {user_username}")

        db.session.commit()

        # Create Test Class and enroll test user
        test_class = Class.query.filter_by(name="Test class").first()
        if not test_class:
            test_class = Class(name="Test class", created_by_id=admin_user.id)
            db.session.add(test_class)
            db.session.flush()
            enrollment = ClassEnrollment(class_id=test_class.id, student_id=test_user.id)
            db.session.add(enrollment)
            print(f"[OK] Created 'Test class' and enrolled test user")
        else:
            print(f"[OK] Test class already exists")

        db.session.commit()
        print("\n[OK] Test users and class setup complete!")

if __name__ == "__main__":
    create_test_users()
