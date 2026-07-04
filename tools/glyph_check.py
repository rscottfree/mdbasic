#!/usr/bin/env python3
"""Glyph check for the docs-pager table engine (plan Verification step 1).

Confirms the PETSCII box-drawing *screen codes* the table engine emits actually
render as lines/corners/tees in the ROM **lowercase** charset (the charset the
docs pager uses). Rather than screenshot the VIC output (whose exit frame lags
live RAM), it reads the character-generator ROM straight out of a headless VICE
(banking CHARGEN in via $01) and checks each glyph's 8x8 bitmap has the expected
arms (up/down/left/right). Fast and deterministic.

    tools/glyph_check.py            # asserts every glyph; exits non-zero on mismatch

Screen-code map (verified): |=$5D  -=$40  ,-=$70 -.=$6E '-=$6D -'=$7D
                            |-=$6B -|=$73  T=$72  bottomT=$71  +=$5B
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import vice_prg_test as harness

PORT = 6560
CHARGEN_LOWER = 0xD000 + 0x0800   # ROM set 2 (lowercase) base once CHARGEN is banked in

# code -> (name, required arms) where arms is a subset of {up,down,left,right}.
# An "arm" means the glyph's line reaches that edge from the centre.
GLYPHS = {
    0x5D: ("vertical  |",  {"up", "down"}),
    0x40: ("horiz     -",  {"left", "right"}),
    0x70: ("corner   ,-",  {"down", "right"}),
    0x6E: ("corner   -.",  {"down", "left"}),
    0x6D: ("corner   '-",  {"up", "right"}),
    0x7D: ("corner   -'",  {"up", "left"}),
    0x6B: ("tee      |-",  {"up", "down", "right"}),
    0x73: ("tee      -|",  {"up", "down", "left"}),
    0x72: ("tee   top T",  {"down", "left", "right"}),
    0x71: ("tee   bot T",  {"up", "left", "right"}),
    0x5B: ("cross     +",  {"up", "down", "left", "right"}),
}


def arms(rows: bytes) -> set[str]:
    """Which edges the drawn line reaches. C64 box glyphs centre on cols 3-4,
    rows 3-4, so probe the top/bottom rows and left/right columns for pixels."""
    got = set()
    if rows[0] or rows[1]:
        got.add("up")
    if rows[6] or rows[7]:
        got.add("down")
    if any(b & 0x80 for b in rows) or any(b & 0x40 for b in rows):
        got.add("left")
    if any(b & 0x01 for b in rows) or any(b & 0x02 for b in rows):
        got.add("right")
    return got


def main() -> int:
    proc = subprocess.Popen(
        [harness.find_tool("x64sc"), "-silent", "-sounddev", "dummy",
         "-binarymonitor", "-binarymonitoraddress", f"ip4://127.0.0.1:{PORT}"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ok = True
    try:
        s = harness.connect_monitor(PORT, 20.0)
        time.sleep(4.0)
        old = harness.mem_get(s, 0x0001, 0x0001)[0]
        harness.mem_set(s, 0x0001, bytes([(old & ~0x04) & 0xFF]))   # CHARGEN visible
        time.sleep(0.2)
        for code, (name, want) in GLYPHS.items():
            base = CHARGEN_LOWER + code * 8
            rows = harness.mem_get(s, base, base + 7)
            got = arms(rows)
            good = got == want
            ok &= good
            print(f"  {'ok  ' if good else 'BAD '} ${code:02x} {name}  "
                  f"arms={sorted(got)}" + ("" if good else f"  want={sorted(want)}"))
        harness.mem_set(s, 0x0001, bytes([old]))
        harness.quit_vice(s)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
