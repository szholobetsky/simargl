I18N.en = {
  // header, scope
  tagline: 'task-to-code search over the task history',
  tab_search: 'Search', tab_rrf: 'RRF', tab_retrieve: 'Retrieve', tab_blackhole: 'Blackholes', tab_index: 'Index',
  tab_status: 'Status', 
  store_title: 'Store: a .simargl folder of a project', project_title: 'Index inside the store (and the model it was built with)',
  theme_title: 'Theme — the same themes as vyrii, alkonost, gamayun and svitovyd', lang_title: 'Language',
  refresh_title: 'Look for stores again', theme_auto: 'Simargl (auto)',
  select_store: 'Select store…', select_index: 'Select index…',
  scope_choose: 'Choose a store and an index above.',
  scope_none: 'No index yet — build one on the Index page, or start simargl in a project folder (the UI looks under {dir}). The dataset is gathered by mokosh: mokosh ui.',
  scope_on: 'Store <b>{name}</b> — {store}', scope_index: 'index <b>{p}</b> · {m} · {d} dims · {what}',
  has_units: 'tasks', has_files: 'code',
  choose_store_first: 'choose a store first', choose_index_first: 'choose an index first',
  searching: 'searching… (the first search loads the model or asks Ollama)', computing: 'computing…', loading: 'loading…',
  none: 'nothing', show: 'Show', copy: 'Copy', copied: 'copied', starting: 'starting…', job_done: '— done',

  // search
  query_ph: 'Paste a task: title and description…',
  mode: 'mode', mode_task: 'task — similar past tasks', mode_file: 'file — code chunks', mode_aggr: 'aggr — tasks + code',
  mode_refine: 'refine — tasks, then code', sort: 'sort', sort_rank: 'rank — best similarity', sort_freq: 'freq — how many similar tasks',
  top_n: 'files', top_n_title: 'how many files to return', top_k: 'similar tasks', top_k_title: 'how many similar past tasks vote for files',
  top_m: 'modules', top_m_title: 'how many modules to return',
  score_blend: 'score blend', blend_title: '1 = similarity only; lower mixes in how often a file was changed',
  coverage_penalty: 'coverage penalty', penalty_title: 'push down files that answer too many queries (needs coverage scores — Blackholes page)',
  refine_k: 'refine: tasks', refine_m: 'refine: modules', include_diff: 'with diffs', exclude_bh: 'skip blackholes',
  search_btn: 'Search', search_status: '{ms} ms · {f} files · {u} similar tasks',
  h_files: 'Files', h_modules: 'Modules', h_units: 'Similar past tasks', h_sources: 'Sources',
  h_answer_map: 'The answer as a map',
  answer_map_note: 'Similar past tasks (circles, larger = more similar) and the files they changed (squares). A file many of them changed is where the answer converges; the files simargl returned are coloured.',
  lg_task: 'similar task', lg_file_found: 'file in the answer', lg_file_other: 'file the tasks changed', lg_size_map: 'size = similarity (task), how many tasks changed it (file)',
  lone_tasks: 'similar tasks that share no file with the others',
  tip_file_tasks: 'changed by {n} of these tasks', tip_found: 'in the answer',
  changed_files: '{n} files changed', diff: 'diff',
  search_guide_t: 'How the search works',
  search_guide_1: 'The task text is turned into a vector by the index\'s own model and compared with the vectors of past tasks (<b>task</b>) or of code chunks (<b>file</b>). In task mode the most similar past tasks vote for the files they changed: <b>rank</b> trusts the most similar ones, <b>freq</b> counts how many similar tasks changed a file. <b>aggr</b> mixes both; <b>refine</b> finds the modules through tasks first and then searches the code inside them.',
  search_guide_2: 'Modules are the first folders of the paths, scored by their files. <b>Blackholes</b> are files that come up for almost any query (huge config files, generated code); they can be skipped or pushed down. A search always uses the model the index was built with.',

  // rrf
  rrf_sources: 'Sources (mode : index)', rrf_k_title: 'the k of reciprocal rank fusion: score = Σ 1 / (k + rank)',
  no_sources: 'This store has no index yet.',
  rrf_help: 'Runs one search per source and merges them by rank position — <b>reciprocal rank fusion</b>: raw scores are dropped, so indexes built with different models can be merged. A file found by several sources rises.',

  // retrieve
  top_n_chunks: 'chunks', source_dir: 'source folder (optional)', source_dir_ph: 'where the code is now, to read the current text',
  retrieve_btn: 'Retrieve', chars_n: '{n} characters',
  retrieve_help: 'Text ready to paste into an LLM\'s context: the most relevant code chunks (file mode) or past tasks (task mode), with their paths. With a source folder the current text of the files is read instead of the indexed one.',

  // blackholes
  bh_method: 'method', bh_centroid: 'centroid — close to the centre of everything', bh_coverage: 'coverage — answers too many random queries',
  bh_float: 'coverage scores — re-rank, mark nothing', bh_threshold: 'threshold', bh_queries: 'test queries',
  bh_detect: 'Detect', bh_list: 'List marked', bh_marked: 'Marked files ({n})',
  bh_help: 'A <b>blackhole</b> is a file whose vectors sit near everything, so it shows up for almost any task. <b>Centroid</b> marks files close to the centre of the whole index; <b>coverage</b> asks random queries and marks files that answer more than the threshold share; <b>coverage scores</b> only stores a score per file for the coverage penalty.',

  // index
  models_t: 'Embedding models', pull_title: 'an ollama:// model to pull into Ollama (ollama://name or ollama://name@host)',
  pull_btn: 'Pull into Ollama', host_ph: 'another Ollama host, e.g. panteon.local', refresh_models: 'Look again',
  model_default: 'New indexes use {m} unless another model is chosen.',
  torch_yes: 'torch is installed: local models {list} run here, fast for indexing many tasks.',
  torch_no: 'torch is not installed: local models need <code>pip install simargl[torch]</code>; Ollama models need nothing here.',
  ollama_batch: '{n} texts per request', ollama_none: 'no models, or not reachable',
  units_t: 'Index the task history', index_name: 'index name', db_path: 'task database (optional)',
  db_ph: 'default: the database of .mokosh/project.yaml', model: 'model', model_ph: 'default: ollama://granite-embedding:30m',
  units_mode: 'units', index_btn: 'Index',
  files_t: 'Index the code', source_folder: 'source folder', chunk_size: 'chunk size', full_rebuild: 'rebuild all',

  vacuum_btn: 'Vacuum the chosen index',
  index_help: 'An index remembers its model, and every search uses that model again — an index built with Ollama searches through Ollama, one built with a local model needs torch. Local models (<code>pip install simargl[torch]</code>) are usually faster for indexing tens of thousands of tasks; Ollama needs nothing on this device and can run on another machine (<code>ollama://granite-embedding:30m@host</code>). <b>Ingest</b> runs mokosh: commits of the repository and the tasks of the tracker into the database. <b>Vacuum</b> drops the vectors of deleted files.',

  // status
  st_index: 'Index {p}', st_store: 'Store', download_zip: 'download the index (zip)',

  // triangulation
  tab_tri: 'Triangulation', x_none: '— none —', x_code_project: 'code', x_depth: 'files per tool', x_btn: 'Triangulate',
  x_status: '{ms} ms · {n} tools · {moved} moved paths resolved through the map',
  x_tool_line: '{n} files · {s} s', x_idents: 'words of the task that lead into the code', x_word_title: '{i} identifiers · {f} files',
  x_top: 'The fused answer (top {n} below the strip)', x_group_3: 'all three: {n}', x_group_2: 'two of three: {n}', x_group_1: 'one tool only: {n}',
  x_was: 'in the task history as {p}', x_each: 'each tool on its own',
  x_companion: 'companion · {p} of past tasks', x_companion_title: 'Changes with a large share of all tasks (a registry, a messages file, the build). Often part of the change, rarely its core — kept in place, only marked.',
  x_gone: 'not in today’s code', x_gone_title: 'The task history remembers this path, but today’s code (the svitovyd map) has no such file and no file of the same name.',
  x_guide_t: 'How triangulation works',
  x_guide_1: 'Three tools answer the same task on their own: <b>simargl</b> by meaning (past tasks like this one and the files they changed), <b>gamayun</b> by statistics (words that significantly lead to files, co-change), <b>svitovyd</b> by structure (the task’s words become the identifiers they name, the identifiers lead to the files that define them). The answers are merged by <b>reciprocal rank fusion</b> with equal weights — each tool adds 1 / (60 + rank) to a file. In the experiment (simrgl exp10, SonarQube, 200 held-out tasks) the tools shared about one file in fifteen of their top 10s, and the fusion beat the best of them on every measure (hit@10 0.62 → 0.755); tuned weights did no better.',
  x_guide_2: 'The coloured numbers are each tool\'s rank for the file. A file all three name is the safest bet; a file only history names is often a companion (a test, a message file); a file only the code names is new ground no past task touched. The task history remembers paths as they were: with a svitovyd map chosen, a path that no longer exists is read as the one file of today\'s code with the same name, so the votes for a moved file add up.',
};
