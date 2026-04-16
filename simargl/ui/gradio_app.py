"""Gradio web UI for simargl.

Start:
  simargl ui                  # default port 7861
  simargl ui --port 7861

Layout:
  [Query input]  [Mode: task/file/aggr]  [Sort: rank/freq]  [Project]  [Search]

  ── Files ──────────────────────────────────────────────────
  score  path  [module]

  ── Modules ────────────────────────────────────────────────
  score  module

  ── Similar tasks/commits ──────────────────────────────────
  [similarity]  unit_id — preview
    Files: f1.java, f2.java
    [Show diff]   ← expands diff in code block
"""
from __future__ import annotations

import json
from pathlib import Path

from ..searcher import search
from ..backends import get_backend
from ..config import STORE_DIR, DEFAULT_TOP_N, DEFAULT_TOP_K, DEFAULT_TOP_M


def _list_projects(store_dir: str = STORE_DIR) -> list[str]:
    p = Path(store_dir)
    if not p.exists():
        return ["default"]
    projects = [d.name for d in p.iterdir() if d.is_dir() and (d / "meta.json").exists()]
    return projects or ["default"]


def _zip_project(store_dir: str, project_id: str) -> str:
    """Zip .simargl/{project_id}/ into a temp file and return its path.

    meta.json is patched before zipping: db_path is reduced to basename only
    so it does not contain a server-side absolute path.
    """
    import zipfile, tempfile, json as _json
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
                    meta['db_path'] = Path(meta['db_path']).name  # basename only
                zf.writestr(str(Path(project_id) / f.name),
                            _json.dumps(meta, indent=2))
            else:
                zf.write(f, arcname=str(Path(project_id) / f.name))
    return tmp.name


def _format_files(files: list[dict]) -> str:
    if not files:
        return "_No files found._"
    lines = []
    for f in files:
        lines.append(f"`{f['score']:.3f}`  **{f['path']}**  `[{f['module']}]`")
    return "\n\n".join(lines)


def _format_modules(modules: list[dict]) -> str:
    if not modules:
        return "_No modules found._"
    return "\n\n".join(
        f"`{m['score']:.3f}`  **{m['module']}**" for m in modules
    )


def _format_units(units: list[dict]) -> str:
    if not units:
        return "_No similar tasks/commits._"
    parts = []
    for u in units:
        unit_type = u["unit_type"].capitalize()
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


def _run_search(query, mode, sort, project_id, top_n, top_k, top_m,
                include_diff, store_dir):
    if not query.strip():
        yield "_Enter a query._", "", ""
        return

    yield "_Searching..._", "_Searching..._", "_Searching..._"

    try:
        result = search(
            query, mode=mode, sort=sort,
            top_n=int(top_n), top_k=int(top_k), top_m=int(top_m),
            include_diff=include_diff,
            project_id=project_id, store_dir=store_dir,
        )
    except Exception as e:
        yield f"**Error:** {e}", "", ""
        return

    files_md   = _format_files(result["files"])
    modules_md = _format_modules(result["modules"])
    units_md   = _format_units(result["units"])
    yield files_md, modules_md, units_md


def build_app(store_dir: str = STORE_DIR):
    try:
        import gradio as gr
    except ImportError:
        raise ImportError(
            "Gradio not installed. Run: pip install simargl[ui]"
        )

    project_root = Path(store_dir).resolve().parent
    project_name = project_root.name

    projects = _list_projects(store_dir)

    with gr.Blocks(title=f"simargl — {project_name}", theme=gr.themes.Monochrome()) as app:
        gr.Markdown(f"## simargl — task-to-code retrieval :: {project_name}")

        with gr.Row():
            query_box = gr.Textbox(
                label="Query",
                placeholder='e.g. "add buildString to project analysis search response"',
                scale=4,
            )
            search_btn = gr.Button("Search", variant="primary", scale=1)

        with gr.Row():
            mode_dd = gr.Dropdown(
                choices=["task", "file", "aggr"],
                value="task",
                label="Mode",
                info="task=via history  file=direct  aggr=centroid",
            )
            sort_dd = gr.Dropdown(
                choices=["rank", "freq"],
                value="rank",
                label="Sort",
                info="rank=similarity  freq=popularity (task mode only)",
            )
            project_dd = gr.Dropdown(
                choices=projects,
                value=projects[0],
                label="Project",
            )
            include_diff_cb = gr.Checkbox(label="Include diffs", value=False)

        with gr.Accordion("Advanced", open=False):
            with gr.Row():
                top_n_sl = gr.Slider(1, 30, value=DEFAULT_TOP_N, step=1, label="Top N files")
                top_k_sl = gr.Slider(1, 50, value=DEFAULT_TOP_K, step=1, label="Top K units")
                top_m_sl = gr.Slider(1, 15, value=DEFAULT_TOP_M, step=1, label="Top M modules")
            store_dir_box = gr.Textbox(value=store_dir, label="Store dir (.simargl/)")

        with gr.Row():
            with gr.Column(scale=2):
                gr.Markdown("### Files")
                files_out = gr.Markdown()
            with gr.Column(scale=1):
                gr.Markdown("### Modules")
                modules_out = gr.Markdown()

        gr.Markdown("### Similar tasks / commits")
        units_out = gr.Markdown()

        # refresh project list when store_dir changes
        def refresh_projects(sd):
            new_projects = _list_projects(sd)
            return gr.Dropdown(choices=new_projects, value=new_projects[0] if new_projects else "default")

        store_dir_box.change(refresh_projects, inputs=store_dir_box, outputs=project_dd)

        inputs = [query_box, mode_dd, sort_dd, project_dd,
                  top_n_sl, top_k_sl, top_m_sl, include_diff_cb, store_dir_box]
        outputs = [files_out, modules_out, units_out]

        search_btn.click(_run_search, inputs=inputs, outputs=outputs,
                          show_progress="full")
        query_box.submit(_run_search, inputs=inputs, outputs=outputs,
                         show_progress="full")

        # ── Download ──────────────────────────────────────────────────────
        with gr.Accordion("Download index", open=False):
            gr.Markdown(
                "Download the full index for a project as a ZIP file.\n\n"
                "Extract on your local machine as `.simargl/` and run `simargl search` or "
                "`simargl status` locally. All six index files are included.\n\n"
                "`db_path` in `meta.json` is automatically reduced to a bare filename "
                "so it contains no server-side absolute paths."
            )
            with gr.Row():
                dl_project_dd = gr.Dropdown(
                    choices=projects, value=projects[0], label="Project to download"
                )
                dl_btn = gr.Button("Prepare ZIP", variant="primary")
            dl_file = gr.File(label="Download", interactive=False)

            def _prepare_zip(sd, pid):
                return _zip_project(sd, pid)

            dl_btn.click(_prepare_zip,
                         inputs=[store_dir_box, dl_project_dd],
                         outputs=dl_file)

            # keep download project list in sync with store_dir changes
            store_dir_box.change(refresh_projects, inputs=store_dir_box,
                                 outputs=dl_project_dd)

    return app


def main(port: int = 7861, host: str = "0.0.0.0", store_dir: str = STORE_DIR):
    app = build_app(store_dir=store_dir)
    print(f"simargl UI — open: http://localhost:{port}")
    app.launch(server_name=host, server_port=port)
