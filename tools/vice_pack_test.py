#!/usr/bin/env python3
"""End-to-end tests of the MDBASIC PACKAGE tool (CTRL+RESTORE menu, P).

Flow under test: on the cart machine, load an example program from a D81,
drive the packager (via the `dopack` direct entry, or the real menu for the
menu test), let it write the packaged PRG back to the same D81 -- then, in a
SECOND, cartridge-less VICE, LOAD"NAME",8,1 that file and assert it auto-runs
with the same output as a hand-typed RUN on the cart machine.

The written file is also byte-compared against tools/pack_prg.py (the host-
side twin): sections built from the same program bytes, boot stub, and the
$8000-$BFFF RAM snapshot taken just before packaging (with the $8002/$8003
menu-handler unpatch the tool must perform, verified against the pristine
image too).

VICE 3.10 notes: the binary monitor pauses the machine while a connection is
open, so all polling here uses short-lived connections; a D81 needs an
explicit -drive8type 1581 under -default.

    tools/vice_pack_test.py [test ...]
"""
from __future__ import annotations

import struct
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import vice_prg_test as harness
import vice_docs_test as dt
import pack_prg

BASEPORT = 6980
WORKDIR = Path("/tmp/mdbasic_pack_test")


# ---------------------------------------------------------------- utilities

def boot(port, crt, disk=None):
    # -default: the user's vicerc can disable true drive emulation / add
    # device traps in combinations that hang cart+disk loads headless
    cmd = [harness.find_tool("x64sc"), "-default", "-silent", "-sounddev", "dummy",
           "-warp", "-binarymonitor",
           "-binarymonitoraddress", f"ip4://127.0.0.1:{port}"]
    if crt:
        cmd += ["-cartcrt", str(crt)]
    if disk:
        cmd += ["-drive8type", "1581", "-8", str(disk)]
    return subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)


def screen_on_port(port, tries=3):
    """Screen text over a fresh connection; retries on monitor sluggishness
    (under -warp plus heavy serial I/O a response can outlast the default
    2s socket timeout)."""
    for attempt in range(tries):
        s = harness.connect_monitor(port, 10.0)
        s.settimeout(15.0)
        try:
            return harness.screen_text(s)
        except (TimeoutError, OSError):
            if attempt == tries - 1:
                raise
            time.sleep(1.0)
        finally:
            s.close()


def wait_screen_on_port(port, expects, timeout, interval=1.0):
    deadline = time.time() + timeout
    last = ""
    ups = [e.upper() for e in expects]
    while time.time() < deadline:
        last = screen_on_port(port)
        up = last.upper()
        if all(e in up for e in ups):
            return True, last
        time.sleep(interval)
    return False, last


def mem_on_port(port, start, end, bank=0, tries=3):
    """One-shot memory read over a fresh connection. bank 1 = RAM (to see the
    MDBASIC image under the BASIC ROM). Retries on monitor sluggishness."""
    for attempt in range(tries):
        s = harness.connect_monitor(port, 10.0)
        s.settimeout(15.0)
        try:
            body = struct.pack("<BHHBH", 0, start, end, 0, bank)
            harness.monitor_cmd(s, 0x01, body)
            while True:
                rtype, err, data = harness.monitor_response(s)
                if rtype == 0x01:
                    if err:
                        raise RuntimeError(f"mem read error {err}")
                    count = struct.unpack("<H", data[:2])[0]
                    return data[2:2 + count]
        except (TimeoutError, OSError):
            if attempt == tries - 1:
                raise
            time.sleep(1.0)
        finally:
            s.close()


def wait_load_done(port, prev_vartab, timeout=90.0):
    """After typing LOAD"...",8 wait until VARTAB changes and stays stable."""
    deadline = time.time() + timeout
    stable = None
    while time.time() < deadline:
        vt = mem_on_port(port, 0x2D, 0x2E)
        vartab = vt[0] | vt[1] << 8
        ndx = mem_on_port(port, 0xC6, 0xC6)[0]
        if ndx == 0 and vartab != prev_vartab:
            if stable == vartab:
                return vartab
            stable = vartab
        time.sleep(1.0)
    raise TimeoutError("LOAD did not finish")


