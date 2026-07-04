#!/usr/bin/env python3
"""Supplemental docs-pager test: doc-view navigation and search-page paths not
covered by vice_docs_test.py -- F5/F3 topic navigation (including the mid-topic
snap-to-top), F7 page down, HOME, F1 page up at the top clamp, DEL filter
backspace, the selected-cell reverse-video highlight, and the once-per-view
status bar staying intact across scrolls.

Builds the same full docs cart as vice_docs_test.py (reusing its build_cart)
and drives the pager through the kernal keyboard buffer.

    tools/vice_docs_nav_test.py
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import vice_prg_test as harness
import vice_docs_test as dt

PORT = 6560


def screen(port):
    s = harness.connect_monitor(port, 20.0)
    txt = harness.screen_text(s).upper()
    s.close()
    return txt


def main() -> int:
    crt, dodocs = dt.build_cart()
    proc = dt.boot(PORT, crt)
    results = {}
    try:
        s = harness.connect_monitor(PORT, 20.0)
        time.sleep(6.0)
        harness.mem_set(s, dt.STUB_ADDR, dt.nmi_frame_stub(dodocs))
        s.close()
        harness.keyboard_type_on_port(PORT, f"SYS{dt.STUB_ADDR}\r")
        time.sleep(2.5)
        results["search_page"] = "SEARCH" in screen(PORT)
        # selected cell (row 2, col 0) is reverse video; unselected (col 20) is not
        s = harness.connect_monitor(PORT, 20.0)
        cell0 = harness.mem_get(s, 0x0400 + 2 * 40, 0x0400 + 2 * 40 + 18)
        cell1 = harness.mem_get(s, 0x0400 + 2 * 40 + 20, 0x0400 + 2 * 40 + 38)
        results["selection_reverse"] = (all(b & 0x80 for b in cell0)
                                        and not any(b & 0x80 for b in cell1))
        s.close()
        # DEL backspaces the filter: no-match filter, two DELs, RETURN opens SPRITE
        harness.keyboard_type_on_port(PORT, "SPRITEQQ")
        time.sleep(1.0)
        harness.keyboard_type_on_port(PORT, "\x14\x14\r")
        time.sleep(1.0)
        results["del_filter"] = "SPRITE" in screen(PORT)
        # back to a fresh search page for the topic-nav phase
        harness.keyboard_type_on_port(PORT, "\x89")
        time.sleep(0.8)
        # RETURN opens the first (selected) topic: ABOUT THIS GUIDE
        harness.keyboard_type_on_port(PORT, "\r")
        time.sleep(0.8)
        top_a = screen(PORT)
        results["open_first_topic"] = "ABOUT THIS GUIDE" in top_a
        # F5 -> next topic (PREFACE)
        harness.keyboard_type_on_port(PORT, "\x87")
        time.sleep(0.8)
        pref = screen(PORT)
        results["f5_next_topic"] = "PREFACE" in pref and pref != top_a
        # CRSR down x3 (mid-topic), then F3 -> snap back to the topic's first line
        harness.keyboard_type_on_port(PORT, "\x11\x11\x11")
        time.sleep(0.8)
        results["crsr_scroll"] = screen(PORT) != pref
        harness.keyboard_type_on_port(PORT, "\x86")
        time.sleep(0.8)
        results["f3_snap_top"] = screen(PORT) == pref
        # F3 again at topic top -> previous topic (back to ABOUT)
        harness.keyboard_type_on_port(PORT, "\x86")
        time.sleep(0.8)
        results["f3_prev_topic"] = screen(PORT) == top_a
        # F7 -> page down (screen changes)
        harness.keyboard_type_on_port(PORT, "\x88")
        time.sleep(0.8)
        paged = screen(PORT)
        results["f7_page_down"] = paged != top_a
        # HOME -> top of doc
        harness.keyboard_type_on_port(PORT, "\x13")
        time.sleep(0.8)
        results["home_top"] = screen(PORT) == top_a
        # F1 at top -> no move, no crash
        harness.keyboard_type_on_port(PORT, "\x85")
        time.sleep(0.8)
        results["f1_at_top"] = screen(PORT) == top_a
        # status bar present on the last row after scrolling (drawbar once)
        harness.keyboard_type_on_port(PORT, "\x11\x11\x11")
        time.sleep(0.8)
        s = harness.connect_monitor(PORT, 20.0)
        row24 = harness.mem_get(s, 0x0400 + 24 * 40, 0x0400 + 24 * 40 + 39)
        results["status_bar_reverse"] = all(b & 0x80 for b in row24)
        s.close()
        harness.keyboard_type_on_port(PORT, "\x03")
        time.sleep(0.6)
        s = harness.connect_monitor(PORT, 20.0)
        results["exit_ready"] = "READY" in harness.screen_text(s).upper()
        harness.quit_vice(s)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    for k, v in results.items():
        print(f"  {'PASS' if v else 'FAIL'}  {k}")
    ok = all(results.values())
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
