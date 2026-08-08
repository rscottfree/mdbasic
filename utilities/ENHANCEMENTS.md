# MDBASIC — enhancements in this fork

This fork tracks the official [MDBASIC by Bowren](https://github.com/bowren/mdbasic)
and layers additive features and tooling on top. The repository **root** is kept
byte-identical to the upstream file set (the core runtime `mdbasic.asm`, the
`mdbasic.pdf` reference, the template `mdbasic.d64`, `README.md`, `LICENSE.txt`,
`NOTICE.txt`, `tasm64.lang`, `compile.sh`, `runcart.sh`). **Everything this fork
adds lives under `utilities/`** so syncing new upstream releases stays clean — the
only shared file that can ever conflict is `mdbasic.asm`, and this fork does not
modify it. See `utilities/README.md` for the folder layout and the full
build/test walkthrough.

## Features

### Built-in manual viewer — CTRL+RESTORE (cartridge builds only)

Press **CTRL+RESTORE** to open a full-screen, searchable viewer of the MDBASIC
manual without disturbing your program; **RUN/STOP** exits back to where you were.
It costs **zero bytes** in the 16K runtime image — the manual is packed into extra
Magic Desk cartridge banks. The existing keys are preserved: **RUN/STOP+RESTORE**
still breaks, and plain **RESTORE** keeps its editor-mode-reset/no-op behaviour.

### IRQ-driven sprite MOVE

`MOVE ... TO ...` returns immediately and advances up to eight sprites from the
sprite IRQ. Its per-sprite delay accumulator preserves the original 0-255 timing
curve while keeping movement independent of BASIC execution and Ultimate 64
turbo modes.

## Building the enhanced artifacts

`sh utilities/tools/build_disk.sh [outdir]` assembles `mdbasic.asm` and writes the
distributables to `utilities/build/` (default):

- `mdbasic.prg` — raw 16K image (`$8000-$BFFF`)
- `mdbasic.d64` / `mdbasic.d81` — disks (the tracked `mdbasic.d64` template with a fresh PRG)
- `mdbasic.crt` — Magic Desk cartridge with the docs pager and utility tools bundled

Requires `tmpx` and VICE (`c1541`/`x64sc`) plus `python3`. The on-cart manual is
rendered from the markdown under `utilities/docs/manual/`. The four artifacts are
committed under `utilities/build/`, so a fresh clone is ready to run; rebuild to
refresh them. The root's `compile.sh` remains the quick assemble-and-launch loop
for the base image.

See `utilities/CLAUDE.md` for full build and architecture details (cartridge
layout, the docs-pager mechanism, and the keyword tables).

## Testing

Tests assemble the build, run it in VICE, and assert on screen RAM. Everything
testing lives in `utilities/tests/` (see its `README.md`):

- `sh utilities/tests/run_all_tests.sh` — the whole VICE regression suite
- `python3 utilities/tests/vice_cart_test.py utilities/build/mdbasic.crt` — boot the CRT, assert the banner
- `python3 utilities/tests/vice_docs_test.py` — docs pager end-to-end (open, search, scroll, exit)
- `python3 utilities/tests/move_timing_test.py` + `sprite_timing.bas` — sprite MOVE jiffy timing
- `sh utilities/tests/u64_sprite_timing_test.sh` — the same timing check on Ultimate 64 hardware

## Syncing with upstream

Root files track Bowren's official repo and are synced manually via GitHub. The
entire enhancement layer lives under `utilities/` (sources in `utilities/src/`,
build/host tools in `utilities/tools/`, tests in `utilities/tests/`, the markdown
manual in `utilities/docs/`) — paths upstream never touches, so they never
conflict.
