"""Table names of a task/commit SQLite database — defined by mokosh, which writes the
database; simargl only reads it. See mokosh/schema.py."""
from mokosh.schema import (COMMIT_NAMES, TASK_NAMES, commit_table, has_task_table,  # noqa: F401
                           task_table, tables)
