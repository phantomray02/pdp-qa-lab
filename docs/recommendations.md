# PDP QA Project — Code Review Recommendations
**Date:** 2026-10-06 · **Reviewed:** Streamlit app (15,660 lines, 365 functions) + PDP Compact HTML Finder extension v5.2.8

## Verdict up front
The core engineering is better than the file size suggests: per-row fault isolation (one bad SKU can't kill a batch), thread-local HTTP sessions, dhash image caching, and guarded report rebuilds are all solid. The debt is the usual kind for a tool that grew retailer-by-retailer. Nothing here is on fire — but item 1 below affects the *correctness of QA output itself*, so it leads.

---

## P0 — Correctness of QA output

### 1. Stop silently swallowing parse failures
~75 `except Exception` handlers, many bare `pass` (e.g. L1068, L1442–1445, L1504, L1603, L2159, L2173, L2257, L2445, L2554). For a **QA tool** this is the worst failure mode: a swallowed parse error produces a blank extract that looks identical to "retailer has no content." At minimum, append the exception to the row's debug dict. Start with the ~20 sites in the Salsify/retailer text extractors.

### 2. Verify Meijer end-to-end
The app has **zero** meijer-specific functions (walgreens 65, cvs 55, kroger 42, sams 24, heb 19, albertsons 7, meijer 0), yet the README claims Meijer support. Either Meijer rows are handled generically (fine — document it) or they silently produce empty bundles (bad, and related to #1). Run one Meijer SKU through and check.

---

## P1 — Performance

### 3. Don't use full HTML as a `@st.cache_data` key
`get_retailer_bundle` (L12084) and `get_visual_row_payload` (L13912) take `row_source_code` — the entire uploaded capture, potentially 100KB+ — as a cache-key argument. Every call hashes a huge string and the string is retained as key material (×1200 max_entries). Pass a sha256 digest instead. Cuts per-call hashing cost and cache memory substantially.

### 4. Actually use the `streamlit_fragment` you defined (L66)
It's stubbed with a fallback but never applied anywhere. Every batch triggers `st.rerun()` (5 call sites), re-executing all 15,660 lines top-to-bottom ~20× per 645-SKU file. It only works because the caches absorb the cost. Fragmenting just the progress/status block would cut rerun cost meaningfully.

### 5. Cap the 7 unbounded `@st.cache_data` getters
L5337, L8257, L9115, L10552, L10889, L11764, L12076 have no `max_entries`/TTL (their neighbors use 1200). They're cleared on new upload, so it's bounded per session — but a long multi-batch session accumulates. Add `max_entries=1200` for consistency.

### 6. Add a timeout to `future.result()` (L15188–15194)
`process_row` shouldn't raise (it's wrapped), but if a worker ever hangs on a network call the whole batch stalls with no per-row timeout at the future level.

---

## P2 — Maintainability

### 7. Delete ~650 lines of dead code
AST call-graph analysis found never-called helpers: `render_debugger_panel` (L4464), `resolve_debug_views` (L4400), `get_debug_views_for_url` (L2535), the `*_compact_capture_from_raw_html` builders (L2875, L3394), `merge_cvs_bundles_prefer_richer_copy` (L11875), `cvs_mirror_salsify_images_for_retailer_side`, `build_image_panel_html`, etc. The comment at L15119 ("debugger removed") confirms iterative deletion without cleanup. Pure win: faster imports, less confusion.

### 8. Merge the triplicated JSON decoder
`_decode_walgreens_json_string` (L9160), `_decode_sams_json_string` (L10932), and `decode_json_string_value` (L10608) are the same `json.loads(f'"{raw}"')` trick with minor variations. One helper in Generic Helpers.

### 9. Delete the duplicate `fetch_json_with_timeout` (L9235)
Identical to L2248 — it's shadowing, not extending.

### 10. Split the monolith (longer-term)
The file is already organized by `# ====` section banners into natural modules: config/constants, HTTP/fetch layer, one module per retailer parser (7), Salsify parsers, scoring, image pipeline, Excel export, Streamlit UI. A split into ~10 files would be mechanical. Do this when the next retailer is added, not before — don't refactor for its own sake mid-QA-cycle.

---

## Extension (background.js) notes

- **The `capture()` injected script is one giant string** (L24). It works, but it's undebuggable — no breakpoints, no stack traces that map to source. Keep a readable `capture.js` source file in the repo and build the string from it (even a simple template-literal import at pack time), so the next retailer fix doesn't require editing a minified blob.
- **IndexedDB name is stale**: `PDPCompactV524` doesn't match v5.2.8. Harmless, but rename on the next breaking change (or comment it) before someone "fixes" it and wipes users' resume state.
- **Retailer detection is string-matching** (`isCVS()` etc. on the retailer label from Streamlit). It works, but document the exact labels the Streamlit side sends — a "CVS pharmacy" vs "CVS" mismatch silently changes retry/cooldown behavior (1 attempt vs 2, different denial thresholds).
- **Worst-case batch time is worth surfacing**: 45s page-load timeout + 4–15s per-item delays × 645 SKUs. The popup shows counts but no ETA. A rough ETA ("~X min remaining") would help operators plan.
- `downloadError` builds a fake multipart body into a `.txt` — odd but functional; leave it.
- `getBatch()` scoring tabs for streamlit/localhost is clever and the `normalize()` payload-shape handling is good defensive coding. No changes needed.

## Security
Clean: no eval/exec/pickle/subprocess, no hardcoded secrets, all file I/O is in-memory BytesIO (no path traversal), and the 22 `unsafe_allow_html=True` uses are consistently paired with `html_escape_text` (51 call sites). Keep that discipline.

---

## Suggested order of attack
1. #1 (silent exceptions → debug logging) + #2 (Meijer check) — correctness first
2. #3 (cache-key hashing) + #4 (fragment) — perf
3. #7, #8, #9 — cleanup, can be one sitting
4. #10 + extension `capture.js` source split — next time you touch those areas anyway
