#!/usr/bin/env python3
"""Regression: exiting the docs pager from a non-screen-0 page must leave the
editor cursor visible.

The cursor is drawn by the KERNAL IRQ using PNT ($d1/$d2), the pointer to the
current screen line. On a SCREEN 1-5 page that pointer (and the editor line-link
table) point at the page's screen RAM ($c8xx...). The pager forces a return to
the $0400 text screen on exit, but SCRBUF only ever held $0400, so that page's
content was never saved and its editor state is stale: if the exit merely
restored a $0400 cursor position, PNT would still point at $c8xx and the cursor
would stay invisible until a keypress recomputed it. The fix clears to a fresh
$0400 screen on a non-page-0 exit (rebuilding the link table + homing PNT); page
0 keeps its restored screen untouched (covered by vice_docs_test).

A real CTRL+RESTORE exits via the kernal NMI tail ($fe72 -> RTI) back to the
*interrupted* editor loop, NOT through READY -- so READY never re-inits PNT for
us. To observe the exact state the pager leaves (before any READY re-init would
mask it) this test returns the synthetic NMI frame into a JMP-self spin loop and
reads PNT/HIBASE/VIC from the frozen machine.

Observed on Ultimate 64 hardware; the cause is KERNAL editor state, so it
reproduces identically in VICE.

    tools/vice_docs_cursor_test.py
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

PORT = 6562
STUB = docs.STUB_ADDR   # $0390 = 912
SPIN = 0x02A7           # a JMP-self we return into, to freeze the pager-exit state


def spin_stub(dodocs: int) -> bytes:
    """docs.nmi_frame_stub, but the NMI return address is SPIN (a JMP-self), not
    $a474/READY -- so after docs exit + RTI the CPU freezes and we read the exact
    editor/VIC state the pager left, before READY could re-initialise PNT."""
    lo, hi = dodocs & 0xFF, dodocs >> 8
    return bytes([
        0xA9, SPIN >> 8, 0x48,               # PCH
        0xA9, SPIN & 0xFF, 0x48,             # PCL
        0xA9, 0x00, 0x48, 0x48, 0x48, 0x48,  # P, A, X, Y
        0x4C, lo, hi,                        # jmp dodocs
    ])


def zp(port: int) -> dict[str, int]:
    s = harness.connect_monitor(port, 20.0)
    hib = harness.mem_get(s, 0x0288, 0x0288)[0]           # HIBASE
    z = harness.mem_get(s, 0x00D1, 0x00D6)                # PNT, PNTR, .., TBLX
    vic = harness.mem_get(s, 0xD011, 0xD018)              # SCROLY..VMCSB
    dd00 = harness.mem_get(s, 0xDD00, 0xDD00)[0]
    s.close()
    return {"hibase": hib, "pnt": z[0] | (z[1] << 8),
            "scroly": vic[0], "vmcsb": vic[7], "ci2pra": dd00}


def main() -> int:
    crt, dodocs = docs.build_cart()
    results: dict[str, bool] = {}
    before = after = {}

    proc = docs.boot(PORT, crt)
    try:
        harness.connect_monitor(PORT, 20.0).close()
        time.sleep(6.0)

        # Enter SCREEN 3 (redefined-char page at $c800) from the interactive
        # prompt: HIBASE + PNT now live on the $c8xx page.
        harness.keyboard_type_on_port(PORT, "SCREEN CLR 3\r")
        time.sleep(0.8)
        before = zp(PORT)
        results["entered_page3"] = before["hibase"] == 0xC8 and (before["pnt"] >> 8) == 0xC8

        # Trigger docs, returning into the spin loop so the pager-exit state is
        # frozen (no READY re-init).
        s = harness.connect_monitor(PORT, 20.0)
        harness.mem_set(s, SPIN, bytes([0x4C, SPIN & 0xFF, SPIN >> 8]))  # JMP self
        harness.mem_set(s, STUB, spin_stub(dodocs))
        s.close()
        harness.keyboard_type_on_port(PORT, f"SYS{STUB}\r")
        time.sleep(1.2)
        s = harness.connect_monitor(PORT, 20.0)
        results["docs_opened"] = "SEARCH" in harness.screen_text(s).upper()
        s.close()
        harness.keyboard_type_on_port(PORT, "\x03")   # RUN/STOP exit -> RTI into SPIN
        time.sleep(0.6)

        after = zp(PORT)
        # The fix: PNT must point back into the visible $0400 screen so the blink
        # IRQ draws the cursor there (not off-screen at $c8xx).
        results["cursor_pnt_onscreen"] = 0x0400 <= after["pnt"] <= 0x07FF
        results["hibase_page0"] = after["hibase"] == 0x04
        # And the VIC is canonical text (the sibling fix), so $0400 is displayed.
        results["vmcsb_canonical"] = after["vmcsb"] == 0x15
        results["bank0"] = (after["ci2pra"] & 0x03) == 0x03
        results["text_mode"] = (after["scroly"] & 0x7F) == 0x1B

        s = harness.connect_monitor(PORT, 20.0)
        harness.quit_vice(s)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    print(f"  before: HIBASE=${before.get('hibase',0):02x} PNT=${before.get('pnt',0):04x}")
    print(f"  after : HIBASE=${after.get('hibase',0):02x} PNT=${after.get('pnt',0):04x} "
          f"VMCSB=${after.get('vmcsb',0):02x}")
    for k, v in results.items():
        print(f"  {'PASS' if v else 'FAIL'}  {k}")
    ok = all(results.values())
    print("PASS -- docs exit from a non-text page leaves the cursor on $0400"
          if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
