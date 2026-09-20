#!/usr/bin/env python3
"""
Rebuild the `blocks` array for Book 93 topics whose stored blocks contain no
main body content (heading/text). These pages render blank because the reader
route (get_book_page) only migrates main_content -> blocks when the `blocks`
key is ABSENT; these pages have an empty/near-empty list, so migration is
skipped and nothing shows.

The scraped main_content keys embed a DOM sequence number:
    "Main Content (N)"          -> body paragraph at DOM position N
    "__heading_L__Title_N"      -> level-L heading "Title" at DOM position N
Ordering by N reconstructs the original article (headings interleaved with
paragraphs). Sidebar-style sections are rendered from sidebar_sections (as the
route does), so heading/text entries that merely duplicate a sidebar section
are skipped.

Usage:
    python scripts/rebuild_book93_blocks.py             # dry run + previews
    python scripts/rebuild_book93_blocks.py --preview A1.3.6 A2.1.3
    python scripts/rebuild_book93_blocks.py --apply     # writes (+ .blocksbak)
"""
import argparse, glob, json, os, re, shutil, sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

BOOK_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "data", "Book_93")

HEAD_KEY = re.compile(r"^__heading_(\d+)__(.*?)_(\d+)$")
MC_KEY = re.compile(r"^Main Content \((\d+)\)$")

# Heading titles that name a sidebar/aside section — the body should not repeat
# them as headings; their content lives in sidebar_sections.
SIDEBAR_TITLES = {
    "vocabulary", "practice questions", "tok / ethics", "tok", "atl skills",
    "approaches to learning", "international-mindedness",
    "international mindedness and ethics", "international-mindedness and ethics",
    "guiding questions", "fun fact", "fun facts", "theory of knowledge",
    "study tip", "study tips", "applied work", "applied", "key point", "key points",
}


def _norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def collect(mc):
    """Return list of (seq, kind, level, text) parsed from main_content keys."""
    items = []
    for key, val in (mc or {}).items():
        m = HEAD_KEY.match(key)
        if m:
            level, title, seq = int(m.group(1)), m.group(2), int(m.group(3))
            items.append((seq, "heading", level, title.strip()))
            continue
        m = MC_KEY.match(key)
        if m:
            items.append((int(m.group(1)), "text", None, (val or "").strip()))
    items.sort(key=lambda t: t[0])
    return items


