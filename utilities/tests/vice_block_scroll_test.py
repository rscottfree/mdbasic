#!/usr/bin/env python3
"""Verify the pure-MDBASIC random coarse block scroller in VICE."""
from __future__ import annotations

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


READY = 0xC400
GO = 0xC401
SCREEN = 0xC000
COLOR = 0xD800
SOURCE = (TESTS / "block_scroll.bas").read_text(encoding="ascii").replace(
    "S=RND(-TI)", "S=RND(-1)").replace(
    "60 FORI=0TO7",
    f"60 POKE{READY},(PEEK({READY})+1)AND255:WAIT{GO},1:POKE{GO},0:"
    "FORI=0TO7:POKE50432+I,X(I)+16:POKE50440+I,Y(I):"
    "POKE50448+I,W(I):POKE50456+I,H(I):NEXTI:FORI=0TO7",
)


def inject_program(sock) -> None:
    prg = c64_basic_prg.compile_basic(SOURCE, "mdbasic", 0x0801)
    harness.mem_set(sock, 0x0801, prg[2:])
    end = 0x0801 + len(prg) - 2
    harness.mem_set(sock, 0x002D, end.to_bytes(2, "little") * 3)
    harness.mem_set(sock, READY, b"\x00\x00")


def wait_byte(sock, address: int, predicate, timeout: float = 5.0) -> int:
    deadline = time.time() + timeout
    while time.time() < deadline:
        value = harness.mem_get(sock, address, address)[0]
        if predicate(value):
            return value
        time.sleep(0.002)
    raise TimeoutError(f"timed out waiting for ${address:04x}")


def step(sock, old_ready: int) -> int:
    harness.mem_set(sock, GO, b"\x01")
    deadline = time.time() + 5.0
    while time.time() < deadline:
        harness.monitor_cmd(sock, 0xAA)
        while True:
            response, error, _ = harness.monitor_response(sock)
            if response == 0xAA:
                if error:
                    raise RuntimeError(f"VICE resume error {error}")
                break
        time.sleep(0.01)
        value = harness.mem_get(sock, READY, READY)[0]
        if value != old_ready:
            return value
    raise TimeoutError(f"timed out waiting for ${READY:04x}")


