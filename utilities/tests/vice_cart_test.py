#!/usr/bin/env python3
"""Boot an MDBASIC .crt in VICE headless and assert the banner appears.

Unlike vice_prg_test.py there is nothing to LOAD/RUN: the Magic Desk cartridge
cold-starts itself. The VICE binary monitor stops the CPU whenever it receives a
command, so we connect, let the cart boot in real time, then read screen RAM
once and check for the expected text.

    tools/vice_cart_test.py build/mdbasic.crt
    tools/vice_cart_test.py build/mdbasic.crt --expect MDBASIC --expect READY
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vice_prg_test as harness  # noqa: E402  (reuse monitor/screen helpers)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("crt", type=Path, help="cartridge image to boot")
    parser.add_argument("--expect", action="append", default=["MDBASIC", "READY"],
                        help="text required on screen (repeatable)")
    parser.add_argument("--port", type=int, default=6514)
    parser.add_argument("--boot-wait", type=float, default=6.0,
                        help="seconds to let the cart boot before reading screen")
    args = parser.parse_args()

    if not args.crt.exists():
        raise SystemExit(f"ERROR: cart not found: {args.crt}")

    x64sc = harness.find_tool("x64sc")
    proc = subprocess.Popen(
        [x64sc, "-silent", "-sounddev", "dummy", "-binarymonitor",
         "-binarymonitoraddress", f"ip4://127.0.0.1:{args.port}",
         "-cartcrt", str(args.crt)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    ok = False
    screen = ""
    try:
        sock = harness.connect_monitor(args.port, 20.0)
        time.sleep(args.boot_wait)
        screen = harness.screen_text(sock)
        upper = screen.upper()
        ok = all(item.upper() in upper for item in args.expect)
        harness.quit_vice(sock)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    print("---- screen ----")
    print(screen)
    if ok:
        print(f"PASS: found {', '.join(args.expect)}")
    else:
        print(f"FAIL: expected {', '.join(args.expect)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
