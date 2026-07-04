# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

MDBASIC is an extension to Commodore 64 BASIC V2, written in 6502 assembly. The entire runtime is one file, `mdbasic.asm` (~9,500 lines), assembled with TMPx/Turbo Assembler into a 8K image that occupies `$8000-$BFFF` on the C64. It adds new keywords (sprites, graphics, SID sound, disk commands, structured editing) and overrides several BASIC ROM vectors to hook tokenization, listing, and execution.

## Build & run

All tooling assumes `tmpx` (TMPx assembler), `x64sc` (VICE emulator), and `c1541` (VICE disk tool) are on `PATH`. Download TMPx from https://style64.org/file/TMPx_v1.1.0-STYLE.zip.

- `sh compile.sh` — assemble `mdbasic.asm` → `mdbasic.prg` (+ `mdbasic.lst`), then launch VICE and `SYS64738` to install. The primary build+run loop.
- `tmpx -l mdbasic.lst -i mdbasic.asm -o mdbasic.prg` — assembly only, to verify the source builds without launching the emulator. The `.lst` listing file is the best reference for resolved addresses.
- `sh runcart.sh` — run the prebuilt `mdbasic.crt` cartridge in VICE with `mdbasic.d64` mounted on drive 8.
- `tools/build_disk.sh [outdir]` — assemble and write all release artifacts to `outdir` (default `build/`): `mdbasic.prg`, `mdbasic.d64` (template copy with the fresh PRG), `mdbasic.d81` (fresh 1581 disk mirroring the D64), and `mdbasic.crt`. Assembles `mdbasic.asm` as-is (no version or color stamping).
- `tools/make_crt.py prg crt` — wrap a 16K MDBASIC PRG into the Magic Desk cartridge (CRT hardware id 19). MDBASIC runs from RAM and pages BASIC ROM in/out, so it can't run from a plainly mapped cart; the loader (`tools/cart_boot.bin`, generated from `boot.asm`) copies the image from banked ROM into `$8000-$BFFF`, disables the cart, and restarts via the copied "CBM80". Given `--pager/--index/--data/--handler`, it also appends the docs-pager banks (3+) and the loader installs the RESTORE docs handler (see Docs pager below). `tools/make_crt.py`'s docstring documents the bank layout.
- **Docs pager (CTRL+RESTORE):** pressing CTRL+RESTORE opens a full-screen viewer of the manual, bundled into extra Magic Desk banks — costs ZERO bytes in the 16K image. The RESTORE NMI fires on every RESTORE; the handler gates on CTRL (keyboard-matrix row 7 / `STKEY` $91 bit 2, which `SCNSTOP` already latched for the STOP test): RUN/STOP+RESTORE breaks, CTRL+RESTORE always opens the docs (clearing editor modes so it returns clean), and plain RESTORE keeps its editor-mode-reset/no-op behaviour. `tools/build_docs.py` extracts `mdbasic.pdf` into fixed 40-col line records + a topic index; `docs_pager.asm` is the viewer (runs at `$c000`); `docs_help.asm` is the RESTORE handler (installed at `$033c`); `boot.asm` is the loader source (it repoints the cart NMI vector `$8002` -> `$033c` and stashes the original `runstp`). `tools/vice_docs_test.py` is the end-to-end test (boot, install, `SYS dodocs` past the CTRL gate, search, exit, sprite_timing regression); `tools/vice_docs_nav_test.py` supplements it with the doc-view navigation keys (F3/F5 topic nav, F7/F1 paging, HOME, DEL, selection highlight, status bar); `tools/vice_docs_clobber_test.py` proves the pager overwrites `$c000-$cfff` (SCREEN pages / bitmap color / RS-232 buffers) — it assumes that 4K is free scratch — and that the exit forces a canonical text mode / VIC bank 0 (VMCSB `$15`, SCROLY text, bank 0) rather than half-restoring the pre-docs graphics state, so a graphics program recovers cleanly by re-`RUN`ning. `tools/vice_docs_cursor_test.py` covers a related editor-state fix: exiting from a SCREEN 1-5 page must leave the cursor visible — that page's screen RAM was never saved (SCRBUF only holds `$0400`), so its stale line-link table / `PNT` ($d1/$d2) would leave the cursor drawn off-screen until a keypress; the exit clears to a fresh `$0400` screen (rebuilding the link table + homing `PNT`) when `savhib != $04`, while page 0 keeps its restored screen. The test freezes the true pager-exit state by returning the synthetic NMI frame into a JMP-self spin loop (a real CTRL+RESTORE RTIs back to the interrupted editor loop, never through READY, so READY can't re-init `PNT` for it). The docs-pager design memory has the full mechanism.
- `tools/vice_cart_test.py crt` — boot a `.crt` headless in VICE and assert the MDBASIC banner.
- For Ultimate 64 manual testing, run `tools/build_disk.sh`, then mount the fresh disk with `$HOME/.local/bin/u64 create mount -t local -p /Users/ryan/Developer/mdbasic/build/mdbasic.d64 -d a -s`. Slot `a` is device 8. If the mount/test path behaves stale or unreliable, ask the user to reset the U64 before continuing.

