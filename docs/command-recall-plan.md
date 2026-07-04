# Command Recall (Ctrl+B) — implementation plan

Status: **DESIGN, not started.** Hand-off for a fresh session. Originally verified
against branch `crt-docs`; **revised 2026-07-03 after a full review** that re-checked
every RAM claim against the tree (including assembling `docs_help.asm` and
`docs_pager.asm` for real addresses). The review found and fixed: two `$CC00`
conflicts, a missing trigger edge-detect, a missing direct-mode gate, a ring-walk
order bug, and a safer/smaller line-clear design. All fixes are folded in below.

## Goal

Recall previously-executed **direct-mode** commands. Pressing **Ctrl+B** types the
most recent direct command at the cursor; pressing it again types the next-older one,
walking back through history and wrapping to the newest after the oldest.

This is a **cartridge-only** feature. It adds **zero bytes to the 16K MDBASIC image**
(the image assembles to a full `$8000-$BFFF`, no slack — verified) and does **not**
lower BASIC memory (**hard constraint** — a MEMSIZ steal was considered in review and
explicitly rejected). Code lives in unused low RAM; the history buffer lives at
`$CC00`, shared with two other users and guarded (see below). It is installed
entirely by the cart loader (`boot.asm` + cart bank space), exactly like the docs
pager.

### Behaviour decision (locked)

Each Ctrl+B **clears the current logical input line first**, then drips the recalled
command into its place (chars typed through the keyboard buffer, like a function-key
macro). So each press *replaces* whatever is on the line with the next command in the
walk. Clearing is done by **dripping DEL characters through the keyboard buffer**
ahead of the recalled text — the main-thread screen editor does all the work (blink,
wrapped logical lines, `PNT` bookkeeping), so nothing screen-related runs in IRQ
context. See component 3 for why this replaced the earlier `$E9FF` design.

## Why this fits (the tight-space analysis)

- **Image is full.** `tmpx` writes the complete 16K (`$8000-$9FFD` + `$A000-$BFFF`).
  No in-image code. All new code is copied to RAM at boot from a cart bank.
- **Can't lower BASIC RAM** (hard constraint) and the `$C000` block is contested:
  - `$C800-$CBFF` = bitmap-mode video matrix + sprite pointers (`mdbasic.asm:3822`).
  - `$CE00-$CFFF` = RS-232/disk I/O in/out buffers (`mdbasic.asm:8519`).
  - `$C000-$CB9F` = docs viewer copy target (currently assembles to exactly
    `$C000-$CB9F` — only `$60` bytes of slack below `$CC00`, so nothing can be slid
    down to free the gap).
  - `$E000-$FF3F` = hi-res bitmap (VIC bank 3).
  - **`$CC00-$CDFF` (512 B) is the best available gap but it is NOT untouched.**
    Review found two consumers the original design missed; both are handled with
    cheap guards rather than moving the buffer:
    1. **Docs pager screen snapshot**: `SCRBUF = $cc00` (`docs_pager.asm:64`) saves
       1K of screen RAM (`$CC00-$CFFF`) on every CTRL+RESTORE entry and restores it
       on exit — it overwrites the whole history buffer while `n_saved` would still
       claim entries exist. **Guard: zero `n_saved` when the docs pager opens**
       (history is lost when you view docs — documented limitation).
    2. **SCREEN page 4** puts the text video matrix at `$CC00-$CFFF`
       (`page`/`pagee`, `mdbasic.asm:3105-3128`; `HIBASE` page4=`$cc`,
       `mdbasic.asm:9226`). Capture would write typed commands as visible garbage
       onto the display. **Guard: capture and trigger both no-op while
       `HIBASE == $cc`** (recall disabled on screen page 4 — documented limitation).
    - Remaining risk: user POKE/ML there (standard `$C000` caveat).
- **Code homes** (normally-mapped low RAM, unused by MDBASIC):
  - `$038E-$03F7` = **106 B** cassette-buffer tail. `docs_help` occupies `$033C-$038D`
    (82 B, **re-verified by assembling `docs_help.asm`**); the `REALGONE` stash sits
    at `$03F8`. MDBASIC uses `$0330-$033B` (ILOAD/ISAVE vectors + IRQ/ERR/KEY temps)
    but nothing in `$038E-$03F7`. **Note:** the docs-pager guard (install step 3)
    grows `docs_help` by a few bytes — re-derive the free-tail start from the grown
    handler's end, don't hardcode `$038E`.
  - `$02A7-$02FF` = **89 B** KERNAL free scratch. Verified: MDBASIC's only equates in
    the `$02Ax` range are `ENABL` `$02A1` and `PALNTSC` `$02A6`, both below `$02A7`.
  - Total ≈ **195 B** for code + control variables. Estimated need ≈ 180-200 B —
    the DEL-drip clear (−~45 B vs the old design) and the dropped drip variables
    roughly pay for the added edge flag, gates, and dedup. If it spills ~20-30 B,
    borrow from the top of the `$CC00` buffer (one fewer slot).

