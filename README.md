# simargl

**S**emantic **I**ndex: **M**ap **A**rtifacts, **R**etrieve from **G**it **L**og

Task-to-code retrieval. Given a description of a change, finds which files and modules are likely affected — using semantic similarity over historical tasks or commits.

Exposes an MCP server (stdio transport) compatible with any MCP-aware agent system.

---

## Install

```bash
cd simargl
pip install -e .
```

The default embedding model (`bge-small`, ~130MB) is downloaded automatically during install.
If that fails or you installed offline, download it manually:

```bash
simargl download
```

---

## Step 1 — Index your project

You need two indexes: one for code files, one for tasks (or commits if no tracker).

```bash
# Index code files (walks the repo, chunks text files, stores vectors)
simargl index files C:/repos/sonar --project sonar

# Index tasks from SQLite (auto-detects tasks vs commits)
simargl index units C:/data/sonar.db --project sonar

# Check what was indexed
simargl status --project sonar
```

Both indexes land in `.simargl/sonar/` relative to your working directory.

Use `--model bge-large` if you need higher accuracy (uses more RAM and disk).

Available model keys:

```bash
# sentence-transformers — runs locally, CPU or GPU, downloads model on first use
--model bge-small                                  # default, 384 dims
--model bge-large                                  # better quality, 1024 dims

# Ollama — no model download, uses whatever is already pulled in Ollama
--model ollama://nomic-embed-text                  # localhost:11434
--model ollama://nomic-embed-text@192.168.1.10     # remote machine

# OpenAI-compatible local server — LM Studio, llama.cpp, LiteLLM, Jan, Koboldcpp
--model openai://localhost:1234/nomic-embed-text   # LM Studio
--model openai://localhost:8080/all-minilm         # llama.cpp server
--model openai://localhost:4000/nomic-embed-text   # LiteLLM
```

`openai://` means OpenAI-compatible API — no cloud, no API key, runs entirely locally.

---

## Step 2 — Connect to 1bcoder

Launch 1bcoder from your project directory — the MCP subprocess inherits that working
directory, so `.simargl` resolves correctly with no extra flags.

```bash
cd C:/Project/my-app
1bcoder
```

If you indexed with the default project_id (no `--project` flag):
```
/mcp connect simargl simargl-mcp
```

If you indexed with a custom project_id:
```
/mcp connect simargl simargl-mcp --project-id bookcrossing
```

The first connect takes 30–60 s while the embedding model loads — this is normal.
Tool calls are instant after that.

To connect to a project in a different directory without restarting 1bcoder, use `--cwd`:
```
/mcp connect simargl simargl-mcp --cwd C:/Project/other-app --project-id myproject
```

Check it connected:

```
/mcp tools simargl
```

You should see: `find`, `index_files`, `index_units`, `status`, `vacuum`, `embedding`, `distance`.

With `--project-id` set at server startup, you never need to pass `project_id` in tool calls.

---

## Step 3 — Index

1bcoder MCP call syntax is `/mcp call server/tool {json_args}`.

```
/mcp call simargl/index_files {"path": "C:/Project/my-app"}
```

If you have a task SQLite (Jira/GitHub export):
```
/mcp call simargl/index_units {"db_path": "C:/data/myproject.db"}
```

Check what was indexed:
```
/mcp call simargl/status {}
```

---

## Step 4 — Search

The call syntax is always `/mcp call simargl/tool {json}`.

### Find files related to a description

```
/mcp call simargl/find {"query": "make author field longer in the book class"}
```

Default mode is `task` + `sort=rank`. If you only indexed files (no task SQLite), use `mode=file`:

```
/mcp call simargl/find {"query": "make author field longer in the book class", "mode": "file"}
```

### All parameters

```
/mcp call simargl/find {
  "query": "make author field longer in the book class",
  "mode": "file",
  "top_n": 10
}
```

| param | values | default |
|---|---|---|
| `mode` | `task`, `file`, `aggr` | `task` |
| `sort` | `rank`, `freq` | `rank` |
| `top_n` | integer | 10 |
| `top_k` | integer | 10 |
| `include_diff` | true/false | false |
| `project_id` | string | `default` |
| `store_dir` | path | `.simargl` |

### If you used a custom project_id at index time

```
/mcp call simargl/find {"query": "add author field", "project_id": "bookcrossing"}
```

To avoid passing `project_id` every time, re-index without it (uses `default`):
```
/mcp call simargl/index_files {"path": "C:/Project/my-app"}
```

---

## Typical 1bcoder workflow

