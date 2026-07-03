# MDBASIC — enhancements in this fork

This fork tracks the official [MDBASIC by Bowren](https://github.com/bowren/mdbasic)
and layers additive features and tooling on top. The core runtime (`mdbasic.asm`,
`mdbasic.pdf`) stays as close to upstream as possible; everything below lives in
its own files so syncing new upstream releases stays clean — the only shared file
that can ever conflict is `mdbasic.asm`.

## Features

### Built-in manual viewer — CTRL+RESTORE (cartridge builds only)

Press **CTRL+RESTORE** to open a full-screen, searchable viewer of the MDBASIC
manual without disturbing your program; **RUN/STOP** exits back to where you were.
It costs **zero bytes** in the 16K runtime image — the manual is packed into extra
Magic Desk cartridge banks. The existing keys are preserved: **RUN/STOP+RESTORE**
still breaks, and plain **RESTORE** keeps its editor-mode-reset/no-op behaviour.

### Jiffy-clock sprite MOVE timing

`MOVE ... TO ...` sprite-movement delays are timed from the C64 jiffy clock
instead of a CPU loop, so movement speed stays stable under Ultimate 64 turbo
modes and other accelerated setups.

## Building the enhanced artifacts

`tools/build_disk.sh [outdir]`
assembles `mdbasic.asm` and writes distributables to `build/` (default):

- `mdbasic.prg` — raw 16K image (`$8000-$BFFF`)
- `mdbasic.d64` / `mdbasic.d81` — disks (the tracked `mdbasic.d64` template with a fresh PRG)
- `mdbasic.crt` — Magic Desk cartridge with the docs pager bundled

Requires `tmpx`, VICE (`c1541`/`x64sc`), `python3`, and `pdftotext` (for the docs
pager). The tracked `mdbasic.prg`/`mdbasic.crt` mirror upstream; rebuild them
here or grab a release. `compile.sh` remains the quick assemble-and-launch loop
for VICE.

See `CLAUDE.md` for full build and architecture details (cartridge layout, the
docs-pager mechanism, and the keyword tables).

## Testing

There is no unit-test framework — tests assemble, run BASIC in VICE, and assert on
screen RAM (see `tools/README.md`):

- `tools/vice_cart_test.py build/mdbasic.crt` — boot the CRT and assert the banner
- `tools/vice_docs_test.py` — docs pager end-to-end (open, search, scroll, exit)
- `tools/move_timing_test.py` + `tests/sprite_timing.bas` — sprite MOVE jiffy timing
- `tools/u64_sprite_timing_test.sh` — the same timing check on Ultimate 64 hardware

## Syncing with upstream

Core files (`mdbasic.asm`, `mdbasic.pdf`, `README.md`, `LICENSE.txt`, `NOTICE.txt`,
`tasm64.lang`, `runcart.sh`) track Bowren's official repo and are synced manually
via GitHub. The enhancement layer (`docs_pager.asm`, `docs_help.asm`, `boot.asm`,
`tools/`, `tests/`) is in separate paths upstream never touches, so those never
conflict.