## Testing

There is no unit-test framework — testing means assembling, then running BASIC in VICE and asserting on screen RAM. The harness in `tools/` automates this:

- `tools/c64_basic_prg.py [--dialect mdbasic] src.bas out.prg` — tokenize ASCII BASIC into a real `$0801` PRG. The `--dialect mdbasic` mode emits MDBASIC extension tokens. Use this instead of `petcat` (petcat misreads uppercase ASCII as shifted PETSCII).
- `tools/vice_prg_test.py --file name=host.prg --run name --expect "TEXT"` — build a temp D64, boot `x64sc`, inject `LOAD`/`RUN` over the binary monitor, and poll screen RAM for expected text.
- `tests/sprite_timing.bas` validates `MOVE ... TO ...` jiffy-clock timing; it writes result bytes to `$C000-$C002`. `tools/u64_sprite_timing_test.sh` runs the same check against the `c64ultimate` hardware.

See `tools/README.md` for full harness usage.

## How MDBASIC installs and runs

The image at `$8000` begins with a cartridge header (`.word resvec,runstp` + `"CBM80"`), so it can be installed as a cartridge or loaded as a PRG and started with `SYS64738`. Two entry paths set up the same state via `newvec`:

- `SYS64738` (reset / `resvec`) — full cold start, shows banner, enters immediate mode.
- `runstp` — Restore-key NMI handler / break path.

MDBASIC works by overriding BASIC's indirect vectors: `ICRNCH ($0304)` for tokenizing, `IQPLOP ($0306)` for listing, `IGONE ($0308)` for execution. `R6510` ($01) is toggled throughout to page the BASIC ROM in/out so the `$8000-$BFFF` RAM image is visible when needed.

## Adding or changing keywords (the critical structure)

New keywords are defined by a set of parallel tables near the top of the image (around lines 391-640 in `mdbasic.asm`). To add a keyword you must keep these in sync, in token order:

1. **`newcmd`** — keyword name strings as `.shift` entries (last char has bit 7 set). Order defines token assignment.
2. **Token constants** (`TOKEN_*`, lines ~341-389) — MDBASIC tokens start at `FIRST_CMD_TOK = $cb`. Statement/command tokens, then statement+function tokens (`ERR`/`KEY`/`TIME` at `$f2-$f4`), then function-only tokens (`$f5-$ff`, with `PI` = `$ff`).
3. **`cmdtab`** — command dispatch table (`.rta` per token, `$80` upward). Entries reuse CBM ROM routines or point at MDBASIC routines; `.rta REM` is used for no-ops like `ELSE`.
4. **`funtab`** — function dispatch table for the function tokens `$f2-$ff`.

Tokenization (`toknew`, from ~line 644) and listing/de-tokenizing must round-trip these consistently. The keyword tables, token constants, and dispatch tables are positionally coupled — an off-by-one between them silently corrupts dispatch.

Custom MDBASIC error messages are appended after the CBM error list (`misop` etc., tokens 31-37) with the `erradd` pointer table; raise via `ldx #errno : jmp ($0300)`.

## Conventions

- Match the surrounding style in `mdbasic.asm`: existing label naming, column alignment, and comment density. Comments explain hardware/intent, not individual opcodes. Zero-page, KERNAL, and VIC/SID register equates are all defined and commented at the top of the file — reuse them rather than hardcoding addresses.
- Generated artifacts are gitignored, not committed: `tools/build_disk.sh` writes them to `build/` (also `mdbasic.lst`, top-level `mdbasic.prg`/`mdbasic.crt`, `tools/cart_boot.bin`); distributables ship via GitHub Releases. Rebuild locally rather than expecting them in the tree. The one exception is `mdbasic.d64`, which IS tracked — it is the template disk (upstream's example library) that `build_disk.sh` copies and swaps the fresh PRG into.
- The version string lives in the `mesge` banner (`.text "mdbasic 26.06.17"`); bump it for releases.
- Commit messages follow `version YY.MM.DD ...` / `BUGFIX:` / `CHANGE:` style (see git log).

## Reference

- `mdbasic.pdf` — full user-facing documentation of every command's syntax. Consult/update it when changing documented behavior.
- `README.md` — feature overview and load/run instructions.
- `docs/single-file-bundle-plan.md` — deferred design for a self-contained single-PRG bundler; do not implement unless explicitly resumed.
