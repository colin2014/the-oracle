"""Read the printed exit tickets (PowerPoint) and turn them into web exit tickets.

Each subtopic folder holds "A1.1.1 Exit Ticket.pptx" (the sheet) and "A1.1.1 Exit Ticket Answers.pptx"
(the teacher answer sheet). The sheets are generated to a fixed layout, so the questions can be read
from the shapes' positions and text without any AI. Anything that can't be read with confidence is
reported as a warning so it can be checked in the editor; imported tickets are always DRAFTS.

Needs python-pptx (only for importing; the running app doesn't use it):  pip install python-pptx

    python exit_ticket_import.py <Subtopics folder>            # dry run: report only
    python exit_ticket_import.py <Subtopics folder> --apply    # create draft tickets in the database
"""
import itertools
import re
import sys
from pathlib import Path

import exit_ticket_logic as L

LABELS = {
    "MULTIPLE CHOICE": "mcq", "TRUE OR FALSE": "truefalse", "FILL THE GAP": "fill", "MATCH THE PAIRS": "match",
    "PUT IN ORDER": "order", "SHORT ANSWER": "short", "EXPLAIN": "explain",
}
STOP_LABELS = {"REFLECTION"}


# --------------------------------------------------------------------------- reading a slide

class Box:
    __slots__ = ("x", "y", "w", "h", "text", "size", "bold", "color")

    def __init__(self, x, y, w, h, text, size, bold, color):
        self.x, self.y, self.w, self.h, self.text, self.size, self.bold, self.color = x, y, w, h, text, size, bold, color

    def __repr__(self):
        return f"Box({self.x:.2f},{self.y:.2f} {self.text[:30]!r})"


def read_boxes(path):
    """Every text shape of every slide, as (slide number, Box), in reading order."""
    from pptx import Presentation
    from pptx.util import Emu
    out = []
    for n, slide in enumerate(Presentation(str(path)).slides):
        for sh in slide.shapes:
            if not getattr(sh, "has_text_frame", False) or not sh.has_text_frame:
                continue
            text = sh.text_frame.text.strip()
            if not text:
                continue
            run = next((r for p in sh.text_frame.paragraphs for r in p.runs), None)
            size = run.font.size.pt if run is not None and run.font.size else 0
            color = None
            try:
                if run is not None and run.font.color and run.font.color.type == 1:
                    color = str(run.font.color.rgb)
            except Exception:  # noqa: BLE001
                pass
            out.append((n, Box(Emu(sh.left).inches, Emu(sh.top).inches, Emu(sh.width).inches, Emu(sh.height).inches,
                               re.sub(r"\s*\n\s*", " ", text), size, bool(run is not None and run.font.bold), color)))
    out.sort(key=lambda t: (t[0], round(t[1].y, 2), t[1].x))
    return out


def strip_number(text):
    return re.sub(r"^\s*\d+\s{1,}", "", text).strip()


# --------------------------------------------------------------------------- the ticket sheet

def read_ticket(path):
    """Header fields and one raw section per question, in order."""
    boxes = read_boxes(path)
    header = {"code": None, "objective": None, "title": None}
    for _, b in boxes:
        m = re.match(r"^(\w\d+\.\d+\.\d+)\s+(.*)$", b.text)
        if m and b.bold and b.size >= 11.5 and not header["code"]:
            header["code"], header["objective"] = m.group(1), m.group(2).strip()
        m2 = re.match(r"^Computer Science\s*·\s*(.+)$", b.text)
        if m2 and not header["title"]:
            header["title"] = m2.group(1).strip()

    sections, current = [], None
    for slide, b in boxes:
        label = b.text.upper()
        if b.color == "FFFFFF" and b.bold and label in LABELS and b.x < 1.2:
            current = {"qtype": LABELS[label], "slide": slide, "top": b.y, "boxes": []}
            sections.append(current)
            continue
        if b.text.upper() in STOP_LABELS:
            current = None
            continue
        if current is not None and current["slide"] == slide and b.y >= current["top"] - 0.01:
            current["boxes"].append(b)
    return header, sections


