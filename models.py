from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=True, index=True)  # lowercase; primary login handle
    email = db.Column(db.String(255), unique=True, nullable=True, index=True)  # optional
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="student")  # "admin" | "student"
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active_flag = db.Column(db.Boolean, default=True, nullable=False)
    # References a key in avatars.AVATAR_CATALOG — a fixed, built-in set of
    # icons, never a free-text value or uploaded/external image. There is
    # deliberately no bio/photo/personal-info field alongside it.
    avatar = db.Column(db.String(40), nullable=True)

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    @staticmethod
    def find_by_login(identifier):
        """Look up a user by username or email (case-insensitive). Username wins."""
        ident = (identifier or "").strip().lower()
        if not ident:
            return None
        return (User.query.filter_by(username=ident).first()
                or User.query.filter_by(email=ident).first())

    def is_admin(self):
        return self.role == "admin"

    @property
    def is_active(self):
        return self.is_active_flag


class Class(db.Model):
    __tablename__ = "classes"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_archived = db.Column(db.Boolean, default=False, nullable=False)

    created_by = db.relationship("User", foreign_keys=[created_by_id])
    enrollments = db.relationship(
        "ClassEnrollment", backref="class_", cascade="all, delete-orphan"
    )
    assignments = db.relationship(
        "ReadingAssignment", backref="class_", cascade="all, delete-orphan"
    )


class ClassEnrollment(db.Model):
    __tablename__ = "class_enrollments"

    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow)
    level = db.Column(db.String(2), nullable=True)  # "HL" or "SL" for IB

    student = db.relationship("User")

    __table_args__ = (
        db.UniqueConstraint("class_id", "student_id", name="uq_class_student"),
    )


class ReadingAssignment(db.Model):
    __tablename__ = "reading_assignments"

    id = db.Column(db.Integer, primary_key=True)
    # Target: either a whole class (class_id set, student_id null) or a single
    # student (student_id set). At least one of the two is always populated.
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=True, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    resource_type = db.Column(db.String(20), nullable=False, default="book_page", server_default="book_page")
    # For resource_type == "book_page": book_folder + page_id identify data/<book_folder>/<page_id>/content.json
    # For resource_type == "exemplar": book_folder is unused, page_id holds the exemplar's PDF filename
    book_folder = db.Column(db.String(120), nullable=False)
    page_id = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(300))
    due_date = db.Column(db.DateTime, nullable=True)
    assigned_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    email_sent_at = db.Column(db.DateTime, nullable=True)

    assigned_by = db.relationship("User", foreign_keys=[assigned_by_id])
    student = db.relationship("User", foreign_keys=[student_id])

    def target_label(self):
        """Human-readable description of who this assignment is for."""
        if self.student_id and self.student:
            return self.student.name
        if self.class_ is not None:
            return self.class_.name
        return "Unknown"

    def resource_url(self, external=False):
        from flask import url_for
        if self.resource_type == "exemplar":
            return url_for("ee_exemplar_pdf", filename=self.page_id, _external=external)
        if self.resource_type == "exemplar_collection":
            return url_for("ee_exemplars", _external=external)
        if self.resource_type == "unit_plan_week":
            # book_folder doubles as the bucket key ("year1sem1", ... or "grade12"),
            # page_id as the week_number/topic_id — same addressing quiz linking uses.
            if self.book_folder == "grade12":
                return url_for("unit_plan.grade12_page", topic=self.page_id, _external=external)
            return url_for("unit_plan.semester_page", key=self.book_folder, week=self.page_id, _external=external)
        return url_for("book_page", book_folder=self.book_folder, page_id=self.page_id, _external=external)

    def resource_label(self):
        if self.resource_type == "exemplar_collection":
            return "EE / IA Collection"
        if self.resource_type == "exemplar":
            return "EE / IA Exemplar"
        if self.resource_type == "unit_plan_week":
            return "Unit Plan"
        return "Reading"


class ReadingActivity(db.Model):
    """One row per (student, book_folder, page_id) - cumulative tracking, not per-visit."""

    __tablename__ = "reading_activity"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    book_folder = db.Column(db.String(120), nullable=False)
    page_id = db.Column(db.String(50), nullable=False)
    first_opened_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_opened_at = db.Column(db.DateTime, default=datetime.utcnow)
    total_seconds = db.Column(db.Integer, default=0)
    completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime, nullable=True)

    student = db.relationship("User")

    __table_args__ = (
        db.UniqueConstraint(
            "student_id", "book_folder", "page_id", name="uq_student_page"
        ),
        db.Index("ix_activity_student_book", "student_id", "book_folder"),
    )


class ReadingDailyLog(db.Model):
    """Per-student per-day reading seconds, updated alongside ReadingActivity.

    ReadingActivity is cumulative per page, so it can't say *when* time was
    spent. This table gives charts an accurate day-by-day breakdown."""

    __tablename__ = "reading_daily_log"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False)
    seconds = db.Column(db.Integer, default=0, nullable=False)

    student = db.relationship("User")

    __table_args__ = (
        db.UniqueConstraint("student_id", "date", name="uq_daily_log_student_date"),
        db.Index("ix_daily_log_student_date", "student_id", "date"),
    )


class StudentConfidence(db.Model):
    """Student confidence ratings for pages (1-5 scale)."""

    __tablename__ = "student_confidence"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    book_folder = db.Column(db.String(120), nullable=False)
    page_id = db.Column(db.String(50), nullable=False)
    confidence_level = db.Column(db.Integer, nullable=False)  # 1-5 scale
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    student = db.relationship("User")

    __table_args__ = (
        db.UniqueConstraint(
            "student_id", "book_folder", "page_id", name="uq_student_confidence_page"
        ),
        db.Index("ix_confidence_student_book", "student_id", "book_folder"),
    )


