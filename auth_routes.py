import os
import re

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from extensions import db
from models import User

auth_bp = Blueprint("auth", __name__)

# No password fallbacks: the previous defaults lived in public source, so anyone
# could read them. Unset means the test-login panel simply has nothing to show.
TEST_ADMIN_USERNAME = os.environ.get("TEST_ADMIN_USERNAME", "admin")
TEST_ADMIN_PASSWORD = os.environ.get("TEST_ADMIN_PASSWORD", "")
TEST_USER_USERNAME = os.environ.get("TEST_USER_USERNAME", "user")
TEST_USER_PASSWORD = os.environ.get("TEST_USER_PASSWORD", "")

USERNAME_RE = re.compile(r"^[a-z0-9._-]{3,80}$")


def normalize_username(raw):
    return (raw or "").strip().lower()


def _show_test_login():
    """Opt-in only. This panel prints working admin credentials onto the login
    page, so it must never appear because a variable was forgotten. It shows
    only when ENABLE_TEST_LOGIN is explicitly on AND the passwords are set.
    """
    env_value = os.environ.get("ENABLE_TEST_LOGIN", "").strip().lower()
    if env_value not in {"1", "true", "yes", "on"}:
        return False
    return bool(TEST_ADMIN_PASSWORD and TEST_USER_PASSWORD)


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        username = normalize_username(request.form.get("username", ""))
        email = request.form.get("email", "").strip().lower()  # optional
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        error = None
        if not name or not username or not password:
            error = "Name, username and password are required."
        elif not USERNAME_RE.match(username):
            error = "Username must be 3–80 characters: letters, numbers, dots, dashes or underscores."
        elif password != confirm:
            error = "Passwords do not match."
        elif len(password) < 8:
            error = "Password must be at least 8 characters."
        elif User.query.filter_by(username=username).first():
            error = "That username is already taken."
        elif email and User.query.filter_by(email=email).first():
            error = "An account with that email already exists."

        if error:
            flash(error, "error")
            return render_template("signup.html", name=name, username=username, email=email)

        user = User(name=name, username=username, email=email or None, role="student")
        user.set_password(password)
        db.session.add(user)
        db.session.flush()  # assigns user.id, needed to pick a default avatar
        from avatars import default_avatar_for
        user.avatar = default_avatar_for(user.id)
        db.session.commit()
        login_user(user)
        return redirect(url_for("dashboard"))

    return render_template("signup.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    from flask import session
    # Visiting the login page always ends any admin→student impersonation,
    # so the redirect below targets the real account, not the viewed student.
    session.pop("impersonating_student_id", None)
    session.pop("impersonation_token", None)

    if current_user.is_authenticated:
        return redirect(url_for("admin.admin_home") if current_user.is_admin() else url_for("dashboard"))

    if request.method == "POST":
        # Field is "identifier"; accept legacy "email" field name too
        identifier = request.form.get("identifier") or request.form.get("email", "")
        password = request.form.get("password", "")
        user = User.find_by_login(identifier)

        if user and user.check_password(password):
            login_user(user)
            next_url = request.args.get("next")
            if next_url:
                return redirect(next_url)
            return redirect(url_for("admin.admin_home") if user.is_admin() else url_for("dashboard"))

        flash("Invalid username or password.", "error")
        return render_template(
            "login.html", identifier=identifier.strip(),
            show_test_login=_show_test_login(), test_admin_username=TEST_ADMIN_USERNAME, test_admin_password=TEST_ADMIN_PASSWORD,
            test_user_username=TEST_USER_USERNAME, test_user_password=TEST_USER_PASSWORD,
        )

    return render_template(
        "login.html",
        show_test_login=_show_test_login(), test_admin_username=TEST_ADMIN_USERNAME, test_admin_password=TEST_ADMIN_PASSWORD,
        test_user_username=TEST_USER_USERNAME, test_user_password=TEST_USER_PASSWORD,
    )


@auth_bp.route("/logout")
@login_required
def logout():
    from flask import session
    session.pop("impersonating_student_id", None)
    session.pop("impersonation_token", None)
    logout_user()
    return redirect(url_for("index"))
