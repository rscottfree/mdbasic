# CTRL+RESTORE utility menu + BASIC renumber/move tool

## Context

The user wants to add a **renumber/move BASIC utility** to the MDBASIC cartridge,
reached through the existing **CTRL+RESTORE** entry point. Today CTRL+RESTORE opens
the docs pager directly. The idea: CTRL+RESTORE first shows a tiny **function-key
menu** (F1 = docs pager, F3 = renumber/move tool), then conditionally loads and runs
the chosen module.

**Why this architecture is the right (and essentially only) one:** the 16K image is
100% full — `mdbasic.lst` ends at `$bffd`, only 2 bytes of padding remain
(`mdbasic.asm:9440`), and the token space `$cb–$ff` is fully used. New BASIC keywords
are therefore impossible without a disruptive redesign. Delivering the tool as a
cart-bank module launched from the CTRL+RESTORE NMI costs **zero image bytes** — the
same pattern the docs pager already proves.

**Headroom (verified):** bank 3 has ~3.2 KB free; Magic Desk allows 128 banks and the
cart currently uses 42, so **~86 banks (~700 KB) are free**. The tool needs **one**
new code bank (no data banks). `$c000–$cfff` (4 KB, free when graphics is inactive) is
the run/scratch area, exactly as the pager uses it.

**Scratch decision:** the tool works **in place, no REU**. MDBASIC already renumbers in
place: the built-in `RENUM` keyword (`renumer` at `mdbasic.asm:9260`) walks the program,
updates `GOTO/GOSUB/ON/ERRL=` references, and **resizes lines in place** when a
reference's digit count changes (`inc2d`/`dec2d` shuffle the program a byte and adjust
`VARTAB`). `DELETE` (`mdbasic.asm:2032`) shows the in-place block-move pattern; `LINKPRG`
($a533) and `FINDLN` ($a613) rebuild links / find lines. Validation is a **pre-flight
pass that rejects a bad operation before mutating anything**, so no rollback/REU is
needed and the tool runs on any stock C64.

## Architecture

**Refactor `docs_help.asm` → `menu.asm`** — the single CTRL+RESTORE front door. It keeps
the existing `$033c` NMI gate (RUN/STOP+RESTORE → break via `REALGONE`; plain RESTORE →
editor-mode reset; CTRL+RESTORE → open), and on the CTRL path it now presents a small
**F1/F3 menu** and **bootstraps the chosen tool** (docs pager **or** renum tool) using the
same page-bank → copy-to-`$c000` → `JSR` mechanism the handler already uses. This removes
the awkward separate "renum_menu" module: there is one menu concept, correctly named.

Memory layout inside `$c000–$cfff` during a CTRL+RESTORE session:
- `$c000–$cbff` — the active tool (docs pager **or** renum tool), 3 KB, one at a time.
- `$cc00–$ccff` — screen snapshot (`SCRBUF`, docs pager already uses this).

Flow (`menu.asm`):
1. Gate as today (SCNSTOP → STOP test → CTRL test).
2. On CTRL: draw a one-line prompt (`F1 DOCS  F3 RENUM  STOP EXIT`) and read a key via
   `GETIN`. (Restore `KEYLOG`→`$eb48` + blink-off for the read, per docs-pager-feature
   memory.)
   - **F1** → page bank 3, copy pager `$8000→$c000` (3 KB), page out, `JSR $c000`
     (pager saves/restores the screen itself).
   - **F3** → page `RENUM_BANK`, copy tool `$8000→$c000`, page out, `JSR $c000`.
   - **RUN/STOP** → skip straight to exit.
3. `jmp $fe72` (NMI tail / RTI) — the same clean return the pager uses; the editor
   resumes. RUN/STOP inside a launched tool returns here (→ RTI to the editor), i.e. one
   menu per CTRL+RESTORE (it is not re-shown after a tool exits).

