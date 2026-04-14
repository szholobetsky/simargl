"""Git connector — extracts commits from a local repository into the COMMIT table."""

import logging
from datetime import datetime, timezone
from tqdm import tqdm


class GitConnector:
    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.logger = logging.getLogger(__name__)

    def extract_commits(self, db_manager, branch: str = 'main',
                        since: str = None, print_content: bool = False):
        """Extract all commits (with per-file diffs) into db_manager.

        Args:
            db_manager: DatabaseManager instance
            branch:     Branch to walk (default: main)
            since:      ISO date string 'YYYY-MM-DD' — skip commits older than this
            print_content: Print each row to console (debug)
        """
        try:
            import git
        except ImportError:
            raise ImportError("gitpython is required: pip install simargl[ingest]")

        since_dt = None
        if since:
            since_dt = datetime.fromisoformat(since).replace(tzinfo=timezone.utc)

        try:
            repo = git.Repo(self.repo_path)
        except Exception as e:
            raise RuntimeError(f"Cannot open git repo at '{self.repo_path}': {e}")

        # Try given branch, fall back to HEAD
        try:
            commits = list(repo.iter_commits(branch))
        except git.exc.GitCommandError:
            self.logger.warning(f"Branch '{branch}' not found, using HEAD")
            commits = list(repo.iter_commits('HEAD'))

        if since_dt:
            commits = [c for c in commits
                       if c.committed_datetime.astimezone(timezone.utc) >= since_dt]
            self.logger.info(f"After since={since}: {len(commits)} commits remain")

        self.logger.info(f"Processing {len(commits)} commits from '{branch}'")
        counter = 0

        for commit in tqdm(commits, desc="Extracting commits", unit="commit"):
            sha = commit.hexsha
            author_name = commit.author.name or ""
            author_email = commit.author.email or ""
            date = commit.committed_datetime.isoformat()
            message = commit.message or ""

            parent = commit.parents[0] if commit.parents else git.NULL_TREE
            try:
                diffs = commit.diff(parent, create_patch=True)
            except Exception as e:
                self.logger.warning(f"Could not diff {sha[:8]}: {e}")
                continue

            for diff in diffs:
                counter += 1
                path = diff.a_path or diff.b_path or ""
                try:
                    diff_content = diff.diff.decode('utf-8', errors='ignore') if diff.diff else ""
                except Exception:
                    diff_content = ""

                db_manager.insert_commit_data(
                    counter, sha, author_name, author_email,
                    date, message, path, diff_content,
                )

                if print_content:
                    print(f"[{counter}] {sha[:8]} {path}")

        self.logger.info(f"Extracted {counter} commit-file rows")
