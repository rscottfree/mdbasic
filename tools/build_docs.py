#!/usr/bin/env python3
"""Build the MDBASIC docs-pager data from the markdown manual (docs/manual/*.md).

Source of truth is one markdown file per topic under docs/manual/. This tool
renders them to 40-column screen-code line records and packs them into Magic Desk
doc banks exactly as before, so make_crt.py / build_disk.sh / docs_pager.asm are
untouched. (The one-time PDF -> markdown scaffolder lives in bootstrap_manual.py.)

    tools/build_docs.py --list
    tools/build_docs.py --preview SCREEN COLOR
    tools/build_docs.py --pack build/docs.bin   # writes .idx + .dat

Markdown body grammar the renderer understands:
  * blank line               -> blank record
  * ```fence``` block        -> verbatim (wrapped only if a line exceeds 40 cols)
  * GFM table (| a | b | + |---|)  -> table engine (box grid / cards / sections)
  * <!-- table: mode=... -->       -> directive selecting a wide-table layout
  * <!-- ... -->             -> comment, dropped (may span lines)
  * any other line           -> passthrough, word-wrapped only if it exceeds 40 cols

The packed image is a raw concatenation of 8 KB doc banks (no CRT/CHIP headers);
make_crt.py appends them after the three image banks. See docs-pager design.
"""
from __future__ import annotations

import argparse
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASM = ROOT / "mdbasic.asm"
MANUAL = ROOT / "docs" / "manual"
COLS = 40
LINES_PER_BANK = 204            # 204*40 = 8160 <= 8192
BANK_SIZE = 0x2000
NAMELEN = 19                    # display name field length (2-col search grid)
IXSTRIDE = 5 + NAMELEN          # index entry: token(1)+start(2)+count(2)+name
NUM_IMAGE_BANKS = 3             # banks 0-2 hold the 16 KB MDBASIC image
INDEX_BANK = NUM_IMAGE_BANKS    # bank 3 = pager code + index
DATA_BANK0 = NUM_IMAGE_BANKS + 1  # banks 4+ = line stream

# Stock CBM BASIC tokens for the commands MDBASIC documents but does not redefine
# in newcmd. Names are matched after stripping $ and () from the header.
STOCK_TOKENS = {
    "CLOSE": 0xA0, "CLR": 0x9C, "NEW": 0xA2, "POKE": 0x97, "RESTORE": 0x8C,
    "RETURN": 0x8E, "RUN": 0x8A, "SAVE": 0x94, "STOP": 0x90, "SYS": 0x9E,
    "WAIT": 0x92,
}

# PETSCII box-drawing glyphs -> C64 screen codes (lowercase charset). Verified in
# VICE by tools/glyph_check.py; the pager embeds these directly, no code change.
BOX_SCREEN = {
    "│": 0x5D,  # |  vertical
    "─": 0x40,  # -  horizontal
    "┌": 0x70,  # ,- top-left
    "┐": 0x6E,  # -. top-right
    "└": 0x6D,  # '- bottom-left
    "┘": 0x7D,  # -' bottom-right
    "├": 0x6B,  # |- left tee
    "┤": 0x73,  # -| right tee
    "┬": 0x72,  # T  top tee
    "┴": 0x71,  # bottom tee
    "┼": 0x5B,  # +  cross
}
V, H = "│", "─"
TL, TR, BL, BR = "┌", "┐", "└", "┘"
LT, RT, TT, BT, XX = "├", "┤", "┬", "┴", "┼"


# --------------------------------------------------------------------------- #
# Token resolution (unchanged: parse newcmd from the assembly source)
# --------------------------------------------------------------------------- #
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
    words = re.findall(r"[A-Z][A-Z0-9]*\$?", name.upper())
    cands = words[1:] + words if words and words[0] == "ON" else words
    for w in cands:
        for cand in (w, w.rstrip("$")):
            if cand in mdtok:
                return mdtok[cand]
            if cand in STOCK_TOKENS:
                return STOCK_TOKENS[cand]
    return None


