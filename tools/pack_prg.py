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

Crunched variant (--crunch): the same content, LZ-compressed into a smaller
self-extracting PRG (see build_crunched below for the layout and lz_crunch for
the format). The compressor here and the 6502 one in pack_tool.asm implement
the identical algorithm, so crunched files stay byte-comparable too.

Usage:
    tools/pack_prg.py --image mdbasic.prg --lst build/mdbasic.lst \
        --stub build/pack_stub.bin program.prg out.prg
    tools/pack_prg.py --image mdbasic.prg --lst build/mdbasic.lst \
        --crunch --crunch-stub build/crunch_stub.bin program.prg out.prg
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

# ---- crunched-variant layout (keep in sync with crunch_stub.asm) ----
CRUNCH_STUB_LOAD = 0x0600    # self-extraction stub (IMAIN points here)
CRUNCH_STUB_MAX = 0x0200     # $0600-$07ff
PAYLOAD_LOAD = 0x0803        # compressed payload, after the $0801 $00,$00
                             # empty-program decoy that keeps the load-time
                             # relink walk off the payload
PAYLOAD_TOP = 0xFFF9         # stub relocates the payload so its last byte
                             # lands here; $fffa-$ffff hold planted RAM
                             # NMI/RESET/IRQ vectors during decrunch
FILE_END_MAX = 0xD000        # a PRG loading past $cfff would write into I/O

# ---- LZ crunch format ----
# Bit-interleaved LZSS, shared bit-for-bit by three implementations:
# lz_crunch/lz_decrunch here, the native 6502 encoder in pack_tool.asm, and
# the decoder in crunch_stub.asm. The encoder is deliberately deterministic
# (greedy parse, fixed hash, fixed chain-walk order and depth) so the native
# tool's output is byte-identical to this oracle.
#
# One stream carries whole bytes and control bits. Control bits come from a
# reservoir byte that both sides fetch/emit inline: the encoder appends a
# placeholder byte at the moment it writes a bit into an empty reservoir; the
# decoder fetches its reservoir byte at the moment it reads a bit from an
# empty one -- consumption orders are identical, so positions align. Bits fill
# each reservoir byte MSB-first; whole bytes (literals, offset low bytes) are
# appended/read at the stream cursor between bits.
#
# Item = control bit: 1 = literal (one whole byte), 0 = match:
#   offset-type bit: 0 = short (whole byte = off-1, offsets 1-256),
#                    1 = long (4 reservoir bits = (off-1) >> 8, then a whole
#                        byte = (off-1) low; offsets 257-4096)
#   then Elias-gamma(len-1), MSB-first (bitlen-1 zeros, then the value's
#   bits from its leading 1); lengths 2-255. Matches copy from the already-
#   decoded output; off < len (self-overlap/RLE) is allowed.
#
# Container (the file payload) = per chunk: dest u16le, outlen u16le, stream
# (reservoir starts empty per chunk); terminated by dest = $0000. Chunks are
# compressed independently.
CRUNCH_WINDOW = 4096
CRUNCH_MINMATCH = 2
CRUNCH_MAXMATCH = 255
CRUNCH_DEPTH = 64            # candidates examined per position
CRUNCH_NIL = 0xFFFF


def _crunch_hash(b0: int, b1: int) -> int:
    return (b0 + (b1 << 2)) & 0x3FF


def _gamma(value: int) -> list[int]:
    """Elias gamma bits for value >= 1, MSB-first with leading zeros."""
    n = value.bit_length() - 1
    return [0] * n + [(value >> i) & 1 for i in range(n, -1, -1)]


class _BitWriter:
    """The interleaved stream writer (see the format comment)."""

    def __init__(self) -> None:
        self.out = bytearray()
        self.res_idx = -1        # position of the open reservoir byte
        self.res_bits = 0        # bits already in it

    def put_bit(self, bit: int) -> None:
        if self.res_bits == 0:
            self.res_idx = len(self.out)
            self.out.append(0)
            self.res_bits = 8
        self.res_bits -= 1
        if bit:
            self.out[self.res_idx] |= 1 << self.res_bits

    def put_bits(self, bits: list[int]) -> None:
        for b in bits:
            self.put_bit(b)

    def put_byte(self, val: int) -> None:
        self.out.append(val)


