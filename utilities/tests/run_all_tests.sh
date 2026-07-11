#!/bin/sh
# Run the VICE regression suite. All test scripts live alongside this one in
# utilities/tests/; cd here so they resolve regardless of the caller's cwd.
cd "$(dirname "$0")"

cleanup() {
  python3 cleanup_test_vice.py >/dev/null 2>&1 || true
}

trap cleanup EXIT INT TERM

for f in vice_renum_test.py vice_docs_test.py vice_docs_nav_test.py \
         vice_docs_clobber_test.py vice_docs_cursor_test.py \
         vice_pack_test.py vice_pack_list_test.py; do
  python3 "$f" || echo "FAILED: $f"
  cleanup
done
