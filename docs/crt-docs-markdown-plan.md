# CRT docs: markdown source + table-aware generator

> **Status: COMPLETE — pipeline built and all tabular topics authored.** The
> genuinely tabular topics have all been hand-authored against `mdbasic.pdf` and the
> Appendix E notes chart reconstructed from the page-96 image (see the "Done" list in
> REMAINING below — nothing tabular is left). `vice_docs_test.py` is green and
> `docs_coverage.py` is at 30 missing (improved from the 33 baseline, all TOC/title
> noise). What is done:
> - **Glyph check (step 1):** `tools/glyph_check.py` reads CHARGEN ROM from a
>   headless VICE and asserts all 11 box screen codes; the plan's map is confirmed
>   correct (│=$5D ─=$40 ┌=$70 ┐=$6E └=$6D ┘=$7D ├=$6B ┤=$73 ┬=$72 ┴=$71 ┼=$5B).
> - **Generator (`tools/build_docs.py`):** rewritten to read `docs/manual/*.md` →
>   records → `.idx`/`.dat`, same CLI/format (drop-in). Includes the table engine:
>   narrow → full PETSCII box grid (auto-wraps cells to fit 40; cells are drawn
>   flush against the `│` separators — no per-cell space padding); wide → `sections`
>   (default: each row is a normal-video sub-header = a leading `─` + the first-column
>   value + `─` filling to column 40, then `LABEL: value` rows) or `cards` (via
>   `<!-- table: mode=cards key=... span=... pack=N -->`). Directive key/span names
>   must be single tokens (parser is whitespace-split); reference multi-word columns
>   by leaving them unnamed (they default to span) rather than quoting.
> - **Bootstrap (`tools/bootstrap_manual.py`):** the old PDF-extraction code; wrote
>   all 86 `docs/manual/NNN-name.md` files (prose + fenced SYNTAX/EXAMPLE). Re-run
>   with `--force` only to re-scaffold; it will clobber hand-authored tables.
> - **Coverage (`tools/docs_coverage.py`, step 0):** PDF-body words vs generated
>   words. Baseline **33 missing**, all TOC/title-page/heading fragments and
>   *improved* scrambled-table artifacts (`else55`, `3theni`, …). This number must
>   not grow for the wrong reasons as tables are authored.
> - **Verification 3/4/5:** `--pack` index 2 KB (≤3 KB budget), `build_disk.sh` +
>   `vice_cart_test.py` boot green, and `vice_docs_test.py` green — extended with
>   `table_wide_render` / `table_box_glyphs` / `table_box_header` assertions that
>   scroll SCREEN's real tables into view on the emulated screen.
> - **Proof that migration is loss-free:** generated non-blank content lines are
>   byte-identical to the pre-migration pipeline across all 86 topics (only blank
>   spacing under banners was standardized to one line).
>
> **AUTHORING PASS — COMPLETE (plan §5 / task 6).** All genuinely tabular topics
> hand-authored against `mdbasic.pdf`. **Done:** SCREEN (PAGE table → sections,
> colorMode MODE table → box grid — the model), COLOR (16 colors as a compact 4-col
> grid; the PDF's original "Read" typo for value 2 was corrected to "Red" per user),
> JOY, MAPCOL, TEXT, WAVE, ENVELOPE (2-/3-col box grids), DISK (wide command table →
> `mode=sections`), SERIAL (parity grid), PLAY (symbol/meaning → sections; needed
> `\|` pipe-escaping in cells), INF (71-row value/info → sections, nested Kernal/
> bank/page/mode sub-tables flattened inline), SPRITE (PATTERN & SIZE grids, bank
> table → sections, binary/data dump → fenced code), DESIGN (letter-A art → fenced
> code, PAGE table → sections, CHARSET grid), Appendix A (page grid), Appendix B
> (error-code grid), Appendix C (96-row ASCII table → 5-col box grid at exactly 40
> cols; £/↑/← spelled out as POUND/UP ARROW/LEFT ARROW), and **Appendix E** notes
> chart reconstructed from the page-96 image (88 keys, sections keyed by KEY+NOTE;
> scientific names + frequencies computed A4=440 equal temperament and all
> cross-checked against the image; Helmholtz names generated systematically;
> open-string annotations + octave nicknames transcribed). Generators for the ASCII
> and notes tables are in the session scratchpad if regeneration is needed. POKE has
> no real table (prose). Appendix D's RS-232 status-bit list was left as prose (reads
> fine; not in the tabular scope) — an optional future polish. **Original-manual data
> fixes (per user):** COLOR value 2 "Read"→"Red"; SPRITE's binary/data example row
> `255,1,1,252` (4 bytes) → `255,1,252` (now a correct 63-byte sprite).
>
> **Pipe rendering fix:** `ascii_to_screen` mapped `|` ($7C) to screen code $42, which
> in the pager's **lowercase** charset draws as the letter "B" ("SCREEN ON B OFF").
> Remapped to $5D (the box-drawing vertical bar `│`), which renders as a proper pipe
> in the lowercase charset — fixes every `|` globally (SCREEN/PLAY syntax, etc.).
> Workflow per topic: edit `docs/manual/*.md`, `build_docs.py --preview <NAME>`,
> then `docs_coverage.py` (missing count must not rise). The interactive design Q&A
> that produced the "Decisions" section is already settled — do not re-ask.
>
> **To resume / manually test:** `tools/build_disk.sh build` writes a docs-enabled
> `build/mdbasic.crt`; run it on real hardware / U64 and press **CTRL+RESTORE** to
> open the pager, search `SCREEN`, page down to see the MODE box grid and the PAGE
> sections table. Regression gate before/after each batch: `tools/vice_docs_test.py`
> (must stay green) and `tools/docs_coverage.py` (missing count must not rise above
> the 33 baseline). Author the next batch by copying SCREEN's GFM-table style.
>
> **Reference artifacts already confirmed during planning (re-derive as needed):**
> - `pdftotext -layout mdbasic.pdf -` — the current extraction source; prose reflows
>   fine, tables scramble.
> - The PDF has exactly ONE image: `pdfimages -list mdbasic.pdf` → page 96 only
>   (854×2400 RGB), the Appendix E notes chart. Extract with
>   `pdfimages -png -f 96 -l 96 mdbasic.pdf <out>`; it is crisp and legible.
> - Downstream contract: `tools/build_docs.py --pack build/docs.bin` writes
>   `build/docs.idx` + `build/docs.dat`; `tools/build_disk.sh:86-87` packs them via
>   `tools/make_crt.py --index/--data`. Index must stay ≤ 3 KB
>   (`HANDLER_OFF-INDEX_OFF` in make_crt.py), i.e. ≤ ~128 topics (we have 86).
> - The pager (`docs_pager.asm`) stores raw 40-byte screen-code records and uses the
>   ROM **lowercase** charset (`$1800`), so any PETSCII glyph embeds directly; bit 7
>   = reverse video. `$40` is already used as the horizontal-rule glyph
>   (`fillrule`, docs_pager.asm:1150) — proof box glyphs render in lowercase mode.