def _prompt(section):
    for b in section["boxes"]:
        if b.bold and b.size >= 11 and re.match(r"^\d+\b", b.text):
            text = strip_number(b.text)
            return "" if re.fullmatch(r"\d+", text) else text      # some questions are just a number; the answer sheet has the wording
    return ""


def parse_section(sec):
    """(question dict, warnings) for one section of the ticket sheet; answers are filled in later."""
    warn = []
    q = {"qtype": sec["qtype"], "prompt": _prompt(sec)}
    boxes = sec["boxes"]
    body = [b for b in boxes
            if not (b.bold and b.size >= 11 and re.match(r"^\d+\b", b.text))
            and b.y < 11.0 and not re.search(r"Page \d+ of \d+", b.text)]          # the footer is not a question

    if q["qtype"] == "mcq":
        opts = [b.text for b in body if b.x > 1.2 and b.size and b.size < 11.5 and not re.fullmatch(r"[A-H]", b.text)]
        q["options"] = opts
    elif q["qtype"] == "truefalse":
        q["statements"] = [b.text for b in body if b.x < 1.2 and b.w > 4 and not re.fullmatch(r"[TF]", b.text)]
    elif q["qtype"] == "fill":
        q["sentences"] = [re.sub(r"_{3,}", L.BLANK, b.text) for b in body if "___" in b.text]
    elif q["qtype"] == "match":
        left = sorted((b for b in body if b.x < 1.2 and b.bold and b.w < 2.5), key=lambda b: b.y)
        right = sorted((b for b in body if 3.0 < b.x < 3.7 and b.w > 3), key=lambda b: b.y)
        q["terms"], q["descriptions"] = [b.text for b in left], [b.text for b in right]
        if len(q["terms"]) != len(q["descriptions"]):
            warn.append("match: the number of terms and descriptions differ")
    elif q["qtype"] == "order":
        q["items"] = [b.text for b in sorted(body, key=lambda b: b.y) if b.x > 1.2 and not re.fullmatch(r"\d", b.text)]
    return q, warn


# --------------------------------------------------------------------------- the answer sheet

def read_answers(path):
    """List of {"qtype","prompt","answer"} blocks from the answer sheet, in order."""
    # A question starts at its label line ("MULTIPLE CHOICE   Which ..."). The "Q1" badges are ignored: they sit
    # at a slightly different height from the label, so position-sorting can put a badge AFTER its label.
    blocks, cur = [], None
    for _, b in read_boxes(path):
        t = b.text
        m = re.match(r"^([A-Z][A-Z ]+?)\s{2,}(.*)$", t)
        if m and m.group(1).strip() in LABELS:
            cur = {"qtype": LABELS[m.group(1).strip()], "prompt": m.group(2).strip(), "answer": ""}
            blocks.append(cur)
        elif t.startswith("Answer:") and cur is not None and not cur["answer"]:
            cur["answer"] = re.sub(r"^Answer:\s*", "", t).strip()
    return blocks


def _words(text):
    return {w[:5] for w in re.findall(r"[a-z]{3,}", text.lower())}


def _assign(terms, hints, descriptions):
    """Match each term's answer hint to a description by shared word stems. Returns (order, confident)."""
    n = len(terms)
    score = [[len(_words(hints[i]) & _words(descriptions[j])) for j in range(n)] for i in range(n)]
    best, best_perm, second = -1, None, -1
    for perm in itertools.permutations(range(n)):
        s = sum(score[i][perm[i]] for i in range(n))
        if s > best:
            best, second, best_perm = s, best, perm
        elif s > second:
            second = s
    return list(best_perm), best > 0 and best > second and all(score[i][best_perm[i]] > 0 for i in range(n))


def _split_alternatives(text):
    text = text.strip().rstrip(".")
    alts = []
    m = re.match(r"^(.*?)\s*\((.+)\)\s*$", text)
    if m:
        alts += [m.group(1), m.group(2)]
    else:
        alts.append(text)
    out = []
    for a in alts:
        out += [x.strip() for x in re.split(r"\s*/\s*|\s+or\s+", a) if x.strip()]
    seen, res = set(), []
    for a in out:
        if a.lower() not in seen:
            seen.add(a.lower()); res.append(a)
    return res


# --------------------------------------------------------------------------- putting it together