def load_program(port, cbmname):
    vt = mem_on_port(port, 0x2D, 0x2E)
    prev = vt[0] | vt[1] << 8
    harness.keyboard_type_on_port(port, f'LOAD"{cbmname.upper()}",8\r')
    return wait_load_done(port, prev)


def sys_stub(port, target):
    """Poke the synthetic-NMI frame stub at $c000 and SYS it (same mechanism
    as the docs/renum suites: past the CTRL gate, frame set up for the
    handler's NMI-tail RTI exit)."""
    s = harness.connect_monitor(port, 20.0)
    harness.mem_set(s, dt.STUB_ADDR, dt.nmi_frame_stub(target))
    s.close()
    harness.keyboard_type_on_port(port, f"SYS{dt.STUB_ADDR}\r")


def package_one(port, dopack, outname, write_timeout=300.0):
    """Drive one packaging run: dopack entry -> filename -> wait for DONE. ->
    keypress back to READY. Returns the status/DONE screen text."""
    sys_stub(port, dopack)
    ok, scr = wait_screen_on_port(port, ["FILENAME:"], 30.0)
    if not ok:
        raise TimeoutError(f"packager prompt did not appear:\n{scr}")
    harness.keyboard_type_on_port(port, outname + "\r")
    ok, scr = wait_screen_on_port(port, ["DONE."], write_timeout, interval=2.0)
    if not ok:
        raise TimeoutError(f"packager did not finish:\n{scr}")
    done_screen = scr
    harness.keyboard_type_on_port(port, " ")
    wait_screen_on_port(port, ["READY."], 20.0)
    return done_screen


def c1541(*args):
    proc = subprocess.run([harness.find_tool("c1541"), *map(str, args)],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"c1541 {args}: {proc.stdout}\n{proc.stderr}")
    return proc.stdout


def read_back(disk, cbmname, hostpath):
    c1541(disk, "-read", cbmname, hostpath)
    return Path(hostpath).read_bytes()


def make_work_d81(path, entries):
    """Fresh D81 with (cbmname, hostfile) entries."""
    path = Path(path)
    if path.exists():
        path.unlink()
    args = ["-format", "packwork,pw", "d81", path]
    for name, host in entries:
        args += ["-write", str(host), name]
    c1541(*args)
    return path


def extract_examples(names):
    """Pull example PRGs off the template mdbasic.d64 into WORKDIR."""
    out = []
    for name in names:
        host = WORKDIR / (name.replace(" ", "_").replace("$", "") + ".prg")
        c1541(ROOT / "mdbasic.d64", "-read", name, host)
        out.append((name, host))
    return out


def patched_stub():
    """The boot stub with newvec/initclk patched, as build_cart produced it
    (build_cart wrote /tmp/pack_stub.bin and /tmp/mdbasic.lst)."""
    return pack_prg.patch_stub_syms(
        Path("/tmp/pack_stub.bin").read_bytes(),
        pack_prg.lst_label_addr(Path("/tmp/mdbasic.lst"), "newvec"),
        pack_prg.lst_label_addr(Path("/tmp/mdbasic.lst"), "initclk"))


# ------------------------------------------------------------------- tests

def t_menu(crt, dopack, domenu, next_port):
    """The real menu path: P=PACKAGE listed above F7=CONVERT, P launches the
    packager, RUN/STOP at the prompt returns to a restored screen."""
    port = next_port()
    proc = boot(port, crt)
    results = {}
    try:
        harness.connect_monitor(port, 20.0).close()
        wait_screen_on_port(port, ["READY."], 30.0)
        harness.keyboard_type_on_port(port, '10 PRINT"ZZPACKMARK"\r')
        time.sleep(0.5)
        sys_stub(port, domenu)
        ok, scr = wait_screen_on_port(port, ["P=PACKAGE", "F7=CONVERT"], 20.0)
        results["menu_shows_package"] = ok
        rows = scr.splitlines() if ok else []
        results["menu_package_above_f7"] = (
            ok and rows.index("P=PACKAGE") + 1 == rows.index("F7=CONVERT"))
        harness.keyboard_type_on_port(port, "P")   # PETSCII $50 = KEY_P
        ok, _ = wait_screen_on_port(port, ["MDBASIC PACKAGE", "FILENAME:"], 20.0)
        results["menu_p_launches_tool"] = ok
        harness.keyboard_type_on_port(port, "\x03")      # RUN/STOP cancels
        ok, scr = wait_screen_on_port(port, ["READY.", "ZZPACKMARK"], 20.0)
        results["cancel_restores_screen"] = ok
    finally:
        harness.shutdown_vice_on_port(proc, port)
    return results