# --------------------------------------------------------------------------- #
# Screen-code conversion
# --------------------------------------------------------------------------- #
def ascii_to_screen(c: str) -> int:
    """ASCII (or PETSCII box glyph) -> C64 screen code (lowercase charset)."""
    if c in BOX_SCREEN:
        return BOX_SCREEN[c]
    o = ord(c)
    if 0x20 <= o <= 0x3F:
        return o
    if o == 0x40:
        return 0x00
    if 0x41 <= o <= 0x5A:
        return o                 # uppercase A-Z -> screen codes $41-$5A
    if 0x5B <= o <= 0x5F:
        return o - 0x40
    if o == 0x7C:                # | -> box vertical bar (renders as a pipe in the
        return 0x5D              #    lowercase charset; screen code $42 shows as "B")
    if 0x61 <= o <= 0x7A:        # lowercase a-z -> screen codes $01-$1A
        return o - 0x60
    return 0x20                  # anything else -> space


def line_to_record(text: str) -> bytes:
    text = text[:COLS]
    rec = bytes(ascii_to_screen(c) for c in text)
    return rec + b"\x20" * (COLS - len(rec))


RVS_SPACE = 0x20 | 0x80         # reverse-video space, fills a banner row


def rvs_record(text: str) -> bytes:
    """A full-width reverse-video record (used for card sub-banners)."""
    t = (" " + text)[:COLS]
    rec = bytes(ascii_to_screen(c) | 0x80 for c in t)
    return rec + bytes([RVS_SPACE]) * (COLS - len(rec))


def to_record(item: str | bytes) -> bytes:
    """A rendered body item is either display text or a pre-built record (bytes)."""
    if isinstance(item, bytes):
        return (item + b"\x20" * COLS)[:COLS]
    return line_to_record(item)


def display_name(name: str) -> str:
    """Produce a NAMELEN-char uppercase display name, space-padded."""
    n = name.upper().strip()
    n = n.replace("(STATEMENT)", "(STMT)")
    n = n.replace("(VARIABLES)", "(VARS)")
    n = n.replace("(VARIABLE)", "(VAR)")
    n = re.sub(r"\s+AND\s+", "/", n)
    if "," in n:
        n = "/".join(p.strip().replace("()", "") for p in n.split(","))
    n = re.sub(r"\s+", " ", n).strip()
    return n[:NAMELEN].ljust(NAMELEN)


def topic_header(name: str) -> tuple[bytes, bytes]:
    """A blank separator record and a full-width reverse-video title banner."""
    blank = b"\x20" * COLS
    title = (" " + name).upper()[:COLS]
    banner = bytes(ascii_to_screen(c) | 0x80 for c in title)
    banner += bytes([RVS_SPACE]) * (COLS - len(banner))
    return blank, banner


def wrap_words(words: list[str], width: int = COLS) -> list[str]:
    out, cur = [], ""
    for w in words:
        cand = (cur + " " + w) if cur else w
        if len(cand) > width and cur:
            out.append(cur)
            cur = w
        else:
            cur = cand
    if cur:
        out.append(cur)
    return out or [""]


def label_value(label: str, value: str) -> list[str]:
    """A wide-table 'LABEL: value' row, word-wrapped to 40 cols."""
    return wrap_words(f"{label}: {value}".split())


# --------------------------------------------------------------------------- #
# Table engine
# --------------------------------------------------------------------------- #
def _cells(line: str) -> list[str]:
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|") and not s.endswith("\\|"):
        s = s[:-1]
    # split on unescaped pipes only, then unescape literal \| inside cells
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", s)]


def parse_gfm(tbl: list[str]) -> tuple[list[str], list[list[str]]]:
    header = _cells(tbl[0])
    ncols = len(header)
    rows = []
    for ln in tbl[2:]:                        # tbl[1] is the |---| separator
        c = _cells(ln)
        c += [""] * (ncols - len(c))
        rows.append(c[:ncols])
    return header, rows


def _col(cells_by_row: list[list[str]], i: int) -> list[str]:
    return [r[i] if i < len(r) else "" for r in cells_by_row]


