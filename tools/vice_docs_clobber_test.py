#!/usr/bin/env python3
"""Docs pager RAM/VIC-state test: proves the $c000-$cfff clobber AND that the
pager now exits into a canonical text mode / VIC bank 0 (no half-restored
graphics state).

The docs pager makes no attempt to preserve data in $c000-$cfff -- it assumes
that 4K block is free scratch. The RESTORE handler copies the 3K pager image to
$c000-$cbff (docs_help.asm) and the pager snapshots the $0400 text screen into
SCRBUF = $cc00-$cfff (docs_pager.asm). Only the standard $0400 screen, color RAM,
and a few registers are saved/restored; nothing in $c000-$cfff is.

But MDBASIC actively parks live video RAM there:
  * SCREEN 1-4 put the redefined-char text screen at $c000/$c400/$c800/$cc00;
  * bitmap graphics (SCREEN 5) put the color matrix at $c800-$cbe7;
  * RS-232 buffers live at $ce00-$cfff.

Phase A -- clobber: run a BASIC program that relocates live screen RAM into both
sub-regions via SCREEN, writes a sentinel byte into each, confirms the sentinels
are resident, then triggers a docs open+exit (the exact `dodocs` path a
CTRL+RESTORE press runs). After the round-trip every sentinel is gone.

Phase B -- canonical exit: enter bitmap graphics (SCREEN 5), so VMCSB / VIC bank
/ SCROLY are all non-canonical, then trigger a docs open+exit. The pager must
land back in the exact state SCREEN 0 (pgzero) produces -- VIC bank 0, VMCSB
$15 (screen $0400 + uppercase ROM charset), SCROLY text mode -- rather than the
old half-restore that put VMCSB back to its graphics value while the bank stayed
0. A graphics program recovers by re-RUNning; the machine is never left wedged
between two modes.

It reuses the cart build + synthetic-NMI stub from vice_docs_test.

    tools/vice_docs_clobber_test.py
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import vice_prg_test as harness
import vice_docs_test as docs

PORT = 6560
STUB_ADDR = docs.STUB_ADDR
SENT = 90  # sentinel byte ('Z' screen code) poked into each region

# One probe cell inside each MDBASIC-owned region that the pager overwrites.
#   $c810 -> SCREEN 3 screen / bitmap color matrix  (inside the $c000-$cbff copy)
#   $cc10 -> SCREEN 4 screen                         (inside SCRBUF $cc00-$cfff)
#   $ce10 -> RS-232 input-buffer page               (inside SCRBUF)
PROBES = {"page3_c810": 0xC810, "page4_cc10": 0xCC10, "rs232_ce10": 0xCE10}

# BASIC driver: relocate the video matrix into $c8xx (page 3) and $ccxx (page 4)
# with real SCREEN commands, return to normal text, then poke a sentinel into
# each region. The SCREEN calls are what make these addresses live MDBASIC RAM;
# the POKEs stand in for a program writing its screen/graphics data there.
BASIC = [
    "10 SCREEN CLR 3",   # redefined-char screen -> $c800 (also fills via clear)
    "20 SCREEN CLR 4",   # redefined-char screen -> $cc00
    "30 SCREEN 0",       # back to the normal $0400 text screen (no clear)
    "40 POKE 51216,90",  # $c810 sentinel  (page-3 region)
    "50 POKE 52240,90",  # $cc10 sentinel  (page-4 / SCRBUF region)
    "60 POKE 52752,90",  # $ce10 sentinel  (RS-232 buffer region)
]

# Canonical text-mode state (matches SCREEN 0 / pgzero in mdbasic.asm).
CANON_VMCSB = 0x15       # screen $0400 + uppercase ROM charset ($1000)
SCROLY_TEXT = 0x1B       # bitmap/ECM off, 25 rows, display on (bit7 raster, masked)


def open_and_exit_docs(port: int, dodocs: int) -> str:
    """Poke the synthetic-NMI stub, SYS it (the CTRL+RESTORE `dodocs` entry past
    the gate), confirm the pager opened, then RUN/STOP back out. Returns the
    upper-cased pager screen text so the caller can assert it opened."""
    s = harness.connect_monitor(port, 20.0)
    harness.mem_set(s, STUB_ADDR, docs.nmi_frame_stub(dodocs))
    s.close()
    harness.keyboard_type_on_port(port, f"SYS{STUB_ADDR}\r")
    time.sleep(1.2)
    s = harness.connect_monitor(port, 20.0)
    opened = harness.screen_text(s).upper()
    s.close()
    harness.keyboard_type_on_port(port, "\x03")   # RUN/STOP -> exit docs
    time.sleep(0.6)
    return opened


def read_probes(port: int) -> dict[str, int]:
    s = harness.connect_monitor(port, 20.0)
    lo, hi = min(PROBES.values()), max(PROBES.values())
    blob = harness.mem_get(s, lo, hi)          # inclusive range
    s.close()
    return {name: blob[addr - lo] for name, addr in PROBES.items()}


def read_vic(port: int) -> dict[str, int]:
    """Read the VIC-bank / matrix / mode registers that a graphics program sets."""
    s = harness.connect_monitor(port, 20.0)
    d011_18 = harness.mem_get(s, 0xD011, 0xD018)   # SCROLY..VMCSB (inclusive)
    dd00 = harness.mem_get(s, 0xDD00, 0xDD00)      # CIA2 port A (VIC bank select)
    s.close()
    return {"scroly": d011_18[0], "vmcsb": d011_18[7], "ci2pra": dd00[0]}


def main() -> int:
    crt, dodocs = docs.build_cart()
    results: dict[str, bool] = {}

    proc = docs.boot(PORT, crt)
    try:
        harness.connect_monitor(PORT, 20.0).close()
        time.sleep(6.0)

        # ================= Phase A: $c000-$cfff data clobber =================
        for line in BASIC:
            harness.keyboard_type_on_port(PORT, line + "\r")
            time.sleep(0.3)
        harness.keyboard_type_on_port(PORT, "RUN\r")
        time.sleep(1.5)

        before = read_probes(PORT)
        for name, val in before.items():
            results[f"before_{name}_set"] = val == SENT

        results["pager_opened"] = "SEARCH" in open_and_exit_docs(PORT, dodocs)

        after = read_probes(PORT)
        for name, val in after.items():
            # The clobber: each sentinel must be gone after the docs round-trip.
            results[f"after_{name}_clobbered"] = val != SENT

        # ============= Phase B: canonical text-mode exit =============
        # Put the VIC in a non-canonical graphics state -- the end-state a program
        # in bitmap mode (SCREEN 5) leaves behind: bitmap bit set, video matrix /
        # charset base off the text defaults, VIC bank 3. We set it directly (not
        # by driving SCREEN through the keyboard, which is cursor/timing fragile)
        # so the precondition is deterministic. The docs exit must force all of
        # this back to canonical text / bank 0 regardless of the entry state.
        # Clear the dirty pre-docs screen first so the later SYS types cleanly.
        harness.keyboard_type_on_port(PORT, "\x93")
        time.sleep(0.3)
        s = harness.connect_monitor(PORT, 20.0)
        harness.mem_set(s, 0xD011, bytes([0x3B]))   # bitmap on (bit5), 25 rows, display on
        harness.mem_set(s, 0xD018, bytes([0x78]))   # non-canonical video matrix + charset base
        harness.mem_set(s, 0xDD00, bytes([0x94]))   # VIC bank 3 (bits 0-1 = %00)
        s.close()
        gfx = read_vic(PORT)
        # Guard: confirm the non-canonical state actually took, else the "after"
        # assertions below would pass trivially.
        results["graphics_before"] = (
            gfx["vmcsb"] != CANON_VMCSB and (gfx["ci2pra"] & 0x03) != 0x03
            and (gfx["scroly"] & 0x7F) != SCROLY_TEXT)

        results["pager_opened_b"] = "SEARCH" in open_and_exit_docs(PORT, dodocs)

        txt = read_vic(PORT)
        results["exit_vmcsb_canonical"] = txt["vmcsb"] == CANON_VMCSB
        results["exit_bank0"] = (txt["ci2pra"] & 0x03) == 0x03
        results["exit_text_mode"] = (txt["scroly"] & 0x7F) == SCROLY_TEXT

        s = harness.connect_monitor(PORT, 20.0)
        harness.quit_vice(s)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    print(f"  sentinel=${SENT:02x}")
    for name, addr in PROBES.items():
        print(f"  {name} (${addr:04x}): "
              f"before=${before.get(name, 0):02x} after=${after.get(name, 0):02x}")
    print(f"  VIC regs: graphics(before)={ {k: hex(v) for k, v in gfx.items()} } "
          f"text(after)={ {k: hex(v) for k, v in txt.items()} }")
    for k, v in results.items():
        print(f"  {'PASS' if v else 'FAIL'}  {k}")
    ok = all(results.values())
    print("PASS -- docs pager clobbers $c000-$cfff and exits into canonical text mode"
          if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