class BookPageFolder(db.Model):
    """Folders for organizing pages within a book."""

    __tablename__ = "book_page_folders"

    id = db.Column(db.Integer, primary_key=True)
    book_folder = db.Column(db.String(120), nullable=False, index=True)  # book folder name
    name = db.Column(db.String(200), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey("book_page_folders.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    parent = db.relationship("BookPageFolder", remote_side=[id], backref="subfolders")
    pages = db.relationship("BookPageAssignment", backref="folder", cascade="all, delete-orphan")

    __table_args__ = (
        db.Index("ix_folder_book", "book_folder"),
    )


class BookPageAssignment(db.Model):
    """Assignment of book pages to folders within a book."""

    __tablename__ = "book_page_assignments"

    id = db.Column(db.Integer, primary_key=True)
    book_folder = db.Column(db.String(120), nullable=False, index=True)
    page_id = db.Column(db.String(50), nullable=False)
    folder_id = db.Column(db.Integer, db.ForeignKey("book_page_folders.id"), nullable=True)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("book_folder", "page_id", name="uq_book_page_assignment"),
        db.Index("ix_assignment_book_page", "book_folder", "page_id"),
    )


class QuizQuestion(db.Model):
    """Short-answer question attached to a book page (section quiz)."""

    __tablename__ = "quiz_questions"

    id = db.Column(db.Integer, primary_key=True)
    book_folder = db.Column(db.String(120), nullable=False)
    page_id = db.Column(db.String(50), nullable=False)
    position = db.Column(db.Integer, default=0, nullable=False)
    # "short_answer" (typed answer, AI/teacher marked) | "multiple_choice" (auto-marked)
    question_type = db.Column(db.String(20), nullable=False, default="short_answer", server_default="short_answer")
    text = db.Column(db.Text, nullable=False)
    markscheme = db.Column(db.Text, nullable=False)
    explanation = db.Column(db.Text, nullable=True)
    # Multiple-choice only. options: JSON list of option strings.
    # correct_options: JSON list of correct indices into options (len 1 = single, >1 = multi-select).
    options = db.Column(db.Text, nullable=True)
    correct_options = db.Column(db.Text, nullable=True)
    summary = db.Column(db.Text, nullable=True)  # Brief summary like "CPU Cache Levels"
    marks = db.Column(db.Integer, default=1, nullable=False)  # Total marks for this question
    difficulty = db.Column(db.String(20), nullable=True, default="medium")  # "easy", "medium", "hard"
    # JSON: list of keyword groups; an answer provisionally passes when every
    # group has at least one of its phrases present.
    # e.g. [["binary"], ["base 2", "two states", "0s and 1s"]]
    keywords = db.Column(db.Text, nullable=False, default="[]")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    answers = db.relationship("QuizAnswer", backref="question", cascade="all, delete-orphan")

    __table_args__ = (
        db.Index("ix_quiz_question_page", "book_folder", "page_id"),
    )

    def keyword_groups(self):
        import json
        try:
            groups = json.loads(self.keywords or "[]")
            return groups if isinstance(groups, list) else []
        except ValueError:
            return []

    def is_multiple_choice(self):
        return self.question_type == "multiple_choice"

    def options_list(self):
        import json
        try:
            opts = json.loads(self.options or "[]")
            return [str(o) for o in opts] if isinstance(opts, list) else []
        except ValueError:
            return []

    def correct_indices(self):
        import json
        try:
            idx = json.loads(self.correct_options or "[]")
            return [int(i) for i in idx] if isinstance(idx, list) else []
        except (ValueError, TypeError):
            return []

    def is_multi_select(self):
        return len(self.correct_indices()) > 1


class QuizAnswer(db.Model):
    """A student's answer to a quiz question, with provisional auto-mark. Supports retakes via attempt_number."""

    __tablename__ = "quiz_answers"

    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey("quiz_questions.id"), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    attempt_number = db.Column(db.Integer, nullable=False, default=1)  # 1 for first attempt, 2 for retake, etc.
    answer_text = db.Column(db.Text, nullable=False)
    auto_correct = db.Column(db.Boolean, nullable=True)  # provisional mark; None = could not auto-mark
    auto_method = db.Column(db.String(20), nullable=False, default="none")  # "keyword" | "gemini" | "none"
    auto_note = db.Column(db.Text, nullable=True)  # e.g. Gemini's one-line reasoning
    final_correct = db.Column(db.Boolean, nullable=True)  # set on teacher review
    marks_awarded = db.Column(db.Integer, nullable=True)  # e.g., 3 (out of question.marks total)
    feedback = db.Column(db.Text, nullable=True)  # teacher or AI feedback (may contain <b> tags)
    what_you_know = db.Column(db.Text, nullable=True)  # AI summary of what was correct in their answer
    improving_understanding = db.Column(db.Text, nullable=True)  # AI summary of what to add (only if needed for clarity)
    improvement_analysis = db.Column(db.Text, nullable=True)  # cached AI cross-attempt progress analysis (stored on latest attempt)
    status = db.Column(db.String(20), nullable=False, default="pending")  # "pending" | "reviewed"
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    student = db.relationship("User", foreign_keys=[student_id])
    reviewed_by = db.relationship("User", foreign_keys=[reviewed_by_id])
    insights = db.relationship("StudentFeedbackInsight", backref="answer", cascade="all, delete-orphan")

    __table_args__ = (
        db.UniqueConstraint("question_id", "student_id", "attempt_number", name="uq_quiz_answer_attempt"),
        db.Index("ix_quiz_answer_student_question", "student_id", "question_id"),
    )


class StudentFeedbackInsight(db.Model):
    """Extracted keywords from quiz answer feedback to build learner profiles."""

    __tablename__ = "student_feedback_insights"

    id = db.Column(db.Integer, primary_key=True)
    answer_id = db.Column(db.Integer, db.ForeignKey("quiz_answers.id"), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    question_id = db.Column(db.Integer, db.ForeignKey("quiz_questions.id"), nullable=False, index=True)
    feedback_text = db.Column(db.Text, nullable=False)  # Full feedback (may contain HTML)
    extracted_keywords = db.Column(db.Text, nullable=False, default="[]")  # JSON list of bold phrases
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    student = db.relationship("User", foreign_keys=[student_id])
    question = db.relationship("QuizQuestion", foreign_keys=[question_id])

    __table_args__ = (
        db.Index("ix_feedback_insight_student", "student_id"),
    )

    def keyword_list(self):
        import json
        try:
            return json.loads(self.extracted_keywords or "[]")
        except (ValueError, TypeError):
            return []


class PageSummary(db.Model):
    """Teacher-curated AI summary (30-50 words) of one book page, shown to
    students as an overview in quiz analytics."""

    __tablename__ = "page_summaries"

    id = db.Column(db.Integer, primary_key=True)
    book_folder = db.Column(db.String(120), nullable=False)
    page_id = db.Column(db.String(50), nullable=False)
    summary = db.Column(db.Text, nullable=False)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("book_folder", "page_id", name="uq_page_summary_page"),
    )


class FlashcardSet(db.Model):
    """A named deck of vocabulary flashcards built from one book's pages."""

    __tablename__ = "flashcard_sets"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    book_folder = db.Column(db.String(120), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    card_type = db.Column(db.String(20), nullable=False, default="flashcard")  # "flashcard" | "matching" | "learn"
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    created_by = db.relationship("User", foreign_keys=[created_by_id])
    cards = db.relationship(
        "Flashcard", backref="set", cascade="all, delete-orphan",
        order_by="Flashcard.position",
    )
    assignments = db.relationship(
        "FlashcardAssignment", backref="set", cascade="all, delete-orphan"
    )

    def page_ids(self):
        """Distinct source pages of this set's cards, in card order."""
        seen = []
        for c in self.cards:
            if c.page_id and c.page_id not in seen:
                seen.append(c.page_id)
        return seen


class Flashcard(db.Model):
    """One term/definition card in a flashcard set."""

    __tablename__ = "flashcards"

    id = db.Column(db.Integer, primary_key=True)
    set_id = db.Column(db.Integer, db.ForeignKey("flashcard_sets.id"), nullable=False, index=True)
    page_id = db.Column(db.String(50), nullable=True)  # source page the term came from
    term = db.Column(db.Text, nullable=False)
    definition = db.Column(db.Text, nullable=False)
    position = db.Column(db.Integer, default=0, nullable=False)

    progress = db.relationship("FlashcardProgress", backref="card", cascade="all, delete-orphan")


class FlashcardAssignment(db.Model):
    """A flashcard set assigned to a class (student_id null) or one student."""

    __tablename__ = "flashcard_assignments"

    id = db.Column(db.Integer, primary_key=True)
    set_id = db.Column(db.Integer, db.ForeignKey("flashcard_sets.id"), nullable=False, index=True)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=True, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    due_date = db.Column(db.DateTime, nullable=True)
    assigned_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    class_ = db.relationship("Class", foreign_keys=[class_id])
    student = db.relationship("User", foreign_keys=[student_id])
    assigned_by = db.relationship("User", foreign_keys=[assigned_by_id])

    def target_label(self):
        if self.student_id and self.student:
            return self.student.name
        if self.class_ is not None:
            return self.class_.name
        return "Unknown"


class FlashcardProgress(db.Model):
    """A student's cumulative self-assessment history for one card."""

    __tablename__ = "flashcard_progress"

    id = db.Column(db.Integer, primary_key=True)
    card_id = db.Column(db.Integer, db.ForeignKey("flashcards.id"), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    correct_count = db.Column(db.Integer, default=0, nullable=False)
    incorrect_count = db.Column(db.Integer, default=0, nullable=False)
    last_correct = db.Column(db.Boolean, nullable=True)  # result of the most recent review
    last_reviewed_at = db.Column(db.DateTime, nullable=True)
    total_dwell_seconds = db.Column(db.Float, default=0.0, nullable=False)  # cumulative time on this card
    correct_streak = db.Column(db.Integer, default=0, nullable=False)  # consecutive correct answers right now

    student = db.relationship("User")

    __table_args__ = (
        db.UniqueConstraint("card_id", "student_id", name="uq_flashcard_progress_student"),
    )

    @property
    def avg_dwell_seconds(self):
        """Average dwell time per review attempt."""
        total_attempts = self.correct_count + self.incorrect_count
        return round(self.total_dwell_seconds / total_attempts, 2) if total_attempts > 0 else 0

    @property
    def is_mastered(self):
        """A card counts as mastered when the student is getting it right *now*,
        regardless of old mistakes: either 3+ correct answers in a row, or their
        latest answer was correct with a quick average match (<10s dwell)."""
        if (self.correct_streak or 0) >= 3:
            return True
        return bool(self.last_correct) and (self.correct_count or 0) >= 2 \
            and 0 < self.avg_dwell_seconds < 10

    def record_result(self, correct):
        """Apply one attempt to the counters (caller commits)."""
        if correct:
            self.correct_count += 1
            self.correct_streak = (self.correct_streak or 0) + 1
        else:
            self.incorrect_count += 1
            self.correct_streak = 0
        self.last_correct = correct
        self.last_reviewed_at = datetime.now()


class FlashcardStudySession(db.Model):
    """One study attempt on a flashcard set: mode, time spent, and score.

    A row is created when a student finishes a round (completed=True) or
    leaves mid-round (completed=False, sent via beacon on page unload)."""

    __tablename__ = "flashcard_study_sessions"

    id = db.Column(db.Integer, primary_key=True)
    set_id = db.Column(db.Integer, db.ForeignKey("flashcard_sets.id"), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    mode = db.Column(db.String(20), nullable=False, default="flashcard")  # "flashcard" | "matching" | "learn"
    started_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    duration_seconds = db.Column(db.Float, nullable=False, default=0.0)
    completed = db.Column(db.Boolean, nullable=False, default=False)
    cards_total = db.Column(db.Integer, nullable=False, default=0)
    cards_correct = db.Column(db.Integer, nullable=False, default=0)
    cards_incorrect = db.Column(db.Integer, nullable=False, default=0)

    set = db.relationship("FlashcardSet", backref=db.backref("study_sessions", cascade="all, delete-orphan"))
    student = db.relationship("User")

    __table_args__ = (
        db.Index("ix_fss_set_student", "set_id", "student_id"),
    )

    @property
    def accuracy(self):
        answered = self.cards_correct + self.cards_incorrect
        return round(self.cards_correct * 100 / answered) if answered else None


class BookVocabulary(db.Model):
    """Editable vocabulary terms extracted from a book's pages."""

    __tablename__ = "book_vocabulary"

    id = db.Column(db.Integer, primary_key=True)
    book_folder = db.Column(db.String(120), nullable=False, index=True)
    page_id = db.Column(db.String(50), nullable=True)  # source page, nullable if term applies to whole book
    term = db.Column(db.Text, nullable=False)
    definition = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.Index("ix_vocab_book", "book_folder"),
        db.Index("ix_vocab_book_page", "book_folder", "page_id"),
    )


class HeadingStyles(db.Model):
    """User-defined heading styles for textbook editor."""

    __tablename__ = "heading_styles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    heading_level = db.Column(db.String(3), nullable=False)  # h1, h2, h3, h4, h5, h6
    font_size = db.Column(db.String(20), nullable=False)
    color = db.Column(db.String(7), nullable=False)  # hex color
    font_family = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship("User", backref="heading_styles")

    __table_args__ = (
        db.UniqueConstraint("user_id", "heading_level", name="uq_user_heading_level"),
        db.Index("ix_user_heading", "user_id", "heading_level"),
    )


class ConceptChain(db.Model):
    """A concept mapping exercise: students connect concepts with relationships."""

    __tablename__ = "concept_chains"

    id = db.Column(db.Integer, primary_key=True)
    chain_id = db.Column(db.String(100), nullable=False, unique=True, index=True)  # e.g., "oop_basics"
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    domain = db.Column(db.String(50), nullable=False)  # e.g., "OOP", "Data Structures", "Web Development"
    difficulty = db.Column(db.String(20), default="medium")  # "basic", "intermediate", "advanced"
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    nodes = db.relationship("ConceptNode", backref="chain", cascade="all, delete-orphan")
    correct_links = db.relationship("ConceptLink", backref="chain", cascade="all, delete-orphan")
    progress = db.relationship("ConceptChainProgress", backref="chain", cascade="all, delete-orphan")


class ConceptNode(db.Model):
    """A single concept in a concept chain."""

    __tablename__ = "concept_nodes"

    id = db.Column(db.Integer, primary_key=True)
    chain_id = db.Column(db.Integer, db.ForeignKey("concept_chains.id"), nullable=False, index=True)
    label = db.Column(db.String(100), nullable=False)
    order = db.Column(db.Integer, default=0)

    __table_args__ = (
        db.Index("ix_node_chain", "chain_id"),
    )


class ConceptLink(db.Model):
    """A correct relationship between two concepts."""

    __tablename__ = "concept_links"

    id = db.Column(db.Integer, primary_key=True)
    chain_id = db.Column(db.Integer, db.ForeignKey("concept_chains.id"), nullable=False, index=True)
    from_node_id = db.Column(db.Integer, db.ForeignKey("concept_nodes.id"), nullable=False)
    to_node_id = db.Column(db.Integer, db.ForeignKey("concept_nodes.id"), nullable=False)
    relationship_type = db.Column(db.String(50), nullable=False)  # e.g., "is-a", "uses", "enables"

    from_node = db.relationship("ConceptNode", foreign_keys=[from_node_id])
    to_node = db.relationship("ConceptNode", foreign_keys=[to_node_id])

    __table_args__ = (
        db.Index("ix_link_chain", "chain_id"),
        db.UniqueConstraint("chain_id", "from_node_id", "to_node_id", "relationship_type", name="uq_concept_link"),
    )


class ConceptChainProgress(db.Model):
    """Student's submission and score for a concept chain."""

    __tablename__ = "concept_chain_progress"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    chain_id = db.Column(db.Integer, db.ForeignKey("concept_chains.id"), nullable=False, index=True)
    submitted_links = db.Column(db.Text, nullable=False, default="[]")  # JSON: list of {from, to, type}
    correct_count = db.Column(db.Integer, default=0)
    total_possible = db.Column(db.Integer, default=0)
    score_percent = db.Column(db.Float, default=0.0)
    submitted_at = db.Column(db.DateTime, nullable=True)
    completed = db.Column(db.Boolean, default=False)

    student = db.relationship("User")

    __table_args__ = (
        db.UniqueConstraint("student_id", "chain_id", name="uq_student_chain_progress"),
        db.Index("ix_progress_student", "student_id"),
        db.Index("ix_progress_chain", "chain_id"),
    )


class UnitPlanSemester(db.Model):
    """One term of the DP Computer Science unit planner (e.g. Year 1 / Semester 1)."""

    __tablename__ = "unit_plan_semesters"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(30), unique=True, nullable=False)  # "year1sem1" | "year1sem2" | "year2sem1" | "year2sem2"
    title = db.Column(db.String(200), nullable=False)
    subtitle = db.Column(db.String(300), nullable=True)
    date_range = db.Column(db.String(120), nullable=True)
    position = db.Column(db.Integer, default=0, nullable=False)

    weeks = db.relationship(
        "UnitPlanWeek", backref="semester", cascade="all, delete-orphan",
        order_by="UnitPlanWeek.position"
    )


class UnitPlanWeek(db.Model):
    """A single week's plan within a semester. Free-form lesson-plan detail and attached
    resources are stored as JSON (see QuizQuestion.options for the same pattern in this codebase)
    since their shape is optional/evolving rather than fixed relational data."""

    __tablename__ = "unit_plan_weeks"

    id = db.Column(db.Integer, primary_key=True)
    semester_id = db.Column(db.Integer, db.ForeignKey("unit_plan_semesters.id"), nullable=False, index=True)
    week_number = db.Column(db.String(10), nullable=False)  # e.g. "1", "12" — unique within a semester
    position = db.Column(db.Integer, default=0, nullable=False)

    topic = db.Column(db.String(300), nullable=False, default="")
    content_focus = db.Column(db.String(400), nullable=True)
    big_idea = db.Column(db.Text, nullable=True)
    assessment = db.Column(db.Text, nullable=True)
    is_break = db.Column(db.Boolean, default=False, nullable=False)
    is_exam = db.Column(db.Boolean, default=False, nullable=False)
    taught = db.Column(db.Boolean, default=False, nullable=False)
    calendar_dates = db.Column(db.String(120), nullable=True)
    note = db.Column(db.Text, nullable=True)
    merged_note = db.Column(db.Text, nullable=True)
    hl = db.Column(db.String(300), nullable=True)
    sl = db.Column(db.String(300), nullable=True)
    syllabus = db.Column(db.String(120), nullable=True)

    objectives = db.Column(db.Text, nullable=False, default="[]")  # JSON list of strings
    detail = db.Column(db.Text, nullable=True)  # JSON object: full lesson-plan detail, or null
    materials = db.Column(db.Text, nullable=False, default="[]")  # JSON list of material dicts

    __table_args__ = (
        db.UniqueConstraint("semester_id", "week_number", name="uq_unit_plan_week"),
    )

    def to_dict(self):
        import json
        d = {
            "id": self.id,
            "week": self.week_number,
            "topic": self.topic,
            "isBreak": self.is_break,
        }
        if self.is_exam:
            d["isExam"] = True
        if self.taught:
            d["taught"] = True
        if self.content_focus:
            d["contentFocus"] = self.content_focus
        if self.big_idea:
            d["bigIdea"] = self.big_idea
        if self.assessment:
            d["assessment"] = self.assessment
        if self.calendar_dates:
            d["calendarDates"] = self.calendar_dates
        if self.note:
            d["note"] = self.note
        if self.merged_note:
            d["mergedNote"] = self.merged_note
        if self.hl is not None:
            d["hl"] = self.hl
        if self.sl is not None:
            d["sl"] = self.sl
        if self.syllabus:
            d["syllabus"] = self.syllabus
        try:
            objectives = json.loads(self.objectives or "[]")
        except ValueError:
            objectives = []
        if objectives:
            d["objectives"] = objectives
        if self.detail:
            try:
                d["detail"] = json.loads(self.detail)
            except ValueError:
                pass
        try:
            materials = json.loads(self.materials or "[]")
        except ValueError:
            materials = []
        if materials:
            d["materials"] = materials
        return d

    def update_from_dict(self, w):
        import json
        self.topic = w.get("topic", "") or ""
        self.is_break = bool(w.get("isBreak", False))
        self.is_exam = bool(w.get("isExam", False))
        self.taught = bool(w.get("taught", False))
        self.content_focus = w.get("contentFocus")
        self.big_idea = w.get("bigIdea")
        self.assessment = w.get("assessment")
        self.calendar_dates = w.get("calendarDates")
        self.note = w.get("note")
        self.merged_note = w.get("mergedNote")
        self.hl = w.get("hl")
        self.sl = w.get("sl")
        self.syllabus = w.get("syllabus")
        self.objectives = json.dumps(w.get("objectives") or [])
        self.detail = json.dumps(w["detail"]) if w.get("detail") else None
        if "materials" in w:
            self.materials = json.dumps(w.get("materials") or [])


class UnitPlanTopic(db.Model):
    """A single Grade 12 syllabus statement in the exam-prep tracker/board."""

    __tablename__ = "unit_plan_topics"

    id = db.Column(db.Integer, primary_key=True)
    topic_id = db.Column(db.String(60), unique=True, nullable=False)  # stable slug, e.g. "a1-1-1"
    code = db.Column(db.String(30), nullable=False)  # e.g. "A1.1.1"
    statement = db.Column(db.Text, nullable=False)
    part = db.Column(db.String(10), nullable=False)  # e.g. "A1"
    part_label = db.Column(db.String(120), nullable=True)
    hl_only = db.Column(db.Boolean, default=False, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="not-done")  # "done" | "not-done"
    plan_position = db.Column(db.Integer, nullable=True)  # null = not in the exam-prep plan
    materials = db.Column(db.Text, nullable=False, default="[]")  # JSON list of material dicts

    def to_dict(self):
        import json
        d = {
            "id": self.topic_id,
            "code": self.code,
            "statement": self.statement,
            "part": self.part,
            "partLabel": self.part_label,
            "status": self.status,
        }
        if self.hl_only:
            d["hlOnly"] = True
        try:
            materials = json.loads(self.materials or "[]")
        except ValueError:
            materials = []
        if materials:
            d["materials"] = materials
        return d


# ---------------------------------------------------------------------------
# Test Builder: timed, single-attempt exams assembled from the question bank.
# Deliberately parallel to QuizQuestion/QuizAnswer (mirrors their shape/
# conventions) rather than reusing those tables — see plan doc for rationale.
# ---------------------------------------------------------------------------

class ResourceFolder(db.Model):
    """A teacher-made folder inside a unit's resource library.

    `scope` is whatever rail item the folder lives under — a syllabus unit
    code ("A1"), one of the two assessment codes ("IA", "Case Study"), or
    "course-wide". Folders nest inside each other via parent_id, but always
    stay within the same scope; the syllabus subsections themselves aren't
    rows here, they're derived from UnitPlanTopic.code."""

    __tablename__ = "resource_folders"

    id = db.Column(db.Integer, primary_key=True)
    scope = db.Column(db.String(40), nullable=False, index=True)
    parent_id = db.Column(db.Integer, db.ForeignKey("resource_folders.id"), nullable=True, index=True)
    name = db.Column(db.String(200), nullable=False)
    position = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    children = db.relationship(
        "ResourceFolder", backref=db.backref("parent", remote_side=[id]), lazy="dynamic",
    )


class Resource(db.Model):
    """Something in the lesson library: a deck, video, PDF or worksheet,
    linked (not uploaded) from OneDrive/YouTube/wherever it already lives.

    `url` is the share link as pasted; `embed_url` is the same link rewritten
    to render inline (OneDrive's `action=embedview`, or a YouTube/Vimeo player
    URL) — stored rather than derived at render time so a link that needs a
    hand-built embed URL can be corrected without special-casing the template.

    A resource attaches to at most one of `topic_id` (a syllabus statement)
    or `folder_id` (a teacher-made folder); both NULL means it's course-wide
    (e.g. the syllabus overview) rather than belonging to one statement."""

    __tablename__ = "resources"

    id = db.Column(db.Integer, primary_key=True)
    kind = db.Column(db.String(20), nullable=False, default="deck")  # deck | video | pdf | worksheet
    topic_id = db.Column(db.String(60), nullable=True, index=True)  # UnitPlanTopic.topic_id
    folder_id = db.Column(db.Integer, db.ForeignKey("resource_folders.id"), nullable=True, index=True)
    title = db.Column(db.String(200), nullable=False)
    url = db.Column(db.Text, nullable=False)
    embed_url = db.Column(db.Text, nullable=True)
    position = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TopicGradeFocus(db.Model):
    """Whether a syllabus statement has been focused on, per year group.

    Per (topic, grade) rather than per topic: the same statement is taught to
    the Grade 11 and Grade 12 cohorts in different years, so one shared tick
    would make the two groups overwrite each other.

    Deliberately separate from UnitPlanTopic.status, which drives the Grade 12
    exam-prep board — ticking a deck as covered here should not silently mark it
    done there."""

    __tablename__ = "topic_grade_focus"

    id = db.Column(db.Integer, primary_key=True)
    topic_id = db.Column(db.String(60), nullable=False, index=True)
    grade = db.Column(db.Integer, nullable=False)  # 11 | 12
    focused = db.Column(db.Boolean, default=False, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("topic_id", "grade", name="uq_topic_grade_focus"),
    )


class StudentReportCache(db.Model):
    """The last AI-generated report card for a student.

    Exists because the report is generated by an Anthropic call that both the
    on-screen view and the PDF export used to make independently — two calls per
    student view, and (since generation is non-deterministic) a PDF whose prose
    did not match what the teacher had just read on screen.

    Keyed on a hash of the fully-built prompt rather than a list of stat fields:
    the prompt is the only thing that actually determines the output, so any
    change to the student's data *or* to the prompt template invalidates the
    entry automatically, with no field list to keep in sync.

    One row per student — a refresh overwrites in place rather than accumulating."""

    __tablename__ = "student_report_cache"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False, index=True)
    prompt_fingerprint = db.Column(db.String(64), nullable=False)  # sha256 hex of the built prompt
    report_json = db.Column(db.Text, nullable=False)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    student = db.relationship("User", foreign_keys=[student_id])


# Marks in the test builder are floats because MCQs are worth 0.5. Nobody wants to
# read "2.0 marks", so whole values render without a decimal point and halves keep
# theirs: 2 -> "2", 0.5 -> "0.5", 1.5 -> "1.5".
def format_marks(value):
    value = float(value or 0)
    return str(int(value)) if value == int(value) else f"{value:g}"


class SubtopicDescriptor(db.Model):
    """A one-line, student-friendly description of what a syllabus subtopic covers,
    imported from the "Subtopic Descriptors" sheet of questions.xlsx.

    Kept in its own table rather than denormalised onto TestQuestion: the
    descriptor belongs to the subtopic, not to any individual question, and
    there are ~112 of them against ~3,400 questions."""

    __tablename__ = "subtopic_descriptors"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)  # e.g. "A1.1.1"
    title = db.Column(db.Text, nullable=False)
    descriptor = db.Column(db.Text, nullable=True)
    question_count = db.Column(db.Integer, nullable=True)
    total_marks = db.Column(db.Integer, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TestQuestion(db.Model):
    """One question from the imported exam question bank (questions.xlsx)."""

    __tablename__ = "test_questions"

    id = db.Column(db.Integer, primary_key=True)
    # The label a teacher sees. It MOVES: deleting a question renumbers the rest of
    # its subtopic so the numbering has no gaps.
    qid = db.Column(db.String(40), unique=True, nullable=False)  # e.g. "A1.1.1-Q01"
    # The key this row came in on from questions.xlsx, which never moves — import
    # joins on this, so renumbering can't make a re-import overwrite the wrong row.
    source_qid = db.Column(db.String(40), nullable=True, index=True)
    subtopic_code = db.Column(db.String(20), nullable=False)  # e.g. "A1.1.1"
    unit_code = db.Column(db.String(10), nullable=False)  # e.g. "A1"
    theme = db.Column(db.String(1), nullable=False)  # "A" | "B"
    subtopic_title = db.Column(db.Text, nullable=False)
    is_hl_only = db.Column(db.Boolean, default=False, nullable=False)
    question_type = db.Column(db.String(20), nullable=False)  # "mcq" | "written"
    difficulty = db.Column(db.String(20), nullable=False)  # "easy" | "medium" | "hard"
    command_term = db.Column(db.String(60), nullable=True)
    text = db.Column(db.Text, nullable=False)
    options = db.Column(db.Text, nullable=True)  # JSON list, MCQ only
    correct_options = db.Column(db.Text, nullable=True)  # JSON list of indices, MCQ only
    # Float, not Integer: MCQs are deliberately worth 0.5 so a paper's score isn't
    # dominated by recall questions. Written questions stay whole marks.
    marks = db.Column(db.Float, default=1.0, nullable=False)
    marking_guidance = db.Column(db.Text, nullable=True)
    common_mistakes = db.Column(db.Text, nullable=True)
    ai_checklist = db.Column(db.Text, nullable=True)
    # Concise "Include: ... Avoid: ..." guidance for the AI marker to draw on when
    # explaining a wrong/partial/blank answer — separate from ai_checklist, which
    # is about *detecting* a correct answer rather than explaining a wrong one.
    if_wrong_explainer = db.Column(db.Text, nullable=True)
    # A suggested illustrative icon (from an external icon library, e.g. Bootstrap
    # Icons) — icon_source_url points at the library's own page for that icon, not
    # a raw asset, so it's rendered as a link rather than an embedded image.
    icon_library = db.Column(db.String(60), nullable=True)
    icon_name = db.Column(db.String(60), nullable=True)
    icon_source_url = db.Column(db.String(300), nullable=True)
    visual_search_terms = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.Index("ix_test_question_subtopic", "subtopic_code"),
        db.Index("ix_test_question_unit", "unit_code"),
    )

    def is_mcq(self):
        return self.question_type == "mcq"

    def options_list(self):
        import json
        try:
            opts = json.loads(self.options or "[]")
            return [str(o) for o in opts] if isinstance(opts, list) else []
        except ValueError:
            return []

    def correct_indices(self):
        import json
        try:
            idx = json.loads(self.correct_options or "[]")
            return [int(i) for i in idx] if isinstance(idx, list) else []
        except (ValueError, TypeError):
            return []