def _wrap_cell(text: str, width: int) -> list[str]:
    return wrap_words(text.split(), width) if text else [""]


def box_grid(header: list[str], rows: list[list[str]]) -> list[str] | None:
    """Render a full PETSCII box grid if it fits in 40 cols; else None (too wide).

    Column widths default to the widest cell, then shrink the roomiest columns
    (never below their longest single word) until the grid fits; cells wrap on
    whitespace only. Only a header rule separates head from body (no per-row
    rules), matching the pager's compact grid style."""
    ncols = len(header)
    allr = [header] + rows
    cols = [_col(allr, i) for i in range(ncols)]
    natw = [max((len(cell) for cell in col), default=1) or 1 for col in cols]
    minw = [max((max((len(w) for w in cell.split()), default=0) for cell in col),
                default=1) or 1 for col in cols]

    def total(ws: list[int]) -> int:
        return sum(ws) + ncols + 1            # borders(ncols+1), no cell padding

    ws = natw[:]
    while total(ws) > COLS:
        slack = [(ws[i] - minw[i], i) for i in range(ncols)]
        best, idx = max(slack)
        if best <= 0:
            return None                        # cannot fit even wrapped -> wide mode
        ws[idx] -= 1

    def hrule(left: str, mid: str, right: str) -> str:
        return left + mid.join(H * w for w in ws) + right

    def datarow(cells: list[str]) -> list[str]:
        wrapped = [_wrap_cell(cells[i] if i < len(cells) else "", ws[i])
                   for i in range(ncols)]
        height = max(len(c) for c in wrapped)
        out = []
        for r in range(height):
            parts = []
            for i in range(ncols):
                seg = wrapped[i][r] if r < len(wrapped[i]) else ""
                parts.append(seg.ljust(ws[i]))
            out.append(V + V.join(parts) + V)
        return out

    lines = [hrule(TL, TT, TR)]
    lines += datarow(header)
    lines.append(hrule(LT, XX, RT))
    for row in rows:
        lines += datarow(row)
    lines.append(hrule(BL, BT, BR))
    return lines


def sections_mode(header: list[str], rows: list[list[str]]) -> list[str | bytes]:
    """Wide fallback: each row -> a normal (non-reversed) sub-header from the first
    column, a PETSCII dash then a space, the title, a trailing space, and dashes out
    to the 40th column, then 'HEADER: value' lines for the remaining non-empty cells.
    A pure 2-column table (one value column) drops the redundant label and emits the
    value as plain full-width text, since the sub-header already names the entry."""
    single = len(header) == 2
    out: list[str | bytes] = []
    for row in rows:
        head = H + " " + row[0] + " "
        head += H * (COLS - len(head))
        out.append(head)
        for h, v in zip(header[1:], row[1:]):
            if v.strip():
                out.extend(wrap_words(v.split()) if single else label_value(h, v))
    return out


def cards_mode(header: list[str], rows: list[list[str]],
               key: list[str], span: list[str], pack: int | None) -> list[str | bytes]:
    """Wide layout: pack the small `key` columns together compactly (LABEL: value
    pairs, `pack` per line max), then emit each wide `span` column as a full-width
    'HEADER: value' wrapped row beneath. Empty cells are skipped."""
    idx = {h: i for i, h in enumerate(header)}
    key_i = [idx[k] for k in key if k in idx]
    span_i = [idx[s] for s in span if s in idx]
    # Any column named in neither key nor span still shows, as a span row.
    named = set(key_i) | set(span_i)
    span_i += [i for i in range(len(header)) if i not in named]

    out: list[str | bytes] = []
    for r, row in enumerate(rows):
        if r:
            out.append("")
        pairs = [f"{header[i]}: {row[i]}" for i in key_i
                 if i < len(row) and row[i].strip()]
        cur: list[str] = []
        for p in pairs:
            cand = cur + [p]
            joined = "  ".join(cand)
            if (pack and len(cand) > pack) or (len(joined) > COLS and cur):
                out.append("  ".join(cur))
                cur = [p]
            else:
                cur = cand
        if cur:
            out.append("  ".join(cur))
        for i in span_i:
            if i < len(row) and row[i].strip():
                out.extend(label_value(header[i], row[i]))
    return out


