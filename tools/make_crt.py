#!/usr/bin/env python3
"""Wrap a 16K MDBASIC PRG ($8000-$BFFF) into a Magic Desk .crt cartridge.

MDBASIC runs from RAM at $8000-$BFFF and pages the BASIC ROM in and out
underneath itself, so it cannot execute directly from a plain mapped cartridge.
The shipped cartridge therefore uses the Magic Desk banking scheme (CRT hardware
id 19): a small loader in bank 0 cold-starts the machine, copies the full 16K
image from the banked $8000-$9FFF window into RAM, disables the cartridge, and
restarts through the normal reset path -- which then finds the "CBM80" signature
of the copied RAM image and launches MDBASIC.

Cartridge layout (three 8K banks, 24K total):

    bank 0, $0000-$009d : loader stub (tools/cart_boot.bin, see below)
    bank 0, $009e-$1fff : first 8034 bytes of the 16K image
    bank 1, $0000-$1fff : next 8192 bytes of the image
    bank 2, $0000-$009d : final 158 bytes of the image
    bank 2, $009e-$1fff : zero padding

The loader stub is hardware/image independent (it always copies $4000 bytes to
$8000), so it is kept as a frozen 158-byte blob in tools/cart_boot.bin. Its
disassembly:

    8000: .word $8009, $8009      ; cold + warm cart vectors
    8004: "CBM80"                 ; autostart signature
    8009: sei / cld / ldx #$fb / txs
          jsr $fda3               ; IOINIT
          jsr $fd50               ; RAMTAS
          lda #$a0 / sta $0284    ; MEMSIZ hi = $a000
          jsr $fd15               ; RESTOR (KERNAL vectors)
          jsr $ff5b               ; CINT  (screen/VIC)
          cli
          lda $d011 / and #$ef / sta $d011   ; blank screen during copy
          ; set up copy: count=$4000, dest=$8000, src=$809e, bank=$00
          ...
          ldx #0 : copy 256 bytes of the PIC copier to $0400 : jmp $0400
    copier (position independent, runs from $0400):
          select Magic Desk bank via $de00, stream src window $8000-$9fff to
          dest, advancing the bank each time src crosses $a000, until $4000
          bytes copied; then sta $de00 with bit 7 set (cart off); jmp ($fffc).

cartconv in current VICE pads Magic Desk input to a power of two (producing a
4-bank/32K image), so this script writes the exact 3-bank .crt itself.
"""
from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

IMAGE_SIZE = 0x4000          # MDBASIC runtime image: $8000-$BFFF (16K)
LOAD_ADDR = 0x8000
BANK_SIZE = 0x2000           # 8K Magic Desk bank
NUM_BANKS = 3                # 24K of ROM holds stub + 16K image + padding
INDEX_BANK = NUM_BANKS       # bank 3: docs pager code + topic index + handler
DATA_BANK0 = NUM_BANKS + 1   # banks 4+: doc line stream
PAGER_MAX = 0x0c00           # menu.asm copies 12 pages (3KB) to $c000 per tool
INDEX_OFF = 0x0c00           # topic index sits at bank 3 $8c00 (3K reserve to $97ff)
HANDLER_OFF = 0x1800         # RESTORE handler sits at bank 3 $9800 (boot.asm reads it)
HANDLER_LEN = 0xb8           # boot.asm HANDLER_LEN: fixed byte count boot.asm copies
                             # from bank 3 $9800 to $033c -- must stay in sync with
                             # boot.asm's own constant, or the copy silently truncates
                             # menu.asm's resident tail at boot/cart-install time
DOCSFLAG_OFF = 9             # boot.asm `docsflag` word, at stub $8009
TOOLBANKS_OFF = 3            # menu.asm `toolbanks`, at $033f (offset 3 past its JMP)
MENU_OFF = 0x1800            # menu-body UI sits at the first tool bank's $9800
TOOL_MAX = PAGER_MAX         # menu.asm copies 12 pages: $c000-$cbff, leaving SCRBUF
                             # at $cc00-$cfff intact
STUB_PATH = Path(__file__).with_name("cart_boot.bin")


