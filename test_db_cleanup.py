"""Run:  python -m unittest test_db_cleanup -v

Bug this guards: deleting a student removed only the users row, leaving their progress
behind for the next account to inherit when SQLite reused the id.
"""
import unittest

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from db_cleanup import purge_dependents

SCHEMA = [
    "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)",
    "CREATE TABLE classes (id INTEGER PRIMARY KEY, name TEXT)",
    "CREATE TABLE enrollments (id INTEGER PRIMARY KEY, student_id INTEGER REFERENCES users(id), class_id INTEGER REFERENCES classes(id))",
    "CREATE TABLE papers (id INTEGER PRIMARY KEY, owner_id INTEGER REFERENCES users(id))",
    "CREATE TABLE submissions (id INTEGER PRIMARY KEY, student_id INTEGER REFERENCES users(id), paper_id INTEGER REFERENCES papers(id))",
    # grandchild: reachable only through submissions
    "CREATE TABLE answers (id INTEGER PRIMARY KEY, submission_id INTEGER REFERENCES submissions(id), reviewed_by_id INTEGER REFERENCES users(id))",
    # great-grandchild
    "CREATE TABLE insights (id INTEGER PRIMARY KEY, answer_id INTEGER REFERENCES answers(id))",
    "CREATE TABLE progress (id INTEGER PRIMARY KEY, student_id INTEGER REFERENCES users(id))",
    # self-reference must not loop forever
    "CREATE TABLE folders (id INTEGER PRIMARY KEY, parent_id INTEGER REFERENCES folders(id), user_id INTEGER REFERENCES users(id))",
]


class PurgeDependentsTests(unittest.TestCase):
    def setUp(self):
        self.session = sessionmaker(bind=create_engine("sqlite://"))()
        for stmt in SCHEMA:
            self.session.execute(text(stmt))
        s = self.session
        s.execute(text("INSERT INTO users VALUES (1,'admin'),(2,'alice'),(3,'bob')"))
        s.execute(text("INSERT INTO classes VALUES (1,'2027')"))
        s.execute(text("INSERT INTO enrollments VALUES (1,2,1),(2,3,1)"))
        s.execute(text("INSERT INTO papers VALUES (1,1)"))
        s.execute(text("INSERT INTO submissions VALUES (1,2,1),(2,3,1)"))
        s.execute(text("INSERT INTO answers VALUES (1,1,1),(2,1,1),(3,2,1)"))
        s.execute(text("INSERT INTO insights VALUES (1,1),(2,2),(3,3)"))
        s.execute(text("INSERT INTO progress VALUES (1,2),(2,2),(3,3)"))
        s.execute(text("INSERT INTO folders VALUES (1,NULL,2),(2,1,2),(3,NULL,3)"))
        s.commit()

    def count(self, table, where="1=1"):
        return self.session.execute(text(f"SELECT COUNT(*) FROM {table} WHERE {where}")).scalar()

    def test_removes_every_dependent_row_at_every_depth(self):
        counts = purge_dependents(self.session, "users", [2])
        self.assertEqual(self.count("enrollments", "student_id=2"), 0)
        self.assertEqual(self.count("submissions", "student_id=2"), 0)
        self.assertEqual(self.count("answers", "submission_id=1"), 0)      # grandchild
        self.assertEqual(self.count("insights", "answer_id IN (1,2)"), 0)  # great-grandchild
        self.assertEqual(self.count("progress", "student_id=2"), 0)
        self.assertEqual(self.count("folders", "user_id=2"), 0)
        self.assertEqual(counts["answers"], 2)
        self.assertEqual(counts["insights"], 2)

    def test_leaves_other_users_data_alone(self):
        purge_dependents(self.session, "users", [2])
        self.assertEqual(self.count("enrollments", "student_id=3"), 1)
        self.assertEqual(self.count("submissions", "student_id=3"), 1)
        self.assertEqual(self.count("answers", "submission_id=2"), 1)
        self.assertEqual(self.count("insights", "answer_id=3"), 1)
        self.assertEqual(self.count("progress", "student_id=3"), 1)
        self.assertEqual(self.count("papers"), 1)                          # the admin's paper survives
        self.assertEqual(self.count("classes"), 1)

    def test_does_not_delete_the_parent_row_itself(self):
        purge_dependents(self.session, "users", [2])
        self.assertEqual(self.count("users", "id=2"), 1)

    def test_no_foreign_key_violations_after_deleting_the_parent(self):
        purge_dependents(self.session, "users", [2])
        self.session.execute(text("DELETE FROM users WHERE id=2"))
        self.assertEqual(self.session.execute(text("PRAGMA foreign_key_check")).fetchall(), [])

    def test_a_new_user_reusing_the_id_inherits_nothing(self):
        purge_dependents(self.session, "users", [3])      # bob is the newest id
        self.session.execute(text("DELETE FROM users WHERE id=3"))
        self.session.execute(text("INSERT INTO users VALUES (3,'carol')"))   # SQLite hands id 3 out again
        for table, col in (("enrollments", "student_id"), ("submissions", "student_id"),
                           ("progress", "student_id"), ("folders", "user_id")):
            self.assertEqual(self.count(table, f"{col}=3"), 0, table)

    def test_deleting_several_users_at_once_and_empty_input(self):
        purge_dependents(self.session, "users", [2, 3])
        self.assertEqual(self.count("progress"), 0)
        self.assertEqual(purge_dependents(self.session, "users", []), {})
        self.assertEqual(purge_dependents(self.session, "users", [999]), {})

    def test_reviewer_column_is_followed_too(self):
        # answers.reviewed_by_id -> users.id: deleting the reviewer removes the answers they reviewed
        purge_dependents(self.session, "users", [1])
        self.assertEqual(self.count("answers"), 0)


if __name__ == "__main__":
    unittest.main()
