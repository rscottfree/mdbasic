#!/usr/bin/env python3
"""Build the MDBASIC docs-pager data from mdbasic.pdf.

Pipeline: pdftotext -> split the User Reference Guide into per-command sections
-> strip running headers/footers -> reflow to 40 columns -> convert to screen
codes -> pack into Magic Desk doc banks (an index bank + a fixed-40-byte line
stream, 204 lines per 8 KB bank). An index keyed by the tokenized keyword byte
maps HELP <topic> to a starting line.

    tools/build_docs.py --list
    tools/build_docs.py --preview SPRITE CIRCLE
    tools/build_docs.py --pack build/docs.bin   # writes the doc-bank image

The packed image is a raw concatenation of 8 KB doc banks (no CRT/CHIP headers);
make_crt.py appends them after the three image banks. See docs-pager design.
"""
from __future__ import annotations

import argparse
import re
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PDF = ROOT / "mdbasic.pdf"
ASM = ROOT / "mdbasic.asm"
COLS = 40
LINES_PER_BANK = 204            # 204*40 = 8160 <= 8192
BANK_SIZE = 0x2000
NAMELEN = 19                    # display name field length (2-col search grid)
IXSTRIDE = 5 + NAMELEN          # index entry: token(1)+start(2)+count(2)+name
NUM_IMAGE_BANKS = 3             # banks 0-2 hold the 16 KB MDBASIC image
INDEX_BANK = NUM_IMAGE_BANKS    # bank 3 = pager code + index
DATA_BANK0 = NUM_IMAGE_BANKS + 1  # banks 4+ = line stream

FOOTER_RE = re.compile(r"^\s*MDBASIC(\s+\d+)?\s*$")
# Page-break artifacts inside the appendices: a bare "APPENDIX F" header repeated
# at the top of each spilled page, or "Appendix G (continued)". Dropped like the
# running footer so they don't litter the reflowed body.
CONTINUED_RE = re.compile(r"^APPENDIX [A-H](\s+\(continued\))?\s*$", re.I)
# A topic header is a short flush-left line immediately followed (within a few
# lines) by PURPOSE: — that anchor is unique to the top of each command block.
# Headers vary: "SPRITE", "HEX$()", "KEY (statement)", "ON ERR", "ON KEY".
ANCHOR = "PURPOSE:"
MAX_HEADER = 30

# Stock CBM BASIC tokens for the commands MDBASIC documents but does not redefine
# in newcmd. Names are matched after stripping $ and () from the header.
STOCK_TOKENS = {
    "CLOSE": 0xA0, "CLR": 0x9C, "NEW": 0xA2, "POKE": 0x97, "RESTORE": 0x8C,
    "RETURN": 0x8E, "RUN": 0x8A, "SAVE": 0x94, "STOP": 0x90, "SYS": 0x9E,
    "WAIT": 0x92,
}


def pdf_text() -> list[str]:
    out = subprocess.run(["pdftotext", "-layout", str(PDF), "-"],
                         check=True, capture_output=True, text=True).stdout
    return out.splitlines()


def mdbasic_tokens() -> dict[str, int]:
    """Parse newcmd from mdbasic.asm: .shift entries from $CB upward."""
    tok = 0xCB
    out: dict[str, int] = {}
    in_block = False
    for ln in ASM.read_text().splitlines():
        s = ln.strip()
        if s == "newcmd":
            in_block = True
            continue
        if not in_block:
            continue
        if s.startswith(".byte 0"):
            break
        m = re.search(r'\.shift\s+"([^"]+)"', s)
        if m:
            out[m.group(1).upper()] = tok
            tok += 1
    return out


