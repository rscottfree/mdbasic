#!/usr/bin/env python3
"""Measure MDBASIC horizontal fine-scroll dwell times in VICE.

The test stops VICE on every write to VIC-II register $D016 and reads the
emulated CPU clock from VICE's instruction history.  Wall-clock speed (including
VICE warp mode) therefore cannot hide a long-lived fine-scroll position.

It compares the scrolling loop shipped on the original MDBASIC disk with the
double-buffered BASIC-only sample in hscroll_smooth.bas.  The legacy loop is
expected to demonstrate the periodic hitch.  The fixed loop gives each pixel
about four frames and prepares the next character row off-screen; every dwell
must stay within three quarters of a frame of that budget on PAL and NTSC.
"""
from __future__ import annotations

import statistics
import struct
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path


TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parents[1]
sys.path.insert(0, str(TESTS))
sys.path.insert(0, str(ROOT / "utilities" / "tools"))

import c64_basic_prg  # noqa: E402
import vice_prg_test as harness  # noqa: E402


PORT = 6538
READY = 0xC000
GO = 0xC001
D016 = 0xD016
PAL_FRAME_CYCLES = 312 * 63
NTSC_FRAME_CYCLES = 263 * 65
CHARACTERS = 5


LEGACY_SOURCE = f"""
10 DIMI,J
20 SCREENCLR:COLOR14,6,14
30 FORI=0TO39:POKE1024+I,I+1:NEXTI
40 POKE{READY},1:WAIT{GO},1
50 FORJ=1TO{CHARACTERS}
60 FORI=7TO0STEP-1
70 WAIT53265,128:SCREEN,,I
80 NEXTI
90 WAIT53265,128
100 SCROLL0,0TO39,0,2,0
110 SCREEN,,7
120 NEXTJ
130 END
"""


FIXED_SOURCE = (TESTS / "hscroll_smooth.bas").read_text(encoding="ascii").replace(
    "60 IFV=0THEN300",
    f"58 POKE{READY},1:WAIT{GO},1\n60 IFV=0THEN300",
)


@dataclass(frozen=True)
class Write:
    clock: int
    line: int
    cycle: int
    fine_x: int
    screen_base: int
    row: bytes


def command_response(sock, command: int, body: bytes = b"", response: int | None = None) -> bytes:
    """Send one binary-monitor command, ignoring asynchronous event frames."""
    harness.monitor_cmd(sock, command, body)
    wanted = command if response is None else response
    while True:
        rtype, error, data = harness.monitor_response(sock)
        if rtype != wanted:
            continue
        if error:
            raise RuntimeError(f"VICE monitor command ${command:02x} failed: ${error:02x}")
        return data


def latest_cpu_clock(sock) -> int:
    """Return the global emulated clock of the most recently executed instruction."""
    data = command_response(sock, 0x86, b"\x00" + struct.pack("<I", 1))
    count = struct.unpack_from("<I", data)[0]
    if count != 1:
        raise RuntimeError(f"VICE returned {count} CPU-history entries, expected one")
    item_size = data[4]
    item = data[5 : 5 + item_size]
    register_count = struct.unpack_from("<H", item)[0]
    offset = 2
    for _ in range(register_count):
        register_size = item[offset]
        offset += register_size + 1
    return struct.unpack_from("<Q", item, offset)[0]


def raster_position(sock) -> tuple[int, int]:
    """Read VICE's synthetic LIN/CYC monitor registers."""
    data = command_response(sock, 0x31, b"\x00")
    count = struct.unpack_from("<H", data)[0]
    offset = 2
    registers: dict[int, int] = {}
    for _ in range(count):
        item_size = data[offset]
        register_id = data[offset + 1]
        registers[register_id] = struct.unpack_from("<H", data, offset + 2)[0]
        offset += item_size + 1
    return registers[53], registers[54]  # IDs discovered as LIN/CYC in VICE 3.10


def wait_for_hit(sock) -> bytes:
    while True:
        rtype, error, data = harness.monitor_response(sock)
        if error:
            raise RuntimeError(f"VICE asynchronous monitor error ${error:02x}")
        if rtype == 0x11 and len(data) >= 5 and data[4]:
            return data


