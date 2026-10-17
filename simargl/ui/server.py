"""simargl web UI — Flask API + static pages (simargl/ui/webui, no build step).

Start:  simargl ui [--port 8099] [--store-dir .simargl] [--root FOLDER] [--host 127.0.0.1]

A store is a .simargl folder with one sub-folder per index ("project": meta.json + vectors). The
dataset the indexes are built from — project.yaml, the ingest — is mokosh's (`mokosh ui`). Stores
are found under the folder the UI was started in, remembered in ~/.simargl/stores.json once
opened, and every request names its store (and index).

  GET  /api/stores                                     known stores with their indexes
  POST /api/stores/open    {path}                      open a store (a .simargl folder or its parent)
  POST /api/models         {}                          default model, local models, torch?, Ollama models
  POST /api/search         {store, project, query, mode, sort, top_n, top_k, top_m, ...}
  POST /api/rrf            {store, query, sources, top_n, top_k, k, sort, score_blend, coverage_penalty}
  POST /api/retrieve       {store, project, query, mode, top_n, ...}  text for an LLM's context
  POST /api/blackhole      {store, project, method, threshold, n_queries, top_k, list_only}
  POST /api/status         {store, project}            index stats
  POST /api/admin          {store, project, action: vacuum|units|files, ...}  -> {job}
  POST /api/pull           {model}                     pull an ollama:// model into Ollama -> {job}
  GET  /api/jobs/<id>                                  {status, log, error}
  GET  /api/tri/sources                                gamayun projects and svitovyd maps on this machine
  POST /api/triangulate    {store, project, gamayun, map, query, k}  the three tools on one task, fused
  GET  /api/download?store=&project=                   the index as a zip
"""
from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import threading
import traceback
import uuid
import zipfile
from collections import defaultdict
from pathlib import Path

from flask import Flask, jsonify, request, send_file, send_from_directory

from ..config import DEFAULT_MODEL, LEGACY_MODEL, MODELS, OLLAMA_BATCH, STORE_DIR

UI_DIR = Path(__file__).parent / "webui"
HOME = Path.home() / ".simargl"
REGISTRY = HOME / "stores.json"
SKIP = {".git", "node_modules", "venv", ".venv", "__pycache__", "build", "dist", "target", ".idea"}

_start = None
_jobs = {}


# ── stores ───────────────────────────────────────────────────────────────────

def _registry() -> list:
    try:
        return [p for p in json.loads(REGISTRY.read_text(encoding="utf-8")) if isinstance(p, str)]
    except (OSError, ValueError):
        return []


def _remember(store: str):
    p = os.path.abspath(store)
    rest = [x for x in _registry() if os.path.abspath(x) != p]
    HOME.mkdir(parents=True, exist_ok=True)
    REGISTRY.write_text(json.dumps([p] + rest[:49], indent=1), encoding="utf-8")


def _is_store(path) -> bool:
    p = Path(path)
    if not p.is_dir():
        return False
    return (p / "project.yaml").is_file() or any((d / "meta.json").is_file() for d in p.iterdir() if d.is_dir())


def _discover(start, max_depth=4) -> list:
    out = []
    if not start or not os.path.isdir(start):
        return out
    base = len(Path(start).parts)
    for dirpath, dirnames, _ in os.walk(start):
        if len(Path(dirpath).parts) - base >= max_depth:
            dirnames[:] = []
        if os.path.basename(dirpath) == STORE_DIR:
            if _is_store(dirpath):
                out.append(dirpath)
            dirnames[:] = []
            continue
        dirnames[:] = [d for d in dirnames if d == STORE_DIR or (d not in SKIP and not d.startswith("."))]
    return out


def _indexes(store) -> list:
    out = []
    for d in sorted(Path(store).iterdir()):
        meta = d / "meta.json"
        if d.is_dir() and meta.is_file():
            try:
                m = json.loads(meta.read_text(encoding="utf-8"))
            except ValueError:
                m = {}
            out.append({"project": d.name, "model_key": m.get("model_key", LEGACY_MODEL), "dim": m.get("dim"),
                        "indexed_at": m.get("indexed_at", ""), "unit_mode": m.get("unit_mode", ""),
                        "files": (d / "files.int8").is_file(), "units": (d / "units.int8").is_file()})
    return out


