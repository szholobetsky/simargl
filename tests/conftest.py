"""Shared fixtures for simargl tests."""
import sqlite3
import numpy as np
import pytest


class MockEmbedder:
    """Deterministic fake embedder — no model download required."""
    dim = 8
    index_flush_size = 256      # the indexer flushes this many texts at a time (BaseEmbedder's default)

    def encode(self, texts: list[str], batch_size: int = 32) -> np.ndarray:
        rng = np.random.RandomState(sum(len(t) for t in texts) % 1000)
        vecs = rng.randn(len(texts), self.dim).astype(np.float32)
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        return vecs / np.where(norms == 0, 1.0, norms)


@pytest.fixture
def mock_embedder(monkeypatch):
    emb = MockEmbedder()
    monkeypatch.setattr("simargl.indexer.get_embedder", lambda key: emb)
    monkeypatch.setattr("simargl.searcher.get_embedder", lambda key: emb)
    return emb


# table layouts seen in the wild: canonical singular, older simargl ingest
# (plural), and the codeXtract datasets sonar.db / flink.db (TASK + COMMITS)
_LAYOUTS = {"singular": ("TASK", '"COMMIT"'), "plural": ("TASKS", "COMMITS"),
            "mixed": ("TASK", "COMMITS")}


@pytest.fixture(params=list(_LAYOUTS))
def tiny_db(tmp_path, request):
    """SQLite with task + commit tables and a few rows, in every table layout."""
    task_t, commit_t = _LAYOUTS[request.param]
    db = tmp_path / "units.db"
    con = sqlite3.connect(db)
    con.execute(f"""
        CREATE TABLE {commit_t} (
            ID INTEGER PRIMARY KEY,
            SHA TEXT, AUTHOR_NAME TEXT, AUTHOR_EMAIL TEXT,
            CMT_DATE TEXT, MESSAGE TEXT, PATH TEXT, DIFF TEXT, TASK_NAME TEXT
        )
    """)
    con.execute(f"""
        CREATE TABLE {task_t} (
            ID INTEGER PRIMARY KEY,
            NAME TEXT, TITLE TEXT, DESCRIPTION TEXT, COMMENTS TEXT
        )
    """)
    rows = [
        (1, "abc1", "Alice", "a@x.com", "2025-01-01",
         "PROJ-1 fix login bug", "auth/login.py", "+ def login():", "PROJ-1"),
        (2, "abc2", "Bob", "b@x.com", "2025-01-02",
         "PROJ-2 add user endpoint", "api/users.py", "+ def get_user():", "PROJ-2"),
        (3, "abc3", "Alice", "a@x.com", "2025-01-03",
         "PROJ-1 update login validation", "auth/login.py", "+ raise ValueError", "PROJ-1"),
    ]
    con.executemany(
        f"INSERT INTO {commit_t} VALUES (?,?,?,?,?,?,?,?,?)", rows
    )
    task_rows = [
        (1, "PROJ-1", "Fix login", "Users cannot login with special chars", ""),
        (2, "PROJ-2", "User endpoint", "Add REST endpoint for user retrieval", ""),
    ]
    con.executemany(f"INSERT INTO {task_t} VALUES (?,?,?,?,?)", task_rows)
    con.commit()
    con.close()
    return db


@pytest.fixture
def tiny_repo(tmp_path):
    """Small directory with Python files for index_files()."""
    (tmp_path / "auth").mkdir()
    (tmp_path / "api").mkdir()
    (tmp_path / "auth" / "login.py").write_text(
        "def login(user, password):\n    return user == 'admin'\n"
    )
    (tmp_path / "api" / "users.py").write_text(
        "def get_user(user_id):\n    return {'id': user_id}\n"
    )
    (tmp_path / "README.md").write_text("# Project\n\nAuthentication module.\n")
    return tmp_path
