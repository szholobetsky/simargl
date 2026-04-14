"""Tests for simargl searcher — requires a pre-built index."""
import pytest
from simargl.indexer import index_units
from simargl.searcher import search


@pytest.fixture
def built_index(mock_embedder, tiny_db, tmp_path):
    index_units(str(tiny_db), project_id="test",
                store_dir=str(tmp_path), backend_type="numpy")
    return tmp_path


def test_search_returns_structure(built_index):
    result = search("login authentication",
                    mode="task", project_id="test",
                    store_dir=str(built_index), backend_type="numpy")
    assert "files" in result
    assert "modules" in result
    assert "units" in result


def test_search_file_mode(built_index):
    result = search("user endpoint",
                    mode="task", project_id="test",
                    store_dir=str(built_index), backend_type="numpy")
    assert isinstance(result["files"], list)


def test_search_returns_scores(built_index):
    result = search("login",
                    mode="task", project_id="test",
                    store_dir=str(built_index), backend_type="numpy")
    for f in result["files"]:
        assert "score" in f
        assert "path" in f
        assert 0.0 <= f["score"] <= 1.0


def test_search_top_n_respected(built_index):
    result = search("login", mode="task", top_n=1,
                    project_id="test", store_dir=str(built_index),
                    backend_type="numpy")
    assert len(result["files"]) <= 1


def test_search_invalid_mode(built_index):
    with pytest.raises(ValueError):
        search("login", mode="invalid",
               project_id="test", store_dir=str(built_index),
               backend_type="numpy")