def _describe(store):
    p = os.path.abspath(store)
    return {"store": p, "root": os.path.dirname(p), "name": os.path.basename(os.path.dirname(p)),
            "has_yaml": os.path.isfile(os.path.join(p, "project.yaml")), "indexes": _indexes(p)}


def _store_arg(b) -> str:
    s = (b.get("store") or "").strip()
    if not s:
        raise ValueError("choose a store first")
    if not _is_store(s):
        raise FileNotFoundError(f"not a simargl store: {s}")
    return os.path.abspath(s)


def _project_arg(store, b) -> str:
    pid = (b.get("project") or "").strip()
    if not pid or "/" in pid or "\\" in pid or pid.startswith("."):
        raise ValueError("choose an index first")
    if not (Path(store) / pid / "meta.json").is_file():
        raise FileNotFoundError(f"no index '{pid}' in {store}")
    return pid


def _num(b, key, default, cast=int, lo=None, hi=None):
    try:
        v = cast(b.get(key, default))
    except (TypeError, ValueError):
        v = default
    if lo is not None:
        v = max(lo, v)
    if hi is not None:
        v = min(hi, v)
    return v


# ── jobs ─────────────────────────────────────────────────────────────────────

def _start_job(fn):
    jid = uuid.uuid4().hex[:12]
    job = {"status": "running", "log": [], "error": ""}
    _jobs[jid] = job

    def run():
        try:
            fn(job)
            if job["status"] == "running":
                job["status"] = "done"
        except Exception as e:
            job["status"] = "error"
            job["error"] = f"{type(e).__name__}: {e}"
            job["log"].append(traceback.format_exc())

    threading.Thread(target=run, daemon=True).start()
    return jid


def _cli_job(args, cwd):
    """Run the simargl CLI as a child process and stream its output into the job's log."""
    cmd = [sys.executable, "-c", "from simargl.ui.cli import main; main()", *args]

    def run(job):
        job["log"].append("$ simargl " + " ".join(args))
        env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")
        proc = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, encoding="utf-8", errors="replace", env=env)
        for line in proc.stdout:
            # tqdm redraws with \r: keep the last state of a line only
            line = line.rstrip("\n").split("\r")[-1]
            if line.strip():
                job["log"].append(line)
                del job["log"][:-400]
        proc.wait()
        if proc.returncode != 0:
            job["status"] = "error"
            job["error"] = f"exit code {proc.returncode}"
    return _start_job(run)


# ── triangulation: simargl (meaning), gamayun (statistics), svitovyd (structure) ──
# Each tool ranks files for the same task on its own; the answers are merged by reciprocal rank
# fusion with equal weights (simrgl exp10: the three find different files, equal weights carried over
# from dev to test better than tuned ones). Paths are compared as '/' paths relative to the repository.

TRI_K = 60
HUB_SHARE = 0.01        # a file changed by >= 1 % of past tasks is a companion of many changes (exp11)
_onto_cache = {}


def _norm(p):
    return str(p).replace("\\", "/").strip()


def _gamayun_projects():
    try:
        from gamayun import store as gstore
    except ImportError:
        return []
    out = []
    for p in gstore.list_projects(start=_start):
        src = p.get("source") or {}
        if (Path(p["dir"]) / "triples.txt").is_file():
            out.append({"project": p["project"], "dir": p["dir"], "repo": src.get("repo") or src.get("files") or p.get("root") or "",
                        "kind": "files" if src.get("files") else "tasks"})
    return out


def _svitovyd_maps():
    try:
        from svitovyd import server as sserver
    except ImportError:
        return []
    seen, out = set(), []
    for m in sserver._read_registry() + sserver._discover(_start):
        a = os.path.abspath(m)
        if a not in seen and os.path.isfile(a):
            seen.add(a)
            d = sserver._describe(a)
            out.append({"map": d["map"], "root": d["root"], "name": d["name"]})
    return out


