"""Extracts task identifiers from commit messages using regex patterns."""

import re
import logging
from typing import Optional


# Built-in pattern presets
PATTERNS = {
    "simple":   r'^[A-Z]+-\d+',               # KAFKA-123 at start
    "bracketed": r'\[([A-Z]+-\d+)\]',          # [KAFKA-123]
    "django":   r'[Ff]ixed\s+#(\d+)',          # Fixed #123
    "generic":  r'(?:fix(?:e[sd])?|clos(?:e[sd]?)|resolv(?:e[sd]?))\s*[:#]?\s*#(\d+)',
    "broad":    r'#(\d+)',                      # any #NNN
}


class TaskExtractor:
    def __init__(self, pattern: str):
        """
        Args:
            pattern: regex string OR a preset name (simple/bracketed/django/generic/broad)
        """
        self.pattern = PATTERNS.get(pattern, pattern)
        self.logger = logging.getLogger(__name__)

    def extract_task_name(self, message: str) -> Optional[str]:
        if not message:
            return None
        match = re.search(self.pattern, message)
        if not match:
            return None
        task_name = match.group(1) if (match.lastindex and match.lastindex >= 1) else match.group(0)
        if task_name.startswith('[') and task_name.endswith(']'):
            inner = re.search(r'\[([A-Z]+-\d+)\]', task_name)
            task_name = inner.group(1) if inner else task_name
        return task_name

    def process_all_commits(self, db_manager):
        """Extract task names from all commits and populate TASK table."""
        commits = db_manager.get_commits_for_extraction()
        extracted = 0
        for commit_id, message in commits:
            task_name = self.extract_task_name(message)
            if task_name:
                db_manager.update_task_name_in_commit(commit_id, task_name)
                extracted += 1
        self.logger.info(f"Extracted {extracted} task names from {len(commits)} commits")

        for task_name in db_manager.get_distinct_task_names():
            db_manager.insert_task(task_name)
        self.logger.info("Task population complete")