## Context

The CTRL+RESTORE docs pager currently builds its content by scraping `mdbasic.pdf`
with `pdftotext -layout` and a large pile of reflow heuristics in
`tools/build_docs.py`. Prose reflows to 40 columns fine, but **tables get
scrambled**: `pdftotext` throws away cell structure and the heuristics collide
values from different columns onto the same wrapped line. Concrete breakage today:

- **SCREEN** — the 4-column PAGE/SCREEN RAM/SPRITE POINTERS/AVAILABLE RAM table and
  the PATTERN/COLOR SOURCE/AVAILABLE COLORS table come out as unreadable soup.
- **Appendix C (ASCII)** — a 5-column × ~130-row table, effectively unusable.
- **Appendix E (Notes)** — the 88-key frequency chart is a PDF *image*, so it is
  dropped entirely.

Fully automating good tables from the PDF is not feasible — cell boundaries are
gone and which blocks are tables (and how to break them) needs human judgment.

**Goal:** move to a hand-editable **markdown source of truth** (one file per topic),
plus a generator that renders tables well on a 40-column screen — full PETSCII box
grids when they fit, and row-oriented "cards" when they don't. The generator stays a
drop-in producer of the same `docs.idx`/`docs.dat` the cartridge build already
consumes, so `docs_pager.asm`, `make_crt.py`, and `build_disk.sh` need no changes.

