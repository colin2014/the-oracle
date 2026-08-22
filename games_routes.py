"""Class Games — teacher-run games played on the board.

Three games available:

- Concept Ladder ("concept_ladder"): co-op climb. The teacher picks topics
  from the question bank; the class answers each rung on their own devices;
  the board shows the ladder, the live answer count, and the anonymous
  answer distribution. HL-only questions are only ever served to HL
  students.

- Think of a Word ("think_of_word"): The teacher thinks of a word silently;
  students ask yes/no questions to figure it out. First person to guess wins.

- Connections ("connections"): A 4×4 grid of 16 words grouped into 4 hidden
  categories. Students work together to find all four groups before running
  out of mistakes.

Adding a game: add a GAME_REGISTRY entry, a setup route, a board template,
and (if students answer on devices) reuse GameParticipant/GameRoundAnswer.
"""

import json
import random
import secrets
from datetime import datetime

from flask import (Blueprint, abort, flash, jsonify, redirect, render_template,
                   request, url_for)
from flask_login import current_user, login_required

from extensions import db
from models import (Class, ClassEnrollment, GameParticipant,
                    GameRoundAnswer, GameSession, TestQuestion)

games_bp = Blueprint("games", __name__, url_prefix="/class-games")

_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # no 0/O/1/I/L lookalikes


# Everything the hub needs to render a game card. Board-only games set
# needs_devices=False and skip the join-code flow entirely.
GAME_REGISTRY = [
    {
        "type": "concept_ladder",
        "name": "Concept Ladder",
        "tagline": "The class climbs together",
        "description": ("A ladder of bank questions, easy to hard, from topics you pick. "
                        "Everyone answers on their own device; the class advances only when "
                        "enough of the room gets the rung right."),
        "mode": "Co-op · devices + board",
        "setup_endpoint": "games.ladder_setup",
        "needs_devices": True,
    },
    {
        "type": "think_of_word",
        "name": "Think of a Word",
        "tagline": "Guess what the teacher is thinking",
        "description": ("The teacher thinks of a word silently. Students ask yes/no questions "
                        "to narrow it down. First to guess the word wins the round."),
        "mode": "Co-op · devices + board",
        "setup_endpoint": "games.word_setup",
        "needs_devices": True,
    },
    {
        "type": "connections",
        "name": "Connections",
        "tagline": "Find the four groups",
        "description": ("A 4×4 grid of 16 words. Each has a hidden group of 4 with a shared "
                        "connection. Find all four groups before running out of mistakes."),
        "mode": "Co-op · devices + board",
        "setup_endpoint": "games.connections_setup",
        "needs_devices": True,
    },
]


def _require_admin():
    if not current_user.is_admin():
        abort(403)


def _generate_join_code(length=6):
    while True:
        code = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(length))
        if not GameSession.query.filter_by(join_code=code).first():
            return code


def _save_state(session_obj, state):
    session_obj.state = json.dumps(state)
    db.session.commit()


# ============================================================
# Hub
# ============================================================

@games_bp.route("/")
@login_required
def hub():
    _require_admin()
    recent = (GameSession.query.order_by(GameSession.created_at.desc()).limit(12).all())
    return render_template("games_admin_hub.html", games=GAME_REGISTRY, recent=recent)


# ============================================================
# Concept Ladder — setup
# ============================================================

# Difficulty ramp for a ladder of n rungs: first ~40% easy, middle ~35%
# medium, top ~25% hard.
def _ladder_difficulties(n):
    easy = max(1, round(n * 0.4))
    hard = max(1, round(n * 0.25))
    medium = max(0, n - easy - hard)
    return ["easy"] * easy + ["medium"] * medium + ["hard"] * hard


def _mcq_pool(subtopic_codes):
    return (TestQuestion.query
            .filter(TestQuestion.subtopic_code.in_(subtopic_codes),
                    TestQuestion.question_type == "mcq")
            .all())


