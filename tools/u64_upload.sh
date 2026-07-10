#!/bin/sh
# Upload the freshly built MDBASIC images to the Ultimate 64's /Temp folder,
# overwriting any existing copies. If the U64 is not reachable on the network
# this exits quietly with success, so it is safe to chain after a build that may
# run while the hardware is off.
#
# Uploaded from the build dir (default tools/../build):
#   mdbasic.d64, mdbasic.d81, mdbasic.crt  ->  /Temp/<name>
#
# The machine address and key come from $HOME/.u64.yaml (see u64 --help). Set
# U64_BIN to override the path to the u64 CLI.
#
# Usage: u64_upload.sh [builddir]

set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)
BUILDDIR="${1:-$ROOT/build}"
REMOTE_DIR="/Temp"
U64="${U64_BIN:-$HOME/.local/bin/u64}"
FILES="mdbasic.d64 mdbasic.d81 mdbasic.crt mdbasic.prg packaged.d81"

command -v "$U64" >/dev/null 2>&1 || {
    echo "ERROR: u64 CLI not found: $U64" >&2
    exit 1
}

# Reachability probe. The U64 FTP control port answers within a few seconds when
# powered on; a connect timeout (or any failure) means "not reachable" -> bail
# out silently rather than erroring.
if ! "$U64" -s read folder -p "$REMOTE_DIR" >/dev/null 2>&1; then
    echo "U64 not reachable — skipping upload"
    exit 0
fi

rc=0
ok=0
fail=0
for name in $FILES; do
    local_path="$BUILDDIR/$name"
    remote_path="$REMOTE_DIR/$name"
    if [ ! -f "$local_path" ]; then
        echo "ERROR: missing local file: $local_path" >&2
        fail=$((fail + 1))
        rc=1
        continue
    fi
    # create upload refuses to overwrite, so delete any existing copy first
    # (a 550 "not found" on a fresh /Temp is expected and ignored).
    "$U64" -s delete file -p "$remote_path" >/dev/null 2>&1 || true
    if "$U64" -s create upload -r "$remote_path" -l "$local_path" >/dev/null 2>&1; then
        echo "OK: $name -> $remote_path"
        ok=$((ok + 1))
    else
        echo "FAILED: $name" >&2
        fail=$((fail + 1))
        rc=1
    fi
done
echo "$ok uploaded, $fail failed"
exit $rc
