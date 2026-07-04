# Command Recall (Ctrl+B) — implementation plan

Status: **DESIGN, not started.** Hand-off for a fresh session. Everything below was
verified against the current tree (branch `crt-docs`) during design.

## Goal

Recall previously-executed **direct-mode** commands. Pressing **Ctrl+B** types the
most recent direct command at the cursor; pressing it again types the next-older one,
walking back through history and wrapping to the newest after the oldest.

This is a **cartridge-only** feature. It adds **zero bytes to the 16K MDBASIC image**
(the image assembles to a full `$8000-$BFFF`, no slack — verified) and does **not**
lower BASIC memory. Code lives in unused low RAM; the history buffer lives in the
`$CC00` gap. It is installed entirely by the cart loader (`boot.asm` + a new cart
bank), exactly like the docs pager.

### Behaviour decision (locked)

Each Ctrl+B **clears the current logical input line first**, then drips the recalled
command into its place (chars typed through the keyboard buffer, like a function-key
macro). So each press *replaces* whatever is on the line with the next command in the
walk — the cycle-through-history UX from the original request. Clearing uses a KERNAL
editor routine that MDBASIC already calls (`$E9FF`, see component 3 and
`mdbasic.asm:3622`/`2114`); this is a small, proven addition, not a rewrite.

## Why this fits (the tight-space analysis)

- **Image is full.** `tmpx` writes the complete 16K (`$8000-$9FFD` + `$A000-$BFFF`).
  No in-image code. All new code is copied to RAM at boot from a cart bank.
- **Can't lower BASIC RAM** and the `$C000` block is contested:
  - `$C800-$CBFF` = bitmap-mode video matrix + sprite pointers (`mdbasic.asm:3822`).
  - `$CE00-$CFFF` = disk I/O in/out buffers (`mdbasic.asm:8519`).
  - `$C000-$CBFF` = docs viewer copy target (`docs_help.asm:74`, 12 pages).
  - `$E000-$FF3F` = hi-res bitmap (VIC bank 3).
  - **`$CC00-$CDFF` (512 B) is the one untouched gap** — safe from BASIC, graphics,
    disk, and docs. Only risk: user POKE/ML there (standard `$C000` caveat).
- **Code homes** (normally-mapped low RAM, unused by MDBASIC):
  - `$038E-$03F7` = **106 B** cassette-buffer tail. `docs_help` occupies `$033C-$038D`
    (82 B, verified by assembling `docs_help.asm`); the `REALGONE` stash sits at
    `$03F8`. MDBASIC uses `$0330-$033B` (ILOAD/ISAVE vectors + IRQ/ERR/KEY temps) but
    nothing in `$038E-$03F7`.
  - `$02A7-$02FF` = **89 B** KERNAL free scratch, unused by MDBASIC.
  - Total ≈ **195 B** for code + control variables. Estimated need ≈ 180 B — fits.
    If it spills ~20-30 B, borrow from the top of the `$CC00` buffer (one fewer slot).

**Bottom line:** code → cassette tail + `$02A7` scratch; buffer → full 512 B at
`$CC00`. They do not compete.

## Memory map (proposed)

| Range | Bytes | Use |
|---|---|---|
| `$CC00-$CDFF` | 512 | History ring buffer: **8 slots × 64 B** (tunable equates) |
| `$038E-$03CF` (approx) | ~66 | Capture shim + Ctrl+B/drip logic (in cassette tail) |
| `$02A7-$02BF` (approx) | ~25 | Overflow code + control variables |

Control variables (~7 bytes, place in the `$02A7` block, **not** in the 512 B buffer):

- `wr_slot`  — next slot index to write (0..N-1), ring
- `n_saved`  — number of valid entries (0..N)
- `rc_idx`   — recall walk position
- `drip_ptr` (2) — pointer into the slot currently being typed out
- `drip_rem` — bytes left to drip
- `rc_flag`  — non-zero while a recall is actively dripping