def _pick(pool, topic_rotation, difficulty, used_ids):
    """Pick an unused question at the given difficulty, preferring the next
    topic in rotation, then any topic, then relaxing difficulty."""
    def candidates(topic, diff):
        return [q for q in pool
                if q.id not in used_ids
                and (topic is None or q.subtopic_code == topic)
                and (diff is None or q.difficulty == diff)]

    for topic in topic_rotation + [None]:
        got = candidates(topic, difficulty)
        if got:
            return random.choice(got)
    # No question at this difficulty anywhere: relax difficulty entirely.
    got = candidates(None, None)
    return random.choice(got) if got else None


def _build_ladder(subtopic_codes, rung_count):
    """Build rungs as [{difficulty, sl_qid, hl_qid}]. sl_qid is always from a
    non-HL question; hl_qid (may be None) is the HL variant for HL students.
    Returns (rungs, error)."""
    pool = _mcq_pool(subtopic_codes)
    sl_pool = [q for q in pool if not q.is_hl_only]
    hl_pool = [q for q in pool if q.is_hl_only]

    if not sl_pool and not hl_pool:
        return None, "No multiple-choice questions found in the chosen topics."

    hl_only_session = not sl_pool  # every chosen topic is HL-only

    rungs = []
    used = set()
    sl_topics = sorted({q.subtopic_code for q in sl_pool})
    hl_topics = sorted({q.subtopic_code for q in hl_pool})

    for i, difficulty in enumerate(_ladder_difficulties(rung_count)):
        rung = {"difficulty": difficulty, "sl_qid": None, "hl_qid": None}

        if sl_pool:
            rotation = sl_topics[i % len(sl_topics):] + sl_topics[:i % len(sl_topics)]
            q = _pick(sl_pool, rotation, difficulty, used)
            if q is None:
                return None, ("Not enough distinct multiple-choice questions in the chosen "
                              "topics for a %d-rung ladder." % rung_count)
            used.add(q.id)
            rung["sl_qid"] = q.id

        if hl_pool:
            rotation = hl_topics[i % len(hl_topics):] + hl_topics[:i % len(hl_topics)]
            q = _pick(hl_pool, rotation, difficulty, used)
            if q is not None:
                used.add(q.id)
                rung["hl_qid"] = q.id
            elif hl_only_session:
                return None, ("Not enough distinct HL multiple-choice questions for a "
                              "%d-rung ladder." % rung_count)

        rungs.append(rung)

    return {"rungs": rungs, "hl_only": hl_only_session}, None


def _subtopic_catalog():
    """Subtopics with MCQ counts, for the setup picker."""
    rows = (db.session.query(
                TestQuestion.subtopic_code,
                TestQuestion.subtopic_title,
                TestQuestion.unit_code,
                TestQuestion.theme,
                db.func.sum(db.case((TestQuestion.question_type == "mcq", 1), else_=0)),
                db.func.max(db.case((TestQuestion.is_hl_only, 1), else_=0)))
            .group_by(TestQuestion.subtopic_code, TestQuestion.subtopic_title,
                      TestQuestion.unit_code, TestQuestion.theme)
            .order_by(TestQuestion.subtopic_code)
            .all())
    return [{"code": r[0], "title": r[1], "unit": r[2], "theme": r[3],
             "mcq_count": int(r[4] or 0), "hl_only": bool(r[5])} for r in rows]


