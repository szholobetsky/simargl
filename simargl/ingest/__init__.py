"""simargl.ingest — data gathering: git extraction + task tracker fetching."""
from .db_manager import DatabaseManager
from .git_connector import GitConnector
from .task_extractor import TaskExtractor
from .task_fetcher import TaskFetcher

__all__ = ["DatabaseManager", "GitConnector", "TaskExtractor", "TaskFetcher"]