DIRECTIVE_RE = re.compile(r"<!--\s*table:\s*(.*?)\s*-->")


def parse_directive(text: str) -> dict[str, object]:
    m = DIRECTIVE_RE.search(text)
    opts: dict[str, object] = {}
    if not m:
        return opts
    for tok in m.group(1).split():
        if "=" in tok:
            k, v = tok.split("=", 1)
            opts[k] = int(v) if k == "pack" and v.isdigit() else v
        else:
            opts[tok] = True
    return opts


def render_table(tbl: list[str], directive: dict[str, object] | None) -> list[str | bytes]:
    header, rows = parse_gfm(tbl)
    directive = directive or {}
    mode = directive.get("mode")
    if mode is None:
        grid = box_grid(header, rows)
        if grid is not None:
            return list(grid)
        mode = "sections"                      # too wide, no directive -> sections
    if mode == "grid":
        grid = box_grid(header, rows)
        return list(grid) if grid is not None else sections_mode(header, rows)
    if mode == "cards":
        key = str(directive.get("key", "")).split(",") if directive.get("key") else []
        span = str(directive.get("span", "")).split(",") if directive.get("span") else []
        key = [k for k in key if k]
        span = [s for s in span if s]
        pack = directive.get("pack")
        return cards_mode(header, rows, key, span, pack if isinstance(pack, int) else None)
    return sections_mode(header, rows)


# --------------------------------------------------------------------------- #
# Markdown parsing
# --------------------------------------------------------------------------- #
LABEL = re.compile(r"^[A-Z][A-Z &/]*:\s*$")


def is_table_row(line: str) -> bool:
    s = line.strip()
    return s.startswith("|") and s.count("|") >= 2


def is_separator(line: str) -> bool:
    s = line.strip().strip("|").strip()
    return bool(s) and set(s.replace("|", "")) <= set("-: ") and "-" in s


def split_frontmatter(text: str) -> tuple[dict[str, str], list[str]]:
    lines = text.splitlines()
    meta: dict[str, str] = {}
    if lines and lines[0].strip() == "---":
        i = 1
        while i < len(lines) and lines[i].strip() != "---":
            if ":" in lines[i]:
                k, v = lines[i].split(":", 1)
                meta[k.strip()] = v.strip()
            i += 1
        return meta, lines[i + 1:]
    return meta, lines


def render_body(raw: list[str]) -> list[str | bytes]:
    out: list[str | bytes] = []
    i, n = 0, len(raw)
    while i < n:
        line = raw[i]
        s = line.rstrip()
        stripped = s.strip()

        # fenced code block: verbatim (wrap only if a line exceeds 40 cols)
        if stripped.startswith("```"):
            i += 1
            while i < n and not raw[i].strip().startswith("```"):
                code = raw[i].rstrip()
                out.extend([code] if len(code) <= COLS else wrap_words(code.split()))
                i += 1
            i += 1
            continue

        # table directive (may precede a table) or comment block
        if stripped.startswith("<!--"):
            if DIRECTIVE_RE.search(stripped) and i + 2 < n \
               and is_table_row(raw[i + 1]) and is_separator(raw[i + 2]):
                directive = parse_directive(stripped)
                i += 1
                tbl = []
                while i < n and is_table_row(raw[i]):
                    tbl.append(raw[i])
                    i += 1
                out.extend(render_table(tbl, directive))
                continue
            # plain comment: drop until the closing --> (possibly multi-line)
            while i < n and "-->" not in raw[i]:
                i += 1
            i += 1
            continue

        # GFM table without a directive
        if is_table_row(s) and i + 1 < n and is_separator(raw[i + 1]):
            tbl = []
            while i < n and is_table_row(raw[i]):
                tbl.append(raw[i])
                i += 1
            out.extend(render_table(tbl, None))
            continue

        # blank
        if not stripped:
            out.append("")
            i += 1
            continue

        # ATX heading marker -> strip leading #'s (shown via banner already)
        if stripped.startswith("#"):
            stripped = stripped.lstrip("#").strip()

        # any other line: passthrough; word-wrap only if it overflows 40 cols
        out.extend([stripped] if len(stripped) <= COLS else wrap_words(stripped.split()))
        i += 1

    # collapse runs of blank records to one, then trim leading/trailing blanks
    collapsed: list[str | bytes] = []
    for it in out:
        if it == "" and collapsed and collapsed[-1] == "":
            continue
        collapsed.append(it)
    while collapsed and collapsed[0] == "":
        collapsed.pop(0)
    while collapsed and collapsed[-1] == "":
        collapsed.pop()
    return collapsed