def t_package_and_run(crt, dopack, domenu, next_port):
    """Package NUM FUNCTIONS on the cart machine, byte-verify the file, then
    auto-run it on a cartridge-less machine and compare the program output
    with a hand-typed RUN on the cart machine (the reference)."""
    results = {}
    examples = extract_examples(["num functions"])
    disk = make_work_d81(WORKDIR / "work.d81", examples)

    port = next_port()
    proc = boot(port, crt, disk)
    try:
        harness.connect_monitor(port, 20.0).close()
        wait_screen_on_port(port, ["READY."], 30.0)
        vartab = load_program(port, "num functions")
        prog = mem_on_port(port, 0x0801, vartab - 1)
        # image as the tool must emit it: RAM snapshot with the $8002/$8003
        # menu-handler patch undone from REALGONE
        image = bytearray(mem_on_port(port, 0x8000, 0xBFFF, bank=1))
        realgone = mem_on_port(port, 0x03F8, 0x03F9)
        results["image_nmi_patched"] = image[2] | image[3] << 8 == 0x033C
        image[2], image[3] = realgone[0], realgone[1]
        package_one(port, dopack, "NFPACK")
        # reference run: same machine, same program, hand-typed RUN
        harness.keyboard_type_on_port(port, "RUN\r")
        ok, ref_screen = wait_screen_on_port(port, ["C000"], 30.0)
        results["reference_runs"] = ok
    finally:
        harness.shutdown_vice_on_port(proc, port)

    # --- host-side byte verification ---
    actual = read_back(disk, "nfpack", WORKDIR / "nfpack.prg")
    stub = patched_stub()
    expected = pack_prg.build_packaged(bytes(prog), bytes(image), stub)
    results["file_matches_oracle"] = actual == expected
    if not results["file_matches_oracle"]:
        diffs = [i for i, (a, b) in enumerate(zip(actual, expected)) if a != b]
        print(f"    oracle mismatch: len {len(actual)} vs {len(expected)}, "
              f"first diffs {[hex(d) for d in diffs[:8]]}")
    # image drift check: RAM snapshot (unpatched) vs the pristine built image
    pristine = pack_prg.load_image_prg(ROOT / "mdbasic.prg")
    drift = sum(1 for a, b in zip(bytes(image), pristine) if a != b)
    results["image_matches_pristine"] = drift == 0
    if drift:
        print(f"    NOTE: RAM image differs from pristine in {drift} bytes")

    # --- run the packaged file on a cartridge-less machine ---
    port = next_port()
    proc = boot(port, None, disk)
    try:
        harness.connect_monitor(port, 20.0).close()
        wait_screen_on_port(port, ["READY."], 30.0)
        harness.keyboard_type_on_port(port, 'LOAD"NFPACK",8,1\r')
        ok, pack_screen = wait_screen_on_port(port, ["C000"], 180.0, interval=2.0)
        results["packaged_autoruns"] = ok
        if ok:
            # program output must equal the reference run's: rows 0-6 are the
            # deterministic prints, row 7 is TIME (boot-clock dependent)
            ref_rows = ref_screen.splitlines()[:7]
            pack_rows = pack_screen.splitlines()[:7]
            results["output_matches_reference"] = ref_rows == pack_rows
            if ref_rows != pack_rows:
                print(f"    ref  rows: {ref_rows}")
                print(f"    pack rows: {pack_rows}")
        # MDBASIC fully installed: MEMSIZ=$7fff, CBM80 signature in place
        memsiz = mem_on_port(port, 0x37, 0x38)
        results["memsiz_7fff"] = memsiz == b"\xff\x7f"
        cbm80 = mem_on_port(port, 0x8004, 0x8008)
        results["cbm80_present"] = cbm80 == b"\xc3\xc2\xcd\x38\x30"
    finally:
        harness.shutdown_vice_on_port(proc, port)
    return results


