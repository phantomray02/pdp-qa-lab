## PDP Compact HTML Finder v5.2.9

Anti-bot upgrade (this version):
- **Session breaks:** after every 20 items the worker pauses 60–180s (randomized,
  interruptible via Stop) so long batches look like human browsing sessions
  instead of one continuous 600-page run.
- **Human-like scrolling:** before each capture (~85% of the time) the worker
  scrolls down the PDP in steps and back to top, killing the
  "loaded but never interacted" fingerprint. Wrapped in try/catch so it can
  never break a capture.
- **Exponential backoff on denials:** the post-denial cooldown now doubles with
  each consecutive denial (45s → 90s → 180s → 360s for CVS/HEB, 30s base for
  others, capped at 10 min) instead of a flat range. Recovers fast from
  one-offs, backs off hard when the retailer is actually angry. The status
  line now shows the actual cooldown seconds.
- **Wider delay jitter:** per-item delays now have real ranges (e.g. CVS
  6–14s, default 4–8s) instead of near-fixed values.
- No changes to capture output format, blocked-page detection, or retry logic.

## PDP Compact HTML Finder v5.2.8

HEB-only bug fix (this version):
- **Fixed:** the extension had no detection for HEB's bot-challenge/"are you
  human" page ("We noticed something unusual," "You're browsing or clicking
  at a speed much faster than typical human speed," "Cookies are disabled in
  your web browser," "A browser plugin or blocker is preventing JavaScript
  from running," "You're using a VPN or privacy tool"). Because the old
  `blocked` regex only recognized phrases like "access denied" or "captcha,"
  a HEB challenge page was captured and recorded as a **successful** page —
  producing a QA report where that SKU's title/description/features/images
  were all blank, even though the item is genuinely live on HEB.
- **Now:** those HEB phrases are added to the `blocked` detection regex, so
  a HEB challenge page is recognized immediately. HEB is also added to the
  same retry/cooldown handling CVS, Kroger, and Meijer already use:
  - Up to 2 capture attempts per item (`isHEB()` added to `maxAttempts`).
  - A denial-cooldown of ~45–75s between consecutive blocked attempts,
    pausing after 3 consecutive blocks (same threshold as CVS/Meijer) so the
    item is retried fresh rather than recorded as a blank success.
- No changes to CVS, Kroger, Meijer, Sam's Club, or Walgreens capture logic
  beyond what v5.2.7 already shipped (CVS sibling-variant fix, retained here
  unchanged).

Prior CVS-only fix (v5.2.7), retained:
- `cvsExtractState()` now captures every sibling product variant on a shared
  CVS PDP URL (not just the one matching the row's RPC), so multiple SKUs
  sharing one CVS page are each matched correctly.

To load unpacked in Edge, extract the ZIP and select the inner folder
containing manifest.json. Start a new HEB capture batch to create a new TXT;
older TXT files captured before this fix may still contain blocked/blank HEB
pages recorded as successes — re-run the HEB batch with this updated
extension to pick up the retry logic.