**Bottom line:** code → cassette tail + `$02A7` scratch; buffer → 512 B at `$CC00`
with the two guards above. They do not compete.

## Memory map (proposed)

| Range | Bytes | Use |
|---|---|---|
| `$CC00-$CDFF` | 512 | History ring buffer: **8 slots × 64 B** (tunable equates) |
| tail after `docs_help` (≈`$0393-…`) | ~66 | Capture shim + Ctrl+B/drip logic (in cassette tail) |
| `$02A7-$02BF` (approx) | ~25 | Overflow code + control variables |

Control variables (**7 bytes**, place in the `$02A7` block, **not** in the 512 B
buffer):

- `wr_slot`  — next slot index to write (0..7), ring
- `n_saved`  — number of valid entries (0..8); zeroed by the docs-pager guard
- `rc_off`   — recall **age offset** (0 = newest), wraps at `n_saved`
- `drip_ptr` (2) — pointer into the slot being typed out; **hi byte `$00` = drip
  idle** (slot pages are `$CC`/`$CD`, never zero) — this sentinel replaces the old
  `rc_flag`
- `del_rem`  — DEL characters still to drip before the text
- `held`     — Ctrl+B combo was down last tick (edge-detect flag)

Review simplifications vs the original var set: `drip_rem` is gone (slots are
NUL-terminated, the drip runs to the NUL exactly like `keypump` does with its
zero-terminated strings), and `rc_flag` is folded into `drip_ptr+1`.