def t_overwrite(crt, dopack, domenu, next_port):
    """Packaging onto an existing filename overwrites it cleanly."""
    results = {}
    examples = extract_examples(["trim$test", "bubblesort"])
    disk = make_work_d81(WORKDIR / "overwrite.d81", examples)

    port = next_port()
    proc = boot(port, crt, disk)
    try:
        harness.connect_monitor(port, 20.0).close()
        wait_screen_on_port(port, ["READY."], 30.0)
        vartab = load_program(port, "bubblesort")
        bubble = mem_on_port(port, 0x0801, vartab - 1)
        package_one(port, dopack, "PACKED")
        # now package a DIFFERENT program under the SAME name (the disk image
        # can only be inspected host-side after VICE lets go of it, so the
        # proof of overwrite is the final content carrying the second program)
        vartab = load_program(port, "trim$test")
        prog = mem_on_port(port, 0x0801, vartab - 1)
        package_one(port, dopack, "PACKED")
    finally:
        harness.shutdown_vice_on_port(proc, port)

    second = read_back(disk, "packed", WORKDIR / "packed2.prg")
    off = 2 + (0x0801 - 0x0302)          # header + $0302..$0800 block
    results["overwrite_has_new_program"] = (
        second[off:off + len(prog)] == bytes(prog)
        and len(second) == off + len(prog) + 0x4000)
    results["overwrite_dropped_old_program"] = (
        second[off:off + len(bubble)] != bytes(bubble))
    # exactly one directory entry under that name
    listing = c1541(disk, "-list")
    results["overwrite_single_entry"] = listing.count('"packed"') == 1

    # and it still runs (TRIM$ output check)
    port = next_port()
    proc = boot(port, None, disk)
    try:
        harness.connect_monitor(port, 20.0).close()
        wait_screen_on_port(port, ["READY."], 30.0)
        harness.keyboard_type_on_port(port, 'LOAD"PACKED",8,1\r')
        ok, _ = wait_screen_on_port(port, ["THIS IS A TRIM$ TEST", "RESULT"],
                                    180.0, interval=2.0)
        results["overwritten_autoruns"] = ok
    finally:
        harness.shutdown_vice_on_port(proc, port)
    return results


def t_datafile(crt, dopack, domenu, next_port):
    """A packaged program that LOADs a sprite file at runtime finds it on the
    disk next to the packaged PRG (data files are NOT bundled)."""
    results = {}
    examples = extract_examples(["playsprite", "bird.spr"])
    disk = make_work_d81(WORKDIR / "datafile.d81", examples)

    port = next_port()
    proc = boot(port, crt, disk)
    try:
        harness.connect_monitor(port, 20.0).close()
        wait_screen_on_port(port, ["READY."], 30.0)
        load_program(port, "playsprite")
        package_one(port, dopack, "PLAYSPRITE+")
    finally:
        harness.shutdown_vice_on_port(proc, port)

    port = next_port()
    proc = boot(port, None, disk)
    try:
        harness.connect_monitor(port, 20.0).close()
        wait_screen_on_port(port, ["READY."], 30.0)
        harness.keyboard_type_on_port(port, 'LOAD"PLAYSPRITE+",8,1\r')
        deadline = time.time() + 240.0
        ok = False
        while time.time() < deadline:
            spena = mem_on_port(port, 0xD015, 0xD015)[0]
            sprptr = mem_on_port(port, 0x07F8, 0x07F8)[0]
            if spena & 1 and sprptr == 208:    # bird.spr block, sprite on
                ok = True
                break
            time.sleep(2.0)
        results["datafile_loaded_and_animating"] = ok
    finally:
        harness.shutdown_vice_on_port(proc, port)
    return results


REGISTRY = [
    ("menu", t_menu),
    ("package_and_run", t_package_and_run),
    ("overwrite", t_overwrite),
    ("datafile", t_datafile),
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
