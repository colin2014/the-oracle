"""Nightly safe copy of data/app.db.

Uses SQLite's online backup API, so the copy is consistent even while the app is
writing (copying the raw file mid-write can produce a corrupt backup). Every copy
is integrity-checked, and copies older than KEEP_DAYS are deleted.

Usage: python backup_db.py [backup_dir]      (default: D:\\OracleBackups)
Exit code is non-zero on any failure, so Task Scheduler shows it as failed.
"""
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

SOURCE = Path(__file__).resolve().parent / "data" / "app.db"
DEFAULT_DEST = Path(r"D:\OracleBackups")
KEEP_DAYS = 14


def log(dest, message):
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S}  {message}"
    print(line)
    try:
        with open(dest / "backup.log", "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        pass


def main():
    dest = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DEST
    if not dest.parent.exists():
        print(f"ERROR: {dest.parent} is not available (is the USB stick plugged in?)")
        return 2
    dest.mkdir(exist_ok=True)

    target = dest / f"app-{datetime.now():%Y%m%d-%H%M%S}.db"
    src = sqlite3.connect(f"file:{SOURCE}?mode=ro", uri=True, timeout=30)
    out = sqlite3.connect(target)
    try:
        src.backup(out)
    finally:
        out.close()
        src.close()

    check = sqlite3.connect(f"file:{target}?mode=ro", uri=True)
    try:
        verdict = check.execute("PRAGMA integrity_check").fetchone()[0]
        tables = check.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
    finally:
        check.close()
    if verdict != "ok":
        log(dest, f"FAILED integrity check on {target.name}: {verdict}")
        target.unlink(missing_ok=True)
        return 3
    log(dest, f"OK {target.name}  {target.stat().st_size / 1e6:.1f} MB  tables={tables}")

    cutoff = time.time() - KEEP_DAYS * 86400
    for old in dest.glob("app-*.db"):
        if old != target and old.stat().st_mtime < cutoff:
            old.unlink()
            log(dest, f"pruned {old.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
