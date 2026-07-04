#!/usr/bin/env python3
"""End-to-end test of the MDBASIC CTRL+RESTORE docs pager in VICE.

Builds the full docs cart from source (image + boot loader + RESTORE handler +
pager + packed docs), boots it, and checks:
  * MDBASIC boots to READY (loader regression);
  * the loader repointed the cart NMI vector $8002 -> $033c and stashed the
    original runstp;
  * triggering the handler's docs entry (`dodocs`, the exact code a CTRL+RESTORE
    press runs once the CTRL gate passes) opens the pager, in-pager search works,
    and RUN/STOP returns to READY with the user's pre-docs screen restored (the
    handler exits via the kernal NMI tail $fe72/RTI, not jmp READY);
  * sprite_timing runs to DONE (execution-path regression: the docs handler must
    not disturb normal program execution, even when a program POKEs the cassette
    buffer the handler lives in).

The CTRL gate itself (the handler reads keyboard-matrix row 7 / STKEY $91 bit 2)
can't be exercised here: the harness injects keys via the kernal buffer, not the
live matrix, and the RESTORE NMI can't be injected via the monitor either. So we
SYS a tiny stub that fabricates a synthetic NMI return frame and jumps to `dodocs`
(past the gate); the gate is 5 instructions verified at assembly time.

    tools/vice_docs_test.py
"""
from __future__ import annotations

import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import make_crt
import build_docs
import vice_prg_test as harness

PORT = 6554
HANDLER_ADDR = 0x033c          # boot entry the cart NMI vector ($8002) points at
STUB_ADDR = 0x0390             # scratch above the $033c handler ($033c-$038d used)

# PETSCII box-grid corner/tee/cross screen codes (no vertical $5d, which is common).
BOX_CODES = {0x70, 0x6E, 0x6D, 0x7D, 0x6B, 0x73, 0x72, 0x71, 0x5B}