def lz_crunch(data: bytes) -> bytes:
    """Compress one chunk. Match finder: 1024-bucket hash of the 2-byte
    prefix, per-position chain table indexed pos & $0fff (slots are unique
    within the 4096-byte window), most-recent-first walk capped at
    CRUNCH_DEPTH; ties keep the earlier (nearer) candidate."""
    head = [CRUNCH_NIL] * 1024
    chain = [CRUNCH_NIL] * 4096
    n = len(data)

    def insert(p: int) -> None:
        if p + CRUNCH_MINMATCH <= n:
            h = _crunch_hash(data[p], data[p + 1])
            chain[p & 0xFFF] = head[h]
            head[h] = p

    w = _BitWriter()
    pos = 0
    while pos < n:
        best_len = 0
        best_off = 0
        maxl = min(CRUNCH_MAXMATCH, n - pos)
        if n - pos >= CRUNCH_MINMATCH:
            cand = head[_crunch_hash(data[pos], data[pos + 1])]
            for _ in range(CRUNCH_DEPTH):
                if cand == CRUNCH_NIL or pos - cand > CRUNCH_WINDOW:
                    break
                l = 0
                while l < maxl and data[cand + l] == data[pos + l]:
                    l += 1
                if l > best_len:
                    best_len, best_off = l, pos - cand
                if l == maxl:
                    break
                cand = chain[cand & 0xFFF]
        if best_len >= CRUNCH_MINMATCH:
            om1 = best_off - 1
            w.put_bit(0)
            if om1 < 256:
                w.put_bit(0)
            else:
                w.put_bit(1)
                w.put_bits([(om1 >> (8 + i)) & 1 for i in (3, 2, 1, 0)])
            w.put_byte(om1 & 0xFF)
            w.put_bits(_gamma(best_len - 1))
            for p in range(pos, pos + best_len):
                insert(p)
            pos += best_len
        else:
            w.put_bit(1)
            w.put_byte(data[pos])
            insert(pos)
            pos += 1
    return bytes(w.out)


class _BitReader:
    def __init__(self, stream: bytes) -> None:
        self.stream = stream
        self.rd = 0
        self.res = 0
        self.res_bits = 0

    def get_bit(self) -> int:
        if self.res_bits == 0:
            self.res = self.stream[self.rd]
            self.rd += 1
            self.res_bits = 8
        self.res_bits -= 1
        return (self.res >> self.res_bits) & 1

    def get_byte(self) -> int:
        b = self.stream[self.rd]
        self.rd += 1
        return b

    def get_gamma(self) -> int:
        n = 0
        while self.get_bit() == 0:
            n += 1
        v = 1
        for _ in range(n):
            v = (v << 1) | self.get_bit()
        return v


def _decode_items(stream: bytes, outlen: int):
    """Yield (kind, payload) per item while decoding; kind 'L' -> the byte,
    'M' -> (off, length). The caller accumulates output; used stream bytes
    are available afterwards via the returned reader (see lz_decrunch)."""
    r = _BitReader(stream)
    produced = 0
    while produced < outlen:
        if r.get_bit():
            yield r, "L", r.get_byte()
            produced += 1
        else:
            hi = 0
            if r.get_bit():
                for _ in range(4):
                    hi = (hi << 1) | r.get_bit()
            om1 = (hi << 8) | r.get_byte()
            length = r.get_gamma() + 1
            yield r, "M", (om1 + 1, length)
            produced += length
    if produced != outlen:
        raise ValueError("chunk overran its outlen")


def lz_decrunch(stream: bytes, outlen: int) -> tuple[bytes, int]:
    """Decode one chunk; returns (data, stream bytes consumed)."""
    out = bytearray()
    reader = None
    for reader, kind, payload in _decode_items(stream, outlen):
        if kind == "L":
            out.append(payload)
        else:
            off, length = payload
            for _ in range(length):
                out.append(out[-off])
    if len(out) != outlen:
        raise ValueError("chunk overran its outlen")
    return bytes(out), reader.rd if reader else 0


def crunch_payload(chunks: list[tuple[int, bytes]]) -> bytes:
    """The file payload: [dest u16le, outlen u16le, stream]... + $0000."""
    out = bytearray()
    for dest, data in chunks:
        out += dest.to_bytes(2, "little")
        out += len(data).to_bytes(2, "little")
        out += lz_crunch(data)
    out += b"\x00\x00"
    return bytes(out)


def _assert_decrunch_safe(payload: bytes, chunks: list[tuple[int, bytes]]) -> None:
    """Simulate the stub's in-memory decrunch and prove the forward decode
    never writes over unread payload bytes.

    The stub relocates the payload so its last byte sits at PAYLOAD_TOP, then
    decodes forward. Walk the token stream tracking the read cursor and every
    write, requiring writes to stay strictly below the read cursor. The
    analytic bound (payload below $8000, output capped at $c000, worst-case
    1-flag-bit-per-literal expansion) leaves >8K of slack for any packageable
    program; this check makes it concrete per file."""
    base = PAYLOAD_TOP + 1 - len(payload)
    rd = 0
    min_slack = 1 << 16
    for dest, data in chunks:
        exp_dest = int.from_bytes(payload[rd:rd + 2], "little")
        outlen = int.from_bytes(payload[rd + 2:rd + 4], "little")
        if (exp_dest, outlen) != (dest, len(data)):
            raise ValueError("payload does not match chunk list")
        rd += 4
        decoded, used = lz_decrunch(payload[rd:], outlen)
        if decoded != data:
            raise ValueError("crunch round-trip failed")
        # item-level pointer walk: after each item, everything written so far
        # must sit strictly below the read cursor
        wr = dest
        for reader, kind, item in _decode_items(payload[rd:], outlen):
            wr += 1 if kind == "L" else item[1]
            slack = (base + rd + reader.rd) - wr
            min_slack = min(min_slack, slack)
        rd += used
    if min_slack < 0x100:
        raise ValueError(f"decrunch overlap slack too small ({min_slack})")