def build_question(raw, ans, warn):
    """One clean question (in the shape L.clean_question expects), or None."""
    qtype, prompt = raw["qtype"], raw["prompt"] or (ans["prompt"] if ans else "")
    answer = ans["answer"] if ans else ""
    if not ans:
        warn.append(f"{qtype}: no matching entry on the answer sheet")

    if qtype == "mcq":
        m = re.search(r"correct answer:\s*([A-H])\b", answer, re.I) or re.match(r"^\s*([A-H])\b", answer)
        if not m:
            warn.append("mcq: couldn't read the correct option letter"); return None
        return {"qtype": "mcq", "prompt": prompt, "data": {"options": raw["options"], "correct": ord(m.group(1).upper()) - 65}}

    if qtype == "truefalse":
        vals = []
        for v in re.split(r"[·•;]", answer):
            m = re.match(r"\s*(true|false)\b", v.strip().lower())
            if v.strip():
                vals.append(m.group(1) if m else v.strip().lower())
        if len(vals) != len(raw["statements"]) or any(v not in ("true", "false") for v in vals):
            warn.append(f"truefalse: {len(raw['statements'])} statements but answers read as {vals}"); return None
        return {"qtype": "truefalse", "prompt": prompt, "data": {"statements": [{"text": s, "answer": v == "true"} for s, v in zip(raw["statements"], vals)]}}

    if qtype == "fill":
        parts = re.findall(r"\(\d+\)\s*(.*?)(?=\s{2,}\(\d+\)|$)", answer)
        blanks_in_text = [s.count("____") for s in raw["sentences"]]
        if len(parts) != sum(blanks_in_text):
            warn.append(f"fill: {sum(blanks_in_text)} blanks but {len(parts)} answers"); return None
        it = iter(parts)
        sentences = [{"text": s, "blanks": [_split_alternatives(next(it)) for _ in range(c)]} for s, c in zip(raw["sentences"], blanks_in_text)]
        return {"qtype": "fill", "prompt": prompt, "data": {"sentences": sentences}}

    if qtype == "match":
        terms, descs = raw["terms"], raw["descriptions"]
        if len(terms) != len(descs) or len(terms) < 2:
            warn.append("match: couldn't read the terms and descriptions"); return None
        entries = [e.strip(" .") for e in re.split(r"\s*[·•]\s*", answer) if e.strip(" .")]
        hints = []
        if len(entries) == len(terms):
            hints = [re.split(r"\s*[-–:]\s*", e, maxsplit=1)[-1] for e in entries]          # text after the first dash
        else:
            for t in terms:
                m = re.search(re.escape(t) + r"\s*[-–:]\s*(.*?)(?=\s*·\s*|$)", answer)
                hints.append(m.group(1) if m else "")
        if not all(hints):
            warn.append("match: couldn't read a term's answer on the answer sheet"); return None
        order, confident = _assign(terms, hints, descs)
        if not confident:
            warn.append("match: the pairing is a best guess (check it in the editor)")
        return {"qtype": "match", "prompt": prompt, "data": {"pairs": [{"left": t, "right": descs[order[i]]} for i, t in enumerate(terms)], "distractors": []}}

    if qtype == "order":
        given = [x.strip().rstrip(".") for x in re.findall(r"\d\s+(.+?)(?=\s*·\s*\d\s|$)", re.sub(r"^Order:\s*", "", answer))]
        items = raw["items"]
        if len(given) != len(items):
            warn.append(f"order: {len(items)} items but the answer sheet lists {len(given)}"); return None
        lowered = {i.lower(): i for i in items}
        if all(g.lower() in lowered for g in given):
            ordered = [lowered[g.lower()] for g in given]
        else:
            perm, confident = _assign(given, given, items)          # answer entry i -> the ticket item it abbreviates
            ordered = [items[perm[i]] for i in range(len(given))]
            if not confident:
                warn.append("order: the sequence is a best guess (check it in the editor)")
        return {"qtype": "order", "prompt": prompt, "data": {"items": ordered}}

    # short / explain: the answer sheet gives a model answer
    model = re.sub(r"^(Model|Any two|Any)\s*:?\s*", "", answer).strip() if answer.startswith("Model") else answer
    points = [p.strip(" .") for p in re.split(r";", model) if len(p.strip()) > 3] if ";" in model else []
    return {"qtype": qtype, "prompt": prompt, "data": {"model_answer": model[:2000], "marking_points": points[:10]}}


