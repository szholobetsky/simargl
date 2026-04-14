"""Tests for simargl indexer — uses MockEmbedder, no GPU required."""
import pytest
from simargl.indexer import index_files, index_units


def test_index_units_returns_stats(mock_embedder, tiny_db, tmp_path):
    result = index_units(
        str(tiny_db),
        model_key="bge-small",
        project_id="test",
        store_dir=str(tmp_path),
        backend_type="numpy",
    )
    assert "units_indexed" in result
    assert result["units_indexed"] > 0


def test_index_units_mode_detected(mock_embedder, tiny_db, tmp_path):
    result = index_units(
        str(tiny_db),
        model_key="bge-small",
        project_id="test",
        store_dir=str(tmp_path),
        backend_type="numpy",
    )
    assert result["mode_used"] in ("tasks", "commits")


def test_index_files_returns_stats(mock_embedder, tiny_repo, tmp_path):
    result = index_files(
        str(tiny_repo),
        model_key="bge-small",
        project_id="test",
        store_dir=str(tmp_path),
        backend_type="numpy",
    )
    assert "files_new" in result
    assert result["files_new"] > 0
    assert result["chunks_added"] > 0


def test_index_files_incremental(mock_embedder, tiny_repo, tmp_path):
    """Second run should find no new files (mtime unchanged)."""
    index_files(str(tiny_repo), project_id="test",
                store_dir=str(tmp_path), backend_type="numpy")
    result2 = index_files(str(tiny_repo), project_id="test",
                          store_dir=str(tmp_path), backend_type="numpy")
    assert result2["files_new"] == 0
    assert result2["files_modified"] == 0


def test_index_units_missing_db(tmp_path):
    with pytest.raises(Exception):
        index_units(str(tmp_path / "nonexistent.db"),
                    project_id="test", store_dir=str(tmp_path))
