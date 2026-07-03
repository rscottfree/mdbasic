# MDBASIC VICE Test Tools

These helpers create real C64 PRG files locally, put them on a D64 with
`c1541`, run them in VICE, and assert the resulting C64 screen through the VICE
binary monitor.

## BASIC PRG Generation

```sh
tools/c64_basic_prg.py source.bas output.prg
tools/c64_basic_prg.py --dialect mdbasic source.bas output.prg
```

The generator writes tokenized C64 BASIC V2 PRGs at `$0801`. The `mdbasic`
dialect also emits MDBASIC extension tokens, so it can build programs intended
to run after MDBASIC has been installed with `SYS64738` or as a cartridge.

This avoids the common `petcat` trap where uppercase ASCII source is interpreted
as shifted PETSCII. If you do use `petcat`, write lowercase BASIC source.

## VICE PRG/D64 Test Harness

```sh
tools/vice_prg_test.py \
  --file main=/tmp/main.prg \
  --file data=/tmp/data.prg \
  --run main \
  --expect "DONE"
```

The harness:

1. Creates a temporary D64.
2. Writes every `--file cbmname=host.prg` to the D64.
3. Starts `x64sc` with drive 8 mounted, virtual device traps enabled, and true
   drive emulation disabled for fast functional tests.
4. Injects only the initial `LOAD"MAIN",8` and `RUN` through short-lived binary
   monitor connections.
5. Polls screen RAM for expected text and quits VICE cleanly.

## Sprite Timing Validation

`tests/sprite_timing.bas` measures sprite `MOVE ... TO ...` delays against the
jiffy clock at `$A2`. It records result bytes at `$C000-$C002`:

- `$C000`: speed 0 delta
- `$C001`: speed 1 delta
- `$C002`: speed 2 delta

Build and run in VICE:

```sh
tmpx -l /tmp/mdbasic.lst -i mdbasic.asm -o /tmp/mdbasic.prg
tools/c64_basic_prg.py --dialect mdbasic tests/sprite_timing.bas /tmp/sprtime.prg
tools/vice_prg_test.py \
  --file sprtime=/tmp/sprtime.prg \
  --file mdbasic=/tmp/mdbasic.prg \
  --run sprtime \
  --expect "DONE"
```

Run the same validation on the Ultimate 64 at `c64ultimate`:

```sh
tools/u64_sprite_timing_test.sh
```

Expected U64 result bytes are typically `010c16` or `020c16`: speed 0 may cross
a sampling boundary, while speed 1 takes about 12 jiffies and speed 2 takes
about 22 jiffies. The same result under `$D030=$FF` turbo confirms the delay is
jiffy-clock based.

## Aseprite to Sprite Conversion

`tools/aseprite_to_spr.py` converts an Aseprite animation into MDBASIC `.spr`
sprite-data file(s). It parses the `.aseprite` file directly (Python 3 standard
library only — no Pillow or Aseprite CLI), so there is no need to export a PNG
first.

```sh
# One sprite per frame, scaled to fit 24x21, loading at index 128 ($2000):
tools/aseprite_to_spr.py run.aseprite run.spr

# Full-resolution 2x2 tiling (four files) into clean upper RAM (bank 3):
tools/aseprite_to_spr.py run.aseprite run.spr --split 2x2 --index 16 --bank 3

# Multicolor, previewing each sprite as ASCII art on stderr:
tools/aseprite_to_spr.py run.aseprite run.spr --multicolor --preview
```

A `.spr` is a PRG-style binary — a 2-byte load address followed by 64-byte
sprite blocks — so it loads with `LOAD"RUN.SPR",8,1` and animates with
`PLAY SPRITE`. Highlights:

- **Colour modes** — hires silhouettes (default) or `--multicolor` (up to three
  auto-picked C64 colours, reported as `SPRITE`/`SPRCOL` values).
- **Splitting** — `--split CxR` tiles artwork larger than one 24x21 sprite
  across a grid at native resolution, positioning the window over all frames to
  avoid clipping and reporting any pixels that must be clipped.
- **Addressing** — target a location with an absolute `--load-addr` or a
  bank-relative `--index N [--bank B]` (`address = index*64 + bank*16384`); the
  data index printed for each file is the value to use with `SPRITE`/
  `PLAY SPRITE`.
- **Layers** — `--skip-layers` (default `BG`) drops backdrop layers so only the
  character is rasterized.

Run `tools/aseprite_to_spr.py --help` for the full option list.

## Building release artifacts

`tools/build_disk.sh [outdir]` assembles `mdbasic.asm` and writes all four
distributable artifacts into `outdir` (default `build/`):

```sh
tools/build_disk.sh
# build/mdbasic.prg  build/mdbasic.d64  build/mdbasic.d81  build/mdbasic.crt
```

- **`mdbasic.d64`** — the template `mdbasic.d64` with the fresh PRG swapped in.
- **`mdbasic.d81`** — a fresh 1581 disk mirroring every file from the D64.
- **`mdbasic.crt`** — a Magic Desk auto-start cartridge (see below).

### Magic Desk cartridge

MDBASIC runs from RAM at `$8000-$BFFF` and pages the BASIC ROM in/out underneath
itself, so it cannot execute from a plainly mapped cartridge. The cartridge is a
3-bank (24K) **Magic Desk** image (CRT hardware id 19): a 158-byte loader in
bank 0 cold-starts the machine, copies the 16K image from the banked
`$8000-$9FFF` window into RAM, disables the cartridge, and restarts through the
normal reset path, which finds the copied "CBM80" signature and launches
MDBASIC.

`tools/make_crt.py` builds the `.crt` from a PRG and the frozen loader
(`tools/cart_boot.bin`); its module docstring documents the layout and the
loader disassembly. The loader is image-independent, so only the 16K image
changes between builds.

```sh
tools/make_crt.py build/mdbasic.prg build/mdbasic.crt
```

(Current VICE `cartconv` pads Magic Desk input to a power of two, yielding a
4-bank/32K image, so `make_crt.py` writes the exact 3-bank `.crt` directly.)

Boot a cartridge headless and assert the banner appears:

```sh
tools/vice_cart_test.py build/mdbasic.crt
```
