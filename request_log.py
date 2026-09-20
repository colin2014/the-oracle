"""Access log: one JSON line per page request, so we can see who visits what.

Each line records the time (UTC), visitor IP and country, method, path, status, how long
it took, the browser (truncated), and who the visitor was: anonymous, a student or the
admin, plus their user id. For redirects it records where they were sent.

Deliberately NOT logged: query strings (they can hold tokens), request bodies, cookies,
and anything typed into a form. That keeps passwords and login attempts out of the log.
A failed login is simply `POST /login -> 200`; a successful one is `-> 302`.

Written to logs/access.log (git-ignored), rotated nightly, 30 days kept. Read it with
`python log_report.py`.
"""
import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from urllib.parse import urlsplit

from flask import g, request

LOGGER_NAME = "oracle.access"

# High-frequency or uninteresting requests that would drown the log.
SKIP_PATHS = re.compile(
    r"^/(static/|health$|favicon\.ico$|service-worker\.js$|api/activity/ping$"
    r"|class-games/play/\d+/state$|class-games/session/\d+/board/state$)"
)

# Pages an anonymous visitor is MEANT to be able to open. Everything else must turn them
# away. Shared with log_report.py, which flags any anonymous success outside this list.
PUBLIC_PATHS = re.compile(
    # /logout only ends a session and redirects. The line is written after the session has
    # ended, so a genuine logout is recorded as "anonymous" and must not look like a breach.
    r"^/(login|signup|logout|health|favicon\.ico|service-worker\.js)?$"
    r"|^/static/"
    r"|^/admin/view-as-student/embed/\d+$"      # protected by a signed, expiring token
)


def _who():
    """('anon'|'student'|'admin', user id or None). Never raises."""
    try:
        from flask_login import current_user
        if current_user.is_authenticated:
            return ("admin" if current_user.is_admin() else "student"), int(current_user.get_id())
    except Exception:  # noqa: BLE001 - logging must never break a request
        pass
    return "anon", None


def _redirect_target(response):
    loc = response.headers.get("Location")
    if not loc or not (300 <= response.status_code < 400):
        return None
    return urlsplit(loc).path[:200] or None


def init_request_logging(app, log_dir=None, keep_days=30):
    directory = Path(log_dir or os.environ.get("ORACLE_LOG_DIR") or Path(__file__).resolve().parent / "logs")
    directory.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False                      # keep it out of the app's own log
    for old in list(logger.handlers):             # safe if the app is initialised twice (tests)
        logger.removeHandler(old)
        old.close()
    handler = TimedRotatingFileHandler(directory / "access.log", when="midnight", backupCount=keep_days,
                                       encoding="utf-8", delay=True)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)

    @app.before_request
    def _start_timer():
        g._access_started = time.perf_counter()

    @app.after_request
    def _write_line(response):
        try:
            if SKIP_PATHS.match(request.path):
                return response
            auth, uid = _who()
            started = getattr(g, "_access_started", None)
            record = {
                "t": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "ip": request.remote_addr,
                "cc": request.headers.get("CF-IPCountry", "")[:2] or None,
                "m": request.method,
                "p": request.path[:200],
                "s": response.status_code,
                "ms": round((time.perf_counter() - started) * 1000) if started else None,
                "a": auth,
                "u": uid,
                "ua": (request.headers.get("User-Agent") or "")[:100] or None,
                "to": _redirect_target(response),
            }
            logger.info(json.dumps({k: v for k, v in record.items() if v is not None}, separators=(",", ":")))
        except Exception:  # noqa: BLE001
            pass
        return response

    return logger