def load_topics() -> list[tuple[str, int, list[str | bytes], int]]:
    """Return [(name, token, [rendered items], order)] sorted by order."""
    mdtok = mdbasic_tokens()
    topics = []
    for path in sorted(MANUAL.glob("*.md")):
        meta, body = split_frontmatter(path.read_text())
        name = meta.get("name", path.stem)
        order = int(meta["order"]) if meta.get("order", "").lstrip("-").isdigit() \
            else _order_from_stem(path.stem)
        tokspec = meta.get("token", "auto").strip().lower()
        if tokspec in ("", "auto"):
            token = topic_token(name, mdtok) or 0
        elif tokspec in ("none", "0"):
            token = 0
        else:
            token = int(tokspec, 0) & 0xFF
        topics.append((name, token, render_body(body), order))
    topics.sort(key=lambda t: t[3])
    return topics


def _order_from_stem(stem: str) -> int:
    m = re.match(r"(\d+)", stem)
    return int(m.group(1)) if m else 9999


# --------------------------------------------------------------------------- #
# Packing (unchanged output format)
# --------------------------------------------------------------------------- #
def build_index_and_data() -> tuple[bytes, bytes, int, int]:
    topics = load_topics()

    records: list[bytes] = []
    index: list[tuple[int, int, int, str]] = []
    for name, tok, body, _order in topics:
        blank, banner = topic_header(name)
        start = len(records)
        records.append(banner)
        records.append(blank)                # uniform 1-line gap under the banner
        records.extend(to_record(it) for it in body)
        index.append((tok, start, len(records) - start, name))
        records.append(blank)

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
        chunk += b"\x20" * (LINES_PER_BANK * COLS - len(chunk))
        chunk += b"\x00" * (BANK_SIZE - len(chunk))
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


def _preview_text(item: str | bytes) -> str:
    if isinstance(item, bytes):
        return "".join(chr(0x20 + (b & 0x7f)) if False else _sc_to_char(b) for b in item)
    return item


_SC_BOX = {v: k for k, v in BOX_SCREEN.items()}


def _sc_to_char(b: int) -> str:
    c = b & 0x7F
    if c in _SC_BOX:
        return _SC_BOX[c]
    if c == 0x00:
        return "@"
    if 0x01 <= c <= 0x1A:
        return chr(ord("a") + c - 1)
    if 0x20 <= c <= 0x3F:
        return chr(c)
    if 0x41 <= c <= 0x5A:
        return chr(c)
    return " "


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--preview", nargs="*", default=None)
    ap.add_argument("--pack", metavar="OUT", default=None)
    args = ap.parse_args()

    if args.pack:
        pack(Path(args.pack))
        return 0

    topics = load_topics()

    if args.list or args.preview is None:
        print(f"{len(topics)} topics:")
        for name, tok, body, _order in topics:
            ts = f"${tok:02x}" if tok else " - "
            print(f"  {name:<24} {ts}  {len(body):3d} lines")
        return 0

    want = {w.upper() for w in args.preview}
    for name, tok, body, _order in topics:
        key = name.replace("()", "").upper()
        if want and key not in want and name.upper() not in want:
            continue
        print(f"===== {name}  ({len(body)} lines) " + "=" * max(0, COLS - len(name) - 18))
        for it in body:
            print("|" + _preview_text(it))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
