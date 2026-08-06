#!/usr/bin/env python3
"""Verify pure-MDBASIC simultaneous vertical/horizontal fine scrolling in VICE."""
from __future__ import annotations

import struct
import subprocess
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
D011 = 0xD011
D016 = 0xD016

SOURCE = (TESTS / "scroll_2d.bas").read_text(encoding="ascii").replace(
    "50 GETK$",
    f"47 POKE{READY},1:WAIT{GO},1\n50 GETK$",
)


def inject_program(sock) -> None:
    prg = c64_basic_prg.compile_basic(SOURCE, "mdbasic", 0x0801)
    harness.mem_set(sock, 0x0801, prg[2:])
    end = 0x0801 + len(prg) - 2
    harness.mem_set(sock, 0x002D, end.to_bytes(2, "little") * 3)
    harness.mem_set(sock, READY, b"\x00\x00")


def press_digit(sock, digit: int) -> None:
    harness.mem_set(sock, 0x0277, bytes([ord(str(digit))]))
    harness.mem_set(sock, 0x00C6, b"\x01")


def collect(sock, count: int, checkpoint_ids: dict[int, str], model: str,
            *, leave_stopped: bool = False) -> list[tuple[int, int]]:
    values: list[tuple[int, int]] = []
    pending_d016_line: int | None = None
    while len(values) < count:
        event = timing.wait_for_hit(sock)
        checkpoint_id = struct.unpack_from("<I", event)[0]
        label = checkpoint_ids[checkpoint_id]
        line, _ = timing.raster_position(sock)
        if label == "D016":
            pending_d016_line = line
            timing.command_response(sock, 0xAA)
            continue
        if pending_d016_line is None:
            raise AssertionError(f"{model}: D011 changed without the preceding D016 write")
        if model == "pal":
            safe = ((pending_d016_line >= 245 and line >= 245) or
                    ((pending_d016_line >= 245 or pending_d016_line <= 50) and
                     line <= 50))
        else:
            safe = ((pending_d016_line >= 235 and line >= 235) or
                    ((pending_d016_line >= 235 or pending_d016_line <= 25) and
                     line <= 25))
        if not safe:
            raise AssertionError(
                f"{model}: SCREEN update escaped the vertical border: "
                f"D016 line {pending_d016_line}, D011 line {line}")
        pending_d016_line = None
        vertical = harness.mem_get(sock, D011, D011)[0] & 7
        horizontal = harness.mem_get(sock, D016, D016)[0] & 7
        values.append((vertical, horizontal))
        if len(values) < count or not leave_stopped:
            timing.command_response(sock, 0xAA)
    return values


def run_model(model: str, port: int) -> None:
    with tempfile.TemporaryDirectory(prefix="mdbasic-scroll-2d-") as tempdir:
        log_path = Path(tempdir) / "vice.log"
        with log_path.open("w", encoding="utf-8", errors="replace") as log:
            proc = subprocess.Popen(
                [harness.find_tool("x64sc"), "+confirmonexit", "-default", "+saveres",
                 "+sound", "-sounddev", "dummy", "-warp", "-model", model,
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
                    raise RuntimeError("2D program did not reach its ready barrier")

                # SCREEN writes D016 first and D011 last. Track both stores so
                # the completed values and their vertical-border placement are
                # verified, not merely the final register state.
                checkpoint_ids: dict[int, str] = {}
                for label, address in (("D016", D016), ("D011", D011)):
                    checkpoint = struct.pack(
                        "<HHBBBBB", address, address, 1, 1, 2, 0, 0)
                    data = timing.command_response(
                        sock, 0x12, checkpoint, response=0x11)
                    checkpoint_ids[struct.unpack_from("<I", data)[0]] = label
                harness.mem_set(sock, GO, b"\x01")
                timing.command_response(sock, 0xAA)

                one = collect(sock, 8, checkpoint_ids, model, leave_stopped=True)
                expected = [(value, value) for value in (6, 5, 4, 3, 2, 1, 0, 7)]
                if one != expected:
                    raise AssertionError(f"{model}: step 1 D011/D016 sequence is wrong: {one}")

                press_digit(sock, 3)
                timing.command_response(sock, 0xAA)
                three = collect(sock, 5, checkpoint_ids, model, leave_stopped=True)
                expected = [(value, value) for value in (4, 1, 6, 3, 0)]
                if three != expected:
                    raise AssertionError(f"{model}: live step 3 sequence is wrong: {three}")
                if harness.mem_get(sock, 0xD020, 0xD020)[0] & 0x0F != 3:
                    raise AssertionError(f"{model}: border did not acknowledge step 3")

                press_digit(sock, 7)
                timing.command_response(sock, 0xAA)
                seven = collect(sock, 4, checkpoint_ids, model)
                expected = [(value, value) for value in (1, 2, 3, 4)]
                if seven != expected:
                    raise AssertionError(f"{model}: live step 7 sequence is wrong: {seven}")

                screen = harness.mem_get(sock, 0x0400, 0x07E7)
                for y in range(24):
                    for x in range(39):
                        if screen[y * 40 + x] != screen[(y + 1) * 40 + x + 1]:
                            raise AssertionError(
                                f"{model}: checker is not diagonal-wrap invariant at {x},{y}")
                print(f"{model.upper()}: pure SCREEN-command steps 1, 3, and 7 passed")
            finally:
                harness.shutdown_vice(proc, sock, timeout=3.0)


def main() -> int:
    run_model("pal", 6610)
    run_model("ntsc", 6611)
    print("PASS: pure MDBASIC 2D scrolling stays synchronized under live changes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
