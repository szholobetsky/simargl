"""Searcher: search() with mode=task/file/aggr, sort=rank/freq.

Mode aliases (both accepted):
  file  | files       — direct cosine search in file chunks
  task  | tasks       — similar units → file mapping (rank or freq sort)
  aggr  | aggregated  — average top-k unit vectors → cosine search in file chunks
"""
from __future__ import annotations

from collections import Counter, defaultdict

import numpy as np

from .config import DEFAULT_MODEL, DEFAULT_TOP_K, DEFAULT_TOP_N, DEFAULT_TOP_M, STORE_DIR
from .embedder import get_embedder
from .backends import make_backend
from .utils import module_from_path

# accept short and long names
_MODE_ALIASES = {
    "file": "file", "files": "file",
    "task": "task", "tasks": "task",
    "aggr": "aggr", "aggregated": "aggr",
}


def search(
    query: str,
    mode: str = "task",    # file | task | aggr
    sort: str = "rank",    # rank | freq  (task mode only)
    top_n: int = DEFAULT_TOP_N,
    top_k: int = DEFAULT_TOP_K,
    top_m: int = DEFAULT_TOP_M,
    include_diff: bool = False,
    project_id: str = "default",
    store_dir: str = STORE_DIR,
    backend_type: str = "numpy",
    db_url: str | None = None,
) -> dict:
    """Search the index.

    Returns:
    {
      "files":   [{"path": ..., "score": ..., "module": ...}],
      "modules": [{"module": ..., "score": ...}],
      "units":   [{"unit_id": ..., "unit_type": ..., "text_preview": ...,
                   "similarity": ..., "files": [...], "diff": "..."}],
      "mode": ..., "sort": ...
    }
    """
    mode = _MODE_ALIASES.get(mode)
    if mode is None:
        raise ValueError(f"Unknown mode. Use: file, task, aggr")

    backend = make_backend(backend_type, store_dir=store_dir,
                           project_id=project_id, db_url=db_url)

    # Load and validate meta BEFORE touching the embedder — fail fast on wrong path/project_id.
    meta = backend.load_meta()
    model_key = meta.get("model_key", DEFAULT_MODEL)
    dim = meta.get("dim")
    if not dim:
        raise ValueError(f"Index at {store_dir}/{project_id} has no dim — re-run index.")

    # Check the relevant index file exists and is non-empty.
    from pathlib import Path
    if mode in ("file", "aggr"):
        idx = Path(store_dir) / project_id / "files.int8"
    else:
        idx = Path(store_dir) / project_id / "units.int8"
    if not idx.exists() or idx.stat().st_size == 0:
        raise FileNotFoundError(
            f"Index file not found or empty: {idx}\n"
            f"Run: simargl index {'files <path>' if mode in ('file','aggr') else 'units <db>'}"
            f"  --project {project_id}"
        )

    embedder = get_embedder(model_key)
    query_vec = embedder.encode([query])[0]  # (dim,) float32

    if mode == "file":
        return _search_file(backend, query_vec, dim, top_n, top_m)
    if mode == "task":
        return _search_task(backend, query_vec, dim, top_n, top_k, top_m, sort, include_diff, meta)
    if mode == "aggr":
        return _search_aggr(backend, query_vec, dim, top_n, top_k, top_m, include_diff, meta)


# ------------------------------------------------------------------ file mode
def _search_file(backend, query_vec, dim, top_n, top_m) -> dict:
    results = backend.search_files(query_vec, dim, top_n=top_n * 2)
    # deduplicate by path, keep max score
    seen: dict[str, float] = {}
    for r in results:
        p = r["path"]
        if p not in seen or r["score"] > seen[p]:
            seen[p] = r["score"]

    files = sorted(
        [{"path": p, "score": s, "module": module_from_path(p)} for p, s in seen.items()],
        key=lambda x: x["score"], reverse=True,
    )[:top_n]

    return {"files": files, "modules": _aggregate_modules(files, top_m),
            "units": [], "mode": "file", "sort": None}