def inject_program(sock, source: str) -> None:
    prg = c64_basic_prg.compile_basic(source, "mdbasic", 0x0801)
    harness.mem_set(sock, 0x0801, prg[2:])
    end = 0x0801 + len(prg) - 2
    # VARTAB, ARYTAB and STREND: RUN will rebuild the remaining BASIC state.
    harness.mem_set(sock, 0x002D, end.to_bytes(2, "little") * 3)
    harness.mem_set(sock, READY, b"\x00\x00")


def measure(source: str, expected_writes: int, port: int, model: str = "pal",
            track_screen_swap: bool = False) -> tuple[list[Write], list[int]]:
    x64sc = harness.find_tool("x64sc")
    with tempfile.TemporaryDirectory(prefix="mdbasic-scroll-") as tempdir:
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
                inject_program(sock, source)
                sock.close()
                sock = None

                harness.keyboard_type_on_port(port, "RUN\r")
                time.sleep(0.5)
                sock = harness.connect_monitor(port, 20.0)
                if harness.mem_get(sock, READY, READY)[0] != 1:
                    raise RuntimeError("timing program did not reach its ready barrier:\n" +
                                       harness.screen_text(sock))

                # Stop on stores to $D016.  The program is still held in WAIT GO.
                checkpoint = struct.pack("<HHBBBBB", D016, D016, 1, 1, 2, 0, 0)
                data = command_response(sock, 0x12, checkpoint, response=0x11)
                d016_checkpoint = struct.unpack_from("<I", data)[0]
                d018_checkpoint = None
                if track_screen_swap:
                    checkpoint = struct.pack("<HHBBBBB", 0xD018, 0xD018, 1, 1, 2, 0, 0)
                    data = command_response(sock, 0x12, checkpoint, response=0x11)
                    d018_checkpoint = struct.unpack_from("<I", data)[0]
                harness.mem_set(sock, GO, b"\x01")
                command_response(sock, 0xAA)

                writes: list[Write] = []
                wrap_gaps: list[int] = []
                pending_wrap_clock: int | None = None
                while len(writes) < expected_writes or pending_wrap_clock is not None:
                    event = wait_for_hit(sock)
                    checkpoint_id = struct.unpack_from("<I", event)[0]
                    clock = latest_cpu_clock(sock)
                    if checkpoint_id == d018_checkpoint:
                        if pending_wrap_clock is None:
                            raise RuntimeError("unexpected D018 write without a D016 wrap")
                        wrap_gaps.append(clock - pending_wrap_clock)
                        pending_wrap_clock = None
                        command_response(sock, 0xAA)
                        continue
                    if checkpoint_id != d016_checkpoint:
                        raise RuntimeError(f"unexpected VICE checkpoint {checkpoint_id}")
                    line, cycle = raster_position(sock)
                    fine_x = harness.mem_get(sock, D016, D016)[0] & 7
                    d018 = harness.mem_get(sock, 0xD018, 0xD018)[0]
                    screen_base = (d018 & 0xF0) << 6
                    row = harness.mem_get(sock, screen_base, screen_base + 39)
                    writes.append(Write(clock, line, cycle, fine_x, screen_base, row))
                    if track_screen_swap and fine_x == 7:
                        pending_wrap_clock = clock
                    command_response(sock, 0xAA)
                return writes, wrap_gaps
            finally:
                if sock is not None:
                    harness.shutdown_vice(proc, sock, timeout=3.0)
                else:
                    harness.shutdown_vice(proc, timeout=3.0)


def distinct_dwells(writes: list[Write]) -> list[tuple[int, int]]:
    """Return (fine-X position, cycles until it visibly changes), coalescing repeats."""
    changes = [writes[0]]
    for write in writes[1:]:
        if write.fine_x != changes[-1].fine_x:
            changes.append(write)
    return [(left.fine_x, right.clock - left.clock)
            for left, right in zip(changes, changes[1:])]