**Size budget:** the menu gate + one-line prompt + key read + shared dispatch copy loop
should fit the `$033c` cassette buffer (~188 B usable below `REALGONE` at `$03f8`; the
current handler is 75 B). If it overflows during implementation, relocate only the
menu-draw/key portion to run at `$cd00` (copied from a bank), keeping the file `menu.asm`
and the `$033c` stub minimal — an internal detail, not a second public module.

### Shared "return to BASIC" — keep it minimal, no flag

The actual hand-back to the editor — `jmp $fe72` (NMI RTI tail) — is **already centralized
in `menu.asm`**: each tool ends with `RTS`, and the menu does the RTI. That is the real
return-to-BASIC step and needs no duplication or flag protocol.

The rest of the pager's exit (`docs_pager.asm:409-475`) is **not** shared code: it mirrors
the pager's own entry snapshot (`savnmi/savkey/savbln/savbdr/savbg/savfg/savhib/savturbo/
sav01`) to restore the user's screen pixel-perfect — a read-only-viewer policy the renum
tool does not want (it changes the program). So each tool owns its own entry/exit
snapshot. The only genuinely reusable, policy-free bit is the ~25-byte "canonical text
mode + VIC bank 0 + restore `$01`" epilogue, which is itself lifted from `SCREEN 0`'s
`pgzero` in `mdbasic.asm`; the **new** renum tool reuses that idiom directly. **Leave the
tested pager exit untouched** — do not refactor it through the menu (it would entangle two
different screen policies and risk the U64 cursor-race fix guarded by
`vice_docs_cursor_test.py`).

## Renumber/move tool (`renum_tool.asm`, assembled at `$c000`, ≤3 KB)

A full-screen UI **that runs as a REPL loop**: top line is a command input; bottom rows
show command syntax and the result/error of the last operation. After a command (success
**or** failure) the tool **stays open** — it reports the outcome and waits for the next
command. Only `RUN/STOP` leaves: it restores the screen and returns to BASIC (through
`menu.asm`'s RTI tail, like the pager). On a successful `r`/`m` the tool `LINKPRG`s and
resets `TXTPTR`/does a `CLR` internally so the program stays consistent, but keeps the
user in the tool.

Reuse the existing primitives rather than reinventing them: the reference-walk +
in-place resize logic in `renumer`/`replac`/`inc2d`/`dec2d` (`mdbasic.asm:9260–9396`),
the block-move pattern in `delete` (`mdbasic.asm:2032`), plus `LINKPRG`/`FINDLN`.
(Those routines run with BASIC ROM paged out — `dec R6510` — as `renumer` already does.)

### `r [<increment>] [<start>] [<end>]` — partial renumber
- Defaults: `increment=10`, source lower bound `0`, `end=63999`.
- **Source set S** = existing lines whose number is in `[start_or_0, end]`.
- **New numbering base** = `start` if `start` was given, else `increment`; assign
  `base, base+inc, base+2·inc, …` to the lines of S in order. Lines outside the range
  keep their numbers.
- Renumbering is done **without physically moving lines** (headers are 2-byte binary, so
  changing them is size-neutral; only reference-digit changes resize, handled in place).
- **Pre-flight validation — abort with an error, no mutation, if any of:**
  - a new number would exceed `63999`;
  - a new number equals a kept (non-renumbered) line's number (**overwrite**);
  - the new numbers would break ascending memory order — since the block is not
    physically moved, every new number must stay **>** the kept line immediately before
    the block in memory and **<** the kept line immediately after it.

### `m <start> <end> <destination>` — move a block (all args required)
- `delta = destination − start`; each moved line's new number = `num + delta`.
- **Fail (no mutation) if:** `end ≤ start`; any new number `> 63999` (or `< 0`); or any
  new number collides with a **non-moved** line — **except** lines inside the vacated
  `[start,end]` window (self-overlap is allowed, e.g. `m 1 100 50` → `50–150` when
  nothing else occupies `101–150`).
- On success: rewrite **all external `GOTO/GOSUB/ON/ERRL=` references** to moved lines
  (`num → num+delta`, reusing the `renumer` reference walk), renumber the block headers
  (`+delta`), then **physically relocate the block** to its sorted position (in-place
  array rotation of the span between the old and new positions — no scratch buffer, like
  `delete`'s byte copy but rotating), then `LINKPRG`.

## Build / packaging

- Rename `docs_help.asm` → `menu.asm` (front-door gate + F1/F3 menu + dispatch). One new
  source file: `renum_tool.asm` (runs at `$c000`). No separate menu module.
- `tools/make_crt.py`: append the **renum tool** as a **new last bank** (`RENUM_BANK`,
  after the doc-data banks) so `DATA_BANK0=4` and the pager's bank math are unchanged; add
  a `--renum` input and pass `RENUM_BANK` to the handler/menu. Rename the existing
  `--handler` wiring to reflect `menu.asm`. Keep `PAGER_MAX`/handler copy-count invariants
  in sync (docs-pager memory notes this coupling).
- `tools/build_disk.sh` / `compile.sh`: assemble `renum_tool.asm` and the renamed
  `menu.asm`, and pass them to `make_crt.py` alongside `--pager/--index/--data`.
- Reuse the existing `docsflag` gate in `boot.asm` to install the menu handler (it already
  copies the handler from bank 3 `$9800` to `$033c`); the same flag now enables the menu.

## Critical files

- `menu.asm` *(renamed from `docs_help.asm`)* — `$033c` NMI gate + F1/F3 menu + dispatch
  to docs pager or renum tool.
- `renum_tool.asm` *(new)* — the renumber/move REPL UI + logic at `$c000`.
- `tools/make_crt.py` — bank layout (`INDEX_BANK`, `DATA_BANK0`, add `RENUM_BANK`);
  `doc_banks()`/`build_crt()`.
- `boot.asm` — loader; verify the handler-copy length still covers the grown `menu.asm`.
- `mdbasic.asm` — reuse targets: `renumer`/`replac`/`inc2d`/`dec2d` (9260–9396),
  `delete` (2032), and ROM `LINKPRG`/`FINDLN`.

## Verification

- **Assemble first:** `tmpx -l mdbasic.lst -i mdbasic.asm -o mdbasic.prg` and assemble
  the two new modules; then `tools/build_disk.sh` to produce the `.crt`.
- **New harness** `tools/vice_renum_test.py` (model on `tools/vice_docs_test.py`): inject
  a known BASIC program, `SYS` to the tool's entry **past** the CTRL/STOP gate (parse the
  address from the `-l` listing via `label_addr`, as the docs test does — the RESTORE NMI
  and CTRL-held can't be injected), drive `r …`/`m …` via the kernal key buffer, and
  assert the resulting program bytes in `$0801…VARTAB` (line links, line numbers, updated
  `GOTO` references). Cover: default `r`, ranged `r`, overflow reject, collision reject,
  a valid `m`, self-overlap `m`, and `end ≤ start` reject (each failure must leave the
  program byte-identical). Also assert the **REPL** behavior: after a successful command
  the tool stays open (a second command in the same session applies), and only RUN/STOP
  returns to BASIC.
- **Regressions:** `tools/vice_docs_test.py` (F1 still opens the pager; sprite_timing
  still reaches DONE) and the docs cursor/clobber tests must stay green.
- **Menu path:** add a check that CTRL+RESTORE → F1 reaches the pager and → F3 reaches the
  renum tool (drive via injected keys; the gate itself remains untested, as with docs).
- **Hardware:** `tools/build_disk.sh` then mount the fresh `.d64`/`.crt` on the Ultimate 64
  and manually confirm the menu, a renumber, a move, and RUN/STOP-exit on real hardware.
