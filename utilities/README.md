# MDBASIC utilities

Everything this fork adds on top of upstream MDBASIC lives here. The repository
root stays byte-identical to upstream (the `mdbasic.asm` runtime, `mdbasic.pdf`,
the template `mdbasic.d64`, `README.md`, `LICENSE.txt`, `NOTICE.txt`,
`tasm64.lang`, and the `compile.sh`/`runcart.sh` dev-loop scripts). The build here
reads `mdbasic.asm` from the root and layers extra cartridge banks on top.

See [`ENHANCEMENTS.md`](ENHANCEMENTS.md) for the feature list and
[`CLAUDE.md`](CLAUDE.md) for the architecture notes.

## Layout

```
utilities/
  src/      Cartridge-tool 6502 sources, assembled into extra Magic Desk banks:
            the CTRL+RESTORE menu (menu.asm / menu_body.asm), docs pager
            (docs_pager.asm), renumber/move/copy tool (edit_tool_common.asm plus
            the renum_tool/move_tool/copy_tool wrappers), number-base converter
            (convert_tool.asm), packager (pack_tool.asm / pack_stub.asm), and the
            cart loader (boot.asm).
  tools/    Build and host-side authoring tools — see tools/README.md.
  tests/    The VICE regression suite — see tests/README.md.
  docs/manual/  The on-cart manual, one markdown file per topic. Edit these; they
                are the source of truth the docs pager is built from.
  build/    build_disk.sh output. Intermediates are ignored; the four final
            distributables (mdbasic.crt/.d64/.d81/.prg) are committed so a fresh
            clone is ready to run.
```

## Prerequisites

Put these on your `PATH`:

- **`tmpx`** — TMPx / Turbo Assembler: <https://style64.org/file/TMPx_v1.1.0-STYLE.zip>
- **`x64sc`** and **`c1541`** — from VICE (tests are validated against 3.10).
- **`python3`** — 3.9+, standard library only.

## Build

From the repository root:

```sh
sh utilities/tools/build_disk.sh            # -> utilities/build/
sh utilities/tools/build_disk.sh /tmp/out   # or build elsewhere
```

This assembles `mdbasic.asm`, renders the markdown manual, and bundles the utility
tools into extra cartridge banks, writing:

| File          | What it is                                                          |
|---------------|---------------------------------------------------------------------|
| `mdbasic.prg` | Raw 16K image (`$8000-$BFFF`).                                       |
| `mdbasic.d64` | 1541 disk: the template `mdbasic.d64` with the fresh PRG swapped in. |
| `mdbasic.d81` | 1581 disk mirroring the D64.                                         |
| `mdbasic.crt` | Magic Desk auto-start cartridge with the docs pager + utility tools. |

The root `compile.sh` stays the fast assemble-and-launch loop for the base image.

## Docs

The manual is markdown under `docs/manual/`. Preview or repack it on its own:

```sh
python3 utilities/tools/build_docs.py --list                 # topic index
python3 utilities/tools/build_docs.py --preview SCREEN COLOR  # render topics
python3 utilities/tools/build_docs.py --pack /tmp/docs.bin    # writes .idx + .dat
```

## Test

```sh
sh utilities/tests/run_all_tests.sh                                    # full VICE suite
python3 utilities/tests/vice_cart_test.py utilities/build/mdbasic.crt  # quick smoke test
```

Any script in `utilities/tests/` runs directly with `python3`. See
[`tests/README.md`](tests/README.md) for the harness details.
