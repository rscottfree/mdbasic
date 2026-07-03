#!/bin/sh
# Build and run the MDBASIC sprite MOVE timing test on an Ultimate 64.

set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)
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
        value=$(u64_mem C000 3)
        case "$value" in
            000000|"") ;;
            *) echo "$value"; return 0 ;;
        esac
        sleep 1
    done
    echo "ERROR: timed out waiting for result bytes at \$C000" >&2
    return 1
}

run_case() {
    label="$1"
    turbo="$2"

    echo "== $label =="
    "$U64" signal machine -t reset -s >/dev/null
    sleep 5
    "$U64" update memory -a D030 -b "$turbo" -s >/dev/null
    "$U64" update memory -a C000 -b 000000 -s >/dev/null

    u64_type 'LOAD"MDBASIC",8,1\n'
    sleep 5
    u64_type 'SYS64738\n'
    sleep 5
    u64_type 'LOAD"SPRTIME",8\n'
    sleep 2
    u64_type 'RUN\n'

    result=$(wait_results)
    echo "result=$result"
    case "$result" in
        000c16|010c16|020c16|000b16|010b16|020b16|000c15|010c15|020c15|000d16|010d16|020d16|000c17|010c17|020c17)
            ;;
        *)
            echo "ERROR: unexpected $label result bytes: $result" >&2
            return 1
            ;;
    esac
}

cd "$ROOT"

tmpx -l "$WORK/mdbasic.lst" -i mdbasic.asm -o "$WORK/mdbasic.prg" >/dev/null
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
