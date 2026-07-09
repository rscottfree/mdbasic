#!/usr/bin/env python3
"""Regression test: MOVE must accept a single-line block (end == start).

do_move's pre-flight used to reject end<=start, which wrongly rejected moving
a single line (start==end is a valid one-line block; only end<start is an
error). Covers the fixed check in edit_tool_common.asm's do_move plus the updated
"?end<start" message, driven the same way as tools/vice_renum_test.py.

Runnable standalone (runs just `single_move`) or as part of the unified
`tools/vice_renum_test.py` invocation, which unions in this file's TESTS.

    tools/vice_renum_single_line_move_test.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import vice_prg_test as harness
import renum_test_lib as lib


def session_single_move(crt, dorenum, domenu, next_port):
    """100 GOSUB 200 / 200 PRINT"SUB" / 300 END
    M 200 200 50 -> single-line block [200,200] moved to dest 50; the source
    line must land exactly on 50, physically relocating before line 100, and
    its reference (100 GOSUB 200) must be rewritten to GOSUB 50."""
    results = {}
    port = next_port()
    prog = ["100 GOSUB 200", '200 PRINT"SUB"', "300 END"]
    proc = lib.boot(port, crt)
    try:
        s = harness.connect_monitor(port, 20.0)
        time.sleep(6.0)
        s.close()
        lib.type_lines(port, prog)
        lib.open_tool(port, lib.DOMOVE)
        lib.cmd(port, "M 200 200 50")
        s = harness.connect_monitor(port, 20.0)
        txt = harness.screen_text(s).upper()
        results["single_move_ok"] = "OK" in txt
        s.close()
        harness.keyboard_type_on_port(port, "\x03")   # RUN/STOP -> leave tool
        time.sleep(0.6)
        harness.keyboard_type_on_port(port, "\x93LIST\r")
        time.sleep(1.2)
        s = harness.connect_monitor(port, 20.0)
        lst = harness.screen_text(s).upper()
        nums = lib.walk_links(s)
        s.close()
        results["single_move_hdr"] = "50 PRINT" in lst
        results["single_move_ref"] = "100 GOSUB 50" in lst
        results["single_move_kept"] = "300 END" in lst
        i50 = lst.find("50 PRINT"); i100 = lst.find("100 GOSUB")
        results["single_move_sorted"] = 0 <= i50 < i100
        results["single_move_links_valid"] = nums == [50, 100, 300]
        harness.quit_vice(harness.connect_monitor(port, 20.0))
    finally:
        lib.finish_on_port(proc, port)
    return results


TESTS = [
    ("single_move", session_single_move),
]


if __name__ == "__main__":
    sys.exit(lib.run_cli(TESTS, sys.argv[1:]))
