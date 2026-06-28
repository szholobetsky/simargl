"""Gradio web UI for simargl.

Start:
  simargl ui                  # default port 7861
  simargl ui --port 7861
  simargl ui --lang uk --theme Soft

Tabs:
  Search    — task / file / aggr / refine with all parameters
  RRF       — multi-source Reciprocal Rank Fusion
  Retrieve  — LLM-context text retrieval
  Blackhole — detect / list semantic noise files
  Status    — index stats + project config (project.yaml + ingest state)
  Admin     — vacuum / re-index files / re-index units / re-ingest
  Init      — create project.yaml via form
  Settings  — theme and language (saved to ~/.simargl/config.json, restart to apply)
  Download  — export project index as ZIP
"""
from __future__ import annotations

import json as _json
import os
import subprocess
from pathlib import Path

from . import i18n
from ..searcher import search, rrf_search, retrieve
from ..backends import make_backend
from ..config import STORE_DIR, DEFAULT_TOP_N, DEFAULT_TOP_K, DEFAULT_TOP_M

# module-level translation dict — populated by build_app() so that
# module-level runner functions can return translated output strings
_T: dict = {}

_CONFIG_DIR  = Path.home() / ".simargl"
_CONFIG_FILE = _CONFIG_DIR / "config.json"

_THEMES = ["Monochrome", "Soft", "Glass", "Ocean", "Default",
           "GithubDark", "Dracula", "Solarized"]


def _dark_theme(primary_hue: str, bg: str, bg2: str, border: str,
                text: str, text_sub: str, input_bg: str, btn2_bg: str):
    """Build a dark Gradio theme by forcing both light and dark CSS vars to the same dark values."""
    import gradio as _gr
    from gradio.themes.utils import colors as _gc
    _base = getattr(_gc, primary_hue.lower(), _gc.blue)
    _primary = _gc.Color(
        c50=btn2_bg, c100=_base.c100, c200=_base.c200,
        c300=_base.c300, c400=_base.c400, c500=_base.c500,
        c600=_base.c600, c700=_base.c700, c800=_base.c800,
        c900=_base.c900, c950=_base.c950,
        name=f"dark-{primary_hue}",
    )
    return _gr.themes.Base(primary_hue=_primary, neutral_hue="slate").set(
        body_background_fill=bg,               body_background_fill_dark=bg,
        background_fill_primary=bg,            background_fill_primary_dark=bg,
        background_fill_secondary=bg2,         background_fill_secondary_dark=bg2,
        block_background_fill=bg2,             block_background_fill_dark=bg2,
        block_label_background_fill=bg2,       block_label_background_fill_dark=bg2,
        block_title_background_fill=bg2,
        panel_background_fill=bg2,             panel_background_fill_dark=bg2,
        block_border_color=border,             block_border_color_dark=border,
        block_label_border_color=border,       block_label_border_color_dark=border,
        border_color_primary=border,           border_color_primary_dark=border,
        body_text_color=text,                  body_text_color_dark=text,
        body_text_color_subdued=text_sub,      body_text_color_subdued_dark=text_sub,
        block_label_text_color=text_sub,       block_label_text_color_dark=text_sub,
        block_title_text_color=text,           block_title_text_color_dark=text,
        block_info_text_color=text_sub,        block_info_text_color_dark=text_sub,
        input_background_fill=bg,             input_background_fill_dark=bg,
        input_background_fill_hover=bg2,      input_background_fill_hover_dark=bg2,
        input_border_color=border,             input_border_color_dark=border,
        input_border_color_hover=text_sub,     input_border_color_hover_dark=text_sub,
        input_placeholder_color=text_sub,      input_placeholder_color_dark=text_sub,
        code_background_fill=bg,               code_background_fill_dark=bg,
        button_secondary_background_fill=btn2_bg,     button_secondary_background_fill_dark=btn2_bg,
        button_secondary_background_fill_hover=border, button_secondary_background_fill_hover_dark=border,
        button_secondary_text_color=text,      button_secondary_text_color_dark=text,
        button_secondary_border_color=border,  button_secondary_border_color_dark=border,
        button_cancel_background_fill=bg2,     button_cancel_background_fill_dark=bg2,
        table_even_background_fill=bg,         table_even_background_fill_dark=bg,
        table_odd_background_fill=bg2,         table_odd_background_fill_dark=bg2,
        table_border_color=border,             table_border_color_dark=border,
        table_text_color=text,                 table_text_color_dark=text,
        checkbox_background_color=bg2,         checkbox_background_color_dark=bg2,
        checkbox_border_color=border,          checkbox_border_color_dark=border,
        checkbox_label_background_fill=bg2,    checkbox_label_background_fill_dark=bg2,
        checkbox_label_text_color=text,        checkbox_label_text_color_dark=text,
        accordion_text_color=text,             accordion_text_color_dark=text,
        error_background_fill=bg2,             error_background_fill_dark=bg2,
        stat_background_fill=bg2,              stat_background_fill_dark=bg2,
    )


# ── config helpers ─────────────────────────────────────────────────────────────

def _load_config() -> dict:
    try:
        return _json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_config(patch: dict) -> None:
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    cfg = _load_config()
    cfg.update(patch)
    _CONFIG_FILE.write_text(_json.dumps(cfg, indent=2), encoding="utf-8")


# ── helpers ────────────────────────────────────────────────────────────────────

def _list_projects(store_dir: str = STORE_DIR) -> list[str]:
    p = Path(store_dir)
    if not p.exists():
        return ["default"]
    projects = [d.name for d in p.iterdir() if d.is_dir() and (d / "meta.json").exists()]
    return projects or ["default"]


