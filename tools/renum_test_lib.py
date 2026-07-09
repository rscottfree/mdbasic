#!/usr/bin/env python3
"""Shared driver helpers + CLI runner for the renum/move tool's VICE tests.

`vice_renum_test.py`, `vice_renum_single_line_move_test.py`, and
`vice_renum_move_overlap_test.py` each define a registry of named tests
(`[(name, fn), ...]`, `fn(crt, dorenum, domenu, next_port) -> dict[str, bool]`)
and drive it through `run_cli()` here, so every file is runnable standalone
(no args = every test in that file's registry; names = just those) and
`vice_renum_test.py` can also union all three registries into one command
that covers the whole suite. `next_port` is a zero-arg callable handed to
each test so ports stay unique across an entire run regardless of which
subset of tests (from however many registries) actually executes -- VICE
needs a fresh port per boot even though boots happen strictly sequentially.

    tools/renum_test_lib.py
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import vice_prg_test as harness
import vice_docs_test as dt

BASEPORT = 6760
DOMOVE = None
DOCOPY = None
DOCONVERT = None


def boot(port, crt):
    proc = subprocess.Popen(
        [harness.find_tool("x64sc"), "-silent", "-sounddev", "dummy",
         "-binarymonitor", "-binarymonitoraddress", f"ip4://127.0.0.1:{port}",
         "-cartcrt", str(crt)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return proc


def type_lines(port, lines):
    for ln in lines:
        harness.keyboard_type_on_port(port, ln + "\r")
        time.sleep(0.3)


def read_prog(sock):
    """Raw program bytes $0801..VARTAB (exclusive)."""
    vt = harness.mem_get(sock, 0x2D, 0x2E)
    end = vt[0] | (vt[1] << 8)
    return harness.mem_get(sock, 0x0801, end - 1)


def open_tool(port, dorenum):
    """Poke the synthetic-NMI stub and SYS it -> renum tool REPL opens."""
    s = harness.connect_monitor(port, 20.0)
    harness.mem_set(s, dt.STUB_ADDR, dt.nmi_frame_stub(dorenum))
    s.close()
    harness.keyboard_type_on_port(port, f"SYS{dt.STUB_ADDR}\r")
    time.sleep(1.0)


def cmd(port, text):
    harness.keyboard_type_on_port(port, text + "\r")
    time.sleep(0.8)


def walk_links(sock):
    """Follow the line-link chain from $0801 and return the list of line numbers,
    or None if the chain is malformed (a corrupted pointer table). This is the
    core anti-'trashed pointers' check: links must move strictly forward, stay
    inside the program, land on 4-byte-aligned line records, and end at $0000
    within VARTAB."""
    vt = harness.mem_get(sock, 0x2D, 0x2E)
    vartab = vt[0] | (vt[1] << 8)
    mem = harness.mem_get(sock, 0x0800, vartab + 1)  # index by absolute addr - 0x0800
    def b(a): return mem[a - 0x0800]
    nums, addr, prev = [], 0x0801, 0x0800
    for _ in range(1000):
        link = b(addr) | (b(addr + 1) << 8)
        if link == 0:
            return nums
        if not (addr < link <= vartab) or link <= prev:
            return None        # non-forward / out-of-range link -> corrupt
        nums.append(b(addr + 2) | (b(addr + 3) << 8))
        prev, addr = addr, link
    return None


def finish(proc):
    harness.shutdown_vice(proc)


def finish_on_port(proc, port):
    harness.shutdown_vice_on_port(proc, port)


def run_cli(registry: list[tuple[str, callable]], argv: list[str]) -> int:
    """Run the named tests in `registry` selected by `argv` (all of them if
    `argv` is empty), print a PASS/FAIL line per result key plus an overall
    verdict, and return the process exit code."""
    names = [n for n, _ in registry]
    if argv:
        unknown = [a for a in argv if a not in names]
        if unknown:
            print(f"unknown test(s): {', '.join(unknown)}")
            print(f"available: {', '.join(names)}")
            return 2
        selected = [(n, f) for n, f in registry if n in argv]
    else:
        selected = registry

    crt, _dodocs = dt.build_cart()
    global DOMOVE, DOCOPY, DOCONVERT
    dorenum = dt.label_addr("/tmp/menu.lst", "dorenum")
    DOMOVE = dt.label_addr("/tmp/menu.lst", "domove")
    DOCOPY = dt.label_addr("/tmp/menu.lst", "docopy")
    DOCONVERT = dt.label_addr("/tmp/menu.lst", "doconvert")
    domenu = dt.label_addr("/tmp/menu.lst", "domenu")
    print(f"dorenum=${dorenum:04x} domove=${DOMOVE:04x} "
          f"docopy=${DOCOPY:04x} doconvert=${DOCONVERT:04x} domenu=${domenu:04x}")

    port_iter = iter(range(BASEPORT, BASEPORT + 1000))
    next_port = lambda: next(port_iter)

    results = {}
    for name, fn in selected:
        print(f"-- {name} --")
        results.update(fn(crt, dorenum, domenu, next_port))

    for k, v in results.items():
        print(f"  {'PASS' if v else 'FAIL'}  {k}")
    ok = all(results.values())
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1
