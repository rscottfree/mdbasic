# MDBASIC build & host tools

Build-time and host-side helpers for the MDBASIC utilities. The VICE regression
tests live one level over in [`../tests/`](../tests/README.md); this directory is
the tooling those tests (and releases) are built from.

All commands below are shown from the repository root. Each script also derives its
own paths, so it can be invoked from anywhere.

## `build_disk.sh` — build the release artifacts

```sh
sh utilities/tools/build_disk.sh [outdir]        # default outdir: utilities/build/
```

Assembles `mdbasic.asm` (from the repo root), renders the markdown manual and
assembles every utility tool into extra cartridge banks, and writes the four
distributables:

- **`mdbasic.prg`** — raw 16K image (`$8000-$BFFF`).
- **`mdbasic.d64`** — the template `mdbasic.d64` with the fresh PRG swapped in.
- **`mdbasic.d81`** — a fresh 1581 disk mirroring every file from the D64.
- **`mdbasic.crt`** — a Magic Desk auto-start cartridge (see `make_crt.py`).

Needs `tmpx`, `c1541`, and `python3`. The docs banks are built from
`utilities/docs/manual/`.

## `make_crt.py` — wrap a PRG into a Magic Desk cartridge

MDBASIC runs from RAM at `$8000-$BFFF` and pages the BASIC ROM in/out underneath
itself, so it cannot execute from a plainly mapped cartridge. The cartridge is a
Magic Desk image (CRT hardware id 19): a small loader in bank 0 cold-starts the
machine, copies the 16K image from the banked window into RAM, disables the
cartridge, and restarts through the normal reset path (which finds the copied
"CBM80" signature and launches MDBASIC).

```sh
python3 utilities/tools/make_crt.py IN.prg OUT.crt \
    [--pager … --index … --data … --handler … --renum … --move … --copy … \
     --convert … --pack … --menu … --mdbasic-lst …]
```

The bare form builds the plain 3-bank image; the `--pager/--handler/…` options
append the docs-pager + utility banks and switch the loader to install the
CTRL+RESTORE handler (`build_disk.sh` supplies them all). The frozen loader stub
is regenerated from `../src/boot.asm` into `cart_boot.bin`; `make_crt.py`'s module
docstring documents the full bank layout.

## `build_docs.py` — render the markdown manual onto the cartridge

The manual is authored as one markdown file per topic under
`utilities/docs/manual/` (edit those directly — they are the source of truth).
This tool renders them to 40-column C64 screen-code line records and packs them
into Magic Desk doc banks that `make_crt.py` appends and `docs_pager.asm` displays.

```sh
python3 utilities/tools/build_docs.py --list                 # topic index
python3 utilities/tools/build_docs.py --preview SCREEN COLOR  # render topics to the terminal
python3 utilities/tools/build_docs.py --pack /tmp/docs.bin    # writes .idx + .dat
```

## `c64_basic_prg.py` — tokenize ASCII BASIC into a PRG

```sh
python3 utilities/tools/c64_basic_prg.py source.bas output.prg
python3 utilities/tools/c64_basic_prg.py --dialect mdbasic source.bas output.prg
```

Writes tokenized C64 BASIC V2 PRGs at `$0801`. The `mdbasic` dialect also emits
MDBASIC extension tokens, so it can build programs meant to run after MDBASIC is
installed. Use this instead of `petcat`, which misreads uppercase ASCII source as
shifted PETSCII.

## `pack_prg.py` — host-side twin of the PACKAGE tool

The C64-side packager (`../src/pack_tool.asm`, menu key **P**) writes MDBASIC + the
BASIC program in memory as one standalone auto-run PRG. `pack_prg.py` reproduces
that exact byte layout on the host, so tests can byte-compare the emulator's output
against an oracle. Imported by the pack tests; also runnable standalone.

## `aseprite_to_spr.py` — Aseprite → MDBASIC sprite data

Converts an Aseprite animation into MDBASIC `.spr` sprite-data file(s). It parses
the `.aseprite` file directly (Python 3 standard library only — no Pillow or the
Aseprite CLI), so there is no need to export a PNG first.

```sh
# One sprite per frame, scaled to fit 24x21, loading at index 128 ($2000):
python3 utilities/tools/aseprite_to_spr.py run.aseprite run.spr

# Full-resolution 2x2 tiling (four files) into clean upper RAM (bank 3):
python3 utilities/tools/aseprite_to_spr.py run.aseprite run.spr --split 2x2 --index 16 --bank 3

# Multicolor, previewing each sprite as ASCII art on stderr:
python3 utilities/tools/aseprite_to_spr.py run.aseprite run.spr --multicolor --preview
```

A `.spr` is a PRG-style binary (2-byte load address + 64-byte sprite blocks), so it
loads with `LOAD"RUN.SPR",8,1` and animates with `PLAY SPRITE`. Highlights:

- **Colour modes** — hires silhouettes (default) or `--multicolor` (up to three
  auto-picked C64 colours, reported as `SPRITE`/`SPRCOL` values).
- **Splitting** — `--split CxR` tiles artwork larger than one 24x21 sprite across a
  grid at native resolution and reports any pixels that must be clipped.
- **Addressing** — `--load-addr` (absolute) or `--index N [--bank B]`
  (`address = index*64 + bank*16384`); the printed data index is the value to use
  with `SPRITE`/`PLAY SPRITE`.
- **Layers** — `--skip-layers` (default `BG`) drops backdrop layers.

Run `python3 utilities/tools/aseprite_to_spr.py --help` for the full option list.

## Smaller helpers

- **`bin2inc.py IN.bin OUT.inc LABEL`** — emit an assembled blob as a tmpx
  `.byte` include under `LABEL` so one tool can embed another (the packager embeds
  its boot stub this way).
- **`d81_copy_args.py`** — used inside `build_disk.sh`: turns a `c1541 -list` into
  NUL-separated copy arguments so the D81 mirror handles filenames with spaces.
- **`stamp_version.sh PATH/TO/mdbasic.asm`** — write a copy of `mdbasic.asm` with
  the version banner stamped to the current date (for releases); prints the temp
  path.
