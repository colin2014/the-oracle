"""Setup clean test data with specific class and student configurations."""

from app import app, db
from models import User, Class, ClassEnrollment


def setup_test_data():
    """Clean up users and create test classes with specific student configurations."""

    with app.app_context():
        db.create_all()

        # Delete all existing data
        print("Cleaning up existing data...")
        ClassEnrollment.query.delete()
        Class.query.delete()
        User.query.delete()
        db.session.commit()
        print("  [OK] Users and classes deleted")

        # Create admin user
        print("\nCreating admin user...")
        admin = User(
            username='admin',
            email='admin@test.local',
            name='Admin User',
            role='admin'
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print(f"  [OK] Admin created: admin / admin123")

        # CLASS 1: 5 students (mix of HL and SL)
        print("\nCreating Class 1 (5 students, mix HL/SL)...")
        class1 = Class(name='Class 1 - Small Mixed', created_by_id=admin.id)
        db.session.add(class1)
        db.session.commit()

        class1_students = [
            ('student_1a', 'Alice Smith', 'HL'),
            ('student_1b', 'Bob Jones', 'HL'),
            ('student_1c', 'Charlie Brown', 'SL'),
            ('student_1d', 'Diana Prince', 'HL'),
            ('student_1e', 'Eve Wilson', 'SL'),
        ]

        for username, name, level in class1_students:
            student = User(
                username=username,
                email=f'{username}@test.local',
                name=name,
                role='student'
            )
            student.set_password('student123')
            db.session.add(student)
            db.session.flush()

            enrollment = ClassEnrollment(
                class_id=class1.id,
                student_id=student.id,
                level=level
            )
            db.session.add(enrollment)

        db.session.commit()
        print(f"  [OK] 5 students created (3 HL, 2 SL)")

        # CLASS 2: 28 students (8 in: 2 SL, 6 HL)
        print("\nCreating Class 2 (28 students, 8 active: 2 SL + 6 HL)...")
        class2 = Class(name='Class 2 - Mixed Large', created_by_id=admin.id)
        db.session.add(class2)
        db.session.commit()

        # Active students: 2 SL + 6 HL
        active_students = [
            ('student_2a', 'Alice Anderson', 'SL'),
            ('student_2b', 'Bob Baker', 'SL'),
            ('student_2c', 'Charlie Clark', 'HL'),
            ('student_2d', 'Diana Davis', 'HL'),
            ('student_2e', 'Eve Evans', 'HL'),
            ('student_2f', 'Frank Foster', 'HL'),
            ('student_2g', 'Grace Green', 'HL'),
            ('student_2h', 'Henry Harris', 'HL'),
        ]

        for username, name, level in active_students:
            student = User(
                username=username,
                email=f'{username}@test.local',
                name=name,
                role='student'
            )
            student.set_password('student123')
            db.session.add(student)
            db.session.flush()

            enrollment = ClassEnrollment(
                class_id=class2.id,
                student_id=student.id,
                level=level
            )
            db.session.add(enrollment)

        # Additional 20 students (inactive/unenrolled for now)
        for i in range(9, 29):
            student = User(
                username=f'student_2x{i:02d}',
                email=f'student_2x{i:02d}@test.local',
                name=f'Student X{i}',
                role='student'
            )
            student.set_password('student123')
            db.session.add(student)
            # Not enrolled in class 2

        db.session.commit()
        print(f"  [OK] 28 students created (8 active: 2 SL + 6 HL, 20 inactive)")

        # CLASS 3: 27 students (3 HL)
        print("\nCreating Class 3 (27 students, 3 HL)...")
        class3 = Class(name='Class 3 - Large HL Focus', created_by_id=admin.id)
        db.session.add(class3)
        db.session.commit()

        # 3 HL students
        hl_students = [
            ('student_3a', 'Alice Alvarez', 'HL'),
            ('student_3b', 'Bob Bennett', 'HL'),
            ('student_3c', 'Charlie Carter', 'HL'),
        ]

        for username, name, level in hl_students:
            student = User(
                username=username,
                email=f'{username}@test.local',
                name=name,
                role='student'
            )
            student.set_password('student123')
            db.session.add(student)
            db.session.flush()

            enrollment = ClassEnrollment(
                class_id=class3.id,
                student_id=student.id,
                level=level
            )
            db.session.add(enrollment)

        # Additional 24 SL students
        for i in range(4, 28):
            student = User(
                username=f'student_3s{i:02d}',
                email=f'student_3s{i:02d}@test.local',
                name=f'Student SL{i}',
                role='student'
            )
            student.set_password('student123')
            db.session.add(student)
            db.session.flush()

            enrollment = ClassEnrollment(
                class_id=class3.id,
                student_id=student.id,
                level='SL'
            )
            db.session.add(enrollment)

        db.session.commit()
        print(f"  [OK] 27 students created (3 HL, 24 SL)")

        # Summary
        print("\n" + "="*50)
        print("TEST DATA SETUP COMPLETE")
        print("="*50)
        print("\nClasses created:")
        print("  1. Class 1 - Small Mixed (5 students: 3 HL, 2 SL)")
        print("  2. Class 2 - Mixed Large (28 students: 8 active [6 HL, 2 SL], 20 inactive)")
        print("  3. Class 3 - Large HL Focus (27 students: 3 HL, 24 SL)")
        print("\nLogin credentials:")
        print("  Admin: admin / admin123")
        print("  Students: student_1a / student123 (and other usernames)")
        print("\nTotal users created: 1 admin + 63 students = 64 users")
        print("="*50 + "\n")


if __name__ == '__main__':
    setup_test_data()
