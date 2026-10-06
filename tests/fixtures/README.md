# tests/fixtures/

Golden-file cases for `test_parser_goldens.py`.

## Layout

```
fixtures/
  <retailer>/            # must match a key in REGISTRY (cvs, kroger, walgreens, heb, sams, albertsons)
    <case_name>/
      capture.txt        # raw HTML from the extension (trim to the relevant part if huge)
      expected.json      # expected parser output — generated, then HAND-REVIEWED
      meta.json          # optional: {"retail_url": "...", "target_rpc": "..."}
```

## Adding a case

1. Save a capture from the extension as `capture.txt` (trimming is fine —
   keep the product JSON-LD / state scripts and the visible product sections).
2. Run `UPDATE_GOLDENS=1 pytest tests/test_parser_goldens.py`.
3. **Read the generated `expected.json` carefully.** Fix anything wrong in the
   parser, not in the golden — the golden locks in *current* behavior.
4. Commit. Future parser changes that alter output will now fail loudly.

## Tips

- One case per interesting page shape: normal PDP, variant PDP, blocked page,
  missing-description page.
- Keep captures small (a few hundred KB max) so the repo stays lean.
- The `debug` paths in expected.json are the parse-confidence signals —
  they tell you *which* selector won, which is exactly what you want to
  regression-test.
