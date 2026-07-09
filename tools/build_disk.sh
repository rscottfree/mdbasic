#!/bin/sh
# Assemble MDBASIC and build the distributable artifacts into the output dir:
#   mdbasic.prg  - raw 16K image ($8000-$BFFF)
#   mdbasic.d64  - 1541 disk: template contents with the fresh PRG
#   mdbasic.d81  - 1581 disk: same files as the D64, on the larger format
#   mdbasic.crt  - Magic Desk auto-start cartridge wrapping the PRG
#
# The D64 is a copy of the template disk with mdbasic.prg replaced. The D81 is
# formatted fresh and mirrors every file from that D64. See tools/make_crt.py
# for the cartridge format.
#
# Usage: build_disk.sh [outdir]

set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)
TEMPLATE="${MDBASIC_D64_TEMPLATE:-$ROOT/mdbasic.d64}"

OUTDIR=""
while [ $# -gt 0 ]; do
    case "$1" in
        -*)
            echo "ERROR: unknown option: $1" >&2
            exit 1
            ;;
        *)
            OUTDIR="$1"; shift ;;
    esac
done
OUTDIR="${OUTDIR:-$ROOT/build}"

PRG="$OUTDIR/mdbasic.prg"
LST="$OUTDIR/mdbasic.lst"
DISK="$OUTDIR/mdbasic.d64"
DISK81="$OUTDIR/mdbasic.d81"
CRT="$OUTDIR/mdbasic.crt"

for tool in tmpx c1541 python3; do
    command -v "$tool" >/dev/null 2>&1 || {
        echo "ERROR: required tool not found: $tool" >&2
        exit 1
    }
done

[ -f "$TEMPLATE" ] || {
    echo "ERROR: template disk not found: $TEMPLATE" >&2
    exit 1
}

mkdir -p "$OUTDIR"

# 1. Assemble the runtime image directly from the tracked source.
tmpx -l "$LST" -i "$ROOT/mdbasic.asm" -o "$PRG"

# 2. D64: copy the template and swap in the fresh PRG.
cp "$TEMPLATE" "$DISK"
c1541 "$DISK" \
    -delete "mdbasic.prg" \
    -write "$PRG" "mdbasic.prg" >/dev/null

# 3. D81: format fresh, mirror every D64 file (attached as unit 9), then refresh
#    the PRG from the fresh build. Filenames may contain spaces, so the copy
#    arguments are emitted NUL-separated and appended to c1541 via xargs -0.
rm -f "$DISK81"
c1541 "$DISK" -list 2>/dev/null \
    | python3 "$ROOT/tools/d81_copy_args.py" \
    | xargs -0 c1541 \
        -format "mdbasic,01" d81 "$DISK81" \
        -attach "$DISK" 9 \
        -unit 8 >/dev/null
c1541 "$DISK81" \
    -delete "mdbasic.prg" \
    -write "$PRG" "mdbasic.prg" >/dev/null

# 4. Docs pager banks (optional): bundle the manual into extra cart banks if the
#    PDF and pdftotext are available. The pager assembles to $c000 (run address);
#    strip its 2-byte load address to get the raw bank-3 image.
DOCS_ARGS=""
if [ -f "$ROOT/mdbasic.pdf" ] && command -v pdftotext >/dev/null 2>&1; then
    PAGER="$OUTDIR/docs_pager.bin"
    HANDLER="$OUTDIR/menu.bin"
    MENUBODY="$OUTDIR/menu_body.bin"
    RENUM="$OUTDIR/renum_tool.bin"
    MOVE="$OUTDIR/move_tool.bin"
    COPY="$OUTDIR/copy_tool.bin"
    CONVERT="$OUTDIR/convert_tool.bin"
    tmpx -i "$ROOT/docs_pager.asm" -o "$OUTDIR/docs_pager.prg" >/dev/null
    tail -c +3 "$OUTDIR/docs_pager.prg" > "$PAGER"
    tmpx -i "$ROOT/menu.asm" -o "$OUTDIR/menu.prg" >/dev/null
    tail -c +3 "$OUTDIR/menu.prg" > "$HANDLER"
    tmpx -i "$ROOT/menu_body.asm" -o "$OUTDIR/menu_body.prg" >/dev/null
    tail -c +3 "$OUTDIR/menu_body.prg" > "$MENUBODY"
    tmpx -i "$ROOT/renum_tool.asm" -o "$OUTDIR/renum_tool.prg" >/dev/null
    tail -c +3 "$OUTDIR/renum_tool.prg" > "$RENUM"
    tmpx -i "$ROOT/move_tool.asm" -o "$OUTDIR/move_tool.prg" >/dev/null
    tail -c +3 "$OUTDIR/move_tool.prg" > "$MOVE"
    tmpx -i "$ROOT/copy_tool.asm" -o "$OUTDIR/copy_tool.prg" >/dev/null
    tail -c +3 "$OUTDIR/copy_tool.prg" > "$COPY"
    tmpx -i "$ROOT/convert_tool.asm" -o "$OUTDIR/convert_tool.prg" >/dev/null
    tail -c +3 "$OUTDIR/convert_tool.prg" > "$CONVERT"
    python3 "$ROOT/tools/build_docs.py" --pack "$OUTDIR/docs.bin" >/dev/null
    DOCS_ARGS="--pager $PAGER --index $OUTDIR/docs.idx --data $OUTDIR/docs.dat --handler $HANDLER --renum $RENUM --move $MOVE --copy $COPY --convert $CONVERT --menu $MENUBODY"
    echo "Built docs: index+data + pager $(wc -c <"$PAGER") B + menu $(wc -c <"$HANDLER") B + menu-body $(wc -c <"$MENUBODY") B + tools R/M/C/F7 $(wc -c <"$RENUM")/$(wc -c <"$MOVE")/$(wc -c <"$COPY")/$(wc -c <"$CONVERT") B"
else
    echo "Skipping docs: mdbasic.pdf or pdftotext not available"
fi

# 5. Magic Desk cartridge (with docs banks if built). Regenerate the loader stub
#    from boot.asm so it stays in sync (it installs the RESTORE docs handler when
#    docs banks are present; behaves as the plain loader otherwise).
tmpx -i "$ROOT/boot.asm" -o "$OUTDIR/cart_boot.prg" >/dev/null
tail -c +3 "$OUTDIR/cart_boot.prg" > "$ROOT/tools/cart_boot.bin"
# shellcheck disable=SC2086
python3 "$ROOT/tools/make_crt.py" "$PRG" "$CRT" $DOCS_ARGS >/dev/null

echo "Built PRG:  $PRG"
echo "Built disk: $DISK"
echo "Built disk: $DISK81"
echo "Built cart: $CRT"
