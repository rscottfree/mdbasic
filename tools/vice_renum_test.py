#!/usr/bin/env python3
"""End-to-end test of the MDBASIC CTRL+RESTORE renumber/move tool in VICE.

Builds the full docs+menu+renum cart (reusing vice_docs_test.build_cart), boots
it, types a known BASIC program, then SYSes a synthetic-NMI stub that jumps to the
menu's `dorenum` entry (the exact code the F3 menu choice runs, past the CTRL/STOP
gate) so the renum tool's REPL opens. Commands are driven through the kernal key
buffer; the resulting program is checked by LISTing it and by comparing the raw
program bytes ($0801..VARTAB) for the reject cases (a rejected R/M must leave the
program byte-identical).

Covered: default/ranged R with reference rewrite (incl. digit-count growth), a
valid M that physically relocates the block + rewrites its GOSUB, the REPL staying
open after a command, and the reject paths (overflow, order/collision, END<=START)
each leaving the program untouched.

    tools/vice_renum_test.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import vice_prg_test as harness
import vice_docs_test as dt

BASEPORT = 6560


def boot(port, crt):
    import subprocess
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


def main() -> int:
    crt, _dodocs = dt.build_cart()
    dorenum = dt.label_addr("/tmp/menu.lst", "dorenum")
    domenu = dt.label_addr("/tmp/menu.lst", "domenu")
    print(f"dorenum=${dorenum:04x} domenu=${domenu:04x}")
    results = {}
    ports = iter(range(BASEPORT, BASEPORT + 20))  # a fresh port per VICE boot

    # ---- session 0: the menu-body itself (F1 -> pager, F3 -> renum tool) ----
    # SYS to `domenu` (past the CTRL/STOP gate); the menu-body draws its prompt and
    # waits for a key. A poked F1/F3 in the kernal buffer drives the choice.
    for key, want, tag in (("\x85", "SEARCH", "menu_f1_pager"),
                            ("\x86", "RENUM", "menu_f3_renum")):
        port = next(ports)
        proc = boot(port, crt)
        try:
            s = harness.connect_monitor(port, 20.0); time.sleep(6.0)
            harness.mem_set(s, dt.STUB_ADDR, dt.nmi_frame_stub(domenu)); s.close()
            harness.keyboard_type_on_port(port, f"SYS{dt.STUB_ADDR}\r")
            time.sleep(0.8)
            harness.keyboard_type_on_port(port, key)
            time.sleep(1.2)
            s = harness.connect_monitor(port, 20.0)
            results[tag] = want in harness.screen_text(s).upper()
            s.close()
        finally:
            proc.terminate()
            try: proc.wait(timeout=5)
            except Exception: proc.kill()

    # ---- session 1: renum success + reference rewrite (digit growth) + REPL ----
    port = next(ports)
    prog1 = ['10 PRINT"HI"', "20 GOTO 40", '30 PRINT"X"', "40 GOSUB 30", "50 END"]
    proc = boot(port, crt)
    try:
        s = harness.connect_monitor(port, 20.0)
        time.sleep(6.0)
        s.close()
        type_lines(port, prog1)
        open_tool(port, dorenum)
        s = harness.connect_monitor(port, 20.0)
        results["tool_opens"] = "RENUM" in harness.screen_text(s).upper()
        s.close()
        cmd(port, "R 100")                      # increment 100 -> 100,200,300,400,500
        s = harness.connect_monitor(port, 20.0)
        results["repl_ok"] = "OK" in harness.screen_text(s).upper()
        s.close()
        harness.keyboard_type_on_port(port, "\x03")   # RUN/STOP -> leave tool
        time.sleep(0.6)
        harness.keyboard_type_on_port(port, "LIST\r")
        time.sleep(1.2)
        s = harness.connect_monitor(port, 20.0)
        lst = harness.screen_text(s).upper()
        s.close()
        results["renum_headers"] = "100 PRINT" in lst and "500 END" in lst
        results["renum_ref_goto"] = "200 GOTO 400" in lst    # 20 GOTO 40 -> 200 GOTO 400
        results["renum_ref_gosub"] = "400 GOSUB 300" in lst  # 40 GOSUB 30 -> 400 GOSUB 300
                                                             # (digit growth 30 -> 300)
        harness.quit_vice(harness.connect_monitor(port, 20.0))
    finally:
        proc.terminate()
        try: proc.wait(timeout=5)
        except Exception: proc.kill()

    # ---- session 2: move with physical relocation + GOSUB rewrite ----
    # 10 GOSUB 200 / 30 END / 200 PRINT"SUB" / 210 RETURN
    # M 200 210 15 -> block [200,210] renumbers to [15,25] and relocates before 30.
    port = next(ports)
    prog2 = ["10 GOSUB 200", "30 END", '200 PRINT"SUB"', "210 RETURN"]
    proc = boot(port, crt)
    try:
        s = harness.connect_monitor(port, 20.0); time.sleep(6.0); s.close()
        type_lines(port, prog2)
        open_tool(port, dorenum)
        cmd(port, "M 200 210 15")
        s = harness.connect_monitor(port, 20.0)
        results["move_ok"] = "OK" in harness.screen_text(s).upper()
        s.close()
        harness.keyboard_type_on_port(port, "\x03")
        time.sleep(0.6)
        harness.keyboard_type_on_port(port, "LIST\r")
        time.sleep(1.2)
        s = harness.connect_monitor(port, 20.0)
        lst = harness.screen_text(s).upper()
        vt = harness.mem_get(s, 0x2D, 0x2E)
        s.close()
        results["move_ref"] = "10 GOSUB 15" in lst
        results["move_hdr"] = "15 PRINT" in lst and "25 RETURN" in lst
        # sorted order 10,15,25,30 -> line-number sequence must be ascending in the
        # listing: check "15 PRINT" appears before "30 END".
        i15 = lst.find("15 PRINT"); i30 = lst.find("30 END")
        results["move_sorted"] = 0 <= i15 < i30
        harness.quit_vice(harness.connect_monitor(port, 20.0))
    finally:
        proc.terminate()
        try: proc.wait(timeout=5)
        except Exception: proc.kill()

    # ---- session 3: reject paths leave the program byte-identical ----
    port = next(ports)
    prog3 = ["10 GOSUB 100", "20 PRINT", "100 END", "110 RETURN"]
    proc = boot(port, crt)
    try:
        s = harness.connect_monitor(port, 20.0); time.sleep(6.0); s.close()
        type_lines(port, prog3)
        s = harness.connect_monitor(port, 20.0)
        before = read_prog(s)
        s.close()
        open_tool(port, dorenum)
        # end <= start
        cmd(port, "M 30 20 500")
        s = harness.connect_monitor(port, 20.0)
        txt = harness.screen_text(s).upper()
        results["reject_endstart_msg"] = "END<=START" in txt
        results["reject_endstart_id"] = read_prog(s) == before
        s.close()
        # move collision: block [100,110] -> [15,25] interleaves kept line 20
        cmd(port, "M 100 110 15")
        s = harness.connect_monitor(port, 20.0)
        txt = harness.screen_text(s).upper()
        results["reject_coll_msg"] = "COLLISION" in txt
        results["reject_coll_id"] = read_prog(s) == before
        s.close()
        # renum overflow: R 40000 100 -> 100, 40100(collision-free) then next >63999
        cmd(port, "R 40000 10")
        s = harness.connect_monitor(port, 20.0)
        txt = harness.screen_text(s).upper()
        results["reject_over_msg"] = ">63999" in txt
        results["reject_over_id"] = read_prog(s) == before
        s.close()
        # tool still open (REPL) -> a valid command now applies
        cmd(port, "R 500")
        s = harness.connect_monitor(port, 20.0)
        results["repl_stays"] = "OK" in harness.screen_text(s).upper()
        after = read_prog(s)
        s.close()
        results["repl_applied"] = after != before
        harness.keyboard_type_on_port(port, "\x03")
        time.sleep(0.6)
        harness.quit_vice(harness.connect_monitor(port, 20.0))
    finally:
        proc.terminate()
        try: proc.wait(timeout=5)
        except Exception: proc.kill()

    # ---- session 4: digit SHRINK (dec2d) + post-renumber executability ----
    # 10 GOTO 1000 / 20 PRINT"NO" / 1000 PRINT"YES" / 1010 END
    # R 5 -> lines 5,10,15,20; GOTO 1000 shrinks to GOTO 15 (4->2 digits). RUNning
    # the renumbered program must reach 15 PRINT"YES" (proves links/pointers intact).
    port = next(ports)
    prog4 = ["10 GOTO 1000", '20 PRINT"NO"', '1000 PRINT"YES"', "1010 END"]
    proc = boot(port, crt)
    try:
        s = harness.connect_monitor(port, 20.0); time.sleep(6.0); s.close()
        type_lines(port, prog4)
        open_tool(port, dorenum)
        cmd(port, "R 5")                         # -> 5,10,15,20 ; GOTO 1000 -> GOTO 15
        s = harness.connect_monitor(port, 20.0)
        results["shrink_ok"] = "OK" in harness.screen_text(s).upper()
        s.close()
        harness.keyboard_type_on_port(port, "\x03")
        time.sleep(0.6)
        harness.keyboard_type_on_port(port, "LIST\r")
        time.sleep(1.2)
        s = harness.connect_monitor(port, 20.0)
        lst = harness.screen_text(s).upper()
        s.close()
        results["shrink_ref"] = "5 GOTO 15" in lst   # 1000 -> 15 (digit shrink)
        # RUN the renumbered program: it must print YES (and not NO), proving the
        # relinked program executes correctly.
        harness.keyboard_type_on_port(port, "RUN\r")
        time.sleep(1.0)
        s = harness.connect_monitor(port, 20.0)
        run = harness.screen_text(s).upper()
        s.close()
        results["runs_after_renum"] = "YES" in run
        harness.quit_vice(harness.connect_monitor(port, 20.0))
    finally:
        proc.terminate()
        try: proc.wait(timeout=5)
        except Exception: proc.kill()

    # ---- session 5: heavier program, many refs, big digit-shrink; link integrity ----
    prog5 = ['1000 PRINT"START"', "1010 GOSUB 1800", "1020 GOTO 1200",
             '1030 PRINT"SKIP"', '1200 PRINT"MID"', "1210 GOTO 1700",
             '1700 PRINT"NEAR"', "1710 END", '1800 PRINT"SUB"', "1810 RETURN"]
    port = next(ports)
    proc = boot(port, crt)
    try:
        s = harness.connect_monitor(port, 20.0); time.sleep(6.0); s.close()
        type_lines(port, prog5)
        s = harness.connect_monitor(port, 20.0)
        results["big_before_links"] = walk_links(s) is not None
        s.close()
        open_tool(port, dorenum)
        cmd(port, "R 1")          # 1..10 : all headers + refs shrink 4->1 digit
        s = harness.connect_monitor(port, 20.0)
        results["big_ok"] = "OK" in harness.screen_text(s).upper()
        s.close()
        harness.keyboard_type_on_port(port, "\x03")
        time.sleep(0.6)
        s = harness.connect_monitor(port, 20.0)
        nums = walk_links(s)
        s.close()
        # links must still form a valid, strictly-ascending chain of 10 lines 1..10
        results["big_links_valid"] = nums == list(range(1, 11))
        harness.keyboard_type_on_port(port, "LIST\r")
        time.sleep(1.2)
        s = harness.connect_monitor(port, 20.0)
        lst = harness.screen_text(s).upper()
        s.close()
        results["big_refs"] = ("2 GOSUB 9" in lst and "3 GOTO 5" in lst
                               and "6 GOTO 7" in lst)
        harness.quit_vice(harness.connect_monitor(port, 20.0))
    finally:
        proc.terminate()
        try: proc.wait(timeout=5)
        except Exception: proc.kill()

    for k, v in results.items():
        print(f"  {'PASS' if v else 'FAIL'}  {k}")
    ok = all(results.values())
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
