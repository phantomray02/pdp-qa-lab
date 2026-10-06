"""Unit tests for pure helper functions in streamlit_app.py.

Functions are loaded via tests/conftest.py (AST extraction), so these run
without importing Streamlit.
"""
import pytest

from tests.app_loader import load_functions

_fns = load_functions(
    "normalize_space",
    "clean_item_number",
    "normalize_text",
    "dedupe_preserve_order",
    "keyword_score",
    "description_similarity_score",
    "html_escape_text",
)
normalize_space = _fns["normalize_space"]
clean_item_number = _fns["clean_item_number"]
normalize_text = _fns["normalize_text"]
dedupe_preserve_order = _fns["dedupe_preserve_order"]
keyword_score = _fns["keyword_score"]
description_similarity_score = _fns["description_similarity_score"]
html_escape_text = _fns["html_escape_text"]


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("  hello   world \n", "hello world"),
        ("a&nbsp;b", "a b"),
        ("", ""),
        (None, ""),
        ("no-extra-space", "no-extra-space"),
    ],
)
def test_normalize_space(raw, expected):
    assert normalize_space(raw) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("123.0", "123"),
        ("970097278", "970097278"),
        ("", ""),
        (None, ""),
    ],
)
def test_clean_item_number(raw, expected):
    assert clean_item_number(raw) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Cottonelle Ultra-Clean!", "cottonelle ultraclean"),
        ("ABC 123", "abc 123"),
        ("", ""),
        (None, ""),
        (123, ""),
    ],
)
def test_normalize_text(raw, expected):
    assert normalize_text(raw) == expected


def test_dedupe_preserve_order():
    assert dedupe_preserve_order(["  a ", "a", "b", "", "b "]) == ["a", "b"]
    assert dedupe_preserve_order([]) == []


def test_keyword_score_identical_is_100():
    assert keyword_score("Cottonelle Ultra Clean", "cottonelle ultra clean") == 100


def test_keyword_score_empty_is_0():
    assert keyword_score("", "") == 0
    assert keyword_score("abc", "") == 0
    assert keyword_score("", "abc") == 0


def test_keyword_score_partial():
    # SequenceMatcher("abc", "abd"): 2*2/(3+3) = 0.667 -> int -> 66
    assert keyword_score("abc", "abd") == 66


def test_description_similarity_score_mirrors_keyword():
    assert description_similarity_score("same text", "same text") == 100
    assert description_similarity_score("", "x") == 0


def test_html_escape_text():
    assert html_escape_text("<b>hi</b>") == "&lt;b&gt;hi&lt;/b&gt;"
    assert html_escape_text("") == ""
