#!/usr/bin/env python3
"""End-to-end test of the MDBASIC CTRL+RESTORE renumber/move/copy/convert tools in VICE.

Builds the full docs+menu+tool cart (reusing vice_docs_test.build_cart), boots
it, types a known BASIC program, then SYSes a synthetic-NMI stub that jumps to the
menu's direct tool entries (past the CTRL/STOP gate), so each tool's REPL opens.
Commands are driven through the kernal key
buffer; the resulting program is checked by LISTing it and by comparing the raw
program bytes ($0801..VARTAB) for the reject cases (a rejected R/M must leave the
program byte-identical).

Covered: menu choices, default/ranged R with reference rewrite (incl. digit-count growth), R's
explicit <dest> anchoring the new numbering away from <start>, a valid M that
physically relocates the block + rewrites its GOSUB (with <start> below the first
actual source line, so the block anchors on <dest> rather than on minsrc-mstart+
dest), the REPL staying open after a command, the reject paths (overflow, order/
collision, END<START) each leaving the program untouched, and that the tool
snapshots the screen on entry and restores it (text + cursor position) on RUN/STOP
exit rather than leaving the screen blank.

This is the entry point for the whole renum/move suite: it defines its own tests
below and unions in the registries from vice_renum_single_line_move_test.py and
vice_renum_move_overlap_test.py, so one invocation covers everything.

    tools/vice_renum_test.py                  # run every test, from all 3 files
    tools/vice_renum_test.py move_basic shrink # run just these
    tools/vice_renum_test.py --list            # print available test names

Each of the three files also stays runnable standalone against its own tests
only (e.g. `tools/vice_renum_move_overlap_test.py` runs just `move_overlap`).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import vice_prg_test as harness
import vice_docs_test as dt
import renum_test_lib as lib


def cursor_cells(sock):
    screen = harness.mem_get(sock, 0x0400, 0x07FF)
    return [i for i, b in enumerate(screen) if b == 0xA0]


def has_blank_gap_before_prompt(screen: str, marker: str) -> bool:
    lines = screen.upper().splitlines()
    for i, line in enumerate(lines[:-2]):
        if marker in line:
            return lines[i + 1] == "" and lines[i + 2].startswith(">")
    return False


def session_menu_choice(crt, dorenum, domenu, next_port):
    """the menu-body itself (F1 -> pager, R/M/C/F7 -> tools). SYS to `domenu`
    (past the CTRL/STOP gate); the menu-body draws its prompt and waits for a
    key. Poked keys in the kernal buffer drive each choice."""
    results = {}
    for key, want, tag in (("\x85", "SEARCH", "menu_f1_pager"),
                            ("r", "RENUMBER", "menu_r_renum"),
                            ("m", "MOVE", "menu_m_move"),
                            ("c", "COPY", "menu_c_copy"),
                            ("\x88", "CONVERT", "menu_f7_convert")):
        port = next_port()
        proc = lib.boot(port, crt)
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
            lib.finish_on_port(proc, port)
    return results


def session_menu_screen(crt, dorenum, domenu, next_port):
    """the menu itself backs up the screen, clears it, and shows the prompt;
    dismissing (STOP) restores the pre-menu screen."""
    results = {}
    port = next_port()
    proc = lib.boot(port, crt)
    try:
        s = harness.connect_monitor(port, 20.0); time.sleep(6.0); s.close()
        lib.type_lines(port, ['10 PRINT"MARKERTEXT"'])
        s = harness.connect_monitor(port, 20.0)
        before = harness.screen_text(s).upper()
        s.close()
        results["menu_marker_before"] = "MARKERTEXT" in before
        s = harness.connect_monitor(port, 20.0)
        harness.mem_set(s, dt.STUB_ADDR, dt.nmi_frame_stub(domenu)); s.close()
        harness.keyboard_type_on_port(port, f"SYS{dt.STUB_ADDR}\r")
        time.sleep(0.8)
        s = harness.connect_monitor(port, 20.0)
        during = harness.screen_text(s).upper()
        s.close()
        results["menu_clears_marker"] = ("MARKERTEXT" not in during
                                         and "F1=DOCS" in during)
        harness.keyboard_type_on_port(port, "\x03")   # STOP -> dismiss
        time.sleep(0.8)
        s = harness.connect_monitor(port, 20.0)
        after = harness.screen_text(s).upper()
        s.close()
        results["menu_restores_marker"] = "MARKERTEXT" in after
        results["menu_prompt_gone"] = "F1=DOCS" not in after
        harness.quit_vice(harness.connect_monitor(port, 20.0))
    finally:
        lib.finish_on_port(proc, port)
    return results


def session_renum_basic(crt, dorenum, domenu, next_port):
    """renum success + reference rewrite (digit growth) + REPL staying open."""
    results = {}
    port = next_port()
    prog1 = ['10 PRINT"HI"', "20 GOTO 40", '30 PRINT"X"', "40 GOSUB 30", "50 END"]
    proc = lib.boot(port, crt)
    try:
        s = harness.connect_monitor(port, 20.0)
        time.sleep(6.0)
        s.close()
        lib.type_lines(port, prog1)
        lib.open_tool(port, dorenum)
        s = harness.connect_monitor(port, 20.0)
        results["tool_opens"] = "RENUM" in harness.screen_text(s).upper()
        s.close()
        lib.cmd(port, "100")                     # increment 100 -> 100,200,300,400,500
        s = harness.connect_monitor(port, 20.0)
        txt = harness.screen_text(s)
        results["repl_ok"] = "OK" in txt.upper()
        results["repl_blank_gap"] = has_blank_gap_before_prompt(txt, "OK")
        s.close()
        harness.keyboard_type_on_port(port, "\x03")   # RUN/STOP -> leave tool
        time.sleep(0.6)
        harness.keyboard_type_on_port(port, "\x93LIST\r")
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
        lib.finish_on_port(proc, port)
    return results


def session_move_basic(crt, dorenum, domenu, next_port):
    """move with physical relocation + GOSUB rewrite.
    10 GOSUB 200 / 30 END / 200 PRINT"SUB" / 210 RETURN
    M 150 210 15 -> <start> (150) is below the first actual line in the block
    (200); the block must still anchor so the FIRST source line (200) lands
    exactly on <dest> (15), not on minsrc-mstart+dest (65) -- regression check
    for the move-anchor bug. Block [200,210] -> [15,25], relocated before 30."""
    results = {}
    port = next_port()
    prog2 = ["10 GOSUB 200", "30 END", '200 PRINT"SUB"', "210 RETURN"]
    proc = lib.boot(port, crt)
    try:
        s = harness.connect_monitor(port, 20.0); time.sleep(6.0); s.close()
        lib.type_lines(port, prog2)
        lib.open_tool(port, lib.DOMOVE)
        lib.cmd(port, "150 210 15")
        s = harness.connect_monitor(port, 20.0)
        txt = harness.screen_text(s)
        results["move_ok"] = "OK" in txt.upper()
        results["move_blank_gap"] = has_blank_gap_before_prompt(txt, "OK")
        s.close()
        harness.keyboard_type_on_port(port, "\x03")
        time.sleep(0.6)
        # RUN/STOP now restores the pre-tool screen (leftover typed-program text)
        # instead of leaving it blank, so clear before LIST to get a screen whose
        # text order reflects only the fresh listing.
        harness.keyboard_type_on_port(port, "\x93LIST\r")
        time.sleep(1.2)
        s = harness.connect_monitor(port, 20.0)
        lst = harness.screen_text(s).upper()
        s.close()
        results["move_ref"] = "10 GOSUB 15" in lst
        results["move_hdr"] = "15 PRINT" in lst and "25 RETURN" in lst
        # sorted order 10,15,25,30 -> line-number sequence must be ascending in the
        # listing: check "15 PRINT" appears before "30 END".
        i15 = lst.find("15 PRINT"); i30 = lst.find("30 END")
        results["move_sorted"] = 0 <= i15 < i30
        harness.quit_vice(harness.connect_monitor(port, 20.0))
    finally:
        lib.finish_on_port(proc, port)
    return results


def session_reject(crt, dorenum, domenu, next_port):
    """reject paths leave the program byte-identical."""
    results = {}
    port = next_port()
    prog3 = ["10 GOSUB 100", "20 PRINT", "100 END", "110 RETURN"]
    proc = lib.boot(port, crt)
    try:
        s = harness.connect_monitor(port, 20.0); time.sleep(6.0); s.close()
        lib.type_lines(port, prog3)
        s = harness.connect_monitor(port, 20.0)
        before = lib.read_prog(s)
        s.close()
        lib.open_tool(port, lib.DOMOVE)
        # end <= start
        lib.cmd(port, "30 20 500")
        s = harness.connect_monitor(port, 20.0)
        txt = harness.screen_text(s).upper()
        results["reject_endstart_msg"] = "END<START" in txt
        results["reject_endstart_id"] = lib.read_prog(s) == before
        s.close()
        # move collision: block [100,110] -> [15,25] interleaves kept line 20
        lib.cmd(port, "100 110 15")
        s = harness.connect_monitor(port, 20.0)
        txt = harness.screen_text(s).upper()
        results["reject_coll_msg"] = "COLLISION" in txt
        results["reject_coll_id"] = lib.read_prog(s) == before
        s.close()
        harness.keyboard_type_on_port(port, "\x03")
        time.sleep(0.6)
        lib.open_tool(port, dorenum)
        # renum overflow: 40000 10 -> 10, 40010(collision-free) then next >63999
        lib.cmd(port, "40000 10")
        s = harness.connect_monitor(port, 20.0)
        txt = harness.screen_text(s).upper()
        results["reject_over_msg"] = ">63999" in txt
        results["reject_over_id"] = lib.read_prog(s) == before
        s.close()
        # tool still open (REPL) -> a valid command now applies
        lib.cmd(port, "500")
        s = harness.connect_monitor(port, 20.0)
        results["repl_stays"] = "OK" in harness.screen_text(s).upper()
        after = lib.read_prog(s)
        s.close()
        results["repl_applied"] = after != before
        harness.keyboard_type_on_port(port, "\x03")
        time.sleep(0.6)
        harness.quit_vice(harness.connect_monitor(port, 20.0))
    finally:
        lib.finish_on_port(proc, port)
    return results


def session_shrink(crt, dorenum, domenu, next_port):
    """digit SHRINK (dec2d) + post-renumber executability.
    10 GOTO 1000 / 20 PRINT"NO" / 1000 PRINT"YES" / 1010 END
    R 5 -> lines 5,10,15,20; GOTO 1000 shrinks to GOTO 15 (4->2 digits). RUNning
    the renumbered program must reach 15 PRINT"YES" (proves links/pointers intact)."""
    results = {}
    port = next_port()
    prog4 = ["10 GOTO 1000", '20 PRINT"NO"', '1000 PRINT"YES"', "1010 END"]
    proc = lib.boot(port, crt)
    try:
        s = harness.connect_monitor(port, 20.0); time.sleep(6.0); s.close()
        lib.type_lines(port, prog4)
        lib.open_tool(port, dorenum)
        lib.cmd(port, "5")                       # -> 5,10,15,20 ; GOTO 1000 -> GOTO 15
        s = harness.connect_monitor(port, 20.0)
        results["shrink_ok"] = "OK" in harness.screen_text(s).upper()
        s.close()
        harness.keyboard_type_on_port(port, "\x03")
        time.sleep(0.6)
        harness.keyboard_type_on_port(port, "\x93LIST\r")
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
        lib.finish_on_port(proc, port)
    return results


def session_big(crt, dorenum, domenu, next_port):
    """heavier program, many refs, big digit-shrink; link integrity."""
    results = {}
    prog5 = ['1000 PRINT"START"', "1010 GOSUB 1800", "1020 GOTO 1200",
             '1030 PRINT"SKIP"', '1200 PRINT"MID"', "1210 GOTO 1700",
             '1700 PRINT"NEAR"', "1710 END", '1800 PRINT"SUB"', "1810 RETURN"]
    port = next_port()
    proc = lib.boot(port, crt)
    try:
        s = harness.connect_monitor(port, 20.0); time.sleep(6.0); s.close()
        lib.type_lines(port, prog5)
        s = harness.connect_monitor(port, 20.0)
        results["big_before_links"] = lib.walk_links(s) is not None
        s.close()
        lib.open_tool(port, dorenum)
        lib.cmd(port, "1")            # 1..10 : all headers + refs shrink 4->1 digit
        s = harness.connect_monitor(port, 20.0)
        results["big_ok"] = "OK" in harness.screen_text(s).upper()
        s.close()
        harness.keyboard_type_on_port(port, "\x03")
        time.sleep(0.6)
        s = harness.connect_monitor(port, 20.0)
        nums = lib.walk_links(s)
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
        lib.finish_on_port(proc, port)
    return results


def session_screen_backup(crt, dorenum, domenu, next_port):
    """screen is backed up on entry and restored on exit. Open the tool (which
    draws its own header + REPL over the whole screen) and leave immediately
    with no command; the direct-mode text typed before entry must reappear,
    and the tool's own header must be gone (not just cleared)."""
    results = {}
    port = next_port()
    proc = lib.boot(port, crt)
    try:
        s = harness.connect_monitor(port, 20.0); time.sleep(6.0); s.close()
        lib.type_lines(port, ['10 PRINT"MARKERTEXT"'])
        s = harness.connect_monitor(port, 20.0)
        before = harness.screen_text(s).upper()
        s.close()
        results["screen_marker_before"] = "MARKERTEXT" in before
        lib.open_tool(port, dorenum)
        s = harness.connect_monitor(port, 20.0)
        during = harness.screen_text(s).upper()
        s.close()
        results["screen_tool_covers"] = ("MARKERTEXT" not in during
                                         and "RENUM" in during)
        harness.keyboard_type_on_port(port, "\x03")   # RUN/STOP, no command run
        time.sleep(0.8)
        s = harness.connect_monitor(port, 20.0)
        after = harness.screen_text(s).upper()
        s.close()
        results["screen_restored"] = "MARKERTEXT" in after
        results["screen_tool_gone"] = "RENUM" not in after
        harness.quit_vice(harness.connect_monitor(port, 20.0))
    finally:
        lib.finish_on_port(proc, port)
    return results


