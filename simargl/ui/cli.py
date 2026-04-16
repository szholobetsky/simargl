"""CLI entry point.

Usage:
  simargl init                                       # wizard: create .simargl/project.yaml
  simargl ingest [--phase git|tasks] [--force]       # extract commits + fetch tasks
  simargl index files <path> [--project P] [--model M]
  simargl index units [--project P] [--model M] [--mode auto|tasks|commits]
  simargl search "query" [--mode task|file|aggr] [--sort rank|freq] [--project P]
  simargl status [--project P]
  simargl vacuum [--project P]
  simargl ui [--port 7861]
  simargl serve [--http --port 8765]
"""
from __future__ import annotations

import argparse
import sys


def _add_backend_args(p):
    p.add_argument("--backend", default="numpy", choices=["numpy", "postgres"],
                   help="Vector backend (default: numpy)")
    p.add_argument("--db-url", default=None,
                   help="PostgreSQL URL: postgresql://user:pass@host/db")
    p.add_argument("--store-dir", default=".simargl")


def _resolve_env_token(value: str) -> str:
    """Expand ${VAR} references to environment variable values."""
    import os, re
    if value and value.startswith("${") and value.endswith("}"):
        var = value[2:-1]
        return os.environ.get(var, "")
    return value or ""


def _load_project_yaml(store_dir: str = ".simargl") -> dict:
    import os, yaml
    path = os.path.join(store_dir, "project.yaml")
    if not os.path.exists(path):
        print(f"project.yaml not found at {path}")
        print("Run: simargl init")
        return None
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_ingest_state(state_path: str) -> dict:
    import os, yaml
    if os.path.exists(state_path):
        with open(state_path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def _save_ingest_state(state_path: str, state: dict):
    import yaml
    with open(state_path, "w", encoding="utf-8") as f:
        yaml.dump(state, f, default_flow_style=False, allow_unicode=True)


def _fresh_ingest_state() -> dict:
    return {
        "git":   {"status": "pending"},
        "tasks": {"status": "pending", "fetched": 0, "last_key": None},
    }


def main():
    parser = argparse.ArgumentParser(prog="simargl")
    sub = parser.add_subparsers(dest="cmd")

    # init
    sub.add_parser("init", help="Wizard: create .simargl/project.yaml")

    # ingest
    ing = sub.add_parser("ingest", help="Extract commits + fetch task details")
    ing.add_argument("--phase", choices=["git", "tasks"], default=None,
                     help="Run only one phase (default: both)")
    ing.add_argument("--force", action="store_true",
                     help="Ignore checkpoint, start from scratch")
    ing.add_argument("--store-dir", default=".simargl")

    # index
    idx = sub.add_parser("index")
    idx_sub = idx.add_subparsers(dest="idx_cmd")

    idx_files = idx_sub.add_parser("files")
    idx_files.add_argument("path")
    idx_files.add_argument("--project", default="default")
    idx_files.add_argument("--model", default=None)
    idx_files.add_argument("--chunk-size", type=int, default=400)
    idx_files.add_argument("--full", action="store_true",
                           help="Re-embed all files, ignore mtime")
    _add_backend_args(idx_files)

    idx_units = idx_sub.add_parser("units")
    idx_units.add_argument("db_path", nargs="?", default="units.db")
    idx_units.add_argument("--project", default="default")
    idx_units.add_argument("--model", default=None)
    idx_units.add_argument("--mode", default="auto", choices=["auto", "tasks", "commits"])
    idx_units.add_argument("--last", type=int, default=None, metavar="N",
                           help="Index only the N most recent tasks/commits (by commit date)")
    _add_backend_args(idx_units)

    # download
    dl = sub.add_parser("download", help="Download default embedding model (bge-small)")
    dl.add_argument("--model", default=None, help="Model key to download (default: bge-small)")

    # search
    srch = sub.add_parser("search", help="Search the index from terminal")
    srch.add_argument("query")
    srch.add_argument("--mode", default="task", choices=["task", "file", "aggr"])
    srch.add_argument("--sort", default="rank", choices=["rank", "freq"])
    srch.add_argument("--project", default="default")
    srch.add_argument("--top-n", type=int, default=10)
    srch.add_argument("--top-k", type=int, default=10)
    srch.add_argument("--diff", action="store_true", help="Include diffs in output")
    _add_backend_args(srch)

    # status
    stat = sub.add_parser("status")
    stat.add_argument("--project", default="default")
    _add_backend_args(stat)

    # vacuum
    vac = sub.add_parser("vacuum", help="Compact index: remove soft-deleted vectors")
    vac.add_argument("--project", default="default")
    _add_backend_args(vac)

    # ui (Gradio)
    ui_p = sub.add_parser("ui", help="Start Gradio web UI")
    ui_p.add_argument("--port", type=int, default=7861)
    ui_p.add_argument("--host", default="0.0.0.0")
    ui_p.add_argument("--store-dir", default=".simargl")

    # about
    sub.add_parser("about", help="Show version and authorship")

    # serve (MCP)
    srv = sub.add_parser("serve", help="Start MCP server")
    srv.add_argument("--http", action="store_true")
    srv.add_argument("--host", default="0.0.0.0")
    srv.add_argument("--port", type=int, default=8765)
    _add_backend_args(srv)

    args = parser.parse_args()

    if args.cmd == "init":
        import os, yaml
        store_dir = ".simargl"
        yaml_path = os.path.join(store_dir, "project.yaml")

        if os.path.exists(yaml_path):
            ans = input(f"{yaml_path} already exists. Overwrite? [y/N]: ").strip().lower()
            if ans != "y":
                print("[cancelled]")
                sys.exit(0)

        print("\nsimargl init\n")
        default_name = os.path.basename(os.path.abspath("."))
        name = input(f"Project name [{default_name}]: ").strip() or default_name
        repo = input("Git repo path [. = current folder]: ").strip() or "."
        branch = input("Branch [main]: ").strip() or "main"
        since = input("Fetch history since (YYYY-MM-DD, Enter = full history): ").strip()

        print()
        tracker = input(
            "Task tracker? [jira/github/youtrack/gitlab, Enter = none]: "
        ).strip().lower() or "none"

        cfg: dict = {
            "project": {"name": name, "db": "units.db"},
            "git": {"repo": repo, "branch": branch},
            "ingest": {"batch_size": 100, "rate_limit_delay": 1.0},
        }
        if since:
            cfg["git"]["since"] = since

        if tracker == "jira":
            jira_url    = input("Jira URL: ").strip()
            jira_proj   = input("Jira project key (e.g. KAFKA): ").strip()
            jira_conn   = input("Connector [api/html/selenium, Enter = api]: ").strip() or "api"
            jira_token  = input("Token (Enter to skip for public instances): ").strip()
            tasks_cfg: dict = {"source": "jira", "jira_url": jira_url,
                               "jira_project": jira_proj, "jira_connector": jira_conn}
            if jira_token:
                tasks_cfg["jira_token"] = jira_token
            cfg["tasks"] = tasks_cfg

        elif tracker == "github":
            gh_owner  = input("GitHub owner (org or user): ").strip()
            gh_repo   = input("GitHub repo: ").strip()
            gh_token  = input("Token (Enter to skip, but only 60 req/h without): ").strip()
            gh_mask   = input("Commit pattern [generic/django/broad, Enter = generic]: ").strip() or "generic"
            tasks_cfg = {"source": "github", "github_owner": gh_owner,
                         "github_repo": gh_repo, "commit_mask": gh_mask}
            if gh_token:
                tasks_cfg["github_token"] = gh_token
            cfg["tasks"] = tasks_cfg

        elif tracker == "youtrack":
            yt_url    = input("YouTrack URL [https://youtrack.jetbrains.com]: ").strip() \
                        or "https://youtrack.jetbrains.com"
            yt_proj   = input("YouTrack project key (e.g. KT): ").strip()
            yt_token  = input("Token (Enter to skip for public instances): ").strip()
            tasks_cfg = {"source": "youtrack", "youtrack_url": yt_url,
                         "youtrack_project": yt_proj}
            if yt_token:
                tasks_cfg["youtrack_token"] = yt_token
            cfg["tasks"] = tasks_cfg

        elif tracker == "gitlab":
            gl_url    = input("GitLab URL [https://gitlab.com]: ").strip() or "https://gitlab.com"
            gl_proj   = input("GitLab project (org/repo): ").strip()
            gl_token  = input("Token (required for comments, Enter to skip): ").strip()
            tasks_cfg = {"source": "gitlab", "gitlab_url": gl_url, "gitlab_project": gl_proj}
            if gl_token:
                tasks_cfg["gitlab_token"] = gl_token
            cfg["tasks"] = tasks_cfg

        os.makedirs(store_dir, exist_ok=True)
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        print(f"\nCreated {yaml_path}")
        has_tasks = "tasks" in cfg
        print(f"Mode: {'full (git + tasks)' if has_tasks else 'commits-only'}")
        print("Next: simargl ingest")

    elif args.cmd == "ingest":
        import os, datetime as _dt
        cfg = _load_project_yaml(args.store_dir)
        if cfg is None:
            sys.exit(1)

        db_path    = cfg["project"]["db"]
        git_cfg    = cfg.get("git", {})
        tasks_cfg  = cfg.get("tasks")
        ingest_cfg = cfg.get("ingest", {})
        has_tasks  = tasks_cfg is not None

        state_path = os.path.join(args.store_dir, "ingest_state.yaml")
        state = _fresh_ingest_state() if args.force else _load_ingest_state(state_path)
        if not state:
            state = _fresh_ingest_state()

        def save_state(updated_tasks_state=None):
            if updated_tasks_state is not None:
                state["tasks"] = updated_tasks_state
            _save_ingest_state(state_path, state)

        from ..ingest.db_manager import DatabaseManager
        from ..ingest.git_connector import GitConnector

        db = DatabaseManager(db_path)
        db.create_tables(has_tasks=has_tasks)

        # ── Phase 1: git ──────────────────────────────────────────────────
        run_git = (args.phase is None or args.phase == "git")
        if run_git and state.get("git", {}).get("status") != "done":
            print("\n[1/2] Extracting commits from Git repository...")
            git_conn = GitConnector(git_cfg.get("repo", "."))
            git_conn.extract_commits(
                db,
                branch=git_cfg.get("branch", "main"),
                since=git_cfg.get("since"),
            )
            state["git"] = {"status": "done",
                            "completed_at": _dt.datetime.now().isoformat()}
            save_state()
            print(f"      Done. Total rows: {db.commit_count()}")
        elif run_git:
            print("[1/2] Git already complete (checkpoint). Skipping.")
        else:
            print("[1/2] Git phase skipped (--phase tasks).")

        # ── Phase 2: tasks ────────────────────────────────────────────────
        run_tasks = (args.phase is None or args.phase == "tasks")
        if run_tasks and has_tasks:
            if state.get("tasks", {}).get("status") == "done":
                print("[2/2] Tasks already complete (checkpoint). Skipping.")
            else:
                print("\n[2/2] Extracting task references from commits...")
                from ..ingest.task_extractor import TaskExtractor
                from ..ingest.task_fetcher import TaskFetcher

                # Determine commit pattern
                mask = tasks_cfg.get("commit_mask", "simple")
                extractor = TaskExtractor(mask)
                extractor.process_all_commits(db)

                print("      Fetching task details from tracker...")
                tracker_cfg = {k: _resolve_env_token(v) if isinstance(v, str) else v
                               for k, v in tasks_cfg.items()}
                fetcher = TaskFetcher(
                    tracker_type=tasks_cfg["source"],
                    tracker_config=tracker_cfg,
                )
                tasks_state = state.get("tasks", {"fetched": 0, "last_key": None})
                fetcher.fetch_all_tasks(
                    db,
                    rate_limit_delay=float(ingest_cfg.get("rate_limit_delay", 1.0)),
                    batch_size=int(ingest_cfg.get("batch_size", 100)),
                    state=tasks_state,
                    state_saver=lambda s: save_state(s),
                )
                state["tasks"] = {**tasks_state, "status": "done"}
                save_state()
                print("      Task fetching complete.")
        elif run_tasks and not has_tasks:
            print("[2/2] No task tracker configured — commits-only mode.")
        else:
            print("[2/2] Tasks phase skipped (--phase git).")

        print(f"\nIngest complete. Run: simargl index units {db_path}")

    elif args.cmd == "download":
        from ..config import MODELS, DEFAULT_MODEL
        from ..embedder import get_embedder
        key = args.model or DEFAULT_MODEL
        if key not in MODELS:
            print(f"Unknown model '{key}'. Known: {list(MODELS)}")
            sys.exit(1)
        print(f"Downloading {key} ({MODELS[key]['name']})...")
        get_embedder(key)
        print("Done.")

    elif args.cmd == "index" and args.idx_cmd == "files":
        from ..indexer import index_files
        from ..config import DEFAULT_MODEL
        result = index_files(
            args.path,
            model_key=args.model or DEFAULT_MODEL,
            project_id=args.project,
            store_dir=args.store_dir,
            chunk_size=args.chunk_size,
            full=args.full,
            backend_type=args.backend,
            db_url=args.db_url,
        )
        print(f"Done. New: {result['files_new']}  Modified: {result['files_modified']}  "
              f"Deleted: {result['files_deleted']}  Chunks: {result['chunks_added']}")

    elif args.cmd == "index" and args.idx_cmd == "units":
        from ..indexer import index_units
        from ..config import DEFAULT_MODEL
        result = index_units(
            args.db_path,
            model_key=args.model or DEFAULT_MODEL,
            project_id=args.project,
            store_dir=args.store_dir,
            mode=args.mode,
            last=args.last,
            backend_type=args.backend,
            db_url=args.db_url,
        )
        last_str = f"  Last: {result['last']}" if result['last'] else ""
        print(f"Done. Units: {result['units_indexed']}  Mode: {result['mode_used']}{last_str}")

    elif args.cmd == "search":
        from ..searcher import search
        try:
            result = search(
                args.query,
                mode=args.mode, sort=args.sort,
                top_n=args.top_n, top_k=args.top_k,
                include_diff=args.diff,
                project_id=args.project,
                store_dir=args.store_dir,
                backend_type=args.backend,
                db_url=args.db_url,
            )
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

        print(f"Query: {args.query}  mode={args.mode}" +
              (f"  sort={args.sort}" if args.mode == "task" else ""))
        print()
        print("Files:")
        for f in result["files"]:
            print(f"  {f['score']:.3f}  {f['path']}  [{f['module']}]")
        if result["modules"]:
            print("\nModules:")
            for m in result["modules"]:
                print(f"  {m['score']:.3f}  {m['module']}")
        if result["units"]:
            print("\nSimilar units:")
            for u in result["units"][:5]:
                print(f"  [{u['similarity']:.3f}] {u['unit_id']} — {u['text_preview'][:80]}")
                if u.get("diff"):
                    print(f"    ---\n{u['diff'][:400]}")

    elif args.cmd == "status":
        from ..backends import make_backend
        try:
            backend = make_backend(args.backend, store_dir=args.store_dir,
                                   project_id=args.project, db_url=args.db_url)
            s = backend.stats()
            print(f"Project:       {args.project}")
            print(f"Backend:       {args.backend}")
            print(f"Model:         {s.get('model_key', '?')}  dim={s.get('dim', '?')}")
            print(f"Files:         {s.get('files', 0)}  ({s.get('chunks', 0)} chunks"
                  + (f", {s.get('deleted_chunks', 0)} deleted" if s.get('deleted_chunks') else "") + ")")
            unit_last = s.get('unit_last')
            last_str = f"  last={unit_last}" if unit_last else ""
            print(f"Units:         {s.get('units', 0)}  (mode={s.get('unit_mode', '?')}{last_str})")
            print(f"Indexed:       {s.get('indexed_at', '?')}")
        except FileNotFoundError as e:
            print(str(e))
            sys.exit(1)

    elif args.cmd == "vacuum":
        from ..backends import make_backend
        try:
            backend = make_backend(args.backend, store_dir=args.store_dir,
                                   project_id=args.project, db_url=args.db_url)
            meta = backend.load_meta()
            result = backend.vacuum_files(meta["dim"])
            print(f"Vacuum complete.")
            print(f"  Chunks before : {result['before']}")
            print(f"  Chunks after  : {result['after']}")
            print(f"  Reclaimed     : {result['reclaimed_mb']} MB")
        except FileNotFoundError as e:
            print(str(e))
            sys.exit(1)

    elif args.cmd == "ui":
        from .gradio_app import main as ui_main
        ui_main(port=args.port, host=args.host, store_dir=args.store_dir)

    elif args.cmd == "serve":
        import sys as _sys
        _sys.argv = ["simargl-mcp"]
        if args.http:
            _sys.argv += ["--http", "--host", args.host, "--port", str(args.port)]
        if args.backend != "numpy":
            _sys.argv += ["--backend", args.backend]
        if args.db_url:
            _sys.argv += ["--db-url", args.db_url]
        from ..mcp_server import main as mcp_main
        mcp_main()

    elif args.cmd == "about":
        print("simargl — Semantic Index: Map Artifacts, Retrieve from Git Log")
        print()
        print("(c) 2026 Stanislav Zholobetskyi")
        print("Institute for Information Recording, National Academy of Sciences of Ukraine, Kyiv")
        print("PhD research: \u00abIntelligent Technology for Software Development and Maintenance Support\u00bb")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
