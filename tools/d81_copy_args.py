#!/usr/bin/env python3
"""Turn a `c1541 <disk> -list` directory dump (on stdin) into NUL-separated
c1541 copy arguments that mirror every file from unit 9 onto the current unit.

Used by build_disk.sh to populate a fresh D81 from the template D64; emitting
NUL separators lets filenames with spaces survive `xargs -0`. The disk header
line and the freshly built mdbasic.prg are skipped (the PRG is written
separately from the fresh build).
"""
import sys

FILE_TYPES = ("prg", "seq", "usr", "rel", "del")

for line in sys.stdin:
    if '"' not in line:
        continue
    head, name, tail = line.split('"', 2)
    name = name.rstrip()
    # Real directory entries carry a file type after the name; the disk header
    # line ("0 \"diskname\" id") does not.
    if not any(t in tail.lower() for t in FILE_TYPES):
        continue
    if not name or name == "mdbasic.prg":
        continue
    for token in ("-copy", "@9:" + name, name):
        sys.stdout.write(token + "\0")