def session_cursor(crt, dorenum, domenu, next_port):
    """the tool draws a solid reverse-space cursor that tracks typing/deletion
    and clears from the submitted line before the next prompt appears."""
    results = {}
    port = next_port()
    proc = lib.boot(port, crt)
    try:
        s = harness.connect_monitor(port, 20.0); time.sleep(6.0); s.close()
        lib.open_tool(port, dorenum)

        s = harness.connect_monitor(port, 20.0)
        cur0 = cursor_cells(s)
        s.close()
        results["cursor_initial"] = len(cur0) == 1

        harness.keyboard_type_on_port(port, "12")
        time.sleep(0.4)
        s = harness.connect_monitor(port, 20.0)
        cur1 = cursor_cells(s)
        s.close()
        results["cursor_moves_forward"] = (len(cur0) == 1 and len(cur1) == 1
                                            and cur1[0] == cur0[0] + 2)

        harness.keyboard_type_on_port(port, "\x14")
        time.sleep(0.4)
        s = harness.connect_monitor(port, 20.0)
        cur2 = cursor_cells(s)
        s.close()
        results["cursor_moves_back"] = (len(cur0) == 1 and len(cur2) == 1
                                         and cur2[0] == cur0[0] + 1)

        harness.keyboard_type_on_port(port, "\r")
        time.sleep(0.8)
        s = harness.connect_monitor(port, 20.0)
        screen = harness.mem_get(s, 0x0400, 0x07FF)
        cur3 = cursor_cells(s)
        s.close()
        results["cursor_old_cell_cleared"] = (len(cur2) == 1 and screen[cur2[0]] == 0x20)
        results["cursor_next_prompt"] = (len(cur2) == 1 and len(cur3) == 1
                                          and cur3[0] > cur2[0])

        harness.keyboard_type_on_port(port, "\x03")
        time.sleep(0.6)
        harness.quit_vice(harness.connect_monitor(port, 20.0))
    finally:
        lib.finish_on_port(proc, port)
    return results


