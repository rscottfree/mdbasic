#!/usr/bin/env python3
"""End-to-end tests of the PACKAGE tool's CRUNCH option (CTRL+RESTORE menu,
P, then Y at the crunch prompt).

The crunched variant is an LZ-compressed self-extracting package: same
auto-run contract as the plain one (LOAD"NAME",8,1 on a stock C64), smaller
file. The native 6502 encoder in pack_tool.asm mirrors tools/pack_prg.py's
lz_crunch operation-for-operation, so the file the tool writes is
byte-compared against pack_prg.build_crunched as the oracle -- the same
proof the plain packager has.

Tests:
  codec          host-only: round-trips + edge cases + the CLI --crunch path
  crunch_and_run cart machine packages with Y, file is byte-identical to the
                 oracle, the plain variant still matches its own oracle, the
                 crunched file is smaller, auto-runs on a cartridge-less
                 machine with output equal to a hand-typed RUN, and the
                 machine stays a full MDBASIC session (LIST decodes, KEY
                 table live) after the program ends.

    tools/vice_crunch_test.py [test ...]
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import vice_prg_test as harness
import vice_docs_test as dt
import vice_pack_test as pt
import pack_prg
import c64_basic_prg

BASEPORT = 7300
WORKDIR = pt.WORKDIR


def patched_crunch_stub():
    """The crunch stub with newvec/initclk patched, as build_cart produced it
    (build_cart wrote /tmp/crunch_stub.bin and /tmp/mdbasic.lst)."""
    return pack_prg.patch_stub_syms(
        Path("/tmp/crunch_stub.bin").read_bytes(),
        pack_prg.lst_label_addr(Path("/tmp/mdbasic.lst"), "newvec"),
        pack_prg.lst_label_addr(Path("/tmp/mdbasic.lst"), "initclk"))


# ------------------------------------------------------------------- tests

def t_codec(crt, dopack, domenu, next_port):
    """Host-only codec properties: round-trips over representative and
    pathological inputs, the decrunch-overlap safety check, and the
    pack_prg.py --crunch CLI."""
    results = {}
    image = pack_prg.load_image_prg(ROOT / "mdbasic.prg")
    cases = {
        "image": image,
        "zeros": bytes(4096),
        "rle": b"AB" * 2000,
        "random": os.urandom(4096),
        "tiny": b"\x01",
        "pair": b"\x01\x01",
    }
    ok = True
    for name, data in cases.items():
        stream = pack_prg.lz_crunch(data)
        back, used = pack_prg.lz_decrunch(stream, len(data))
        if back != data or used != len(stream):
            print(f"    codec round-trip failed: {name}")
            ok = False
    results["codec_round_trips"] = ok
    results["codec_compresses_image"] = len(pack_prg.lz_crunch(image)) < len(image) * 0.85

    # hardest case: a near-maximal, incompressible program. Its chunk expands
    # (9 bits per literal), but with the real image always compressing to
    # ~12.4K the file still ends below $d000 and the decrunch-overlap slack
    # stays positive -- build_crunched's internal checks prove both, so the
    # property here is simply that it builds (the tool needs no size guard:
    # MEMSIZ caps programs at $7fff on the packing machine).
    lines = bytearray()
    num = 0
    while len(lines) < 0x6E00:
        body = b"\x8f" + os.urandom(58).replace(b"\x00", b"\x01")  # REM junk
        lines += b"\xff\xff" + num.to_bytes(2, "little") + body + b"\x00"
        num += 1                     # relink() rewrites the link words
    big = bytes(lines) + b"\x00\x00"
    built = pack_prg.build_crunched(big, image, bytes(300))
    results["worst_case_program_builds"] = len(built) > 0

    # CLI smoke test: --crunch writes the same bytes build_crunched returns
    src = '10 PRINT "CLI"\n20 END\n'
    prg = WORKDIR / "cli_src.prg"
    prg.write_bytes(c64_basic_prg.compile_basic(src, "mdbasic", 0x0801))
    out = WORKDIR / "cli_crunched.prg"
    subprocess.run(
        [sys.executable, str(ROOT / "tools/pack_prg.py"),
         "--image", str(ROOT / "mdbasic.prg"), "--lst", "/tmp/mdbasic.lst",
         "--crunch", "--crunch-stub", "/tmp/crunch_stub.bin",
         str(prg), str(out)], check=True, capture_output=True)
    expect = pack_prg.build_crunched(prg.read_bytes()[2:], image,
                                     patched_crunch_stub())
    results["cli_crunch_matches_library"] = out.read_bytes() == expect
    return results


def t_crunch_and_run(crt, dopack, domenu, next_port):
    """Package NUM FUNCTIONS twice (crunched + plain), byte-verify both
    against their oracles, auto-run the crunched file on a cartridge-less
    machine and compare its output with a hand-typed RUN, then prove the
    session survives the program's end (LIST decoding, KEY table)."""
    results = {}
    examples = pt.extract_examples(["num functions"])
    disk = pt.make_work_d81(WORKDIR / "crunch.d81", examples)

    port = next_port()
    proc = pt.boot(port, crt, disk)
    try:
        harness.connect_monitor(port, 20.0).close()
        pt.wait_screen_on_port(port, ["READY."], 30.0)
        vartab = pt.load_program(port, "num functions")
        prog = pt.mem_on_port(port, 0x0801, vartab - 1)
        image = bytearray(pt.mem_on_port(port, 0x8000, 0xBFFF, bank=1))
        realgone = pt.mem_on_port(port, 0x03F8, 0x03F9)
        image[2], image[3] = realgone[0], realgone[1]
        pt.package_one(port, dopack, "NFCRUNCH", crunch=True)
        pt.package_one(port, dopack, "NFPLAIN", crunch=False)
        # reference run: same machine, same program, hand-typed RUN
        harness.keyboard_type_on_port(port, "RUN\r")
        ok, ref_screen = pt.wait_screen_on_port(port, ["C000"], 30.0)
        results["reference_runs"] = ok
    finally:
        harness.shutdown_vice_on_port(proc, port)

    # --- host-side byte verification, both variants ---
    crunched = pt.read_back(disk, "nfcrunch", WORKDIR / "nfcrunch.prg")
    plain = pt.read_back(disk, "nfplain", WORKDIR / "nfplain.prg")
    expected = pack_prg.build_crunched(bytes(prog), bytes(image),
                                       patched_crunch_stub())
    results["crunched_matches_oracle"] = crunched == expected
    if not results["crunched_matches_oracle"]:
        diffs = [i for i, (a, b) in enumerate(zip(crunched, expected))
                 if a != b]
        print(f"    oracle mismatch: len {len(crunched)} vs {len(expected)},"
              f" first diffs {[hex(d) for d in diffs[:8]]}")
    results["plain_still_matches_oracle"] = plain == pack_prg.build_packaged(
        bytes(prog), bytes(image), pt.patched_stub())
    results["crunched_is_smaller"] = len(crunched) < len(plain)
    print(f"    plain {len(plain)} bytes -> crunched {len(crunched)} bytes "
          f"({100 * len(crunched) // len(plain)}%)")

    # --- auto-run on a cartridge-less machine ---
    port = next_port()
    proc = pt.boot(port, None, disk)
    try:
        harness.connect_monitor(port, 20.0).close()
        pt.wait_screen_on_port(port, ["READY."], 30.0)
        harness.keyboard_type_on_port(port, 'LOAD"NFCRUNCH",8,1\r')
        ok, pack_screen = pt.wait_screen_on_port(port, ["C000"], 180.0,
                                                 interval=2.0)
        results["crunched_autoruns"] = ok
        if ok:
            # rows 0-6 are the deterministic prints, row 7 is TIME
            ref_rows = ref_screen.splitlines()[:7]
            pack_rows = pack_screen.splitlines()[:7]
            results["output_matches_reference"] = ref_rows == pack_rows
            if ref_rows != pack_rows:
                print(f"    ref  rows: {ref_rows}")
                print(f"    pack rows: {pack_rows}")
        # MDBASIC fully installed, program parked at $0801
        results["memsiz_7fff"] = pt.mem_on_port(port, 0x37, 0x38) == b"\xff\x7f"
        results["cbm80_present"] = (pt.mem_on_port(port, 0x8004, 0x8008)
                                    == b"\xc3\xc2\xcd\x38\x30")
        vt = pt.mem_on_port(port, 0x2D, 0x2E)
        results["vartab_points_at_program_end"] = (
            vt[0] | vt[1] << 8) == 0x0801 + len(prog)
        # the session stays a full MDBASIC environment after the program ends
        harness.keyboard_type_on_port(port, "LIST\r")
        ok, _ = pt.wait_screen_on_port(port, ["10 ", "READY."], 30.0)
        results["list_decodes_after_run"] = ok
        harness.keyboard_type_on_port(port, "KEY LIST\r")
        ok, _ = pt.wait_screen_on_port(port, ['KEY1,"LIST"'], 30.0)
        results["function_key_table_live"] = ok
    finally:
        harness.shutdown_vice_on_port(proc, port)
    return results


REGISTRY = [
    ("codec", t_codec),
    ("crunch_and_run", t_crunch_and_run),
]


def main() -> int:
    argv = sys.argv[1:]
    names = [n for n, _ in REGISTRY]
    unknown = [a for a in argv if a not in names]
    if unknown:
        print(f"unknown test(s): {', '.join(unknown)}; available: {', '.join(names)}")
        return 2
    selected = [(n, f) for n, f in REGISTRY if not argv or n in argv]

    WORKDIR.mkdir(exist_ok=True)
    crt, _dodocs = dt.build_cart()
    dopack = dt.label_addr("/tmp/menu.lst", "dopack")
    domenu = dt.label_addr("/tmp/menu.lst", "domenu")
    print(f"dopack=${dopack:04x} domenu=${domenu:04x}")

    port_iter = iter(range(BASEPORT, BASEPORT + 1000))
    next_port = lambda: next(port_iter)

    results = {}
    for name, fn in selected:
        print(f"-- {name} --")
        results.update(fn(crt, dopack, domenu, next_port))

    for k, v in results.items():
        print(f"  {'PASS' if v else 'FAIL'}  {k}")
    ok = all(results.values())
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
