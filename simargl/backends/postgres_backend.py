"""PostgreSQL + pgvector backend.

Same interface as NumpyBackend — drop-in replacement.

Install:
  pip install simargl[postgres]   # psycopg2-binary + pgvector

Requires PostgreSQL with pgvector extension:
  CREATE EXTENSION IF NOT EXISTS vector;

Tables per project (schema = simargl by default):
  simargl.{project_id}_files       — file chunks + vectors
  simargl.{project_id}_units       — task/commit vectors
  simargl.{project_id}_unit_files  — unit → file mapping
  simargl.{project_id}_meta        — key/value (replaces meta.json)

Advantages over numpy:
  - HNSW index → sub-linear search even on millions of vectors
  - Native soft delete — vacuum is just DELETE + VACUUM ANALYZE, no file rebuild
  - Concurrent writes safe
  - No memmap RAM constraints
"""
from __future__ import annotations

import json
from contextlib import contextmanager

import numpy as np


def _vec_str(v: np.ndarray) -> str:
    """Convert float32 array to pgvector literal '[0.1,0.2,...]'."""
    return "[" + ",".join(f"{x:.6f}" for x in v.tolist()) + "]"


class PostgresBackend:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "simargl",
        user: str = "postgres",
        password: str = "postgres",
        schema: str = "simargl",
        project_id: str = "default",
    ):
        self.dsn = dict(host=host, port=port, dbname=database, user=user, password=password)
        self.schema = schema
        self.project_id = project_id
        self._conn = None

    # ------------------------------------------------------------------ connection
    def _connect(self):
        if self._conn is None or self._conn.closed:
            import psycopg2
            self._conn = psycopg2.connect(**self.dsn)
            self._conn.autocommit = False
            with self._conn.cursor() as cur:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                cur.execute(f"CREATE SCHEMA IF NOT EXISTS {self.schema};")
            self._conn.commit()
        return self._conn

    @contextmanager
    def _cur(self):
        conn = self._connect()
        cur = conn.cursor()
        try:
            yield cur
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()

    def _tbl(self, name: str) -> str:
        """Fully qualified table name: schema.project_id_name"""
        return f'{self.schema}."{self.project_id}_{name}"'

    # ------------------------------------------------------------------ schema init
    def _ensure_files_table(self, dim: int) -> None:
        with self._cur() as cur:
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {self._tbl("files")} (
                    id      SERIAL PRIMARY KEY,
                    path    TEXT    NOT NULL,
                    chunk_n INTEGER NOT NULL DEFAULT 0,
                    norm    REAL    NOT NULL DEFAULT 1.0,
                    deleted BOOLEAN NOT NULL DEFAULT FALSE,
                    vector  vector({dim}) NOT NULL
                );
            """)
            cur.execute(f"""
                CREATE INDEX IF NOT EXISTS "{self.project_id}_files_vec_idx"
                ON {self._tbl("files")}
                USING hnsw (vector vector_cosine_ops);
            """)
            cur.execute(f"""
                CREATE INDEX IF NOT EXISTS "{self.project_id}_files_path_idx"
                ON {self._tbl("files")} (path) WHERE NOT deleted;
            """)

    def _ensure_units_table(self, dim: int) -> None:
        with self._cur() as cur:
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {self._tbl("units")} (
                    id           SERIAL PRIMARY KEY,
                    unit_id      TEXT NOT NULL,
                    unit_type    TEXT NOT NULL,
                    text_preview TEXT,
                    norm         REAL NOT NULL DEFAULT 1.0,
                    vector       vector({dim}) NOT NULL
                );
            """)
            cur.execute(f"""
                CREATE INDEX IF NOT EXISTS "{self.project_id}_units_vec_idx"
                ON {self._tbl("units")}
                USING hnsw (vector vector_cosine_ops);
            """)

    def _ensure_unit_files_table(self) -> None:
        with self._cur() as cur:
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {self._tbl("unit_files")} (
                    unit_id   TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    module    TEXT,
                    sha       TEXT,
                    db_path   TEXT
                );
            """)
            cur.execute(f"""
                CREATE INDEX IF NOT EXISTS "{self.project_id}_uf_unit_idx"
                ON {self._tbl("unit_files")} (unit_id);
            """)

    def _ensure_meta_table(self) -> None:
        with self._cur() as cur:
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {self._tbl("meta")} (
                    key   TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
            """)

    # ------------------------------------------------------------------ meta
    def save_meta(self, meta: dict) -> None:
        self._ensure_meta_table()
        with self._cur() as cur:
            for k, v in meta.items():
                cur.execute(f"""
                    INSERT INTO {self._tbl("meta")} (key, value)
                    VALUES (%s, %s)
                    ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
                """, (k, json.dumps(v)))

    def load_meta(self) -> dict:
        self._ensure_meta_table()
        with self._cur() as cur:
            cur.execute(f"SELECT key, value FROM {self._tbl('meta')};")
            rows = cur.fetchall()
        if not rows:
            raise FileNotFoundError(
                f"No index found for project '{self.project_id}'. Run index first."
            )
        return {k: json.loads(v) for k, v in rows}

    # ------------------------------------------------------------------ write
    def write_files(self, paths: list[str], chunk_ns: list[int],
                    vectors_f32: np.ndarray, dim: int) -> None:
        self._ensure_files_table(dim)
        norms = np.linalg.norm(vectors_f32, axis=1).astype(float)
        from psycopg2.extras import execute_values
        with self._cur() as cur:
            execute_values(cur, f"""
                INSERT INTO {self._tbl("files")} (path, chunk_n, norm, vector)
                VALUES %s
            """, [
                (paths[i], chunk_ns[i], float(norms[i]), _vec_str(vectors_f32[i]))
                for i in range(len(paths))
            ])

    def write_units(self, unit_ids: list[str], unit_types: list[str],
                    previews: list[str], vectors_f32: np.ndarray, dim: int) -> None:
        self._ensure_units_table(dim)
        norms = np.linalg.norm(vectors_f32, axis=1).astype(float)
        from psycopg2.extras import execute_values
        with self._cur() as cur:
            execute_values(cur, f"""
                INSERT INTO {self._tbl("units")} (unit_id, unit_type, text_preview, norm, vector)
                VALUES %s
            """, [
                (unit_ids[i], unit_types[i], previews[i],
                 float(norms[i]), _vec_str(vectors_f32[i]))
                for i in range(len(unit_ids))
            ])

    def write_unit_files(self, rows: list[tuple]) -> None:
        self._ensure_unit_files_table()
        from psycopg2.extras import execute_values
        with self._cur() as cur:
            execute_values(cur, f"""
                INSERT INTO {self._tbl("unit_files")}
                    (unit_id, file_path, module, sha, db_path)
                VALUES %s
            """, rows)

    # ------------------------------------------------------------------ soft delete
    def mark_deleted(self, paths: list[str]) -> int:
        if not paths:
            return 0
        with self._cur() as cur:
            cur.execute(f"""
                UPDATE {self._tbl("files")}
                SET deleted = TRUE
                WHERE path = ANY(%s) AND NOT deleted;
            """, (paths,))
            return cur.rowcount

    def indexed_paths(self) -> set[str]:
        try:
            with self._cur() as cur:
                cur.execute(f"""
                    SELECT DISTINCT path FROM {self._tbl("files")}
                    WHERE NOT deleted;
                """)
                return {r[0] for r in cur.fetchall()}
        except Exception:
            return set()

    # ------------------------------------------------------------------ vacuum
    def vacuum_files(self, dim: int) -> dict:
        """Delete soft-deleted rows + VACUUM ANALYZE (no file rebuild needed)."""
        with self._cur() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {self._tbl('files')};")
            before = cur.fetchone()[0]
            cur.execute(f"DELETE FROM {self._tbl('files')} WHERE deleted;")
            deleted = cur.rowcount

        # VACUUM must run outside transaction
        conn = self._connect()
        old_autocommit = conn.autocommit
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(f"VACUUM ANALYZE {self._tbl('files')};")
        conn.autocommit = old_autocommit

        after = before - deleted
        # estimate: float32 vector (dim * 4 bytes) + row overhead (~50 bytes)
        reclaimed_mb = round(deleted * (dim * 4 + 50) / (1024 * 1024), 2)
        return {"before": before, "after": after, "reclaimed_mb": reclaimed_mb}

    # ------------------------------------------------------------------ search
    def search_files(self, query_f32: np.ndarray, dim: int, top_n: int = 10) -> list[dict]:
        q = _vec_str(query_f32)
        with self._cur() as cur:
            cur.execute(f"""
                SELECT path, chunk_n,
                       1 - (vector <=> %s::vector) AS score
                FROM {self._tbl("files")}
                WHERE NOT deleted
                ORDER BY vector <=> %s::vector
                LIMIT %s;
            """, (q, q, top_n * 2))  # fetch extra, dedup by path in searcher
            rows = cur.fetchall()
        return [{"path": r[0], "chunk_n": r[1], "score": float(r[2])} for r in rows]

    def search_units(self, query_f32: np.ndarray, dim: int, top_k: int = 20) -> list[dict]:
        q = _vec_str(query_f32)
        with self._cur() as cur:
            cur.execute(f"""
                SELECT id, unit_id, unit_type, text_preview,
                       1 - (vector <=> %s::vector) AS score
                FROM {self._tbl("units")}
                ORDER BY vector <=> %s::vector
                LIMIT %s;
            """, (q, q, top_k))
            rows = cur.fetchall()
        return [
            {"db_id": r[0], "unit_id": r[1], "unit_type": r[2],
             "text_preview": r[3], "score": float(r[4])}
            for r in rows
        ]

    def get_unit_vectors_by_ids(self, ids: list[int], dim: int) -> np.ndarray:
        if not ids:
            return np.empty((0, dim), dtype=np.float32)
        with self._cur() as cur:
            cur.execute(f"""
                SELECT vector FROM {self._tbl("units")}
                WHERE id = ANY(%s)
                ORDER BY id;
            """, (ids,))
            rows = cur.fetchall()
        # pgvector returns vectors as lists via psycopg2 adapter
        from pgvector.psycopg2 import register_vector
        return np.array([list(r[0]) for r in rows], dtype=np.float32)

    def get_unit_files(self, unit_id: str) -> list[dict]:
        with self._cur() as cur:
            cur.execute(f"""
                SELECT file_path, module, sha, db_path
                FROM {self._tbl("unit_files")}
                WHERE unit_id = %s;
            """, (unit_id,))
            rows = cur.fetchall()
        return [{"file_path": r[0], "module": r[1], "sha": r[2], "db_path": r[3]}
                for r in rows]

    def stats(self) -> dict:
        meta = self.load_meta()
        file_count = chunk_count = deleted_count = unit_count = 0
        try:
            with self._cur() as cur:
                cur.execute(f"""
                    SELECT
                        COUNT(*) FILTER (WHERE NOT deleted),
                        COUNT(DISTINCT path) FILTER (WHERE NOT deleted),
                        COUNT(*) FILTER (WHERE deleted)
                    FROM {self._tbl("files")};
                """)
                r = cur.fetchone()
                chunk_count, file_count, deleted_count = r[0], r[1], r[2]
                cur.execute(f"SELECT COUNT(*) FROM {self._tbl('units')};")
                unit_count = cur.fetchone()[0]
        except Exception:
            pass
        return {
            **meta,
            "files": file_count,
            "chunks": chunk_count,
            "deleted_chunks": deleted_count,
            "units": unit_count,
        }
