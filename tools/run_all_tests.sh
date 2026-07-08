for f in tools/vice_renum_test.py tools/vice_docs_test.py tools/vice_docs_nav_test.py \
         tools/vice_docs_clobber_test.py tools/vice_docs_cursor_test.py; do
  python3 "$f" || echo "FAILED: $f"
done
