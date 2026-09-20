"""
Remove the duplicated leading "Key Concept" label from Key Concept sidebox
components.

Key Concept sideboxes are blocks of type "sidebox" whose title is "Key Concept".
Their `text` field frequently repeats the label, e.g.:

    "Key ConceptTruth tables"
    "<p style=\"...\">Key ConceptPolling and Interrupt Handling</p>"

which renders as "Key ConceptTruth tables" under the "KEY CONCEPT" heading.
This script strips a single leading "Key Concept" from the text (after any
opening HTML tags / whitespace), leaving the real definition behind.

Usage:
    python scripts/dedupe_key_concept.py           # dry run, shows changes
    python scripts/dedupe_key_concept.py --apply    # write changes (.bak backups)
"""
import json
import glob
import os
import re
import shutil
import sys

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

# Leading whitespace / opening HTML tags, then "Key Concept" (any spacing/case).
LEADING_KEY_CONCEPT = re.compile(
    r'^(\s*(?:<[^>]+>\s*)*)key\s*concept\s*',
    re.IGNORECASE,
)


def strip_label(text):
    """Return text with a single leading 'Key Concept' removed, or None if no change."""
    new = LEADING_KEY_CONCEPT.sub(r'\1', text, count=1)
    return new if new != text else None


def is_key_concept_block(block):
    return (
        isinstance(block, dict)
        and block.get("type") == "sidebox"
        and str(block.get("title", "")).strip().lower() == "key concept"
    )


def main():
    apply = "--apply" in sys.argv
    files = glob.glob(os.path.join(DATA_DIR, "**", "content.json"), recursive=True)

    changed_files = 0
    changed_blocks = 0

    for path in files:
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except (json.JSONDecodeError, OSError):
            continue

        blocks = data.get("blocks") if isinstance(data, dict) else data
        if not isinstance(blocks, list):
            continue

        file_touched = False
        for block in blocks:
            if not is_key_concept_block(block):
                continue
            text = block.get("text")
            if not isinstance(text, str):
                continue
            new_text = strip_label(text)
            if new_text is None:
                continue
            rel = os.path.relpath(path, DATA_DIR)
            print(f"[{rel}]")
            print(f"  - {text!r}")
            print(f"  + {new_text!r}")
            block["text"] = new_text
            file_touched = True
            changed_blocks += 1

        if file_touched:
            changed_files += 1
            if apply:
                shutil.copy2(path, path + ".bak")
                with open(path, "w", encoding="utf-8") as fh:
                    json.dump(data, fh, ensure_ascii=False, indent=1)

    mode = "APPLIED" if apply else "DRY RUN (no files written)"
    print(f"\n{mode}: {changed_blocks} block(s) in {changed_files} file(s).")
    if not apply and changed_blocks:
        print("Re-run with --apply to write changes (.bak backups will be made).")


if __name__ == "__main__":
    main()