def _zip_project(store_dir: str, project_id: str) -> str:
    import zipfile, tempfile
    project_dir = Path(store_dir) / project_id
    if not project_dir.exists():
        tmp = tempfile.NamedTemporaryFile(mode='w', suffix='_error.txt',
                                          delete=False, encoding='utf-8')
        tmp.write(f"Project not found: {project_dir}\nRun: simargl index files/units first.")
        tmp.close()
        return tmp.name

    tmp = tempfile.NamedTemporaryFile(suffix=f'_{project_id}.zip', delete=False)
    tmp.close()
    with zipfile.ZipFile(tmp.name, 'w', zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(project_dir.iterdir()):
            if not f.is_file():
                continue
            if f.name == 'meta.json':
                meta = _json.loads(f.read_text(encoding='utf-8'))
                if 'db_path' in meta:
                    meta['db_path'] = Path(meta['db_path']).name
                zf.writestr(str(Path(project_id) / f.name),
                            _json.dumps(meta, indent=2))
            else:
                zf.write(f, arcname=str(Path(project_id) / f.name))
    return tmp.name


def _fmt_files(files: list[dict]) -> str:
    if not files:
        return _T.get("out_no_files", "_No files found._")
    return "\n\n".join(
        f"`{f['score']:.3f}`  **{f['path']}**  `[{f['module']}]`" for f in files
    )


def _fmt_modules(modules: list[dict]) -> str:
    if not modules:
        return _T.get("out_no_modules", "_No modules found._")
    return "\n\n".join(
        f"`{m['score']:.3f}`  **{m['module']}**" for m in modules
    )


def _fmt_units(units: list[dict]) -> str:
    if not units:
        return _T.get("out_no_units", "_No similar tasks/commits._")
    parts = []
    for u in units:
        files_str = ", ".join(f"`{f}`" for f in u["files"][:5])
        if len(u["files"]) > 5:
            files_str += f" _(+{len(u['files']) - 5} more)_"
        block = (
            f"**[{u['similarity']:.3f}]** `{u['unit_id']}` — {u['text_preview'][:100]}\n\n"
            f"Files: {files_str}"
        )
        if u.get("diff"):
            block += f"\n\n```diff\n{u['diff'][:1200]}\n```"
        parts.append(block)
    return "\n\n---\n\n".join(parts)


def _load_meta_fields(store_dir: str, project_id: str) -> tuple[str, str]:
    try:
        backend = make_backend("numpy", store_dir=store_dir, project_id=project_id)
        meta = backend.load_meta()
        return meta.get("db_path", ""), meta.get("model_key", "")
    except Exception:
        return "", ""


def _load_project_config(store_dir: str) -> tuple[str, str]:
    try:
        import yaml as _yaml
    except ImportError:
        return "(yaml not installed)", ""

    yaml_path  = Path(store_dir) / "project.yaml"
    state_path = Path(store_dir) / "ingest_state.yaml"

    if yaml_path.exists():
        try:
            cfg = _yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
            for section in cfg.values():
                if isinstance(section, dict):
                    for k in list(section.keys()):
                        if any(s in k.lower() for s in ("token", "password", "secret")):
                            section[k] = "***"
            yaml_text = _yaml.dump(cfg, default_flow_style=False,
                                   allow_unicode=True, sort_keys=False)
        except Exception as e:
            yaml_text = f"Error reading project.yaml: {e}"
    else:
        yaml_text = "(no project.yaml — run: simargl init)"

    if state_path.exists():
        try:
            state = _yaml.safe_load(state_path.read_text(encoding="utf-8")) or {}
            state_text = _yaml.dump(state, default_flow_style=False,
                                    allow_unicode=True, sort_keys=False)
        except Exception as e:
            state_text = f"Error reading ingest_state.yaml: {e}"
    else:
        state_text = "(no ingest_state.yaml yet)"

    return yaml_text, state_text


# ── subprocess streaming helper ────────────────────────────────────────────────

def _iter_subprocess(cmd: list[str]):
    header = "$ " + " ".join(str(c) for c in cmd) + "\n\n"
    yield header
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
        )
        acc = header
        for line in proc.stdout:
            acc += line
            yield acc
        proc.wait()
        tail = "\n[OK]" if proc.returncode == 0 else f"\n[EXIT {proc.returncode}]"
        yield acc + tail
    except FileNotFoundError:
        yield header + "ERROR: 'simargl' not found in PATH. Is the package installed?"
    except Exception as e:
        yield header + f"ERROR: {e}"


# ── search / retrieval runners ─────────────────────────────────────────────────

def _run_search(query, mode, sort, project_id, top_n, top_k, top_m,
                include_diff, exclude_blackholes, coverage_penalty, score_blend,
                refine_top_k, refine_top_m, store_dir):
    if not query.strip():
        yield _T.get("out_enter_query", "_Enter a query._"), "", ""
        return
    searching = _T.get("out_searching", "_Searching..._")
    yield searching, searching, searching
    try:
        result = search(
            query, mode=mode, sort=sort,
            top_n=int(top_n), top_k=int(top_k), top_m=int(top_m),
            include_diff=include_diff,
            exclude_blackholes=exclude_blackholes,
            coverage_penalty=float(coverage_penalty),
            score_blend=float(score_blend),
            refine_top_k=int(refine_top_k),
            refine_top_m=int(refine_top_m),
            project_id=project_id, store_dir=store_dir,
        )
    except Exception as e:
        yield f"**Error:** {e}", "", ""
        return
    yield _fmt_files(result["files"]), _fmt_modules(result["modules"]), _fmt_units(result["units"])


def _run_rrf(query, sources, top_n, top_k, k, sort, score_blend, coverage_penalty, store_dir):
    if not query.strip():
        return _T.get("out_enter_query", "_Enter a query._"), "", ""
    try:
        result = rrf_search(
            query,
            sources=sources,
            top_n=int(top_n),
            top_k=int(top_k),
            k=int(k),
            sort=sort,
            score_blend=float(score_blend),
            coverage_penalty=float(coverage_penalty),
            store_dir=store_dir,
        )
    except Exception as e:
        return f"**Error:** {e}", "", ""

    no_res = _T.get("out_no_src_res", "_no results_")
    src_parts = []
    for src in result.get("sources", []):
        hdr = f"**{src['mode']}:{src['project_id']}**"
        if "error" in src:
            src_parts.append(f"{hdr} — ERROR: {src['error']}")
        else:
            paths = ", ".join(f"`{f['path']}`" for f in src["files"][:5])
            src_parts.append(f"{hdr}: {paths or no_res}")

    return (
        _fmt_files(result["files"]),
        _fmt_modules(result["modules"]),
        "\n\n".join(src_parts) or _T.get("out_no_sources", "_No sources._"),
    )


