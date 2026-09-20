"""Decides whether a path under data/ may be served to a logged-in user.

data/ holds book images and PDFs, but also app.db. Blocking by file *name* is not
enough on Windows, where "APP.DB", "app.db." (trailing dot), "app.db " (trailing
space) and "app.db::$DATA" (NTFS alternate stream) all open the same file. So this
is an allowlist of asset types, plus a same-file check against the database.
"""
import os
from pathlib import Path

SERVABLE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico",
    ".pdf", ".pptx", ".mp4", ".webm", ".mp3",
}


def is_servable(filepath, data_dir="data", db_path=None):
    if not filepath or ":" in filepath or any(ord(ch) < 32 for ch in filepath):
        return False
    name = Path(filepath).name
    # splitext("x.png.") -> ".", splitext("app.db ") -> ".db " : neither is allowlisted
    if os.path.splitext(name)[1].lower() not in SERVABLE_EXTENSIONS:
        return False
    if db_path is not None:
        target = Path(data_dir) / filepath
        try:
            if target.exists() and os.path.samefile(target, db_path):
                return False
        except OSError:
            return False
    return True