def session_dest_anchor(crt, dorenum, domenu, next_port):
    """R with explicit <dest> anchors the new numbering there.
    10 PRINT"A" / 20 PRINT"B" / 30 PRINT"C"
    R 5 10 30 1000 -> inc=5, source range [10,30], new numbering anchored at
    dest=1000 (not at start=10): 1000, 1005, 1010."""
    results = {}
    port = next_port()
    prog7 = ['10 PRINT"A"', '20 PRINT"B"', '30 PRINT"C"']
    proc = lib.boot(port, crt)
    try:
        s = harness.connect_monitor(port, 20.0); time.sleep(6.0); s.close()
        lib.type_lines(port, prog7)
        lib.open_tool(port, dorenum)
        lib.cmd(port, "5 10 30 1000")
        s = harness.connect_monitor(port, 20.0)
        results["dest_ok"] = "OK" in harness.screen_text(s).upper()
        s.close()
        harness.keyboard_type_on_port(port, "\x03")
        time.sleep(0.6)
        harness.keyboard_type_on_port(port, "\x93LIST\r")
        time.sleep(1.2)
        s = harness.connect_monitor(port, 20.0)
        lst = harness.screen_text(s).upper()
        s.close()
        results["dest_headers"] = ("1000 PRINT" in lst and "1005 PRINT" in lst
                                   and "1010 PRINT" in lst)
        harness.quit_vice(harness.connect_monitor(port, 20.0))
    finally:
        lib.finish_on_port(proc, port)
    return results