@games_bp.route("/ladder/new", methods=["GET", "POST"])
@login_required
def ladder_setup():
    _require_admin()
    classes = (Class.query.filter_by(is_archived=False).order_by(Class.name).all())

    if request.method == "POST":
        class_id = request.form.get("class_id", type=int)
        topics = request.form.getlist("topics")
        rung_count = min(12, max(4, request.form.get("rung_count", 8, type=int)))
        threshold = min(100, max(30, request.form.get("threshold", 70, type=int)))
        seconds_per_rung = min(300, max(15, request.form.get("seconds_per_rung", 60, type=int)))

        cls = Class.query.get(class_id) if class_id else None
        if cls is None:
            flash("Pick a class.", "error")
        elif not topics:
            flash("Pick at least one topic.", "error")
        else:
            ladder, err = _build_ladder(topics, rung_count)
            if err:
                flash(err, "error")
            else:
                session_obj = GameSession(
                    game_type="concept_ladder",
                    class_id=cls.id,
                    created_by_id=current_user.id,
                    join_code=_generate_join_code(),
                    status="lobby",
                    config=json.dumps({
                        "topics": topics,
                        "rung_count": rung_count,
                        "threshold": threshold,
                        "seconds_per_rung": seconds_per_rung,
                        "hl_only": ladder["hl_only"],
                    }),
                    state=json.dumps({
                        "rungs": ladder["rungs"],
                        "phase": "lobby",          # lobby | rung_open | rung_reveal | finished
                        "rung_index": 0,
                        "attempt": 1,
                        "rung_results": [],        # per rung: {passed, attempts: [{correct, total}]}
                        "opened_at": None,
                    }),
                )
                db.session.add(session_obj)
                db.session.commit()
                return redirect(url_for("games.board", session_id=session_obj.id))

    return render_template("game_ladder_setup.html",
                           classes=classes, subtopics=_subtopic_catalog())


# ============================================================
# Boards (shared entry, per-game template)
# ============================================================

@games_bp.route("/session/<int:session_id>/board")
@login_required
def board(session_id):
    _require_admin()
    s = GameSession.query.get_or_404(session_id)
    if s.game_type == "concept_ladder":
        return render_template("game_board_ladder.html", session_obj=s,
                               config=s.config_dict(), state=s.state_dict())
    if s.game_type == "think_of_word":
        return render_template("game_board_word.html", session_obj=s,
                               config=s.config_dict(), state=s.state_dict())
    if s.game_type == "connections":
        return render_template("game_board_connections.html", session_obj=s,
                               config=s.config_dict(), state=s.state_dict())
    abort(404)


# ============================================================
# Concept Ladder — board state + actions
# ============================================================

def _rung_distribution(s, rung_index, attempt):
    """Anonymous option distribution + correct count for a rung attempt.
    Distributions are keyed per-question so HL and SL variants stay separate."""
    answers = GameRoundAnswer.query.filter_by(
        session_id=s.id, round_index=rung_index, attempt=attempt).all()
    by_question = {}
    correct = 0
    for a in answers:
        if a.is_correct:
            correct += 1
        if a.question_id is not None and a.answer_index is not None:
            by_question.setdefault(a.question_id, {}).setdefault(a.answer_index, 0)
            by_question[a.question_id][a.answer_index] += 1
    return answers, correct, by_question


def _ladder_board_state(s):
    state = s.state_dict()
    config = s.config_dict()
    participants = GameParticipant.query.filter_by(session_id=s.id).all()
    rung_index = state.get("rung_index", 0)
    attempt = state.get("attempt", 1)
    answers, correct, by_question = _rung_distribution(s, rung_index, attempt)

    payload = {
        "phase": state.get("phase"),
        "rung_index": rung_index,
        "rung_count": len(state.get("rungs", [])),
        "attempt": attempt,
        "threshold": config.get("threshold", 70),
        "seconds_per_rung": config.get("seconds_per_rung", 60),
        "opened_at": state.get("opened_at"),
        "server_now": datetime.utcnow().isoformat() + "Z",
        "participants": [{"name": p.student.name, "level": p.level} for p in participants],
        "answered_count": len(answers),
        "rung_results": state.get("rung_results", []),
        "join_code": s.join_code,
        "hl_only": config.get("hl_only", False),
    }

    if state.get("phase") in ("rung_open", "rung_reveal") and state.get("rungs"):
        rung = state["rungs"][rung_index]
        questions = {}
        for role, qid in (("sl", rung.get("sl_qid")), ("hl", rung.get("hl_qid"))):
            if qid is None:
                continue
            q = TestQuestion.query.get(qid)
            if q is None:
                continue
            entry = {
                "qid": q.qid, "text": q.text, "options": q.options_list(),
                "subtopic": q.subtopic_code, "difficulty": q.difficulty,
                "is_hl_only": q.is_hl_only,
            }
            if state.get("phase") == "rung_reveal":
                entry["correct"] = q.correct_indices()
                entry["distribution"] = by_question.get(q.id, {})
            questions[role] = entry
        payload["questions"] = questions
        if state.get("phase") == "rung_reveal":
            total = len(answers)
            payload["reveal"] = {
                "correct": correct,
                "total": total,
                "passed": total > 0 and (correct * 100.0 / total) >= payload["threshold"],
            }
    return payload


