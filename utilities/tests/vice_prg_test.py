#!/usr/bin/env python3
"""Create a D64, autostart it in VICE, and assert final screen text."""
from __future__ import annotations

import argparse
import os
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
from pathlib import Path


VICE_BIN = Path.home() / "Developer" / "vice-arm64-gtk3-3.9" / "bin"


def find_tool(name: str) -> str:
    found = shutil.which(name)
    if found:
        return found
    candidate = VICE_BIN / name
    if candidate.exists():
        return str(candidate)
    raise SystemExit(f"ERROR: {name} not found on PATH or at {candidate}")


def run_checked(cmd: list[str], *, quiet: bool = False) -> None:
    proc = subprocess.run(cmd, text=True, capture_output=True)
    if proc.returncode != 0:
        if proc.stdout:
            print(proc.stdout, file=sys.stderr)
        if proc.stderr:
            print(proc.stderr, file=sys.stderr)
        raise SystemExit(proc.returncode)
    if not quiet and proc.stdout:
        print(proc.stdout, end="")


def monitor_cmd(sock: socket.socket, ctype: int, body: bytes = b"") -> None:
    sock.sendall(struct.pack("<BBII", 0x02, 0x02, len(body), 0x4242) + bytes([ctype]) + body)


def recv_exact(sock: socket.socket, n: int) -> bytes:
    data = b""
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            raise EOFError("monitor closed")
        data += chunk
    return data


def monitor_response(sock: socket.socket) -> tuple[int, int, bytes]:
    header = recv_exact(sock, 12)
    _, _, body_len, rtype, err = struct.unpack("<BBIBB", header[:8])
    body = recv_exact(sock, body_len) if body_len else b""
    return rtype, err, body


def mem_get(sock: socket.socket, start: int, end: int) -> bytes:
    body = struct.pack("<BHHBH", 0, start, end, 0, 0)
    monitor_cmd(sock, 0x01, body)
    while True:
        rtype, err, data = monitor_response(sock)
        if rtype == 0x01:
            if err:
                raise RuntimeError(f"VICE mem_get error {err}")
            count = struct.unpack("<H", data[:2])[0]
            return data[2 : 2 + count]


def mem_set(sock: socket.socket, start: int, data: bytes) -> None:
    end = start + len(data) - 1
    body = struct.pack("<BHHBH", 1, start, end, 0, 0) + data
    monitor_cmd(sock, 0x02, body)
    while True:
        rtype, err, _ = monitor_response(sock)
        if rtype == 0x02:
            if err:
                raise RuntimeError(f"VICE mem_set error {err}")
            return


def monitor_feed(sock: socket.socket, text: str, timeout: float = 3.0) -> None:
    data = text.encode("latin1")
    if len(data) > 255:
        raise ValueError("VICE monitor feed command accepts at most 255 bytes")
    monitor_cmd(sock, 0x72, bytes([len(data)]) + data)
    old_timeout = sock.gettimeout()
    sock.settimeout(timeout)
    try:
        while True:
            rtype, err, _ = monitor_response(sock)
            if rtype == 0x72:
                if err:
                    raise RuntimeError(f"VICE feed error {err}")
                return
    finally:
        sock.settimeout(old_timeout)


def wait_keyboard_empty(sock: socket.socket, timeout: float = 20.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if mem_get(sock, 0x00C6, 0x00C6)[0] == 0:
            return
        time.sleep(0.05)
    raise TimeoutError("C64 keyboard buffer did not drain")


def keyboard_type(sock: socket.socket, text: str) -> None:
    data = text.encode("latin1").replace(b"\n", b"\r")
    offset = 0
    while offset < len(data):
        chunk = data[offset : offset + 10]
        wait_keyboard_empty(sock)
        mem_set(sock, 0x0277, chunk)
        mem_set(sock, 0x00C6, bytes([len(chunk)]))
        offset += len(chunk)
        time.sleep(0.15)


def keyboard_type_on_port(port: int, text: str) -> None:
    data = text.encode("latin1").replace(b"\n", b"\r")
    offset = 0
    while offset < len(data):
        chunk = data[offset : offset + 10]
        sock = connect_monitor(port, 5.0)
        try:
            wait_keyboard_empty(sock)
            mem_set(sock, 0x0277, chunk)
            mem_set(sock, 0x00C6, bytes([len(chunk)]))
        finally:
            sock.close()
        offset += len(chunk)
        time.sleep(0.75)


def connect_monitor(port: int, timeout: float) -> socket.socket:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            return socket.create_connection(("127.0.0.1", port), timeout=2.0)
        except OSError:
            time.sleep(0.25)
    raise SystemExit(f"ERROR: could not connect to VICE binary monitor on port {port}")


def screen_char(code: int) -> str:
    code &= 0x7F
    if code == 0x20:
        return " "
    if 1 <= code <= 26:
        return chr(ord("A") + code - 1)
    if 0x41 <= code <= 0x5A:
        return chr(code)
    if 0x30 <= code <= 0x39:
        return chr(code)
    punctuation = {
        0x21: "!",
        0x22: '"',
        0x23: "#",
        0x24: "$",
        0x25: "%",
        0x26: "&",
        0x27: "'",
        0x28: "(",
        0x29: ")",
        0x2A: "*",
        0x2B: "+",
        0x2C: ",",
        0x2D: "-",
        0x2E: ".",
        0x2F: "/",
        0x3A: ":",
        0x3B: ";",
        0x3C: "<",
        0x3D: "=",
        0x3E: ">",
        0x3F: "?",
    }
    return punctuation.get(code, ".")


def screen_text(sock: socket.socket) -> str:
    data = mem_get(sock, 0x0400, 0x07E7)
    lines = []
    for row in range(25):
        line = "".join(screen_char(data[row * 40 + col]) for col in range(40)).rstrip()
        lines.append(line)
    return "\n".join(lines)


def wait_for_screen(sock: socket.socket, expects: list[str], timeout: float) -> tuple[bool, str]:
    deadline = time.time() + timeout
    last = ""
    expects_upper = [item.upper() for item in expects]
    while time.time() < deadline:
        last = screen_text(sock)
        upper = last.upper()
        if all(item in upper for item in expects_upper):
            return True, last
        time.sleep(0.5)
    return False, last


def close_socket(sock: socket.socket | None) -> None:
    if sock is None:
        return
    try:
        sock.close()
    except OSError:
        pass


def quit_vice(sock: socket.socket) -> None:
    try:
        monitor_cmd(sock, 0xBB)
        time.sleep(0.3)
    except OSError:
        pass
    finally:
        close_socket(sock)


def shutdown_vice(proc: subprocess.Popen, sock: socket.socket | None = None,
                  *, timeout: float = 5.0) -> None:
    should_close = sock is not None
    if sock is not None:
        try:
            quit_vice(sock)
            should_close = False
        except Exception:
            pass
        finally:
            if should_close:
                close_socket(sock)
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=timeout)