def session_copy_basic(crt, dorenum, domenu, next_port):
    """copy success + internal reference retarget + reject identity.
    10 GOSUB 100 / 20 END / 100 PRINT"SUB" / 110 GOTO 100 / 120 RETURN
    C 100 120 200 leaves the source in place and creates
    200 PRINT"SUB" / 210 GOTO 200 / 220 RETURN. The external 10 GOSUB 100 and
    original 110 GOTO 100 must stay pointed at the source block. A colliding copy
    is rejected before mutation."""
    results = {}
    port = next_port()
    prog = ["10 GOSUB 100", "20 END", '100 PRINT"SUB"', "110 GOTO 100", "120 RETURN"]
    proc = lib.boot(port, crt)
    try:
        s = harness.connect_monitor(port, 20.0); time.sleep(6.0); s.close()
        lib.type_lines(port, prog)
        s = harness.connect_monitor(port, 20.0)
        before = lib.read_prog(s)
        s.close()
        lib.open_tool(port, lib.DOCOPY)
        lib.cmd(port, "100 120 110")
        s = harness.connect_monitor(port, 20.0)
        txt = harness.screen_text(s).upper()
        results["copy_reject_coll_msg"] = "COLLISION" in txt
        results["copy_reject_coll_id"] = lib.read_prog(s) == before
        s.close()
        lib.cmd(port, "100 120 200")
        s = harness.connect_monitor(port, 20.0)
        txt = harness.screen_text(s)
        results["copy_ok"] = "OK" in txt.upper()
        results["copy_blank_gap"] = has_blank_gap_before_prompt(txt, "OK")
        nums = lib.walk_links(s)
        s.close()
        results["copy_links_valid"] = nums == [10, 20, 100, 110, 120, 200, 210, 220]
        harness.keyboard_type_on_port(port, "\x03")
        time.sleep(0.6)
        harness.keyboard_type_on_port(port, "\x93LIST\r")
        time.sleep(1.2)
        s = harness.connect_monitor(port, 20.0)
        lst = harness.screen_text(s).upper()
        s.close()
        results["copy_source_kept"] = "10 GOSUB 100" in lst and "110 GOTO 100" in lst
        results["copy_headers"] = "200 PRINT" in lst and "220 RETURN" in lst
        results["copy_internal_ref"] = "210 GOTO 200" in lst
        harness.quit_vice(harness.connect_monitor(port, 20.0))
    finally:
        lib.finish_on_port(proc, port)
    return results