@games_bp.route("/session/<int:session_id>/board/state")
@login_required
def board_state(session_id):
    _require_admin()
    s = GameSession.query.get_or_404(session_id)
    if s.game_type == "concept_ladder":
        return jsonify(_ladder_board_state(s))
    if s.game_type == "think_of_word":
        return jsonify(s.state_dict())
    if s.game_type == "connections":
        return jsonify(s.state_dict())
    abort(404)


@games_bp.route("/session/<int:session_id>/action", methods=["POST"])
@login_required
def board_action(session_id):
    _require_admin()
    s = GameSession.query.get_or_404(session_id)
    action = (request.json or {}).get("action")
    if s.game_type == "concept_ladder":
        return _ladder_action(s, action)
    if s.game_type == "think_of_word":
        return _word_action(s, action, request.json or {})
    if s.game_type == "connections":
        return _connections_action(s, action, request.json or {})
    abort(404)


def _ladder_action(s, action):
    state = s.state_dict()
    config = s.config_dict()
    rung_index = state.get("rung_index", 0)
    rungs = state.get("rungs", [])

    if action == "open_rung":
        # From lobby (first rung) or from a failed reveal (retry) or next rung.
        if state["phase"] == "lobby":
            s.status = "active"
        state["phase"] = "rung_open"
        state["opened_at"] = datetime.utcnow().isoformat() + "Z"
        _save_state(s, state)

    elif action == "reveal":
        if state["phase"] != "rung_open":
            return jsonify({"error": "No rung open."}), 409
        answers, correct, _ = _rung_distribution(s, rung_index, state.get("attempt", 1))
        total = len(answers)
        passed = total > 0 and (correct * 100.0 / total) >= config.get("threshold", 70)
        results = state.setdefault("rung_results", [])
        while len(results) <= rung_index:
            results.append({"passed": False, "attempts": []})
        results[rung_index]["attempts"].append({"correct": correct, "total": total})
        results[rung_index]["passed"] = passed
        state["phase"] = "rung_reveal"
        _save_state(s, state)

    elif action == "retry":
        # Post-discussion second attempt on the same rung.
        if state["phase"] != "rung_reveal" or state.get("attempt", 1) >= 2:
            return jsonify({"error": "Retry not available."}), 409
        state["attempt"] = 2
        state["phase"] = "rung_open"
        state["opened_at"] = datetime.utcnow().isoformat() + "Z"
        _save_state(s, state)

    elif action == "next_rung":
        if state["phase"] != "rung_reveal":
            return jsonify({"error": "Reveal the current rung first."}), 409
        if rung_index + 1 >= len(rungs):
            state["phase"] = "finished"
            s.status = "finished"
            s.finished_at = datetime.utcnow()
        else:
            state["rung_index"] = rung_index + 1
            state["attempt"] = 1
            state["phase"] = "rung_open"
            state["opened_at"] = datetime.utcnow().isoformat() + "Z"
        _save_state(s, state)

    elif action == "finish":
        state["phase"] = "finished"
        s.status = "finished"
        s.finished_at = datetime.utcnow()
        _save_state(s, state)

    else:
        return jsonify({"error": "Unknown action."}), 400

    return jsonify({"ok": True})


# ============================================================
# Concept Ladder — student join + play
# ============================================================

def _participant_for(s):
    return GameParticipant.query.filter_by(
        session_id=s.id, student_id=current_user.id).first()


