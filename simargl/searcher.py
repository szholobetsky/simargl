"""Searcher: search() with mode=task/file/aggr/refine, sort=rank/freq.

Mode aliases (both accepted):
  file   | files       — direct cosine search in file chunks
  task   | tasks       — similar units → file mapping (rank or freq sort)
  aggr   | aggregated  — average top-k unit vectors → cosine search in file chunks
  refine              — pseudo-relevance feedback: expand query with terms from
                        top-k similar commits/tasks, then run file search
"""
from __future__ import annotations

import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from .config import DEFAULT_MODEL, DEFAULT_TOP_K, DEFAULT_TOP_N, DEFAULT_TOP_M, STORE_DIR
from .embedder import get_embedder
from .backends import make_backend
from .utils import module_from_path, chunk_text

# accept short and long names
_MODE_ALIASES = {
    "file": "file", "files": "file",
    "task": "task", "tasks": "task",
    "aggr": "aggr", "aggregated": "aggr",
    "refine": "refine",
}

# minimal stopwords — common English + common commit verbs
_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "up", "is", "it", "as", "be", "was", "are",
    "has", "have", "had", "that", "this", "not", "no", "via", "get", "set",
    "all", "its", "one", "now", "out", "if", "we", "use", "add", "fix",
    "make", "also", "into", "when", "will", "can", "do", "new", "so", "into",
}


def _tokenize(text: str) -> list[str]:
    """Split text into lowercase alpha tokens, filter stopwords and short tokens."""
    tokens = re.findall(r'[A-Za-z][A-Za-z0-9_]*', text)
    return [t.lower() for t in tokens if len(t) >= 3 and t.lower() not in _STOPWORDS]


def _refine_query(
    original_query: str,
    original_vec: np.ndarray,
    backend,
    dim: int,
    embedder,
    refine_top_k: int = 10,
    refine_top_m: int = 8,
    min_cosine: float = 0.6,
) -> tuple[str, np.ndarray]:
    """Pseudo-relevance feedback: expand query with terms from top-k similar units.

    1. Find top-k semantically similar commits/tasks using the original query vector.
    2. Tokenize their texts; collect terms absent from the original query.
    3. Add the top-M most frequent new terms to the query and re-embed.
    4. Safety check: if cosine(original, expanded) < min_cosine the expansion went
       in the wrong direction — fall back to original.

    Returns (expanded_query_text, expanded_query_vec).
    """
    unit_hits = backend.search_units(original_vec, dim, top_k=refine_top_k)
    if not unit_hits:
        return original_query, original_vec

    corpus_text = " ".join(h["text_preview"] for h in unit_hits)
    original_tokens = set(_tokenize(original_query))
    new_term_counts = Counter(
        t for t in _tokenize(corpus_text) if t not in original_tokens
    )
    if not new_term_counts:
        return original_query, original_vec

    expansion_terms = [t for t, _ in new_term_counts.most_common(refine_top_m)]
    expanded_query = original_query + " " + " ".join(expansion_terms)
    expanded_vec = embedder.encode([expanded_query])[0]

    # safety: don't expand if direction changes too much
    orig_n = np.linalg.norm(original_vec)
    exp_n  = np.linalg.norm(expanded_vec)
    cos = float(np.dot(original_vec, expanded_vec) / ((orig_n * exp_n) + 1e-9))
    if cos < min_cosine:
        return original_query, original_vec

    return expanded_query, expanded_vec