def _gamayun_files(project_dir, text, k):
    from gamayun.onto import Onto
    from gamayun import pipeline
    path = Path(project_dir) / "triples.txt"
    key, mtime = str(path.resolve()), path.stat().st_mtime
    hit = _onto_cache.get(key)
    if not hit or hit[0] != mtime:
        hit = (mtime, Onto(path))
        _onto_cache[key] = hit
    params = pipeline.DEFAULT_PARAMS
    pj = Path(project_dir) / "params.json"
    if pj.is_file():
        p = json.loads(pj.read_text(encoding="utf-8"))
        params = {"module": p["module"], "file": p["file"]}
    res = hit[1].query(text).search(params, k)
    return [{"file": _norm(f["target"]), "score": f.get("score"),
             "why": ", ".join(e["term"] for e in f.get("evidence", [])[:4])} for f in res["files"]]


def _fuse(lists, k=TRI_K):
    score, ranks = defaultdict(float), defaultdict(dict)
    for tool, files in lists.items():
        for r, f in enumerate(files, 1):
            score[f] += 1.0 / (k + r)
            ranks[f][tool] = r
    order = sorted(score, key=lambda f: -score[f])
    return [{"file": f, "score": round(score[f], 5), "ranks": ranks[f], "tools": len(ranks[f])} for f in order]


# ── app ──────────────────────────────────────────────────────────────────────