def _student_question_for_rung(s, participant, rung):
    """The question this student is served for a rung. THE HL RULE LIVES HERE:
    SL participants are only ever served sl_qid, which _build_ladder guarantees
    is a non-HL question. Belt and braces: even if a session were mis-built,
    the final is_hl_only check refuses to serve HL content to an SL student."""
    qid = None
    if participant.level == "HL" and rung.get("hl_qid"):
        qid = rung["hl_qid"]
    else:
        qid = rung.get("sl_qid")
    if qid is None:
        return None
    q = TestQuestion.query.get(qid)
    if q is None:
        return None
    if q.is_hl_only and participant.level != "HL":
        return None
    return q


@games_bp.route("/join", methods=["GET", "POST"])
@login_required
def join():
    error = None
    if request.method == "POST":
        code = (request.form.get("code") or "").strip().upper()
        s = GameSession.query.filter_by(join_code=code).first() if code else None
        if s is None or s.status == "finished":
            error = "That code doesn't match a running game."
        else:
            enrollment = ClassEnrollment.query.filter_by(
                class_id=s.class_id, student_id=current_user.id).first()
            if enrollment is None:
                error = "This game is for a class you're not enrolled in."
            else:
                level = "HL" if (enrollment.level or "").upper() == "HL" else "SL"
                if s.config_dict().get("hl_only") and level != "HL":
                    error = "This ladder uses HL-only topics, so it's for HL students."
                else:
                    p = _participant_for(s)
                    if p is None:
                        p = GameParticipant(session_id=s.id,
                                            student_id=current_user.id, level=level)
                        db.session.add(p)
                        db.session.commit()
                    return redirect(url_for("games.play", session_id=s.id))
    return render_template("game_join.html", error=error,
                           prefill=(request.args.get("code") or "").upper())


@games_bp.route("/play/<int:session_id>")
@login_required
def play(session_id):
    s = GameSession.query.get_or_404(session_id)
    p = _participant_for(s)
    if p is None:
        return redirect(url_for("games.join"))
    if s.game_type == "concept_ladder":
        return render_template("game_play_ladder.html", session_obj=s)
    if s.game_type == "think_of_word":
        return render_template("game_play_word.html", session_obj=s)
    if s.game_type == "connections":
        return render_template("game_play_connections.html", session_obj=s,
                               config=s.config_dict(), state=s.state_dict())
    abort(404)


@games_bp.route("/play/<int:session_id>/state")
@login_required
def play_state(session_id):
    s = GameSession.query.get_or_404(session_id)
    if s.game_type == "concept_ladder":
        p = _participant_for(s)
        if p is None:
            abort(403)
        state = s.state_dict()
        config = s.config_dict()
        phase = state.get("phase")
        rung_index = state.get("rung_index", 0)
        attempt = state.get("attempt", 1)

        payload = {
            "phase": phase,
            "rung_index": rung_index,
            "rung_count": len(state.get("rungs", [])),
            "attempt": attempt,
            "seconds_per_rung": config.get("seconds_per_rung", 60),
            "opened_at": state.get("opened_at"),
            "server_now": datetime.utcnow().isoformat() + "Z",
        }

        if phase in ("rung_open", "rung_reveal") and state.get("rungs"):
            rung = state["rungs"][rung_index]
            q = _student_question_for_rung(s, p, rung)
            if q is not None:
                payload["question"] = {
                    "text": q.text,
                    "options": q.options_list(),
                    "difficulty": q.difficulty,
                    "is_hl": q.is_hl_only,
                }
                mine = GameRoundAnswer.query.filter_by(
                    session_id=s.id, participant_id=p.id,
                    round_index=rung_index, attempt=attempt).first()
                payload["answered"] = mine is not None
                if mine is not None:
                    payload["my_answer"] = mine.answer_index
                if phase == "rung_reveal":
                    payload["question"]["correct"] = q.correct_indices()
                    if mine is not None:
                        payload["my_correct"] = mine.is_correct
        return jsonify(payload)
    if s.game_type == "think_of_word":
        state = s.state_dict()
        # Add whether current user is the thinker
        state["is_thinker"] = (state.get("thinker_id") == current_user.id)
        # Add thinker info (name and level)
        if state.get("thinker_id"):
            thinker = GameParticipant.query.filter_by(
                session_id=s.id,
                student_id=state.get("thinker_id")
            ).first()
            if thinker:
                state["thinker_name"] = thinker.student.name
                state["thinker_level"] = thinker.level
        # Add server time for timer calculations
        state["server_now"] = datetime.utcnow().isoformat() + "Z"
        return jsonify(state)
    if s.game_type == "connections":
        return jsonify(s.state_dict())
    abort(404)


