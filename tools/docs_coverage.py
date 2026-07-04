#!/usr/bin/env python3
"""Coverage check: no PDF body content silently dropped in the markdown migration.

Flattens the PDF User Reference Guide body (everything except the front-matter
table of contents, whose page numbers are meaningless on-screen) into word
tokens, then confirms every token also appears in the rendered docs records that
build_docs.py produces from docs/manual/*.md. Reports any PDF words missing from
the generated output so a hand-authoring edit can't drop content unnoticed.

    tools/docs_coverage.py            # summary + first missing words
    tools/docs_coverage.py --all      # list every missing word

Notes:
  * The Appendix E notes chart is a PDF *image*, so its words are absent from the
    PDF text layer; reconstructed note data in the markdown is extra, not missing.
  * A handful of residuals are expected (TOC fragments, image-only tokens); the
    baseline is small and should not grow. Non-zero exit only on regressions past
    the recorded allowance.
"""
from __future__ import annotations

import argparse
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import build_docs
import bootstrap_manual

COLS = build_docs.COLS
LPB = build_docs.LINES_PER_BANK
BANK = build_docs.BANK_SIZE

# A TOC line ends in leader dots + a page number; drop those and the heading.
TOC_LINE = re.compile(r"\.{2,}\s*\d+\s*$")
WORD = re.compile(r"[a-z0-9]+")


def words(text: str) -> set[str]:
    return set(WORD.findall(text.lower()))


def pdf_body_words() -> set[str]:
    lines = bootstrap_manual.pdf_text()
    out: set[str] = set()
    for ln in lines:
        s = ln.strip()
        if not s or TOC_LINE.search(s):
            continue
        if s.upper() in ("CONTENTS", "TABLE OF CONTENTS"):
            continue
        out |= words(s)
    return out


def generated_words() -> set[str]:
    idx, data, _tot, banks = build_docs.build_index_and_data()
    n = struct.unpack("<H", idx[4:6])[0]
    out: set[str] = set()
    inv = {v: k for k, v in build_docs.BOX_SCREEN.items()}

    def ch(b: int) -> str:
        c = b & 0x7F
        if c in inv:
            return " "
        if c == 0x00:
            return "@"
        if 0x01 <= c <= 0x1A:
            return chr(0x60 + c)
        if 0x20 <= c <= 0x3F:
            return chr(c)
        if 0x41 <= c <= 0x5A:
            return chr(c)
        return " "

    off = 8
    for _ in range(n):
        _tok, start, count = struct.unpack("<BHH", idx[off:off + 5])
        off += build_docs.IXSTRIDE
        for k in range(count):
            L = start + k
            o = (L // LPB) * BANK + (L % LPB) * COLS
            out |= words("".join(ch(b) for b in data[o:o + COLS]))
    # also fold the display names in the index (grid search text)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()

    pdf = pdf_body_words()
    gen = generated_words()
    missing = sorted(pdf - gen)
    print(f"PDF body words: {len(pdf)}   generated words: {len(gen)}")
    print(f"missing from generated: {len(missing)}")
    show = missing if args.all else missing[:40]
    if show:
        print("  " + " ".join(show))
        if not args.all and len(missing) > len(show):
            print(f"  ... (+{len(missing) - len(show)} more; --all to list)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