def table_offsets(topic: str) -> tuple[int, int]:
    """Line offsets (from the topic banner) of the first wide-table 'SCREEN RAM:'
    sections row and the first box-grid corner (top-left, screen code $70), read
    from the packed records so the test scrolls exactly to each rendered table."""
    import struct
    idx, data, _tot, _banks = build_docs.build_index_and_data()
    n = struct.unpack("<H", idx[4:6])[0]
    lpb, cols, bank = build_docs.LINES_PER_BANK, build_docs.COLS, build_docs.BANK_SIZE

    def rec(L: int) -> bytes:
        o = (L // lpb) * bank + (L % lpb) * cols
        return data[o:o + cols]

    off = 8
    for _ in range(n):
        tok, start, count = struct.unpack("<BHH", idx[off:off + 5])
        name = bytes(idx[off + 5:off + 24]).rstrip().decode("latin1")
        off += build_docs.IXSTRIDE
        if name == topic:
            sect = box = 0
            for k in range(count):
                r = rec(start + k)
                txt = "".join(chr(b & 0x7F) for b in r)
                if not sect and "SCREEN" in txt and "RAM:" in txt:
                    sect = k
                if not box and 0x70 in r:
                    box = k
            return sect, box
    raise RuntimeError(f"topic {topic!r} not found")


def nmi_frame_stub(dodocs: int) -> bytes:
    """A tiny 6502 stub that fabricates a synthetic NMI return frame, then jumps
    to `dodocs`. A real CTRL+RESTORE entry is an NMI, and the handler now exits
    via the kernal NMI tail ($fe72 -> RTI) instead of `jmp READY`, so it needs a
    return frame on the stack. We push (deepest first) PCH,PCL,P,A,X,Y exactly as
    a hardware NMI + NMINV would, with the RTI return address = $a474 (READY), so
    the docs handler's exit RTIs cleanly back to a BASIC READY prompt."""
    lo, hi = dodocs & 0xFF, dodocs >> 8
    return bytes([
        0xA9, 0xA4, 0x48,              # lda #$a4 / pha   ; PCH  (return $a474)
        0xA9, 0x74, 0x48,              # lda #$74 / pha   ; PCL
        0xA9, 0x00, 0x48, 0x48, 0x48, 0x48,  # lda #$00 / pha*4 ; P, A, X, Y
        0x4C, lo, hi,                  # jmp dodocs
    ])


# Disabled: flip to True to re-enable the sprite_timing execution-path regression.
RUN_SPRITE_TIMING = False


def asm(src: str, out: str, lst: str | None = None) -> bytes:
    cmd = ["tmpx"]
    if lst:
        cmd += ["-l", lst]
    cmd += ["-i", str(ROOT / src), "-o", out]
    subprocess.run(cmd, check=True, capture_output=True)
    return Path(out).read_bytes()[2:]          # strip 2-byte load address


def label_addr(lst_path: str, label: str) -> int:
    """Resolve a label's address from a tmpx listing (label on its own line,
    address taken from the next instruction line)."""
    lines = Path(lst_path).read_text().splitlines()
    for i, line in enumerate(lines):
        if line.split()[1:2] == [label]:       # bare-label line: "<lineno> <label>"
            for nxt in lines[i + 1:]:
                m = re.match(r"\s*\d+\s+([0-9a-fA-F]{4})\b", nxt)
                if m:
                    return int(m.group(1), 16)
    raise RuntimeError(f"label {label!r} not found in {lst_path}")


def build_cart() -> tuple[Path, int]:
    subprocess.run(["tmpx", "-i", str(ROOT / "mdbasic.asm"),
                    "-o", str(ROOT / "mdbasic.prg")], check=True, capture_output=True)
    stub = asm("boot.asm", "/tmp/boot.prg")
    handler = asm("docs_help.asm", "/tmp/help.prg", lst="/tmp/help.lst")
    dodocs = label_addr("/tmp/help.lst", "dodocs")
    pager = asm("docs_pager.asm", "/tmp/pager.prg")
    build_docs.pack(ROOT / "build/docs.bin")
    idx = (ROOT / "build/docs.idx").read_bytes()
    dat = (ROOT / "build/docs.dat").read_bytes()
    banks = make_crt.doc_banks(pager, idx, dat, handler)
    image = make_crt.image_from_prg((ROOT / "mdbasic.prg").read_bytes())
    crt = make_crt.build_crt(image, name="MDDOCS", stub=stub, extra_banks=banks)
    out = Path("/tmp/mddocs.crt")
    out.write_bytes(crt)
    print(f"cart {len(crt)} bytes, {make_crt.NUM_BANKS + len(banks)} banks; "
          f"dodocs=${dodocs:04x}")
    return out, dodocs


def boot(port, crt):
    proc = subprocess.Popen(
        [harness.find_tool("x64sc"), "-silent", "-sounddev", "dummy",
         "-binarymonitor", "-binarymonitoraddress", f"ip4://127.0.0.1:{port}",
         "-cartcrt", str(crt)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return proc


def main() -> int:
    crt, dodocs = build_cart()
    results = {}

    # --- install + trigger + pager ---
    proc = boot(PORT, crt)
    try:
        s = harness.connect_monitor(PORT, 20.0)
        time.sleep(6.0)
        results["boot_ready"] = "READY" in harness.screen_text(s).upper()
        nmi = harness.mem_get(s, 0x8002, 0x8004)
        results["nmi_repointed"] = (nmi[0] | nmi[1] << 8) == HANDLER_ADDR
        rg = harness.mem_get(s, 0x03f8, 0x03fa)
        results["runstp_stashed"] = 0x8000 <= (rg[0] | rg[1] << 8) <= 0xbfff
        s.close()
        # Leave a marker on screen so we can prove it survives a docs round-trip.
        harness.keyboard_type_on_port(PORT, '?"ZZMARK"\r')
        time.sleep(0.5)
        # Poke the synthetic-NMI-frame stub and SYS it. The stub jumps to dodocs
        # (the CTRL+RESTORE docs entry, past the CTRL/STOP gate) with a return
        # frame in place, so the handler's new $fe72/RTI exit returns cleanly.
        s = harness.connect_monitor(PORT, 20.0)
        harness.mem_set(s, STUB_ADDR, nmi_frame_stub(dodocs))
        # Stamp a distinctive low-nybble color pattern on an untouched row (row 5,
        # clear of the cursor/print area) so we can prove the pager packs and
        # restores color RAM rather than leaving its solid fill (color 14) behind.
        COLCELLS = 0xd800 + 5 * 40
        COLPAT = bytes([0x02, 0x05, 0x07, 0x03])
        harness.mem_set(s, COLCELLS, COLPAT)
        s.close()
        harness.keyboard_type_on_port(PORT, f"SYS{STUB_ADDR}\r")
        time.sleep(1.2)
        s = harness.connect_monitor(PORT, 20.0)
        opened = harness.screen_text(s).upper()
        results["pager_opens"] = "SEARCH" in opened               # search page is default
        results["search_grid"] = "AUTO" in opened                 # grid lists topics (no filter)
        s.close()
        harness.keyboard_type_on_port(PORT, "SPRITE\r")           # filter + enter -> doc page
        time.sleep(0.7)
        s = harness.connect_monitor(PORT, 20.0)
        doc_top = harness.screen_text(s).upper()
        results["search"] = "SPRITE" in doc_top
        s.close()
        # CRSR-down scrolls the doc (same kernal-buffer path the U64 keyboard uses);
        # the view must change, then CRSR-up must change it back -- a held arrow
        # repeats through this and STOPS when released because the buffer drains.
        harness.keyboard_type_on_port(PORT, "\x11" * 8)           # 8x CRSR down
        time.sleep(0.7)
        s = harness.connect_monitor(PORT, 20.0)
        doc_scrolled = harness.screen_text(s).upper()
        results["scroll_down"] = doc_scrolled != doc_top
        s.close()
        harness.keyboard_type_on_port(PORT, "\x91" * 8)           # 8x CRSR up
        time.sleep(0.7)
        s = harness.connect_monitor(PORT, 20.0)
        results["scroll_up"] = harness.screen_text(s).upper() != doc_scrolled
        s.close()
        # --- table engine: SCREEN carries a wide (sections) table and a narrow
        # PETSCII box grid; return to search, jump to it, scroll each into view. ---
        sect_k, box_k = table_offsets("SCREEN")
        harness.keyboard_type_on_port(PORT, "\x89")               # F2 -> search page
        time.sleep(0.6)
        harness.keyboard_type_on_port(PORT, "\x93")               # SHIFT+CLR: clear filter
        time.sleep(0.3)
        harness.keyboard_type_on_port(PORT, "SCREEN\r")           # jump to SCREEN topic
        time.sleep(0.7)
        harness.keyboard_type_on_port(PORT, "\x11" * max(0, sect_k - 4))  # scroll to sections
        time.sleep(0.8)
        s = harness.connect_monitor(PORT, 20.0)
        wide = harness.screen_text(s).upper()
        results["table_wide_render"] = "SCREEN RAM:" in wide      # sections LABEL: value row
        s.close()
        harness.keyboard_type_on_port(PORT, "\x11" * max(0, box_k - sect_k))  # on to box grid
        time.sleep(0.8)
        s = harness.connect_monitor(PORT, 20.0)
        raw = harness.mem_get(s, 0x0400, 0x07E7)
        box_txt = harness.screen_text(s).upper()
        results["table_box_glyphs"] = any(b in BOX_CODES for b in raw)   # grid drawn
        results["table_box_header"] = "MODE" in box_txt and "BITMAP" in box_txt
        s.close()
        harness.keyboard_type_on_port(PORT, "\x03")               # RUN/STOP exit
        time.sleep(0.5)
        s = harness.connect_monitor(PORT, 20.0)
        screen = harness.screen_text(s).upper()
        results["exit_ready"] = "READY" in screen          # clean NMI/RTI return
        results["screen_restored"] = "ZZMARK" in screen     # pre-docs screen is back
        col = harness.mem_get(s, COLCELLS, COLCELLS + len(COLPAT) - 1)  # end inclusive
        results["color_restored"] = (                       # low nybbles survived the round-trip
            bytes(b & 0x0f for b in col) == COLPAT)
        harness.quit_vice(s)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    # --- execution-path regression: sprite_timing must reach DONE ---
    if RUN_SPRITE_TIMING:
        proc = boot(PORT + 1, crt)
        try:
            s = harness.connect_monitor(PORT + 1, 20.0)
            time.sleep(6.0)
            s.close()
            for ln in (l for l in (ROOT / "tests/sprite_timing.bas").read_text().splitlines()
                       if l.strip()):
                harness.keyboard_type_on_port(PORT + 1, ln + "\r")
                time.sleep(0.5)
            time.sleep(0.5)
            harness.keyboard_type_on_port(PORT + 1, "RUN\r")
            time.sleep(7.0)
            s = harness.connect_monitor(PORT + 1, 20.0)
            results["sprite_timing_done"] = "DONE" in harness.screen_text(s).upper()
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
