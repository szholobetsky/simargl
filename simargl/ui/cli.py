"""CLI entry point.

Usage:
  simargl index files <path> [--project P] [--model M]
  simargl index units [--project P] [--model M] [--mode auto|tasks|commits]
  simargl search "query" [--mode task|file|aggr] [--sort rank|freq] [--project P]
  simargl status [--project P]
  simargl vacuum [--project P]
  simargl ui [--port 7861]
  simargl serve [--http --port 8765]

The dataset the indexes are built from (project.yaml, the ingest, export, plaintext) is mokosh's:
`mokosh ui`, or `mokosh init` / `mokosh ingest` / `mokosh export` / `mokosh plaintext`.
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


def _remember_store(store_dir):
    """Remember a store machine-wide (~/.simargl/stores.json), so the web UI lists it from anywhere."""
    try:
        from .server import _remember, _is_store
        if _is_store(store_dir):
            _remember(store_dir)
    except Exception:
        pass


def main():
    # a Windows console (cp1251, cp1252) cannot print every character of the help (λ, α):
    # UTF-8 where the stream allows it, and never a crash on one that does not fit
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    parser = argparse.ArgumentParser(prog="simargl")
    sub = parser.add_subparsers(dest="cmd")

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
    dl = sub.add_parser("download", help="Get an embedding model ready: an ollama:// model is pulled into Ollama, "
                                         "a local one downloaded (default: the default model, "
                                         "ollama://granite-embedding:30m)")
    dl.add_argument("--model", default=None, help="Model key (default: ollama://granite-embedding:30m)")

    # search
    srch = sub.add_parser("search", help="Search the index from terminal")
    srch.add_argument("query", help="Query text, or '-' to read from stdin")
    srch.add_argument("--mode", default="task", choices=["task", "file", "aggr", "refine"])
    srch.add_argument("--sort", default="rank", choices=["rank", "freq"])
    srch.add_argument("--project", default="default")
    srch.add_argument("--top-n", type=int, default=10)
    srch.add_argument("--top-k", type=int, default=10)
    srch.add_argument("--diff", action="store_true", help="Include diffs in output")
    srch.add_argument("--no-blackholes", action="store_true",
                      help="Exclude blackhole files from results")
    srch.add_argument("--coverage-penalty", type=float, default=0.0, metavar="λ",
                      help="Re-ranking penalty for omnipresent files (e.g. 0.2). "
                           "Run 'simargl blackhole --method coverage_float' first.")
    srch.add_argument("--score-blend", type=float, default=1.0, metavar="α",
                      help="Topic concentration blend: α*max+(1-α)*mean per file. "
                           "1.0=off (default), 0.5-0.7 pushes down broad documents.")
    srch.add_argument("--refine-top-k", type=int, default=10,
                      help="refine mode: commits used for query expansion (default: 10)")
    srch.add_argument("--refine-top-m", type=int, default=8,
                      help="refine mode: new terms added to query (default: 8)")
    srch.add_argument("--format", default="text",
                      choices=["text", "json", "paths", "modules"],
                      help="Output format: text (default), json, paths (files only), modules (modules only)")
    _add_backend_args(srch)

    # rrf
    rrf_p = sub.add_parser("rrf", help="Merge search results from multiple modes/projects (RRF)")
    rrf_p.add_argument("query", help="Query text, or '-' to read from stdin")
    rrf_p.add_argument("--sources", default="task:default,file:default",
                       metavar="SOURCES",
                       help="Comma-separated mode:project_id pairs  "
                            "(e.g. task:default,file:jina)")
    rrf_p.add_argument("--top-n", type=int, default=5)
    rrf_p.add_argument("--top-k", type=int, default=10,
                       help="Candidates per source before merge (default: 10)")
    rrf_p.add_argument("--k", type=int, default=60,
                       help="RRF damping constant (default: 60)")
    rrf_p.add_argument("--sort", default="freq", choices=["rank", "freq"],
                       help="Sort for task sources (default: freq)")
    rrf_p.add_argument("--score-blend", type=float, default=1.0, metavar="α")
    rrf_p.add_argument("--format", default="text", choices=["text", "json", "paths"])
    _add_backend_args(rrf_p)

    # blackhole
    bh = sub.add_parser("blackhole", help="Detect and mark blackhole files (semantic noise)")
    bh.add_argument("--method", default="centroid",
                    choices=["centroid", "coverage", "coverage_float"],
                    help="centroid: fast binary; coverage: binary by query fraction; "
                         "coverage_float: store float scores for re-ranking (recommended)")
    bh.add_argument("--threshold", type=float, default=None,
                    help="Threshold (centroid: 0.85; coverage: 0.3 — fraction of queries)")
    bh.add_argument("--n-queries", type=int, default=100,
                    help="Number of specific test queries for coverage method (default: 100)")
    bh.add_argument("--top-k", type=int, default=20,
                    help="Top-k file results per query for coverage method (default: 20)")
    bh.add_argument("--project", default="default")
    bh.add_argument("--list", action="store_true", help="List marked blackhole paths")
    _add_backend_args(bh)

    # retrieve
    ret = sub.add_parser("retrieve", help="Retrieve text chunks ready for LLM context injection")
    ret.add_argument("query")
    ret.add_argument("--mode", default="file", choices=["file", "task", "aggr"])
    ret.add_argument("--top-n", type=int, default=5)
    ret.add_argument("--diff", action="store_true", help="Include diffs (task mode)")
    ret.add_argument("--no-blackholes", action="store_true",
                     help="Exclude blackhole files from results")
    ret.add_argument("--coverage-penalty", type=float, default=0.0, metavar="λ",
                     help="Re-ranking penalty for omnipresent files (e.g. 0.2)")
    ret.add_argument("--score-blend", type=float, default=1.0, metavar="α",
                     help="Topic concentration blend: α*max+(1-α)*mean (e.g. 0.7)")
    ret.add_argument("--files", default=None,
                     help="Comma-separated file paths to fetch content (aggr step 2)")
    ret.add_argument("--source", default=None, metavar="DIR",
                     help="Directory where indexed files live (for webindex projects)")
    ret.add_argument("--project", default="default")
    _add_backend_args(ret)

    # status
    stat = sub.add_parser("status")
    stat.add_argument("--project", default="default")
    _add_backend_args(stat)

    # vacuum
    vac = sub.add_parser("vacuum", help="Compact index: remove soft-deleted vectors")
    vac.add_argument("--project", default="default")
    _add_backend_args(vac)

    # ui (Flask; --gradio for the older one)
    ui_p = sub.add_parser("ui", help="Start the web UI (Flask; --gradio for the older Gradio UI)")
    ui_p.add_argument("--port", type=int, default=None, help="Port (default 8099; Gradio 7861)")
    ui_p.add_argument("--host", default=None,
                      help="Address to listen on (default 127.0.0.1; 0.0.0.0 to open it to other devices)")
    ui_p.add_argument("--store-dir", default=".simargl")
    ui_p.add_argument("--root", default=None, help="Folder to look for .simargl stores under (default: current directory)")
    ui_p.add_argument("--gradio", action="store_true", help="The older Gradio UI (needs: pip install simargl[gradio])")
    ui_p.add_argument("--lang",  default=None, help="Gradio UI language (en/uk; default from config)")
    ui_p.add_argument("--theme", default=None, help="Gradio UI theme (Monochrome/Soft/Glass/Ocean/Default)")

    # about
    sub.add_parser("about", help="Show version and authorship")

    # serve (MCP)
    srv = sub.add_parser("serve", help="Start MCP server")
    srv.add_argument("--http", action="store_true")
    srv.add_argument("--host", default="0.0.0.0")
    srv.add_argument("--port", type=int, default=8765)
    _add_backend_args(srv)

    args = parser.parse_args()

    if args.cmd == "download":
        from ..config import MODELS, DEFAULT_MODEL
        from ..embedder import get_embedder, ollama_pull
        key = args.model or DEFAULT_MODEL
        if key.startswith("ollama://"):
            ollama_pull(key, log=print)
            print("Done.")
        elif key in MODELS:
            print(f"Downloading {key} ({MODELS[key]['name']})...")
            try:
                get_embedder(key)
            except RuntimeError as e:
                print(e)
                sys.exit(1)
            print("Done.")
        else:
            print(f"Unknown model '{key}'. Known local models: {list(MODELS)}; or ollama://<model>")
            sys.exit(1)

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
        _remember_store(args.store_dir)

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
        _remember_store(args.store_dir)

    elif args.cmd == "search":
        import json as _json
        from ..searcher import search

        query = sys.stdin.read().strip() if args.query == "-" else args.query
        if not query:
            print("Error: empty query", file=sys.stderr)
            sys.exit(1)

        try:
            result = search(
                query,
                mode=args.mode, sort=args.sort,
                top_n=args.top_n, top_k=args.top_k,
                include_diff=args.diff,
                exclude_blackholes=args.no_blackholes,
                coverage_penalty=args.coverage_penalty,
                score_blend=args.score_blend,
                refine_top_k=args.refine_top_k,
                refine_top_m=args.refine_top_m,
                project_id=args.project,
                store_dir=args.store_dir,
                backend_type=args.backend,
                db_url=args.db_url,
            )
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

        fmt = args.format

        if fmt == "json":
            print(_json.dumps(result, ensure_ascii=False, indent=2))

        elif fmt == "paths":
            for f in result["files"]:
                print(f["path"])

        elif fmt == "modules":
            for m in result["modules"]:
                print(m["module"])

        else:  # text
            print(f"Query: {query}  mode={args.mode}" +
                  (f"  sort={args.sort}" if args.mode == "task" else ""), file=sys.stderr)
            if result.get("refined"):
                print(f"Expanded: {result['expanded_query']}", file=sys.stderr)
            print(file=sys.stderr)
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

    elif args.cmd == "rrf":
        import json as _json
        from ..searcher import rrf_search

        query = sys.stdin.read().strip() if args.query == "-" else args.query
        if not query:
            print("Error: empty query", file=sys.stderr)
            sys.exit(1)

        try:
            result = rrf_search(
                query,
                sources=args.sources,
                top_n=args.top_n,
                k=args.k,
                top_k=args.top_k,
                sort=args.sort,
                score_blend=args.score_blend,
                store_dir=args.store_dir,
                backend_type=args.backend,
                db_url=args.db_url,
            )
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

        if args.format == "json":
            print(_json.dumps(result, ensure_ascii=False, indent=2))
        elif args.format == "paths":
            for f in result["files"]:
                print(f["path"])
        else:
            print(f"Query:   {query}", file=sys.stderr)
            print(f"Sources: {args.sources}  k={args.k}", file=sys.stderr)
            print(file=sys.stderr)
            for sr in result["sources"]:
                err = sr.get("error", "")
                status = f"ERROR: {err}" if err else f"{len(sr['files'])} candidates"
                print(f"  [{sr['mode']}:{sr['project_id']}]  {status}", file=sys.stderr)
            print(file=sys.stderr)
            print(f"RRF top-{args.top_n}:")
            for f in result["files"]:
                print(f"  {f['score']:.6f}  {f['path']}  [{f['module']}]")
            if result["modules"]:
                print("\nModules:")
                for m in result["modules"]:
                    print(f"  {m['module']}")

    elif args.cmd == "blackhole":
        from ..backends import make_backend
        try:
            backend = make_backend(args.backend, store_dir=args.store_dir,
                                   project_id=args.project, db_url=args.db_url)
            if args.list:
                paths = sorted(backend.blackhole_paths())
                if paths:
                    print(f"Blackhole files ({len(paths)}):")
                    for p in paths:
                        print(f"  {p}")
                else:
                    print("No blackhole files marked. Run: simargl blackhole")
            else:
                meta = backend.load_meta()
                if args.method == "coverage_float":
                    result = backend.compute_file_coverage(
                        meta["dim"], n_queries=args.n_queries, top_k=args.top_k,
                    )
                    print(f"Coverage scores computed — project={args.project}")
                    print(f"  Method      : coverage_float (re-ranking, no binary filter)")
                    print(f"  Test queries: {result['n_queries']}")
                    print(f"  Top-k       : {result['top_k']}")
                    print(f"  Total paths : {result['total_paths']}")
                    print(f"  Max coverage: {result['max_coverage']:.4f}")
                    print(f"\nUse --coverage-penalty 0.2 in search/retrieve to re-rank.")
                elif args.method == "coverage":
                    threshold = args.threshold if args.threshold is not None else 0.3
                    result = backend.compute_blackholes_coverage(
                        meta["dim"], n_queries=args.n_queries,
                        threshold=threshold, top_k=args.top_k,
                    )
                    n_q = result["n_queries"]
                    print(f"Blackhole detection complete (coverage) — project={args.project}")
                    print(f"  Method     : coverage")
                    print(f"  Threshold  : {threshold} ({int(threshold * n_q)} / {n_q} queries)")
                    print(f"  Top-k      : {result['top_k']}")
                    print(f"  Total paths: {result['total_paths']}")
                    print(f"  Marked     : {result['marked']}")
                    print(f"\nRun with --list to see marked files.")
                    print(f"Use --no-blackholes in search/retrieve to exclude them.")
                else:
                    threshold = args.threshold if args.threshold is not None else 0.85
                    result = backend.compute_blackholes(meta["dim"], threshold=threshold)
                    print(f"Blackhole detection complete (centroid) — project={args.project}")
                    print(f"  Method     : centroid")
                    print(f"  Threshold  : {result['threshold']}")
                    print(f"  Total paths: {result['total_paths']}")
                    print(f"  Marked     : {result['marked']}")
                    print(f"\nRun with --list to see marked files.")
                    print(f"Use --no-blackholes in search/retrieve to exclude them.")
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.cmd == "retrieve":
        from ..searcher import retrieve
        files_list = [f.strip() for f in args.files.split(",")] if args.files else None
        try:
            text = retrieve(
                args.query,
                mode=args.mode,
                top_n=args.top_n,
                include_diff=args.diff,
                exclude_blackholes=args.no_blackholes,
                coverage_penalty=args.coverage_penalty,
                score_blend=args.score_blend,
                files_to_fetch=files_list,
                project_id=args.project,
                store_dir=args.store_dir,
                backend_type=args.backend,
                db_url=args.db_url,
                source_dir=args.source,
            )
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        sys.stdout.buffer.write((text + "\n").encode("utf-8", errors="replace"))

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
        if args.gradio:
            try:
                import gradio  # noqa: F401
            except ImportError:
                print("error: the Gradio UI needs gradio — pip install simargl[gradio]", file=sys.stderr)
                sys.exit(1)
            from .gradio_app import main as ui_main, _load_config
            cfg   = _load_config()
            lang  = args.lang  or cfg.get("lang",  "en")
            theme = args.theme or cfg.get("theme", "Monochrome")
            ui_main(port=args.port or 7861, host=args.host or "0.0.0.0", store_dir=args.store_dir,
                    lang=lang, theme=theme)
        else:
            from .server import serve
            serve(host=args.host or "127.0.0.1", port=args.port or 8099,
                  store_dir=args.store_dir, start=args.root)

    elif args.cmd == "serve":
        import sys as _sys
        _sys.argv = ["simargl-mcp"]
        if args.http:
            _sys.argv += ["--http", "--host", args.host, "--port", str(args.port)]
        if args.backend != "numpy":
            _sys.argv += ["--backend", args.backend]
        if args.db_url:
            _sys.argv += ["--db-url", args.db_url]
        try:
            import mcp  # noqa: F401
        except ImportError:
            print("error: the MCP server needs mcp — pip install simargl[mcp]", file=sys.stderr)
            sys.exit(1)
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