class TestPaper(db.Model):
    """A teacher-assembled exam: a fixed, ordered set of TestQuestion rows."""

    __tablename__ = "test_papers"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="draft")  # draft|published|unpublished
    time_limit_minutes = db.Column(db.Integer, nullable=False, default=60)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = db.relationship("User", foreign_keys=[owner_id])
    paper_questions = db.relationship(
        "TestPaperQuestion", backref="paper", cascade="all, delete-orphan",
        order_by="TestPaperQuestion.position",
    )
    assignments = db.relationship("TestAssignment", backref="paper", cascade="all, delete-orphan")
    submissions = db.relationship("TestSubmission", backref="paper", cascade="all, delete-orphan")

    @property
    def questions(self):
        return [pq.question for pq in self.paper_questions]

    @property
    def total_marks(self):
        return sum((pq.question.marks or 0) for pq in self.paper_questions)

    @property
    def has_hl_only_questions(self):
        return any(pq.question.is_hl_only for pq in self.paper_questions)


class TestPaperQuestion(db.Model):
    """Ordered membership of one TestQuestion in one TestPaper."""

    __tablename__ = "test_paper_questions"

    id = db.Column(db.Integer, primary_key=True)
    test_paper_id = db.Column(db.Integer, db.ForeignKey("test_papers.id"), nullable=False, index=True)
    question_id = db.Column(db.Integer, db.ForeignKey("test_questions.id"), nullable=False, index=True)
    position = db.Column(db.Integer, default=0, nullable=False)

    question = db.relationship("TestQuestion")

    __table_args__ = (
        db.UniqueConstraint("test_paper_id", "question_id", name="uq_test_paper_question"),
    )


