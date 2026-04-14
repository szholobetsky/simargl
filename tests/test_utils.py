"""Tests for simargl.utils — pure functions, no model required."""
import pytest
from simargl.utils import (
    preprocess_text, combine_fields, norm_path, module_from_path, chunk_text
)


def test_preprocess_text_string():
    assert preprocess_text("  hello  ") == "hello"


def test_preprocess_text_none():
    assert preprocess_text(None) == ""


def test_preprocess_text_nan():
    import math
    assert preprocess_text(float("nan")) == ""


def test_combine_fields_basic():
    row = {"title": "Fix bug", "description": "Login fails"}
    result = combine_fields(row, ["title", "description"])
    assert "Fix bug" in result
    assert "Login fails" in result


def test_combine_fields_missing_key():
    result = combine_fields({"title": "X"}, ["title", "missing"])
    assert result == "X"


def test_combine_fields_all_empty():
    result = combine_fields({}, ["a", "b"])
    assert result == "empty"


def test_norm_path_backslash():
    assert norm_path("auth\\login.py") == "auth/login.py"


def test_norm_path_empty():
    assert norm_path("") == "unknown"


def test_module_from_path_nested():
    assert module_from_path("auth/login.py") == "auth"


def test_module_from_path_root():
    assert module_from_path("main.py") == "root"


def test_chunk_text_splits():
    text = " ".join(["word"] * 500)
    chunks = chunk_text(text, chunk_size=100, overlap=10)
    assert len(chunks) > 1
    assert all(len(c.split()) <= 100 for c in chunks)


def test_chunk_text_empty():
    assert chunk_text("") == []


def test_chunk_text_short_text():
    chunks = chunk_text("hello world", chunk_size=100)
    assert chunks == ["hello world"]