def shutdown_vice_on_port(proc: subprocess.Popen, port: int, *,
                          connect_timeout: float = 1.0,
                          timeout: float = 5.0) -> None:
    sock = None
    if proc.poll() is None:
        try:
            sock = connect_monitor(port, connect_timeout)
        except SystemExit:
            sock = None
    shutdown_vice(proc, sock, timeout=timeout)


def parse_file_arg(value: str) -> tuple[str, Path]:
    if "=" not in value:
        path = Path(value)
        return path.stem.lower(), path
    name, path = value.split("=", 1)
    return name, Path(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", action="append", default=[], help="cbmname=host.prg")
    parser.add_argument("--disk", type=Path)
    parser.add_argument("--run", help="CBM filename to autostart; defaults to first --file")
    parser.add_argument("--expect", action="append", default=[])
    parser.add_argument("--port", type=int, default=6529)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--boot-wait", type=float, default=5.0)
    parser.add_argument("--load-wait", type=float, default=8.0)
    parser.add_argument("--keep-disk", action="store_true")
    parser.add_argument("--leave-running", action="store_true")
    args = parser.parse_args()

    if not args.file:
        raise SystemExit("ERROR: pass at least one --file cbmname=host.prg")

    c1541 = find_tool("c1541")
    x64sc = find_tool("x64sc")
    entries = [parse_file_arg(item) for item in args.file]
    run_name = args.run or entries[0][0]
    run_path = None
    for name, path in entries:
        if name.lower() == run_name.lower():
            run_path = path
            break
    if run_path is None:
        raise SystemExit(f"ERROR: --run {run_name!r} is not one of the --file names")

    tempdir = tempfile.TemporaryDirectory(prefix="mdbasic-vice-")
    disk = args.disk or Path(tempdir.name) / "test.d64"
    if disk.exists():
        disk.unlink()

    cmd = [c1541, "-format", "test,tt", "d64", str(disk)]
    for name, path in entries:
        if not path.exists():
            raise SystemExit(f"ERROR: missing PRG {path}")
        cmd.extend(["-write", str(path), name.lower()])
    run_checked(cmd, quiet=True)

    env = dict(os.environ)
    log_path = Path(tempdir.name) / "vice.log"
    log = log_path.open("w", encoding="utf-8", errors="replace")
    vice_cmd = [
        x64sc,
        "+confirmonexit",
        "-default",
        "+saveres",
        "+sound",
        "-sounddev",
        "dummy",
        "-warp",
        "-virtualdev8",
        "+drive8truedrive",
        "-binarymonitor",
        "-binarymonitoraddress",
        f"ip4://127.0.0.1:{args.port}",
        "-8",
        str(disk),
    ]
    proc = subprocess.Popen(vice_cmd, stdout=log, stderr=subprocess.STDOUT, text=True, env=env)
    sock: socket.socket | None = None
    failed = False
    try:
        sock = connect_monitor(args.port, 20.0)
        time.sleep(args.boot_wait)
        ready, _ = wait_for_screen(sock, ["READY."], 15.0)
        if not ready:
            raise SystemExit("ERROR: C64 BASIC prompt did not appear before startup command injection")
        sock.close()
        sock = None
        time.sleep(0.5)
        keyboard_type_on_port(args.port, f'LOAD"{run_name.upper()}",8\r')
        time.sleep(args.load_wait)
        keyboard_type_on_port(args.port, "RUN\r")
        sock = connect_monitor(args.port, 20.0)
        ok, screen = wait_for_screen(sock, args.expect, args.timeout) if args.expect else (True, screen_text(sock))
        print("---- screen ----")
        print(screen)
        if not ok:
            failed = True
            raise SystemExit("ERROR: expected text not found: " + ", ".join(args.expect))
    finally:
        if sock and not args.leave_running:
            quit_vice(sock)
        if not args.leave_running:
            shutdown_vice(proc, timeout=3.0)
        log.close()
        if failed and log_path.exists():
            lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
            print("---- vice log tail ----")
            print("\n".join(lines[-80:]))
        if args.keep_disk and not args.disk:
            print(f"disk kept at {disk}")
        elif not args.keep_disk:
            tempdir.cleanup()


if __name__ == "__main__":
    main()
