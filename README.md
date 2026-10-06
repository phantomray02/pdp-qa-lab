# PDP QA Lab

Experimental / test-bed version of the PDP brand-compliance QA tooling.
The production build lives outside this repo — break things here freely.

## What this is

Two tools that work as a pipeline:

1. **`extension/`** — "PDP Compact HTML Finder" browser extension (v5.2.9).
   Captures live retailer product pages into compact TXT batches.
   Load unpacked in Edge/Chrome to test.
2. **`streamlit_app.py`** — the QA app. Compares Salsify source content against
   the captured live PDPs (title, description, features, images) and produces
   Excel + visual HTML compliance reports. One retailer at a time.

## Run the app locally

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Deploy to Streamlit Community Cloud (test)

1. Push this repo to GitHub (private).
2. Go to https://share.streamlit.io → "New app" → pick this repo.
3. Entrypoint: `streamlit_app.py`. That's it — requirements install automatically.

## Run the tests

```bash
pip install -r requirements.txt
pytest tests/ -v
```

See `tests/fixtures/README.md` for how to add golden-file fixtures from real
captures. Regenerate goldens after an intentional parser change with:

```bash
UPDATE_GOLDENS=1 pytest tests/test_parser_goldens.py
```

## Layout

```
streamlit_app.py      # the QA app (Streamlit entrypoint)
requirements.txt
extension/            # browser extension source
data/                 # sample SKU/retailer input CSV
docs/                 # code-review recommendations
tests/
  conftest.py         # AST-based function loader (no Streamlit import needed)
  test_helpers.py     # unit tests for pure helpers
  test_parser_goldens.py
  fixtures/           # golden-file cases per retailer
```

## Roadmap (from code review)

`docs/recommendations.md` has the full 20/10 list. The headline items:

1. Golden-file parser tests (this repo's `tests/` is the start)
2. Parse-confidence signals — never confuse "parser found nothing" with "retailer has nothing"
3. Retailer plugin architecture
4. Versioned capture format between extension and app
5. Month-over-month diff reporting
