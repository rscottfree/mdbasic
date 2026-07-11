#!/bin/sh
# Write a copy of mdbasic.asm with the version banner stamped to the current
# date (YY.MM.DD) and print the path of the stamped temp file. The caller
# assembles the temp file and removes it afterwards, so the tracked source is
# left untouched.
#
#   tmp=$(tools/stamp_version.sh path/to/mdbasic.asm)
#   tmpx ... -i "$tmp" ... ; rm -f "$tmp"
#
# The date can be overridden for reproducible builds:
#   MDBASIC_VERSION_DATE=26.06.17 tools/stamp_version.sh ...

set -eu

SRC="$1"
DATE="${MDBASIC_VERSION_DATE:-$(date +%y.%m.%d)}"

case "$DATE" in
    [0-9][0-9].[0-9][0-9].[0-9][0-9]) ;;
    *)
        echo "ERROR: version date must be YY.MM.DD, got: $DATE" >&2
        exit 1
        ;;
esac

# Keep a real .asm filename (some toolchains key off the extension) by placing
# it inside a uniquely named temp dir. mktemp only substitutes trailing X's.
TMPD=$(mktemp -d "${TMPDIR:-/tmp}/mdbasic.XXXXXX")
TMP="$TMPD/mdbasic.asm"

# Replace only the banner date: .text "mdbasic NN.NN.NN"
sed -E "s/(\.text \"mdbasic )[0-9]{2}\.[0-9]{2}\.[0-9]{2}(\")/\1${DATE}\2/" \
    "$SRC" > "$TMP"

# Guard against the banner being renamed/reformatted out from under us.
if ! grep -q "\"mdbasic ${DATE}\"" "$TMP"; then
    rm -f "$TMP"
    echo "ERROR: could not stamp version banner in $SRC" >&2
    exit 1
fi

echo "$TMP"