class TestAssignment(db.Model):
    """A TestPaper assigned to a class (student_id null) or one student, taken in
    class in one sitting — no open/due window, just a time limit counted from the
    moment each student enters the access code."""

    __tablename__ = "test_assignments"

    id = db.Column(db.Integer, primary_key=True)
    test_paper_id = db.Column(db.Integer, db.ForeignKey("test_papers.id"), nullable=False, index=True)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=True, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    assigned_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    # Only meaningful for a class target: "HL"/"SL" narrows the assignment to just
    # that half of the class (matching ClassEnrollment.level); None means both.
    level_filter = db.Column(db.String(2), nullable=True)
    time_limit_minutes = db.Column(db.Integer, nullable=False)  # snapshot/override of paper default
    # Short join code students type in (like a game pin) — the primary way they reach the
    # test, rather than browsing an assignments list. Regenerable if it leaks. Cleared to
    # None once every targeted student has submitted — the assignment and its results stay
    # around for review, but the code itself retires so it can't be reused.
    access_code = db.Column(db.String(8), unique=True, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    class_ = db.relationship("Class", foreign_keys=[class_id])
    student = db.relationship("User", foreign_keys=[student_id])
    assigned_by = db.relationship("User", foreign_keys=[assigned_by_id])
    submissions = db.relationship("TestSubmission", backref="assignment")

    def target_label(self):
        if self.student_id and self.student:
            return self.student.name
        if self.class_ is not None:
            suffix = f" ({self.level_filter} only)" if self.level_filter else ""
            return f"{self.class_.name}{suffix}"
        return "Unknown"


class TestSubmission(db.Model):
    """A single student's one-and-only sitting of a TestPaper. The unique
    constraint on (test_paper_id, student_id) is what actually enforces
    single-attempt — not application logic."""

    __tablename__ = "test_submissions"

    id = db.Column(db.Integer, primary_key=True)
    test_paper_id = db.Column(db.Integer, db.ForeignKey("test_papers.id"), nullable=False, index=True)
    test_assignment_id = db.Column(db.Integer, db.ForeignKey("test_assignments.id"), nullable=True, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    started_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    submitted_at = db.Column(db.DateTime, nullable=True)
    # Recorded once, at submit, rather than recomputed from the timestamps on every
    # read: seconds (not minutes) so a 3m20s attempt doesn't report as "3 minutes",
    # and a stable record even if started_at is ever corrected. Null on rows that
    # pre-date this column — see time_taken_seconds_effective.
    time_taken_seconds = db.Column(db.Integer, nullable=True)
    time_limit_minutes = db.Column(db.Integer, nullable=False)  # snapshot at start time
    status = db.Column(db.String(20), nullable=False, default="in_progress")
    # in_progress | submitted | marked | reviewed
    total_marks_awarded = db.Column(db.Float, nullable=True)
    total_marks_possible = db.Column(db.Float, nullable=True)
    # Marks rows created by the admin "simulate students starting" dev tool —
    # never written by real student activity — so they can always be told
    # apart from a genuine attempt and cleared without touching real data.
    is_simulated = db.Column(db.Boolean, nullable=False, default=False)
    # The AI-written encouragement/revision prose on the report, cached as JSON so
    # opening the report twice (or exporting the PDF) doesn't pay for a second
    # model call. report_narrative_key fingerprints the marks it was written from,
    # so a teacher re-marking an answer invalidates it automatically.
    report_narrative = db.Column(db.Text, nullable=True)
    report_narrative_key = db.Column(db.String(64), nullable=True)

    student = db.relationship("User", foreign_keys=[student_id])
    answers = db.relationship("TestAnswer", backref="submission", cascade="all, delete-orphan")

    __table_args__ = (
        db.UniqueConstraint("test_paper_id", "student_id", name="uq_test_submission_single_attempt"),
    )

    @property
    def deadline(self):
        from datetime import timedelta
        return self.started_at + timedelta(minutes=self.time_limit_minutes)

    @property
    def time_taken_seconds_effective(self):
        """Stored duration, falling back to the timestamp difference for rows
        written before time_taken_seconds existed. None while in progress."""
        if self.time_taken_seconds is not None:
            return self.time_taken_seconds
        if self.submitted_at:
            return max(0, int((self.submitted_at - self.started_at).total_seconds()))
        return None

    @property
    def is_overdue(self):
        return self.submitted_at is None and datetime.utcnow() > self.deadline


class TestAnswer(db.Model):
    """A student's answer to one TestQuestion within a TestSubmission."""

    __tablename__ = "test_answers"

    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey("test_submissions.id"), nullable=False, index=True)
    question_id = db.Column(db.Integer, db.ForeignKey("test_questions.id"), nullable=False, index=True)
    response_text = db.Column(db.Text, nullable=True)
    selected_options = db.Column(db.Text, nullable=True)  # JSON list of indices, MCQ only
    auto_correct = db.Column(db.Boolean, nullable=True)
    marks_awarded = db.Column(db.Float, nullable=True)  # halves possible (MCQs are 0.5)
    ai_feedback = db.Column(db.Text, nullable=True)
    confidence = db.Column(db.Float, nullable=True)  # 0-1, AI written-marking self-report
    status = db.Column(db.String(20), nullable=False, default="pending")  # pending | reviewed
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

    question = db.relationship("TestQuestion")
    reviewed_by = db.relationship("User", foreign_keys=[reviewed_by_id])

    __table_args__ = (
        db.UniqueConstraint("submission_id", "question_id", name="uq_test_answer_question"),
    )

    def selected_indices(self):
        import json
        try:
            idx = json.loads(self.selected_options or "[]")
            return [int(i) for i in idx] if isinstance(idx, list) else []
        except (ValueError, TypeError):
            return []


# ============================================================
# Class Games — teacher-run, on-the-board games
# ============================================================

class GameSession(db.Model):
    """One run of a class game (Concept Ladder, Bug Hunt Auction, ...).

    Deliberately generic: game_type names the game, config holds the setup
    the teacher chose (frozen at creation), state holds the live game state
    the board mutates as it runs. New games add a registry entry and their
    own config/state shapes — no new tables unless they need per-student
    answers (GameRoundAnswer) beyond what's here.
    """

    __tablename__ = "game_sessions"

    id = db.Column(db.Integer, primary_key=True)
    game_type = db.Column(db.String(30), nullable=False)  # "concept_ladder" | "think_of_word" | "connections"
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=True, index=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    # Short join code students type in — same convention as TestAssignment.access_code.
    # Null for board-only games (Bug Hunt) where students don't need devices.
    join_code = db.Column(db.String(8), unique=True, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="lobby")  # lobby | active | finished
    config = db.Column(db.Text, nullable=False, default="{}")  # JSON, frozen at creation
    state = db.Column(db.Text, nullable=False, default="{}")  # JSON, mutated by board actions
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    finished_at = db.Column(db.DateTime, nullable=True)

    class_ = db.relationship("Class", foreign_keys=[class_id])
    created_by = db.relationship("User", foreign_keys=[created_by_id])
    participants = db.relationship("GameParticipant", backref="session", cascade="all, delete-orphan")

    def config_dict(self):
        import json
        try:
            d = json.loads(self.config or "{}")
            return d if isinstance(d, dict) else {}
        except ValueError:
            return {}

    def state_dict(self):
        import json
        try:
            d = json.loads(self.state or "{}")
            return d if isinstance(d, dict) else {}
        except ValueError:
            return {}


class GameParticipant(db.Model):
    """A student who joined a device-based game session."""

    __tablename__ = "game_participants"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("game_sessions.id"), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    # Snapshot of ClassEnrollment.level at join time ("HL"/"SL"); students with
    # no level recorded are treated as SL so they can never be served HL-only
    # content by accident.
    level = db.Column(db.String(2), nullable=False, default="SL")
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    student = db.relationship("User")

    __table_args__ = (
        db.UniqueConstraint("session_id", "student_id", name="uq_game_participant"),
    )


class GameRoundAnswer(db.Model):
    """One student's answer to one round/rung of a game session.

    question_id points at the bank question actually served to *that student*
    (HL and SL students on the same rung may hold different questions), so
    per-student analytics stay truthful.
    """

    __tablename__ = "game_round_answers"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("game_sessions.id"), nullable=False, index=True)
    participant_id = db.Column(db.Integer, db.ForeignKey("game_participants.id"), nullable=False, index=True)
    round_index = db.Column(db.Integer, nullable=False)
    attempt = db.Column(db.Integer, nullable=False, default=1)  # 1 = first try, 2 = post-discussion retry
    question_id = db.Column(db.Integer, db.ForeignKey("test_questions.id"), nullable=True, index=True)
    answer_index = db.Column(db.Integer, nullable=True)  # chosen MCQ option
    is_correct = db.Column(db.Boolean, nullable=False, default=False)
    answered_at = db.Column(db.DateTime, default=datetime.utcnow)

    participant = db.relationship("GameParticipant")
    question = db.relationship("TestQuestion")

    __table_args__ = (
        db.UniqueConstraint("session_id", "participant_id", "round_index", "attempt",
                            name="uq_game_round_answer"),
    )