def white_cells(sock, frame: int) -> set[tuple[int, int]]:
    screen = harness.mem_get(sock, SCREEN, SCREEN + 999)
    colors = harness.mem_get(sock, COLOR, COLOR + 999)
    cells: set[tuple[int, int]] = set()
    for offset, (code, color) in enumerate(zip(screen, colors)):
        if code == 160:
            if color & 15 != 9:
                raise AssertionError("reverse-space block cell is not white")
            cells.add((offset % 40, offset // 40))
        elif code != 32 or color & 15 != 9:
            state = harness.mem_get(sock, 50432, 50463)
            current_color = harness.mem_get(sock, 0x0286, 0x0286)[0]
            cursor = harness.mem_get(sock, 0x00CC, 0x00D6)
            blocks = [
                (state[i] - 16, state[8 + i], state[16 + i], state[24 + i])
                for i in range(8)
            ]
            raise AssertionError(
                f"frame {frame}: background corruption at "
                f"{offset % 40},{offset // 40}: "
                f"code {code}, color {color & 15}; COLOR={current_color}; "
                f"BLNSW/BLNON={cursor[0]}/{cursor[3]}, "
                f"cursor={cursor[7]},{cursor[10]}; prior block states {blocks}")
    return cells


def rectangles(cells: set[tuple[int, int]], frame: int) -> list[tuple[int, int]]:
    columns = sorted({x for x, _ in cells})
    groups: list[list[int]] = []
    for x in columns:
        if not groups or x != groups[-1][-1] + 1:
            groups.append([x])
        else:
            groups[-1].append(x)

    result: list[tuple[int, int]] = []
    previous_right = -3
    for group in groups:
        left, right = group[0], group[-1]
        if left - previous_right - 1 < 2:
            intervals = [(part[0], part[-1]) for part in groups]
            raise AssertionError(
                f"blocks have less than two blank columns between them: {intervals}")
        ys = [y for x, y in cells if left <= x <= right]
        top, bottom = min(ys), max(ys)
        expected = {
            (x, y)
            for x in range(left, right + 1)
            for y in range(top, bottom + 1)
        }
        actual = {(x, y) for x, y in cells if left <= x <= right}
        if actual != expected:
            column_rows = {
                x: sorted(y for cx, y in cells if cx == x)
                for x in range(left, right + 1)
            }
            raise AssertionError(
                f"frame {frame}: block at columns {left}-{right} is not "
                f"rectangular: {column_rows}")
        width, height = right - left + 1, bottom - top + 1
        if not (1 <= width <= 8 and 1 <= height <= 8):
            raise AssertionError(f"illegal visible block size {width}x{height}")
        result.append((width, height))
        previous_right = right
    return result


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="mdbasic-block-scroll-") as tempdir:
        log_path = Path(tempdir) / "vice.log"
        with log_path.open("w", encoding="utf-8", errors="replace") as log:
            proc = subprocess.Popen(
                [harness.find_tool("x64sc"), "+confirmonexit", "-default",
                 "+saveres", "+sound", "-sounddev", "dummy", "-warp",
                 "-model", "pal", "-binarymonitor", "-binarymonitoraddress",
                 "ip4://127.0.0.1:6620", "-cartcrt", str(ROOT / "mdbasic.crt")],
                stdout=log, stderr=subprocess.STDOUT, text=True)
            sock = None
            try:
                time.sleep(2.0)
                sock = harness.connect_monitor(6620, 20.0)
                inject_program(sock)
                sock.close()
                sock = None
                harness.keyboard_type_on_port(6620, "RUN\r")
                sock = harness.connect_monitor(6620, 20.0)
                ready = wait_byte(sock, READY, lambda value: value != 0)

                if not harness.mem_get(sock, 0xD016, 0xD016)[0] & 0x10:
                    raise AssertionError("multicolor text mode is not enabled")
                shared_colors = tuple(
                    value & 15 for value in harness.mem_get(sock, 0xD021, 0xD023))
                if shared_colors != (0, 6, 11):
                    raise AssertionError(
                        f"unexpected background palette {shared_colors}")
                previous = white_cells(sock, 0)
                sizes: set[tuple[int, int]] = set()
                saw_entry = False
                saw_exit = False
                max_blocks = 0
                for frame in range(180):
                    try:
                        ready = step(sock, ready)
                    except TimeoutError:
                        raw = harness.mem_get(sock, SCREEN, SCREEN + 999)
                        line_bytes = harness.mem_get(sock, 0x0039, 0x003A)
                        basic_line = int.from_bytes(line_bytes, "little")
                        handshake = harness.mem_get(sock, READY, GO)
                        text = "\n".join(
                            "".join(harness.screen_char(code) for code in raw[row * 40:(row + 1) * 40])
                            for row in range(25)
                        )
                        raise RuntimeError(
                            f"program stopped before test frame {frame + 1} "
                            f"(BASIC line {basic_line}, READY/GO "
                            f"{handshake[0]}/{handshake[1]}):\n{text}") from None
                    current = white_cells(sock, frame + 1)
                    rects = rectangles(current, frame + 1)
                    sizes.update(rects)
                    max_blocks = max(max_blocks, len(rects))

                    shifted = {(x - 1, y) for x, y in previous if x > 0}
                    if not shifted.issubset(current):
                        missing = sorted(shifted - current)[:5]
                        raise AssertionError(
                            f"frame {frame + 1}: block cells failed to move left: "
                            f"{missing}; current rectangles {rects}")
                    introduced = current - shifted
                    if any(x != 39 for x, _ in introduced):
                        raise AssertionError("a block appeared anywhere except the right edge")
                    saw_entry |= bool(introduced)
                    saw_exit |= any(x == 0 for x, _ in previous)
                    previous = current

                if not saw_entry or not saw_exit:
                    raise AssertionError("did not observe both gradual entry and gradual exit")
                if max_blocks < 3:
                    raise AssertionError(f"only observed {max_blocks} simultaneous blocks")
                if len({height for _, height in sizes}) < 3:
                    raise AssertionError(f"random heights were not varied: {sorted(sizes)}")
                print(
                    f"PASS: {max_blocks} simultaneous blocks; "
                    f"observed visible sizes {sorted(sizes)}")
            finally:
                harness.shutdown_vice(proc, sock, timeout=3.0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
