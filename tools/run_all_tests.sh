cleanup() {
  python3 tools/cleanup_test_vice.py >/dev/null 2>&1 || true
}

trap cleanup EXIT INT TERM

for f in tools/vice_renum_test.py tools/vice_docs_test.py tools/vice_docs_nav_test.py \
         tools/vice_docs_clobber_test.py tools/vice_docs_cursor_test.py \
         tools/vice_pack_test.py; do
  python3 "$f" || echo "FAILED: $f"
  cleanup
done