def _run_retrieve(query, mode, project_id, top_n, exclude_blackholes,
                  coverage_penalty, score_blend, source_dir, store_dir):
    if not query.strip():
        return _T.get("out_enter_query", "_Enter a query._")
    try:
        text = retrieve(
            query,
            mode=mode,
            top_n=int(top_n),
            exclude_blackholes=exclude_blackholes,
            coverage_penalty=float(coverage_penalty),
            score_blend=float(score_blend),
            project_id=project_id,
            store_dir=store_dir,
            source_dir=source_dir.strip() or None,
        )
        return text or _T.get("out_no_results", "_No results._")
    except Exception as e:
        return f"**Error:** {e}"


def _run_blackhole(store_dir, project_id, method, threshold, n_queries, top_k, list_only):
    try:
        backend = make_backend("numpy", store_dir=store_dir, project_id=project_id)
        if list_only:
            paths = sorted(backend.blackhole_paths())
            if not paths:
                return _T.get("out_no_bh", "No blackhole files marked.")
            return f"Blackhole files ({len(paths)}):\n" + "\n".join(f"  {p}" for p in paths)
        meta = backend.load_meta()
        thr = float(threshold)
        if method == "coverage_float":
            result = backend.compute_file_coverage(
                meta["dim"], n_queries=int(n_queries), top_k=int(top_k)
            )
            return (
                f"Coverage scores computed — project={project_id}\n"
                f"  Method      : coverage_float (re-ranking, no binary filter)\n"
                f"  Test queries: {result['n_queries']}\n"
                f"  Top-k       : {result['top_k']}\n"
                f"  Total paths : {result['total_paths']}\n"
                f"  Max coverage: {result['max_coverage']:.4f}\n\n"
                f"Use search/retrieve with coverage_penalty >= 0.2 to re-rank."
            )
        elif method == "coverage":
            result = backend.compute_blackholes_coverage(
                meta["dim"], n_queries=int(n_queries), threshold=thr, top_k=int(top_k)
            )
            return (
                f"Blackhole detection complete (coverage) — project={project_id}\n"
                f"  Threshold  : {result['threshold']} "
                f"({int(result['threshold']*result['n_queries'])} / {result['n_queries']} queries)\n"
                f"  Top-k      : {result['top_k']}\n"
                f"  Total paths: {result['total_paths']}\n"
                f"  Marked     : {result['marked']}\n\n"
                f"Use search/retrieve with exclude_blackholes=True to filter them."
            )
        else:
            result = backend.compute_blackholes(meta["dim"], threshold=thr)
            return (
                f"Blackhole detection complete (centroid) — project={project_id}\n"
                f"  Threshold  : {result['threshold']}\n"
                f"  Total paths: {result['total_paths']}\n"
                f"  Marked     : {result['marked']}\n\n"
                f"Use search/retrieve with exclude_blackholes=True to filter them."
            )
    except Exception as e:
        return f"ERROR: {e}"


def _run_status(store_dir: str, project_id: str) -> tuple[str, str, str]:
    try:
        backend = make_backend("numpy", store_dir=store_dir, project_id=project_id)
        s = backend.stats()
        lines = [
            f"Project:  {project_id}",
            f"Backend:  numpy",
            f"Model:    {s.get('model_key', '?')}  dim={s.get('dim', '?')}",
            f"Files:    {s.get('files', 0)}  ({s.get('chunks', 0)} chunks"
            + (f", {s.get('deleted_chunks', 0)} deleted)" if s.get('deleted_chunks') else ")"),
            f"Units:    {s.get('units', 0)}  (mode={s.get('unit_mode', '?')})"
            + (f"  last={s['unit_last']}" if s.get('unit_last') else ""),
            f"Indexed:  {s.get('indexed_at', '?')}",
        ]
        stats_text = "\n".join(lines)
    except Exception as e:
        stats_text = f"ERROR: {e}"

    yaml_text, state_text = _load_project_config(store_dir)
    return stats_text, yaml_text, state_text


# ── admin runners ──────────────────────────────────────────────────────────────

def _admin_vacuum(store_dir, project_id):
    try:
        backend = make_backend("numpy", store_dir=store_dir, project_id=project_id)
        meta = backend.load_meta()
        result = backend.vacuum_files(meta["dim"])
        yield (
            f"Vacuum complete — project={project_id}\n"
            f"  chunks before : {result['before']}\n"
            f"  chunks after  : {result['after']}\n"
            f"  reclaimed     : {result['reclaimed_mb']} MB"
        )
    except Exception as e:
        yield f"ERROR: {e}"


def _admin_reindex_units(store_dir, project_id, db_path, model):
    if not db_path.strip():
        meta_db, meta_model = _load_meta_fields(store_dir, project_id)
        db_path = meta_db or "units.db"
        if not model.strip():
            model = meta_model

    abs_store = os.path.abspath(store_dir)
    cmd = ["simargl", "index", "units", db_path,
           "--project", project_id, "--store-dir", abs_store]
    if model.strip():
        cmd += ["--model", model.strip()]
    yield from _iter_subprocess(cmd)


def _admin_reindex_files(store_dir, project_id, source_path, model, chunk_size, full_rebuild):
    if not source_path.strip():
        yield "Source path is required (directory that was indexed)."
        return
    abs_store = os.path.abspath(store_dir)
    cmd = ["simargl", "index", "files", source_path.strip(),
           "--project", project_id, "--store-dir", abs_store,
           "--chunk-size", str(int(chunk_size))]
    if model.strip():
        cmd += ["--model", model.strip()]
    if full_rebuild:
        cmd.append("--full")
    yield from _iter_subprocess(cmd)


