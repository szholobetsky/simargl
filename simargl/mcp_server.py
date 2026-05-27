"""MCP server — tools: find, rrf, retrieve, index_files, index_units, status, vacuum, embedding, distance.
              prompts: search_task, search_file, search_aggr, search_rrf, search_refine.

Stdio (local):
  simargl-mcp

HTTP/SSE (LAN — laptop, phone via Termux, any machine):
  simargl-mcp --http --port 8765 --host 0.0.0.0
  pip install -e ".[http]"   # adds uvicorn

Connect from 1bcoder / Claude Code / Cursor over LAN:
  /mcp connect simargl http://192.168.1.phone:8765/sse

Full standalone on Android (Termux):
  pkg install python ollama
  ollama pull nomic-embed-text
  pip install simargl
  simargl index units sonar.db --model ollama://nomic-embed-text
  simargl index files /path/to/repo --model ollama://nomic-embed-text
  simargl-mcp --http --port 8765
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from mcp.server.fastmcp import FastMCP

from .config import DEFAULT_MODEL, DEFAULT_TOP_K, DEFAULT_TOP_N, DEFAULT_TOP_M, STORE_DIR
from .indexer import index_files as _index_files, index_units as _index_units
from .searcher import search as _search, retrieve as _retrieve, rrf_search as _rrf_search
from .embedder import get_embedder
from .backends import make_backend

mcp = FastMCP("simargl")


def _resolve(store_dir: str, project_id: str) -> tuple[str, str]:
    """Apply global defaults if set at server startup.

    _PROJECT_ID is a default, not an override — if the caller passed an explicit
    project_id (anything other than "default"), that value takes precedence.
    """
    return (
        _STORE_DIR if _STORE_DIR != STORE_DIR or store_dir == STORE_DIR else store_dir,
        _PROJECT_ID if (_PROJECT_ID is not None and project_id == "default") else project_id,
    )

# Server-level backend config — set once via CLI args, used by all tools.
_BACKEND_TYPE: str = "numpy"
_DB_URL: str | None = None
_STORE_DIR: str = STORE_DIR
_PROJECT_ID: str | None = None  # None = use per-call value (default: "default")


@mcp.tool()
def find(
    query: str,
    mode: str = "task",
    sort: str = "rank",
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
) -> str:
    """Find files related to a query.

    mode=task   — embed query → similar tasks/commits → files changed in those units
    mode=file   — embed query → direct cosine search in file chunks
    mode=aggr   — average top-k unit vectors → centroid cosine search in file chunks
    mode=refine — pseudo-relevance feedback: find similar commits → extract their
                  most frequent terms → expand query → file search with expanded query.
                  Best for natural-language queries that don't use project vocabulary.
                  refine_top_k: how many commits to use for expansion (default 10)
                  refine_top_m: how many new terms to add to query (default 8)
    sort=rank   — file score = max similarity among matching tasks (task mode only)
    sort=freq   — file score = count of matching tasks that changed it (task mode only)

    score_blend — α in  adjusted = α*max_chunk + (1-α)*mean_chunk  (default 1.0 = off).
      Focused files (all chunks relevant) are unaffected.
      Broad documents (relnotes, changelogs) where only one chunk matches are pushed down.
      Typical range: 0.5-0.8. No pre-computation needed — works at query time.

    coverage_penalty — subtract λ*coverage from scores (0.0 = off).
      Run blackhole(method="coverage_float") first.
    """
    try:
        store_dir, project_id = _resolve(store_dir, project_id)
        result = _search(
            query, mode=mode, sort=sort,
            top_n=top_n, top_k=top_k, top_m=top_m,
            include_diff=include_diff,
            exclude_blackholes=exclude_blackholes,
            coverage_penalty=coverage_penalty,
            score_blend=score_blend,
            refine_top_k=refine_top_k,
            refine_top_m=refine_top_m,
            project_id=project_id, store_dir=store_dir,
            backend_type=_BACKEND_TYPE, db_url=_DB_URL,
        )
    except Exception as e:
        return f"ERROR: {e}"

    header = f"Query: {query}  mode={mode}"
    if mode == "task":
        header += f"  sort={sort}"
    if result.get("refined"):
        header += f"\nExpanded: {result['expanded_query']}"
    lines = [header, ""]
    lines.append(f"Files (top {top_n}):")
    for f in result["files"]:
        lines.append(f"  {f['score']:.3f}  {f['path']}  [{f['module']}]")

    if result["modules"]:
        lines += ["", f"Modules (top {top_m}):"]
        for m in result["modules"]:
            lines.append(f"  {m['score']:.3f}  {m['module']}")

    if result["units"]:
        lines += ["", "Similar units:"]
        for u in result["units"][:5]:
            lines.append(f"  [{u['similarity']:.3f}] {u['unit_id']} — {u['text_preview'][:80]}")
            if u.get("diff"):
                lines.append(f"    diff:\n{u['diff'][:400]}")

    return "\n".join(lines)


@mcp.tool()
def rrf(
    query: str,
    sources: str = "task:default,file:default",
    top_n: int = 5,
    k: int = 60,
    sort: str = "freq",
    score_blend: float = 1.0,
    store_dir: str = STORE_DIR,
) -> str:
    """Merge search results from multiple modes/projects using Reciprocal Rank Fusion.

    sources — comma-separated "mode:project_id" pairs:
      "task:default,file:jina"              task on bge-small index + file on jina index
      "task:default,file:jina,aggr:default" three-way merge

    RRF formula: score(file) = sum( 1/(k+rank_i) ) across all sources.
    Files found by multiple sources rise automatically.
    Files found by only one source stay in the list but rank lower.
    Raw scores are discarded — only rank position matters (cross-model safe).

    k=60  standard damping constant. Lower = top ranks dominate more strongly.
    sort  applies to task sources only: freq (file touched by many commits) or rank.
    """
    try:
        store_dir, _ = _resolve(store_dir, "default")
        result = _rrf_search(
            query,
            sources=sources,
            top_n=top_n,
            k=k,
            top_k=DEFAULT_TOP_K,
            sort=sort,
            score_blend=score_blend,
            store_dir=store_dir,
            backend_type=_BACKEND_TYPE,
            db_url=_DB_URL,
        )
    except Exception as e:
        return f"ERROR: {e}"

    lines = [f"Query: {query}", f"Sources: {sources}  k={k}", ""]
    for sr in result["sources"]:
        err = sr.get("error", "")
        status = f"ERROR: {err}" if err else f"{len(sr['files'])} candidates"
        lines.append(f"  [{sr['mode']}:{sr['project_id']}]  {status}")
    lines += ["", f"RRF top-{top_n}:"]
    for f in result["files"]:
        lines.append(f"  {f['score']:.6f}  {f['path']}  [{f['module']}]")
    if result["modules"]:
        lines += ["", "Modules:"]
        for m in result["modules"]:
            lines.append(f"  {m['module']}")
    return "\n".join(lines)


@mcp.tool()
def retrieve(
    query: str,
    mode: str = "file",
    top_n: int = 5,
    include_diff: bool = False,
    exclude_blackholes: bool = False,
    coverage_penalty: float = 0.0,
    score_blend: float = 1.0,
    files: str = "",
    project_id: str = "default",
    store_dir: str = STORE_DIR,
) -> str:
    """Retrieve text chunks ready for LLM context injection.

    mode=file  — top-N chunk texts from indexed files
    mode=task  — full task text + changed files + optional diff
    mode=aggr  — step 1 (files=""): ranked file list for review;
                 step 2 (files="a.py,b.py"): fetch content of selected files
    score_blend    — re-ranking by topic concentration (see find tool).
    coverage_penalty — re-ranking penalty for omnipresent files (see find tool).
    """
    try:
        store_dir, project_id = _resolve(store_dir, project_id)
        files_list = [f.strip() for f in files.split(",")] if files.strip() else None
        return _retrieve(
            query,
            mode=mode,
            top_n=top_n,
            include_diff=include_diff,
            exclude_blackholes=exclude_blackholes,
            coverage_penalty=coverage_penalty,
            score_blend=score_blend,
            files_to_fetch=files_list,
            project_id=project_id,
            store_dir=store_dir,
            backend_type=_BACKEND_TYPE,
            db_url=_DB_URL,
        )
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def index_files(
    path: str,
    model_key: str = DEFAULT_MODEL,
    project_id: str = "default",
    store_dir: str = STORE_DIR,
    chunk_size: int = 400,
) -> str:
    """Index code files at path. Stores vectors in .simargl/{project_id}/."""
    try:
        store_dir, project_id = _resolve(store_dir, project_id)
        result = _index_files(
            path, model_key=model_key, project_id=project_id,
            store_dir=store_dir, chunk_size=chunk_size,
            backend_type=_BACKEND_TYPE, db_url=_DB_URL,
        )
        return (
            f"New: {result['files_new']}  Modified: {result['files_modified']}  "
            f"Deleted: {result['files_deleted']}  Chunks: {result['chunks_added']}  "
            f"model={model_key}  project={project_id}"
        )
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def index_units(
    db_path: str,
    model_key: str = DEFAULT_MODEL,
    project_id: str = "default",
    store_dir: str = STORE_DIR,
    mode: str = "auto",
) -> str:
    """Index tasks or commits from SQLite (TASK + COMMIT tables).

    mode=auto    detect by TASK_NAME coverage in COMMIT table
    mode=tasks   embed TASK.TITLE + TASK.DESCRIPTION
    mode=commits embed COMMIT.MESSAGE grouped by SHA
    """
    try:
        store_dir, project_id = _resolve(store_dir, project_id)
        result = _index_units(
            db_path, model_key=model_key, project_id=project_id,
            store_dir=store_dir, mode=mode,
            backend_type=_BACKEND_TYPE, db_url=_DB_URL,
        )
        return (
            f"Indexed {result['units_indexed']} units  (mode={result['mode_used']})  "
            f"model={model_key}  project={project_id}"
        )
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def status(
    project_id: str = "default",
    store_dir: str = STORE_DIR,
) -> str:
    """Show index stats: file count, unit count, model, index date."""
    try:
        store_dir, project_id = _resolve(store_dir, project_id)
        backend = make_backend(_BACKEND_TYPE, store_dir=store_dir,
                               project_id=project_id, db_url=_DB_URL)
        s = backend.stats()
        return "\n".join([
            f"Project:  {project_id}",
            f"Backend:  {_BACKEND_TYPE}",
            f"Model:    {s.get('model_key', '?')}  dim={s.get('dim', '?')}",
            f"Files:    {s.get('files', 0)}  ({s.get('chunks', 0)} chunks"
            + (f", {s.get('deleted_chunks', 0)} deleted)" if s.get('deleted_chunks') else ")"),
            f"Units:    {s.get('units', 0)}  (mode={s.get('unit_mode', '?')})",
            f"Indexed:  {s.get('indexed_at', '?')}",
        ])
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def blackhole(
    threshold: float = 0.85,
    method: str = "centroid",
    n_queries: int = 100,
    top_k: int = 20,
    project_id: str = "default",
    store_dir: str = STORE_DIR,
    list_paths: bool = False,
) -> str:
    """Detect and mark blackhole files (semantic noise that matches all queries equally).

    method=centroid (default, fast):
      Marks files whose mean chunk similarity to the corpus centroid exceeds threshold.
      Good for files with uniformly generic language (logs, boilerplate).

    method=coverage (binary filter):
      Marks files that appear in top_k results for >= threshold fraction of specific queries.
      threshold is a fraction [0.0-1.0], e.g. 0.3 = appears in 30% of queries.
      Risk: may mark core project files that are genuinely central to all tasks.

    method=coverage_float (RECOMMENDED — re-ranking, no binary cutoff):
      Computes per-file coverage score [0..1] and stores it. Does NOT mark any file as
      blackhole. Use find/retrieve with coverage_penalty=0.2 to re-rank results.
      Noise files (relnotes, CHANGELOG) are pushed down; core files stay on top because
      their raw similarity exceeds the penalty on specific queries.

    Use list_paths=True to see which files are currently marked as binary blackholes.
    """
    try:
        store_dir, project_id = _resolve(store_dir, project_id)
        backend = make_backend(_BACKEND_TYPE, store_dir=store_dir,
                               project_id=project_id, db_url=_DB_URL)
        if list_paths:
            paths = sorted(backend.blackhole_paths())
            if not paths:
                return "No blackhole files marked. Run blackhole(method='centroid') or blackhole(method='coverage') first."
            return f"Blackhole files ({len(paths)}):\n" + "\n".join(f"  {p}" for p in paths)
        meta = backend.load_meta()
        if method == "coverage_float":
            result = backend.compute_file_coverage(
                meta["dim"], n_queries=n_queries, top_k=top_k
            )
            return (
                f"Coverage scores computed — project={project_id}\n"
                f"  Method      : coverage_float (re-ranking, no binary filter)\n"
                f"  Test queries: {result['n_queries']}\n"
                f"  Top-k       : {result['top_k']}\n"
                f"  Total paths : {result['total_paths']}\n"
                f"  Max coverage: {result['max_coverage']:.4f}\n"
                f"\nNow use find/retrieve with coverage_penalty=0.2 (or adjust) to re-rank.\n"
                f"Higher penalty = stronger push-down of omnipresent files."
            )
        elif method == "coverage":
            thr = threshold if threshold is not None else 0.3
            result = backend.compute_blackholes_coverage(
                meta["dim"], n_queries=n_queries, threshold=thr, top_k=top_k
            )
            return (
                f"Blackhole detection complete (coverage) — project={project_id}\n"
                f"  Method     : coverage\n"
                f"  Threshold  : {result['threshold']} ({int(result['threshold']*result['n_queries'])} / {result['n_queries']} queries)\n"
                f"  Top-k      : {result['top_k']}\n"
                f"  Total paths: {result['total_paths']}\n"
                f"  Marked     : {result['marked']}\n"
                f"Use find/retrieve with exclude_blackholes=True to filter them out."
            )
        else:
            thr = threshold if threshold is not None else 0.85
            result = backend.compute_blackholes(meta["dim"], threshold=thr)
            return (
                f"Blackhole detection complete (centroid) — project={project_id}\n"
                f"  Threshold  : {result['threshold']}\n"
                f"  Total paths: {result['total_paths']}\n"
                f"  Marked     : {result['marked']}\n"
                f"Use find/retrieve with exclude_blackholes=True to filter them out."
            )
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def vacuum(
    project_id: str = "default",
    store_dir: str = STORE_DIR,
) -> str:
    """Compact the files index: remove soft-deleted vectors, rebuild int8 file.

    Run after many incremental index runs to reclaim disk space.
    """
    try:
        store_dir, project_id = _resolve(store_dir, project_id)
        backend = make_backend(_BACKEND_TYPE, store_dir=store_dir,
                               project_id=project_id, db_url=_DB_URL)
        meta = backend.load_meta()
        result = backend.vacuum_files(meta["dim"])
        return (
            f"Vacuum complete — project={project_id}\n"
            f"  chunks before : {result['before']}\n"
            f"  chunks after  : {result['after']}\n"
            f"  reclaimed     : {result['reclaimed_mb']} MB"
        )
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def embedding(
    text: str = "",
    file: str = "",
    project_id: str = "default",
    store_dir: str = STORE_DIR,
) -> str:
    """Compute embedding vector for a text or file.

    Returns JSON array of floats. Capture with -> varname to store as {{varname}}.
    Model loaded from project meta.json (same model used at index time).
    """
    try:
        store_dir, project_id = _resolve(store_dir, project_id)
        backend = make_backend(_BACKEND_TYPE, store_dir=store_dir,
                               project_id=project_id, db_url=_DB_URL)
        meta = backend.load_meta()
        embedder = get_embedder(meta.get("model_key", DEFAULT_MODEL))

        source = Path(file).read_text(encoding="utf-8", errors="ignore") if file else text
        if not source:
            return "ERROR: provide text= or file="

        vec = embedder.encode([source])[0]
        return json.dumps(vec.tolist())
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def distance(
    source1: str,
    source2: str,
    project_id: str = "default",
    store_dir: str = STORE_DIR,
) -> str:
    """Compute cosine similarity between two sources.

    Each source can be: a file path, a JSON vector string (from {{vector1}}), or inline text.
    """
    def _resolve_src(src: str, embedder) -> np.ndarray:
        src = src.strip()
        if src.startswith("["):
            return np.array(json.loads(src), dtype=np.float32)
        p = Path(src)
        if p.exists() and p.is_file():
            return embedder.encode([p.read_text(encoding="utf-8", errors="ignore")])[0]
        return embedder.encode([src])[0]

    try:
        backend = make_backend(_BACKEND_TYPE, store_dir=store_dir,
                               project_id=project_id, db_url=_DB_URL)
        meta = backend.load_meta()
        embedder = get_embedder(meta.get("model_key", DEFAULT_MODEL))

        v1, v2 = _resolve_src(source1, embedder), _resolve_src(source2, embedder)
        sim = float(np.dot(v1 / (np.linalg.norm(v1) or 1),
                           v2 / (np.linalg.norm(v2) or 1)))

        def _type(s: str) -> str:
            if s.strip().startswith("["): return "vector"
            if Path(s.strip()).exists(): return "file"
            return "text"

        return json.dumps({
            "similarity": round(sim, 6),
            "source1_type": _type(source1),
            "source2_type": _type(source2),
        }, indent=2)
    except Exception as e:
        return f"ERROR: {e}"


@mcp.prompt()
def search_task(query: str) -> str:
    """Find files relevant to a Jira/GitHub task description.

    Use when you have a natural-language task: bug report, feature request, ticket title.
    Searches the task/commit index — finds files that were historically changed for similar work.
    """
    return (
        f'Call find(query="{query}", mode="task", sort="freq", top_n=5). '
        f"sort=freq ranks files by how many similar commits touched them — "
        f"most historically relevant files rise to the top. "
        f"Report file paths with scores and explain why each is likely relevant to the task."
    )


@mcp.prompt()
def search_file(query: str) -> str:
    """Find files by code content — function names, class names, error messages, patterns.

    Use when you know what you're looking for in the code itself (not what task it belongs to).
    Searches directly in file chunk embeddings.
    """
    return (
        f'Call find(query="{query}", mode="file", sort="rank", top_n=5). '
        f"sort=rank gives the file with the highest single-chunk similarity — "
        f"best for pinpointing exact code locations. "
        f"Report file paths with scores."
    )


@mcp.prompt()
def search_aggr(query: str) -> str:
    """Find affected modules for architecture-level analysis.

    Use when you need a high-level answer: which subsystem or module owns this feature?
    Aggregates task vectors into a centroid, then searches file chunks with that centroid.
    """
    return (
        f'Call find(query="{query}", mode="aggr", top_n=5, top_m=3). '
        f"Focus on the Modules section of the result — it shows which subsystems are most affected. "
        f"Explain which module owns the feature and why."
    )


@mcp.prompt()
def search_rrf(query: str) -> str:
    """Most confident file ranking: merges task search + file search via Reciprocal Rank Fusion.

    Use when you want the highest confidence results and have both task and file indexes available.
    Files that appear in both task-search and file-search results get a ×2 score boost.
    A file at rank 1 in both sources is almost certainly the right target.
    """
    return (
        f'Call rrf(query="{query}", sources="task:default,file:default", top_n=5). '
        f"Report the RRF-ranked file list. "
        f"If a file has score ≥ 0.030 it was found by multiple sources — high confidence. "
        f"If score < 0.017 it was found by only one source — lower confidence."
    )


@mcp.prompt()
def search_refine(query: str) -> str:
    """Vocabulary-expanding search for natural language queries that don't use code terms.

    Use when the query is in business language and the codebase uses technical jargon.
    Finds similar commits, extracts their most frequent terms, expands the query, then searches files.
    """
    return (
        f'Call find(query="{query}", mode="refine", top_n=5, refine_top_k=10, refine_top_m=8). '
        f"The result will show an Expanded query line — report it so the user can see "
        f"what technical terms were added. Then report the matched files."
    )


def main():
    global _BACKEND_TYPE, _DB_URL, _STORE_DIR, _PROJECT_ID

    parser = argparse.ArgumentParser(prog="simargl-mcp")
    parser.add_argument("--http", action="store_true",
                        help="Use HTTP/SSE transport instead of stdio")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--backend", default="numpy", choices=["numpy", "postgres"])
    parser.add_argument("--db-url", default=None)
    parser.add_argument("--store-dir", default=None,
                        help="Override default .simargl store directory")
    parser.add_argument("--project-id", default=None,
                        help="Set default project_id for all tool calls")
    args = parser.parse_args()

    _BACKEND_TYPE = args.backend
    _DB_URL = args.db_url
    if args.store_dir:
        _STORE_DIR = args.store_dir
    if args.project_id:
        _PROJECT_ID = args.project_id

    # Pre-warm embedder at startup so the first tool call doesn't hang.
    # Reads meta.json to find the model that was used at index time.
    try:
        from .backends import make_backend as _mb
        _project = _PROJECT_ID or "default"
        _meta = _mb(_BACKEND_TYPE, store_dir=_STORE_DIR,
                    project_id=_project, db_url=_DB_URL).load_meta()
        print(f"[simargl] pre-warming model {_meta.get('model_key', DEFAULT_MODEL)} ...",
              file=sys.stderr, flush=True)
        get_embedder(_meta.get("model_key", DEFAULT_MODEL))
        print(f"[simargl] ready — project={_project}  store={_STORE_DIR}", file=sys.stderr, flush=True)
    except Exception as _e:
        print(f"[simargl] warning: could not pre-warm model: {_e}", file=sys.stderr, flush=True)

    if args.http:
        try:
            import uvicorn
        except ImportError:
            print("HTTP transport requires uvicorn: pip install simargl[http]", file=sys.stderr)
            sys.exit(1)
        print(f"simargl MCP server — http://{args.host}:{args.port}/sse", file=sys.stderr)
        print(f"Connect:  /mcp connect simargl http://<ip>:{args.port}/sse", file=sys.stderr)
        mcp.run(transport="sse", host=args.host, port=args.port)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