def topic_token(name: str, mdtok: dict[str, int]) -> int | None:
    """Resolve a header like 'KEY (statement)' or 'ON ERR' to a keyword token."""
    # Words in the header, keeping a trailing $ (HEX$) but dropping () and punct.
    words = re.findall(r"[A-Z][A-Z0-9]*\$?", name.upper())
    # Prefer the first word that names a keyword; for 'ON ERR'/'ON KEY' the
    # leading ON is itself a token, so skip it when a later word also resolves.
    cands = words[1:] + words if words and words[0] == "ON" else words
    for w in cands:
        for cand in (w, w.rstrip("$")):     # TRIM$ folds to the TRIM token
            if cand in mdtok:
                return mdtok[cand]
            if cand in STOCK_TOKENS:
                return STOCK_TOKENS[cand]
    return None


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
        if t.lstrip() != t:             # must be flush-left
            continue
        name = t.strip()
        if not name or FOOTER_RE.match(t) or len(name) > MAX_HEADER:
            continue
        if name.endswith(":"):          # PURPOSE:/SYNTAX:/DESCRIPTION: etc.
            continue
        # PURPOSE: appears once, right below the header of each command block.
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


def wrap_words(words: list[str]) -> list[str]:
    out, cur = [], ""
    for w in words:
        cand = (cur + " " + w) if cur else w
        if len(cand) > COLS and cur:
            out.append(cur)
            cur = w
        else:
            cur = cand
    if cur:
        out.append(cur)
    return out or [""]


VERBATIM = re.compile(r"^(SYNTAX|EXAMPLE|EXAMPLES):\s*$")
LABEL = re.compile(r"^[A-Z][A-Z &]*:\s*$")
# 5+ consecutive spaces inside a stripped line signals a PDF two-column layout.
COL_SEP = re.compile(r" {5,}")
# A numbered list entry: a code (e.g. 14 or 37-127) followed by an UPPERCASE
# word. When BOTH halves of a two-column split match, the columns are two halves
# of one numbered list (e.g. the Appendix B error table, 0-18 | 19-37) that must
# be flattened one-per-line, NOT joined into "code DESC  code DESC" rows. The
# uppercase-word requirement excludes value tables like ENVELOPE "0  0.002 secs".
NUM_ENTRY = re.compile(r"^\d+(-\d+)?\s+[A-Z]")


def reflow(lines: list[str]) -> list[str]:
    out: list[str] = []
    para: list[str] = []
    verbatim = False
    two_col_left: list[str] = []   # accumulated left-column entries
    two_col_right: list[str] = []  # accumulated right-column entries
    in_two_col = False             # True only after seeing a twin header (left == right)

    def flush():
        nonlocal para
        if para:
            out.extend(wrap_words(" ".join(para).split()))
            para = []

    def flush_two_col():
        """Emit a two-column block as left-column lines then right-column lines."""
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
            # Verbatim mode persists across blank lines; only a non-verbatim
            # LABEL (DESCRIPTION:, NOTE:, etc.) resets it.
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
            # Detect a PDF two-column layout: 5+ spaces between two non-empty halves.
            # Use the widest gap to split — some tables have 5+ spaces within
            # a half (e.g. ENVELOPE "0      0.002 seconds") so the first match
            # can fall inside the left half rather than between the two halves.
            _all = list(COL_SEP.finditer(s))
            m = max(_all, key=lambda x: x.end() - x.start()) if _all else None
            if m and m.start() > 0 and m.end() < len(s):
                left = " ".join(s[:m.start()].split())
                right = " ".join(s[m.end():].split())
                if left and right:
                    if not in_two_col:
                        # Two halves of a numbered list (the error table): accumulate
                        # as a two-column block so it flattens to the left column then
                        # the right column, one entry per line and in order.
                        if NUM_ENTRY.match(left) and NUM_ENTRY.match(right):
                            in_two_col = True
                            two_col_left.append(left)
                            two_col_right.append(right)
                            continue
                        # Only enter twin-table mode when the header repeats
                        # itself (e.g. "VALUE COLOR  VALUE COLOR"). A multi-
                        # column table with distinct headers falls through to
                        # normal paragraph handling instead.
                        if left == right:
                            in_two_col = True
                            two_col_left.append(left)  # header added once
                            continue
                        # A short left side (≤15 chars) signals a table row
                        # (e.g. "c1", "n/a, Restricted", "Bitmap Graphics"):
                        # emit left + right as one wrapped line immediately.
                        if len(left) <= 15:
                            flush()
                            flush_two_col()
                            out.extend(wrap_words((left + " " + right).split()))
                            continue
                        # else: fall through to normal processing below
                    else:
                        # Inside a twin-table block: accumulate both halves.
                        two_col_left.append(left)
                        two_col_right.append(right)
                        continue
            # Not a two-column line (or not in twin-table mode) — flush any
            # accumulated two-col block first.
            if in_two_col:
                flush_two_col()
            # Flush before digit-starting lines regardless of length (long
            # numbered table rows like INF 10-70), and before any short line
            # that follows a colon-ended paragraph introduction.
            if para and (s[0].isdigit() or
                         (len(s) < 58 and para[-1].rstrip().endswith(':'))):
                flush()
            para.append(s)
            # Short source lines are structural (table rows, list items, the
            # tail of a sentence): end the paragraph so they stay one-per-row.
            if len(s) < 58:
                flush()
    flush()
    flush_two_col()
    return out