class BugHuntSnippet(db.Model):
    """A teacher-authored code snippet with planted bugs for Bug Hunt Auction.

    Content follows the product's ground-truth rule: authored by the teacher
    (or imported), never generated at play time. Sample snippets shipped with
    the feature are labelled is_sample and can be archived.
    """

    __tablename__ = "bug_hunt_snippets"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    language = db.Column(db.String(20), nullable=False, default="pseudocode")  # pseudocode | python
    code = db.Column(db.Text, nullable=False)
    # JSON list of {"line": int (1-based), "description": str}
    bugs = db.Column(db.Text, nullable=False, default="[]")
    difficulty = db.Column(db.String(20), nullable=False, default="medium")  # easy | medium | hard
    description = db.Column(db.Text, nullable=True)  # What this code does, shown to students
    topic_label = db.Column(db.String(120), nullable=True)  # free label, e.g. "Iteration"
    is_sample = db.Column(db.Boolean, default=False, nullable=False)
    is_archived = db.Column(db.Boolean, default=False, nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    created_by = db.relationship("User", foreign_keys=[created_by_id])

    def bugs_list(self):
        import json
        try:
            b = json.loads(self.bugs or "[]")
            return b if isinstance(b, list) else []
        except ValueError:
            return []

    def line_count(self):
        return len((self.code or "").splitlines())


# ---------------------------------------------------------------------------
# Exit tickets: short web quizzes, one per syllabus subtopic, assigned to classes
# ---------------------------------------------------------------------------

class ExitTicket(db.Model):
    """A short end-of-lesson quiz for one syllabus subtopic (e.g. A1.1.1 The CPU).

    Questions live in ExitTicketQuestion; the teacher edits them in the browser.
    """

    __tablename__ = "exit_tickets"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(30), nullable=True, index=True)        # "A1.1.1"
    topic_id = db.Column(db.String(60), nullable=True, index=True)    # slug in unit_plan_topics, e.g. "a1-1-1"
    title = db.Column(db.String(200), nullable=False)                 # "The CPU"
    objective = db.Column(db.Text, nullable=True)                     # the syllabus statement
    status = db.Column(db.String(20), nullable=False, default="draft")  # draft | published
    allow_retries = db.Column(db.Boolean, nullable=False, default=True)
    show_answers = db.Column(db.String(10), nullable=False, default="after")  # after | never
    # Bumped whenever a save actually changes the questions. Each attempt records the version it was taken on.
    version = db.Column(db.Integer, nullable=False, default=1, server_default="1")
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    created_by = db.relationship("User", foreign_keys=[created_by_id])
    # Every question row ever saved, including ones the teacher has since removed (kept for history).
    all_questions = db.relationship(
        "ExitTicketQuestion", backref="ticket", cascade="all, delete-orphan",
        order_by="ExitTicketQuestion.position",
    )
    assignments = db.relationship("ExitTicketAssignment", backref="ticket", cascade="all, delete-orphan")

    @property
    def questions(self):
        """The questions students get now (removed ones are hidden, not deleted)."""
        return [q for q in self.all_questions if q.active]

    @property
    def total_marks(self):
        return sum((q.marks or 0) for q in self.questions)


