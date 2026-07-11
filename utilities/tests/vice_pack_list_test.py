#!/usr/bin/env python3
"""LIST-text parity between a disk-PRG MDBASIC install and a packaged PRG.

The reference environment is the non-cartridge install path from README.md:
boot a plain C64, LOAD"MDBASIC",8,1 from disk, SYS64738.  There a source
program is loaded whose every line carries MDBASIC extension tokens that
stock BASIC V2 would tokenize/list differently -- including OFF, the token
$cb that stock BASIC owns as GO (MDBASIC renames it), which a stock LIST
would render as GO.  Its LIST text is captured, then the program is RUN to
its marker and broken out of its endless loop.

The same source file is then packaged with the cartridge packager (dopack),
and the package auto-run on a second, cartridge-less machine: the marker
must print, RUN/STOP (the same ISTOP result a real keypress produces) must
break the loop, and the standalone LIST text must be character-identical to
the reference listing -- proving both environments decode the same token
bytes to the same keywords, not just that the bytes survived packaging.

    tools/vice_pack_list_test.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import vice_prg_test as harness
import vice_docs_test as dt
import vice_pack_test as pt
import c64_basic_prg

BASEPORT = 7150
WORKDIR = Path("/tmp/mdbasic_pack_list_test")

# Every line uses at least one MDBASIC token: SCREEN+CLR, SPRITE/ERR + OFF
# (the repurposed GO token $cb), HEX$, MOD, ELSE, and IF..THEN..:ELSE flow.
# The marker is split across string literals so the RUN output never appears
# verbatim in the LIST text (and vice versa).
SRC = """\
10 SCREEN CLR
20 SPRITE OFF
30 ERR OFF
40 A$=HEX$(48879)
50 B=MOD(14,4)
60 IF B=2 THEN C$="Y":ELSE C$="N"
70 PRINT "PK";"MARK ";A$;C$
80 GOTO 80
"""
EXPECTED_ROWS = SRC.splitlines()
MARKER = "PKMARK BEEFY"          # HEX$(48879)="BEEF", MOD(14,4)=2 -> C$="Y"
LOOP_LINE = 80


def load_absolute(port, cbmname):
    """LOAD"name",8,1 (non-relocating; direct mode still updates VARTAB from
    the KERNAL end address, which wait_load_done keys on)."""
    vt = pt.mem_on_port(port, 0x2D, 0x2E)
    prev = vt[0] | vt[1] << 8
    harness.keyboard_type_on_port(port, f'LOAD"{cbmname.upper()}",8,1\r')
    pt.wait_load_done(port, prev)


def wait_banner(port, timeout=30.0):
    """After SYS64738 the reset clears the screen: the MDBASIC banner is up
    once MDBASIC+READY show without the pre-reset SYS64738 echo."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        up = pt.screen_on_port(port).upper()
        if "MDBASIC" in up and "READY." in up and "SYS64738" not in up:
            return True
        time.sleep(0.5)
    return False


def break_program(port, line):
    """Force the Z=1 STOP result a real RUN/STOP keypress returns through the
    ISTOP vector (same technique as vice_pack_test), then restore the vector."""
    saved = pt.mem_on_port(port, 0x0328, 0x0329)
    s = harness.connect_monitor(port, 20.0)
    harness.mem_set(s, 0x03F0, b"\xa9\x00\x60")     # lda #0 / rts
    harness.mem_set(s, 0x0328, b"\xf0\x03")
    s.close()
    ok, _ = pt.wait_screen_on_port(port, [f"BREAK IN {line}", "READY."], 30.0)
    s = harness.connect_monitor(port, 20.0)
    harness.mem_set(s, 0x0328, bytes(saved))
    s.close()
    return ok


def capture_listing(port, timeout=30.0):
    """Type LIST and return the screen rows between the LIST echo and the
    following READY. exactly as displayed (LIST opens with a CR, so blank
    edge rows are dropped)."""
    harness.keyboard_type_on_port(port, "LIST\r")
    deadline = time.time() + timeout
    while time.time() < deadline:
        rows = pt.screen_on_port(port).splitlines()
        starts = [i for i, r in enumerate(rows) if r.strip() == "LIST"]
        if starts:
            body = []
            for r in rows[starts[-1] + 1:]:
                if r.strip() == "READY.":
                    while body and not body[-1]:
                        body.pop()
                    while body and not body[0]:
                        body.pop(0)
                    if body:
                        return body
                    break
                body.append(r)
        time.sleep(0.5)
    raise TimeoutError(f"LIST output did not complete:\n"
                       + pt.screen_on_port(port))