**No-loss guarantee (per user):** preserve *all* body content from the PDF. The
**only** thing intentionally dropped is the front-matter **table of contents** (page
numbers are meaningless on-screen and navigation is by topic index). Nothing else is
abridged. A coverage check (see Verification) diffs PDF body text against generated
output so nothing drops silently.

**Notes image is portable (verified):** the PDF has exactly one image — Appendix E,
page 96 — extracted with `pdfimages` and confirmed legible. It is the standard 88-key
chart: Key number · Helmholtz name · Scientific name (C8, A♯7/B♭7, …) · Frequency
(Hz) · Corresponding Open Strings (Violin/Viola/Cello/Bass/Guitar). Frequencies are
equal-tempered (A4=440), so every row is reconstructable exactly and cross-checked
against the image. It becomes a real data table in markdown (see step 5), so the one
piece of content the current pipeline loses is recovered.

## Decisions (confirmed with user)

- **Narrow tables (fit ≤40 cols):** full PETSCII box grid (borders + interior
  separators), cells wrap on whitespace only (never mid-word).
- **Wide tables (>40 cols):** row-oriented. Keep the small/narrow columns together
  compactly (e.g. a boxed mini-row or `HEX: 03  BINARY: 00000011` packed with 2–3
  spaces), and emit wide columns (e.g. DESC) as full-width `LABEL: value` rows
  beneath, wrapped on whitespace. Author picks per-table via a directive.
- Everything that can be represented at 40 cols is preserved; Appendix E's note
  chart is **reconstructed** as data (not lost).

## Approach

Full migration to markdown, made tractable by an automatic bootstrap that does the
prose (~90% of the text) and leaves only tables for hand-authoring.

### 1. New source tree: `docs/manual/`
One markdown file per topic, e.g. `docs/manual/072-screen.md`. Minimal frontmatter:

```
---
name: SCREEN            # banner/grid display name (verbatim, may include qualifiers)
order: 72               # sequence in the guide
token: auto             # optional; default derives from name like today
---
```

