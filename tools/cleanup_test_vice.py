#!/usr/bin/env python3
"""Kill leftover VICE test instances launched against /tmp/mddocs.crt."""

from __future__ import annotations

import os
import signal
import subprocess
import time

MATCH = "-cartcrt /tmp/mddocs.crt"


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def vice_pids() -> list[int]:
    proc = subprocess.run(
        ["ps", "-Ao", "pid=,command="],
        text=True,
        capture_output=True,
        check=True,
    )
    pids = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line or MATCH not in line or "x64sc" not in line:
            continue
        pid_text, _sep, _cmd = line.partition(" ")
        try:
            pids.append(int(pid_text))
        except ValueError:
            continue
    return pids


def terminate(pid: int) -> None:
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        return
    deadline = time.time() + 3.0
    while time.time() < deadline:
        if not alive(pid):
            return
        time.sleep(0.1)
    try:
        os.kill(pid, signal.SIGKILL)
    except OSError:
        return


def main() -> int:
    for pid in vice_pids():
        terminate(pid)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