```
# 1. Find files
/mcp call simargl/find {"query": "make author field longer in the book class", "mode": "file"} -> find_result
/var set find_files matches

# 2. Read the most relevant files
/read {{find_files}}

# 3. Ask the model
make the author field longer in the Book class

# 4. Apply
/patch models.py code
```

---

## Other tools

### Check index status

```
/mcp call simargl/status {}
/mcp call simargl/status {"project_id": "bookcrossing"}
```

### Compute embedding for any text

```
/mcp call simargl/embedding {"text": "add user authentication to login flow"} -> vector1
```

Stores the vector as `{{vector1}}`. Use later with `distance`.

### Measure semantic distance between two things

```
/mcp call simargl/distance {"source1": "auth.py", "source2": "views.py"}
/mcp call simargl/distance {"source1": "add user auth", "source2": "auth.py"}
```

Returns cosine similarity (0–1).

### Vacuum (reclaim disk after many incremental re-indexes)

```
/mcp call simargl/vacuum {}
```

### Re-index after code changes

```bash
# Incremental (default) — only processes files modified since last run
simargl index files C:/repos/sonar --project sonar

# Full reindex — re-embeds everything regardless of mtime
simargl index files C:/repos/sonar --project sonar --full
```

Incremental index uses `mtime` comparison against the previous `indexed_at` timestamp:
- unchanged files → skipped
- modified files → old chunks soft-deleted, new chunks appended
- deleted files → chunks soft-deleted

Soft-deleted vectors stay in the int8 file until you vacuum. Run vacuum periodically
(e.g. after a big refactor) to reclaim disk space:

```bash
simargl vacuum --project sonar
# or from 1bcoder:
/mcp simargl vacuum
```

Units index is separate — re-run `index units` only when the SQLite is updated.

---

## Parameters reference

| Tool | Key params | Default |
|---|---|---|
| `find` | `mode` (tasks\|files), `sort` (rank\|freq), `top_n`, `top_k`, `top_m`, `include_diff` | tasks, rank, 10, 10, 5, false |
| `index_files` | `path`, `model_key`, `project_id`, `chunk_size` | —, bge-small, default, 400 |
| `index_units` | `db_path`, `model_key`, `project_id`, `mode` | —, bge-small, default, auto |
| `embedding` | `text` or `file`, `project_id` | — |
| `distance` | `source1`, `source2`, `project_id` | — |

---

## Multiple projects

```bash
simargl index units kafka.db --project kafka
simargl index files C:/repos/kafka --project kafka
```

```
/mcp simargl find "add partition rebalance" project_id=kafka
/mcp simargl status project_id=kafka
```

Each project stores its vectors in `.simargl/{project_id}/` independently.

---

## Running on Android (Termux) — LAN access from laptop

simargl runs fully on Android via Termux. With 8GB+ RAM (e.g. Redmi Note 14 Pro 12/512)
Ollama + nomic-embed-text + simargl-mcp all fit comfortably on the phone.
The laptop connects over LAN — no cloud, no GPU, everything local.

### Phone setup (Termux)

```bash
# base tools
pkg update && pkg install python git

# Ollama for Android (ARM64)
pkg install ollama
ollama serve &
ollama pull nomic-embed-text      # 274MB embedding model
# optional: ollama pull nemotron-mini  (if you want LLM on phone too)

# simargl
pip install simargl
pip install simargl[http]         # adds starlette + uvicorn for LAN transport

# index your project (copy SQLite and repo to phone storage first)
simargl index units /sdcard/data/sonar.db \
    --project sonar \
    --model ollama://nomic-embed-text

simargl index files /sdcard/repos/sonar \
    --project sonar \
    --model ollama://nomic-embed-text

# start MCP server on LAN
simargl-mcp --http --port 8765
# → simargl MCP server — http://0.0.0.0:8765/sse
```

### Laptop — connect to phone

Find phone IP: `ip addr` in Termux or check Wi-Fi settings.

**1bcoder:**
```
/mcp connect simargl http://192.168.1.42:8765/sse
/mcp tools simargl
```

**Claude Desktop** (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "simargl": {
      "url": "http://192.168.1.42:8765/sse"
    }
  }
}
```

**Claude Code / OpenCode / Cursor** — same URL pattern, see agent-specific config above.

### Keep server running in Termux background

```bash
# run in background, log to file
nohup simargl-mcp --http --port 8765 > ~/.simargl-mcp.log 2>&1 &