@games_bp.route("/play/<int:session_id>/answer", methods=["POST"])
@login_required
def play_answer(session_id):
    s = GameSession.query.get_or_404(session_id)
    if s.game_type == "concept_ladder":
        p = _participant_for(s)
        if p is None:
            abort(403)
        state = s.state_dict()
        if state.get("phase") != "rung_open":
            return jsonify({"error": "Answers are closed for this rung."}), 409

        rung_index = state.get("rung_index", 0)
        attempt = state.get("attempt", 1)
        rung = state.get("rungs", [])[rung_index]
        q = _student_question_for_rung(s, p, rung)
        if q is None:
            return jsonify({"error": "No question available for you on this rung."}), 404

        answer_index = (request.json or {}).get("answer_index")
        if not isinstance(answer_index, int) or not (0 <= answer_index < len(q.options_list())):
            return jsonify({"error": "Pick one of the options."}), 400

        existing = GameRoundAnswer.query.filter_by(
            session_id=s.id, participant_id=p.id,
            round_index=rung_index, attempt=attempt).first()
        if existing is not None:
            return jsonify({"error": "Already answered."}), 409

        db.session.add(GameRoundAnswer(
            session_id=s.id, participant_id=p.id, round_index=rung_index,
            attempt=attempt, question_id=q.id, answer_index=answer_index,
            is_correct=(answer_index in q.correct_indices()),
        ))
        db.session.commit()
        return jsonify({"ok": True})
    abort(404)


@games_bp.route("/play/<int:session_id>/action", methods=["POST"])
@login_required
def play_action(session_id):
    s = GameSession.query.get_or_404(session_id)
    if s.game_type == "think_of_word":
        return _word_action(s, (request.json or {}).get("action"), request.json or {})
    if s.game_type == "connections":
        return _connections_action(s, (request.json or {}).get("action"), request.json or {})
    abort(404)


@games_bp.route("/session/<int:session_id>/participants")
@login_required
def get_participants(session_id):
    s = GameSession.query.get_or_404(session_id)
    _require_admin()
    participants = GameParticipant.query.filter_by(session_id=s.id).all()
    return jsonify([{
        "id": p.student_id,
        "name": p.student.name,
        "level": p.level
    } for p in participants])


# ============================================================
# Think of a Word — board actions
# ============================================================