Tunable equates: `SLOT_SZ = 64`, `N_SLOTS = 8` (8×64 = 512). Most direct commands are
short; if you prefer more depth, `SLOT_SZ = 40`, `N_SLOTS = 12` also works. Commands
longer than `SLOT_SZ-1` are truncated on capture (document as a limitation).

## The three code components

### 1. Capture shim — hooks `ICRNCH` (`$0304`, → `toknew`)

`toknew` (`mdbasic.asm:645`) crunches **every** entered line, and sees the **raw
ASCII** still in `BUF` (`$0200`) before tokenising — exactly the text we want.

Shim logic (runs *before* `toknew`, then falls through to it):

```
; skip leading spaces in BUF
; peek first non-space char:
;   $00 (empty line)        -> skip capture, jmp toknew
;   '0'..'9' (leading digit) -> program-line entry/deletion, skip, jmp toknew
;   else                     -> direct command: capture it
; copy BUF[0..] up to $00 terminator into slot[wr_slot], max SLOT_SZ-1 bytes,
;   NUL-terminate
; wr_slot = (wr_slot + 1) mod N_SLOTS
; if n_saved < N_SLOTS: inc n_saved
; rc_idx = wr_slot           ; reset recall walk to "newest" position
; jmp toknew
```

Note: no `CURLIN` check needed — the leading-digit test distinguishes program-line
edits (which start with a line number) from direct commands.

### 2. Ctrl+B trigger + drip — hooks `KEYLOG` (`$028F`, → `keychk`)

`keychk` (`mdbasic.asm:4959`) is the IRQ keyboard-decode hook MDBASIC already owns for
function keys. `KEYLOG` is called from the KERNAL keyscan on **every IRQ** (~60 Hz),
which is the same cadence the existing `keypump` uses to drip function-key strings.

The shim runs *before* `keychk` each IRQ and does two jobs, then `jmp keychk`:

```
; --- (a) detect Ctrl+B press to START a recall ---
; if SHFLAG ($028d) == 4 (CTRL only) AND SFDX ($cb) == B's matrix code:
;     if n_saved > 0:
;         jsr clear_input_line          ; component 3 — blank line, cursor to its start
;         set up drip from slot[rc_idx]:
;             drip_ptr = &slot[rc_idx]; drip_rem = length; rc_flag = 1
;         rc_idx = (rc_idx - 1) mod n_saved   ; walk to older, wrap to newest
;     ; swallow the key so it doesn't also type Ctrl+B ($02):
;     ; set SFDX/LSTX so the KERNAL decode produces nothing this tick
;
; --- (b) drip one char per IRQ while a recall is active ---
; if rc_flag != 0 AND NDX ($c6) == 0:        ; keyboard buffer empty
;     push *drip_ptr into KEYD ($0277), inc NDX
;     drip_ptr++; if --drip_rem == 0: rc_flag = 0
;
; jmp keychk
```

- **B's matrix code**: `SFDX` for `B` is **`$1C` (28)** in the standard C64 matrix.
  Confirm empirically (read `$CB` while holding B) or from the KERNAL decode table.
  For Ctrl+**P** instead, use P's code — that is the *only* change to switch keys.
- **Swallowing the key**: without care, the KERNAL will also decode Ctrl+B to PETSCII
  `$02`. Simplest suppression: after detecting the combo, force the decode to "no key"
  for this tick (e.g. set `LSTX`/`SFDX` to `$40`/none, mirroring how the KERNAL treats
  no-key). Verify on hardware/VICE that no stray `$02` leaks into the line.
- Dripping into `KEYD` when `NDX==0` reuses the exact mechanism `keypump`
  (`mdbasic.asm:5040`) uses, so a full 80-char line flows in past the 10-byte buffer
  limit — no line-clear, chars land at the cursor "just like function keys." We do the
  drip **inside the keychk shim** rather than chaining `keypump`, so no edit to the
  in-image IRQ chain (`mdbirqhdl`) is needed.

### 3. Clear the current input line (`clear_input_line`)