def topic_text(lines: list[str], start: int, end: int) -> list[str]:
    return reflow(clean(lines[start:end]))


def ascii_to_screen(c: str) -> int:
    """ASCII -> C64 screen code (lowercase/uppercase charset)."""
    o = ord(c)
    if 0x20 <= o <= 0x3F:
        return o
    if o == 0x40:
        return 0x00
    if 0x41 <= o <= 0x5A:
        return o                 # uppercase A-Z -> screen codes $41-$5A (display uppercase)
    if 0x5B <= o <= 0x5F:
        return o - 0x40
    if o == 0x7C:                # | -> shifted-B
        return 0x42
    if 0x61 <= o <= 0x7A:        # lowercase a-z -> screen codes $01-$1A (display lowercase)
        return o - 0x60
    return 0x20                  # anything else -> space


def display_name(name: str) -> str:
    """Produce a NAMELEN-char uppercase display name, space-padded, as a plain string.

    The 2-column search grid is wide enough (19 chars) to keep the disambiguating
    qualifiers, just abbreviated so the long ones fit:
      KEY (statement)          -> KEY (STMT)
      KEY and KEY$ (variables) -> KEY/KEY$ (VARS)
      TIME and TIME$           -> TIME/TIME$
      VALB(), VALH(), VALO()   -> VALB/VALH/VALO
    Single-function headers keep their "()" marker (HEX$() -> HEX$()).
    """
    n = name.upper().strip()
    n = n.replace("(STATEMENT)", "(STMT)")    # abbreviate the (kind) qualifiers
    n = n.replace("(VARIABLES)", "(VARS)")
    n = n.replace("(VARIABLE)", "(VAR)")
    n = re.sub(r"\s+AND\s+", "/", n)          # "KEY and KEY$" -> "KEY/KEY$"
    if "," in n:                              # "VALB(), VALH(), VALO()" -> "VALB/VALH/VALO"
        n = "/".join(p.strip().replace("()", "") for p in n.split(","))
    n = re.sub(r"\s+", " ", n).strip()
    return n[:NAMELEN].ljust(NAMELEN)


def line_to_record(text: str) -> bytes:
    text = text[:COLS]
    rec = bytes(ascii_to_screen(c) for c in text)
    return rec + b"\x20" * (COLS - len(rec))


RVS_SPACE = 0x20 | 0x80         # reverse-video space, fills the title banner


def topic_header(name: str) -> list[bytes]:
    """Two lead-in records that delimit a topic: a blank separator line and the
    topic title as a full-width reverse-video banner."""
    blank = b"\x20" * COLS
    title = (" " + name).upper()[:COLS]
    banner = bytes(ascii_to_screen(c) | 0x80 for c in title)
    banner += bytes([RVS_SPACE]) * (COLS - len(banner))
    return [blank, banner]


# The appendices are reference tables / prose (not PURPOSE-anchored command
# blocks), so find_sections cannot pick them up — they are extracted separately
# and given a short (<=19-char) grid/banner name. Each appendix runs from its
# "APPENDIX x" header to the next appendix (H runs to BIBLIOGRAPHY / end). The
# musical-notes table in E is an image and is not extractable, so E carries only
# its descriptive prose. The BIBLIOGRAPHY page is not included.
APPENDIX_RE = re.compile(r"^APPENDIX ([A-H])$")
APPENDIX_LETTERS = "ABCDEFGH"
APPENDIX_NAMES = {
    "A": "APPENDIX A: SCREENS",
    "B": "APPENDIX B: ERRORS",
    "C": "APPENDIX C: ASCII",
    "D": "APPENDIX D: RS-232",
    "E": "APPENDIX E: NOTES",
    "F": "APPENDIX F: TERMS",
    "G": "APPENDIX G: SAMPLES",
    "H": "APPENDIX H: TIPS",
}