# or use tmux (pkg install tmux)
tmux new -s simargl
simargl-mcp --http --port 8765
# Ctrl+B D  to detach
```

### What runs where

| Component | Phone | Laptop |
|---|---|---|
| Vector index (.simargl/) | yes | — |
| Embedding model (nomic-embed-text) | yes (Ollama) | — |
| MCP server (simargl-mcp) | yes | — |
| Agent / LLM (1bcoder, Claude) | — | yes |
| Repo source files | yes (for indexing) | yes (for editing) |

The phone stores the index and computes embeddings. The laptop runs the agent and edits code.
Both use the same `.simargl/` directory — if you prefer, mount phone storage via sshfs
so the laptop can also run `simargl index` directly against it.

---

## Connecting to agent systems

simargl-mcp uses **stdio transport** — the universal MCP default. Always pass `--store-dir`
with the absolute path to your project root so the subprocess always finds `.simargl/`
regardless of which directory the agent system uses as its working directory.

### Claude Desktop

Config file:
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "simargl": {
      "command": "simargl-mcp",
      "args": ["--store-dir", "C:/repos/sonar/.simargl", "--project-id", "sonar"]
    }
  }
}
```

Restart Claude Desktop after editing. Tools appear automatically in the UI.

### Claude Code (CLI)

Option A — add to global settings `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "simargl": {
      "command": "simargl-mcp",
      "args": ["--store-dir", "C:/repos/sonar/.simargl", "--project-id", "sonar"]
    }
  }
}
```

Option B — connect interactively from any session (no restart needed):

```
/mcp add simargl simargl-mcp --store-dir C:/repos/sonar/.simargl --project-id sonar
```

Then call tools directly in your prompt:
```
use simargl find to locate files related to "add buildString to project analysis"
```

### OpenCode

Config file: `~/.config/opencode/config.json`

```json
{
  "mcp": {
    "simargl": {
      "command": ["simargl-mcp"],
      "cwd": "C:/repos/sonar"
    }
  }
}
```

### OpenAI Codex CLI

Config file: `~/.codex/config.yaml`

```yaml
mcp_servers:
  simargl:
    command: simargl-mcp
    cwd: C:/repos/sonar
```

### Cursor

Config file: `.cursor/mcp.json` in your project root (or global `~/.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "simargl": {
      "command": "simargl-mcp",
      "cwd": "${workspaceFolder}"
    }
  }
}
```

`${workspaceFolder}` resolves to the open project directory — simargl will look for `.simargl/` there.

### Windsurf (Codeium)

Config file: `~/.codeium/windsurf/mcp_settings.json`

```json
{
  "mcpServers": {
    "simargl": {
      "command": "simargl-mcp",
      "cwd": "C:/repos/sonar"
    }
  }
}
```

### Any other MCP-compatible system

The pattern is always the same:

```json
{
  "command": "simargl-mcp",
  "args": [],
  "cwd": "<directory where .simargl/ lives>"
}
```

If the agent system does not support `cwd`, pass it as an env variable instead and adjust the server startup — or simply `cd` to the right directory before launching.

---

### Tip: multiple projects across agents

If you work on several repos, use `project_id` to keep their indexes separate under the same `.simargl/` directory:

```
find files related to "add partition rebalance"  project_id=kafka
find files related to "add buildString to API"   project_id=sonar
```

---

## PostgreSQL + pgvector backend

For larger codebases or when you want sub-linear search via HNSW index.

```bash
pip install simargl[postgres]
```

Requires PostgreSQL with pgvector extension:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### Index with postgres backend

```bash
simargl index units sonar.db --project sonar \
    --backend postgres \
    --db-url postgresql://postgres:postgres@localhost/simargl

simargl index files C:/repos/sonar --project sonar \
    --backend postgres \
    --db-url postgresql://postgres:postgres@localhost/simargl
```

### MCP server with postgres

```bash
simargl-mcp --backend postgres \
    --db-url postgresql://postgres:postgres@localhost/simargl
```

### numpy vs postgres — when to choose which

| | numpy | postgres |
|---|---|---|
| Install | zero extra deps | psycopg2 + pgvector |
| Search speed | linear scan | sub-linear (HNSW) |
| Scales well to | ~500k chunks | millions of chunks |
| Vacuum | file rebuild | `DELETE` + `VACUUM ANALYZE` |
| Concurrent writes | no | yes |
| Termux / Android | yes | harder |
| Laptop / server | yes | yes |

For most projects (sonar.db = ~100k chunks) numpy is fast enough. Switch to postgres when search latency becomes noticeable or you index multiple large repos.

---

## Deferred (session 2)

- Ollama and OpenAI embedding providers (`ollama://nomic-embed`, `openai://text-embedding-3-small`)
- Mode `aggregated` — avg task vectors → file search
- Set operations: `/mcp simargl find "query" mode=tasks+files` (union/intersection)
- Gradio web UI (`simargl ui`)
- PostgreSQL backend (`pip install -e ".[postgres]"`)
