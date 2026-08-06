# MDBASIC tests

Each test **assembles the build, boots it in VICE (`x64sc`), and asserts on C64
screen RAM / memory** over the binary monitor. All testing lives in this folder;
the build/host tools it imports are in [`../tools/`](../tools/README.md).

## Running

```sh
sh utilities/tests/run_all_tests.sh          # the full regression suite
python3 utilities/tests/<one_test>.py        # any single test, run directly
```

`run_all_tests.sh` runs the core suite (renum, docs, docs-nav, docs-clobber,
docs-cursor, pack, pack-list) and invokes `cleanup_test_vice.py` between runs to
reap any stray emulator. Requires `tmpx`, `x64sc`, `c1541`, and `python3`
(validated against VICE 3.10).

Each test computes its own paths: sibling test modules resolve from this folder,
the build tools from `../tools/`, and the pristine `mdbasic.asm` / template
`mdbasic.d64` from the repo root. `vice_docs_test.build_cart()` assembles the full
cartridge (image + docs + tool banks) into `/tmp` for the suite to boot.

## Harness / shared modules

- **`vice_prg_test.py`** — the base harness: build a temp D64, boot `x64sc` with
  drive 8, inject `LOAD`/`RUN` over short-lived monitor connections, poll screen
  RAM. Also a standalone CLI:
  ```sh
  python3 utilities/tests/vice_prg_test.py \
    --file main=/tmp/main.prg --run main --expect "DONE"
  ```
- **`vice_docs_test.py`** — assembles the whole cartridge (`build_cart()`) and runs
  the docs-pager end-to-end test; other tests import it for the shared build.
- **`renum_test_lib.py`** — shared helpers for the renumber/move/copy tests.
- **`cleanup_test_vice.py`** — kill leftover VICE processes/monitor sockets.

## Test scripts

- **`vice_cart_test.py CRT`** — boot a `.crt` headless and assert the banner.
- **`vice_renum_test.py`** — the renumber/move/copy tool (menu wiring, renumber +
  reference rewrite with digit grow/shrink, reject paths stay byte-identical, REPL
  persistence, post-op link integrity + executability). Also drives
  `vice_renum_single_line_move_test.py` and `vice_renum_move_overlap_test.py`.
- **`vice_docs_test.py` / `vice_docs_nav_test.py`** — docs pager open/search/exit
  and the in-view navigation keys (topic nav, paging, HOME, selection, status bar).
- **`vice_docs_clobber_test.py` / `vice_docs_cursor_test.py`** — the pager's use of
  `$c000-$cfff` scratch and its canonical text-mode / cursor-visible exit.
- **`vice_pack_test.py` / `vice_pack_list_test.py`** — the PACKAGE tool: menu wiring,
  byte-compare against the `pack_prg.py` oracle, overwrite, cartless auto-run output
  equality, and the full post-BREAK LIST/edit/SAVE/RUN development loop.
- **`vice_pack_examples.py`** — package the example-program sample into a
  temporary D81 with the real in-emulator tool and verify each.
- **`vice_scroll_timing_test.py`** — uses a VICE `$D016` write watchpoint and
  CPU-history clocks to reproduce the original fine-scroll hitch, then verifies
  `hscroll_smooth.bas` keeps every horizontal position within three quarters of
  a frame of its four-frame budget on PAL and NTSC. The sample prepares a second screen at
  `$2000` and swaps it at the coarse-scroll boundary, so no partially shifted
  row is displayed (warp mode does not affect the emulated timing).
- **`vice_scroll_step_test.py`** — runs `hscroll_step.bas` on PAL and NTSC,
  changes its live pixel displacement from 1 to 5 and then 8 through the C64
  keyboard buffer, and verifies both the fine-scroll sequence and page swaps.
- **`vice_scroll_2d_test.py`** — verifies the pure-MDBASIC `scroll_2d.bas` uses
  one `SCREEN` command to update `$D011` and `$D016` on PAL and NTSC, including
  live step changes from 1 to 3 and 7, and checks that its checkerboard is
  invariant across diagonal coarse wraps.
- **`block_scroll.bas`** — a pure-MDBASIC coarse character scroller with several
  randomly sized 1-8 by 1-8 white reverse-space blocks. Blocks enter and leave one column at a
  time, and horizontal spawn spacing prevents overlap. A custom stipple character
  uses multicolor character mode to supply a dark, bitmap-like tiled background
  while the reverse spaces remain solid white, retaining text `SCROLL`;
  redefining screen code 32 makes the spaces inserted by non-wrapping `SCROLL`
  display the proper tile, while `FILL` draws the new block edge and explicitly
  restores its trailing edge. Degenerate one-column moves use `FILL` because the
  cartridge's left-scroll copy loop requires a region at least two columns wide.
- **`vice_block_scroll_test.py`** — single-steps that example in VICE and checks
  every frame for white solid rectangles, legal dimensions, left-only movement,
  right-edge-only entry, gradual left-edge exit, background restoration, and
  at least two blank columns between simultaneous blocks.

## Sprite MOVE timing

`sprite_timing.bas` measures sprite `MOVE ... TO ...` delays against the jiffy clock
at `$A2`, writing result bytes to `$C000-$C002` (speed 0/1/2 deltas). Run it against
Ultimate 64 hardware with:

```sh
sh utilities/tests/u64_sprite_timing_test.sh
```

Expected U64 result bytes are typically `010c16` or `020c16` (speed 1 ≈ 12 jiffies,
speed 2 ≈ 22 jiffies); the same result under `$D030=$FF` turbo confirms the delay
is jiffy-clock based. `move_timing_test.py` runs the corresponding check in VICE.