def _chip_packet(bank: int, data: bytes) -> bytes:
    """One Magic Desk CHIP packet: 16-byte header + an 8K bank."""
    if len(data) != BANK_SIZE:
        raise ValueError(f"bank {bank} is {len(data)} bytes, need {BANK_SIZE}")
    chip = bytearray(0x10)
    chip[0:4] = b"CHIP"
    struct.pack_into(">I", chip, 0x04, 0x10 + BANK_SIZE)  # packet length
    struct.pack_into(">H", chip, 0x08, 0)                 # chip type: ROM
    struct.pack_into(">H", chip, 0x0a, bank)              # bank number
    struct.pack_into(">H", chip, 0x0c, LOAD_ADDR)         # load address
    struct.pack_into(">H", chip, 0x0e, BANK_SIZE)         # rom size
    return bytes(chip) + data


def _cart_header(name: str) -> bytearray:
    header = bytearray(0x40)
    header[0:16] = b"C64 CARTRIDGE   "
    struct.pack_into(">I", header, 0x10, 0x40)      # header length
    struct.pack_into(">H", header, 0x14, 0x0100)    # version 1.0
    struct.pack_into(">H", header, 0x16, 19)        # hardware id: Magic Desk
    header[0x18] = 0x00                              # EXROM
    header[0x19] = 0x01                              # GAME  -> 8K config
    encoded = name.encode("ascii")[:32]
    header[0x20:0x20 + len(encoded)] = encoded
    return header


def doc_banks(pager: bytes, index: bytes, data: bytes, handler: bytes = b"",
              renum: bytes = b"", move: bytes = b"", copy: bytes = b"",
              convert: bytes = b"",
              menu: bytes = b"") -> list[bytes]:
    """Compose the cart banks: bank 3 = pager+index+handler, banks 4+ = doc data,
    and (if tools/menu are given) four final tool banks: renumber, move, copy,
    convert. The first tool bank also carries menu-body at $9800. Tool bank
    numbers depend on the doc-data bank count, so the first tool bank number is
    patched into the resident handler here."""
    if len(pager) > PAGER_MAX:
        raise ValueError(f"pager {len(pager)} bytes exceeds {PAGER_MAX}")
    if len(index) > HANDLER_OFF - INDEX_OFF:
        raise ValueError(f"index {len(index)} bytes exceeds reserve")
    if len(handler) > BANK_SIZE - HANDLER_OFF:
        raise ValueError(f"handler {len(handler)} bytes exceeds reserve")
    if len(handler) > HANDLER_LEN:
        raise ValueError(f"handler {len(handler)} bytes exceeds boot.asm's "
                          f"HANDLER_LEN ({HANDLER_LEN}) -- bump HANDLER_LEN in "
                          f"boot.asm (and here) to match, or the boot copy will "
                          f"silently truncate menu.asm's tail")
    if len(data) % BANK_SIZE:
        raise ValueError(f"doc data {len(data)} not a multiple of {BANK_SIZE}")
    data_banks = [data[i:i + BANK_SIZE] for i in range(0, len(data), BANK_SIZE)]

    tool_banks = []
    if renum or move or copy or convert or menu:
        if not (renum and move and copy and convert and menu):
            raise ValueError("renum, move, copy, convert and menu must be given together")
        for name, tool in (("renum", renum), ("move", move),
                           ("copy", copy), ("convert", convert)):
            if len(tool) > TOOL_MAX:
                raise ValueError(f"{name} tool {len(tool)} bytes exceeds {TOOL_MAX} "
                                 f"runtime copy limit ($c000-$cbff)")
        if len(menu) > BANK_SIZE - MENU_OFF:
            raise ValueError(f"menu-body {len(menu)} bytes exceeds reserve")
        # Tool banks are appended after bank3 + doc data.
        first_tool_bank = NUM_BANKS + 1 + len(data_banks)
        handler = bytearray(handler)
        handler[TOOLBANKS_OFF:TOOLBANKS_OFF + 4] = bytes([
            first_tool_bank, first_tool_bank + 1,
            first_tool_bank + 2, first_tool_bank + 3])
        handler = bytes(handler)
        for i, tool in enumerate((renum, move, copy, convert)):
            tb = bytearray(b"\x00" * BANK_SIZE)
            tb[0:len(tool)] = tool
            if i == 0:
                tb[MENU_OFF:MENU_OFF + len(menu)] = menu
            tool_banks.append(bytes(tb))

    bank3 = bytearray(b"\x00" * BANK_SIZE)
    bank3[0:len(pager)] = pager
    bank3[INDEX_OFF:INDEX_OFF + len(index)] = index
    bank3[HANDLER_OFF:HANDLER_OFF + len(handler)] = handler
    banks = [bytes(bank3)] + data_banks
    banks.extend(tool_banks)
    return banks