def allocate_marks(questions):
    """The scheme the printed tickets follow: MCQ 1, T/F 1 per statement, fill 1 per blank, match/order/short 2,
    explain takes the rest of the 10. Returns True if the total came to exactly 10."""
    for q in questions:
        d = q["data"]
        q["marks"] = {"mcq": 1.0, "truefalse": float(len(d.get("statements", []))),
                      "fill": float(sum(len(s["blanks"]) for s in d.get("sentences", []))),
                      "match": 2.0, "order": 2.0, "short": 2.0, "explain": 2.0}[q["qtype"]]
    return abs(sum(q["marks"] for q in questions) - 10) < 1e-9


def convert(ticket_path, answers_path):
    """(ticket dict ready for L.clean_ticket, warnings). Raises if the files can't be read at all."""
    warn = []
    header, sections = read_ticket(ticket_path)
    answers = read_answers(answers_path) if answers_path and Path(answers_path).exists() else []
    if not header["code"]:
        warn.append("couldn't read the topic code")
    if len(answers) != len(sections):
        warn.append(f"{len(sections)} questions on the sheet but {len(answers)} on the answer sheet")
    questions = []
    for i, sec in enumerate(sections):
        raw, w = parse_section(sec)
        warn += w
        ans = answers[i] if i < len(answers) and answers[i]["qtype"] == sec["qtype"] else next((a for a in answers if a["qtype"] == sec["qtype"]), None)
        q = build_question(raw, ans, warn)
        if q:
            questions.append(q)
        else:
            warn.append(f"question {i + 1} ({sec['qtype']}) was NOT imported")
    if not allocate_marks(questions):
        warn.append(f"marks add up to {sum(q['marks'] for q in questions):g}, not 10")
    ticket = {"title": header["title"] or header["code"] or "Exit ticket", "code": header["code"], "objective": header["objective"],
              "status": "draft", "allow_retries": True, "show_answers": "after", "questions": questions}
    return ticket, warn


def find_pairs(folder):
    for f in sorted(Path(folder).rglob("* Exit Ticket.pptx")):
        yield f, f.with_name(f.name.replace("Exit Ticket.pptx", "Exit Ticket Answers.pptx"))


def main(argv):
    folder, apply = argv[1], "--apply" in argv
    ok = needs_check = failed = 0
    good = []
    for ticket_path, answers_path in find_pairs(folder):
        try:
            ticket, warn = convert(ticket_path, answers_path)
            L.clean_ticket(ticket)                                  # must satisfy the same rules as the editor
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"FAILED  {ticket_path.name}: {exc}")
            continue
        if warn:
            needs_check += 1
            print(f"CHECK   {ticket_path.name}: " + "; ".join(warn))
        else:
            ok += 1
        good.append(ticket)
    print(f"\n{ok} clean, {needs_check} imported with warnings, {failed} failed  ({ok + needs_check + failed} tickets)")
    if apply:
        from app import app
        from extensions import db
        from models import ExitTicket, ExitTicketQuestion, UnitPlanTopic, User
        import json
        with app.app_context():
            admin = User.query.filter_by(role="admin").order_by(User.id).first()
            made = skipped = 0
            for t in good:
                if t["code"] and ExitTicket.query.filter_by(code=t["code"]).first():
                    skipped += 1
                    continue
                topic = UnitPlanTopic.query.filter_by(code=t["code"]).first() if t["code"] else None
                row = ExitTicket(title=t["title"], code=t["code"], topic_id=topic.topic_id if topic else None, objective=t["objective"],
                                 status="draft", created_by_id=admin.id)
                db.session.add(row); db.session.flush()
                for pos, q in enumerate(L.clean_ticket(t)["questions"]):
                    db.session.add(ExitTicketQuestion(ticket_id=row.id, position=pos, qtype=q["qtype"], prompt=q["prompt"], marks=q["marks"], data=json.dumps(q["data"])))
                made += 1
            db.session.commit()
            print(f"created {made} draft tickets, skipped {skipped} that already exist")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
