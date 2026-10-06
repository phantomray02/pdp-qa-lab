"""Golden-file regression tests for retailer text extractors.

Fixture layout:
    tests/fixtures/<retailer>/<case_name>/
        capture.txt    # raw HTML saved from the extension (trimmed is fine)
        expected.json  # expected parser output (title/description/features/debug)
        meta.json      # optional: {"retail_url": ..., "target_rpc": ...}

Each extractor is loaded from streamlit_app.py via tests/conftest.py
(transitive callees included), so no Streamlit import is needed.

Add a fixture: save a capture, then run
    UPDATE_GOLDENS=1 pytest tests/test_parser_goldens.py
and HAND-REVIEW the generated expected.json before committing it.
Goldens are only as trustworthy as that review.

Parser registry: retailer dir name -> extractor function name.
"""
import json
import os
import pathlib

import pytest

from tests.app_loader import load_functions

FIXTURES = pathlib.Path(__file__).parent / "fixtures"

REGISTRY = {
    "cvs": "_extract_cvs_text_from_html",
    "kroger": "extract_kroger_text_from_html",
    "walgreens": "extract_walgreens_text_from_html",
    "heb": "extract_heb_text_from_html",
    "sams": "extract_sams_text_from_html",
    "albertsons": "extract_albertsons_text_from_html",
}

_fns = load_functions(*sorted(set(REGISTRY.values())))


def _cases():
    out = []
    if not FIXTURES.exists():
        return out
    for retailer_dir in sorted(FIXTURES.iterdir()):
        if not retailer_dir.is_dir() or retailer_dir.name.startswith("_"):
            continue
        for case_dir in sorted(retailer_dir.iterdir()):
            capture = case_dir / "capture.txt"
            if case_dir.is_dir() and capture.exists():
                out.append(pytest.param(retailer_dir.name, case_dir.name,
                                       id=f"{retailer_dir.name}/{case_dir.name}"))
    return out


def _read_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


@pytest.mark.parametrize("retailer,case", _cases())
def test_golden(retailer, case, tmp_path):
    if retailer not in REGISTRY:
        pytest.skip(f"no parser registered for retailer {retailer!r}")
    case_dir = FIXTURES / retailer / case
    html_text = (case_dir / "capture.txt").read_text(encoding="utf-8")
    meta_path = case_dir / "meta.json"
    meta = _read_json(meta_path) if meta_path.exists() else {}
    parser = _fns[REGISTRY[retailer]]
    result = parser(
        html_text,
        retail_url=meta.get("retail_url", ""),
        target_rpc=meta.get("target_rpc", ""),
    )
    expected_path = case_dir / "expected.json"
    if os.environ.get("UPDATE_GOLDENS") == "1":
        expected_path.write_text(
            json.dumps(result, indent=2, sort_keys=True, default=str)
            + "\n",
            encoding="utf-8",
        )
        pytest.skip("golden regenerated — review expected.json, then re-run")
    assert expected_path.exists(), (
        f"missing expected.json for {retailer}/{case}; "
        "run with UPDATE_GOLDENS=1 to generate, then hand-review it"
    )
    expected = _read_json(expected_path)
    actual = json.loads(json.dumps(result, sort_keys=True, default=str))
    assert actual == expected, (
        f"parser output changed for {retailer}/{case}. "
        "If the change is intentional, re-run with UPDATE_GOLDENS=1 and review the diff."
    )


def test_registry_covers_known_extractors():
    # Guards against the registry drifting from the app's extractor names.
    from tests.app_loader import APP_PATH
    import ast

    tree = ast.parse(APP_PATH.read_text(encoding="utf-8"))
    defined = {
        n.name for n in tree.body if isinstance(n, ast.FunctionDef)
    }
    for retailer, fn in REGISTRY.items():
        assert fn in defined, f"registry points at missing function {fn} ({retailer})"
