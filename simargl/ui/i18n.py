"""Internationalisation strings for simargl Gradio UI.

Usage:
    from . import i18n
    t = i18n.get("uk")   # returns dict of translated strings
    label = t["search_btn"]

To add a new language: add an entry to STRINGS with the lang code as key.
Missing keys fall back to English automatically (see get()).
"""
from __future__ import annotations

LANGS: list[str] = ["en", "uk"]

STRINGS: dict[str, dict[str, str]] = {

    # ── English ───────────────────────────────────────────────────────────────
    "en": {
        # app
        "app_title":  "SIMARGL | {project_name}",
        "app_header": "## SIMARGL | task-to-code retrieval :: {project_name}",
        "store_dir_label": "Store dir (.simargl/)",

        # tabs
        "tab_search":    "Search",
        "tab_rrf":       "RRF",
        "tab_retrieve":  "Retrieve",
        "tab_blackhole": "Blackhole",
        "tab_status":    "Status",
        "tab_admin":     "Admin",
        "tab_init":      "Init",
        "tab_settings":  "Settings",
        "tab_download":  "Download",

        # search
        "search_query_label":       "Query",
        "search_query_placeholder": 'e.g. "add buildString to project analysis search response"',
        "search_btn":               "Search",
        "search_mode_label":        "Mode",
        "search_mode_info":         "task=via history  file=direct  aggr=centroid  refine=query expansion",
        "search_sort_label":        "Sort",
        "search_sort_info":         "rank=similarity  freq=popularity (task mode only)",
        "search_project_label":     "Project",
        "search_diff_label":        "Include diffs",
        "search_advanced":          "Advanced",
        "search_top_n":             "Top N files",
        "search_top_k":             "Top K units",
        "search_top_m":             "Top M modules",
        "search_excl_bh":           "Exclude blackholes",
        "search_cov_pen_label":     "Coverage penalty λ",
        "search_cov_pen_info":      "Push down omnipresent files (needs coverage_float run first)",
        "search_blend_label":       "Score blend α",
        "search_blend_info":        "Topic concentration weight",
        "search_ref_k_label":       "Refine top-k commits",
        "search_ref_k_info":        "Query expansion source size (refine mode only)",
        "search_ref_m_label":       "Refine top-m terms",
        "search_ref_m_info":        "New terms added to query (refine mode only)",
        "search_files_header":      "### Files",
        "search_modules_header":    "### Modules",
        "search_units_header":      "### Similar tasks / commits",

        # rrf
        "rrf_desc": (
            "**Reciprocal Rank Fusion** — merge results from multiple sources "
            "(different modes or projects). Scores are rank-based, not raw similarity, "
            "so sources with different models are comparable."
        ),
        "rrf_query_label":   "Query",
        "rrf_btn":           "Search",
        "rrf_sources_label": "Sources",
        "rrf_sources_info":  'Comma-separated mode:project pairs. E.g. "task:default,file:jina,aggr:default"',
        "rrf_top_n":         "Top N files (merged)",
        "rrf_top_k":         "Top K per source",
        "rrf_k":             "RRF damping k",
        "rrf_sort_label":    "Sort (task sources)",
        "rrf_blend_label":   "Score blend α",
        "rrf_cov_pen_label": "Coverage penalty λ",
        "rrf_files_header":  "### Files (merged)",
        "rrf_modules_header":"### Modules",
        "rrf_src_header":    "### Per-source breakdown",

        # retrieve
        "ret_desc": "**Retrieve** — returns full file/task text for LLM context (use for RAG pipelines).",
        "ret_query_label":         "Query",
        "ret_btn":                 "Retrieve",
        "ret_mode_label":          "Mode",
        "ret_mode_info":           "file=file content  task=commit messages  aggr=centroid files",
        "ret_project_label":       "Project",
        "ret_top_n":               "Top N",
        "ret_excl_bh":             "Exclude blackholes",
        "ret_cov_pen":             "Coverage penalty λ",
        "ret_blend":               "Score blend α",
        "ret_source_dir_label":    "Source dir (optional)",
        "ret_source_dir_ph":       "/path/to/repo — read file contents from here",
        "ret_out_label":           "Retrieved context",

        # blackhole
        "bh_desc": (
            "**Detect semantic noise** — files that match every query equally "
            "(logs, changelogs, boilerplate). Three methods:\n\n"
            "- **centroid** — fast, marks files close to corpus centroid.\n"
            "- **coverage** — marks files appearing in top-k for >= threshold fraction of queries.\n"
            "- **coverage_float** _(recommended)_ — computes per-file coverage score, no binary cutoff. "
            "Use `coverage_penalty` in search to re-rank without hard filtering."
        ),
        "bh_project_label":    "Project",
        "bh_method_label":     "Method",
        "bh_threshold_label":  "Threshold",
        "bh_threshold_info":   "centroid: similarity to centroid (0.85)  coverage: query fraction (0.3)",
        "bh_n_queries_label":  "Test queries (coverage methods)",
        "bh_top_k_label":      "Top-k per query (coverage methods)",
        "bh_list_btn":         "List marked blackholes",
        "bh_detect_btn":       "Run detection",
        "bh_out_label":        "Result",

        # status
        "st_project_label": "Project",
        "st_btn":           "Refresh",
        "st_stats_label":   "Index stats",
        "st_config_label":  "project.yaml",
        "st_state_label":   "ingest_state.yaml",

        # admin
        "adm_desc":             "Maintenance operations for the selected project. Re-ingest and Re-index operations stream output line by line.",
        "adm_project_label":    "Project",
        "adm_vacuum_title":     "Vacuum — compact file index",
        "adm_vacuum_desc":      "Remove soft-deleted vectors and rebuild the int8 file. Run after many incremental `index files` updates.",
        "adm_vacuum_btn":       "Run vacuum",
        "adm_vacuum_out":       "Result",
        "adm_riu_title":        "Re-index units — embed commits / tasks",
        "adm_riu_desc":         "Re-embed the units DB (commits or tasks). DB path and model are auto-loaded from the existing index if left blank.",
        "adm_riu_db_label":     "DB path (optional)",
        "adm_riu_db_ph":        "auto-loaded from index if blank",
        "adm_riu_model_label":  "Model (optional)",
        "adm_riu_model_ph":     "leave blank to keep current model",
        "adm_riu_btn":          "Re-index units",
        "adm_rif_title":        "Re-index files — embed source files",
        "adm_rif_desc":         "Re-scan and re-embed a directory of source files. Incremental by default (only changed files). Use **Full rebuild** to re-embed everything.",
        "adm_rif_path_label":   "Source path",
        "adm_rif_path_ph":      "/path/to/repo or ./docs",
        "adm_rif_model_label":  "Model (optional)",
        "adm_rif_model_ph":     "leave blank to keep current model",
        "adm_rif_chunk_label":  "Chunk size (tokens)",
        "adm_rif_full_label":   "Full rebuild (ignore mtime)",
        "adm_rif_btn":          "Re-index files",
        "adm_ri_title":         "Re-ingest — extract commits + fetch tasks",
        "adm_ri_desc":          "Re-run the ingest pipeline defined in `project.yaml`. Reads git history and/or fetches task details from the configured tracker. By default resumes from checkpoint — use **Force** to start from scratch.",
        "adm_ri_phase_label":   "Phase",
        "adm_ri_force_label":   "Force (ignore checkpoint)",
        "adm_ri_btn":           "Run ingest",
        "adm_out_label":        "Output",

        # init
        "init_desc":             "Create `.simargl/project.yaml` for the current directory. Defines git repo, task tracker, and ingest settings. After saving — go to **Admin → Re-ingest** to extract commits and tasks.",
        "init_name_label":       "Project name",
        "init_db_label":         "DB path",
        "init_repo_label":       "Git repo path (local folder with .git/)",
        "init_repo_info":        ". = current working directory",
        "init_branch_label":     "Branch",
        "init_since_label":      "Since (YYYY-MM-DD, optional)",
        "init_since_ph":         "full history if blank",
        "init_tracker_label":    "Task tracker",
        "init_jira_header":      "**Jira**",
        "init_jira_url_label":   "Jira URL",
        "init_jira_url_ph":      "https://your-org.atlassian.net",
        "init_jira_proj_label":  "Project key",
        "init_jira_proj_ph":     "KAFKA",
        "init_jira_conn_label":  "Connector",
        "init_jira_conn_info":   "api = REST (recommended)  html = scrape  selenium = JS-rendered",
        "init_jira_token_label": "Token (optional for public instances)",
        "init_gh_header":        "**GitHub**",
        "init_gh_owner_label":   "Owner (org or user)",
        "init_gh_owner_ph":      "apache",
        "init_gh_repo_label":    "Repo",
        "init_gh_repo_ph":       "kafka",
        "init_gh_token_label":   "Token (60 req/h without)",
        "init_gh_mask_label":    "Commit pattern",
        "init_gh_mask_info":     "generic = issue refs like #123 / PROJ-456",
        "init_yt_header":        "**YouTrack**",
        "init_yt_url_label":     "YouTrack URL",
        "init_yt_proj_label":    "Project key",
        "init_yt_proj_ph":       "KT",
        "init_yt_token_label":   "Token (optional for public)",
        "init_gl_header":        "**GitLab**",
        "init_gl_url_label":     "GitLab URL",
        "init_gl_proj_label":    "Project (org/repo)",
        "init_gl_proj_ph":       "myorg/myrepo",
        "init_gl_token_label":   "Token (required for comments)",
        "init_overwrite_label":  "Force overwrite existing project.yaml",
        "init_btn":              "Create project.yaml",
        "init_result_label":     "Result",
        "init_yaml_label":       "Generated project.yaml",

        # settings
        "settings_theme_header":    "### Theme",
        "settings_theme_label":     "Theme",
        "settings_theme_save_btn":  "Save",
        "settings_lang_header":     "### Language",
        "settings_lang_label":      "Language",
        "settings_lang_save_btn":   "Save",
        "settings_restart_hint":    "Saved — restart to apply.",
        "settings_reload_delay_label": "Reload delay (s)",
        "settings_restart_btn":     "Restart application",
        "settings_restarting":      "Restarting...",

        # download
        "dl_desc": (
            "Download the full index for a project as a ZIP file.\n\n"
            "Extract on your local machine as `.simargl/` and run `simargl search` or "
            "`simargl status` locally. All six index files are included.\n\n"
            "`db_path` in `meta.json` is automatically reduced to a bare filename "
            "so it contains no server-side absolute paths."
        ),
        "dl_project_label": "Project to download",
        "dl_btn":           "Prepare ZIP",
        "dl_file_label":    "Download",

        # output strings (returned by helper functions)
        "out_no_files":    "_No files found._",
        "out_no_modules":  "_No modules found._",
        "out_no_units":    "_No similar tasks/commits._",
        "out_enter_query": "_Enter a query._",
        "out_searching":   "_Searching..._",
        "out_no_results":  "_No results._",
        "out_no_src_res":  "_no results_",
        "out_no_sources":  "_No sources._",
        "out_no_bh":       "No blackhole files marked.",
    },

    # ── Ukrainian ─────────────────────────────────────────────────────────────
    "uk": {
        # app
        "app_title":  "SIMARGL | {project_name}",
        "app_header": "## SIMARGL | task-to-code retrieval :: {project_name}",
        "store_dir_label": "Тека зберігання (.simargl/)",

        # tabs
        "tab_search":    "Пошук",
        "tab_rrf":       "RRF",
        "tab_retrieve":  "Вибірка",
        "tab_blackhole": "Чорна діра",
        "tab_status":    "Статус",
        "tab_admin":     "Адмін",
        "tab_init":      "Ініціалізація",
        "tab_settings":  "Налаштування",
        "tab_download":  "Завантаження",

        # search
        "search_query_label":       "Запит",
        "search_query_placeholder": 'напр. "додати buildString до пошуку в project analysis"',
        "search_btn":               "Шукати",
        "search_mode_label":        "Режим",
        "search_mode_info":         "task=через історію  file=прямий  aggr=центроїд  refine=розширення запиту",
        "search_sort_label":        "Сортування",
        "search_sort_info":         "rank=схожість  freq=популярність (лише режим task)",
        "search_project_label":     "Проект",
        "search_diff_label":        "Включати діфи",
        "search_advanced":          "Додатково",
        "search_top_n":             "Top N файлів",
        "search_top_k":             "Top K одиниць",
        "search_top_m":             "Top M модулів",
        "search_excl_bh":           "Виключати чорні діри",
        "search_cov_pen_label":     "Штраф покриття λ",
        "search_cov_pen_info":      "Знижувати рейтинг всюдисущих файлів (потрібен попередній запуск coverage_float)",
        "search_blend_label":       "Змішування оцінок α",
        "search_blend_info":        "Вага концентрації теми",
        "search_ref_k_label":       "Refine top-k комітів",
        "search_ref_k_info":        "Розмір джерела розширення запиту (лише режим refine)",
        "search_ref_m_label":       "Refine top-m термінів",
        "search_ref_m_info":        "Нові терміни, додані до запиту (лише режим refine)",
        "search_files_header":      "### Файли",
        "search_modules_header":    "### Модулі",
        "search_units_header":      "### Схожі задачі / коміти",

        # rrf
        "rrf_desc": (
            "**Reciprocal Rank Fusion** — об'єднання результатів з кількох джерел "
            "(різні режими або проекти). Оцінки базуються на рангах, а не сирій схожості, "
            "тому джерела з різними моделями можна порівнювати."
        ),
        "rrf_query_label":   "Запит",
        "rrf_btn":           "Шукати",
        "rrf_sources_label": "Джерела",
        "rrf_sources_info":  'Пари mode:project через кому. Напр. "task:default,file:jina,aggr:default"',
        "rrf_top_n":         "Top N файлів (об'єднано)",
        "rrf_top_k":         "Top K на джерело",
        "rrf_k":             "RRF демпфування k",
        "rrf_sort_label":    "Сортування (task-джерела)",
        "rrf_blend_label":   "Змішування оцінок α",
        "rrf_cov_pen_label": "Штраф покриття λ",
        "rrf_files_header":  "### Файли (об'єднано)",
        "rrf_modules_header":"### Модулі",
        "rrf_src_header":    "### Розбивка по джерелах",

        # retrieve
        "ret_desc": "**Вибірка** — повертає повний текст файлу/задачі для контексту LLM (для RAG пайплайнів).",
        "ret_query_label":      "Запит",
        "ret_btn":              "Отримати",
        "ret_mode_label":       "Режим",
        "ret_mode_info":        "file=вміст файлу  task=повідомлення комітів  aggr=файли центроїду",
        "ret_project_label":    "Проект",
        "ret_top_n":            "Top N",
        "ret_excl_bh":          "Виключати чорні діри",
        "ret_cov_pen":          "Штраф покриття λ",
        "ret_blend":            "Змішування оцінок α",
        "ret_source_dir_label": "Тека джерела (необов'язково)",
        "ret_source_dir_ph":    "/шлях/до/репо — читати вміст файлів звідси",
        "ret_out_label":        "Отриманий контекст",

        # blackhole
        "bh_desc": (
            "**Виявлення семантичного шуму** — файли, які однаково збігаються з кожним запитом "
            "(логи, changelog, шаблони). Три методи:\n\n"
            "- **centroid** — швидкий, позначає файли близькі до центроїду корпусу.\n"
            "- **coverage** — позначає файли, що з'являються у top-k для >= threshold частки запитів.\n"
            "- **coverage_float** _(рекомендований)_ — обчислює плаваючий бал покриття, без бінарного відсікання. "
            "Використовуй `coverage_penalty` у пошуку для перевпорядкування без жорсткої фільтрації."
        ),
        "bh_project_label":   "Проект",
        "bh_method_label":    "Метод",
        "bh_threshold_label": "Поріг",
        "bh_threshold_info":  "centroid: схожість до центроїду (0.85)  coverage: частка запитів (0.3)",
        "bh_n_queries_label": "Тестових запитів (методи coverage)",
        "bh_top_k_label":     "Top-k на запит (методи coverage)",
        "bh_list_btn":        "Список позначених чорних дір",
        "bh_detect_btn":      "Запустити виявлення",
        "bh_out_label":       "Результат",

        # status
        "st_project_label": "Проект",
        "st_btn":           "Оновити",
        "st_stats_label":   "Статистика індексу",
        "st_config_label":  "project.yaml",
        "st_state_label":   "ingest_state.yaml",

        # admin
        "adm_desc":             "Операції обслуговування для обраного проекту. Операції Re-ingest та Re-index стрімлять вивід рядок за рядком.",
        "adm_project_label":    "Проект",
        "adm_vacuum_title":     "Vacuum — компактизація файлового індексу",
        "adm_vacuum_desc":      "Видалити м'яко-видалені вектори та перебудувати int8-файл. Запускай після багатьох інкрементальних оновлень `index files`.",
        "adm_vacuum_btn":       "Запустити vacuum",
        "adm_vacuum_out":       "Результат",
        "adm_riu_title":        "Re-index units — векторизація комітів / задач",
        "adm_riu_desc":         "Перезаіндексувати БД одиниць (коміти або задачі). Шлях до БД і модель завантажуються автоматично з поточного індексу, якщо залишити порожнім.",
        "adm_riu_db_label":     "Шлях до БД (необов'язково)",
        "adm_riu_db_ph":        "автозавантажується з індексу, якщо порожньо",
        "adm_riu_model_label":  "Модель (необов'язково)",
        "adm_riu_model_ph":     "залиш порожнім, щоб зберегти поточну модель",
        "adm_riu_btn":          "Re-index units",
        "adm_rif_title":        "Re-index files — векторизація вихідних файлів",
        "adm_rif_desc":         "Повторно просканувати та заіндексувати директорію вихідних файлів. Інкрементальний режим за замовчуванням (лише змінені файли). Використовуй **Повне перебудування** для повного переіндексування.",
        "adm_rif_path_label":   "Шлях до джерела",
        "adm_rif_path_ph":      "/шлях/до/репо або ./docs",
        "adm_rif_model_label":  "Модель (необов'язково)",
        "adm_rif_model_ph":     "залиш порожнім, щоб зберегти поточну модель",
        "adm_rif_chunk_label":  "Розмір чанку (токени)",
        "adm_rif_full_label":   "Повне перебудування (ігнорувати mtime)",
        "adm_rif_btn":          "Re-index files",
        "adm_ri_title":         "Re-ingest — вилучення комітів + отримання задач",
        "adm_ri_desc":          "Перезапустити пайплайн інгесту, визначений у `project.yaml`. Читає git-історію та/або отримує деталі задач з налаштованого трекера. За замовчуванням продовжує з контрольної точки — використовуй **Примусово** для початку з нуля.",
        "adm_ri_phase_label":   "Фаза",
        "adm_ri_force_label":   "Примусово (ігнорувати контрольну точку)",
        "adm_ri_btn":           "Запустити ingest",
        "adm_out_label":        "Вивід",

        # init
        "init_desc":             "Створити `.simargl/project.yaml` для поточної директорії. Визначає git-репо, трекер задач та налаштування інгесту. Після збереження — перейди до **Admin → Re-ingest** для вилучення комітів та задач.",
        "init_name_label":       "Назва проекту",
        "init_db_label":         "Шлях до БД",
        "init_repo_label":       "Шлях до git-репо (локальна папка з .git/)",
        "init_repo_info":        ". = поточна робоча директорія",
        "init_branch_label":     "Гілка",
        "init_since_label":      "Починаючи з (YYYY-MM-DD, необов'язково)",
        "init_since_ph":         "повна історія, якщо порожньо",
        "init_tracker_label":    "Трекер задач",
        "init_jira_header":      "**Jira**",
        "init_jira_url_label":   "Jira URL",
        "init_jira_url_ph":      "https://your-org.atlassian.net",
        "init_jira_proj_label":  "Ключ проекту",
        "init_jira_proj_ph":     "KAFKA",
        "init_jira_conn_label":  "Конектор",
        "init_jira_conn_info":   "api = REST (рекомендовано)  html = парсинг  selenium = JS-рендеринг",
        "init_jira_token_label": "Токен (необов'язковий для публічних)",
        "init_gh_header":        "**GitHub**",
        "init_gh_owner_label":   "Власник (орг або користувач)",
        "init_gh_owner_ph":      "apache",
        "init_gh_repo_label":    "Репозиторій",
        "init_gh_repo_ph":       "kafka",
        "init_gh_token_label":   "Токен (60 запитів/год без нього)",
        "init_gh_mask_label":    "Шаблон коміту",
        "init_gh_mask_info":     "generic = посилання на задачі типу #123 / PROJ-456",
        "init_yt_header":        "**YouTrack**",
        "init_yt_url_label":     "YouTrack URL",
        "init_yt_proj_label":    "Ключ проекту",
        "init_yt_proj_ph":       "KT",
        "init_yt_token_label":   "Токен (необов'язковий для публічних)",
        "init_gl_header":        "**GitLab**",
        "init_gl_url_label":     "GitLab URL",
        "init_gl_proj_label":    "Проект (орг/репо)",
        "init_gl_proj_ph":       "myorg/myrepo",
        "init_gl_token_label":   "Токен (обов'язковий для коментарів)",
        "init_overwrite_label":  "Примусово перезаписати наявний project.yaml",
        "init_btn":              "Створити project.yaml",
        "init_result_label":     "Результат",
        "init_yaml_label":       "Згенерований project.yaml",

        # settings
        "settings_theme_header":   "### Тема",
        "settings_theme_label":    "Тема",
        "settings_theme_save_btn": "Зберегти",
        "settings_lang_header":    "### Мова",
        "settings_lang_label":     "Мова",
        "settings_lang_save_btn":  "Зберегти",
        "settings_restart_hint":   "Збережено — перезапусти для застосування.",
        "settings_reload_delay_label": "Затримка перезапуску (с)",
        "settings_restart_btn":    "Перезапустити застосунок",
        "settings_restarting":     "Перезапуск...",

        # download
        "dl_desc": (
            "Завантажити повний індекс проекту у вигляді ZIP-файлу.\n\n"
            "Розпакуй на локальній машині як `.simargl/` та запусти `simargl search` або "
            "`simargl status` локально. Включено всі шість файлів індексу.\n\n"
            "`db_path` у `meta.json` автоматично скорочується до короткого імені файлу, "
            "щоб не містити серверні абсолютні шляхи."
        ),
        "dl_project_label": "Проект для завантаження",
        "dl_btn":           "Підготувати ZIP",
        "dl_file_label":    "Завантажити",

        # output strings
        "out_no_files":    "_Файлів не знайдено._",
        "out_no_modules":  "_Модулів не знайдено._",
        "out_no_units":    "_Схожих задач/комітів немає._",
        "out_enter_query": "_Введіть запит._",
        "out_searching":   "_Пошук..._",
        "out_no_results":  "_Результатів немає._",
        "out_no_src_res":  "_немає результатів_",
        "out_no_sources":  "_Джерел немає._",
        "out_no_bh":       "Жодного файлу чорної діри не позначено.",
    },
}


def get(lang: str) -> dict[str, str]:
    base = STRINGS["en"]
    if lang == "en" or lang not in STRINGS:
        return base
    # merge: start with English, overlay target language (missing keys fall back to en)
    return {**base, **STRINGS[lang]}
