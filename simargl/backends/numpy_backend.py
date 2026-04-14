"""Default backend: numpy memmap + int8 + SQLite metadata.

Storage layout per project:
  .simargl/{project_id}/
    files.int8       — np.memmap (N, dim), int8  (append-only; deleted rows kept until vacuum)
    files.db         — SQLite: (id INTEGER, path TEXT, chunk_n INTEGER, norm REAL, deleted INTEGER)
    units.int8       — np.memmap (M, dim), int8
    units.db         — SQLite: (id INTEGER, unit_id TEXT, unit_type TEXT, text_preview TEXT, norm REAL)
    unit_files.db    — SQLite: (unit_id TEXT, file_path TEXT, module TEXT, sha TEXT, db_path TEXT)
    meta.json        — {model_key, dim, unit_mode, db_path, indexed_at (unix timestamp)}

Soft delete: mark rows deleted=1 in files.db; vectors stay in int8 until vacuum.
Vacuum: rebuild int8 keeping only live rows; reassign sequential ids.

Quantization: float32 → int8 via x*127; norms stored separately for cosine.
Search: int8 dot product → float32, divide by norms → cosine similarity.
RAM: only accessed pages stay resident (OS page cache).
"""
from __future__ import annotations

import json
import sqlite3
import tempfile
import shutil
from pathlib import Path

import numpy as np


