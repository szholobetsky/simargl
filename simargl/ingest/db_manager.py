"""Database manager for simargl ingest.

Tables:
  COMMITS — one row per (sha, file) pair extracted from git
  TASKS   — one row per unique task key, with title/description/comments
"""

import sqlite3
import logging
from typing import List, Tuple, Optional


class DatabaseManager:
    """Manages SQLite database operations for commit and task data."""

    def __init__(self, db_file: str):
        self.db_file = db_file
        self.logger = logging.getLogger(__name__)

    def create_tables(self, has_tasks: bool = True):
        """Create COMMITS (and optionally TASKS) tables if they don't exist."""
        conn = sqlite3.connect(self.db_file)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS COMMITS (
                    ID          INTEGER PRIMARY KEY,
                    SHA         TEXT,
                    AUTHOR_NAME TEXT,
                    AUTHOR_EMAIL TEXT,
                    CMT_DATE    TEXT,
                    MESSAGE     BLOB,
                    PATH        BLOB,
                    DIFF        BLOB,
                    TASK_NAME   TEXT
                )
            """)
            if has_tasks:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS TASKS (
                        ID          INTEGER PRIMARY KEY AUTOINCREMENT,
                        NAME        TEXT UNIQUE,
                        TITLE       TEXT,
                        DESCRIPTION TEXT,
                        COMMENTS    TEXT
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS TASK_NAME_INDX ON TASKS (NAME ASC)")
            conn.commit()
        finally:
            conn.close()

    # ------------------------------------------------------------------ COMMIT

    def insert_commit_data(self, commit_id: int, sha: str, author_name: str,
                           author_email: str, date: str, message: str,
                           path: str, diff: str):
        conn = sqlite3.connect(self.db_file)
        try:
            conn.execute(
                "INSERT OR IGNORE INTO COMMITS"
                "(ID, SHA, AUTHOR_NAME, AUTHOR_EMAIL, CMT_DATE, MESSAGE, PATH, DIFF) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (commit_id, sha, author_name, author_email, date, message, path, diff),
            )
            conn.commit()
        finally:
            conn.close()

    def insert_commit_data_batch(self, data_list: List[Tuple]):
        conn = sqlite3.connect(self.db_file)
        try:
            batch_size = 200
            for i in range(0, len(data_list), batch_size):
                conn.executemany(
                    "INSERT OR IGNORE INTO COMMITS"
                    "(ID, SHA, AUTHOR_NAME, AUTHOR_EMAIL, CMT_DATE, MESSAGE, PATH, DIFF) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    data_list[i:i + batch_size],
                )
                conn.commit()
        finally:
            conn.close()

    def commit_count(self) -> int:
        conn = sqlite3.connect(self.db_file)
        try:
            return conn.execute("SELECT COUNT(*) FROM COMMITS").fetchone()[0]
        finally:
            conn.close()

    def update_task_name_in_commit(self, commit_id: int, task_name: str):
        conn = sqlite3.connect(self.db_file)
        try:
            conn.execute(
                "UPDATE COMMITS SET TASK_NAME = ? WHERE ID = ?",
                (task_name, commit_id),
            )
            conn.commit()
        finally:
            conn.close()

    def update_task_name_by_sha(self, sha: str, task_name: str):
        conn = sqlite3.connect(self.db_file)
        try:
            conn.execute(
                "UPDATE COMMITS SET TASK_NAME = ? WHERE SHA = ? AND TASK_NAME IS NULL",
                (task_name, sha),
            )
            conn.commit()
        finally:
            conn.close()

    def get_commits_for_extraction(self) -> List[Tuple]:
        """Return all (id, message) rows for task-name extraction."""
        conn = sqlite3.connect(self.db_file)
        try:
            return conn.execute("SELECT ID, MESSAGE FROM COMMITS").fetchall()
        finally:
            conn.close()

    def get_distinct_task_names(self) -> List[str]:
        conn = sqlite3.connect(self.db_file)
        try:
            rows = conn.execute(
                "SELECT DISTINCT TASK_NAME FROM COMMITS "
                "WHERE TASK_NAME IS NOT NULL ORDER BY TASK_NAME"
            ).fetchall()
            return [r[0] for r in rows]
        finally:
            conn.close()

    # ------------------------------------------------------------------ TASKS

    def insert_task(self, task_name: str):
        conn = sqlite3.connect(self.db_file)
        try:
            conn.execute("INSERT OR IGNORE INTO TASKS (NAME) VALUES (?)", (task_name,))
            conn.commit()
        finally:
            conn.close()

    def get_tasks_without_details(self) -> List[str]:
        conn = sqlite3.connect(self.db_file)
        try:
            rows = conn.execute(
                "SELECT NAME FROM TASKS WHERE TITLE IS NULL AND NAME IS NOT NULL"
            ).fetchall()
            return [r[0] for r in rows]
        finally:
            conn.close()

    def update_task_details(self, task_name: str, title: str,
                            description: str, comments: str):
        conn = sqlite3.connect(self.db_file)
        try:
            conn.execute(
                "UPDATE TASKS SET TITLE=?, DESCRIPTION=?, COMMENTS=? WHERE NAME=?",
                (title, description, comments, task_name),
            )
            conn.commit()
        finally:
            conn.close()

    def upsert_task_with_details(self, name: str, title: str,
                                  description: str, comments: str):
        conn = sqlite3.connect(self.db_file)
        try:
            conn.execute(
                "INSERT INTO TASKS (NAME, TITLE, DESCRIPTION, COMMENTS) VALUES (?,?,?,?) "
                "ON CONFLICT(NAME) DO UPDATE SET "
                "TITLE=excluded.TITLE, DESCRIPTION=excluded.DESCRIPTION, COMMENTS=excluded.COMMENTS",
                (name, title, description, comments),
            )
            conn.commit()
        finally:
            conn.close()

    def bulk_upsert_tasks(self, tasks: List[Tuple]):
        conn = sqlite3.connect(self.db_file)
        try:
            batch_size = 200
            for i in range(0, len(tasks), batch_size):
                conn.executemany(
                    "INSERT INTO TASKS (NAME, TITLE, DESCRIPTION, COMMENTS) VALUES (?,?,?,?) "
                    "ON CONFLICT(NAME) DO UPDATE SET "
                    "TITLE=excluded.TITLE, DESCRIPTION=excluded.DESCRIPTION, COMMENTS=excluded.COMMENTS",
                    tasks[i:i + batch_size],
                )
                conn.commit()
        finally:
            conn.close()
