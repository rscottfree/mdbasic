#!/usr/bin/env python3
"""Install an MDBASIC image in VICE, then LOAD+RUN the sprite MOVE timing test.

Unlike vice_prg_test.py (which autostarts one BASIC PRG), MDBASIC must be
installed first: LOAD"MDBASIC",8,1 then SYS64738 (the in-RAM "CBM80" signature
makes the reset autostart it). Then we LOAD the timing program and RUN it,
and dump the final screen showing the jiffy timings for each speed.

Usage:
  tools/move_timing_test.py --mdbasic build/mdbasic.prg \
      --prg ss=tests/ss_new.prg --prg bird.spr=/tmp/bird.spr.prg --run ss
"""
from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vice_prg_test import (  # noqa: E402
    connect_monitor,
    find_tool,
    keyboard_type_on_port,
    quit_vice,
    run_checked,
    screen_text,
    wait_for_screen,
)


def parse_named(value: str) -> tuple[str, Path]:
    name, path = value.split("=", 1)
    return name, Path(path)


def poll_screen_reconnect(port: int, expects, timeout: float):
    """Poll screen RAM by opening a fresh monitor connection for each read.

    VICE's binary monitor pauses emulation while a socket is held open, so a
    persistent connection starves the running BASIC program. Reconnecting per
    read (and sleeping with the socket closed) lets the program run freely.
    """
    deadline = time.time() + timeout
    wanted = [e.upper() for e in expects]
    last = ""
    while time.time() < deadline:
        s = connect_monitor(port, 10.0)
        try:
            last = screen_text(s)
        finally:
            s.close()
        if all(w in last.upper() for w in wanted):
            return True, last
        time.sleep(1.0)
    return False, last


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mdbasic", required=True, type=Path, help="mdbasic PRG ($8000)")
    ap.add_argument("--prg", action="append", default=[], help="cbmname=host.prg")
    ap.add_argument("--run", required=True, help="CBM filename to LOAD+RUN")
    ap.add_argument("--expect", action="append", default=["DONE"])
    ap.add_argument("--port", type=int, default=6529)
    ap.add_argument("--timeout", type=float, default=180.0)
    ap.add_argument("--keep-disk", action="store_true")
    ap.add_argument("--no-warp", action="store_true",
                    help="run VICE at real speed (timings are jiffy-based so warp "
                         "does not change them; use this to prove it)")
    args = ap.parse_args()

    c1541 = find_tool("c1541")
    x64sc = find_tool("x64sc")

    entries = [parse_named(p) for p in args.prg]
    tempdir = tempfile.TemporaryDirectory(prefix="mdbasic-move-")
    disk = Path(tempdir.name) / "test.d64"

    cmd = [c1541, "-format", "test,tt", "d64", str(disk),
           "-write", str(args.mdbasic), "mdbasic"]
    for name, path in entries:
        if not path.exists():
            raise SystemExit(f"ERROR: missing PRG {path}")
        cmd += ["-write", str(path), name.lower()]
    run_checked(cmd, quiet=True)

    log_path = Path(tempdir.name) / "vice.log"
    log = log_path.open("w", encoding="utf-8", errors="replace")
    vice_cmd = [
        x64sc, "+confirmonexit", "-default", "+saveres", "+sound",
        "-sounddev", "dummy", "+warp" if args.no_warp else "-warp",
        "-virtualdev8", "+drive8truedrive",
        "-binarymonitor", "-binarymonitoraddress",
        f"ip4://127.0.0.1:{args.port}", "-8", str(disk),
    ]
    proc = subprocess.Popen(vice_cmd, stdout=log, stderr=subprocess.STDOUT,
                            text=True, env=dict(os.environ))
    failed = False
    try:
        time.sleep(5.0)
        ok, _ = poll_screen_reconnect(args.port, ["READY."], 15.0)
        if not ok:
            raise SystemExit("ERROR: no BASIC prompt before install")

        # Install MDBASIC: load to $8000 then reset-autostart via CBM80
        # (SYS64738 soft-resets, then the in-RAM CBM80 signature autostarts it).
        keyboard_type_on_port(args.port, 'LOAD"MDBASIC",8,1\r')
        ok, _ = poll_screen_reconnect(args.port, ["READY."], 30.0)
        keyboard_type_on_port(args.port, "SYS64738\r")
        ok, _ = poll_screen_reconnect(args.port, ["MDBASIC"], 30.0)
        if not ok:
            raise SystemExit("ERROR: MDBASIC banner did not appear after install")

        # Load and run the timing program.
        keyboard_type_on_port(args.port, f'LOAD"{args.run.upper()}",8\r')
        poll_screen_reconnect(args.port, ["READY."], 30.0)
        keyboard_type_on_port(args.port, "RUN\r")
        ok, screen = poll_screen_reconnect(args.port, args.expect, args.timeout)
        print("---- screen ----")
        print(screen)
        if not ok:
            failed = True
            raise SystemExit("ERROR: expected text not found: " + ", ".join(args.expect))
    finally:
        try:
            s = connect_monitor(args.port, 5.0); quit_vice(s); s.close()
        except OSError:
            pass
        try:
            proc.wait(timeout=3.0)
        except subprocess.TimeoutExpired:
            proc.kill(); proc.wait(timeout=3.0)
        log.close()
        if failed and log_path.exists():
            print("---- vice log tail ----")
            print("\n".join(log_path.read_text(errors="replace").splitlines()[-40:]))
        if args.keep_disk:
            keepdir = Path(__file__).resolve().parent.parent / "build"
            keepdir.mkdir(parents=True, exist_ok=True)
            kept = keepdir / "move_timing_test.d64"
            kept.write_bytes(disk.read_bytes())
            print(f"disk kept at {kept}")
        tempdir.cleanup()


if __name__ == "__main__":
    main()
