import hmac
import os
import re

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from extensions import db, limiter
from models import User

auth_bp = Blueprint("auth", __name__)

# Signup is gated by a shared code so a public URL can't be used to mass-create
# accounts. Unset means signup is closed. Compared in constant time.
SIGNUP_CODE = os.environ.get("SIGNUP_CODE", "").strip()

# No password fallbacks: the previous defaults lived in public source, so anyone
# could read them. Unset means the test-login panel simply has nothing to show.
TEST_ADMIN_USERNAME = os.environ.get("TEST_ADMIN_USERNAME", "admin")
TEST_ADMIN_PASSWORD = os.environ.get("TEST_ADMIN_PASSWORD", "")
TEST_USER_USERNAME = os.environ.get("TEST_USER_USERNAME", "user")
TEST_USER_PASSWORD = os.environ.get("TEST_USER_PASSWORD", "")

USERNAME_RE = re.compile(r"^[a-z0-9._-]{3,80}$")


def normalize_username(raw):
    return (raw or "").strip().lower()


def _safe_next(url):
    """Only follow same-site paths from ?next=; anything else is an open redirect."""
    if url and url.startswith("/") and not url.startswith("//") and "\\" not in url:
        return url
    return None


def _show_test_login():
    """Opt-in only. This panel prints working admin credentials onto the login
    page, so it must never appear because a variable was forgotten. It shows
    only when ENABLE_TEST_LOGIN is explicitly on AND the passwords are set.
    """
    env_value = os.environ.get("ENABLE_TEST_LOGIN", "").strip().lower()
    if env_value not in {"1", "true", "yes", "on"}:
        return False
    return bool(TEST_ADMIN_PASSWORD and TEST_USER_PASSWORD)


# Year groups a student can join at signup. Only these class names are offered,
# so other classes a teacher creates never appear on the public form.
SIGNUP_CLASSES = ("Class of 2027", "Class of 2028")


def _signup_page(**chosen):
    """Render the signup form with its fixed choices (classes, words, avatars)."""
    from avatars import AVATAR_CATALOG
    from models import Class
    from playful_names import ANIMALS, HAPPY_WORDS

    classes = (
        Class.query.filter(Class.name.in_(SIGNUP_CLASSES), Class.is_archived.is_(False))
        .order_by(Class.name).all()
    )
    taken = {row[0] for row in db.session.query(User.avatar).filter(User.avatar.isnot(None)).all()}
    return render_template(
        "signup.html", classes=classes, happy_words=HAPPY_WORDS, animals=ANIMALS,
        avatars=AVATAR_CATALOG, taken_avatars=taken, chosen=chosen,
    )


@auth_bp.route("/signup", methods=["GET", "POST"])
@limiter.limit("5 per hour", methods=["POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        from avatars import AVATAR_KEYS
        from models import Class, ClassEnrollment
        from playful_names import display_name, is_valid_pair, username_for
        from sqlalchemy.exc import IntegrityError

        form = request.form
        happy = form.get("happy_word", "")
        animal = form.get("animal", "")
        avatar = form.get("avatar", "")
        class_id = form.get("class_id", type=int)
        password = form.get("password", "")
        confirm = form.get("confirm_password", "")
        code = form.get("signup_code", "").strip()
        chosen = {"happy_word": happy, "animal": animal, "avatar": avatar, "class_id": class_id}

        chosen_class = None
        if class_id:
            chosen_class = Class.query.filter(
                Class.id == class_id, Class.name.in_(SIGNUP_CLASSES), Class.is_archived.is_(False)
            ).first()

        error = None
        if not SIGNUP_CODE:
            error = "Signup is currently closed."
        elif not hmac.compare_digest(code.encode(), SIGNUP_CODE.encode()):
            error = "Invalid signup code."
        elif not chosen_class:
            error = "Pick your class."
        elif not is_valid_pair(happy, animal):
            error = "Pick one happy word and one animal for your name."
        elif avatar not in AVATAR_KEYS:
            error = "Pick an icon."
        elif not password:
            error = "Choose a password."
        elif password != confirm:
            error = "Passwords do not match."
        elif len(password) < 8:
            error = "Password must be at least 8 characters."

        username = username_for(happy, animal) if is_valid_pair(happy, animal) else None
        if not error and User.query.filter_by(username=username).first():
            error = f"Someone is already {display_name(happy, animal)}. Pick a different word or animal."
        if not error and User.query.filter_by(avatar=avatar).first():
            error = "That icon was just taken. Pick another one."

        if error:
            flash(error, "error")
            return _signup_page(**chosen)

        # users.name is NOT NULL and shown throughout; the playful name stands in,
        # so no real name or email is ever collected.
        user = User(name=display_name(happy, animal), username=username, email=None,
                    role="student", avatar=avatar)
        user.set_password(password)
        try:
            db.session.add(user)
            db.session.flush()
            db.session.add(ClassEnrollment(class_id=chosen_class.id, student_id=user.id))
            db.session.commit()
        except IntegrityError:
            db.session.rollback()   # two students picked the same name at once
            flash(f"Someone is already {display_name(happy, animal)}. Pick a different word or animal.", "error")
            return _signup_page(**chosen)
        login_user(user)
        return redirect(url_for("dashboard"))

    return _signup_page()


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute; 100 per hour", methods=["POST"])
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
            next_url = _safe_next(request.args.get("next"))
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