def _word_action(s, action, payload):
    state = s.state_dict()
    config = s.config_dict()
    word_bank = config.get("word_bank", DEFAULT_WORD_BANK)

    if action == "start_game":
        # Assign a random player as the thinker
        participants = GameParticipant.query.filter_by(session_id=s.id).all()
        if participants:
            thinker = random.choice(participants)
            state["thinker_id"] = thinker.student_id
            word = random.choice(word_bank)
            state["phase"] = "thinking_time"
            state["current_word"] = word
            state["question_count"] = 0
            state["guessed"] = False
            state["round_number"] = state.get("round_number", 0) + 1
            state["thinking_started_at"] = datetime.utcnow().isoformat() + "Z"
            state["thinking_time_seconds"] = 10
        else:
            return jsonify({"error": "No players joined yet."}), 409
        _save_state(s, state)

    elif action == "thinking_time_done":
        # Move from thinking time to questioning phase
        state["phase"] = "questioning"
        state["thinking_started_at"] = None
        _save_state(s, state)

    elif action == "increment_questions":
        state["question_count"] = state.get("question_count", 0) + 1
        _save_state(s, state)

    elif action == "guess_correct":
        state["guessed"] = True
        state["phase"] = "round_over"
        guessed_by = payload.get("guessed_by", "Unknown")
        rounds = state.setdefault("rounds", [])
        thinker = GameParticipant.query.filter_by(session_id=s.id, student_id=state.get("thinker_id")).first()
        thinker_name = thinker.student.name if thinker else "Unknown"
        rounds.append({
            "word": state.get("current_word"),
            "question_count": state.get("question_count", 0),
            "guessed_by": guessed_by,
            "thinker_name": thinker_name,
            "guessed_at": datetime.utcnow().isoformat() + "Z",
        })
        _save_state(s, state)

    elif action == "next_round":
        state["phase"] = "waiting_for_players"
        state["current_word"] = None
        state["question_count"] = 0
        state["guessed"] = False
        state["thinker_id"] = None
        _save_state(s, state)

    elif action == "finish":
        state["phase"] = "finished"
        s.status = "finished"
        s.finished_at = datetime.utcnow()
        _save_state(s, state)

    else:
        return jsonify({"error": "Unknown action."}), 400

    return jsonify({"ok": True})


# ============================================================
# Connections — board actions
# ============================================================

def _connections_action(s, action, payload):
    state = s.state_dict()
    config = s.config_dict()
    groups = config.get("groups", [])

    if action == "start_game":
        state["phase"] = "playing"
        _save_state(s, state)

    elif action == "select_word":
        word_idx = payload.get("word_idx")
        board = state.get("board", [])
        selection = state.get("selection", [])

        if not (isinstance(word_idx, int) and 0 <= word_idx < len(board)):
            return jsonify({"error": "Invalid word index."}), 400

        if word_idx in selection:
            selection.remove(word_idx)
        else:
            if len(selection) < 4:
                selection.append(word_idx)
        state["selection"] = selection
        _save_state(s, state)

    elif action == "submit_guess":
        board = state.get("board", [])
        selection = state.get("selection", [])

        if len(selection) != 4:
            return jsonify({"error": "Select exactly 4 words."}), 400

        selected_words = [board[i].upper() for i in selection]
        mistakes = state.get("mistakes", 0)

        # Check if selection matches any group
        for group_idx, group in enumerate(groups):
            group_words = [w.upper() for w in group.get("words", [])]
            if set(selected_words) == set(group_words):
                # Correct! Remove solved group
                solved = state.setdefault("solved_groups", [])
                if group_idx not in solved:
                    solved.append(group_idx)
                    # Remove these words from board
                    board = [w for i, w in enumerate(board) if i not in selection]
                    state["board"] = board
                state["selection"] = []
                if len(solved) == 4:
                    state["phase"] = "finished"
                    s.status = "finished"
                    s.finished_at = datetime.utcnow()
                _save_state(s, state)
                return jsonify({"ok": True, "correct": True})

        # Wrong guess — deduct a mistake
        mistakes += 1
        state["mistakes"] = mistakes
        state["selection"] = []
        if mistakes >= 4:
            state["phase"] = "finished"
            s.status = "finished"
            s.finished_at = datetime.utcnow()
        _save_state(s, state)
        return jsonify({"ok": True, "correct": False, "mistakes": mistakes})

    elif action == "shuffle":
        board = state.get("board", [])
        random.shuffle(board)
        state["board"] = board
        state["selection"] = []
        _save_state(s, state)

    elif action == "finish":
        state["phase"] = "finished"
        s.status = "finished"
        s.finished_at = datetime.utcnow()
        _save_state(s, state)

    else:
        return jsonify({"error": "Unknown action."}), 400

    return jsonify({"ok": True})


# ============================================================
# Think of a Word — setup + play
# ============================================================

