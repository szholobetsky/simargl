![simargl](https://raw.githubusercontent.com/szholobetsky/simrgl/main/images/logo/simargl.png)

# simargl

**S**emantic **I**ndex: **M**ap **A**rtifacts, **R**etrieve from **G**it **L**og

Task-to-code retrieval for software projects — given a description of a change, finds the files and modules it is likely to touch, by semantic search over the project's past tasks, commits and code, with local embedding models and no LLM.

## What it does

simargl builds vector indexes of a project:

- **units** — the past tasks (or commits) of the project, each linked to the files it changed,
  from the SQLite database that [mokosh](https://pypi.org/project/mokosh/) gathers;
- **files** — the code and documents themselves, cut into chunks.

A new task description is embedded the same way and compared with them. The answer is the files
and modules most likely to change, the similar past tasks behind them, and, if asked, their diffs.

Around that it offers:

- **search** in several modes: past tasks, code chunks, tasks averaged per file, and a query
  refined with the words of similar commits;
- **rrf** — several indexes merged by rank;
- **retrieve** — the matching text, ready to put into an LLM's context;
- **blackhole** — detect files that answer almost any query (generated files, changelogs) and push
  them down;
- **ui** — the same in the browser, plus **Triangulation**: one task asked of simargl,
  [gamayun](https://pypi.org/project/gamayun-ontology/) and [svitovyd](https://pypi.org/project/svitovyd/)
  at once;
- **an MCP server**, so AI agents can search the history and the code themselves.

Embeddings run through Ollama, any OpenAI-compatible local server, or sentence-transformers. The
index is a few plain files (int8 vectors and SQLite), and nothing leaves the machine.

---

## Statement of need

Most of what a developer needs to know about a new task is in the project's history: someone has
done something similar before, and the files they changed are where the new change will go. Plain
text search finds only the exact words, and a task is rarely written in the words of the code.
Code assistants that read the whole repository need a large model and send the code to it.

simargl searches the history by meaning, with small embedding models that run on a CPU, and points
to files, not only to past tasks. It is meant for:

- **developers** who need to find where a task leads in a large or unfamiliar code base;
- **AI coding agents**, including ones on small local models, that need the right files before
  they read anything (through the MCP server or the command line);
- **researchers in software engineering** who study task-to-code retrieval and change impact and
  need a reproducible retrieval baseline over real project histories.

---

## Install

```bash
pip install simargl              # core + web UI: numpy, Flask, mokosh — no torch
pip install "simargl[torch]"     # + local models via sentence-transformers (bge-small, bge-large, jina-code)
pip install "simargl[mcp]"       # + the MCP server (simargl serve, simargl-mcp)
pip install "simargl[http]"      # + MCP over HTTP/SSE (remote agents, LAN)
pip install "simargl[postgres]"  # + the PostgreSQL / pgvector backend
pip install "simargl[gradio]"    # + the older Gradio UI (simargl ui --gradio)
pip install "simargl[all]"       # torch + MCP + HTTP
```

Python 3.10+. The core has no torch, so it installs anywhere Python runs; the embedding model can
run in Ollama on the same machine or another one.

---

## Quick start

```bash
cd my-project                              # a git clone
mokosh init && mokosh ingest               # past tasks + commits -> units.db (installed with simargl)

simargl download                           # pull the default embedding model into Ollama
simargl index units units.db               # the past tasks
simargl index files .                      # the code
simargl status

simargl search "Login fails after the session expires"
simargl search "Login fails after the session expires" --mode file
simargl ui                                 # http://127.0.0.1:8099/
```

Both indexes go to `.simargl/default/` in the current folder. To refresh: `mokosh ingest`, then
`simargl index units` again; `simargl index files .` re-embeds only the files changed since the
last run.

---

## Commands

| Command | What it does |
|---|---|
| `simargl index units DB [--last N] [--mode auto\|tasks\|commits]` | Index the past tasks (or commits) of a mokosh database |
| `simargl index files PATH [--full] [--chunk-size N]` | Index code and documents (incremental; `--full` re-embeds everything) |
| `simargl search QUERY [--mode task\|file\|aggr\|refine]` | Files, modules and similar past tasks for a query |
| `simargl rrf QUERY --sources task:default,file:code` | Several indexes or modes merged by reciprocal rank fusion |
| `simargl retrieve QUERY` | The matching text, ready for an LLM's context |
| `simargl blackhole [--method coverage_float] [--list]` | Detect files that answer almost any query |
| `simargl status` | What an index holds |
| `simargl vacuum` | Reclaim the space of deleted vectors |
| `simargl download [--model M]` | Get an embedding model ready |
| `simargl ui [--port 8099] [--host 0.0.0.0] [--root FOLDER]` | The web UI |
| `simargl serve [--http --port 8765]` | The MCP server (also `simargl-mcp`) |
| `simargl about` | Version and authorship |

Common options: `--project P` keeps several indexes side by side (`.simargl/<P>/`), `--model M`
picks the embedding model, `--store-dir DIR` puts the store elsewhere, `--format json|paths|modules`
changes the output of `search`, `--diff` adds the diffs of the past tasks, `--top-n` / `--top-k` set
how many files and past tasks to return.

### Search modes

| Mode | How it finds files |
|---|---|
| `task` (default) | finds the most similar past tasks and returns the files they changed (`--sort rank` by similarity, `--sort freq` by how many of them changed the file) |
| `file` | compares the query with the chunks of the code itself |
| `aggr` | compares the query with every file's average over the past tasks that changed it |
| `refine` | expands the query with words from the most similar commits, then searches again |

`--last N` indexes only the N most recent tasks: in a project developed for years, recent work
describes today's code better than the whole history.

---

## Example

The output below comes from a small demo shop project: 300 synthetic tasks built from a few dozen
titles, and 13 Java files in the modules auth, checkout, billing and catalog.

```
$ simargl search "Customers are charged twice when two discount codes are used" --top-n 3 --top-k 5 --sort freq
Query: Customers are charged twice when two discount codes are used  mode=task  sort=freq

Files:
  4.000  checkout/src/PriceCalculator.java  [checkout]
  1.000  checkout/src/DiscountRule.java  [checkout]

Modules:
  4.000  checkout

Similar units:
  [0.766] SHOP-194 — Two discounts applied to one item
  [0.766] SHOP-236 — Two discounts applied to one item
  [0.766] SHOP-141 — Two discounts applied to one item
  [0.766] SHOP-217 — Two discounts applied to one item
  [0.766] SHOP-103 — Two discounts applied to one item
```

The five most similar past tasks were found, and the files they changed are counted: four of them
changed `PriceCalculator.java`, one `DiscountRule.java`.

---

## Embedding models

New indexes use `ollama://granite-embedding:30m` (63 MB, 384 dimensions) unless `--model` says
otherwise. An index records its model in `meta.json`, and every search uses that model again.

```bash
# Ollama: uses what is pulled into Ollama, on this machine or another
--model ollama://granite-embedding:30m            # default
--model ollama://nomic-embed-text
--model ollama://nomic-embed-text@192.168.1.10    # Ollama on another machine

# OpenAI-compatible local servers: LM Studio, llama.cpp, LiteLLM, Jan, Koboldcpp
--model openai://localhost:1234/nomic-embed-text  # LM Studio
--model openai://localhost:8080/all-minilm        # llama.cpp server

# sentence-transformers (needs simargl[torch]); usually the fastest for indexing a large history
--model bge-small                                 # 384 dimensions
--model bge-large                                 # 1024 dimensions, more RAM and disk
```

`openai://` means an OpenAI-compatible API on your own machine: no cloud and no API key.
`simargl download --model M` gets a model ready (pulls it into Ollama, or downloads a local one).

---

## Web UI

```bash
simargl ui                          # http://127.0.0.1:8099/
simargl ui --host 0.0.0.0           # reachable from other devices on the LAN
simargl ui --root ~/projects        # look for .simargl stores under this folder
```

The UI lists the `.simargl` stores under the folder it was started in and remembers every store
opened there or indexed by the CLI (`~/.simargl/stores.json`). One store and one index are worked on
at a time.

- **Search:** every mode and parameter; files with score bars, modules, the similar past tasks with
  their diffs, and the answer as a map: the similar tasks and the files they changed, so the files
  many of them share stand out.
- **Triangulation:** one task asked of three tools at once: simargl (similar past tasks), gamayun
  (words that significantly lead to files, files that change together) and svitovyd (identifiers
  of the task that the code defines). Their answers are merged by equal-weight reciprocal rank
  fusion; each file shows its rank in every tool, and a strip shows how many files all three, two
  or one of them named. With a svitovyd map, a path the history remembers but today's code no
  longer has is matched to the moved file or marked *not in today's code*. With a gamayun project,
  a file that changes with at least 1 % of all past tasks (a messages file, the build) is marked a
  *companion*: often part of a change, rarely its core.
- **RRF:** several sources (`task:default`, `file:code`, …) merged by rank.
- **Retrieve:** the matching text, ready for an LLM.
- **Blackholes:** files that answer almost any query.
- **Index:** the embedding models (what each Ollama host has, pull a model), index the history or
  the code, vacuum.
- **Status:** what the index holds, and the whole index as a ZIP to search it on another machine
  without re-indexing.

The UI has 8 colour themes and 6 languages (English, Ukrainian, German, French, Spanish,
Portuguese). The task database itself is set up in `mokosh ui`.

---

## MCP server

```bash
simargl-mcp                                # stdio, for local agents
simargl-mcp --http --port 8765             # HTTP/SSE, for remote agents and the LAN
simargl-mcp --store-dir /path/to/my-project/.simargl --project-id myproj
```

| Tool | What it does |
|---|---|
| `find` | files, modules and similar past tasks for a query (`mode`, `sort`, `top_n`, `top_k`, `include_diff`) |
| `rrf` | several sources merged by rank |
| `retrieve` | the matching text for an LLM's context |
| `index_files`, `index_units` | build or update an index |
| `status`, `vacuum`, `blackhole` | the index itself |
| `embedding`, `distance` | the vector of a text or file, and the cosine similarity of two |

The first connection takes 30–60 seconds while the embedding model loads; later calls are fast.
Pass `--store-dir` with an absolute path, so the server finds `.simargl/` whatever folder the agent
starts it in. With `--project-id` set, the tools need no `project_id` argument.

### Setup per agent

**Claude Desktop** (`%APPDATA%\Claude\claude_desktop_config.json` on Windows,
`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS) and **Claude Code**
(`~/.claude/settings.json`):

```json
{
  "mcpServers": {
    "simargl": {
      "command": "simargl-mcp",
      "args": ["--store-dir", "/path/to/my-project/.simargl", "--project-id", "myproj"]
    }
  }
}
```

Claude Code can also add it from a session:

```
/mcp add simargl simargl-mcp --store-dir /path/to/my-project/.simargl --project-id myproj
```

**OpenCode** (`~/.config/opencode/config.json`):

```json
{ "mcp": { "simargl": { "command": ["simargl-mcp"], "cwd": "/path/to/my-project" } } }
```

**OpenAI Codex CLI** (`~/.codex/config.yaml`):

```yaml
mcp_servers:
  simargl:
    command: simargl-mcp
    cwd: /path/to/my-project
```

**Cursor** (`.cursor/mcp.json` in the project, or `~/.cursor/mcp.json`):

```json
{ "mcpServers": { "simargl": { "command": "simargl-mcp", "cwd": "${workspaceFolder}" } } }
```

**Windsurf** (`~/.codeium/windsurf/mcp_settings.json`):

```json
{ "mcpServers": { "simargl": { "command": "simargl-mcp", "cwd": "/path/to/my-project" } } }
```

**A remote server** (any agent that takes a URL):

```json
{ "mcpServers": { "simargl": { "url": "http://192.168.1.42:8765/sse" } } }
```

**Any other MCP client:** the command is `simargl-mcp`, and its working folder (or `--store-dir`)
is where `.simargl/` lives.

### With 1bcoder

Start [1bcoder](https://pypi.org/project/1bcoder/) in the project folder, so the server finds
`.simargl/` there:

```
/mcp connect simargl simargl-mcp
/mcp connect simargl simargl-mcp --project-id myproj
/mcp connect simargl simargl-mcp --cwd /path/to/other-project --project-id other
/mcp tools simargl
```

A typical session:

```
/mcp call simargl/find {"query": "make the author field longer in the Book class", "mode": "file"} -> find_result
/var set find_files matches
/read {{find_files}}
make the author field longer in the Book class
/patch models.py code
```

---

## Running on another machine or a phone

The index, the embedding model, the MCP server and the web UI can all run on another machine on
the LAN: a server, a Raspberry Pi, or an Android phone with Termux. The laptop only opens the
browser or connects an agent.

```bash
# on the phone (Termux)
pkg update && pkg install python git ollama
ollama serve &
ollama pull nomic-embed-text
pip install "simargl[http]"

simargl index units /sdcard/data/units.db --project myproj --model ollama://nomic-embed-text
simargl index files /sdcard/repos/my-project --project myproj --model ollama://nomic-embed-text

nohup simargl-mcp --http --port 8765 > ~/.simargl-mcp.log 2>&1 &
simargl ui --host 0.0.0.0
```

```
# on the laptop
/mcp connect simargl http://192.168.1.42:8765/sse        # 1bcoder
http://192.168.1.42:8099/                                 # the web UI
```

| Component | Server / phone | Laptop |
|---|---|---|
| Index (`.simargl/`), embedding model, MCP server, web UI | yes | — |
| Agent / LLM (1bcoder, Claude, …) | — | yes |
| Source files | for indexing | for editing |

---

## PostgreSQL + pgvector backend

For very large indexes, or for search through an HNSW index instead of a linear scan:

```bash
pip install "simargl[postgres]"
psql -c "CREATE EXTENSION IF NOT EXISTS vector;"

simargl index units units.db --backend postgres --db-url postgresql://user:pass@localhost/simargl
simargl index files .         --backend postgres --db-url postgresql://user:pass@localhost/simargl
simargl-mcp                   --backend postgres --db-url postgresql://user:pass@localhost/simargl
```

| | numpy (default) | postgres |
|---|---|---|
| Install | nothing extra | psycopg2 + pgvector |
| Search | linear scan | HNSW (sub-linear) |
| Comfortable size | up to ~500k chunks | millions of chunks |
| Concurrent writes | no | yes |
| Phone / Termux | yes | harder |

---

## Python API

```python
from simargl.searcher import search, get_chunk_text

r = search("Login fails after the session expires", mode="task", top_n=10, top_k=10)
r["files"]      # [{"path", "score", "module"}, ...]
r["modules"]    # [{"module", "score"}, ...]
r["units"]      # the similar past tasks: unit_id, text_preview, similarity, files (+ diff with include_diff=True)

r = search("Login fails after the session expires", mode="file", top_n=5)
for f in r["files"]:
    print(f["path"], f["score"], get_chunk_text(f["path"], f["chunk_n"]))   # the chunk that matched
```

`project_id`, `store_dir`, `backend_type` and `db_url` select the index, as on the command line.

---

## Tests

```bash
git clone https://github.com/szholobetsky/simargl
cd simargl
pip install -e .
pip install pytest
pytest
```

## Support

The project is on GitHub: [github.com/szholobetsky/simargl](https://github.com/szholobetsky/simargl).
Questions, bug reports and suggestions go to its
[issues](https://github.com/szholobetsky/simargl/issues).

---

## Part of the SIMARGL toolkit

simargl is one of ten tools that together form an **intellectual development support system**:

| Tool | Role |
|---|---|
| **[simargl](https://github.com/szholobetsky/simargl)** | Task-to-code retrieval — given a task description, finds which files and modules are likely affected, using semantic similarity over git history |
| **[svitovyd](https://github.com/szholobetsky/svitovyd)** | Project map — scans any codebase and produces a structural map of definitions and cross-file dependencies; queried from the CLI, a web UI with a layered map, or an MCP server |
| **[1bcoder](https://github.com/szholobetsky/1bcoder)** | AI coding assistant for small local models — surgical context management, agents, parallel inference, proc scripts |
| **[yasna](https://github.com/szholobetsky/yasna)** | Session memory — indexes conversations from all AI agents so you can find what was discussed, when, and where |
| **[radogast](https://github.com/szholobetsky/radogast)** | Context drift monitor — measures how far an AI agent's conversation has drifted from the original task |
| **[vyrii](https://github.com/szholobetsky/vyrii)** | Local AI web UI — chat, translate, web research, RAG and file management in the browser (Flask; Gradio optional); powered by Ollama or any OpenAI-compatible backend |
| **[syryn](https://github.com/szholobetsky/syryn)** | Bluetooth identity beacon for headless devices — the device's IP is its Bluetooth name; hostname, mDNS and network interfaces on request |
| **[alkonost](https://github.com/szholobetsky/alkonost)** | Browser cockpit for 1bcoder's flows — the `deepagent_*` spec pipeline (plan tree → specs → task board) and the glossary (build, browse, search), tuned for small local models |
| **[gamayun](https://github.com/szholobetsky/gamayun)** | Statistical ontology without an LLM — builds triples of terms, identifiers, files and modules from task history or a folder of documents and code; every triple carries its significance test |
| **[mokosh](https://github.com/szholobetsky/mokosh)** | Dataset gathering — commits of a git repository and the tasks of its tracker (Jira, GitHub, GitLab, YouTrack) in one SQLite database that the other tools read |

- **simargl** finds the code related to a task by vector search over the task history (embeddings).
- **svitovyd** answers: *how is the code structured and what depends on what?*
- **1bcoder** answers: *how do I work with local models efficiently?*
- **yasna** answers: *where did I already discuss this?*
- **radogast** answers: *is the AI agent still on track toward the goal?*
- **vyrii** answers: *how do I access all of this through a browser?*
- **syryn** answers: *what is the address of this headless device?*
- **alkonost** answers: *how do I turn one task description into a reviewed, working plan — and see the project's glossary — without a big model or a big context window?*
- **gamayun** finds the code related to a task through an ontology of significant links between words, files and modules (no LLM).
- **mokosh** prepares the initial dataset from version control and the issue tracker.

Together they cover the full development loop: understand the codebase, find relevant history, work with AI locally, remember what was decided, and verify the context stays on target.

The name comes from Slavic mythology. Simargl (Симаргл) is a winged guardian spirit — a fiery dog with wings, protector of seeds and the earth, messenger between the heavens and the world of men. A fitting name for a tool that retrieves the seeds of code most relevant to any task.

---

## License

MIT. See [LICENSE](LICENSE).

## About

(c) 2026 Stanislav Zholobetskyi, Oleh Andriichuk  
Institute for Information Recording, National Academy of Sciences of Ukraine, Kyiv  
PhD research: «Intelligent Technology for Software Development and Maintenance Support»
