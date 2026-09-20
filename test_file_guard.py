"""Regression tests for the /data/ file guard.

Run:  python -m unittest test_file_guard -v

Bug this guards: a name-based block on 'app.db' was bypassed on Windows by 'APP.DB',
'app.db.', 'app.db ' and 'app.db::$DATA', letting any logged-in user download the
whole SQLite database (every password hash) from /data/<name>.
"""
import os
import tempfile
import unittest
from pathlib import Path

from file_guard import is_servable


class FileGuardTests(unittest.TestCase):
    def test_database_spellings_are_refused(self):
        for bad in ("app.db", "APP.DB", "App.Db", "app.db.", "app.db ", "APP.DB.",
                    "app.db::$DATA", "app.db:$DATA", "app.db-wal", "app.db-journal",
                    "sub/app.db", "backup.db", "x.sqlite", "app.db.bak"):
            with self.subTest(bad=bad):
                self.assertFalse(is_servable(bad))

    def test_secrets_and_code_are_refused(self):
        for bad in (".env", "config.json", "books.json", "notes.txt", "x.py", "x.html", "x.png.exe", "noextension"):
            with self.subTest(bad=bad):
                self.assertFalse(is_servable(bad))

    def test_control_characters_and_empty_are_refused(self):
        for bad in ("", None, "a\x00.png", "a\n.png"):
            with self.subTest(bad=repr(bad)):
                self.assertFalse(is_servable(bad))

    def test_real_assets_still_served(self):
        for good in ("Book_93/images/fig1.png", "Book_93/images/Photo.JPG", "ee_exemplars/essay.pdf",
                     "covers/a.webp", "unit_plan_resources/slides.pptx", "x/y/z.svg"):
            with self.subTest(good=good):
                self.assertTrue(is_servable(good))

    def test_same_file_check_catches_a_renamed_alias(self):
        # Even an allowlisted extension must never resolve to the database itself.
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "app.db"
            db.write_bytes(b"SQLite format 3\x00")
            alias = Path(tmp) / "alias.png"
            try:
                os.link(db, alias)          # hard link: same file, innocent name
            except OSError:
                self.skipTest("hard links unavailable here")
            self.assertFalse(is_servable("alias.png", tmp, db))
            (Path(tmp) / "real.png").write_bytes(b"\x89PNG")
            self.assertTrue(is_servable("real.png", tmp, db))


if __name__ == "__main__":
    unittest.main()