def create_app():
    app = Flask(__name__, static_folder=None)

    @app.errorhandler(ValueError)
    @app.errorhandler(FileNotFoundError)
    @app.errorhandler(RuntimeError)
    def _bad(e):
        return jsonify({"error": str(e)}), 400

    @app.get("/")
    def index():
        return send_from_directory(UI_DIR, "index.html")

    @app.get("/ui/<path:name>")
    def ui(name):
        return send_from_directory(UI_DIR, name)

    @app.get("/api/stores")
    def stores():
        seen, out = set(), []
        for p in _registry() + _discover(_start):
            a = os.path.abspath(p)
            if a not in seen and _is_store(a):
                seen.add(a)
                out.append(_describe(a))
        return jsonify({"stores": out, "start": str(_start or "")})

    @app.post("/api/stores/open")
    def open_store():
        b = request.get_json(silent=True) or {}
        p = (b.get("path") or "").strip().strip('"')
        if os.path.isdir(os.path.join(p, STORE_DIR)):
            p = os.path.join(p, STORE_DIR)
        if not _is_store(p):
            raise ValueError(f"not a simargl store (a {STORE_DIR} folder with project.yaml or an index): {p}")
        _remember(p)
        return jsonify(_describe(p))

    @app.post("/api/models")
    def models():
        from ..embedder import ollama_models, parse_ollama_key, torch_available
        b = request.get_json(silent=True) or {}
        hosts = {"http://localhost:11434"}
        for s in _registry() + _discover(_start):
            if _is_store(s):
                for ix in _indexes(s):
                    if str(ix["model_key"]).startswith("ollama://"):
                        hosts.add(parse_ollama_key(ix["model_key"])[1])
        extra = (b.get("host") or "").strip()
        if extra:
            hosts.add(extra if "://" in extra else "http://" + extra)
        ollama = [{"host": h, "models": ollama_models(h)} for h in sorted(hosts)]
        return jsonify({"default": DEFAULT_MODEL, "legacy": LEGACY_MODEL, "local": list(MODELS),
                        "torch": torch_available(), "ollama": ollama, "ollama_batch": OLLAMA_BATCH})

    @app.post("/api/search")
    def search():
        from ..searcher import search as do_search
        b = request.get_json(silent=True) or {}
        store = _store_arg(b)
        pid = _project_arg(store, b)
        q = (b.get("query") or "").strip()
        if not q:
            raise ValueError("type a task: a title and a description")
        res = do_search(q, mode=b.get("mode") or "task", sort=b.get("sort") or "rank",
                        top_n=_num(b, "top_n", 10, lo=1, hi=200), top_k=_num(b, "top_k", 10, lo=1, hi=200),
                        top_m=_num(b, "top_m", 5, lo=1, hi=100), include_diff=bool(b.get("include_diff")),
                        exclude_blackholes=bool(b.get("exclude_blackholes")),
                        coverage_penalty=_num(b, "coverage_penalty", 0.0, float, 0.0, 1.0),
                        score_blend=_num(b, "score_blend", 1.0, float, 0.0, 1.0),
                        refine_top_k=_num(b, "refine_top_k", 10, lo=1, hi=200),
                        refine_top_m=_num(b, "refine_top_m", 8, lo=1, hi=100),
                        project_id=pid, store_dir=store)
        return jsonify(res)

    @app.post("/api/rrf")
    def rrf():
        from ..searcher import rrf_search
        b = request.get_json(silent=True) or {}
        store = _store_arg(b)
        q = (b.get("query") or "").strip()
        if not q:
            raise ValueError("type a task: a title and a description")
        sources = (b.get("sources") or "").strip()
        if not sources:
            raise ValueError("choose at least one source (mode:index)")
        return jsonify(rrf_search(q, sources=sources, top_n=_num(b, "top_n", 10, lo=1, hi=200),
                                  top_k=_num(b, "top_k", 10, lo=1, hi=200), k=_num(b, "k", 60, lo=1, hi=1000),
                                  sort=b.get("sort") or "freq", score_blend=_num(b, "score_blend", 1.0, float, 0.0, 1.0),
                                  coverage_penalty=_num(b, "coverage_penalty", 0.0, float, 0.0, 1.0), store_dir=store))

    @app.post("/api/retrieve")
    def retrieve():
        from ..searcher import retrieve as do_retrieve
        b = request.get_json(silent=True) or {}
        store = _store_arg(b)
        pid = _project_arg(store, b)
        q = (b.get("query") or "").strip()
        if not q:
            raise ValueError("type a task: a title and a description")
        src = (b.get("source_dir") or "").strip() or None
        text = do_retrieve(q, mode=b.get("mode") or "file", top_n=_num(b, "top_n", 5, lo=1, hi=50),
                           exclude_blackholes=bool(b.get("exclude_blackholes")),
                           coverage_penalty=_num(b, "coverage_penalty", 0.0, float, 0.0, 1.0),
                           score_blend=_num(b, "score_blend", 1.0, float, 0.0, 1.0),
                           project_id=pid, store_dir=store, source_dir=src)
        return jsonify({"text": text or ""})

    @app.post("/api/blackhole")
    def blackhole():
        from ..backends import make_backend
        b = request.get_json(silent=True) or {}
        store = _store_arg(b)
        pid = _project_arg(store, b)
        backend = make_backend("numpy", store_dir=store, project_id=pid)
        if b.get("list_only"):
            return jsonify({"paths": sorted(backend.blackhole_paths())})
        meta = backend.load_meta()
        method = b.get("method") or "centroid"
        thr = _num(b, "threshold", 0.85, float, 0.0, 1.0)
        if method == "coverage_float":
            r = backend.compute_file_coverage(meta["dim"], n_queries=_num(b, "n_queries", 200, lo=10, hi=5000),
                                              top_k=_num(b, "top_k", 10, lo=1, hi=200))
        elif method == "coverage":
            r = backend.compute_blackholes_coverage(meta["dim"], n_queries=_num(b, "n_queries", 200, lo=10, hi=5000),
                                                    threshold=thr, top_k=_num(b, "top_k", 10, lo=1, hi=200))
        else:
            r = backend.compute_blackholes(meta["dim"], threshold=thr)
        r["method"] = method
        r["paths"] = sorted(backend.blackhole_paths())
        return jsonify(r)

    @app.post("/api/status")
    def status():
        from ..backends import make_backend
        b = request.get_json(silent=True) or {}
        store = _store_arg(b)
        out = {"store": store}
        pid = (b.get("project") or "").strip()
        if pid:
            pid = _project_arg(store, b)
            out["stats"] = make_backend("numpy", store_dir=store, project_id=pid).stats()
            out["meta"] = json.loads((Path(store) / pid / "meta.json").read_text(encoding="utf-8"))
        return jsonify(out)

    @app.post("/api/admin")
    def admin():
        b = request.get_json(silent=True) or {}
        store = _store_arg(b)
        cwd = os.path.dirname(store)
        action = b.get("action")
        pid = (b.get("project") or "").strip()
        if not pid or "/" in pid or "\\" in pid or pid.startswith("."):
            raise ValueError("name the index (letters, digits, - and _)")
        model = (b.get("model") or "").strip()
        if action == "vacuum":
            _project_arg(store, b)
            return jsonify({"job": _cli_job(["vacuum", "--project", pid, "--store-dir", store], cwd)})
        if action == "units":
            db = (b.get("db") or "").strip()
            if not db:
                meta = Path(store) / pid / "meta.json"
                if meta.is_file():
                    db = json.loads(meta.read_text(encoding="utf-8")).get("db_path", "")
            if not db:
                # the database mokosh gathered: <project>/.mokosh/project.yaml, or an older .simargl/project.yaml
                import yaml
                for y in (Path(cwd) / ".mokosh" / "project.yaml", Path(store) / "project.yaml"):
                    if y.is_file():
                        cfg = yaml.safe_load(y.read_text(encoding="utf-8")) or {}
                        db = os.path.join(cwd, (cfg.get("project") or {}).get("db", "units.db"))
                        break
            if not db:
                raise ValueError("give the task database (units.db) — mokosh gathers it: mokosh ui")
            args = ["index", "units", db, "--project", pid, "--store-dir", store]
            if b.get("mode") in ("tasks", "commits"):
                args += ["--mode", b["mode"]]
            if model:
                args += ["--model", model]
            return jsonify({"job": _cli_job(args, cwd)})
        if action == "files":
            src = (b.get("source") or "").strip()
            if not src or not os.path.isdir(src):
                raise ValueError("give the folder to index (the source code)")
            args = ["index", "files", src, "--project", pid, "--store-dir", store,
                    "--chunk-size", str(_num(b, "chunk_size", 400, lo=50, hi=4000))]
            if model:
                args += ["--model", model]
            if b.get("full"):
                args.append("--full")
            return jsonify({"job": _cli_job(args, cwd)})
        raise ValueError("unknown action")

    @app.post("/api/pull")
    def pull():
        from ..embedder import ollama_pull
        b = request.get_json(silent=True) or {}
        key = (b.get("model") or "").strip()
        if not key.startswith("ollama://"):
            raise ValueError("only ollama:// models are pulled here; local models download on first use")

        def run(job):
            ollama_pull(key, log=lambda s: (job["log"].append(str(s)), job["log"].__delitem__(slice(None, -200))))
        return jsonify({"job": _start_job(run)})

    @app.get("/api/tri/sources")
    def tri_sources():
        return jsonify({"gamayun": _gamayun_projects(), "svitovyd": _svitovyd_maps()})

    @app.post("/api/triangulate")
    def triangulate():
        import time
        from ..searcher import search as do_search
        b = request.get_json(silent=True) or {}
        q = (b.get("query") or "").strip()
        if not q:
            raise ValueError("type a task: a title and a description")
        k = _num(b, "k", 50, lo=5, hi=200)
        tools, errors, times = {}, {}, {}
        if b.get("store") and b.get("project"):
            try:
                t0 = time.time()
                store = _store_arg(b)
                pid = _project_arg(store, b)
                res = do_search(q, mode=b.get("mode") or "task", sort=b.get("sort") or "freq",
                                top_n=k, top_k=_num(b, "top_k", 10, lo=1, hi=200), project_id=pid, store_dir=store)
                tools["simargl"] = [{"file": _norm(f["path"]), "score": round(float(f["score"]), 4), "why": f.get("module", "")}
                                    for f in res["files"] if f["path"] and f["path"] != "unknown"]   # the no-path placeholder
                times["simargl"] = round(time.time() - t0, 2)
            except Exception as e:
                errors["simargl"] = str(e)
        gdir = (b.get("gamayun") or "").strip()
        if gdir:
            try:
                t0 = time.time()
                if not (Path(gdir) / "triples.txt").is_file():
                    raise FileNotFoundError(f"no gamayun ontology in {gdir}")
                tools["gamayun"] = _gamayun_files(gdir, q, k)
                times["gamayun"] = round(time.time() - t0, 2)
            except Exception as e:
                errors["gamayun"] = str(e)
        mp = (b.get("map") or "").strip()
        idents = []
        if mp:
            try:
                t0 = time.time()
                from svitovyd import graph as G
                from svitovyd.server import _is_map
                if not _is_map(mp):
                    raise ValueError(f"not a svitovyd map: {mp}")
                r = G.files_for_text(G.load(mp), q, k)           # the map only
                tools["svitovyd"] = [{"file": x["file"], "score": x["score"], "why": ", ".join(x["names"])} for x in r["files"]]
                idents = r["words"]
                times["svitovyd"] = round(time.time() - t0, 2)
            except Exception as e:
                errors["svitovyd"] = str(e)
        if not tools and not errors:
            raise ValueError("choose at least one source: a simargl index, a gamayun project or a svitovyd map")
        # history remembers paths as they were; with a map, a path that no longer exists is read as
        # the one file of today's code with the same name, if there is exactly one (a moved file)
        moved = {}
        if mp and "svitovyd" not in errors:
            from svitovyd import graph as G
            files_now = G.load(mp).files
            now = set(files_now)
            by_name = defaultdict(list)
            for f in files_now:
                by_name[f.rsplit("/", 1)[-1]].append(f)
            for t, lst in tools.items():
                for x in lst:
                    f = x["file"]
                    if f not in now:
                        cand = by_name.get(f.rsplit("/", 1)[-1], [])
                        if len(cand) == 1:
                            moved[f] = cand[0]
                            x["now"] = cand[0]
        lists = {}
        for t, v in tools.items():
            seen, lst = set(), []
            for x in v:
                f = moved.get(x["file"], x["file"])
                if f not in seen:
                    seen.add(f)
                    lst.append(f)
            lists[t] = lst
        fused = _fuse(lists)
        was = defaultdict(set)
        for old_path, new_path in moved.items():
            was[new_path].add(old_path)
        for x in fused:
            if was.get(x["file"]):
                x["was"] = sorted(was[x["file"]])
        # companions: files that change with a large share of all tasks (core.properties, build.gradle, the
        # component registries). Often right, rarely the core of the change — marked, never dropped (exp11)
        if gdir and "gamayun" not in errors:
            O = _onto_cache[str((Path(gdir) / "triples.txt").resolve())][1]
            if O.N:
                for x in fused:
                    n = max([O.count["file"].get(p, 0) for p in [x["file"]] + x.get("was", [])])
                    if n / O.N >= HUB_SHARE:
                        x["share"] = round(n / O.N, 3)
        # a path the history remembers but today's code no longer has (and no moved twin was found)
        if mp and "svitovyd" not in errors:
            for x in fused:
                if x["file"] not in now:
                    x["gone"] = True
        top = min(10, k)
        sets = {t: set(v[:top]) for t, v in lists.items()}
        names = list(sets)
        overlap = {}
        for i, a in enumerate(names):
            for b2 in names[i + 1:]:
                u = sets[a] | sets[b2]
                overlap[f"{a}|{b2}"] = round(len(sets[a] & sets[b2]) / len(u), 3) if u else 0.0
        return jsonify({"tools": tools, "errors": errors, "times": times, "identifiers": idents,
                        "fused": fused[:k], "top": top, "overlap": overlap, "moved": len(moved)})

    @app.get("/api/jobs/<jid>")
    def job(jid):
        j = _jobs.get(jid)
        if not j:
            raise ValueError("unknown job")
        return jsonify(j)

    @app.get("/api/download")
    def download():
        store = _store_arg({"store": request.args.get("store", "")})
        pid = _project_arg(store, {"project": request.args.get("project", "")})
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in sorted((Path(store) / pid).iterdir()):
                if not f.is_file():
                    continue
                if f.name == "meta.json":
                    meta = json.loads(f.read_text(encoding="utf-8"))
                    if "db_path" in meta:
                        meta["db_path"] = Path(meta["db_path"]).name     # no local paths in a shared index
                    zf.writestr(f"{pid}/meta.json", json.dumps(meta, indent=2))
                else:
                    zf.write(f, arcname=f"{pid}/{f.name}")
        buf.seek(0)
        return send_file(buf, as_attachment=True, download_name=f"{pid}.zip", mimetype="application/zip")

    return app


def serve(host="127.0.0.1", port=8099, store_dir=STORE_DIR, start=None):
    global _start
    _start = os.path.abspath(start or os.getcwd())
    if store_dir and _is_store(store_dir):
        _remember(store_dir)
    from waitress import serve as waitress_serve
    print(f"simargl UI: http://{'127.0.0.1' if host in ('0.0.0.0', '') else host}:{port}/")
    waitress_serve(create_app(), host=host, port=port, threads=8)