class NumpyBackend:
    def __init__(self, store_dir: str = ".simargl", project_id: str = "default"):
        self.project_dir = Path(store_dir) / project_id
        self.project_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ paths
    def _path(self, name: str) -> Path:
        return self.project_dir / name

    # ------------------------------------------------------------------ meta
    def save_meta(self, meta: dict) -> None:
        with open(self._path("meta.json"), "w") as f:
            json.dump(meta, f, indent=2)

    def load_meta(self) -> dict:
        p = self._path("meta.json")
        if not p.exists():
            raise FileNotFoundError(f"No index found at {self.project_dir}. Run index first.")
        with open(p) as f:
            return json.load(f)

    # ------------------------------------------------------------------ write
    def _quantize(self, vecs_f32: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Return (int8 vectors, float32 norms)."""
        norms = np.linalg.norm(vecs_f32, axis=1).astype(np.float32)
        safe_norms = np.where(norms == 0, 1.0, norms)
        normalized = vecs_f32 / safe_norms[:, None]
        int8_vecs = (normalized * 127).clip(-127, 127).astype(np.int8)
        return int8_vecs, norms

    def _open_files_db(self) -> sqlite3.Connection:
        db = sqlite3.connect(self._path("files.db"))
        db.execute(
            "CREATE TABLE IF NOT EXISTS chunks "
            "(id INTEGER PRIMARY KEY, path TEXT, chunk_n INTEGER, norm REAL, deleted INTEGER DEFAULT 0)"
        )
        # add deleted column if upgrading from MVP schema
        cols = {r[1] for r in db.execute("PRAGMA table_info(chunks)")}
        if "deleted" not in cols:
            db.execute("ALTER TABLE chunks ADD COLUMN deleted INTEGER DEFAULT 0")
        db.commit()
        return db

    def write_files(self, paths: list[str], chunk_ns: list[int],
                    vectors_f32: np.ndarray, dim: int) -> None:
        """Append file chunk vectors."""
        int8_vecs, norms = self._quantize(vectors_f32)
        n = len(int8_vecs)

        int8_path = self._path("files.int8")
        existing = int8_path.stat().st_size // dim if int8_path.exists() else 0
        fp = np.memmap(int8_path, dtype="int8", mode="r+" if existing else "w+",
                       shape=(existing + n, dim))
        fp[existing:] = int8_vecs
        del fp

        db = self._open_files_db()
        db.executemany(
            "INSERT INTO chunks (path, chunk_n, norm, deleted) VALUES (?, ?, ?, 0)",
            [(paths[i], chunk_ns[i], float(norms[i])) for i in range(n)],
        )
        db.commit()
        db.close()

    def write_units(self, unit_ids: list[str], unit_types: list[str],
                    previews: list[str], vectors_f32: np.ndarray, dim: int) -> None:
        int8_vecs, norms = self._quantize(vectors_f32)
        n = len(int8_vecs)

        int8_path = self._path("units.int8")
        existing = int8_path.stat().st_size // dim if int8_path.exists() else 0
        fp = np.memmap(int8_path, dtype="int8", mode="r+" if existing else "w+",
                       shape=(existing + n, dim))
        fp[existing:] = int8_vecs
        del fp

        db = sqlite3.connect(self._path("units.db"))
        db.execute(
            "CREATE TABLE IF NOT EXISTS units "
            "(id INTEGER PRIMARY KEY, unit_id TEXT, unit_type TEXT, text_preview TEXT, norm REAL)"
        )
        db.executemany(
            "INSERT INTO units (unit_id, unit_type, text_preview, norm) VALUES (?, ?, ?, ?)",
            [(unit_ids[i], unit_types[i], previews[i], float(norms[i])) for i in range(n)],
        )
        db.commit()
        db.close()

    def write_unit_files(self, rows: list[tuple]) -> None:
        db = sqlite3.connect(self._path("unit_files.db"))
        db.execute(
            "CREATE TABLE IF NOT EXISTS unit_files "
            "(unit_id TEXT, file_path TEXT, module TEXT, sha TEXT, db_path TEXT)"
        )
        db.executemany("INSERT INTO unit_files VALUES (?, ?, ?, ?, ?)", rows)
        db.commit()
        db.close()

    # ------------------------------------------------------------------ soft delete
    def mark_deleted(self, paths: list[str]) -> int:
        """Mark all chunks for given paths as deleted. Returns count of rows affected."""
        if not paths:
            return 0
        db = self._open_files_db()
        placeholders = ",".join("?" * len(paths))
        cur = db.execute(
            f"UPDATE chunks SET deleted=1 WHERE path IN ({placeholders}) AND deleted=0",
            paths,
        )
        count = cur.rowcount
        db.commit()
        db.close()
        return count

    def indexed_paths(self) -> set[str]:
        """Return all non-deleted paths currently in the index."""
        p = self._path("files.db")
        if not p.exists():
            return set()
        db = sqlite3.connect(p)
        rows = db.execute("SELECT DISTINCT path FROM chunks WHERE deleted=0").fetchall()
        db.close()
        return {r[0] for r in rows}

    # ------------------------------------------------------------------ vacuum
    def vacuum_files(self, dim: int) -> dict:
        """Compact files index: remove deleted rows, rebuild int8 + db with sequential ids.

        Returns: {before: N, after: M, reclaimed_mb: float}
        """
        int8_path = self._path("files.int8")
        db_path = self._path("files.db")

        if not int8_path.exists():
            return {"before": 0, "after": 0, "reclaimed_mb": 0.0}

        db = self._open_files_db()
        # load live rows ordered by id (= original memmap row order)
        live = db.execute(
            "SELECT id, path, chunk_n, norm FROM chunks WHERE deleted=0 ORDER BY id"
        ).fetchall()
        total = db.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        db.close()

        before = total
        after = len(live)

        if after == total:
            return {"before": before, "after": after, "reclaimed_mb": 0.0}

        # load full memmap
        n_total = int8_path.stat().st_size // dim
        old_mm = np.memmap(int8_path, dtype="int8", mode="r", shape=(n_total, dim))

        # build new int8 and new db in temp files
        tmp_int8 = self._path("files.int8.tmp")
        tmp_db   = self._path("files.db.tmp")

        new_mm = np.memmap(tmp_int8, dtype="int8", mode="w+", shape=(after, dim))
        for new_idx, (old_id, path, chunk_n, norm) in enumerate(live):
            old_idx = old_id - 1  # id is 1-based
            new_mm[new_idx] = old_mm[old_idx]
        del old_mm, new_mm

        new_db = sqlite3.connect(tmp_db)
        new_db.execute(
            "CREATE TABLE chunks "
            "(id INTEGER PRIMARY KEY, path TEXT, chunk_n INTEGER, norm REAL, deleted INTEGER DEFAULT 0)"
        )
        new_db.executemany(
            "INSERT INTO chunks (path, chunk_n, norm, deleted) VALUES (?, ?, ?, 0)",
            [(r[1], r[2], r[3]) for r in live],
        )
        new_db.commit()
        new_db.close()

        # atomic swap
        int8_path.unlink()
        db_path.unlink()
        tmp_int8.rename(int8_path)
        tmp_db.rename(db_path)

        reclaimed = (before - after) * dim / (1024 * 1024)
        return {"before": before, "after": after, "reclaimed_mb": round(reclaimed, 2)}

    # ------------------------------------------------------------------ search
    def _load_vectors(self, name: str, dim: int) -> np.ndarray:
        p = self._path(f"{name}.int8")
        if not p.exists():
            return np.empty((0, dim), dtype="int8")
        n = p.stat().st_size // dim
        return np.memmap(p, dtype="int8", mode="r", shape=(n, dim))

    def search_files(self, query_f32: np.ndarray, dim: int, top_n: int = 10) -> list[dict]:
        """Cosine search in files index. Returns top_n [{path, chunk_n, score}], deleted excluded."""
        vecs = self._load_vectors("files", dim)
        if len(vecs) == 0:
            return []

        db = self._open_files_db()
        # load id for live rows only (norms not needed — vectors are pre-normalized before quantization)
        live_rows = db.execute(
            "SELECT id FROM chunks WHERE deleted=0 ORDER BY id"
        ).fetchall()
        db.close()

        if not live_rows:
            return []

        live_ids  = np.array([r[0] for r in live_rows], dtype=np.int64)
        live_idxs  = live_ids - 1  # 0-based memmap positions

        # Stored int8 vectors = normalized_f32 * 127. Query quantized the same way.
        # cosine = (v_int8 @ q_int8) / 127² since both sides are unit-normalized.
        q_int8 = (query_f32 * 127).clip(-127, 127).astype(np.float32)

        subset = vecs[live_idxs].astype(np.float32)
        scores = (subset @ q_int8) / (127.0 ** 2)

        k = min(top_n, len(scores))
        top_pos = np.argpartition(scores, -k)[-k:]
        top_pos = top_pos[np.argsort(scores[top_pos])[::-1]]

        db = self._open_files_db()
        results = []
        for pos in top_pos:
            orig_id = int(live_ids[pos])
            row = db.execute(
                "SELECT path, chunk_n FROM chunks WHERE id = ?", (orig_id,)
            ).fetchone()
            if row:
                results.append({"path": row[0], "chunk_n": row[1], "score": float(scores[pos])})
        db.close()
        return results

    def search_units(self, query_f32: np.ndarray, dim: int, top_k: int = 20) -> list[dict]:
        vecs = self._load_vectors("units", dim)
        if len(vecs) == 0:
            return []

        p = self._path("units.db")
        if not p.exists():
            return []
        db = sqlite3.connect(p)
        all_rows = db.execute(
            "SELECT id FROM units ORDER BY id"
        ).fetchall()
        db.close()

        if not all_rows:
            return []

        ids = np.array([r[0] for r in all_rows], dtype=np.int64)

        q_int8 = (query_f32 * 127).clip(-127, 127).astype(np.float32)
        scores = (vecs.astype(np.float32) @ q_int8) / (127.0 ** 2)

        k = min(top_k, len(scores))
        top_pos = np.argpartition(scores, -k)[-k:]
        top_pos = top_pos[np.argsort(scores[top_pos])[::-1]]

        db = sqlite3.connect(self._path("units.db"))
        results = []
        for pos in top_pos:
            row = db.execute(
                "SELECT unit_id, unit_type, text_preview FROM units WHERE id = ?",
                (int(ids[pos]),),
            ).fetchone()
            if row:
                results.append({
                    "db_id": int(ids[pos]),
                    "unit_id": row[0], "unit_type": row[1],
                    "text_preview": row[2], "score": float(scores[pos]),
                })
        db.close()
        return results

    def get_unit_vectors_by_ids(self, ids: list[int], dim: int) -> np.ndarray:
        """Return float32 vectors for given unit db ids (1-based). Shape (N, dim)."""
        vecs = self._load_vectors("units", dim)
        if len(vecs) == 0:
            return np.empty((0, dim), dtype=np.float32)
        idxs = np.array(ids, dtype=np.int64) - 1  # 1-based → 0-based
        valid = idxs[(idxs >= 0) & (idxs < len(vecs))]
        return vecs[valid].astype(np.float32)

    def get_unit_files(self, unit_id: str) -> list[dict]:
        p = self._path("unit_files.db")
        if not p.exists():
            return []
        db = sqlite3.connect(p)
        rows = db.execute(
            "SELECT file_path, module, sha, db_path FROM unit_files WHERE unit_id = ?",
            (unit_id,),
        ).fetchall()
        db.close()
        return [{"file_path": r[0], "module": r[1], "sha": r[2], "db_path": r[3]} for r in rows]

    def stats(self) -> dict:
        meta = self.load_meta()
        file_count = chunk_count = deleted_count = unit_count = 0
        p = self._path("files.db")
        if p.exists():
            db = sqlite3.connect(p)
            chunk_count   = db.execute("SELECT COUNT(*) FROM chunks WHERE deleted=0").fetchone()[0]
            file_count    = db.execute("SELECT COUNT(DISTINCT path) FROM chunks WHERE deleted=0").fetchone()[0]
            deleted_count = db.execute("SELECT COUNT(*) FROM chunks WHERE deleted=1").fetchone()[0]
            db.close()
        p = self._path("units.db")
        if p.exists():
            db = sqlite3.connect(p)
            unit_count = db.execute("SELECT COUNT(*) FROM units").fetchone()[0]
            db.close()
        return {
            **meta,
            "files": file_count,
            "chunks": chunk_count,
            "deleted_chunks": deleted_count,
            "units": unit_count,
        }