# Front matter (Preface .. User Reference Guide intro), extracted as topics that
# lead the guide. Each entry is (exact PDF header, <=19-char grid/banner name);
# the real header line is stripped from the body so it is not shown twice.
FRONTMATTER = [
    ("PREFACE", "PREFACE"),
    ("INSTALLATION", "INSTALLATION"),
    ("FEATURES & ENHANCEMENTS", "FEATURES & ENHANCE."),
    ("NOMENCLATURE", "NOMENCLATURE"),
    ("USER REFERENCE GUIDE", "USER REF. GUIDE"),
]

# This page is the ONLY content not extracted from the PDF — a note about the
# on-screen guide itself. It makes clear that everything else is Mark Bowren's
# work, merely reflowed to 40 columns, and points the reader at the full manual.
# Lines are pre-wrapped to <=40 columns.
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


def frontmatter_topics(lines: list[str]) -> list[tuple[str, int, list[str]]]:
    """Extract the Preface .. User Reference Guide intro (token 0; name/start nav)."""
    pos: dict[str, int] = {}
    headers = [h for h, _ in FRONTMATTER]
    for i, ln in enumerate(lines):
        s = ln.strip()                       # TOC lines carry trailing dots, so an
        if s in headers and s not in pos:    # exact match only hits the body header
            pos[s] = i
    sections = find_sections(lines)
    guide_start = sections[0][1] if sections else len(lines)
    out = []
    for j, (hdr, gridname) in enumerate(FRONTMATTER):
        if hdr not in pos:
            continue
        # The URG intro ends where the first command section (AUTO) begins; the
        # others end at the next front-matter header.
        if hdr == "USER REFERENCE GUIDE":
            end = guide_start
        else:
            nxt = FRONTMATTER[j + 1][0]
            end = pos.get(nxt, len(lines))
        body = topic_text(lines, pos[hdr], end)
        if body and body[0].strip().upper() == hdr.upper():
            body = body[1:]                  # drop the header (shown as a banner)
        out.append((gridname, 0, body))
    return out


def appendix_topics(lines: list[str]) -> list[tuple[str, int, list[str]]]:
    """Extract appendices A-H as topics (token 0; nav is by name/start, not token)."""
    pos: dict[str, int] = {}
    for i, ln in enumerate(lines):
        m = APPENDIX_RE.match(ln.strip())
        if m and m.group(1) not in pos:
            pos[m.group(1)] = i
    # The last appendix (H) ends at BIBLIOGRAPHY; its TOC line has trailing dots,
    # so the bare-word match lands on the body header only.
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
        # Drop the leading "APPENDIX X" line — the pager shows the name as a banner.
        if body and body[0].strip().upper() == f"APPENDIX {letter}":
            body = body[1:]
        out.append((APPENDIX_NAMES[letter], 0, body))
    return out


def bibliography_topic(lines: list[str]) -> list[tuple[str, int, list[str]]]:
    """Extract the closing BIBLIOGRAPHY as the final topic (token 0)."""
    start = None
    for i, ln in enumerate(lines):
        if ln.strip().upper() == "BIBLIOGRAPHY":   # body header, not the dotted TOC
            start = i
    if start is None:
        return []
    body = topic_text(lines, start, len(lines))
    if body and body[0].strip().upper() == "BIBLIOGRAPHY":
        body = body[1:]
    return [("BIBLIOGRAPHY", 0, body)]


def build_topics(lines: list[str]):
    """Return (topics, mdtok) where topics = [(name, token, [text lines])]."""
    mdtok = mdbasic_tokens()
    # The about page leads the list so it is the default selection on open, then
    # the front matter (Preface .. User Reference Guide) before the command list.
    topics = [(ABOUT_NAME, 0, list(ABOUT_TEXT))]
    topics.extend(frontmatter_topics(lines))
    for name, s, e in find_sections(lines):
        body = topic_text(lines, s, e)
        # The body's first line is the section header (the topic name); the pager
        # now shows it as a reverse-video banner, so drop the duplicate.
        if body and body[0].strip().upper() == name.strip().upper():
            body = body[1:]
        tok = topic_token(name, mdtok)
        topics.append((name, tok, body))
    topics.extend(appendix_topics(lines))
    topics.extend(bibliography_topic(lines))
    return topics, mdtok