def build_blocks(data):
    """Reconstruct a blocks array from raw scraped fields (route-compatible)."""
    mc = data.get("main_content") or {}
    items = collect(mc)

    # Signatures of sidebar section text, so we can drop body paragraphs that are
    # just a duplicate of an aside (International-Mindedness, ATL, ...).
    side_sigs = [_norm(v)[:60] for v in (data.get("sidebar_sections") or {}).values()
                 if _norm(v)]

    # Legacy pages carry one giant "Main Content (1)" blob that concatenates the
    # whole article; the granular paragraphs (3,4,5,...) repeat its content. Drop
    # any paragraph whose text is a superset containing >= 2 other paragraphs.
    text_norms = {i: _norm(t) for i, (seq, k, lv, t) in enumerate(items)
                  if k == "text" and t}
    blob_idx = set()
    for i, ni in text_norms.items():
        if len(ni) < 400:
            continue
        contained = sum(1 for j, nj in text_norms.items()
                        if j != i and len(nj) > 200 and nj in ni)
        if contained >= 2:
            blob_idx.add(i)

    blocks = []
    if data.get("main_heading"):
        blocks.append({"type": "heading", "level": 1, "text": data["main_heading"]})

    seen = set()
    for i, (seq, kind, level, text) in enumerate(items):
        if not text:
            continue
        if kind == "heading":
            if _norm(text) in SIDEBAR_TITLES:
                continue
            blocks.append({"type": "heading", "level": max(2, min(level, 4)), "text": text})
        else:  # text paragraph
            if i in blob_idx:
                continue                      # giant concatenated blob
            full = _norm(text)
            sig = full[:60]
            if not sig or sig in seen:
                continue                      # exact/near duplicate paragraph
            if any(sig == s for s in side_sigs):
                continue                      # duplicates an aside section
            # A bare label that is really a sidebar heading, e.g. "Practice Questions"
            if _norm(text) in SIDEBAR_TITLES:
                continue
            seen.add(sig)
            blocks.append({"type": "text", "text": text})

    # Preserve any existing Guiding-Questions panel block from the stored blocks
    # (these pages already had one; the reader renders it into #guidingQuestions).
    guiding = [b for b in (data.get("blocks") or []) if b.get("type") == "guiding"]
    if guiding:
        insert_at = 1 if blocks and blocks[0]["type"] == "heading" else 0
        for g in reversed(guiding):
            blocks.insert(insert_at, g)

    # Practice questions -> reveal blocks (route parity)
    practice = data.get("practice_questions") or []
    if practice:
        blocks.append({"type": "heading", "level": 3, "text": "Practice Questions"})
        for q in practice:
            qt = q.get("question", "")
            if q.get("marks"):
                qt = f"[{q['marks']}]  {qt}"
            blocks.append({"type": "question", "text": qt, "answer": q.get("answer", "")})

    # Sidebar sections -> sideboxes (vocab is re-injected canonically by the route,
    # so we skip vocab here to avoid a duplicate).
    for name, text in (data.get("sidebar_sections") or {}).items():
        if "Vocab" in name:
            continue
        style = "study"
        if "Theory" in name:
            style = "theory"
        elif "Applied" in name or "Activity" in name:
            style = "applied"
        elif "Fun" in name:
            style = "funfact"
        blocks.append({"type": "sidebox", "style": style, "title": name, "text": text})

    # Videos (side) then images
    for v in data.get("videos", []) or []:
        if v.get("src"):
            blocks.append({"type": "video", "src": v["src"],
                           "title": v.get("title") or "Video", "side": True})
    for img in data.get("images", []) or []:
        src = img["local_path"]
        if not (src.startswith("data:") or src.startswith("http") or src.startswith("/data/")):
            src = f"/data/{src}"
        blocks.append({"type": "image", "src": src, "alt": img.get("alt_text", "")})

    return blocks


def needs_rebuild(data):
    body = sum(1 for b in (data.get("blocks") or [])
               if b.get("type") in ("text", "heading") and str(b.get("text", "")).strip())
    return body == 0


def preview(folder, blocks):
    print(f"\n===== {folder}  ({len(blocks)} blocks) =====")
    for b in blocks:
        t = b["type"]
        if t == "heading":
            print(f"  H{b['level']}: {b['text'][:90]}")
        elif t == "text":
            print(f"  P  : {b['text'][:90].replace(chr(10),' ')} ... ({len(b['text'])} ch)")
        elif t == "sidebox":
            print(f"  BOX[{b['style']}] {b['title']}: {str(b['text'])[:60].replace(chr(10),' ')}")
        elif t == "question":
            print(f"  Q  : {b['text'][:70]}")
        else:
            print(f"  {t}: {str(b.get('src',''))[:60]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--preview", nargs="*", help="folder names to preview in full")
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(BOOK_DIR, "*", "content.json")))
    targets, n_written = [], 0
    for path in files:
        data = json.load(open(path, encoding="utf-8"))
        folder = os.path.basename(os.path.dirname(path))
        if not needs_rebuild(data):
            continue
        blocks = build_blocks(data)
        targets.append((folder, path, data, blocks))

    if args.preview:
        for folder, path, data, blocks in targets:
            if folder in args.preview:
                preview(folder, blocks)
        return

    print(f"{len(targets)} topics need rebuild "
          f"({'APPLY' if args.apply else 'DRY RUN'})")
    for folder, path, data, blocks in targets:
        body = sum(1 for b in blocks if b["type"] in ("text", "heading"))
        print(f"  {folder:<10} -> {len(blocks):>2} blocks ({body} body)")
        if args.apply:
            shutil.copyfile(path, path + ".blocksbak")
            data["blocks"] = blocks
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            n_written += 1
    if args.apply:
        print(f"\nwrote {n_written} files (backups: *.blocksbak)")
    else:
        print("\n(dry run — use --preview <folders> to inspect, --apply to write)")


if __name__ == "__main__":
    main()
