"""Indexer: index_files() and index_units() with auto-detect.

Incremental indexing:
  - Skips files whose mtime <= indexed_at (unchanged)
  - Re-embeds modified files (marks old chunks deleted, appends new)
  - Marks deleted files (in index but missing on disk) as deleted
  - Use simargl vacuum to compact the int8 file after many incremental runs
"""
from __future__ import annotations

import datetime
import time
import sqlite3
from pathlib import Path

from tqdm import tqdm

from .config import DEFAULT_MODEL, STORE_DIR
from .embedder import get_embedder
from .backends import make_backend
from .utils import preprocess_text, combine_fields, norm_path, module_from_path, chunk_text

SKIP_DIRS = {
    ".git", ".svn", "__pycache__", "node_modules", ".tox", ".venv", "venv",
    ".idea", ".vscode", "dist", "build", "target",
}
TEXT_EXTENSIONS = {
    ".py", ".java", ".kt", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs",
    ".cpp", ".c", ".h", ".cs", ".rb", ".php", ".scala", ".swift",
    ".sql", ".yaml", ".yml", ".json", ".toml", ".ini", ".cfg",
    ".md", ".txt", ".xml", ".html", ".css",
}


def index_files(
    path: str,
    model_key: str = DEFAULT_MODEL,
    project_id: str = "default",
    store_dir: str = STORE_DIR,
    chunk_size: int = 400,
    full: bool = False,
    backend_type: str = "numpy",
    db_url: str | None = None,
) -> dict:
    """Walk path, chunk text files, embed, store in numpy backend.

    Incremental by default: skips files unchanged since last index (mtime check).
    Pass full=True to re-embed everything regardless of mtime.

    Returns: {files_new, files_modified, files_deleted, chunks_added}
    """
    embedder = get_embedder(model_key)
    backend = make_backend(backend_type, store_dir=store_dir,
                           project_id=project_id, db_url=db_url)

    # load previous indexed_at timestamp (unix) — 0 means index everything
    prev_ts: float = 0.0
    if not full:
        try:
            meta = backend.load_meta()
            prev_ts = float(meta.get("indexed_at_ts", 0))
        except FileNotFoundError:
            pass

    root = Path(path)
    texts: list[str] = []
    rel_paths: list[str] = []
    chunk_ns: list[int] = []

    files_new = 0
    files_modified = 0
    chunks_added = 0
    disk_paths: set[str] = set()
    modified_paths: list[str] = []

    # collect candidate files first so tqdm can show total
    candidates = []
    for fpath in root.rglob("*"):
        parts = fpath.relative_to(root).parts
        if any(p.startswith(".") or p in SKIP_DIRS for p in parts):
            continue
        if fpath.is_file() and fpath.suffix.lower() in TEXT_EXTENSIONS:
            candidates.append(fpath)

    indexed = backend.indexed_paths()

    with tqdm(candidates, desc="Scanning files", unit="file") as bar:
        for fpath in bar:
            rel = norm_path(str(fpath.relative_to(root)))
            disk_paths.add(rel)

            mtime = fpath.stat().st_mtime
            if mtime <= prev_ts:
                continue

            try:
                content = fpath.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if not content.strip():
                continue

            bar.set_postfix_str(rel[-40:])

            if rel in indexed:
                files_modified += 1
                modified_paths.append(rel)
            else:
                files_new += 1

            chunks = chunk_text(content, chunk_size=chunk_size)
            for i, chunk in enumerate(chunks):
                texts.append(chunk)
                rel_paths.append(rel)
                chunk_ns.append(i)

            if len(texts) >= 256:
                if modified_paths:
                    backend.mark_deleted(modified_paths)
                    modified_paths = []
                vecs = embedder.encode(texts)
                backend.write_files(rel_paths, chunk_ns, vecs, embedder.dim)
                chunks_added += len(texts)
                texts, rel_paths, chunk_ns = [], [], []

    # flush remainder
    if texts:
        if modified_paths:
            backend.mark_deleted(modified_paths)
        vecs = embedder.encode(texts)
        backend.write_files(rel_paths, chunk_ns, vecs, embedder.dim)
        chunks_added += len(texts)

    # detect deleted files (in index, not on disk)
    indexed_now = backend.indexed_paths()
    gone = [p for p in indexed_now if p not in disk_paths]
    files_deleted = 0
    if gone:
        files_deleted = len(gone)
        backend.mark_deleted(gone)

    now_ts = time.time()
    meta = {
        "model_key": model_key,
        "dim": embedder.dim,
        "indexed_at": datetime.datetime.utcnow().isoformat(),
        "indexed_at_ts": now_ts,
    }
    try:
        existing = backend.load_meta()
        existing.update(meta)
        meta = existing
    except FileNotFoundError:
        pass
    backend.save_meta(meta)

    return {
        "files_new": files_new,
        "files_modified": files_modified,
        "files_deleted": files_deleted,
        "chunks_added": chunks_added,
    }