class ExitTicketQuestion(db.Model):
    """One question. `qtype` decides the shape of `data` (JSON):

    mcq        {"options": [str, ...], "correct": int}
    truefalse  {"statements": [{"text": str, "answer": bool}, ...]}
    fill       {"sentences": [{"text": "The ____ does X.", "blanks": [[accepted, ...], ...]}, ...]}
    match      {"pairs": [{"left": str, "right": str}, ...], "distractors": [str, ...]}
    order      {"items": [str, ...]}                       # stored in the CORRECT order
    short      {"model_answer": str, "marking_points": [str, ...]}
    explain    {"model_answer": str, "marking_points": [str, ...]}
    """

    __tablename__ = "exit_ticket_questions"

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("exit_tickets.id"), nullable=False, index=True)
    position = db.Column(db.Integer, nullable=False, default=0)
    qtype = db.Column(db.String(20), nullable=False)
    prompt = db.Column(db.Text, nullable=False, default="")
    marks = db.Column(db.Float, nullable=False, default=1.0)
    data = db.Column(db.Text, nullable=False, default="{}")
    # False = the teacher removed it. The row stays so attempts that included it keep their history.
    active = db.Column(db.Boolean, nullable=False, default=True, server_default="1")

    def data_dict(self):
        import json
        try:
            d = json.loads(self.data or "{}")
            return d if isinstance(d, dict) else {}
        except ValueError:
            return {}


