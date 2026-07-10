#!/usr/bin/env python3
"""Produce build/packaged.d81: a representative sample of the original
MDBASIC example programs (from the template mdbasic.d64) packaged into
self-contained auto-run PRGs by the REAL in-emulator PACKAGE tool, alongside
the sprite/font data files those programs load at runtime.

One cart VICE session loads each example from the D81 and drives the packager
(dopack entry) to write "<NAME>+" back to the same disk. Afterwards each
packaged PRG (where the example has observable output) is booted on a
cartridge-less VICE with LOAD"<NAME>+",8,1 and its behaviour asserted.

    tools/vice_pack_examples.py [--skip-verify]
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
import vice_pack_list_test as plt
import c64_basic_prg

BASEPORT = 7200
OUT_D81 = ROOT / "build" / "packaged.d81"

# (example name, screen text expected from the packaged auto-run; None = no
# text check -- verified by the memory/VIC probes below or packaging only)
EXAMPLES = [
    ("demo1", "SIMPLE SPRITE DEMO"),
    ("spritetest", None),
    ("playsprite", None),          # verified via sprite probes
    ("fonttest", None),            # verified via READY-without-error
    ("bubblesort", "RUNTIME:"),
    ("num functions", "C000"),
    ("trim$test", "THIS IS A TRIM$ TEST"),
    ("linetest", None),            # verified via bitmap mode/drawn RAM probe
    ("gamesounds", "GAME-LIKE SOUNDS"),
    ("pklist", plt.MARKER),        # LIST-parity test program (endless loop)
]
DATA_FILES = ["bird.spr", "font1", "font2", "font3", "font4", "font5"]

# Not on the template D64: compiled from vice_pack_list_test's source instead.
COMPILED = {"pklist": plt.SRC}


def packaged_name(example: str) -> str:
    return example.upper() + "+"


def build_disk_and_package(crt, dopack, port) -> None:
    entries = pt.extract_examples(
        [n for n, _ in EXAMPLES if n not in COMPILED] + DATA_FILES)
    for name, src in COMPILED.items():
        host = pt.WORKDIR / f"{name}_src.prg"
        host.write_bytes(c64_basic_prg.compile_basic(src, "mdbasic", 0x0801))
        entries.append((name, host))
    pt.make_work_d81(OUT_D81, entries)
    proc = pt.boot(port, crt, OUT_D81)
    try:
        harness.connect_monitor(port, 20.0).close()
        ok, _ = pt.wait_screen_on_port(port, ["READY."], 30.0)
        if not ok:
            raise RuntimeError("cart machine did not boot")
        for name, _ in EXAMPLES:
            print(f"  packaging {name!r} -> {packaged_name(name)!r}")
            pt.load_program(port, name)
            pt.package_one(port, dopack, packaged_name(name))
    finally:
        harness.shutdown_vice_on_port(proc, port)


def verify_one(port, name, expect) -> dict[str, bool]:
    """Boot plain VICE with the deliverable disk and auto-run one packaged
    program."""
    results = {}
    key = packaged_name(name)
    proc = pt.boot(port, None, OUT_D81)
    try:
        harness.connect_monitor(port, 20.0).close()
        pt.wait_screen_on_port(port, ["READY."], 30.0)
        harness.keyboard_type_on_port(port, f'LOAD"{key}",8,1\r')
        if expect:
            ok, _ = pt.wait_screen_on_port(port, [expect], 240.0, interval=2.0)
            results[f"{key} output"] = ok
        elif name == "playsprite":
            deadline = time.time() + 240.0
            ok = False
            while time.time() < deadline:
                spena = pt.mem_on_port(port, 0xD015, 0xD015)[0]
                if spena & 1 and pt.mem_on_port(port, 0x07F8, 0x07F8)[0] == 208:
                    ok = True
                    break
                time.sleep(2.0)
            results[f"{key} sprite"] = ok
        elif name == "linetest":
            deadline = time.time() + 240.0
            ok = False
            while time.time() < deadline:
                if pt.mem_on_port(port, 0xD011, 0xD011)[0] & 0x20:
                    ok = True
                    break
                # In warp mode this short drawing demo can enter bitmap mode,
                # finish, and have MDBASIC's immediate loop restore text mode
                # before the first host-side VIC probe.  Its completed bitmap
                # remains in RAM under the KERNAL, so accept that deterministic
                # result as well as observing the transient mode bit.
                if pt.mem_on_port(port, 0xE000, 0xE007, bank=1) == bytes.fromhex(
                        "55 5a 5a 7a 7d 7f 7f 7f"):
                    ok = True
                    break
                time.sleep(0.2)
            results[f"{key} bitmap"] = ok
        elif name == "fonttest":
            # runs ~10s of WAITs through five font loads, then SCREEN0/READY
            ok, scr = pt.wait_screen_on_port(port, ["READY."], 240.0, interval=2.0)
            results[f"{key} completes"] = ok and "ERROR" not in scr.upper()
    finally:
        harness.shutdown_vice_on_port(proc, port)
    return results


def main() -> int:
    skip_verify = "--skip-verify" in sys.argv
    pt.WORKDIR.mkdir(exist_ok=True)
    OUT_D81.parent.mkdir(exist_ok=True)
    crt, _dodocs = dt.build_cart()
    dopack = dt.label_addr("/tmp/menu.lst", "dopack")

    port_iter = iter(range(BASEPORT, BASEPORT + 1000))
    print("-- packaging the example sample --")
    build_disk_and_package(crt, dopack, next(port_iter))

    # every packaged file must exist with a sane size
    listing = pt.c1541(OUT_D81, "-list")
    results = {}
    for name, _ in EXAMPLES:
        results[f"{packaged_name(name)} on disk"] = (
            f'"{name.lower()}+"' in listing)

    if not skip_verify:
        print("-- verifying packaged programs on a cartridge-less machine --")
        for name, expect in EXAMPLES:
            if expect is None and name in ("spritetest", "gamesounds"):
                continue
            if expect is None and name not in ("playsprite", "linetest",
                                               "fonttest"):
                continue
            print(f"  running {packaged_name(name)!r}")
            results.update(verify_one(next(port_iter), name, expect))

    for k, v in results.items():
        print(f"  {'PASS' if v else 'FAIL'}  {k}")
    ok = all(results.values())
    print(("PASS" if ok else "FAIL") + f"  ({OUT_D81})")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