Body is GFM-ish markdown the generator understands:
- Paragraphs → word-wrapped to 40 cols (existing `wrap_words`).
- `LABEL:` lines (PURPOSE:, SYNTAX:, …) → emitted as labels (existing behavior).
- ```` ```text ```` fences → verbatim (SYNTAX/EXAMPLE code), wrapped not reflowed.
- GFM tables (`| a | b |` + `|---|`) → table engine below.

### 2. Table engine (the core new logic)
Given a parsed table (headers + rows), compute the full-box-grid width (col widths =
max cell width, cells wrappable). Then:
- **width ≤ 40:** render a full box grid using PETSCII line glyphs — top
  `┌┬┐`, header rule `├┼┤`, `│` separators, bottom `└┴┘`, `─` fills — with
  multi-line wrapped cells vertically aligned.
- **width > 40:** wide mode, selected by an optional directive line immediately
  before the table:
  `<!-- table: mode=cards key=ASCII,HEX,BINARY,SCREEN span=DESC pack=2 -->`
  - `mode=sections` (default when wide, no directive): each row → a reverse-video
    sub-banner from the first column, then `HEADER: value` lines for the rest.
  - `mode=cards`: `key=` columns render together compactly (packed on as few lines
    as fit, box-drawn if they fit a grid); `span=` columns render as full-width
    `HEADER: value` wrapped rows beneath each key group. `pack=N` caps key pairs per
    line. This delivers the user's "small values in a table, big DESC spans below."
  - Empty cells are skipped (keeps the sparse ASCII table compact).

PETSCII glyph → C64 **screen codes** to use (lowercase charset; `$40`=`─` already
proven by `fillrule` in `docs_pager.asm:1150`). Verify in VICE step 1 before relying:
`│`=$5D `┌`=$70 `┐`=$6E `└`=$6D `┘`=$7D `├`=$6B `┤`=$73 `┬`=$72 `┴`=$71 `┼`=$5B.
(Derivation: PETSCII $A0-$BF → screen $60-$7F, PETSCII $C0-$DF → screen $40-$5F.)
These embed directly in the 40-byte records — no pager change.

### 3. Generator: repurpose `tools/build_docs.py`
Rewrite `build_docs.py` to read `docs/manual/*.md` → `[(name, token, [records])]`,
keeping the **same** `--pack` / `--list` / `--preview` CLI and the **same** output
format so `build_disk.sh:86` is untouched. Reuse unchanged from today:
`ascii_to_screen`, `display_name`, `topic_header`, `line_to_record`,
`build_index_and_data` packing, and constants (`COLS=40`, `NAMELEN=19`,
`LINES_PER_BANK=204`, `IXSTRIDE=24`). Token resolution keeps `mdbasic_tokens()` +
`STOCK_TOKENS`. Index budget: 3 KB / ~128 topics; we have 86 → fine.

### 4. Bootstrap the markdown (one-time): `tools/bootstrap_manual.py`
Move today's PDF-extraction code here. For each topic it writes
`docs/manual/NNN-name.md` with frontmatter + the current reflowed **prose**, SYNTAX/
EXAMPLE blocks as fenced code, and any detected table region emitted as a best-effort
GFM table *plus* a `<!-- TODO verify against PDF -->` marker and the raw
`pdftotext -layout` slice in an HTML comment for hand-fixing. Run once to scaffold all
86 files; then it is a dev tool, not part of the build.

### 5. Hand-authoring pass
Fix tables file-by-file against the PDF, concentrating on the ~15 genuinely tabular
topics (SCREEN, COLOR, DISK, ENVELOPE, WAVE, SERIAL, DESIGN, SPRITE, INF, JOY, PLAY,
POKE, TEXT, MAPCOL, appendices A/B/C). Reconstruct **Appendix E** notes as a real
table with **all** image columns preserved (key#, Helmholtz name, scientific name,
frequency Hz, and any open-string annotations), rendered as paged cards; frequencies
generated from A4=440 equal temperament and each cross-checked against the extracted
`pdfimages` PNG. Keep the existing descriptive prose above it.

## Files

- `tools/build_docs.py` — rewritten: markdown → records → `.idx`/`.dat` (drop-in).
- `tools/bootstrap_manual.py` — new: one-time PDF→markdown scaffolder (old extraction code).
- `docs/manual/*.md` — new: 86 topic source files (source of truth going forward).
- `tools/vice_docs_test.py` — extend: assert a rendered box-table row and a wide-table
  card render; keep existing boot/search/regression assertions green.
- No changes to `docs_pager.asm`, `make_crt.py`, `build_disk.sh`, `boot.asm`.

## Verification

0. **Coverage check:** a script that flattens PDF body text (minus the TOC) into
   word tokens and confirms every token appears in the generated markdown/records, so
   no content is silently dropped in the migration. Notes-chart rows verified against
   the extracted image.
1. **Glyph check (first):** render candidate box screen codes in VICE (headless
   screenshot) to confirm they draw as lines/corners in the lowercase charset; adjust
   the code map if any differ.
2. `python3 tools/build_docs.py --preview SCREEN COLOR` — eyeball ASCII/PETSCII
   previews of box grids and wide-table cards.
3. `python3 tools/build_docs.py --pack build/docs.bin` — confirm index ≤ 3 KB, sane
   line/bank counts.
4. `tools/build_disk.sh build && tools/vice_cart_test.py build/mdbasic.crt` — CRT
   still boots.
5. `tools/vice_docs_test.py` — end-to-end: CTRL+RESTORE opens docs, search, exit,
   sprite_timing regression, plus new table-render assertions.

## Scope note

This is a large authoring pass (86 files); the bootstrap handles prose automatically,
and the table hand-fixing should be done in reviewable batches. The PDF stays the
ultimate reference; `bootstrap_manual.py` can re-scaffold if the manual changes
materially.
