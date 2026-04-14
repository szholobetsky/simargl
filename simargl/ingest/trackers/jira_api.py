"""Jira REST API connector — works for public instances without a token."""

import requests
import logging
from typing import Tuple


class JiraApiConnector:
    def __init__(self, jira_url: str, token: str = None):
        self.jira_url = jira_url.rstrip('/')
        self.logger = logging.getLogger(__name__)
        self.headers = {'Accept': 'application/json'}
        if token:
            self.headers['Authorization'] = f'Bearer {token}'

    def fetch_task_details(self, task_key: str) -> Tuple[str, str, str]:
        url = f"{self.jira_url}/rest/api/3/issue/{task_key}"
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            title = data.get('fields', {}).get('summary', '')
            description = str(data.get('fields', {}).get('description', ''))
            comments_data = data.get('fields', {}).get('comment', {}).get('comments', [])
            comments = ' '.join(c.get('body', '') for c in comments_data)
            return title, description, comments
        except Exception as e:
            self.logger.error(f"Error fetching {task_key}: {e}")
            return '', '', ''
