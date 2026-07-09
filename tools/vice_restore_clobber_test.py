#!/usr/bin/env python3
"""Focused regression for the CTRL+RESTORE resident stub location.

Build the docs cart, overwrite the classic sprite-data range in the cassette
buffer ($0340-$037f), then trigger the direct docs entry through a synthetic NMI
frame. The pager must still open and RUN/STOP must return to READY.

    tools/vice_restore_clobber_test.py
"""
from __future__ import annotations

import subprocess
import sys
import time

import vice_docs_test as docs
import vice_prg_test as harness

PORT = 6562


def main() -> int:
    crt, dodocs = docs.build_cart()
    results: dict[str, bool] = {}

    proc = docs.boot(PORT, crt)
    try:
        harness.connect_monitor(PORT, 20.0).close()
        time.sleep(6.0)

        s = harness.connect_monitor(PORT, 20.0)
        harness.mem_set(s, 0x0340, bytes(range(64)))
        s.close()

        opened = docs.open_docs_via_stub(PORT, dodocs)
        results["pager_opens_after_0340_clobber"] = "SEARCH" in opened

        harness.keyboard_type_on_port(PORT, "\x03")
        time.sleep(0.7)
        s = harness.connect_monitor(PORT, 20.0)
        screen = harness.screen_text(s).upper()
        results["returns_to_ready"] = "READY" in screen
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