Called once when a recall starts (from the keychk shim, so it runs in the keyscan IRQ
context — verify no editor re-entrancy issue; the main thread is idle in the input loop
at that moment). Uses KERNAL editor routines MDBASIC already relies on:

- `$E9FF` — clear one physical screen line, line number in `X`. MDBASIC's own `csrclr`
  (`mdbasic.asm:3622`) is literally `ldx TBLX : jsr $e9ff`, and `mdbasic.asm:2114`
  clears two lines the same way.
- `$E56C` — recompute the start-of-line screen pointer (`PNT`) from `TBLX`.
- `$E566` — home the cursor (used at `mdbasic.asm:2127`).
- `PLOT` (carry set = read) returns `X` = physical line, `Y` = logical column.

Recommended sequence:

```
clear_input_line
; read cursor position
    sec
    jsr PLOT                 ; X = physical line, Y = logical column
; find the START physical line of this logical line via the line-link table
; LDTB1 ($D9): high bit set = start of a logical line, clear = continuation
findstart
    lda $d9,x                ; LDTB1,x
    bmi atstart              ; bit7 set -> x is the logical line's first row
    dex
    bpl findstart
atstart
; clear the physical line(s) of the logical line (1 or 2 rows on a 40-col screen)
    txa : pha                ; remember start row
    jsr $e9ff                ; clear start row (X)
    ; if next row is a continuation (LDTB1,x+1 bit7 clear), clear it too:
    inx
    lda $d9,x
    bmi done1
    jsr $e9ff
done1
; home cursor to column 0 of the logical line
    pla : tax                ; start row
    stx TBLX                 ; $d6
    lda #0
    sta PNTR                 ; $d3 logical column
    jsr $e56c                ; set PNT for TBLX
    ; make the physical cursor match (PLOT with carry clear, or the editor's
    ; own reposition) so the dripped chars land at column 0
    rts
```

Then the drip (component 2b) types the recalled text at the now-blank line start.
Simpler fallback if wrap-handling proves troublesome: clear just the cursor's physical
line exactly like `csrclr` (`ldx TBLX : jsr $e9ff`) — correct for commands that fit on
one physical line (≤40 chars), which is the common case.

## Install (boot loader changes) — the zero-image-cost trick

`newvec` (`mdbasic.asm:5784`) re-installs the vector overrides on cold start **and on
every STOP+RESTORE break** (`brkirq` → `newvec`, `mdbasic.asm:4951`). So patching the
live `$0304`/`$028F` vectors directly would be undone by a break. Instead, patch
`newvec`'s **immediate operands** in the RAM image so it installs *our* shims — this
survives breaks. `boot.asm` already does exactly this pattern (it rewrites the IGONE
operand bytes and repoints `$8002`; see its header comment).

Operands to patch in the in-RAM image:

- `newvec` `lda #<toknew` / `lda #>toknew` (`mdbasic.asm:5799-5802`, sets `ICRNCH`)
  → point at **capture shim** address. Shim ends with `jmp toknew`.
- `newvec` `lda #<keychk` / `lda #>keychk` (`mdbasic.asm:5815-5818`, sets `KEYLOG`)
  → point at **keychk shim** address. Shim ends with `jmp keychk`.

Resolve `toknew` / `keychk` addresses from `mdbasic.lst`; the shims tail-call them by
absolute address.

Boot sequence additions (in `boot.asm`, mirroring the docs_help copy at
`boot.asm:108`):

1. Copy the new recall module from its cart bank into its RAM homes (`$038E-…` and
   `$02A7-…`).
2. Apply the four operand patches above.
3. Zero the control vars (`n_saved=0`, `wr_slot=0`, `rc_flag=0`). Buffer slots need no
   pre-clear (capture writes NUL-terminated).

`tools/make_crt.py` bank layout must gain the recall module (new/extended bank);
follow how the docs pager banks are appended (see its docstring and the
`--pager/--index/--data/--handler` handling).

## Assembly / build notes