def index_units(
    db_path: str,
    model_key: str = DEFAULT_MODEL,
    project_id: str = "default",
    store_dir: str = STORE_DIR,
    mode: str = "auto",
    backend_type: str = "numpy",
    db_url: str | None = None,
) -> dict:
    """Index semantic units (tasks or commits) from SQLite.

    mode="auto"    → detect by TASK_NAME coverage in COMMIT table
    mode="tasks"   → TASKS.TITLE + TASKS.DESCRIPTION
    mode="commits" → COMMIT.MESSAGE grouped by SHA
    """
    embedder = get_embedder(model_key)
    backend = make_backend(backend_type, store_dir=store_dir,
                           project_id=project_id, db_url=db_url)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # auto-detect mode
    if mode == "auto":
        total = conn.execute("SELECT COUNT(*) FROM COMMITS").fetchone()[0]
        if total == 0:
            mode = "tasks"
        else:
            named = conn.execute(
                "SELECT COUNT(*) FROM COMMITS WHERE TASK_NAME IS NOT NULL AND TASK_NAME != ''"
            ).fetchone()[0]
            mode = "tasks" if (named / total) > 0.5 else "commits"

    unit_ids: list[str] = []
    unit_types: list[str] = []
    previews: list[str] = []
    texts: list[str] = []
    unit_file_rows: list[tuple] = []

    if mode == "tasks":
        tasks = conn.execute(
            "SELECT NAME, TITLE, DESCRIPTION FROM TASKS"
        ).fetchall()
        for task in tqdm(tasks, desc="Reading tasks", unit="task"):
            name = task["NAME"]
            text = combine_fields(dict(task), ["TITLE", "DESCRIPTION"])
            unit_ids.append(name)
            unit_types.append("task")
            previews.append(text[:120])
            texts.append(text)

        rows = conn.execute(
            "SELECT TASK_NAME, PATH, SHA FROM COMMITS WHERE TASK_NAME IS NOT NULL"
        ).fetchall()
        for r in rows:
            fp = norm_path(r["PATH"])
            unit_file_rows.append((r["TASK_NAME"], fp, module_from_path(fp),
                                   r["SHA"] or "", db_path))

    else:  # commits
        rows = conn.execute(
            "SELECT SHA, MESSAGE, PATH FROM COMMITS WHERE SHA IS NOT NULL GROUP BY SHA"
        ).fetchall()
        seen_sha: set[str] = set()
        for r in rows:
            sha = r["SHA"]
            if sha in seen_sha:
                continue
            seen_sha.add(sha)
            text = preprocess_text(r["MESSAGE"])
            unit_ids.append(sha)
            unit_types.append("commit")
            previews.append(text[:120])
            texts.append(text)

        all_rows = conn.execute(
            "SELECT SHA, PATH FROM COMMITS WHERE SHA IS NOT NULL"
        ).fetchall()
        for r in all_rows:
            fp = norm_path(r["PATH"])
            unit_file_rows.append((r["SHA"], fp, module_from_path(fp), r["SHA"], db_path))

    conn.close()

    if texts:
        vecs = embedder.encode(texts)
        backend.write_units(unit_ids, unit_types, previews, vecs, embedder.dim)
        backend.write_unit_files(unit_file_rows)

    meta = {
        "model_key": model_key,
        "dim": embedder.dim,
        "unit_mode": mode,
        "db_path": db_path,
        "indexed_at": datetime.datetime.utcnow().isoformat(),
    }
    try:
        existing = backend.load_meta()
        existing.update(meta)
        meta = existing
    except FileNotFoundError:
        pass
    backend.save_meta(meta)

    return {"units_indexed": len(texts), "mode_used": mode}
