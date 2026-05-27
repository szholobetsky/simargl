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
        cols = {r[1] for r in db.execute("PRAGMA table_info(chunks)")}
        if "deleted" not in cols:
            db.execute("ALTER TABLE chunks ADD COLUMN deleted INTEGER DEFAULT 0")
        if "blackhole" not in cols:
            db.execute("ALTER TABLE chunks ADD COLUMN blackhole INTEGER DEFAULT 0")
        if "coverage" not in cols:
            db.execute("ALTER TABLE chunks ADD COLUMN coverage REAL DEFAULT 0.0")
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

    def compute_blackholes(self, dim: int, threshold: float = 0.85) -> dict:
        """Mark chunks as blackholes: paths whose mean cosine similarity to the
        corpus centroid exceeds threshold. Returns {marked, total_paths, centroid_norm}.

        A blackhole file has uniformly high similarity to everything — it matches
        all queries equally and pollutes search results (e.g. CHANGELOG, relnotes).
        """
        vecs = self._load_vectors("files", dim)
        if len(vecs) == 0:
            return {"marked": 0, "total_paths": 0}

        db = self._open_files_db()
        live_rows = db.execute(
            "SELECT id, path FROM chunks WHERE deleted=0 ORDER BY id"
        ).fetchall()
        if not live_rows:
            db.close()
            return {"marked": 0, "total_paths": 0}

        live_ids = np.array([r[0] for r in live_rows], dtype=np.int64)
        live_paths = [r[1] for r in live_rows]
        live_idxs = live_ids - 1

        live_vecs = vecs[live_idxs].astype(np.float32)

        # Compute corpus centroid and normalize
        centroid = live_vecs.mean(axis=0)
        centroid_norm = float(np.linalg.norm(centroid))
        centroid /= centroid_norm + 1e-9

        # Score each chunk against centroid (same quantization as search_files)
        q_int8 = (centroid * 127).clip(-127, 127).astype(np.float32)
        scores = (live_vecs @ q_int8) / (127.0 ** 2)

        # Group by path: mean score per path
        from collections import defaultdict
        path_scores: dict[str, list[float]] = defaultdict(list)
        for i, path in enumerate(live_paths):
            path_scores[path].append(float(scores[i]))

        blackhole_paths = {
            p for p, sc in path_scores.items()
            if (sum(sc) / len(sc)) >= threshold
        }

        # Reset all, then mark blackholes
        db.execute("UPDATE chunks SET blackhole=0 WHERE deleted=0")
        if blackhole_paths:
            placeholders = ",".join("?" * len(blackhole_paths))
            db.execute(
                f"UPDATE chunks SET blackhole=1 WHERE path IN ({placeholders}) AND deleted=0",
                list(blackhole_paths),
            )
        db.commit()
        db.close()

        return {
            "marked": len(blackhole_paths),
            "total_paths": len(path_scores),
            "threshold": threshold,
            "centroid_norm": round(centroid_norm, 4),
        }

    def compute_blackholes_coverage(
        self, dim: int, n_queries: int = 100, threshold: float = 0.3, top_k: int = 20
    ) -> dict:
        """Mark blackholes by query-coverage: files that appear in the top-k results
        for an unusually large fraction of specific (non-generic) queries.

        Algorithm:
        1. Load unit vectors; compute unit centroid.
        2. Specificity = 1 - cosine(unit, centroid). High = unique commit/task.
        3. Select top n_queries most specific units as test queries.
        4. For each test query, find which file paths appear in top_k file results.
        5. coverage[path] = fraction of test queries where path appears in top_k.
        6. Mark paths with coverage >= threshold as blackholes.

        Relnotes / CHANGELOGs appear for ALL queries → high coverage.
        Structural cop files appear for SOME queries (related cops only) → low coverage.
        """
        unit_vecs = self._load_vectors("units", dim)
        if len(unit_vecs) == 0:
            return {"marked": 0, "total_paths": 0, "method": "coverage"}

        file_vecs = self._load_vectors("files", dim)
        if len(file_vecs) == 0:
            return {"marked": 0, "total_paths": 0, "method": "coverage"}

        db = self._open_files_db()
        live_rows = db.execute(
            "SELECT id, path FROM chunks WHERE deleted=0 ORDER BY id"
        ).fetchall()
        if not live_rows:
            db.close()
            return {"marked": 0, "total_paths": 0, "method": "coverage"}

        live_ids   = np.array([r[0] for r in live_rows], dtype=np.int64)
        live_paths = [r[1] for r in live_rows]
        live_idxs  = live_ids - 1
        live_vecs  = file_vecs[live_idxs].astype(np.float32)

        # --- step 1-2: unit specificity
        unit_f32 = unit_vecs.astype(np.float32)
        unit_centroid = unit_f32.mean(axis=0)
        norm = np.linalg.norm(unit_centroid)
        unit_centroid /= norm + 1e-9

        q_c = (unit_centroid * 127).clip(-127, 127).astype(np.float32)
        centroid_sims = (unit_f32 @ q_c) / (127.0 ** 2)
        specificity = 1.0 - centroid_sims

        # --- step 3: select top n_queries most specific units
        n_q = min(n_queries, len(unit_f32))
        top_unit_idxs = np.argpartition(specificity, -n_q)[-n_q:]
        query_vecs = unit_f32[top_unit_idxs]  # (n_q, dim)

        # --- step 4-5: batch cosine scores for all queries vs all live file chunks
        q_batch = (query_vecs * 127).clip(-127, 127).astype(np.float32)
        # scores: (n_q, n_live_chunks)
        scores_matrix = (q_batch @ live_vecs.T) / (127.0 ** 2)

        # For each query find top_k chunk indices
        k = min(top_k, live_vecs.shape[0])
        from collections import Counter
        path_hit_count: Counter = Counter()
        unique_paths = list(dict.fromkeys(live_paths))  # preserve order

        for row in scores_matrix:
            top_chunk_pos = np.argpartition(row, -k)[-k:]
            hit_paths = {live_paths[pos] for pos in top_chunk_pos}
            for p in hit_paths:
                path_hit_count[p] += 1

        # --- step 6: store float coverage per path + mark binary blackhole
        coverage_threshold = threshold * n_q
        blackhole_set = {p for p, cnt in path_hit_count.items() if cnt >= coverage_threshold}

        db.execute("UPDATE chunks SET blackhole=0, coverage=0.0 WHERE deleted=0")
        for path in unique_paths:
            cov = path_hit_count.get(path, 0) / n_q
            db.execute(
                "UPDATE chunks SET coverage=? WHERE path=? AND deleted=0",
                (cov, path),
            )
        if blackhole_set:
            placeholders = ",".join("?" * len(blackhole_set))
            db.execute(
                f"UPDATE chunks SET blackhole=1 WHERE path IN ({placeholders}) AND deleted=0",
                list(blackhole_set),
            )
        db.commit()
        db.close()

        return {
            "marked": len(blackhole_set),
            "total_paths": len(unique_paths),
            "threshold": threshold,
            "n_queries": n_q,
            "top_k": top_k,
            "method": "coverage",
        }

    def compute_file_coverage(
        self, dim: int, n_queries: int = 200, top_k: int = 20
    ) -> dict:
        """Compute per-file coverage score [0..1]: fraction of specific unit queries
        where the file appears in top_k results. Stores in files.db `coverage` column.

        Use with search_files(coverage_penalty=λ) to re-rank rather than filter.
        Core files (high coverage + high relevance) survive; noise files (high coverage
        + moderate relevance) are pushed down by the penalty.

        Does NOT mark binary blackhole — use compute_blackholes_coverage() for that.
        """
        unit_vecs = self._load_vectors("units", dim)
        if len(unit_vecs) == 0:
            return {"total_paths": 0, "n_queries": 0, "method": "coverage_float"}

        file_vecs = self._load_vectors("files", dim)
        if len(file_vecs) == 0:
            return {"total_paths": 0, "n_queries": 0, "method": "coverage_float"}

        db = self._open_files_db()
        live_rows = db.execute(
            "SELECT id, path FROM chunks WHERE deleted=0 ORDER BY id"
        ).fetchall()
        if not live_rows:
            db.close()
            return {"total_paths": 0, "n_queries": 0, "method": "coverage_float"}

        live_ids   = np.array([r[0] for r in live_rows], dtype=np.int64)
        live_paths = [r[1] for r in live_rows]
        live_idxs  = live_ids - 1
        live_vecs  = file_vecs[live_idxs].astype(np.float32)

        unit_f32 = unit_vecs.astype(np.float32)
        unit_centroid = unit_f32.mean(axis=0)
        cnorm = np.linalg.norm(unit_centroid)
        unit_centroid /= cnorm + 1e-9

        q_c = (unit_centroid * 127).clip(-127, 127).astype(np.float32)
        centroid_sims = (unit_f32 @ q_c) / (127.0 ** 2)
        specificity = 1.0 - centroid_sims

        n_q = min(n_queries, len(unit_f32))
        top_unit_idxs = np.argpartition(specificity, -n_q)[-n_q:]
        query_vecs = unit_f32[top_unit_idxs]

        q_batch = (query_vecs * 127).clip(-127, 127).astype(np.float32)
        scores_matrix = (q_batch @ live_vecs.T) / (127.0 ** 2)

        k = min(top_k, live_vecs.shape[0])
        from collections import Counter
        path_hit_count: Counter = Counter()
        unique_paths = list(dict.fromkeys(live_paths))

        for row in scores_matrix:
            top_chunk_pos = np.argpartition(row, -k)[-k:]
            hit_paths = {live_paths[pos] for pos in top_chunk_pos}
            for p in hit_paths:
                path_hit_count[p] += 1

        # Store float coverage [0..1], do NOT touch blackhole column
        db.execute("UPDATE chunks SET coverage=0.0 WHERE deleted=0")
        for path in unique_paths:
            cov = path_hit_count.get(path, 0) / n_q
            if cov > 0:
                db.execute(
                    "UPDATE chunks SET coverage=? WHERE path=? AND deleted=0",
                    (cov, path),
                )
        db.commit()
        db.close()

        max_cov = max(path_hit_count.values()) / n_q if path_hit_count else 0.0
        return {
            "total_paths": len(unique_paths),
            "n_queries": n_q,
            "top_k": top_k,
            "max_coverage": round(max_cov, 4),
            "method": "coverage_float",
        }

    def blackhole_paths(self) -> set[str]:
        """Return set of paths currently marked as blackholes."""
        db = self._open_files_db()
        rows = db.execute(
            "SELECT DISTINCT path FROM chunks WHERE blackhole=1 AND deleted=0"
        ).fetchall()
        db.close()
        return {r[0] for r in rows}

    def search_files(self, query_f32: np.ndarray, dim: int, top_n: int = 10,
                     exclude_blackholes: bool = False,
                     coverage_penalty: float = 0.0,
                     score_blend: float = 1.0) -> list[dict]:
        """Cosine search in files index. Returns top_n [{path, chunk_n, score}], deleted excluded.

        score_blend: α in  adjusted = α*max_chunk + (1-α)*mean_chunk  (default 1.0 = pure max).
          Focused files (all chunks relevant) have max ≈ mean → unaffected.
          Broad documents (one relevant chunk among many) have max >> mean → pushed down.
          Typical range: 0.5-0.8.

        coverage_penalty: subtract λ*coverage from chunk scores before ranking (0.0 = off).
          Run blackhole(method='coverage_float') first to populate coverage column.
        """
        vecs = self._load_vectors("files", dim)
        if len(vecs) == 0:
            return []

        db = self._open_files_db()
        where = "deleted=0" + (" AND blackhole=0" if exclude_blackholes else "")
        live_rows = db.execute(
            f"SELECT id, path, chunk_n, coverage FROM chunks WHERE {where} ORDER BY id"
        ).fetchall()
        db.close()

        if not live_rows:
            return []

        live_ids       = np.array([r[0] for r in live_rows], dtype=np.int64)
        live_paths     = [r[1] for r in live_rows]
        live_chunk_ns  = [r[2] for r in live_rows]
        live_coverages = np.array([r[3] or 0.0 for r in live_rows], dtype=np.float32)

        q_int8 = (query_f32 * 127).clip(-127, 127).astype(np.float32)
        scores = (vecs[live_ids - 1].astype(np.float32) @ q_int8) / (127.0 ** 2)

        if coverage_penalty > 0.0:
            scores = scores - coverage_penalty * live_coverages

        # Group by path: collect (score, chunk_n) per file.
        # adjusted = α*max + (1-α)*mean  — rewards files uniformly about the topic.
        from collections import defaultdict
        path_chunks: dict[str, list] = defaultdict(list)
        for i, path in enumerate(live_paths):
            path_chunks[path].append((float(scores[i]), live_chunk_ns[i]))

        results = []
        for path, chunk_list in path_chunks.items():
            chunk_scores = [s for s, _ in chunk_list]
            mx = max(chunk_scores)
            if score_blend < 1.0:
                mn = sum(chunk_scores) / len(chunk_scores)
                adj = score_blend * mx + (1.0 - score_blend) * mn
            else:
                adj = mx
            best_cn = max(chunk_list, key=lambda x: x[0])[1]
            results.append({"path": path, "chunk_n": best_cn, "score": adj})

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_n]

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