- New source file, e.g. `cmd_recall.asm`, assembled at its RAM origin(s). Because the
  code spans two non-contiguous homes (`$038E` tail + `$02A7` scratch), either use two
  `*=` segments in one file or split into two tiny objects. Keep the capture shim and
  the keychk shim each fully within one segment so the `jmp` tail-calls are simple.
- Re-check `docs_help`'s end (`$038D`) hasn't grown before trusting `$038E` as free.
- `TMPx has no operator precedence` — parenthesise any `base + i*SLOT_SZ` address math
  (see the `tmpx-no-operator-precedence` memory).

## Testing (add to `tools/`)

Model on `tools/vice_prg_test.py` / `tools/vice_docs_test.py`:

1. Boot the cart headless in VICE, install MDBASIC.
2. Enter a direct command (e.g. `PRINT 123`) so the capture shim fills a slot. Enter a
   second (`PRINT 456`).
3. Simulate Ctrl+B. Two options:
   - Poke `SHFLAG=$04` and `SFDX=$1C` for one keyscan (drive via the binary monitor), or
   - Call the recall-start entry directly, then let IRQs run.
4. Poll `KEYD`/`NDX` and/or screen RAM for the recalled text (`PRINT 456`, then
   `PRINT 123` on a second press), and confirm wrap.
5. Regression: run the existing `sprite_timing` and docs-pager tests unchanged (the
   feature must not perturb the IRQ or the RESTORE NMI path).

## Risk register

- **Key suppression**: the fiddly bit is stopping Ctrl+B from also typing `$02`.
  Prototype this first and verify no stray char.
- **`$CC00` buffer**: not protected from user ML/POKE — acceptable, documented.
- **Truncation** of commands longer than `SLOT_SZ-1` — documented limitation; consider
  `SLOT_SZ=64` to cover most.
- **Break survival**: verified the operand-patch approach survives STOP+RESTORE;
  confirm after implementation that a break then Ctrl+B still recalls.
- **Line-clear from IRQ**: `clear_input_line` calls editor routines (`PLOT`/`$E9FF`/
  `$E56C`) from the keyscan IRQ. Verify no re-entrancy glitch with the main-thread input
  loop (expected safe — main thread is idle waiting for a key at that moment).
- **Two-row logical lines**: `$E9FF` clears one physical row; a >40-char command wraps
  to two rows. Handle both rows (link-table walk in component 3) or accept the ≤40-char
  fallback.

## Build order (recommended)

0. **Branch first.** Create a working branch off `crt-docs`:
   `git switch crt-docs && git switch -c command-recall` (or
   `git checkout crt-docs && git checkout -b command-recall`). Do all work there; open
   the PR against `crt-docs` (or `master`, per the release flow at the time).
1. Capture shim + ring buffer + a debug peek (POKE the slot to screen) — prove capture.
2. Ctrl+B detection + key suppression + `clear_input_line` + drip replay — prove
   clear-and-type-in-place.
3. `boot.asm`/`make_crt.py` wiring into a cart bank — prove end-to-end from `.crt`.
4. VICE test + README/`mdbasic.pdf` doc note.

## Anchors (current tree)

- `ICRNCH`=`$0304`, `IQPLOP`=`$0306`, `IGONE`=`$0308`, `KEYLOG`=`$028F`
- `BUF`=`$0200`, `KEYD`=`$0277`, `NDX`=`$c6`, `SFDX`=`$cb`, `LSTX`=`$c5`,
  `SHFLAG`=`$028d`, `QTSW`=`$d4`
- `toknew` `mdbasic.asm:645` · `keychk` `mdbasic.asm:4959` · `keypump` `mdbasic.asm:5040`
  · `newvec` `mdbasic.asm:5784` (ICRNCH set 5799-5802, KEYLOG set 5815-5818) ·
  `brkirq`→`newvec` `mdbasic.asm:4951`
- `docs_help.asm` occupies `$033C-$038D`; free tail `$038E-$03F7`; `REALGONE`=`$03F8`
- Buffer gap `$CC00-$CDFF` (512 B)
