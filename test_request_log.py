"""Run:  python -m unittest test_request_log -v

No database or login setup needed: a tiny Flask app stands in for the real one.
"""
import json
import logging
import tempfile
import unittest
from pathlib import Path

from flask import Flask, jsonify, redirect

import log_report
from request_log import LOGGER_NAME, PUBLIC_PATHS, SKIP_PATHS, init_request_logging


def make_app(log_dir):
    app = Flask(__name__)
    init_request_logging(app, log_dir=log_dir)

    @app.route("/")
    def home():
        return "home"

    @app.route("/login", methods=["GET", "POST"])
    def login():
        return "login page"

    @app.route("/admin/students")
    def admin():
        return redirect("/login?next=/admin/students", 302)

    @app.route("/boom")
    def boom():
        raise RuntimeError("secret internal detail")

    @app.route("/api/activity/ping", methods=["POST"])
    def ping():
        return jsonify(ok=True)

    return app


class RequestLogTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = make_app(self.tmp.name)
        self.client = self.app.test_client()

    def tearDown(self):
        for h in list(logging.getLogger(LOGGER_NAME).handlers):
            h.close()
            logging.getLogger(LOGGER_NAME).removeHandler(h)
        self.tmp.cleanup()

    def lines(self):
        for h in logging.getLogger(LOGGER_NAME).handlers:
            h.flush()
        path = Path(self.tmp.name) / "access.log"
        return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []

    def test_one_json_line_per_page_with_the_expected_fields(self):
        self.client.get("/", headers={"CF-IPCountry": "GB", "User-Agent": "TestBrowser/1.0"})
        (rec,) = self.lines()
        self.assertEqual((rec["m"], rec["p"], rec["s"], rec["a"], rec["cc"]), ("GET", "/", 200, "anon", "GB"))
        self.assertEqual(rec["ua"], "TestBrowser/1.0")
        self.assertRegex(rec["t"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        self.assertIsInstance(rec["ms"], int)
        self.assertNotIn("u", rec)                       # anonymous: no user id

    def test_query_strings_and_form_bodies_never_reach_the_log(self):
        self.client.get("/?token=SECRETTOKEN&next=/x")
        self.client.post("/login", data={"identifier": "someone", "password": "hunter2-hunter2"})
        text = (Path(self.tmp.name) / "access.log").read_text(encoding="utf-8")
        for secret in ("SECRETTOKEN", "hunter2", "someone", "?"):
            self.assertNotIn(secret, text)

    def test_redirect_target_is_recorded_without_its_query(self):
        self.client.get("/admin/students")
        (rec,) = self.lines()
        self.assertEqual((rec["s"], rec["to"]), (302, "/login"))

    def test_noisy_paths_are_skipped(self):
        self.client.post("/api/activity/ping")
        self.client.get("/health")
        self.client.get("/static/css/style.css")
        self.assertEqual(self.lines(), [])
        for skipped in ("/class-games/play/12/state", "/class-games/session/3/board/state", "/favicon.ico"):
            self.assertTrue(SKIP_PATHS.match(skipped), skipped)
        self.assertFalse(SKIP_PATHS.match("/class-games/join"))

    def test_an_error_page_is_still_logged_and_the_response_is_unharmed(self):
        self.app.config["PROPAGATE_EXCEPTIONS"] = False
        r = self.client.get("/boom")
        self.assertEqual(r.status_code, 500)
        self.assertEqual([x["s"] for x in self.lines()], [500])
        self.assertNotIn("secret internal detail", json.dumps(self.lines()))

    def test_logging_failures_can_never_break_a_request(self):
        for h in logging.getLogger(LOGGER_NAME).handlers:
            h.emit = lambda record: (_ for _ in ()).throw(OSError("disk full"))
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_public_page_list(self):
        for ok in ("/", "/login", "/signup", "/logout", "/health", "/favicon.ico", "/static/x.css", "/admin/view-as-student/embed/7"):
            self.assertTrue(PUBLIC_PATHS.match(ok), ok)
        for private in ("/dashboard", "/admin/students", "/api/books", "/data/x.png", "/admin/view-as-student/embed/7/x"):
            self.assertFalse(PUBLIC_PATHS.match(private), private)


class ReportTests(unittest.TestCase):
    @staticmethod
    def rec(m, p, s, a="anon", u=None, to=None, ip="1.2.3.4", cc="GB"):
        r = {"t": "2026-09-20T12:00:00Z", "ip": ip, "cc": cc, "m": m, "p": p, "s": s, "a": a}
        if u is not None:
            r["u"] = u
        if to:
            r["to"] = to
        return r

    def analyse(self, *recs):
        return log_report.analyse(list(recs))

    def test_clean_traffic_reports_no_problems(self):
        res = self.analyse(self.rec("GET", "/", 200), self.rec("GET", "/dashboard", 302, to="/login"),
                           self.rec("GET", "/api/books", 401), self.rec("GET", "/dashboard", 200, a="student", u=5),
                           self.rec("GET", "/admin/students", 403, a="student", u=5), self.rec("GET", "/admin/students", 200, a="admin", u=1))
        self.assertEqual(res["problems"], 0)
        self.assertEqual(res["anon_enforced"], 2)
        self.assertEqual(res["student_admin_refused"], 1)

    def test_anonymous_served_a_protected_page_is_flagged(self):
        res = self.analyse(self.rec("GET", "/admin/students", 200), self.rec("GET", "/api/books", 200))
        self.assertEqual(res["problems"], 2)
        self.assertIn("GET /admin/students -> 200", res["anon_violations"])

    def test_a_redirect_that_is_not_to_login_does_not_count_as_enforced(self):
        res = self.analyse(self.rec("GET", "/dashboard", 302, to="/somewhere-else"))
        self.assertEqual(res["anon_enforced"], 0)
        self.assertEqual(res["problems"], 0)              # not served, so not a violation, but shown as 'other'
        self.assertTrue(res["anon_other"])

    def test_student_served_an_admin_page_is_flagged_except_clear_impersonation(self):
        res = self.analyse(self.rec("GET", "/admin/students", 200, a="student", u=9),
                           self.rec("POST", "/admin/clear-impersonation", 200, a="student", u=9),
                           self.rec("POST", "/admin/students/4/reset-password", 200, a="student", u=9))
        self.assertEqual(res["problems"], 2)
        self.assertTrue(any("reset-password" in k and "<id>" in k for k in res["student_admin_violations"]))

    def test_login_counts_and_brute_force_hint(self):
        recs = [self.rec("POST", "/login", 200, ip="9.9.9.9") for _ in range(6)] + [self.rec("POST", "/login", 302, a="student", u=2)]
        res = self.analyse(*recs)
        self.assertEqual((res["logins"][302], res["logins"][200]), (1, 6))
        self.assertEqual(res["login_fail_ips"], [("9.9.9.9", 6)])

    def test_render_states_the_verdict(self):
        good = log_report.render(self.analyse(self.rec("GET", "/", 200)))
        bad = log_report.render(self.analyse(self.rec("GET", "/admin/students", 200)))
        self.assertIn("login requirements are being met", good)
        self.assertIn("1 problem(s)", bad)
        self.assertEqual(log_report.render(self.analyse()), "No requests in the log yet.")


if __name__ == "__main__":
    unittest.main()