def _admin_reingest(store_dir, phase, force):
    abs_store = os.path.abspath(store_dir)
    yaml_path = Path(abs_store) / "project.yaml"
    if not yaml_path.exists():
        yield (
            f"project.yaml not found at {yaml_path}\n\n"
            f"Run 'simargl init' from the project directory first."
        )
        return
    cmd = ["simargl", "ingest", "--store-dir", abs_store]
    if phase != "both":
        cmd += ["--phase", phase]
    if force:
        cmd.append("--force")
    yield from _iter_subprocess(cmd)


# ── init runner ────────────────────────────────────────────────────────────────

def _init_project(
    store_dir, overwrite,
    project_name, db_path, git_repo, branch, since,
    tracker,
    jira_url, jira_project, jira_connector, jira_token,
    gh_owner, gh_repo, gh_token, gh_mask,
    yt_url, yt_project, yt_token,
    gl_url, gl_project, gl_token,
):
    try:
        import yaml as _yaml
    except ImportError:
        return "ERROR: PyYAML not installed (pip install pyyaml)", ""

    abs_store = os.path.abspath(store_dir)
    yaml_path = Path(abs_store) / "project.yaml"

    if yaml_path.exists() and not overwrite:
        existing = yaml_path.read_text(encoding="utf-8")
        return (
            f"project.yaml already exists at {yaml_path}\n\n"
            f"Check 'Force overwrite' to replace it.",
            existing,
        )

    name = project_name.strip() or Path(abs_store).parent.name
    cfg = {
        "project": {"name": name, "db": db_path.strip() or "units.db"},
        "git":     {"repo": git_repo.strip() or ".", "branch": branch.strip() or "main"},
        "ingest":  {"batch_size": 100, "rate_limit_delay": 1.0},
    }
    if since.strip():
        cfg["git"]["since"] = since.strip()

    if tracker == "jira":
        tc: dict = {
            "source": "jira",
            "jira_url": jira_url.strip(),
            "jira_project": jira_project.strip(),
            "jira_connector": jira_connector or "api",
        }
        if jira_token.strip():
            tc["jira_token"] = jira_token.strip()
        cfg["tasks"] = tc
    elif tracker == "github":
        tc = {
            "source": "github",
            "github_owner": gh_owner.strip(),
            "github_repo": gh_repo.strip(),
            "commit_mask": gh_mask or "generic",
        }
        if gh_token.strip():
            tc["github_token"] = gh_token.strip()
        cfg["tasks"] = tc
    elif tracker == "youtrack":
        tc = {
            "source": "youtrack",
            "youtrack_url": yt_url.strip() or "https://youtrack.jetbrains.com",
            "youtrack_project": yt_project.strip(),
        }
        if yt_token.strip():
            tc["youtrack_token"] = yt_token.strip()
        cfg["tasks"] = tc
    elif tracker == "gitlab":
        tc = {
            "source": "gitlab",
            "gitlab_url": gl_url.strip() or "https://gitlab.com",
            "gitlab_project": gl_project.strip(),
        }
        if gl_token.strip():
            tc["gitlab_token"] = gl_token.strip()
        cfg["tasks"] = tc

    Path(abs_store).mkdir(parents=True, exist_ok=True)
    yaml_str = _yaml.dump(cfg, default_flow_style=False, allow_unicode=True, sort_keys=False)
    yaml_path.write_text(yaml_str, encoding="utf-8")

    mode = "full (git + tasks)" if "tasks" in cfg else "commits-only"
    msg = (
        f"Created {yaml_path}\n"
        f"Mode: {mode}\n\n"
        f"Next steps:\n"
        f"  1. Admin → Re-ingest  (extract commits + fetch tasks)\n"
        f"  2. Admin → Re-index units  (embed into vector index)\n"
        f"  3. Search"
    )
    return msg, yaml_str


# ── UI ─────────────────────────────────────────────────────────────────────────