def summarize(label: str, writes: list[Write], frame_cycles: int = PAL_FRAME_CYCLES) -> list[tuple[int, int]]:
    dwells = distinct_dwells(writes)
    cycles = [cycles for _, cycles in dwells]
    print(f"{label}: {len(writes)} D016 writes, {len(dwells)} visible dwells")
    print("  write sequence:", " ".join(str(write.fine_x) for write in writes))
    print("  raster lines:  ", " ".join(str(write.line) for write in writes))
    print("  dwell frames:  ", " ".join(f"{cycles / frame_cycles:.3f}"
                                         for _, cycles in dwells))
    print(f"  spread: {max(cycles) - min(cycles)} cycles; "
          f"median: {statistics.median(cycles):.0f} cycles")
    return dwells


def main() -> int:
    legacy, _ = measure(LEGACY_SOURCE, CHARACTERS * 9, PORT)
    fixed_pal, pal_wrap_gaps = measure(
        FIXED_SOURCE, CHARACTERS * 8, PORT + 1, "pal", track_screen_swap=True)
    fixed_ntsc, ntsc_wrap_gaps = measure(
        FIXED_SOURCE, CHARACTERS * 8, PORT + 2, "ntsc", track_screen_swap=True)
    legacy_dwells = summarize("legacy", legacy)
    fixed_pal_dwells = summarize("fixed PAL", fixed_pal, PAL_FRAME_CYCLES)
    fixed_ntsc_dwells = summarize("fixed NTSC", fixed_ntsc, NTSC_FRAME_CYCLES)

    legacy_cycles = [cycles for _, cycles in legacy_dwells]

    # The original code must reproduce the reported hitch, making this a useful
    # regression rather than a test that can pass without observing the bug.
    if max(legacy_cycles) < PAL_FRAME_CYCLES * 1.5:
        print("FAIL: legacy loop did not reproduce a long-lived pixel position")
        return 1
    if not any(left.fine_x == right.fine_x == 7
               for left, right in zip(legacy, legacy[1:])):
        print("FAIL: legacy loop did not reproduce the duplicate offset-7 write")
        return 1

    expected_sequence = (list(range(6, -1, -1)) + [7]) * CHARACTERS
    for label, writes, dwells, frame_cycles, wrap_gaps in (
            ("PAL", fixed_pal, fixed_pal_dwells, PAL_FRAME_CYCLES, pal_wrap_gaps),
            ("NTSC", fixed_ntsc, fixed_ntsc_dwells, NTSC_FRAME_CYCLES, ntsc_wrap_gaps)):
        if [write.fine_x for write in writes] != expected_sequence:
            print(f"FAIL: fixed {label} loop visited horizontal offsets out of order")
            return 1
        for index, (left, right) in enumerate(zip(writes, writes[1:])):
            # The native three-byte copy writes D016 first, so its watchpoint
            # stops VICE a few instructions before the D018 page change.  Check
            # the completed swap at the following fine-X=6 event instead.
            if left.fine_x == 7 and right.fine_x == 6:
                before = writes[index - 1]
                if right.screen_base == before.screen_base:
                    print(f"FAIL: fixed {label} wrap did not swap screen buffers")
                    return 1
                if right.row[:-1] != before.row[1:]:
                    print(f"FAIL: fixed {label} wrap did not advance exactly one character")
                    return 1
            elif right.fine_x == 7:
                continue
            elif right.screen_base != left.screen_base or right.row != left.row:
                print(f"FAIL: fixed {label} changed the visible row between wraps")
                return 1
        tolerance = frame_cycles * 3 // 4
        if any(abs(cycles - 4 * frame_cycles) > tolerance for _, cycles in dwells):
            print(f"FAIL: fixed {label} dwell escaped four frames +/- "
                  f"{tolerance} cycles")
            return 1
        if len(wrap_gaps) != CHARACTERS or max(wrap_gaps) > 256:
            print(f"FAIL: fixed {label} D016/D018 wrap was not atomic enough: "
                  f"{wrap_gaps}")
            return 1
        print(f"  {label} D016-to-D018 wrap gaps: " +
              " ".join(str(gap) for gap in wrap_gaps) + " cycles")

    print("PASS: fast buffered BASIC loop has no long-lived wrap position")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
