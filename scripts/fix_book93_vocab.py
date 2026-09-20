#!/usr/bin/env python3
"""
Review and normalize every vocabulary block in Book 93.

Goals
-----
1. Make sidebar_sections the single source of truth for vocabulary:
   remove any duplicated vocab sidebox from a page's stored ``blocks`` array
   (the render route re-injects it from sidebar_sections at request time).
2. Normalize the vocab text so each definition renders on its own line,
   as ``<strong>Term</strong>: definition`` joined by <br>.
3. Best-effort auto-repair of messy blocks: mojibake (U+FFFD -> en dash),
   run-on / unbolded term lists, and ``Term:</strong>:`` double colons.
   Anything parsed with low confidence is flagged for manual review.

Usage
-----
    python scripts/fix_book93_vocab.py            # dry run: report only
    python scripts/fix_book93_vocab.py --apply    # write changes (+ .vocabbak backups)
"""
import argparse
import glob
import json
import os
import re
import shutil
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

BOOK_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "data", "Book_93")


# --------------------------------------------------------------------------- #
# Parsing
# --------------------------------------------------------------------------- #
def _clean(text):
    """Strip inline tags and collapse whitespace, leaving plain text."""
    text = re.sub(r"(?i)</?strong>", "", text)
    text = re.sub(r"(?i)</?b>", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&amp;", "&").replace("&nbsp;", " ")
    return re.sub(r"[ \t]+", " ", text).strip()


# A trailing, unbolded term introduces a new definition:  "... foo. Bar Baz – ..."
_RUNON = re.compile(
    r"(?<=[.)])\s+"
    r"(?=[A-Z][A-Za-z0-9()/&]*(?:\s+[A-Za-z0-9()/&]+){0,4}\s+[–—-]\s+[A-Z])"
)

# A short Title-case term phrase (<=5 words) immediately followed by ':' or a
# spaced dash — used to split inline, unbolded run-on lists like
# "Schema: The structure of a database.   DDL: Language used to ...".
_TERM = r"[A-Z][\w()/.'’&+-]*(?:\s+[A-Za-z0-9()/.'’&+-]+){0,4}?(?::|\s[–—-]\s)"
_INLINE_BOUNDARY = re.compile(r"(?<=[.?!)])\s+(?=" + _TERM + r")")
# Dash glossary "Term – lowercase def   Term – lowercase def" (no sentence break
# between items, e.g. multi-space separated lists that _clean has collapsed).
_DASH_BOUNDARY = re.compile(
    r"\s+(?=[A-Z][\w()/.'’&+-]*(?:\s+[A-Za-z0-9()/.'’&+-]+){0,3}\s[–—]\s[a-z])"
)


def _is_prose(term, definition):
    """A parsed 'term' that is really Study Tip / Fun fact prose, not vocabulary."""
    return (len(term.split()) > 7
            or term.rstrip().endswith(".")
            or (not definition and len(term) > 30))


def _split_inline(clean_text):
    """Split one cleaned chunk into (term, definition) pairs, handling both
    bolded-then-runon and fully inline unbolded term lists."""
    raw_segs = []
    for seg in _INLINE_BOUNDARY.sub("\x00", clean_text).split("\x00"):
        for piece in _RUNON.split(seg):
            raw_segs.extend(_DASH_BOUNDARY.sub("\x00", piece).split("\x00"))

    # A boundary can fire falsely after an abbreviation ("Latency vs." | "Throughput").
    # A fragment with no term header belongs to the term name that follows it.
    segs, carry = [], ""
    for seg in raw_segs:
        seg = seg.strip()
        if not seg:
            continue
        if _has_sep(seg):
            segs.append((carry + " " + seg).strip() if carry else seg)
            carry = ""
        else:
            carry = (carry + " " + seg).strip() if carry else seg
    if carry:
        if segs:
            segs[-1] = segs[-1] + " " + carry
        else:
            segs.append(carry)

    entries = []
    for seg in segs:
        term, definition = _term_def(seg)
        if term:
            entries.append((term, definition))
    return entries


def _term_def(chunk):
    """Split one cleaned chunk into (term, definition)."""
    chunk = chunk.strip()
    # Prefer a colon separator, then a *spaced* dash (so "8-bit" is not split).
    m = re.match(r"^(.{1,70}?)\s*:\s+(.*)$", chunk, re.S)
    if not m:
        m = re.match(r"^(.{1,70}?)\s+[–—-]\s+(.*)$", chunk, re.S)
    if m:
        term, definition = m.group(1), m.group(2)
    else:
        term, definition = chunk, ""
    term = term.strip().rstrip(":").strip()
    # "Vocabulary" section title occasionally leaked into the first bold term,
    # sometimes with no separating space ("VocabularyGPU").
    term = re.sub(r"^Vocabulary\s*(?=[A-Z])", "", term)
    return term, re.sub(r"\s+", " ", definition).strip()


def _has_sep(seg):
    """True if seg begins with a real 'term: def' / 'term - def' header."""
    return bool(_term_def(seg)[1])


def parse_vocab(raw):
    """Return entries = list of (term, definition) parsed from a vocab blob."""
    if not raw or not raw.strip():
        return []

    s = raw
    s = re.sub(r"(?i)<br\s*/?>", "\n", s)
    s = re.sub(r"(?i)</div>", "\n", s)
    s = re.sub(r"(?i)<div[^>]*>", "\n", s)
    s = s.replace("&nbsp;", " ")
    s = s.replace("�", "–")          # mojibake -> en dash
    s = s.replace("\r", "")
    # Force every bolded term to begin a new record.
    s = re.sub(r"(?i)\s*<strong>\s*", "\x00<strong>", s)

    parts = re.split(r"\x00|\n+", s)
    entries = []
    for part in parts:
        cleaned = _clean(part)
        if cleaned:
            entries.extend(_split_inline(cleaned))
    return entries


def _norm(text):
    # Punctuation-insensitive so "8-bit" and "8 bit" compare equal when matching
    # concatenated section text against the vocab blob.
    return re.sub(r"[^a-z0-9]+", " ", _clean(text or "").lower()).strip()


def trim_junk(entries, other_text):
    """Drop the trailing run of entries that are really other sidebar sections.

    Scraping concatenated Study Tip / Fun fact / Applied Work / TOK text onto the
    end of the Vocabulary field; those sections also exist under their own keys,
    so the first entry whose text reappears in ``other_text`` marks the boundary
    between genuine vocabulary and junk (junk is always trailing).
    """
    for i, (term, definition) in enumerate(entries):
        probe = _norm(f"{term} {definition}")[:35]
        matches_section = len(probe) >= 15 and probe in other_text
        # Junk is trailing: prose masquerading as a term, or a bare heading
        # ("Procedure:", "OLAP Analysis") with no definition.
        junk_like = i >= 1 and (_is_prose(term, definition) or not definition)
        if matches_section or junk_like:
            return entries[:i], entries[i:]
    return entries, []


def assess(entries):
    """Flag a kept vocab list as low confidence (worth a human glance)."""
    if len(entries) < 2:
        return True
    for term, definition in entries:
        if not definition or _is_prose(term, definition):
            return True          # a sentence misread as a term, or a bare term
    return False


def build_canonical(entries):
    """Render entries as one definition per line."""
    lines = []
    for term, definition in entries:
        if definition:
            lines.append(f"<strong>{term}</strong>: {definition}")
        else:
            lines.append(f"<strong>{term}</strong>")
    return "<br>".join(lines)


# --------------------------------------------------------------------------- #
# Per-file processing
# --------------------------------------------------------------------------- #
def sidebar_vocab_key(data):
    for k in data.get("sidebar_sections", {}):
        if "Vocab" in k:
            return k
    return None


def block_vocab(data):
    for b in data.get("blocks", []) or []:
        if b.get("type") == "sidebox" and b.get("style") == "vocab":
            return b
    return None


def process(path):
    """Return (report, data, changed) for one content.json."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    folder = os.path.basename(os.path.dirname(path))
    rep = {"folder": folder, "path": path, "action": "none", "source": None,
           "kept": 0, "dropped": 0, "review": False, "note": "",
           "entries": [], "dropped_entries": []}

    side_key = sidebar_vocab_key(data)
    side_text = data["sidebar_sections"][side_key] if side_key else None
    blk = block_vocab(data)
    blk_text = blk.get("text") if blk else None

    if side_text is None and blk_text is None:
        return rep, data, False  # page has no vocabulary

    # Pick the richer source when both exist and disagree.
    source, base_text = "sidebar", side_text
    if blk_text is not None:
        if side_text is None:
            source, base_text = "block", blk_text
        elif _clean(side_text) != _clean(blk_text):
            s_n, b_n = len(parse_vocab(side_text)), len(parse_vocab(blk_text))
            if (b_n, len(_clean(blk_text))) > (s_n, len(_clean(side_text))):
                source, base_text = "block", blk_text
                rep["note"] = "divergent -> kept block (richer)"
            else:
                rep["note"] = "divergent -> kept sidebar (richer)"

    # Junk detection compares against every OTHER sidebar section + questions.
    other = " \x01 ".join(_norm(v) for k, v in data["sidebar_sections"].items()
                          if k != side_key)
    other += " \x01 " + _norm(" ".join(str(q) for q in data.get("practice_questions", [])))

    entries = parse_vocab(base_text)
    kept, dropped = trim_junk(entries, other)
    canonical = build_canonical(kept)

    rep.update(source=source, kept=len(kept), dropped=len(dropped),
               review=assess(kept), entries=kept, dropped_entries=dropped)

    dest_key = side_key or "Vocabulary"
    changed = False
    if data["sidebar_sections"].get(dest_key) != canonical:
        data["sidebar_sections"][dest_key] = canonical
        changed = True
    if blk is not None:
        data["blocks"] = [b for b in data["blocks"]
                          if not (b.get("type") == "sidebox" and b.get("style") == "vocab")]
        changed = True
        rep["note"] = (rep["note"] + "; " if rep["note"] else "") + "removed dup sidebox from blocks"

    rep["action"] = "update" if changed else "none"
    return rep, data, changed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write changes (default: dry run)")
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(BOOK_DIR, "*", "content.json")))
    reports, review = [], []
    n_changed = tot_kept = tot_dropped = 0

    for path in files:
        rep, data, changed = process(path)
        reports.append(rep)
        tot_kept += rep["kept"]
        tot_dropped += rep["dropped"]
        if rep["review"]:
            review.append(rep)
        if changed:
            n_changed += 1
            if args.apply:
                shutil.copyfile(path, path + ".vocabbak")
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

    mode = "APPLIED" if args.apply else "DRY RUN"
    print(f"=== Book 93 vocabulary normalization ({mode}) ===")
    print(f"scanned {len(files)} pages | {n_changed} changed | "
          f"{tot_kept} real defs kept | {tot_dropped} junk defs dropped\n")

    for r in reports:
        if r["action"] == "none" and not r["review"]:
            continue
        flag = "  << REVIEW" if r["review"] else ""
        drop = f" drop={r['dropped']}" if r["dropped"] else ""
        note = f"  [{r['note']}]" if r["note"] else ""
        print(f"  {r['folder']:<10} {r['action']:<7} src={r['source'] or '-':<7} "
              f"kept={r['kept']:<3}{drop}{note}{flag}")

    if review:
        print(f"\n--- {len(review)} page(s) LOW CONFIDENCE (verify by hand) ---")
        for r in review:
            print(f"  {r['folder']}  (kept {r['kept']}, dropped {r['dropped']})")

    # Full before/after dump for human review.
    report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "book93_vocab_report.txt")
    with open(report_path, "w", encoding="utf-8") as rf:
        for r in reports:
            if r["action"] == "none" and not r["review"]:
                continue
            rf.write(f"===== {r['folder']}  (src={r['source']}, kept={r['kept']}, "
                     f"dropped={r['dropped']}{', REVIEW' if r['review'] else ''}) =====\n")
            for t, d in r["entries"]:
                rf.write(f"  KEEP  {t}: {d}\n")
            for t, d in r["dropped_entries"]:
                rf.write(f"  DROP  {t}: {d[:90]}\n")
            rf.write("\n")
    print(f"\nfull before/after report written to: {report_path}")

    if not args.apply:
        print("(dry run — no files written; re-run with --apply, backups go to *.vocabbak)")


if __name__ == "__main__":
    main()