def build_crunched(program: bytes, image: bytes, crunch_stub: bytes) -> bytes:
    """Assemble the crunched packaged PRG (including the load address).

    Layout (load address $0302):
        $0302-$0303 : IMAIN -> the crunch stub at $0600
        $0304-$0333 : the standard vector block (same as the plain variant)
        $0334-$03ff : zero fill (cassette buffer, unused on a stock machine)
        $0400-$05ff : screen rows 0-12: blanks + the banner row
        $0600-$07ff : crunch_stub.asm (self-extraction), space-padded
        $0800       : $00 (byte before BASIC text)
        $0801-$0802 : $00,$00 -- an empty program, so the load-time relink
                      stops immediately instead of walking the payload
        $0803-      : compressed payload (program chunk, image chunk, $0000)

    The stub needs no per-file patching: it finds the payload end in the
    KERNAL's load-end pointer $ae/$af and the chunk geometry in the payload
    itself (VARTAB comes from the write cursor after the program chunk).
    """
    if len(image) != IMAGE_SIZE:
        raise ValueError(f"image must be {IMAGE_SIZE} bytes, got {len(image)}")
    if len(crunch_stub) > CRUNCH_STUB_MAX:
        raise ValueError(f"crunch stub is {len(crunch_stub)} bytes, "
                         f"max {CRUNCH_STUB_MAX}")
    program = relink(program)
    chunks = [(BASIC_LOAD, program), (IMAGE_LOAD, image)]
    payload = crunch_payload(chunks)
    _assert_decrunch_safe(payload, chunks)

    out = bytearray()
    out += FILE_LOAD.to_bytes(2, "little")           # PRG load address
    out += CRUNCH_STUB_LOAD.to_bytes(2, "little")    # $0302 IMAIN -> stub
    out += VECTOR_BLOCK                              # $0304-$0333
    out += b"\x00" * (0x0400 - STUB_LOAD)            # $0334-$03ff
    out += screen_fill()[:0x200]                     # $0400-$05ff (banner row)
    out += crunch_stub.ljust(CRUNCH_STUB_MAX, b"\x20")  # $0600-$07ff
    out += b"\x00"                                   # $0800
    out += b"\x00\x00"                               # $0801 empty-program decoy
    out += payload                                   # $0803-
    end = FILE_LOAD + len(out) - 2
    if end > FILE_END_MAX:
        raise ValueError(f"crunched file ends at ${end:04x}, past "
                         f"${FILE_END_MAX:04x}")
    return bytes(out)


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


def _patch_jsr(stub: bytearray, sentinel: int, target: int, expect: int) -> None:
    pat = bytes([0x20, sentinel & 0xFF, sentinel >> 8])
    hits = [i for i in range(len(stub) - 2) if bytes(stub[i:i + 3]) == pat]
    if len(hits) != expect:
        raise RuntimeError(f"expected {expect} jsr ${sentinel:04x} in stub, "
                           f"found {len(hits)}")
    for hit in hits:
        stub[hit + 1] = target & 0xFF
        stub[hit + 2] = target >> 8


def patch_stub_syms(blob: bytes, newvec: int, initclk: int,
                    expect: int = 1) -> bytes:
    """Patch the newvec/initclk jsr sentinels with real addresses. `blob` is
    either a bare stub (expect=1) or a binary embedding several, like
    pack_tool.bin with both the plain and the crunch stub templates
    (expect=2)."""
    out = bytearray(blob)
    _patch_jsr(out, NEWVEC_SENTINEL, newvec, expect)
    _patch_jsr(out, INITCLK_SENTINEL, initclk, expect)
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
    parser.add_argument("--stub", type=Path,
                        help="assembled pack_stub binary (raw, for $0334)")
    parser.add_argument("--crunch", action="store_true",
                        help="write the LZ-crunched self-extracting variant")
    parser.add_argument("--crunch-stub", type=Path,
                        help="assembled crunch_stub binary (raw, for $0600; "
                             "required with --crunch)")
    args = parser.parse_args()

    newvec = lst_label_addr(args.lst, "newvec")
    initclk = lst_label_addr(args.lst, "initclk")
    if args.crunch:
        if not args.crunch_stub:
            parser.error("--crunch requires --crunch-stub")
        stub = patch_stub_syms(args.crunch_stub.read_bytes(), newvec, initclk)
        out = build_crunched(load_program_prg(args.program),
                             load_image_prg(args.image), stub)
    else:
        if not args.stub:
            parser.error("--stub is required (or use --crunch)")
        stub = patch_stub_syms(args.stub.read_bytes(), newvec, initclk)
        out = build_packaged(load_program_prg(args.program),
                             load_image_prg(args.image), stub)
    args.out.write_bytes(out)
    print(f"packaged {args.out} ({len(out)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