DEFAULT_WORD_BANK = [
    "algorithm", "variable", "function", "loop", "array", "string", "integer",
    "boolean", "class", "object", "method", "parameter", "return", "condition",
    "debugging", "syntax", "library", "module", "recursion", "iteration",
    "encryption", "database", "query", "network", "protocol", "server",
]


@games_bp.route("/word/new", methods=["GET", "POST"])
@login_required
def word_setup():
    _require_admin()
    classes = (Class.query.filter_by(is_archived=False).order_by(Class.name).all())

    if request.method == "POST":
        class_id = request.form.get("class_id", type=int)
        timer_seconds = min(300, max(15, request.form.get("timer_seconds", 60, type=int)))
        word_bank_raw = (request.form.get("word_bank") or "").strip()
        word_bank = [w.strip().lower() for w in word_bank_raw.split("\n") if w.strip()]
        if not word_bank:
            word_bank = DEFAULT_WORD_BANK

        cls = Class.query.get(class_id) if class_id else None
        if cls is None:
            flash("Pick a class.", "error")
        else:
            session_obj = GameSession(
                game_type="think_of_word",
                class_id=cls.id,
                created_by_id=current_user.id,
                join_code=_generate_join_code(),
                status="lobby",
                config=json.dumps({
                    "timer_seconds": timer_seconds,
                    "word_bank": word_bank,
                }),
                state=json.dumps({
                    "phase": "waiting_for_players",
                    "round_number": 0,
                    "thinker_id": None,
                    "current_word": None,
                    "question_count": 0,
                    "guessed": False,
                    "rounds": [],
                }),
            )
            db.session.add(session_obj)
            db.session.commit()
            return redirect(url_for("games.board", session_id=session_obj.id))

    return render_template("game_word_setup.html", classes=classes)


# ============================================================
# Connections — setup + play
# ============================================================

@games_bp.route("/connections/new", methods=["GET", "POST"])
@login_required
def connections_setup():
    _require_admin()
    classes = (Class.query.filter_by(is_archived=False).order_by(Class.name).all())

    if request.method == "POST":
        class_id = request.form.get("class_id", type=int)
        title = (request.form.get("title") or "").strip() or "Connections Puzzle"

        words = [w.strip().upper() for w in request.form.getlist("word") if w.strip()]
        if len(words) != 16:
            flash("Exactly 16 words required.", "error")
        else:
            groups = []
            for i in range(4):
                group_words = [w.strip().upper() for w in request.form.getlist(f"group_{i}_words") if w.strip()]
                group_title = (request.form.get(f"group_{i}_title") or "").strip()
                group_color = request.form.get(f"group_{i}_color") or "yellow"
                if len(group_words) != 4:
                    flash(f"Group {i+1} needs exactly 4 words.", "error")
                    break
                if not group_title:
                    flash(f"Group {i+1} needs a title/theme.", "error")
                    break
                groups.append({
                    "title": group_title,
                    "words": group_words,
                    "color": group_color,
                })
            else:
                cls = Class.query.get(class_id) if class_id else None
                if cls is None:
                    flash("Pick a class.", "error")
                else:
                    # Shuffle word order for the puzzle
                    all_words = []
                    for g in groups:
                        all_words.extend(g["words"])
                    random.shuffle(all_words)

                    session_obj = GameSession(
                        game_type="connections",
                        class_id=cls.id,
                        created_by_id=current_user.id,
                        join_code=_generate_join_code(),
                        status="lobby",
                        config=json.dumps({
                            "title": title,
                            "groups": groups,
                        }),
                        state=json.dumps({
                            "phase": "lobby",  # lobby | playing | finished
                            "board": all_words,  # current word order
                            "solved_groups": [],  # indices of solved group categories
                            "mistakes": 0,  # 0-4 allowed mistakes
                            "selection": [],  # currently selected word indices
                        }),
                    )
                    db.session.add(session_obj)
                    db.session.commit()
                    return redirect(url_for("games.board", session_id=session_obj.id))

    return render_template("game_connections_setup.html", classes=classes)
