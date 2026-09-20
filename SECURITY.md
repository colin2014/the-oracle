# Security Policy

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Report them privately through GitHub's
[private vulnerability reporting](https://github.com/colin2014/the-oracle/security/advisories/new)
(Security tab → Report a vulnerability). This keeps the details between us
until a fix is available.

Please include:

- The type of issue (e.g. authentication bypass, injection, data exposure)
- Where the affected code lives (file paths, routes, or a commit)
- Steps to reproduce, and a proof of concept if you have one
- What an attacker could achieve with it

You can expect an acknowledgement within **5 working days** and a view on
whether the report is accepted, with an expected fix timeline, within
**10 working days**.

## Scope

This project is an educational content-management system that handles
**student data**. Reports touching the following are especially welcome:

- Authentication, session handling, and the admin role boundary
- Access control between teachers, classes, and students
- Exposure of student records or the local teacher name mappings
- Injection of any kind, and file-upload handling

## Out of Scope

- Vulnerabilities requiring `ENABLE_TEST_LOGIN=true`, which is a
  development-only setting that is off by default
- Reports against a deployment running with `FLASK_DEBUG` enabled
- Findings from automated scanners with no demonstrated impact

## Deployment Notes

If you run your own instance:

- `SECRET_KEY` **must** be set to a strong random value. The app refuses to
  start without it outside development. Sharing or reusing this key allows
  session forgery.
- Leave `ENABLE_TEST_LOGIN` unset or `false` in production. When enabled,
  the login page displays working credentials.
- Never commit `.env`. Copy `.env.example` instead.
- `teacher_names/` holds real student names and must stay off version
  control; it is gitignored by default.
