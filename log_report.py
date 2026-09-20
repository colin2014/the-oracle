"""Summarise logs/access.log and check the login requirements were enforced.

    python log_report.py                 # everything in the log
    python log_report.py --hours 24      # just the last 24 hours
    python log_report.py --dir D:\\logs   # a different log folder

The two checks that matter:
  1. Anonymous visitors must only ever be served the public pages (see request_log.PUBLIC_PATHS);
     everywhere else they must be redirected to login or refused.
  2. Students must never be served an /admin page.
"""
import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from request_log import PUBLIC_PATHS

REDIRECTS = {301, 302, 303, 307, 308}
STUDENT_ALLOWED_ADMIN = {"/admin/clear-impersonation"}   # only clears the caller's own session


def load_records(log_dir, hours=None):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours) if hours else None
    records, bad = [], 0
    for path in sorted(Path(log_dir).glob("access.log*")):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    when = datetime.strptime(rec["t"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                except (ValueError, KeyError):
                    bad += 1
                    continue
                if cutoff is None or when >= cutoff:
                    rec["_when"] = when
                    records.append(rec)
    return records, bad


def normalise(path):
    """/admin/students/5/delete -> /admin/students/<id>/delete"""
    return re.sub(r"/\d+(?=/|$)", "/<id>", path)


def analyse(records):
    out = {"total": len(records)}
    out["by_auth"] = Counter(r.get("a", "anon") for r in records)
    out["by_country"] = Counter(r.get("cc") or "??" for r in records)
    out["by_status"] = Counter(f"{str(r['s'])[0]}xx" for r in records)
    out["top_paths"] = Counter(f"{r['m']} {normalise(r['p'])}" for r in records)

    anon = [r for r in records if r.get("a", "anon") == "anon"]
    protected = [r for r in anon if not PUBLIC_PATHS.match(r["p"])]
    out["anon_protected_total"] = len(protected)
    out["anon_violations"] = Counter(f"{r['m']} {normalise(r['p'])} -> {r['s']}" for r in protected if 200 <= r["s"] < 300)
    enforced = [r for r in protected if r["s"] in (401, 403, 404, 405, 429) or (r["s"] in REDIRECTS and re.search(r"/login\b", r.get("to") or ""))]
    out["anon_enforced"] = len(enforced)
    out["anon_other"] = Counter(f"{r['m']} {normalise(r['p'])} -> {r['s']}" for r in protected
                                if r not in enforced and not (200 <= r["s"] < 300))

    out["student_admin_violations"] = Counter(
        f"{r['m']} {normalise(r['p'])} -> {r['s']} (user {r.get('u')})" for r in records
        if r.get("a") == "student" and r["p"].startswith("/admin") and 200 <= r["s"] < 300 and r["p"] not in STUDENT_ALLOWED_ADMIN)
    out["student_admin_refused"] = sum(1 for r in records if r.get("a") == "student" and r["p"].startswith("/admin") and r["s"] in (401, 403, 404))

    logins = [r for r in records if r["m"] == "POST" and r["p"] == "/login"]
    out["logins"] = Counter({302: 0, 200: 0, 429: 0}) + Counter(r["s"] for r in logins)
    fails = Counter(r.get("ip") for r in logins if r["s"] in (200, 429))
    out["login_fail_ips"] = [(ip, n) for ip, n in fails.most_common(5) if n >= 5]
    out["signups"] = Counter(r["s"] for r in records if r["m"] == "POST" and r["p"] == "/signup")

    out["not_found"] = Counter(f"{r['p']}" for r in anon if r["s"] == 404).most_common(8)
    out["problems"] = len(out["anon_violations"]) + len(out["student_admin_violations"])
    return out


def _lines(counter, limit=10, indent="    "):
    return [f"{indent}{n:>6}  {k}" for k, n in counter.most_common(limit)] or [f"{indent}(none)"]


def render(res, bad_lines=0, hours=None):
    if res["total"] == 0:
        return "No requests in the log yet."
    L = [f"ACCESS LOG REPORT  ({'last %s h' % hours if hours else 'all records'}, times are UTC)", "=" * 64,
         f"Requests: {res['total']}    unreadable lines: {bad_lines}",
         f"Visitors: " + ", ".join(f"{k} {v}" for k, v in res["by_auth"].most_common()),
         f"Status  : " + ", ".join(f"{k} {v}" for k, v in sorted(res["by_status"].items())),
         f"Country : " + ", ".join(f"{k} {v}" for k, v in res["by_country"].most_common(8)), ""]

    L.append("LOGIN REQUIREMENTS")
    L.append("-" * 64)
    L.append(f"Anonymous requests to protected pages: {res['anon_protected_total']}  "
             f"(turned away or sent to login: {res['anon_enforced']})")
    if res["anon_violations"]:
        L.append("  !! Anonymous visitor was SERVED a protected page:")
        L += _lines(res["anon_violations"], indent="       ")
    else:
        L.append("  OK: no anonymous visitor was served a protected page")
    if res["anon_other"]:
        L.append("  (other outcomes, e.g. errors or bad requests:)")
        L += _lines(res["anon_other"], 6, indent="       ")
    L.append(f"Students who tried /admin pages and were refused: {res['student_admin_refused']}")
    if res["student_admin_violations"]:
        L.append("  !! A student was SERVED an admin page:")
        L += _lines(res["student_admin_violations"], indent="       ")
    else:
        L.append("  OK: no student was served an admin page")
    L.append("")

    L.append("SIGN-INS")
    L.append("-" * 64)
    lg = res["logins"]
    L.append(f"Logins: {lg[302]} succeeded, {lg[200]} failed, {lg[429]} rate-limited")
    for ip, n in res["login_fail_ips"]:
        L.append(f"  !! {n} failed/blocked logins from {ip}")
    sg = res["signups"]
    L.append(f"Signups: {sg[302]} created, {sg[200]} rejected, {sg[429]} rate-limited")
    L.append("")

    L.append("BUSIEST PAGES")
    L.append("-" * 64)
    L += _lines(res["top_paths"], 12)
    if res["not_found"]:
        L += ["", "PAGES THAT DON'T EXIST, asked for by anonymous visitors (scanners look like this)"]
        L += [f"    {n:>6}  {p}" for p, n in res["not_found"]]
    L += ["", "VERDICT: " + ("login requirements are being met." if res["problems"] == 0
                             else f"{res['problems']} problem(s) above need attention.")]
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hours", type=float, help="only look at the last N hours")
    ap.add_argument("--dir", default=str(Path(__file__).resolve().parent / "logs"), help="folder holding access.log")
    args = ap.parse_args(argv)
    records, bad = load_records(args.dir, args.hours)
    print(render(analyse(records), bad, args.hours))
    return 0


if __name__ == "__main__":
    sys.exit(main())
