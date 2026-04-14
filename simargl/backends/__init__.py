"""Backend factory.

Usage:
    get_backend("numpy", store_dir=".simargl", project_id="sonar")
    get_backend("postgres", host="localhost", port=5432, database="simargl",
                user="postgres", password="postgres", project_id="sonar")

    # from connection URL:
    get_backend_from_url("postgresql://postgres:postgres@localhost/simargl", project_id="sonar")
"""
from __future__ import annotations
from .numpy_backend import NumpyBackend


def get_backend(backend_type: str = "numpy", **kwargs):
    if backend_type == "numpy":
        return NumpyBackend(**kwargs)
    if backend_type in ("postgres", "postgresql"):
        from .postgres_backend import PostgresBackend
        return PostgresBackend(**kwargs)
    raise ValueError(f"Unknown backend '{backend_type}'. Use 'numpy' or 'postgres'.")


def get_backend_from_url(url: str, project_id: str = "default"):
    """Parse postgresql://user:pass@host:port/dbname and return PostgresBackend."""
    from urllib.parse import urlparse
    p = urlparse(url)
    if p.scheme not in ("postgres", "postgresql"):
        raise ValueError(f"Expected postgresql:// URL, got: {url}")
    from .postgres_backend import PostgresBackend
    return PostgresBackend(
        host=p.hostname or "localhost",
        port=p.port or 5432,
        database=p.path.lstrip("/") or "simargl",
        user=p.username or "postgres",
        password=p.password or "",
        project_id=project_id,
    )


def make_backend(
    backend_type: str = "numpy",
    store_dir: str = ".simargl",
    project_id: str = "default",
    db_url: str | None = None,
):
    """Unified factory used by indexer, searcher, mcp_server, cli.

    Priority: db_url > backend_type.
    db_url=postgresql://...  → PostgresBackend (ignores store_dir)
    backend_type=numpy       → NumpyBackend (uses store_dir)
    backend_type=postgres    → PostgresBackend via default localhost config
    """
    if db_url:
        return get_backend_from_url(db_url, project_id=project_id)
    return get_backend(backend_type, store_dir=store_dir, project_id=project_id)
