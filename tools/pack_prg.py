#!/usr/bin/env python3
"""Build (or verify) a packaged MDBASIC program: one self-contained PRG that
loads with LOAD"NAME",8,1 on a stock C64 and auto-runs, installing MDBASIC
from an embedded copy of the 16K image first.

This is the host-side twin of the C64-side PACKAGE tool (pack_tool.asm, on the
CTRL+RESTORE menu): both produce byte-identical files, so the VICE test suite
uses this module as the oracle for what the in-emulator tool must write.

Packaged file layout (load address $0302):

    $0302-$0303 : IMAIN vector -> the boot stub at $0334 (the autostart hook:
                  after a direct-mode LOAD, BASIC prints READY and jumps
                  through IMAIN)
    $0304-$0333 : the standard vector table values -- loading over live
                  vectors is safe exactly because every byte written equals
                  the byte already there (the IRQ vector included)
    $0334-$03ff : boot stub (pack_stub.asm), progend word patched
    $0400-$07ff : screen RAM fill -- blanks plus a banner row (the load is
                  visible on screen)
    $0800       : $00 (byte before BASIC text)
    $0801-      : the tokenized BASIC program, at its final address
    progend-    : the 16K MDBASIC image ($8000-$bfff body); the boot stub
                  copies it up to $8000 after load

Usage:
    tools/pack_prg.py --image mdbasic.prg --lst build/mdbasic.lst \
        --stub build/pack_stub.bin program.prg out.prg
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

FILE_LOAD = 0x0302           # packaged file load address
STUB_LOAD = 0x0334           # boot stub home (cassette buffer)
STUB_MAX = 0x0400 - STUB_LOAD          # 204 bytes
STUB_PROGEND_OFF = 3         # progend word, right after the stub's jmp
BASIC_LOAD = 0x0801
IMAGE_SIZE = 0x4000
IMAGE_LOAD = 0x8000
NEWVEC_SENTINEL = 0xCAF1     # jsr operands in pack_stub.asm the build patches
INITCLK_SENTINEL = 0xCAF2

# $0304-$0333 on a stock machine: BASIC indirects (ICRNCH..IEVAL), the USR
# jump, and the KERNAL RAM vector table. The packaged file streams these over
# the live vectors mid-load, so they MUST equal the standard values.
VECTOR_BLOCK = bytes([
    0x7C, 0xA5,              # $0304 ICRNCH  $a57c
    0x1A, 0xA7,              # $0306 IQPLOP  $a71a
    0xE4, 0xA7,              # $0308 IGONE   $a7e4
    0x86, 0xAE,              # $030a IEVAL   $ae86
    0x00, 0x00, 0x00, 0x00,  # $030c SAREG/SXREG/SYREG/SPREG
    0x4C, 0x48, 0xB2,        # $0310 USR jmp $b248 (ILLEGAL QUANTITY)
    0x00,                    # $0313
    0x31, 0xEA,              # $0314 CINV    $ea31 (live IRQ -- same value!)
    0x66, 0xFE,              # $0316 CBINV   $fe66
    0x47, 0xFE,              # $0318 NMINV   $fe47
    0x4A, 0xF3,              # $031a IOPEN   $f34a
    0x91, 0xF2,              # $031c ICLOSE  $f291
    0x0E, 0xF2,              # $031e ICHKIN  $f20e
    0x50, 0xF2,              # $0320 ICKOUT  $f250
    0x33, 0xF3,              # $0322 ICLRCH  $f333
    0x57, 0xF1,              # $0324 IBASIN  $f157
    0xCA, 0xF1,              # $0326 IBSOUT  $f1ca
    0xED, 0xF6,              # $0328 ISTOP   $f6ed (checked every load byte)
    0x3E, 0xF1,              # $032a IGETIN  $f13e
    0x2F, 0xF3,              # $032c ICLALL  $f32f
    0x66, 0xFE,              # $032e USRCMD  $fe66
    0xA5, 0xF4,              # $0330 ILOAD   $f4a5
    0xED, 0xF5,              # $0332 ISAVE   $f5ed
])

BANNER = "MDBASIC PACKAGED PROGRAM"
BANNER_ROW = 12


def lst_label_addr(lst_path: Path, label: str) -> int:
    """Resolve a label's address from a tmpx listing: the label sits on its
    own line, the address comes from the next line that carries one. Accepts
    both `NNN addr` and `NNN:MMM addr` line-number prefixes."""
    addr_re = re.compile(r"^\s*\d+(?::\d+)?\s+([0-9a-fA-F]{4})\b")
    lines = lst_path.read_text().splitlines()
    for i, line in enumerate(lines):
        if line.split()[1:2] == [label]:
            for nxt in lines[i + 1:]:
                m = addr_re.match(nxt)
                if m:
                    return int(m.group(1), 16)
    raise RuntimeError(f"label {label!r} not found in {lst_path}")


def _patch_jsr(stub: bytearray, sentinel: int, target: int) -> None:
    pat = bytes([0x20, sentinel & 0xFF, sentinel >> 8])
    hits = [i for i in range(len(stub) - 2) if bytes(stub[i:i + 3]) == pat]
    if len(hits) != 1:
        raise RuntimeError(f"expected one jsr ${sentinel:04x} in stub, "
                           f"found {len(hits)}")
    stub[hits[0] + 1] = target & 0xFF
    stub[hits[0] + 2] = target >> 8


def patch_stub_syms(blob: bytes, newvec: int, initclk: int) -> bytes:
    """Patch the newvec/initclk jsr sentinels with real addresses. `blob` is
    either the bare stub or a binary embedding it (pack_tool.bin)."""
    out = bytearray(blob)
    _patch_jsr(out, NEWVEC_SENTINEL, newvec)
    _patch_jsr(out, INITCLK_SENTINEL, initclk)
    return bytes(out)


def screen_fill() -> bytes:
    """The $0400-$07ff block: blank screen codes plus a centered banner row."""
    block = bytearray(b"\x20" * 0x400)
    codes = bytes((ord(c) - 0x40) if "A" <= c <= "Z" else ord(c)
                  for c in BANNER)
    col = (40 - len(codes)) // 2
    off = BANNER_ROW * 40 + col
    block[off:off + len(codes)] = codes
    return bytes(block)


def relink(program: bytes) -> bytes:
    """Rewrite the line links for $0801, as BASIC's own relink does after a
    load. Saved-from-$0801 programs come back byte-identical."""
    out = bytearray(program)
    pos = 0
    while True:
        if pos + 2 > len(out):
            raise ValueError("program truncated (no end marker)")
        if out[pos] == 0 and out[pos + 1] == 0:
            return bytes(out[:pos + 2])
        end = out.index(0, pos + 4)          # line terminator
        nxt = BASIC_LOAD + end + 1
        out[pos] = nxt & 0xFF
        out[pos + 1] = nxt >> 8
        pos = end + 1


def build_packaged(program: bytes, image: bytes, stub: bytes) -> bytes:
    """Assemble the full packaged PRG (including the 2-byte load address).

    program: tokenized BASIC body as at $0801 (ends with the $00,$00 marker).
    image:   16K MDBASIC image body ($8000-$bfff).
    stub:    pack_stub.bin with the newvec/initclk sentinels already patched.
    """
    if len(image) != IMAGE_SIZE:
        raise ValueError(f"image must be {IMAGE_SIZE} bytes, got {len(image)}")
    if len(stub) > STUB_MAX:
        raise ValueError(f"stub is {len(stub)} bytes, max {STUB_MAX}")
    program = relink(program)
    progend = BASIC_LOAD + len(program)

    stub = bytearray(stub.ljust(STUB_MAX, b"\x00"))
    stub[STUB_PROGEND_OFF] = progend & 0xFF
    stub[STUB_PROGEND_OFF + 1] = progend >> 8

    out = bytearray()
    out += FILE_LOAD.to_bytes(2, "little")           # PRG load address
    out += STUB_LOAD.to_bytes(2, "little")           # $0302 IMAIN -> stub
    out += VECTOR_BLOCK                              # $0304-$0333
    out += stub                                      # $0334-$03ff
    out += screen_fill()                             # $0400-$07ff
    out += b"\x00"                                   # $0800
    out += program                                   # $0801-
    out += image                                     # progend-
    return bytes(out)


def load_program_prg(path: Path) -> bytes:
    prg = path.read_bytes()
    load = prg[0] | (prg[1] << 8)
    if load != BASIC_LOAD:
        raise ValueError(f"{path}: load address ${load:04x} != $0801")
    return prg[2:]


def load_image_prg(path: Path) -> bytes:
    prg = path.read_bytes()
    load = prg[0] | (prg[1] << 8)
    if load != IMAGE_LOAD:
        raise ValueError(f"{path}: load address ${load:04x} != $8000")
    return prg[2:]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("program", type=Path, help="tokenized BASIC PRG ($0801)")
    parser.add_argument("out", type=Path, help="output packaged PRG")
    parser.add_argument("--image", type=Path, required=True,
                        help="MDBASIC image PRG ($8000, 16K body)")
    parser.add_argument("--lst", type=Path, required=True,
                        help="mdbasic.lst for newvec/initclk addresses")
    parser.add_argument("--stub", type=Path, required=True,
                        help="assembled pack_stub binary (raw, for $0334)")
    args = parser.parse_args()

    stub = patch_stub_syms(args.stub.read_bytes(),
                           lst_label_addr(args.lst, "newvec"),
                           lst_label_addr(args.lst, "initclk"))
    out = build_packaged(load_program_prg(args.program),
                         load_image_prg(args.image), stub)
    args.out.write_bytes(out)
    print(f"packaged {args.out} ({len(out)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
