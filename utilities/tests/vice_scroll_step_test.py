#!/usr/bin/env python3
"""Exercise live 1-8 pixel step changes in hscroll_step.bas under VICE."""
from __future__ import annotations

import subprocess
import struct
import sys
import tempfile
import time
from pathlib import Path


TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parents[1]
sys.path.insert(0, str(TESTS))
sys.path.insert(0, str(ROOT / "utilities" / "tools"))

import c64_basic_prg  # noqa: E402
import vice_prg_test as harness  # noqa: E402
import vice_scroll_timing_test as timing  # noqa: E402


READY = 0xC000
GO = 0xC001
D016 = 0xD016
KEYD = 0x0277
NDX = 0x00C6

SOURCE = (TESTS / "hscroll_step.bas").read_text(encoding="ascii").replace(
    "70 GETK$",
    f"67 POKE{READY},1:WAIT{GO},1\n70 GETK$",
)


def inject_program(sock) -> None:
    prg = c64_basic_prg.compile_basic(SOURCE, "mdbasic", 0x0801)
    harness.mem_set(sock, 0x0801, prg[2:])
    end = 0x0801 + len(prg) - 2
    harness.mem_set(sock, 0x002D, end.to_bytes(2, "little") * 3)
    harness.mem_set(sock, READY, b"\x00\x00")


def press_digit(sock, digit: int) -> None:
    harness.mem_set(sock, KEYD, bytes([ord(str(digit))]))
    harness.mem_set(sock, NDX, b"\x01")


def collect(sock, count: int, *, leave_stopped: bool = False) -> list[tuple[int, int]]:
    result: list[tuple[int, int]] = []
    for index in range(count):
        timing.wait_for_hit(sock)
        fine_x = harness.mem_get(sock, D016, D016)[0] & 7
        d018 = harness.mem_get(sock, 0xD018, 0xD018)[0]
        result.append((fine_x, (d018 & 0xF0) << 6))
        if index + 1 < count or not leave_stopped:
            timing.command_response(sock, 0xAA)
    return result


def run_model(model: str, port: int) -> None:
    x64sc = harness.find_tool("x64sc")
    with tempfile.TemporaryDirectory(prefix="mdbasic-scroll-step-") as tempdir:
        log_path = Path(tempdir) / "vice.log"
        with log_path.open("w", encoding="utf-8", errors="replace") as log:
            proc = subprocess.Popen(
                [x64sc, "+confirmonexit", "-default", "+saveres", "+sound",
                 "-sounddev", "dummy", "-warp", "-model", model,
                 "-binarymonitor", "-binarymonitoraddress",
                 f"ip4://127.0.0.1:{port}", "-cartcrt", str(ROOT / "mdbasic.crt")],
                stdout=log, stderr=subprocess.STDOUT, text=True)
            sock = None
            try:
                time.sleep(2.0)
                sock = harness.connect_monitor(port, 20.0)
                inject_program(sock)
                sock.close()
                sock = None

                harness.keyboard_type_on_port(port, "RUN\r")
                time.sleep(0.5)
                sock = harness.connect_monitor(port, 20.0)
                if harness.mem_get(sock, READY, READY)[0] != 1:
                    raise RuntimeError("step program did not reach its ready barrier")

                checkpoint = struct.pack(
                    "<HHBBBBB", D016, D016, 1, 1, 2, 0, 0)
                timing.command_response(sock, 0x12, checkpoint, response=0x11)
                harness.mem_set(sock, GO, b"\x01")
                timing.command_response(sock, 0xAA)

                one = collect(sock, 8, leave_stopped=True)
                if [fine for fine, _ in one] != [6, 5, 4, 3, 2, 1, 0, 7]:
                    raise AssertionError(f"{model}: step 1 sequence is wrong: {one}")

                # VICE is stopped on the last D016 store, so the key is waiting
                # when BASIC reaches GET on resumption.
                press_digit(sock, 5)
                timing.command_response(sock, 0xAA)
                five = collect(sock, 6, leave_stopped=True)
                if [fine for fine, _ in five] != [2, 5, 0, 3, 6, 1]:
                    raise AssertionError(f"{model}: step 5 sequence is wrong: {five}")
                active = five[-1][1]
                if harness.mem_get(sock, active + 86, active + 86)[0] != ord("5"):
                    raise AssertionError(f"{model}: visible step indicator did not change to 5")

                press_digit(sock, 8)
                timing.command_response(sock, 0xAA)
                eight = collect(sock, 4)
                if [fine for fine, _ in eight] != [1, 1, 1, 1]:
                    raise AssertionError(f"{model}: step 8 sequence is wrong: {eight}")
                pages = [page for _, page in eight]
                if any(left == right for left, right in zip(pages, pages[1:])):
                    raise AssertionError(f"{model}: step 8 did not swap pages: {pages}")
                active = eight[-1][1]
                if harness.mem_get(sock, active + 86, active + 86)[0] != ord("8"):
                    raise AssertionError(f"{model}: visible step indicator did not change to 8")

                print(f"{model.upper()}: step 1, live step 5, and live step 8 passed")
            finally:
                harness.shutdown_vice(proc, sock, timeout=3.0)


def main() -> int:
    run_model("pal", 6600)
    run_model("ntsc", 6601)
    print("PASS: number keys change horizontal pixel displacement while scrolling")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
