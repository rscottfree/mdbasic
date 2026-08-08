#!/bin/sh
# Build and run the MDBASIC sprite MOVE timing test on an Ultimate 64.

set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)   # the utilities/ dir
REPO=$(cd "$ROOT/.." && pwd)             # repo root (pristine mdbasic.asm)
WORK="${TMPDIR:-/tmp}/mdbasic-sprite-u64"
U64="${U64:-$HOME/.local/bin/u64}"

mkdir -p "$WORK"

[ -x "$U64" ] || {
    echo "ERROR: u64 CLI not found at $U64" >&2
    exit 1
}

for tool in tmpx c1541 python3; do
    command -v "$tool" >/dev/null 2>&1 || {
        echo "ERROR: required tool not found: $tool" >&2
        exit 1
    }
done

hex_bytes_for_text() {
    python3 - "$1" <<'PY'
import sys
text = sys.argv[1].replace("\\n", "\r").upper()
print(" ".join(f"{ord(ch):02X}" for ch in text))
PY
}

u64_type() {
    bytes=$(hex_bytes_for_text "$1")
    for b in $bytes; do
        "$U64" update keyboard -b "$b" -s >/dev/null
        "$U64" update memory -a 00C6 -b 01 -s >/dev/null
        sleep 0.25
    done
}

u64_mem() {
    "$U64" read memory -a "$1" -l "$2" |
        python3 -c 'import json,sys; print(json.load(sys.stdin)["result"]["body"]["content"])'
}

wait_results() {
    deadline=$(( $(date +%s) + 90 ))
    while [ "$(date +%s)" -lt "$deadline" ]; do
        value=$(u64_mem C080 11)
        case "$value" in
            *ff) echo "$value"; return 0 ;;
            *) ;;
        esac
        sleep 1
    done
    echo "ERROR: timed out waiting for timing results at \$C080" >&2
    return 1
}

run_case() {
    label="$1"
    turbo="$2"

    echo "== $label =="
    "$U64" signal machine -t reset -s >/dev/null
    sleep 5
    "$U64" update memory -a D030 -b "$turbo" -s >/dev/null
    "$U64" update memory -a C080 -b 0000000000000000000000 -s >/dev/null

    u64_type 'LOAD"MDBASIC",8,1\n'
    sleep 5
    u64_type 'SYS64738\n'
    sleep 5
    u64_type 'LOAD"SPRTIME",8\n'
    sleep 2
    u64_type 'RUN\n'

    result=$(wait_results)
    echo "result=$result"
    python3 - "$label" "$result" <<'PY'
import sys

label, raw = sys.argv[1], bytes.fromhex(sys.argv[2])
if len(raw) != 11 or raw[-1] != 0xff:
    raise SystemExit(f"ERROR: unexpected {label} result bytes: {raw.hex()}")
got = [raw[i] | raw[i + 1] << 8 for i in range(0, 10, 2)]
want = [5, 86, 173, 259, 344]
if any(abs(a - b) > 2 for a, b in zip(got, want)):
    raise SystemExit(f"ERROR: {label} timings {got}, expected about {want}")
print(f"timings={got}")
PY
}

cd "$ROOT"

tmpx -l "$WORK/mdbasic.lst" -i "$REPO/mdbasic.asm" -o "$WORK/mdbasic.prg" >/dev/null
tools/c64_basic_prg.py --dialect mdbasic tests/sprite_timing.bas "$WORK/sprtime.prg"
rm -f "$WORK/sprtime.d64"
c1541 -format "sprtime,st" d64 "$WORK/sprtime.d64" \
    -write "$WORK/sprtime.prg" sprtime \
    -write "$WORK/mdbasic.prg" mdbasic >/dev/null

"$U64" create mount -t local -p "$WORK/sprtime.d64" -d a -s >/dev/null

run_case "normal" 00
run_case "turbo" ff

"$U64" update memory -a D030 -b 00 -s >/dev/null
echo "PASS"