# ------------------------------------------------------------------ task mode
def _search_task(backend, query_vec, dim, top_n, top_k, top_m, sort, include_diff, meta) -> dict:
    unit_hits = backend.search_units(query_vec, dim, top_k=top_k)

    if sort == "rank":
        file_scores: dict[str, float] = {}
        for hit in unit_hits:
            for uf in backend.get_unit_files(hit["unit_id"]):
                fp = uf["file_path"]
                file_scores[fp] = max(file_scores.get(fp, 0.0), hit["score"])
    else:  # freq
        freq: Counter = Counter()
        for hit in unit_hits:
            for uf in backend.get_unit_files(hit["unit_id"]):
                freq[uf["file_path"]] += 1
        file_scores = {fp: float(cnt) for fp, cnt in freq.items()}

    files = sorted(
        [{"path": p, "score": s, "module": module_from_path(p)} for p, s in file_scores.items()],
        key=lambda x: x["score"], reverse=True,
    )[:top_n]

    units = _build_units(unit_hits, backend, include_diff, meta)
    return {"files": files, "modules": _aggregate_modules(files, top_m),
            "units": units, "mode": "task", "sort": sort}


# ------------------------------------------------------------------ aggr mode
def _search_aggr(backend, query_vec, dim, top_n, top_k, top_m, include_diff, meta) -> dict:
    """Average top-k unit vectors → use centroid to search file chunks directly."""
    unit_hits = backend.search_units(query_vec, dim, top_k=top_k)
    if not unit_hits:
        return {"files": [], "modules": [], "units": [],
                "mode": "aggr", "sort": None}

    db_ids = [h["db_id"] for h in unit_hits]
    unit_vecs = backend.get_unit_vectors_by_ids(db_ids, dim)  # (K, dim) float32

    # weighted average: weight by similarity score
    weights = np.array([h["score"] for h in unit_hits[:len(unit_vecs)]], dtype=np.float32)
    weights /= weights.sum() + 1e-9
    centroid = (unit_vecs * weights[:, None]).sum(axis=0)
    norm = np.linalg.norm(centroid)
    centroid /= norm if norm > 0 else 1.0

    results = backend.search_files(centroid, dim, top_n=top_n * 2)
    seen: dict[str, float] = {}
    for r in results:
        p = r["path"]
        if p not in seen or r["score"] > seen[p]:
            seen[p] = r["score"]

    files = sorted(
        [{"path": p, "score": s, "module": module_from_path(p)} for p, s in seen.items()],
        key=lambda x: x["score"], reverse=True,
    )[:top_n]

    units = _build_units(unit_hits, backend, include_diff, meta)
    return {"files": files, "modules": _aggregate_modules(files, top_m),
            "units": units, "mode": "aggr", "sort": None}


# ------------------------------------------------------------------ helpers
def _aggregate_modules(files: list[dict], top_m: int) -> list[dict]:
    mod_score: dict[str, float] = defaultdict(float)
    for f in files:
        m = f["module"]
        mod_score[m] = max(mod_score[m], f["score"])
    return sorted(
        [{"module": m, "score": s} for m, s in mod_score.items()],
        key=lambda x: x["score"], reverse=True,
    )[:top_m]


def _build_units(unit_hits, backend, include_diff, meta) -> list[dict]:
    units = []
    for hit in unit_hits:
        uf_list = backend.get_unit_files(hit["unit_id"])
        entry = {
            "unit_id":      hit["unit_id"],
            "unit_type":    hit["unit_type"],
            "text_preview": hit["text_preview"],
            "similarity":   hit["score"],
            "files":        [uf["file_path"] for uf in uf_list],
        }
        if include_diff:
            entry["diff"] = _fetch_diff(hit, uf_list, meta)
        units.append(entry)
    return units


def _fetch_diff(hit: dict, uf_list: list[dict], meta: dict) -> str:
    import sqlite3
    diffs = []
    unit_mode = meta.get("unit_mode", "tasks")
    for uf in uf_list[:3]:
        db_path = uf.get("db_path") or meta.get("db_path", "")
        if not db_path:
            continue
        try:
            conn = sqlite3.connect(db_path)
            if unit_mode == "tasks":
                row = conn.execute(
                    "SELECT DIFF FROM COMMITS WHERE TASK_NAME=? AND PATH=?",
                    (hit["unit_id"], uf["file_path"]),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT DIFF FROM COMMITS WHERE SHA=? AND PATH=?",
                    (hit["unit_id"], uf["file_path"]),
                ).fetchone()
            conn.close()
            if row and row[0]:
                diffs.append(f"--- {uf['file_path']}\n{row[0]}")
        except Exception:
            pass
    return "\n\n".join(diffs)