def build_app(store_dir: str = STORE_DIR, lang: str = "en", theme: str = "Monochrome"):
    global _T
    t = i18n.get(lang)
    _T.update(t)

    try:
        import gradio as gr
    except ImportError:
        raise ImportError("Gradio not installed. Run: pip install simargl[ui]")

    _theme_map = {
        "Monochrome": gr.themes.Monochrome(),
        "Soft":       gr.themes.Soft(),
        "Glass":      gr.themes.Glass(),
        "Ocean":      gr.themes.Ocean(),
        "Default":    gr.themes.Default(),
        "GithubDark": _dark_theme(
            primary_hue="blue",
            bg="#0d1117", bg2="#161b22", border="#30363d",
            text="#c9d1d9", text_sub="#8b949e",
            input_bg="#0d1117", btn2_bg="#21262d",
        ),
        "Dracula": _dark_theme(
            primary_hue="purple",
            bg="#282a36", bg2="#1e1f29", border="#44475a",
            text="#f8f8f2", text_sub="#6272a4",
            input_bg="#282a36", btn2_bg="#44475a",
        ),
        "Solarized": _dark_theme(
            primary_hue="cyan",
            bg="#002b36", bg2="#073642", border="#586e75",
            text="#839496", text_sub="#657b83",
            input_bg="#002b36", btn2_bg="#073642",
        ),
    }
    active_theme = _theme_map.get(theme, gr.themes.Monochrome())

    project_root = Path(store_dir).resolve().parent
    project_name = project_root.name
    projects = _list_projects(store_dir)

    with gr.Blocks(
        title=t["app_title"].format(project_name=project_name),
        theme=active_theme,
    ) as app:
        gr.Markdown(t["app_header"].format(project_name=project_name))

        store_dir_box = gr.Textbox(value=store_dir, label=t["store_dir_label"], scale=3)

        def _refresh_dd(sd):
            p = _list_projects(sd)
            return gr.Dropdown(choices=p, value=p[0] if p else "default")

        with gr.Tabs():

            # ── Search ──────────────────────────────────────────────────────
            with gr.Tab(t["tab_search"]):
                s_query = gr.Textbox(
                    label=t["search_query_label"],
                    placeholder=t["search_query_placeholder"],
                    lines=2,
                )
                s_btn = gr.Button(t["search_btn"], variant="primary")

                with gr.Row():
                    s_mode = gr.Dropdown(
                        choices=["task", "file", "aggr", "refine"],
                        value="task", label=t["search_mode_label"],
                        info=t["search_mode_info"],
                    )
                    s_sort = gr.Dropdown(
                        choices=["rank", "freq"], value="rank",
                        label=t["search_sort_label"], info=t["search_sort_info"],
                    )
                    s_project = gr.Dropdown(choices=projects, value=projects[0],
                                            label=t["search_project_label"])
                    s_diff = gr.Checkbox(label=t["search_diff_label"], value=False)

                with gr.Accordion(t["search_advanced"], open=False):
                    with gr.Row():
                        s_top_n = gr.Slider(1, 30, value=DEFAULT_TOP_N, step=1, label=t["search_top_n"])
                        s_top_k = gr.Slider(1, 50, value=DEFAULT_TOP_K, step=1, label=t["search_top_k"])
                        s_top_m = gr.Slider(1, 15, value=DEFAULT_TOP_M, step=1, label=t["search_top_m"])
                    with gr.Row():
                        s_excl_bh = gr.Checkbox(label=t["search_excl_bh"], value=False)
                        s_cov_pen = gr.Slider(0.0, 1.0, value=0.0, step=0.05,
                                              label=t["search_cov_pen_label"],
                                              info=t["search_cov_pen_info"])
                        s_blend   = gr.Slider(0.0, 2.0, value=1.0, step=0.05,
                                              label=t["search_blend_label"],
                                              info=t["search_blend_info"])
                    with gr.Row():
                        s_ref_k = gr.Slider(1, 20, value=10, step=1,
                                            label=t["search_ref_k_label"],
                                            info=t["search_ref_k_info"],
                                            visible=False)
                        s_ref_m = gr.Slider(1, 15, value=8, step=1,
                                            label=t["search_ref_m_label"],
                                            info=t["search_ref_m_info"],
                                            visible=False)

                def _s_mode_change(mode):
                    show = mode == "refine"
                    return gr.update(visible=show), gr.update(visible=show)

                s_mode.change(_s_mode_change, inputs=[s_mode], outputs=[s_ref_k, s_ref_m])

                with gr.Row():
                    with gr.Column(scale=2):
                        gr.Markdown(t["search_files_header"])
                        s_files_out = gr.Markdown()
                    with gr.Column(scale=1):
                        gr.Markdown(t["search_modules_header"])
                        s_mods_out = gr.Markdown()
                gr.Markdown(t["search_units_header"])
                s_units_out = gr.Markdown()

                s_inputs  = [s_query, s_mode, s_sort, s_project,
                             s_top_n, s_top_k, s_top_m,
                             s_diff, s_excl_bh, s_cov_pen, s_blend,
                             s_ref_k, s_ref_m, store_dir_box]
                s_outputs = [s_files_out, s_mods_out, s_units_out]
                s_btn.click(_run_search, inputs=s_inputs, outputs=s_outputs, show_progress="full")
                s_query.submit(_run_search, inputs=s_inputs, outputs=s_outputs, show_progress="full")
                store_dir_box.change(_refresh_dd, inputs=store_dir_box, outputs=s_project)

            # ── RRF ─────────────────────────────────────────────────────────
            with gr.Tab(t["tab_rrf"]):
                gr.Markdown(t["rrf_desc"])
                with gr.Row():
                    rrf_query = gr.Textbox(label=t["rrf_query_label"], scale=3)
                    rrf_btn   = gr.Button(t["rrf_btn"], variant="primary", scale=1)
                rrf_sources = gr.Textbox(
                    value="task:default,file:default",
                    label=t["rrf_sources_label"],
                    info=t["rrf_sources_info"],
                )
                with gr.Row():
                    rrf_top_n = gr.Slider(1, 30, value=5,    step=1, label=t["rrf_top_n"])
                    rrf_top_k = gr.Slider(1, 50, value=10,   step=1, label=t["rrf_top_k"])
                    rrf_k     = gr.Slider(10, 120, value=60, step=5, label=t["rrf_k"])
                with gr.Row():
                    rrf_sort    = gr.Dropdown(choices=["rank", "freq"], value="freq",
                                             label=t["rrf_sort_label"])
                    rrf_blend   = gr.Slider(0.0, 2.0, value=1.0, step=0.05, label=t["rrf_blend_label"])
                    rrf_cov_pen = gr.Slider(0.0, 1.0, value=0.0, step=0.05, label=t["rrf_cov_pen_label"])

                with gr.Row():
                    with gr.Column(scale=2):
                        gr.Markdown(t["rrf_files_header"])
                        rrf_files_out = gr.Markdown()
                    with gr.Column(scale=1):
                        gr.Markdown(t["rrf_modules_header"])
                        rrf_mods_out = gr.Markdown()
                gr.Markdown(t["rrf_src_header"])
                rrf_src_out = gr.Markdown()

                rrf_inputs  = [rrf_query, rrf_sources, rrf_top_n, rrf_top_k,
                               rrf_k, rrf_sort, rrf_blend, rrf_cov_pen, store_dir_box]
                rrf_outputs = [rrf_files_out, rrf_mods_out, rrf_src_out]
                rrf_btn.click(_run_rrf, inputs=rrf_inputs, outputs=rrf_outputs)
                rrf_query.submit(_run_rrf, inputs=rrf_inputs, outputs=rrf_outputs)

            # ── Retrieve ─────────────────────────────────────────────────────
            with gr.Tab(t["tab_retrieve"]):
                gr.Markdown(t["ret_desc"])
                with gr.Row():
                    ret_query = gr.Textbox(label=t["ret_query_label"], scale=3)
                    ret_btn   = gr.Button(t["ret_btn"], variant="primary", scale=1)
                with gr.Row():
                    ret_mode    = gr.Dropdown(
                        choices=["file", "task", "aggr"], value="file",
                        label=t["ret_mode_label"], info=t["ret_mode_info"],
                    )
                    ret_project = gr.Dropdown(choices=projects, value=projects[0],
                                             label=t["ret_project_label"])
                    ret_top_n   = gr.Slider(1, 20, value=5, step=1, label=t["ret_top_n"])
                with gr.Row():
                    ret_excl_bh = gr.Checkbox(label=t["ret_excl_bh"], value=False)
                    ret_cov_pen = gr.Slider(0.0, 1.0, value=0.0, step=0.05, label=t["ret_cov_pen"])
                    ret_blend   = gr.Slider(0.0, 2.0, value=1.0, step=0.05, label=t["ret_blend"])
                ret_source_dir = gr.Textbox(
                    label=t["ret_source_dir_label"],
                    placeholder=t["ret_source_dir_ph"],
                )
                ret_out = gr.Code(label=t["ret_out_label"], language=None, lines=20)

                ret_inputs = [ret_query, ret_mode, ret_project, ret_top_n,
                              ret_excl_bh, ret_cov_pen, ret_blend,
                              ret_source_dir, store_dir_box]
                ret_btn.click(_run_retrieve, inputs=ret_inputs, outputs=ret_out)
                ret_query.submit(_run_retrieve, inputs=ret_inputs, outputs=ret_out)
                store_dir_box.change(_refresh_dd, inputs=store_dir_box, outputs=ret_project)

            # ── Blackhole ────────────────────────────────────────────────────
            with gr.Tab(t["tab_blackhole"]):
                gr.Markdown(t["bh_desc"])
                with gr.Row():
                    bh_project = gr.Dropdown(choices=projects, value=projects[0],
                                            label=t["bh_project_label"])
                    bh_method  = gr.Dropdown(
                        choices=["centroid", "coverage", "coverage_float"],
                        value="centroid", label=t["bh_method_label"],
                    )
                with gr.Row():
                    bh_threshold = gr.Slider(0.0, 1.0, value=0.85, step=0.05,
                                            label=t["bh_threshold_label"],
                                            info=t["bh_threshold_info"])
                    bh_n_queries = gr.Slider(10, 500, value=100, step=10,
                                            label=t["bh_n_queries_label"])
                    bh_top_k     = gr.Slider(5, 50, value=20, step=5,
                                            label=t["bh_top_k_label"])
                with gr.Row():
                    bh_list_btn   = gr.Button(t["bh_list_btn"])
                    bh_detect_btn = gr.Button(t["bh_detect_btn"], variant="primary")
                bh_out = gr.Code(label=t["bh_out_label"], language=None, lines=12)

                def _bh_method_change(method):
                    defaults = {"centroid": 0.85, "coverage": 0.3, "coverage_float": 0.3}
                    return gr.update(value=defaults.get(method, 0.85))

                bh_method.change(_bh_method_change, inputs=[bh_method], outputs=[bh_threshold])
                bh_detect_btn.click(
                    _run_blackhole,
                    inputs=[store_dir_box, bh_project, bh_method,
                            bh_threshold, bh_n_queries, bh_top_k, gr.State(False)],
                    outputs=bh_out,
                )
                bh_list_btn.click(
                    _run_blackhole,
                    inputs=[store_dir_box, bh_project, bh_method,
                            bh_threshold, bh_n_queries, bh_top_k, gr.State(True)],
                    outputs=bh_out,
                )
                store_dir_box.change(_refresh_dd, inputs=store_dir_box, outputs=bh_project)

            # ── Status ───────────────────────────────────────────────────────
            with gr.Tab(t["tab_status"]):
                with gr.Row():
                    st_project = gr.Dropdown(choices=projects, value=projects[0],
                                             label=t["st_project_label"], scale=3)
                    st_btn     = gr.Button(t["st_btn"], variant="primary", scale=1)

                st_stats_out = gr.Code(label=t["st_stats_label"], language=None, lines=6)
                with gr.Row():
                    with gr.Column():
                        st_config_out = gr.Code(label=t["st_config_label"],
                                                language="yaml", lines=20)
                    with gr.Column():
                        st_state_out  = gr.Code(label=t["st_state_label"],
                                                language="yaml", lines=10)

                st_btn.click(_run_status,
                             inputs=[store_dir_box, st_project],
                             outputs=[st_stats_out, st_config_out, st_state_out])
                store_dir_box.change(_refresh_dd, inputs=store_dir_box, outputs=st_project)

            # ── Admin ────────────────────────────────────────────────────────
            with gr.Tab(t["tab_admin"]):
                gr.Markdown(t["adm_desc"])
                adm_project = gr.Dropdown(choices=projects, value=projects[0],
                                          label=t["adm_project_label"])
                store_dir_box.change(_refresh_dd, inputs=store_dir_box, outputs=adm_project)

                with gr.Accordion(t["adm_vacuum_title"], open=False):
                    gr.Markdown(t["adm_vacuum_desc"])
                    vac_btn = gr.Button(t["adm_vacuum_btn"], variant="primary")
                    vac_out = gr.Code(label=t["adm_vacuum_out"], language=None, lines=5)
                    vac_btn.click(_admin_vacuum,
                                  inputs=[store_dir_box, adm_project], outputs=vac_out)

                with gr.Accordion(t["adm_ri_title"], open=False):
                    gr.Markdown(t["adm_ri_desc"])
                    with gr.Row():
                        ri_phase = gr.Radio(
                            choices=["both", "git", "tasks"],
                            value="both", label=t["adm_ri_phase_label"],
                        )
                        ri_force = gr.Checkbox(label=t["adm_ri_force_label"], value=False)
                    ri_btn = gr.Button(t["adm_ri_btn"], variant="primary")
                    ri_out = gr.Code(label=t["adm_out_label"], language=None, lines=15)
                    ri_btn.click(_admin_reingest,
                                 inputs=[store_dir_box, ri_phase, ri_force],
                                 outputs=ri_out)

                with gr.Accordion(t["adm_riu_title"], open=False):
                    gr.Markdown(t["adm_riu_desc"])
                    with gr.Row():
                        riu_db    = gr.Textbox(label=t["adm_riu_db_label"],
                                               placeholder=t["adm_riu_db_ph"])
                        riu_model = gr.Textbox(label=t["adm_riu_model_label"],
                                               placeholder=t["adm_riu_model_ph"])
                    riu_btn = gr.Button(t["adm_riu_btn"], variant="primary")
                    riu_out = gr.Code(label=t["adm_out_label"], language=None, lines=10)
                    riu_btn.click(_admin_reindex_units,
                                  inputs=[store_dir_box, adm_project, riu_db, riu_model],
                                  outputs=riu_out)

                    def _adm_proj_change(sd, proj):
                        db, model = _load_meta_fields(sd, proj)
                        return (
                            gr.update(placeholder=db or t["adm_riu_db_ph"]),
                            gr.update(placeholder=model or t["adm_riu_model_ph"]),
                        )

                    adm_project.change(_adm_proj_change,
                                       inputs=[store_dir_box, adm_project],
                                       outputs=[riu_db, riu_model])
                    store_dir_box.change(_adm_proj_change,
                                         inputs=[store_dir_box, adm_project],
                                         outputs=[riu_db, riu_model])

                with gr.Accordion(t["adm_rif_title"], open=False):
                    gr.Markdown(t["adm_rif_desc"])
                    with gr.Row():
                        rif_path  = gr.Textbox(label=t["adm_rif_path_label"],
                                               placeholder=t["adm_rif_path_ph"])
                        rif_model = gr.Textbox(label=t["adm_rif_model_label"],
                                               placeholder=t["adm_rif_model_ph"])
                    with gr.Row():
                        rif_chunk = gr.Slider(100, 1000, value=400, step=50,
                                             label=t["adm_rif_chunk_label"])
                        rif_full  = gr.Checkbox(label=t["adm_rif_full_label"], value=False)
                    rif_btn = gr.Button(t["adm_rif_btn"], variant="primary")
                    rif_out = gr.Code(label=t["adm_out_label"], language=None, lines=10)
                    rif_btn.click(_admin_reindex_files,
                                  inputs=[store_dir_box, adm_project,
                                          rif_path, rif_model, rif_chunk, rif_full],
                                  outputs=rif_out)

            # ── Init ─────────────────────────────────────────────────────────
            with gr.Tab(t["tab_init"]):
                gr.Markdown(t["init_desc"])

                with gr.Row():
                    init_name   = gr.Textbox(label=t["init_name_label"],
                                             placeholder=project_root.name)
                    init_db     = gr.Textbox(label=t["init_db_label"], value="units.db")
                with gr.Row():
                    init_repo   = gr.Textbox(label=t["init_repo_label"], value=".",
                                             info=t["init_repo_info"])
                    init_branch = gr.Textbox(label=t["init_branch_label"], value="main")
                    init_since  = gr.Textbox(label=t["init_since_label"],
                                             placeholder=t["init_since_ph"])

                init_tracker = gr.Radio(
                    choices=["none", "jira", "github", "youtrack", "gitlab"],
                    value="none", label=t["init_tracker_label"],
                )

                with gr.Column(visible=False) as init_jira_sec:
                    gr.Markdown(t["init_jira_header"])
                    with gr.Row():
                        init_jira_url  = gr.Textbox(label=t["init_jira_url_label"],
                                                    placeholder=t["init_jira_url_ph"])
                        init_jira_proj = gr.Textbox(label=t["init_jira_proj_label"],
                                                    placeholder=t["init_jira_proj_ph"])
                    with gr.Row():
                        init_jira_conn  = gr.Dropdown(
                            choices=["api", "html", "selenium"], value="api",
                            label=t["init_jira_conn_label"], info=t["init_jira_conn_info"],
                        )
                        init_jira_token = gr.Textbox(label=t["init_jira_token_label"],
                                                     type="password")

                with gr.Column(visible=False) as init_gh_sec:
                    gr.Markdown(t["init_gh_header"])
                    with gr.Row():
                        init_gh_owner = gr.Textbox(label=t["init_gh_owner_label"],
                                                   placeholder=t["init_gh_owner_ph"])
                        init_gh_repo  = gr.Textbox(label=t["init_gh_repo_label"],
                                                   placeholder=t["init_gh_repo_ph"])
                    with gr.Row():
                        init_gh_token = gr.Textbox(label=t["init_gh_token_label"],
                                                   type="password")
                        init_gh_mask  = gr.Dropdown(
                            choices=["generic", "django", "broad"], value="generic",
                            label=t["init_gh_mask_label"], info=t["init_gh_mask_info"],
                        )

                with gr.Column(visible=False) as init_yt_sec:
                    gr.Markdown(t["init_yt_header"])
                    with gr.Row():
                        init_yt_url     = gr.Textbox(label=t["init_yt_url_label"],
                                                     value="https://youtrack.jetbrains.com")
                        init_yt_project = gr.Textbox(label=t["init_yt_proj_label"],
                                                     placeholder=t["init_yt_proj_ph"])
                        init_yt_token   = gr.Textbox(label=t["init_yt_token_label"],
                                                     type="password")

                with gr.Column(visible=False) as init_gl_sec:
                    gr.Markdown(t["init_gl_header"])
                    with gr.Row():
                        init_gl_url     = gr.Textbox(label=t["init_gl_url_label"],
                                                     value="https://gitlab.com")
                        init_gl_project = gr.Textbox(label=t["init_gl_proj_label"],
                                                     placeholder=t["init_gl_proj_ph"])
                        init_gl_token   = gr.Textbox(label=t["init_gl_token_label"],
                                                     type="password")

                def _tracker_change(tracker):
                    return (
                        gr.update(visible=tracker == "jira"),
                        gr.update(visible=tracker == "github"),
                        gr.update(visible=tracker == "youtrack"),
                        gr.update(visible=tracker == "gitlab"),
                    )

                init_tracker.change(
                    _tracker_change,
                    inputs=[init_tracker],
                    outputs=[init_jira_sec, init_gh_sec, init_yt_sec, init_gl_sec],
                )

                with gr.Row():
                    init_overwrite = gr.Checkbox(label=t["init_overwrite_label"], value=False)
                    init_btn = gr.Button(t["init_btn"], variant="primary")

                init_status_out = gr.Code(label=t["init_result_label"], language=None, lines=6)
                init_yaml_out   = gr.Code(label=t["init_yaml_label"], language="yaml", lines=20)

                init_btn.click(
                    _init_project,
                    inputs=[
                        store_dir_box, init_overwrite,
                        init_name, init_db, init_repo, init_branch, init_since,
                        init_tracker,
                        init_jira_url, init_jira_proj, init_jira_conn, init_jira_token,
                        init_gh_owner, init_gh_repo, init_gh_token, init_gh_mask,
                        init_yt_url, init_yt_project, init_yt_token,
                        init_gl_url, init_gl_project, init_gl_token,
                    ],
                    outputs=[init_status_out, init_yaml_out],
                )

            # ── Settings ─────────────────────────────────────────────────────
            with gr.Tab(t["tab_settings"]):
                gr.Markdown(t["settings_theme_header"])
                with gr.Row():
                    s_theme = gr.Dropdown(choices=_THEMES, value=theme,
                                          label=t["settings_theme_label"], scale=2)
                    s_theme_btn = gr.Button(t["settings_theme_save_btn"], scale=1)
                s_theme_hint = gr.Markdown("")

                gr.Markdown(t["settings_lang_header"])
                with gr.Row():
                    s_lang = gr.Dropdown(choices=i18n.LANGS, value=lang,
                                         label=t["settings_lang_label"], scale=2)
                    s_lang_btn = gr.Button(t["settings_lang_save_btn"], scale=1)
                s_lang_hint = gr.Markdown("")

                def _do_save_theme(name):
                    _save_config({"theme": name})
                    return t["settings_restart_hint"]

                def _do_save_lang(name):
                    _save_config({"lang": name})
                    return t["settings_restart_hint"]

                s_theme_btn.click(_do_save_theme, inputs=[s_theme], outputs=[s_theme_hint])
                s_lang_btn.click(_do_save_lang, inputs=[s_lang], outputs=[s_lang_hint])

                gr.Markdown("---")
                _restart_delay = int(_load_config().get("restart_delay", 5))
                with gr.Row():
                    s_restart_delay = gr.Number(
                        value=_restart_delay, minimum=2, maximum=60, step=1,
                        label=t["settings_reload_delay_label"], precision=0, scale=3,
                    )
                    s_delay_save = gr.Button(t["settings_theme_save_btn"], scale=1)
                s_delay_hint = gr.Markdown("")

                def _do_save_restart_delay(d):
                    _save_config({"restart_delay": int(d)})
                    return t["settings_restart_hint"]

                s_delay_save.click(_do_save_restart_delay,
                                   inputs=[s_restart_delay], outputs=[s_delay_hint])

                s_restart_btn = gr.Button(t["settings_restart_btn"], variant="stop")
                s_restart_out = gr.Markdown("")

                def _do_restart_app(delay):
                    import sys, threading
                    import subprocess as _sp
                    def _relaunch():
                        _sp.Popen(sys.argv, cwd=os.getcwd())
                        os._exit(0)
                    threading.Timer(1.5, _relaunch).start()
                    return t["settings_restarting"]

                s_restart_btn.click(
                    _do_restart_app,
                    inputs=[s_restart_delay],
                    outputs=[s_restart_out],
                    js="""(delay) => {
  const ms = Math.max(2, parseInt(delay) || 5) * 1000;
  const overlay = document.createElement('div');
  overlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;z-index:99999;background:#1e293b;padding:10px 16px;box-shadow:0 2px 8px rgba(0,0,0,.5)';
  const lbl = document.createElement('div');
  lbl.style.cssText = 'color:#e2e8f0;font-size:13px;margin-bottom:6px;font-family:monospace';
  const track = document.createElement('div');
  track.style.cssText = 'width:100%;height:8px;background:#334155;border-radius:4px;overflow:hidden';
  const fill = document.createElement('div');
  fill.style.cssText = 'height:100%;width:0%;background:#3b82f6;border-radius:4px';
  track.appendChild(fill);
  overlay.appendChild(lbl);
  overlay.appendChild(track);
  document.body.appendChild(overlay);
  const start = Date.now();
  const tick = setInterval(() => {
    const elapsed = Date.now() - start;
    const pct = Math.min(100, (elapsed / ms) * 100);
    const secs = Math.max(0, Math.ceil((ms - elapsed) / 1000));
    fill.style.width = pct + '%';
    lbl.textContent = 'Restarting SIMARGL… reloading in ' + secs + ' s';
    if (elapsed >= ms) { clearInterval(tick); window.location.reload(); }
  }, 100);
}""",
                )

            # ── Download ─────────────────────────────────────────────────────
            with gr.Tab(t["tab_download"]):
                gr.Markdown(t["dl_desc"])
                with gr.Row():
                    dl_project = gr.Dropdown(choices=projects, value=projects[0],
                                            label=t["dl_project_label"])
                    dl_btn     = gr.Button(t["dl_btn"], variant="primary")
                dl_file = gr.File(label=t["dl_file_label"], interactive=False)

                dl_btn.click(_zip_project, inputs=[store_dir_box, dl_project], outputs=dl_file)
                store_dir_box.change(_refresh_dd, inputs=store_dir_box, outputs=dl_project)

    app.queue()
    return app


def main(port: int = 7861, host: str = "0.0.0.0",
         store_dir: str = STORE_DIR, lang: str = "en", theme: str = "Monochrome"):
    app = build_app(store_dir=store_dir, lang=lang, theme=theme)
    print(f"SIMARGL UI — open: http://localhost:{port}")
    app.launch(server_name=host, server_port=port)
