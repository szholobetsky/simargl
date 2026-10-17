I18N.de = {
  // header, scope
  tagline: 'Code zu einer Aufgabe finden, aus der Aufgabenhistorie',
  tab_search: 'Suche', tab_rrf: 'RRF', tab_retrieve: 'Kontext', tab_blackhole: 'Schwarze Löcher', tab_index: 'Index',
  tab_status: 'Status', 
  store_title: 'Speicher: ein .simargl-Ordner eines Projekts', project_title: 'Index im Speicher (und das Modell, mit dem er gebaut wurde)',
  theme_title: 'Design — dieselben Designs wie in vyrii, alkonost, gamayun und svitovyd', lang_title: 'Sprache',
  refresh_title: 'Speicher erneut suchen', theme_auto: 'Simargl (auto)',
  select_store: 'Speicher wählen…', select_index: 'Index wählen…',
  scope_choose: 'Wählen Sie oben einen Speicher und einen Index.',
  scope_none: 'Noch kein Index — auf der Seite Index bauen oder simargl in einem Projektordner starten (die UI sucht unter {dir}). Den Datensatz sammelt mokosh: mokosh ui.',
  scope_on: 'Speicher <b>{name}</b> — {store}', scope_index: 'Index <b>{p}</b> · {m} · {d} Dimensionen · {what}',
  has_units: 'Aufgaben', has_files: 'Code',
  choose_store_first: 'zuerst einen Speicher wählen', choose_index_first: 'zuerst einen Index wählen',
  searching: 'suche… (die erste Suche lädt das Modell oder fragt Ollama)', computing: 'berechne…', loading: 'lade…',
  none: 'nichts', show: 'Anzeigen', copy: 'Kopieren', copied: 'kopiert', starting: 'starte…', job_done: '— fertig',

  // search
  query_ph: 'Aufgabe einfügen: Titel und Beschreibung…',
  mode: 'Modus', mode_task: 'task — ähnliche frühere Aufgaben', mode_file: 'file — Codeausschnitte', mode_aggr: 'aggr — Aufgaben + Code',
  mode_refine: 'refine — Aufgaben, dann Code', sort: 'Sortierung', sort_rank: 'rank — größte Ähnlichkeit', sort_freq: 'freq — wie viele ähnliche Aufgaben',
  top_n: 'Dateien', top_n_title: 'wie viele Dateien zurückgegeben werden', top_k: 'ähnliche Aufgaben', top_k_title: 'wie viele ähnliche frühere Aufgaben für Dateien stimmen',
  top_m: 'Module', top_m_title: 'wie viele Module zurückgegeben werden',
  score_blend: 'Score-Mischung', blend_title: '1 = nur Ähnlichkeit; kleiner mischt ein, wie oft eine Datei geändert wurde',
  coverage_penalty: 'Abdeckungsstrafe', penalty_title: 'Dateien herabsetzen, die auf zu viele Anfragen antworten (benötigt Abdeckungswerte — Seite „Schwarze Löcher“)',
  refine_k: 'refine: Aufgaben', refine_m: 'refine: Module', include_diff: 'mit Diffs', exclude_bh: 'schwarze Löcher überspringen',
  search_btn: 'Suchen', search_status: '{ms} ms · {f} Dateien · {u} ähnliche Aufgaben',
  h_files: 'Dateien', h_modules: 'Module', h_units: 'Ähnliche frühere Aufgaben', h_sources: 'Quellen',
  h_answer_map: 'Die Antwort als Karte',
  answer_map_note: 'Ähnliche frühere Aufgaben (Kreise, größer = ähnlicher) und die Dateien, die sie geändert haben (Quadrate). Eine Datei, die viele davon geändert haben, ist der Punkt, an dem die Antwort zusammenläuft; die von simargl gelieferten Dateien sind farbig.',
  lg_task: 'ähnliche Aufgabe', lg_file_found: 'Datei in der Antwort', lg_file_other: 'von den Aufgaben geänderte Datei', lg_size_map: 'Größe = Ähnlichkeit (Aufgabe), wie viele Aufgaben sie geändert haben (Datei)',
  lone_tasks: 'ähnliche Aufgaben ohne gemeinsame Datei mit den anderen',
  tip_file_tasks: 'von {n} dieser Aufgaben geändert', tip_found: 'in der Antwort',
  changed_files: '{n} Dateien geändert', diff: 'Diff',
  search_guide_t: 'Wie die Suche funktioniert',
  search_guide_1: 'Der Aufgabentext wird vom eigenen Modell des Index in einen Vektor verwandelt und mit den Vektoren früherer Aufgaben (<b>task</b>) oder von Codeausschnitten (<b>file</b>) verglichen. Im Modus task stimmen die ähnlichsten früheren Aufgaben für die Dateien, die sie geändert haben: <b>rank</b> vertraut den ähnlichsten, <b>freq</b> zählt, wie viele ähnliche Aufgaben eine Datei geändert haben. <b>aggr</b> mischt beides; <b>refine</b> findet zuerst die Module über Aufgaben und sucht dann im Code darin.',
  search_guide_2: 'Module sind die ersten Ordner der Pfade, bewertet nach ihren Dateien. <b>Schwarze Löcher</b> sind Dateien, die bei fast jeder Anfrage auftauchen (riesige Konfigurationen, generierter Code); sie lassen sich überspringen oder herabsetzen. Eine Suche verwendet immer das Modell, mit dem der Index gebaut wurde.',

  // rrf
  rrf_sources: 'Quellen (Modus : Index)', rrf_k_title: 'das k der Reciprocal Rank Fusion: Score = Σ 1 / (k + Rang)',
  no_sources: 'Dieser Speicher hat noch keinen Index.',
  rrf_help: 'Führt eine Suche pro Quelle aus und vereint sie nach Rangposition — <b>Reciprocal Rank Fusion</b>: rohe Scores werden verworfen, sodass sich mit verschiedenen Modellen gebaute Indizes vereinen lassen. Eine von mehreren Quellen gefundene Datei steigt auf.',

  // retrieve
  top_n_chunks: 'Ausschnitte', source_dir: 'Quellordner (optional)', source_dir_ph: 'wo der Code jetzt liegt, um den aktuellen Text zu lesen',
  retrieve_btn: 'Abrufen', chars_n: '{n} Zeichen',
  retrieve_help: 'Text, bereit zum Einfügen in den Kontext eines LLM: die relevantesten Codeausschnitte (Modus file) oder früheren Aufgaben (Modus task) mit ihren Pfaden. Mit einem Quellordner wird der aktuelle Text der Dateien gelesen statt des indexierten.',

  // blackholes
  bh_method: 'Methode', bh_centroid: 'centroid — nahe am Zentrum von allem', bh_coverage: 'coverage — beantwortet zu viele zufällige Anfragen',
  bh_float: 'Abdeckungswerte — neu ordnen, nichts markieren', bh_threshold: 'Schwelle', bh_queries: 'Testanfragen',
  bh_detect: 'Erkennen', bh_list: 'Markierte anzeigen', bh_marked: 'Markierte Dateien ({n})',
  bh_help: 'Ein <b>schwarzes Loch</b> ist eine Datei, deren Vektoren nahe bei allem liegen, sodass sie bei fast jeder Aufgabe erscheint. <b>Centroid</b> markiert Dateien nahe dem Zentrum des ganzen Index; <b>coverage</b> stellt zufällige Anfragen und markiert Dateien, die auf mehr als den Schwellenanteil antworten; <b>Abdeckungswerte</b> speichern nur einen Wert pro Datei für die Abdeckungsstrafe.',

  // index
  models_t: 'Embedding-Modelle', pull_title: 'ein ollama://-Modell, das in Ollama geladen wird (ollama://name oder ollama://name@host)',
  pull_btn: 'In Ollama laden', host_ph: 'ein anderer Ollama-Host, z. B. panteon.local', refresh_models: 'Erneut prüfen',
  model_default: 'Neue Indizes verwenden {m}, sofern kein anderes Modell gewählt wird.',
  torch_yes: 'torch ist installiert: die lokalen Modelle {list} laufen hier, schnell beim Indexieren vieler Aufgaben.',
  torch_no: 'torch ist nicht installiert: lokale Modelle brauchen <code>pip install simargl[torch]</code>; Ollama-Modelle brauchen hier nichts.',
  ollama_batch: '{n} Texte pro Anfrage', ollama_none: 'keine Modelle oder nicht erreichbar',
  units_t: 'Die Aufgabenhistorie indexieren', index_name: 'Indexname', db_path: 'Aufgabendatenbank (optional)',
  db_ph: 'Standard: die Datenbank aus .mokosh/project.yaml', model: 'Modell', model_ph: 'Standard: ollama://granite-embedding:30m',
  units_mode: 'Einheiten', index_btn: 'Indexieren',
  files_t: 'Den Code indexieren', source_folder: 'Quellordner', chunk_size: 'Ausschnittgröße', full_rebuild: 'alles neu bauen',

  vacuum_btn: 'Gewählten Index verdichten',
  index_help: 'Ein Index merkt sich sein Modell, und jede Suche verwendet wieder dieses Modell — ein mit Ollama gebauter Index sucht über Ollama, einer mit lokalem Modell braucht torch. Lokale Modelle (<code>pip install simargl[torch]</code>) sind beim Indexieren Zehntausender Aufgaben meist schneller; Ollama braucht auf diesem Gerät nichts und kann auf einem anderen Rechner laufen (<code>ollama://granite-embedding:30m@host</code>). <b>Sammeln</b> führt mokosh aus: Commits des Repositorys und Aufgaben des Trackers in die Datenbank. <b>Verdichten</b> entfernt die Vektoren gelöschter Dateien.',

  // status
  st_index: 'Index {p}', st_store: 'Speicher', download_zip: 'Index herunterladen (zip)',

  // triangulation
  tab_tri: 'Triangulation',
  x_none: '— keins —',
  x_code_project: 'Code',
  x_depth: 'Dateien pro Werkzeug',
  x_btn: 'Triangulieren',
  x_status: '{ms} ms · {n} Werkzeuge · {moved} verschobene Pfade über die Karte aufgelöst',
  x_tool_line: '{n} Dateien · {s} s',
  x_idents: 'Wörter der Aufgabe, die in den Code führen', x_word_title: '{i} Bezeichner · {f} Dateien',
  x_top: 'Die vereinte Antwort (Top {n} unter dem Streifen)',
  x_group_3: 'alle drei: {n}',
  x_group_2: 'zwei von drei: {n}',
  x_group_1: 'nur ein Werkzeug: {n}',
  x_was: 'in der Aufgabenhistorie als {p}',
  x_companion: 'Begleiter · {p} der früheren Aufgaben', x_companion_title: 'Ändert sich mit einem großen Anteil aller Aufgaben (eine Registry, eine Meldungsdatei, der Build). Oft Teil der Änderung, selten ihr Kern — bleibt an seinem Platz, nur markiert.',
  x_gone: 'nicht im heutigen Code', x_gone_title: 'Die Aufgabenhistorie kennt diesen Pfad, aber der heutige Code (die svitovyd-Karte) hat weder diese Datei noch eine gleichnamige.',
  x_each: 'jedes Werkzeug für sich',
  x_guide_t: 'Wie die Triangulation funktioniert',
  x_guide_1: 'Drei Werkzeuge beantworten dieselbe Aufgabe für sich: <b>simargl</b> nach Bedeutung (frühere ähnliche Aufgaben und die Dateien, die sie geändert haben), <b>gamayun</b> nach Statistik (Wörter, die signifikant zu Dateien führen, gemeinsame Änderungen), <b>svitovyd</b> nach Struktur (die Wörter der Aufgabe werden zu den Bezeichnern, die sie nennen, und die Bezeichner führen zu den Dateien, die sie definieren). Die Antworten werden durch <b>Reciprocal Rank Fusion</b> mit gleichen Gewichten vereint — jedes Werkzeug gibt einer Datei 1 / (60 + Rang). Im Experiment (simrgl exp10, SonarQube, 200 zurückgehaltene Aufgaben) teilten die Werkzeuge in ihren Top 10 etwa eine von fünfzehn Dateien, und die Fusion schlug das beste von ihnen in jedem Maß (hit@10 0.62 → 0.755); abgestimmte Gewichte waren nicht besser.',
  x_guide_2: 'Die farbigen Zahlen sind der Rang der Datei bei jedem Werkzeug. Eine Datei, die alle drei nennen, ist die sicherste Wahl; eine nur aus der Historie ist oft ein Begleiter (ein Test, eine Meldungsdatei); eine nur aus dem Code ist Neuland, das keine frühere Aufgabe berührt hat. Die Aufgabenhistorie merkt sich Pfade, wie sie waren: ist eine svitovyd-Karte gewählt, wird ein nicht mehr existierender Pfad als die eine Datei des heutigen Codes mit demselben Namen gelesen, sodass sich die Stimmen für eine verschobene Datei addieren.',
};