def session_convert_basic(crt, dorenum, domenu, next_port):
    """convert accepts valid input, rejects bad input, and stays in the REPL.
    Decimal 255 should print %11111111 / @377 / $FF. Invalid %102 should print
    ?INVALID, and a follow-up hex conversion should still work."""
    results = {}
    port = next_port()
    proc = lib.boot(port, crt)
    try:
        s = harness.connect_monitor(port, 20.0); time.sleep(6.0); s.close()
        lib.open_tool(port, lib.DOCONVERT)
        s = harness.connect_monitor(port, 20.0)
        results["convert_opens"] = "CONVERT" in harness.screen_text(s).upper()
        s.close()
        lib.cmd(port, "255")
        s = harness.connect_monitor(port, 20.0)
        txt = harness.screen_text(s).upper()
        s.close()
        results["convert_dec_bin"] = "%11111111" in txt
        results["convert_dec_oct"] = ".377" in txt
        results["convert_dec_hex"] = "$FF" in txt
        lib.cmd(port, "%102")
        s = harness.connect_monitor(port, 20.0)
        txt = harness.screen_text(s).upper()
        s.close()
        results["convert_invalid"] = "?INVALID" in txt
        lib.cmd(port, "$2A")
        s = harness.connect_monitor(port, 20.0)
        txt = harness.screen_text(s).upper()
        s.close()
        results["convert_repl_stays"] = ("%101010" in txt and ".52" in txt and "42" in txt)
        harness.keyboard_type_on_port(port, "\x03")
        time.sleep(0.6)
        harness.quit_vice(harness.connect_monitor(port, 20.0))
    finally:
        lib.finish_on_port(proc, port)
    return results


TESTS = [
    ("menu_choice", session_menu_choice),
    ("menu_screen", session_menu_screen),
    ("renum_basic", session_renum_basic),
    ("move_basic", session_move_basic),
    ("reject", session_reject),
    ("shrink", session_shrink),
    ("big", session_big),
    ("screen_backup", session_screen_backup),
    ("cursor", session_cursor),
    ("dest_anchor", session_dest_anchor),
    ("copy_basic", session_copy_basic),
    ("convert_basic", session_convert_basic),
]

# Union in the sibling files' registries so this one entry point can run the
# whole renum/move suite, or any subset by name, in a single invocation.
import vice_renum_single_line_move_test as slm
import vice_renum_move_overlap_test as mov
TESTS = TESTS + slm.TESTS + mov.TESTS


def main() -> int:
    argv = sys.argv[1:]
    if argv == ["--list"]:
        print("\n".join(n for n, _ in TESTS))
        return 0
    return lib.run_cli(TESTS, argv)


if __name__ == "__main__":
    sys.exit(main())
