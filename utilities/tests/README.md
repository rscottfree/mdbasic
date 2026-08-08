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

## Sprite MOVE timing

`sprite_timing.bas` reproduces the original `SS` test's 344-pixel move at speeds
0/64/128/192/255. It installs a 30-byte waiter at `$C100` that watches the
VIC-II X register and sprite-0 X-MSB with interrupts enabled, snapshots the
24-bit jiffy clock at `$C070-$C072` when X reaches 344, and returns to BASIC.
This timestamps a non-blocking MOVE without adding a BASIC polling loop's delay.
The five 16-bit little-endian results are written to `$C080-$C089`, followed by
the `$FF` completion marker at `$C08A`. Run it against Ultimate 64 hardware with:

```sh
sh utilities/tests/u64_sprite_timing_test.sh
```

Results should remain close to the original 5/86/173/259/344 jiffies. The same
result under `$D030=$FF` turbo confirms that movement remains IRQ-driven rather
than tied to BASIC execution speed. `move_timing_test.py` runs the corresponding
check in VICE.