class ExitTicketAssignment(db.Model):
    """A ticket assigned to a whole class (student_id null) or to one student."""

    __tablename__ = "exit_ticket_assignments"

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("exit_tickets.id"), nullable=False, index=True)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=True, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    assigned_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    due_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    class_ = db.relationship("Class", foreign_keys=[class_id])
    student = db.relationship("User", foreign_keys=[student_id])
    assigned_by = db.relationship("User", foreign_keys=[assigned_by_id])


class ExitTicketSubmission(db.Model):
    """One attempt at a ticket by one student. Retries create new rows (attempt_number)."""

    __tablename__ = "exit_ticket_submissions"

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("exit_tickets.id"), nullable=False, index=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey("exit_ticket_assignments.id"), nullable=True, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    attempt_number = db.Column(db.Integer, nullable=False, default=1)
    started_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    submitted_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="in_progress")  # in_progress | submitted
    total_awarded = db.Column(db.Float, nullable=True)
    total_possible = db.Column(db.Float, nullable=True)
    confidence = db.Column(db.Integer, nullable=True)         # the Reflection box: 1-5
    reflection_note = db.Column(db.Text, nullable=True)       # "One thing I still want to check"
    # The ticket's questions (with answers) exactly as they were when this attempt started. Marking, the
    # review screen and the teacher's view all use THIS, so later edits to the ticket never change it.
    snapshot = db.Column(db.Text, nullable=True)
    ticket_version = db.Column(db.Integer, nullable=True)
    # Per-attempt shuffles for match/order questions, with opaque tokens, so the browser
    # never receives the correct pairing or order: {"<question id>": {...}}
    layout = db.Column(db.Text, nullable=False, default="{}")

    ticket = db.relationship("ExitTicket", foreign_keys=[ticket_id])
    student = db.relationship("User", foreign_keys=[student_id])
    answers = db.relationship("ExitTicketAnswer", backref="submission", cascade="all, delete-orphan")

    __table_args__ = (
        db.UniqueConstraint("ticket_id", "student_id", "attempt_number", name="uq_exit_ticket_attempt"),
    )

    def layout_dict(self):
        import json
        try:
            d = json.loads(self.layout or "{}")
            return d if isinstance(d, dict) else {}
        except ValueError:
            return {}


class ExitTicketAnswer(db.Model):
    """A student's answer to one question, with how it was marked."""

    __tablename__ = "exit_ticket_answers"

    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey("exit_ticket_submissions.id"), nullable=False, index=True)
    question_id = db.Column(db.Integer, db.ForeignKey("exit_ticket_questions.id"), nullable=False, index=True)
    response = db.Column(db.Text, nullable=True)              # JSON of what the student answered
    marks_awarded = db.Column(db.Float, nullable=True)
    marks_possible = db.Column(db.Float, nullable=False, default=1.0)
    feedback = db.Column(db.Text, nullable=True)
    detail = db.Column(db.Text, nullable=True)                # JSON: per-item right/wrong for objective types
    status = db.Column(db.String(20), nullable=False, default="pending")  # marked | pending | needs_review
    marked_by = db.Column(db.String(10), nullable=True)       # auto | ai | teacher
    confidence = db.Column(db.Float, nullable=True)           # AI's own confidence, 0-1
    ai_tries = db.Column(db.Integer, nullable=False, default=0)

    question = db.relationship("ExitTicketQuestion", foreign_keys=[question_id])

    __table_args__ = (
        db.UniqueConstraint("submission_id", "question_id", name="uq_exit_ticket_answer_question"),
    )