Tunable equates: `SLOT_SZ = 64`, `N_SLOTS = 8` (8×64 = 512). **Keep the power of
two** — the ring arithmetic becomes `AND #7` masks and slot addressing is two shifts;
a 12×40 layout costs real bytes in mod/multiply code. Commands longer than
`SLOT_SZ-1` are truncated on capture (documented limitation; the dripped text is
visible before RETURN, so it's not silent).

## The three code components

### 1. Capture shim — hooks `ICRNCH` (`$0304`, → `toknew`)

`toknew` (`mdbasic.asm:645`) crunches **every** entered line, and sees the **raw
ASCII** still in `BUF` (`$0200`) before tokenising — exactly the text we want.
Capture happens *before* execution, so even commands with syntax errors are
recallable (a feature — recall to fix the typo).

Shim logic (runs *before* `toknew`, then falls through to it):

```
; if HIBASE == $cc: skip capture, jmp toknew      ; SCREEN page 4 guard
; skip leading spaces in BUF
; peek first non-space char:
;   $00 (empty line)        -> skip capture, jmp toknew
;   '0'..'9' (leading digit) -> program-line entry/deletion, skip, jmp toknew
;   else                     -> direct command: capture it
; dedup: if n_saved > 0 and BUF matches slot[(wr_slot-1) AND 7] byte-for-byte
;   (up to the NUL): rc_off = 0, jmp toknew        ; don't store consecutive dupes
; copy BUF[0..] up to $00 terminator into slot[wr_slot], max SLOT_SZ-1 bytes,
;   NUL-terminate
; wr_slot = (wr_slot + 1) AND 7
; if n_saved < N_SLOTS: inc n_saved
; rc_off = 0                  ; reset recall walk to "newest"
; jmp toknew
```

Notes:
- No `CURLIN` check needed **on the capture side** — the leading-digit test
  distinguishes program-line edits from direct commands. (The *trigger* side does
  need a direct-mode gate; see component 2.)
- The dedup (~20 B) matters for usability: recall + RETURN re-captures the same
  text, so without it the ring fills with duplicates and cycling degenerates.

### 2. Ctrl+B trigger + drip — hooks `KEYLOG` (`$028F`, → `keychk`)

`keychk` (`mdbasic.asm:4959`) is the keyboard-decode hook MDBASIC already owns for
function keys. `KEYLOG` is jumped through by the KERNAL `SCNKEY` on **every IRQ**
(~60 Hz), even with no key down (`SFDX` = `$40`).

The shim runs *before* `keychk` each IRQ, then `jmp keychk`:

```
; --- (a) Ctrl+B detection, edge-gated ---
; if SHFLAG ($028d) == 4 (CTRL only) AND SFDX ($cb) == $1C (B):
;     sta-swallow: SFDX = $40                  ; always, so no $02 is ever typed
;     if held != 0: goto drip                  ; still held from a previous tick
;     held = 1                                 ; new press — trigger once
;     ; gates: all must pass or the press is swallowed but ignored
;     if MSGFLG ($9d) == 0: goto drip          ; program running — same gate keychk uses
;     if MDBIRQ ($0313) bit2 set: goto drip    ; function-key pump active, don't interleave
;     if HIBASE == $cc: goto drip              ; SCREEN page 4 — buffer is the display
;     if n_saved == 0: goto drip
;     ; --- start a recall ---
;     lda #0 : sta QTSW : sta INSRT : sta NDX  ; kill quote/insert mode, flush pending keys
;     slot = (wr_slot - 1 - rc_off) AND 7      ; compute BEFORE advancing (see note)
;     rc_off = rc_off + 1; if rc_off == n_saved: rc_off = 0   ; wrap oldest -> newest
;     drip_ptr = &slot[slot]                   ; hi byte becomes $cc/$cd -> drip active
;     del_rem = PNTR ($d3)
;     if LDTB1[TBLX] ($d9,x) bit7 clear: del_rem += 40   ; cursor on a continuation row
; else:
;     held = 0                                 ; combo released — re-arm edge detect
;
; --- (b) drip while active (drip_ptr hi != 0), fill the buffer each tick ---
; drip:
; while NDX ($c6) < XMAX ($0289):              ; up to 10 chars per IRQ, ~600 cps
;     if del_rem > 0: push $14 (DEL) into KEYD ($0277), inc NDX, dec del_rem
;     else: lda (drip_ptr):
;         if 0: drip_ptr+1 = 0, break          ; NUL — drip done
;         push into KEYD, inc NDX, inc drip_ptr
;
; jmp keychk
```

Design notes (each of these was a review finding — don't drop them):

- **Edge detection is mandatory.** `SCNKEY` re-reads the matrix every IRQ, so `SFDX`
  stays `$1C` for every tick the key is held — and MDBASIC sets `RPTFLAG = $80`
  ("all keys repeat", in `newvec`). Without the `held` flag the shim retriggers at
  ~60 Hz and cycles the whole history in a fraction of a second. `LSTX` **cannot**
  be used for edge detect: the swallow makes `LSTX` become `$40` each tick.
- **Direct-mode gate**: without the `MSGFLG` check, Ctrl+B during a running program
  clears whatever line the cursor is on and feeds the recalled command into any
  pending `GET`/`INPUT`. `keychk` itself gates function keys on `MSGFLG`
  (`mdbasic.asm:4960`) — mirror it for consistent semantics.
- **F-key pump guard**: if `MDBIRQ` bit 2 is set (`mdbasic.asm:4964`), `keypump` is
  dripping a function-key macro into the same `KEYD`; starting a recall then would
  interleave the two streams.
- **Swallow verified against `keychk`**: with `SHFLAG` = 4, `keychk` falls through
  to `$EB48` (`nokey`, `mdbasic.asm:4968-4987`), and `SFDX` = `$40` decodes to the
  no-key `$FF` entry — no stray `$02`, no interference with the F-key path.
- **Compute the slot before advancing `rc_off`.** The original pseudocode dripped
  `slot[rc_idx]` *then* decremented, with `rc_idx` reset to `wr_slot` — since
  `wr_slot` is the next *write* position, the first press delivered an empty slot
  (ring not yet wrapped) or the *oldest* entry (wrapped), never the newest. The
  age-offset form above (`rc_off` = 0 ⇒ newest) is both correct and smaller, and
  avoids the original's mixed `mod n_saved` / ring-index arithmetic.
- **Flushing `NDX`** on trigger discards any half-delivered chars from a previous
  recall when the user presses Ctrl+B mid-drip (at worst it also eats one just-typed
  keystroke — acceptable, the line is being replaced anyway).
- **Fill to `XMAX`, not one char per tick.** At 1 char/IRQ, clearing 38 chars and
  retyping a 60-char command takes ~1.6 s; filling `KEYD` to capacity (10) each tick
  is ~10× faster for a few bytes of loop.
- Pressing Ctrl+B again mid-drip restarts cleanly: the trigger path overwrites
  `del_rem`/`drip_ptr` and re-derives the DEL count from the current (partially
  redrawn) line state.

### 3. Clearing the line = dripping DELs (design change from review)

The original design called KERNAL editor routines (`PLOT`/`$E9FF`/`$E56C`) from the
keyscan IRQ to blank the logical line. Review dropped it for three reasons:

1. **Cursor-blink corruption**: by the time the `KEYLOG` shim runs, the IRQ's blink
   phase has already executed. If `BLNON` is set, the char under the cursor is saved
   in `GDBLN`, and after moving `TBLX`/`PNTR` the next blink toggle writes that stale
   char at the *new* cursor position — a stray character at column 0.
2. IRQ re-entrancy against the main-thread editor (was flagged "verify" in the old
   risk register — now simply not a thing).
3. Size: ~45 B of positioning code vs ~12 B of DEL counting.

Instead, component 2 prepends `del_rem` DEL (`$14`) characters to the drip. The
main-thread editor processes them natively — blink, two-row logical lines, and `PNT`
bookkeeping all handled. Requirements:

- **The count must be exact**: excess DELs walk up into the previous screen line
  (the C64 editor DELs across logical-line starts). `del_rem = PNTR`, plus 40 if the
  cursor's physical row is a continuation row (`LDTB1` bit 7 clear).
- **Zero `QTSW` and `INSRT` at trigger time** (done in component 2). Deleting a
  quote does *not* clear quote mode on the C64, and in insert mode DEL prints a
  reverse character instead of deleting — either would garble the replay.
- Chars to the *right* of the cursor survive (DEL only deletes leftward). The cursor
  sits at end-of-typed-text in normal use, so this matches the common case; same
  practical coverage as the old design's single-line fallback.

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

1. Copy the recall module from cart bank 3 into its RAM homes (cassette tail +
   `$02A7-…`). **No new bank needed**: the module is ~200 B and rides in bank 3
   after the RESTORE handler blob at `$9800` (handler is 82 B; the bank has room).
2. Apply the four operand patches above.
3. **Docs-pager guard**: add `lda #0 : sta n_saved` to the `docs_help` handler's
   open-the-docs path (cart-specific concern, so it belongs in `docs_help.asm`, not
   the shared pager core). This grows the handler past `$038D` — the recall module's
   cassette-tail origin must be set from the *grown* handler's end.
4. Zero the control vars (`n_saved=0`, `wr_slot=0`, `rc_off=0`, `held=0`,
   `drip_ptr+1=0`). Buffer slots need no pre-clear (capture writes NUL-terminated).

`tools/make_crt.py` needs the recall module appended into the bank 3 payload; follow
how the `--handler` blob is placed (see its docstring).

## Assembly / build notes

- New source file, e.g. `cmd_recall.asm`, assembled at its RAM origin(s). Because the
  code spans two non-contiguous homes (cassette tail + `$02A7` scratch), either use
  two `*=` segments in one file or split into two tiny objects. Keep the capture shim
  and the keychk shim each fully within one segment so the `jmp` tail-calls are
  simple.
- Re-derive the cassette-tail origin from the assembled end of the **grown**
  `docs_help` (guard added in install step 3) — don't trust `$038E`.
- `TMPx has no operator precedence` — parenthesise any `base + i*SLOT_SZ` address
  math (see the `tmpx-no-operator-precedence` memory).

## Testing (add to `tools/`)

Model on `tools/vice_prg_test.py` / `tools/vice_docs_test.py`:

1. Boot the cart headless in VICE, install MDBASIC.
2. Enter a direct command (e.g. `PRINT 123`) so the capture shim fills a slot. Enter a
   second (`PRINT 456`).
3. Trigger a recall by **calling the recall-start entry directly** (via the binary
   monitor), then let IRQs run the drip. **Do NOT try to fake the keypress by poking
   `SHFLAG`/`SFDX`** — `SCNKEY` rewrites both from the hardware matrix at the start
   of every scan, *before* jumping through `KEYLOG`, so monitor pokes are erased
   before the shim ever sees them. The swallow and edge-detect behaviour therefore
   need one **manual VICE check**: hold Ctrl+B and confirm (a) no stray `$02`/char
   appears and (b) exactly one recall fires per press.
4. Poll `KEYD`/`NDX` and/or screen RAM for the recalled text (`PRINT 456`, then
   `PRINT 123` on a second press), confirm wrap, and confirm the line is *replaced*
   (DEL prefix worked). Also assert dedup: entering `PRINT 456` twice must store one
   slot.
5. Docs-pager guard: open and close the docs pager, then confirm Ctrl+B does nothing
   (history invalidated), and that new commands re-populate it.
6. Regression: run the existing `sprite_timing` and docs-pager tests unchanged (the
   feature must not perturb the IRQ or the RESTORE NMI path).

## Risk register

- **Key suppression + edge detect**: prototype first (build order step 2) and verify
  by hand in VICE — no stray char, one recall per press even with `RPTFLAG=$80`.
- **`$CC00` buffer sharing**: docs pager wipes it (guarded by `n_saved=0` on docs
  open) and SCREEN page 4 displays it (guarded by the `HIBASE` checks). Both are
  documented limitations. Still unprotected from user ML/POKE — acceptable,
  documented.
- **Truncation** of commands longer than `SLOT_SZ-1` — documented limitation.
- **Break survival**: the operand-patch approach survives STOP+RESTORE by design;
  confirm after implementation that a break then Ctrl+B still recalls.
- **Exact DEL count**: an over-count eats the previous screen line. The
  `PNTR` + continuation-row formula is exact for a cursor inside the logical line;
  verify against a wrapped (2-row) command in the VICE test.
- **`docs_help` growth**: the guard shifts the free-tail start; the build must derive
  the recall origin from the assembled handler end (assemble-time symbol, not a
  hardcoded address).

## Build order (recommended)

0. **Branch first.** Create a working branch off `crt-docs`:
   `git switch crt-docs && git switch -c command-recall` (or
   `git checkout crt-docs && git checkout -b command-recall`). Do all work there; open
   the PR against `crt-docs` (or `master`, per the release flow at the time).
1. Capture shim + ring buffer + a debug peek (POKE the slot to screen) — prove
   capture, dedup, and the leading-digit/HIBASE gates.
2. Ctrl+B detection + edge flag + key suppression + DEL-drip + text drip — prove
   clear-and-type-in-place, one recall per press.
3. `boot.asm`/`make_crt.py` wiring into bank 3 + the `docs_help` guard — prove
   end-to-end from `.crt`.
4. VICE test + README/`mdbasic.pdf` doc note (document: cart-only, 63-char slots,
   history cleared by docs viewer, disabled on SCREEN page 4).

## Anchors (current tree — re-verified 2026-07-03)

- `ICRNCH`=`$0304`, `IQPLOP`=`$0306`, `IGONE`=`$0308`, `KEYLOG`=`$028F`
- `BUF`=`$0200`, `KEYD`=`$0277`, `NDX`=`$c6`, `XMAX`=`$0289`, `SFDX`=`$cb`,
  `LSTX`=`$c5`, `SHFLAG`=`$028d`, `RPTFLAG`=`$028a`, `HIBASE`=`$0288`,
  `MSGFLG`=`$9d`, `MDBIRQ`=`$0313`
- Editor state: `PNTR`=`$d3`, `TBLX`=`$d6`, `LDTB1`=`$d9`, `QTSW`=`$d4`,
  `INSRT`=`$d8`, `BLNON`=`$cf`, `GDBLN`=`$ce`
- `toknew` `mdbasic.asm:645` · `keychk` `mdbasic.asm:4959` (MSGFLG gate 4960, fkey
  pump flag 4964, `nokey`→`$EB48` 4987) · `keypump` `mdbasic.asm:5040` · `newvec`
  `mdbasic.asm:5784` (ICRNCH set 5799-5802, KEYLOG set 5815-5818, `RPTFLAG=$80`
  nearby) · `brkirq`→`newvec` `mdbasic.asm:4951`
- B's matrix code: `SFDX`=`$1C` (28); CTRL-only is `SHFLAG`=4
- `docs_help.asm` assembles to `$033C-$038D` (82 B) **before** the guard is added;
  free tail runs from its (grown) end to `$03F7`; `REALGONE`=`$03F8`
- `docs_pager.asm` assembles to `$C000-$CB9F`; `SCRBUF`=`$CC00-$CFFF`
  (`docs_pager.asm:64`)
- SCREEN page 4 matrix: `pagee` `mdbasic.asm:3111`, `spage` `mdbasic.asm:9226`
- Buffer `$CC00-$CDFF` (512 B), shared per the guards above