def search(
    query: str,
    mode: str = "task",    # file | task | aggr | refine
    sort: str = "rank",    # rank | freq  (task mode only)
    top_n: int = DEFAULT_TOP_N,
    top_k: int = DEFAULT_TOP_K,
    top_m: int = DEFAULT_TOP_M,
    include_diff: bool = False,
    exclude_blackholes: bool = False,
    coverage_penalty: float = 0.0,
    score_blend: float = 1.0,
    refine_top_k: int = 10,
    refine_top_m: int = 8,
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
        raise ValueError(f"Unknown mode. Use: file, task, aggr, refine")

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
    elif mode == "refine":
        idx = Path(store_dir) / project_id / "units.int8"
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
        return _search_file(backend, query_vec, dim, top_n, top_m, exclude_blackholes, coverage_penalty, score_blend)
    if mode == "task":
        return _search_task(backend, query_vec, dim, top_n, top_k, top_m, sort, include_diff, meta)
    if mode == "aggr":
        return _search_aggr(backend, query_vec, dim, top_n, top_k, top_m, include_diff, meta, exclude_blackholes, coverage_penalty, score_blend)
    if mode == "refine":
        return _search_refine(backend, query, query_vec, dim, embedder, top_n, top_m,
                              exclude_blackholes, coverage_penalty, score_blend,
                              refine_top_k, refine_top_m)


# ------------------------------------------------------------------ file mode
def _search_file(backend, query_vec, dim, top_n, top_m,
                 exclude_blackholes: bool = False,
                 coverage_penalty: float = 0.0,
                 score_blend: float = 1.0) -> dict:
    results = backend.search_files(query_vec, dim, top_n=top_n * 2,
                                   exclude_blackholes=exclude_blackholes,
                                   coverage_penalty=coverage_penalty,
                                   score_blend=score_blend)
    # keep the chunk_n of the best-scoring chunk per file — callers that need
    # the actual matched text (not just a ranking) use it via get_chunk_text().
    seen: dict[str, dict] = {}
    for r in results:
        p = r["path"]
        if p not in seen or r["score"] > seen[p]["score"]:
            seen[p] = {"score": r["score"], "chunk_n": r["chunk_n"]}

    files = sorted(
        [{"path": p, "score": v["score"], "chunk_n": v["chunk_n"], "module": module_from_path(p)}
         for p, v in seen.items()],
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
def _search_aggr(backend, query_vec, dim, top_n, top_k, top_m, include_diff, meta,
                 exclude_blackholes: bool = False,
                 coverage_penalty: float = 0.0,
                 score_blend: float = 1.0) -> dict:
    """Average top-k unit vectors → use centroid to search file chunks directly."""
    unit_hits = backend.search_units(query_vec, dim, top_k=top_k)
    if not unit_hits:
        return {"files": [], "modules": [], "units": [],
                "mode": "aggr", "sort": None}

    db_ids = [h["db_id"] for h in unit_hits]
    unit_vecs = backend.get_unit_vectors_by_ids(db_ids, dim)

    weights = np.array([h["score"] for h in unit_hits[:len(unit_vecs)]], dtype=np.float32)
    weights /= weights.sum() + 1e-9
    centroid = (unit_vecs * weights[:, None]).sum(axis=0)
    norm = np.linalg.norm(centroid)
    centroid /= norm if norm > 0 else 1.0

    results = backend.search_files(centroid, dim, top_n=top_n * 2,
                                   exclude_blackholes=exclude_blackholes,
                                   coverage_penalty=coverage_penalty,
                                   score_blend=score_blend)
    seen: dict[str, dict] = {}
    for r in results:
        p = r["path"]
        if p not in seen or r["score"] > seen[p]["score"]:
            seen[p] = {"score": r["score"], "chunk_n": r["chunk_n"]}

    files = sorted(
        [{"path": p, "score": v["score"], "chunk_n": v["chunk_n"], "module": module_from_path(p)}
         for p, v in seen.items()],
        key=lambda x: x["score"], reverse=True,
    )[:top_n]

    units = _build_units(unit_hits, backend, include_diff, meta)
    return {"files": files, "modules": _aggregate_modules(files, top_m),
            "units": units, "mode": "aggr", "sort": None}


# ------------------------------------------------------------------ refine mode
def _search_refine(backend, query, query_vec, dim, embedder, top_n, top_m,
                   exclude_blackholes, coverage_penalty, score_blend,
                   refine_top_k, refine_top_m) -> dict:
    """Pseudo-relevance feedback: expand query, then run file search."""
    expanded_query, expanded_vec = _refine_query(
        query, query_vec, backend, dim, embedder,
        refine_top_k=refine_top_k, refine_top_m=refine_top_m,
    )
    result = _search_file(backend, expanded_vec, dim, top_n, top_m,
                          exclude_blackholes, coverage_penalty, score_blend)
    result["mode"] = "refine"
    result["expanded_query"] = expanded_query
    result["refined"] = expanded_query != query
    return result


# ------------------------------------------------------------------ rrf

def _rrf_merge(ranked_lists: list[list[str]], k: int = 60) -> list[tuple[str, float]]:
    """Reciprocal Rank Fusion of multiple ranked file lists.

    score(file) = sum( 1/(k + rank_i) ) for each list i that contains the file.
    Files in multiple lists get multiple addends → rise automatically.
    Files in only one list stay but score lower.

    Path deduplication: if one path is a suffix of another (e.g. "cop/style/a.rb"
    vs "lib/cop/style/a.rb"), they are the same file indexed from different base
    directories. The longer path is used as canonical.
    """
    def _norm(p: str) -> str:
        return p.replace("\\", "/")

    all_paths = list({_norm(p) for ranked in ranked_lists for p in ranked})

    # map each path to its canonical (longest suffix-matching) version
    canonical: dict[str, str] = {}
    for p in all_paths:
        best = p
        for q in all_paths:
            if q != p and (q.endswith("/" + p) or p.endswith("/" + q)):
                best = q if len(q) > len(best) else best
        canonical[p] = best

    scores: dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, path in enumerate(ranked, start=1):
            canon = canonical.get(_norm(path), _norm(path))
            scores[canon] = scores.get(canon, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


def rrf_search(
    query: str,
    sources: str = "task:default,file:default",
    top_n: int = 5,
    k: int = 60,
    top_k: int = DEFAULT_TOP_K,
    sort: str = "freq",
    score_blend: float = 1.0,
    coverage_penalty: float = 0.0,
    store_dir: str = STORE_DIR,
    backend_type: str = "numpy",
    db_url: str | None = None,
) -> dict:
    """Multi-source search merged with Reciprocal Rank Fusion.

    sources: comma-separated "mode:project_id" pairs
      "task:default,file:jina"         — task (bge-small) + file (jina-code)
      "task:default,file:jina,aggr:default" — three-way merge

    Each pair runs an independent search. Results are merged by rank position —
    raw scores are discarded (cross-model safe: bge-small 0.7 ≠ jina 0.55).

    Returns:
      files   — RRF-ranked list with rrf_score
      modules — aggregated modules
      sources — per-source file lists and any errors
      k       — damping constant used
    """
    parsed = []
    for part in sources.split(","):
        part = part.strip()
        if ":" not in part:
            raise ValueError(
                f"Invalid source '{part}'. Expected format: mode:project_id  "
                f"e.g. task:default or file:jina"
            )
        mode, project_id = part.split(":", 1)
        parsed.append((mode.strip(), project_id.strip()))

    source_results = []
    for mode, project_id in parsed:
        try:
            result = search(
                query,
                mode=mode,
                sort=sort,
                top_n=top_k,
                top_k=top_k,
                score_blend=score_blend,
                coverage_penalty=coverage_penalty,
                project_id=project_id,
                store_dir=store_dir,
                backend_type=backend_type,
                db_url=db_url,
            )
            source_results.append({
                "mode": mode,
                "project_id": project_id,
                "files": result["files"],
            })
        except Exception as e:
            source_results.append({
                "mode": mode,
                "project_id": project_id,
                "files": [],
                "error": str(e),
            })

    ranked_lists = [[f["path"] for f in sr["files"]] for sr in source_results]
    merged = _rrf_merge(ranked_lists, k=k)

    files = [
        {"path": p, "score": round(s, 6), "module": module_from_path(p)}
        for p, s in merged[:top_n]
    ]
    return {
        "files": files,
        "modules": _aggregate_modules(files, DEFAULT_TOP_M),
        "sources": source_results,
        "k": k,
    }


# ------------------------------------------------------------------ retrieve

def retrieve(
    query: str,
    mode: str = "file",
    top_n: int = 5,
    include_diff: bool = False,
    exclude_blackholes: bool = False,
    coverage_penalty: float = 0.0,
    score_blend: float = 1.0,
    files_to_fetch: list[str] | None = None,
    project_id: str = "default",
    store_dir: str = STORE_DIR,
    backend_type: str = "numpy",
    db_url: str | None = None,
    source_dir: str | None = None,
) -> str:
    """Return formatted text ready to inject into LLM context.

    mode=file  — top-N chunk texts from indexed files
    mode=task  — full task text + changed files + optional diff
    mode=aggr  — step 1 (files_to_fetch=None): file list for review;
                 step 2 (files_to_fetch=[...]): file contents
    """
    mode = _MODE_ALIASES.get(mode)
    if mode is None:
        raise ValueError("Unknown mode. Use: file, task, aggr")

    backend = make_backend(backend_type, store_dir=store_dir,
                           project_id=project_id, db_url=db_url)
    meta = backend.load_meta()

    if mode == "aggr" and files_to_fetch:
        return _fetch_file_contents(files_to_fetch)

    model_key = meta.get("model_key", DEFAULT_MODEL)
    dim = meta.get("dim")
    if not dim:
        raise ValueError("Index has no dim — re-run index.")

    embedder = get_embedder(model_key)
    query_vec = embedder.encode([query])[0]

    if mode == "file":
        return _retrieve_file_chunks(backend, query_vec, dim, top_n, meta, exclude_blackholes, coverage_penalty, score_blend, source_dir=source_dir)
    if mode == "task":
        return _retrieve_task_texts(backend, query_vec, dim, top_n, include_diff, meta)
    if mode == "aggr":
        result = _search_aggr(backend, query_vec, dim, top_n, DEFAULT_TOP_K, DEFAULT_TOP_M,
                               False, meta, exclude_blackholes, coverage_penalty, score_blend)
        lines = ["Files matching query (review and select relevant ones):"]
        for f in result["files"]:
            lines.append(f"  {f['score']:.3f}  {f['path']}")
        lines.append('\nTo fetch content: simargl retrieve --mode aggr --files "a.py,b.py" "<query>"')
        return "\n".join(lines)


def _resolve_and_extract_chunk(path: str, chunk_n: int, chunk_size: int,
                               source_dir: str | None = None) -> tuple[str | None, int]:
    """Read `path` (trying source_dir as a fallback base), re-chunk it the same
    way indexing did, and return (chunk_text, total_chunks). (None, 0) if the
    file can't be found."""
    candidates = [Path(path)]
    if source_dir:
        candidates.append(Path(source_dir) / Path(path).name)
        candidates.append(Path(source_dir) / path)
    content = None
    for candidate in candidates:
        try:
            content = candidate.read_text(encoding="utf-8", errors="ignore")
            break
        except FileNotFoundError:
            continue
    if content is None:
        return None, 0
    chunks = chunk_text(content, chunk_size=chunk_size)
    text = chunks[chunk_n] if chunk_n < len(chunks) else content
    return text, len(chunks)


def get_chunk_text(path: str, chunk_n: int, project_id: str = "default",
                   store_dir: str = STORE_DIR, backend_type: str = "numpy",
                   db_url: str | None = None, source_dir: str | None = None) -> str:
    """Return the actual chunk text for a (path, chunk_n) pair from search()'s
    file results — the piece of the file that matched, not the file's head.

    Use together with search(mode="file"): each entry in result["files"] now
    carries "chunk_n"; pass it here to get real content for LLM context
    instead of naively reading the first N characters of the file.
    """
    backend = make_backend(backend_type, store_dir=store_dir,
                           project_id=project_id, db_url=db_url)
    meta = backend.load_meta()
    chunk_size = int(meta.get("chunk_size", 400))
    text, _total = _resolve_and_extract_chunk(path, chunk_n, chunk_size, source_dir=source_dir)
    return text or ""


def _retrieve_file_chunks(backend, query_vec, dim: int, top_n: int, meta: dict,
                          exclude_blackholes: bool = False,
                          coverage_penalty: float = 0.0,
                          score_blend: float = 1.0,
                          source_dir: str | None = None) -> str:
    chunk_size = int(meta.get("chunk_size", 400))
    hits = backend.search_files(query_vec, dim, top_n=top_n * 3,
                                exclude_blackholes=exclude_blackholes,
                                coverage_penalty=coverage_penalty,
                                score_blend=score_blend)

    seen: dict[str, dict] = {}
    for h in hits:
        p = h["path"]
        if p not in seen or h["score"] > seen[p]["score"]:
            seen[p] = h

    top_hits = sorted(seen.values(), key=lambda x: x["score"], reverse=True)[:top_n]

    parts = []
    for h in top_hits:
        text, total_chunks = _resolve_and_extract_chunk(
            h["path"], h["chunk_n"], chunk_size, source_dir=source_dir)
        if text is None:
            continue
        chunk_n = h["chunk_n"]
        parts.append(f"--- {h['path']}  (score: {h['score']:.3f}, chunk {chunk_n}/{total_chunks}) ---\n{text}")

    return "\n\n".join(parts) if parts else "No results."


def _retrieve_task_texts(backend, query_vec, dim: int, top_n: int,
                         include_diff: bool, meta: dict) -> str:
    db_path = meta.get("db_path", "")
    unit_hits = backend.search_units(query_vec, dim, top_k=top_n)

    parts = []
    for hit in unit_hits:
        unit_id = hit["unit_id"]

        full_text = hit["text_preview"]
        if db_path:
            try:
                conn = sqlite3.connect(db_path)
                row = conn.execute(
                    "SELECT TITLE, DESCRIPTION FROM TASKS WHERE NAME = ?", (unit_id,)
                ).fetchone()
                conn.close()
                if row:
                    full_text = "\n\n".join(p for p in [row[0] or "", row[1] or ""] if p).strip()
            except Exception:
                pass

        uf_list = backend.get_unit_files(unit_id)
        files = [uf["file_path"] for uf in uf_list]

        section = [f"--- {unit_id}  (score: {hit['score']:.3f}) ---", full_text]
        if files:
            section.append(f"\nChanged files: {', '.join(files[:10])}")
        if include_diff:
            diff = _fetch_diff(hit, uf_list, meta)
            if diff:
                section.append(f"\nDiff:\n{diff[:2000]}")

        parts.append("\n".join(section))

    return "\n\n".join(parts) if parts else "No results."


def _fetch_file_contents(files: list[str]) -> str:
    parts = []
    for path in files:
        try:
            content = Path(path).read_text(encoding="utf-8", errors="ignore")
            parts.append(f"--- {path} ---\n{content}")
        except FileNotFoundError:
            parts.append(f"--- {path} --- [NOT FOUND]")
    return "\n\n".join(parts)


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