def run_test(crt, dopack, next_port):
    results = {}
    source_prg = WORKDIR / "pklist_src.prg"
    source_prg.write_bytes(c64_basic_prg.compile_basic(SRC, "mdbasic", 0x0801))
    disk = pt.make_work_d81(WORKDIR / "packlist.d81",
                            [("mdbasic", Path("/tmp/mdbasic.prg")),   # as build_cart assembled it
                             ("pklist src", source_prg)])

    # --- reference: the disk-PRG install (no cartridge anywhere) ---
    port = next_port()
    proc = pt.boot(port, None, disk)
    ref_rows = []
    try:
        harness.connect_monitor(port, 20.0).close()
        pt.wait_screen_on_port(port, ["READY."], 30.0)
        load_absolute(port, "mdbasic")
        harness.keyboard_type_on_port(port, "SYS64738\r")
        results["prg_install_banner"] = wait_banner(port)
        results["prg_install_memsiz_7fff"] = (
            pt.mem_on_port(port, 0x37, 0x38) == b"\xff\x7f")
        pt.load_program(port, "pklist src")
        ref_rows = capture_listing(port)
        harness.keyboard_type_on_port(port, "RUN\r")
        ok, _ = pt.wait_screen_on_port(port, [MARKER], 30.0)
        results["reference_marker_prints"] = ok
        results["reference_break_from_loop"] = break_program(port, LOOP_LINE)
    finally:
        harness.shutdown_vice_on_port(proc, port)

    # The $cb byte in line 20 must already list as OFF here, not stock GO.
    results["reference_lists_off_not_go"] = "20 SPRITE OFF" in ref_rows
    results["reference_matches_source_text"] = ref_rows == EXPECTED_ROWS
    if ref_rows != EXPECTED_ROWS:
        print(f"    reference rows: {ref_rows}")

    # --- package the identical source file on the cart machine ---
    port = next_port()
    proc = pt.boot(port, crt, disk)
    try:
        harness.connect_monitor(port, 20.0).close()
        pt.wait_screen_on_port(port, ["READY."], 30.0)
        pt.load_program(port, "pklist src")
        pt.package_one(port, dopack, "PKLIST")
    finally:
        harness.shutdown_vice_on_port(proc, port)

    # --- standalone: auto-run the package on a cartridge-less machine ---
    port = next_port()
    proc = pt.boot(port, None, disk)
    pack_rows = []
    try:
        harness.connect_monitor(port, 20.0).close()
        pt.wait_screen_on_port(port, ["READY."], 30.0)
        harness.keyboard_type_on_port(port, 'LOAD"PKLIST",8,1\r')
        ok, _ = pt.wait_screen_on_port(port, [MARKER], 240.0, interval=2.0)
        results["packaged_marker_prints"] = ok
        results["packaged_break_from_loop"] = break_program(port, LOOP_LINE)
        pack_rows = capture_listing(port)
    finally:
        harness.shutdown_vice_on_port(proc, port)

    results["listing_text_identical"] = bool(ref_rows) and ref_rows == pack_rows
    if ref_rows != pack_rows:
        print(f"    reference listing: {ref_rows}")
        print(f"    packaged  listing: {pack_rows}")
    return results


def main() -> int:
    WORKDIR.mkdir(exist_ok=True)
    crt, _dodocs = dt.build_cart()
    dopack = dt.label_addr("/tmp/menu.lst", "dopack")
    print(f"dopack=${dopack:04x}")

    port_iter = iter(range(BASEPORT, BASEPORT + 1000))
    results = run_test(crt, dopack, lambda: next(port_iter))

    for k, v in results.items():
        print(f"  {'PASS' if v else 'FAIL'}  {k}")
    ok = all(results.values())
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