def build_crt(image: bytes, *, name: str = "MDBASIC", stub: bytes | None = None,
              extra_banks: list[bytes] | None = None) -> bytes:
    """Return a Magic Desk .crt wrapping a 16K MDBASIC image.

    extra_banks, if given, are appended as banks 3.. (the docs-pager banks) and
    the loader's `docsflag` is set so it installs the RESTORE handler and
    repoints the cart NMI vector (see boot.asm / docs-pager design).
    """
    if len(image) != IMAGE_SIZE:
        raise ValueError(f"image must be {IMAGE_SIZE} bytes, got {len(image)}")
    if stub is None:
        stub = STUB_PATH.read_bytes()
    if extra_banks:
        stub = bytearray(stub)
        stub[DOCSFLAG_OFF] = 0x01            # enable the docs-pager install
        stub = bytes(stub)

    raw = stub + image
    total = NUM_BANKS * BANK_SIZE
    if len(raw) > total:
        raise ValueError(f"stub+image ({len(raw)}) exceeds {total} bytes")
    raw = raw.ljust(total, b"\x00")

    out = bytearray(_cart_header(name))
    for bank in range(NUM_BANKS):
        out += _chip_packet(bank, raw[bank * BANK_SIZE:(bank + 1) * BANK_SIZE])
    for i, bank_data in enumerate(extra_banks or []):
        out += _chip_packet(NUM_BANKS + i, bank_data)
    return bytes(out)


def image_from_prg(prg: bytes) -> bytes:
    """Strip the 2-byte load address from a PRG and validate it is the image."""
    if len(prg) < 2:
        raise ValueError("PRG too short")
    load = prg[0] | (prg[1] << 8)
    if load != LOAD_ADDR:
        raise ValueError(f"PRG load address ${load:04x} != ${LOAD_ADDR:04x}")
    return prg[2:]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("prg", type=Path, help="MDBASIC PRG ($8000, 16K body)")
    parser.add_argument("crt", type=Path, help="output .crt path")
    parser.add_argument("-n", "--name", default="MDBASIC", help="cartridge name")
    parser.add_argument("--stub", type=Path, default=STUB_PATH,
                        help="Magic Desk loader stub (default: tools/cart_boot.bin)")
    parser.add_argument("--pager", type=Path, help="docs pager binary (raw, for $c000)")
    parser.add_argument("--index", type=Path, help="docs topic index (build/docs.idx)")
    parser.add_argument("--data", type=Path, help="docs line stream (build/docs.dat)")
    parser.add_argument("--handler", type=Path, help="RESTORE handler binary (raw, for $033c)")
    parser.add_argument("--renum", type=Path, help="renumber tool binary (raw, for $c000)")
    parser.add_argument("--move", type=Path, help="move tool binary (raw, for $c000)")
    parser.add_argument("--copy", type=Path, help="copy tool binary (raw, for $c000)")
    parser.add_argument("--convert", type=Path, help="convert tool binary (raw, for $c000)")
    parser.add_argument("--menu", type=Path, help="menu-body UI binary (raw, for $c000)")
    args = parser.parse_args()

    extra = None
    docs_args = (args.pager, args.index, args.data, args.handler)
    if any(docs_args):
        if not all(docs_args):
            parser.error("--pager, --index, --data and --handler must be given together")
        renum_args = (args.renum, args.move, args.copy, args.convert, args.menu)
        if any(renum_args) and not all(renum_args):
            parser.error("--renum, --move, --copy, --convert and --menu must be given together")
        renum = args.renum.read_bytes() if args.renum else b""
        move = args.move.read_bytes() if args.move else b""
        copy = args.copy.read_bytes() if args.copy else b""
        convert = args.convert.read_bytes() if args.convert else b""
        menu = args.menu.read_bytes() if args.menu else b""
        extra = doc_banks(args.pager.read_bytes(), args.index.read_bytes(),
                          args.data.read_bytes(), args.handler.read_bytes(),
                          renum=renum, move=move, copy=copy, convert=convert,
                          menu=menu)

    image = image_from_prg(args.prg.read_bytes())
    crt = build_crt(image, name=args.name, stub=args.stub.read_bytes(),
                    extra_banks=extra)
    args.crt.write_bytes(crt)
    nbanks = NUM_BANKS + (len(extra) if extra else 0)
    print(f"Built cart: {args.crt} ({len(crt)} bytes, {nbanks} banks)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
