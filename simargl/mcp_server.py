"""MCP server — tools: find, index_files, index_units, status, vacuum, embedding, distance.

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
from .searcher import search as _search
from .embedder import get_embedder
from .backends import make_backend

mcp = FastMCP("simargl")


def _resolve(store_dir: str, project_id: str) -> tuple[str, str]:
    """Apply global defaults if set at server startup."""
    return (
        _STORE_DIR if _STORE_DIR != STORE_DIR or store_dir == STORE_DIR else store_dir,
        _PROJECT_ID if _PROJECT_ID is not None else project_id,
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
    project_id: str = "default",
    store_dir: str = STORE_DIR,
) -> str:
    """Find files related to a query.

    mode=task  — embed query → similar tasks/commits → files changed in those units
    mode=file  — embed query → direct cosine search in file chunks
    mode=aggr  — average top-k unit vectors → centroid cosine search in file chunks
    sort=rank  — file score = max similarity among matching tasks (task mode only)
    sort=freq  — file score = count of matching tasks that changed it (task mode only)
    """
    try:
        store_dir, project_id = _resolve(store_dir, project_id)
        result = _search(
            query, mode=mode, sort=sort,
            top_n=top_n, top_k=top_k, top_m=top_m,
            include_diff=include_diff,
            project_id=project_id, store_dir=store_dir,
            backend_type=_BACKEND_TYPE, db_url=_DB_URL,
        )
    except Exception as e:
        return f"ERROR: {e}"

    lines = [f"Query: {query}  mode={mode}" + (f"  sort={sort}" if mode == "task" else ""), ""]
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