def build_index_and_data() -> tuple[bytes, bytes, int, int]:
    """Return (index_blob, data_blob, total_lines, data_banks).

    index_blob: 'MDIX' magic, u16 topic_count, u16 total_lines, then 5-byte
                entries {token, start_line(u16), line_count(u16)}. Goes at a
                fixed offset in cart bank 3, alongside the pager code.
    data_blob:  cart banks 4+ : 204 fixed 40-byte line records per 8 KB bank,
                each bank padded to 8 KB so a line never straddles a bank.
    The pager maps global line L -> Magic Desk bank DATA_BANK0 + L//204,
    addr $8000 + (L%204)*40.
    """
    lines = pdf_text()
    topics, _ = build_topics(lines)

    records: list[bytes] = []
    index: list[tuple[int, int, int, str]] = []  # token, start, count, name
    for name, tok, body in topics:
        blank, banner = topic_header(name)
        start = len(records)                 # jump/nav target = title banner
        records.append(banner)
        records.extend(line_to_record(t) for t in body)
        index.append((tok if tok is not None else 0, start, len(records) - start, name))
        records.append(blank)                # end-of-topic separator (not in range)

    total_lines = len(records)
    data_banks = (total_lines + LINES_PER_BANK - 1) // LINES_PER_BANK

    idx = bytearray(b"MDIX")
    idx += struct.pack("<HH", len(index), total_lines)
    for tok, start, count, name in index:
        dn = display_name(name)
        name_bytes = bytes(ascii_to_screen(c) for c in dn)
        idx += struct.pack("<BHH", tok & 0xFF, start, count) + name_bytes

    data = bytearray()
    for b in range(data_banks):
        chunk = b"".join(records[b * LINES_PER_BANK:(b + 1) * LINES_PER_BANK])
        chunk += b"\x20" * (LINES_PER_BANK * COLS - len(chunk))   # pad lines
        chunk += b"\x00" * (BANK_SIZE - len(chunk))               # pad bank
        data += chunk
    return bytes(idx), bytes(data), total_lines, data_banks


def pack(out_path: Path) -> None:
    idx, data, total_lines, data_banks = build_index_and_data()
    stem = out_path.with_suffix("")
    idx_path = stem.with_suffix(".idx")
    dat_path = stem.with_suffix(".dat")
    idx_path.write_bytes(idx)
    dat_path.write_bytes(data)
    print(f"wrote {idx_path}: {len(idx)} bytes index "
          f"(placed in cart bank {INDEX_BANK} with the pager code)")
    print(f"wrote {dat_path}: {len(data)} bytes = {data_banks} data banks "
          f"(cart banks {DATA_BANK0}..{DATA_BANK0 + data_banks - 1})")
    print(f"topics: {len(idx[8:]) // IXSTRIDE}   total lines: {total_lines}")
    if len(idx) > 0xc00:
        print(f"WARNING: index {len(idx)} bytes exceeds the 3 KB reserved at "
              f"$8c00-$97ff in bank {INDEX_BANK} (RESTORE handler at $9800)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--preview", nargs="*", default=None)
    ap.add_argument("--pack", metavar="OUT", default=None)
    args = ap.parse_args()

    if args.pack:
        pack(Path(args.pack))
        return 0

    lines = pdf_text()
    topics, mdtok = build_topics(lines)

    if args.list or args.preview is None:
        print(f"{len(topics)} topics:")
        for name, tok, body in topics:
            ts = f"${tok:02x}" if tok is not None else " - "
            print(f"  {name:<10} {ts}  {len(body):3d} lines")
        return 0

    want = {w.upper() for w in args.preview}
    for name, tok, body in topics:
        if want and name.replace("()", "").upper() not in want \
           and name.upper() not in want:
            continue
        print(f"===== {name}  ({len(body)} lines) " + "=" * (COLS - len(name) - 18))
        print("\n".join("|" + b for b in body))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
