#!/usr/bin/env python3
"""Regression test: MOVE must reject when the *shifted range* (not just the
destination line itself) would land on an existing kept line number.

Reported scenario: program
    1 PRINT"1"
    3 PRINT"3"
    5 PRINT"MOVE ME"
    7 PRINT"AND ME"
and a move whose source block covers both line 5 and line 7 (so minsrc=5,
maxsrc=7), moved to dest=2. The shifted range is [2,4] (2, 3, 4), which
interleaves the kept line 3 -- this must be rejected as a collision, leaving
the program byte-identical, exactly like the existing block-move collision
case in vice_renum_test.py (session 3, block [100,110] -> [15,25] over kept
line 20). This test isolates that same check against the user's literal
repro shape (sparse single-digit lines) rather than round-hundred lines.

    tools/vice_renum_move_overlap_test.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import vice_prg_test as harness
import vice_docs_test as dt
import vice_renum_test as rt


def main() -> int:
    crt, _dodocs = dt.build_cart()
    dorenum = dt.label_addr("/tmp/menu.lst", "dorenum")
    results = {}
    port = 6650

    prog = ['1 PRINT"1"', '3 PRINT"3"', '5 PRINT"MOVE ME"', '7 PRINT"AND ME"']
    proc = rt.boot(port, crt)
    try:
        s = harness.connect_monitor(port, 20.0)
        time.sleep(6.0)
        s.close()
        rt.type_lines(port, prog)
        s = harness.connect_monitor(port, 20.0)
        before = rt.read_prog(s)
        s.close()

        rt.open_tool(port, dorenum)

        # Source block [5,7] covers lines 5 and 7 (minsrc=5, maxsrc=7); dest=2
        # -> shifted range [2,4], which contains the kept line 3.
        rt.cmd(port, "M 5 7 2")
        s = harness.connect_monitor(port, 20.0)
        txt = harness.screen_text(s).upper()
        results["overlap_rejected_msg"] = "COLLISION" in txt
        results["overlap_rejected_id"] = rt.read_prog(s) == before
        s.close()

        # Sanity: the REPL is still open and a legitimate move now succeeds,
        # proving the rejection didn't wedge the tool.
        rt.cmd(port, "M 5 7 10")
        s = harness.connect_monitor(port, 20.0)
        txt2 = harness.screen_text(s).upper()
        results["followup_move_ok"] = "OK" in txt2
        s.close()

        harness.keyboard_type_on_port(port, "\x03")   # RUN/STOP -> leave tool
        time.sleep(0.6)
        harness.keyboard_type_on_port(port, "\x93LIST\r")
        time.sleep(1.2)
        s = harness.connect_monitor(port, 20.0)
        lst = harness.screen_text(s).upper()
        s.close()
        results["followup_headers"] = ("10 PRINT" in lst and "12 PRINT" in lst
                                        and "3 PRINT" in lst)
        harness.quit_vice(harness.connect_monitor(port, 20.0))
    finally:
        proc.terminate()
        try: proc.wait(timeout=5)
        except Exception: proc.kill()

    for k, v in results.items():
        print(f"  {'PASS' if v else 'FAIL'}  {k}")
    ok = all(results.values())
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
