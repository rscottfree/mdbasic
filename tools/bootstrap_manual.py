#!/usr/bin/env python3
"""One-time scaffolder: mdbasic.pdf -> docs/manual/*.md (the new source of truth).

This holds the old PDF-extraction pipeline that build_docs.py used to run inline
(pdftotext -> split into command/appendix/front-matter sections -> strip running
headers -> reflow to 40 cols). It writes one markdown file per topic with minimal
frontmatter plus the reflowed prose; SYNTAX/EXAMPLE blocks are wrapped in ```text
fences so odd characters pass through the generator verbatim. Scrambled PDF tables
land as prose to be replaced by hand (GFM tables) in the authoring pass.

    tools/bootstrap_manual.py            # writes docs/manual/*.md
    tools/bootstrap_manual.py --force    # overwrite existing files

It is a dev tool, not part of the build. build_docs.py reads the markdown; run
this again only if the PDF changes materially and you want to re-scaffold.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from build_docs import mdbasic_tokens, topic_token, wrap_words, COLS  # shared helpers

PDF = ROOT / "mdbasic.pdf"
MANUAL = ROOT / "docs" / "manual"

FOOTER_RE = re.compile(r"^\s*MDBASIC(\s+\d+)?\s*$")
CONTINUED_RE = re.compile(r"^APPENDIX [A-H](\s+\(continued\))?\s*$", re.I)
ANCHOR = "PURPOSE:"
MAX_HEADER = 30

VERBATIM = re.compile(r"^(SYNTAX|EXAMPLE|EXAMPLES):\s*$")
LABEL = re.compile(r"^[A-Z][A-Z &]*:\s*$")
COL_SEP = re.compile(r" {5,}")
NUM_ENTRY = re.compile(r"^\d+(-\d+)?\s+[A-Z]")

APPENDIX_RE = re.compile(r"^APPENDIX ([A-H])$")
APPENDIX_LETTERS = "ABCDEFGH"
APPENDIX_NAMES = {
    "A": "APPENDIX A: SCREENS", "B": "APPENDIX B: ERRORS", "C": "APPENDIX C: ASCII",
    "D": "APPENDIX D: RS-232", "E": "APPENDIX E: NOTES", "F": "APPENDIX F: TERMS",
    "G": "APPENDIX G: SAMPLES", "H": "APPENDIX H: TIPS",
}
FRONTMATTER = [
    ("PREFACE", "PREFACE"),
    ("INSTALLATION", "INSTALLATION"),
    ("FEATURES & ENHANCEMENTS", "FEATURES & ENHANCE."),
    ("NOMENCLATURE", "NOMENCLATURE"),
    ("USER REFERENCE GUIDE", "USER REF. GUIDE"),
]
ABOUT_NAME = "ABOUT THIS GUIDE"
ABOUT_TEXT = [
    "Besides this quick note, all the text",
    "that follows comes directly from the",
    "MDBASIC manual written by Mark Bowren.",
    "The text has been adapted to fit the",
    "40-column screen of the Commodore 64.",
    "",
    "The reflow to 40 columns means some",
    "detail, tables, and examples could not",
    "be reproduced here. For the complete,",
    "unabridged documentation, look for",
    "Mark's original MDBASIC manual.",
    "",
    "With deep gratitude and respect for his",
    "work, and for keeping the Commodore 64",
    "alive and fun to program.",
    "",
    "Thank you, Mark.",
]


def pdf_text() -> list[str]:
    out = subprocess.run(["pdftotext", "-layout", str(PDF), "-"],
                         check=True, capture_output=True, text=True).stdout
    return out.splitlines()


def guide_bounds(lines: list[str]) -> tuple[int, int]:
    start = 0
    for i, ln in enumerate(lines):
        if "USER REFERENCE GUIDE" in ln.upper():
            start = i
    end = len(lines)
    for i in range(start, len(lines)):
        if re.match(r"^APPENDIX\b", lines[i].strip()):
            end = i
            break
    return start, end


def find_sections(lines: list[str]) -> list[tuple[str, int, int]]:
    start, end = guide_bounds(lines)
    heads: list[tuple[str, int]] = []
    for i in range(start, end):
        t = lines[i]
        if t.lstrip() != t:
            continue
        name = t.strip()
        if not name or FOOTER_RE.match(t) or len(name) > MAX_HEADER:
            continue
        if name.endswith(":"):
            continue
        look = "\n".join(lines[i + 1:i + 6]).upper()
        if ANCHOR not in look:
            continue
        if not heads or i - heads[-1][1] > 8:
            heads.append((name, i))
    return [(n, idx, heads[j + 1][1] if j + 1 < len(heads) else end)
            for j, (n, idx) in enumerate(heads)]


def clean(lines: list[str]) -> list[str]:
    out = [ln.replace('{', '(').replace('}', ')').replace('©', '(c)').rstrip()
           for ln in lines if not FOOTER_RE.match(ln) and not CONTINUED_RE.match(ln)]
    res, blank = [], 0
    for ln in out:
        if not ln.strip():
            blank += 1
            if blank > 1:
                continue
        else:
            blank = 0
        res.append(ln)
    while res and not res[0].strip():
        res.pop(0)
    while res and not res[-1].strip():
        res.pop()
    return res


def reflow(lines: list[str]) -> list[str]:
    out: list[str] = []
    para: list[str] = []
    verbatim = False
    two_col_left: list[str] = []
    two_col_right: list[str] = []
    in_two_col = False

    def flush():
        nonlocal para
        if para:
            out.extend(wrap_words(" ".join(para).split()))
            para = []

    def flush_two_col():
        nonlocal in_two_col
        if two_col_left:
            out.extend(two_col_left)
            out.extend(two_col_right)
            two_col_left.clear()
            two_col_right.clear()
        in_two_col = False

    for ln in lines:
        s = ln.strip()
        if not s:
            flush()
            flush_two_col()
            out.append("")
            continue
        if LABEL.match(s):
            flush()
            flush_two_col()
            verbatim = bool(VERBATIM.match(s))
            out.append(s)
            continue
        if verbatim:
            out.extend([s] if len(ln) <= COLS else wrap_words(ln.split()))
        else:
            _all = list(COL_SEP.finditer(s))
            m = max(_all, key=lambda x: x.end() - x.start()) if _all else None
            if m and m.start() > 0 and m.end() < len(s):
                left = " ".join(s[:m.start()].split())
                right = " ".join(s[m.end():].split())
                if left and right:
                    if not in_two_col:
                        if NUM_ENTRY.match(left) and NUM_ENTRY.match(right):
                            in_two_col = True
                            two_col_left.append(left)
                            two_col_right.append(right)
                            continue
                        if left == right:
                            in_two_col = True
                            two_col_left.append(left)
                            continue
                        if len(left) <= 15:
                            flush()
                            flush_two_col()
                            out.extend(wrap_words((left + " " + right).split()))
                            continue
                    else:
                        two_col_left.append(left)
                        two_col_right.append(right)
                        continue
            if in_two_col:
                flush_two_col()
            if para and (s[0].isdigit() or
                         (len(s) < 58 and para[-1].rstrip().endswith(':'))):
                flush()
            para.append(s)
            if len(s) < 58:
                flush()
    flush()
    flush_two_col()
    return out


def topic_text(lines: list[str], start: int, end: int) -> list[str]:
    return reflow(clean(lines[start:end]))


def frontmatter_topics(lines: list[str]) -> list[tuple[str, int, list[str]]]:
    pos: dict[str, int] = {}
    headers = [h for h, _ in FRONTMATTER]
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s in headers and s not in pos:
            pos[s] = i
    sections = find_sections(lines)
    guide_start = sections[0][1] if sections else len(lines)
    out = []
    for j, (hdr, gridname) in enumerate(FRONTMATTER):
        if hdr not in pos:
            continue
        if hdr == "USER REFERENCE GUIDE":
            end = guide_start
        else:
            nxt = FRONTMATTER[j + 1][0]
            end = pos.get(nxt, len(lines))
        body = topic_text(lines, pos[hdr], end)
        if body and body[0].strip().upper() == hdr.upper():
            body = body[1:]
        out.append((gridname, 0, body))
    return out


def appendix_topics(lines: list[str]) -> list[tuple[str, int, list[str]]]:
    pos: dict[str, int] = {}
    for i, ln in enumerate(lines):
        m = APPENDIX_RE.match(ln.strip())
        if m and m.group(1) not in pos:
            pos[m.group(1)] = i
    end_all = len(lines)
    for i, ln in enumerate(lines):
        if ln.strip().upper() == "BIBLIOGRAPHY":
            end_all = i
            break
    letters = [c for c in APPENDIX_LETTERS if c in pos]
    out = []
    for k, letter in enumerate(letters):
        end = pos[letters[k + 1]] if k + 1 < len(letters) else end_all
        body = topic_text(lines, pos[letter], end)
        if body and body[0].strip().upper() == f"APPENDIX {letter}":
            body = body[1:]
        out.append((APPENDIX_NAMES[letter], 0, body))
    return out


def bibliography_topic(lines: list[str]) -> list[tuple[str, int, list[str]]]:
    start = None
    for i, ln in enumerate(lines):
        if ln.strip().upper() == "BIBLIOGRAPHY":
            start = i
    if start is None:
        return []
    body = topic_text(lines, start, len(lines))
    if body and body[0].strip().upper() == "BIBLIOGRAPHY":
        body = body[1:]
    return [("BIBLIOGRAPHY", 0, body)]


def build_topics(lines: list[str]) -> list[tuple[str, int | None, list[str]]]:
    mdtok = mdbasic_tokens()
    topics: list[tuple[str, int | None, list[str]]] = [(ABOUT_NAME, 0, list(ABOUT_TEXT))]
    topics.extend(frontmatter_topics(lines))
    for name, s, e in find_sections(lines):
        body = topic_text(lines, s, e)
        if body and body[0].strip().upper() == name.strip().upper():
            body = body[1:]
        topics.append((name, topic_token(name, mdtok), body))
    topics.extend(appendix_topics(lines))
    topics.extend(bibliography_topic(lines))
    return topics


# --------------------------------------------------------------------------- #
# Markdown emission
# --------------------------------------------------------------------------- #
def slugify(name: str) -> str:
    n = name.lower()
    n = n.replace("$", "").replace("&", "and")
    n = re.sub(r"[(),]", " ", n)
    n = re.sub(r"[^a-z0-9]+", "-", n)
    return n.strip("-") or "topic"


def fence_body(body: list[str]) -> list[str]:
    """Emit the reflowed prose, wrapping SYNTAX/EXAMPLE blocks in ```text fences
    so their contents (odd chars, leading #, table-ish rows) pass through
    verbatim rather than being reinterpreted as markdown."""
    out: list[str] = []
    i, n = 0, len(body)
    while i < n:
        line = body[i]
        if VERBATIM.match(line.strip()):
            out.append(line)
            i += 1
            block = []
            while i < n and not LABEL.match(body[i].strip()):
                block.append(body[i])
                i += 1
            while block and not block[-1].strip():   # trim trailing blanks
                block.pop()
            if block:
                out.append("```text")
                out.extend(block)
                out.append("```")
            out.append("")
            continue
        out.append(line)
        i += 1
    return out


def write_topic(name: str, token: int | None, body: list[str], order: int,
                force: bool) -> Path:
    fname = f"{order:03d}-{slugify(name)}.md"
    path = MANUAL / fname
    if path.exists() and not force:
        return path
    tokspec = "auto" if token else "none"
    lines = ["---", f"name: {name}", f"order: {order}", f"token: {tokspec}", "---", ""]
    lines += fence_body(body)
    path.write_text("\n".join(lines).rstrip() + "\n")
    return path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="overwrite existing files")
    args = ap.parse_args()

    MANUAL.mkdir(parents=True, exist_ok=True)
    topics = build_topics(pdf_text())
    written = 0
    for order, (name, token, body) in enumerate(topics):
        path = write_topic(name, token, body, order, args.force)
        if path.exists():
            written += 1
    print(f"{len(topics)} topics -> {MANUAL} ({written} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
