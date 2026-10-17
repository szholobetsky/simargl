I18N.es = {
  // header, scope
  tagline: 'encontrar el código de una tarea en el historial de tareas',
  tab_search: 'Búsqueda', tab_rrf: 'RRF', tab_retrieve: 'Contexto', tab_blackhole: 'Agujeros negros', tab_index: 'Índice',
  tab_status: 'Estado', 
  store_title: 'Almacén: una carpeta .simargl de un proyecto', project_title: 'Índice del almacén (y el modelo con que se construyó)',
  theme_title: 'Tema — los mismos temas que vyrii, alkonost, gamayun y svitovyd', lang_title: 'Idioma',
  refresh_title: 'Buscar almacenes de nuevo', theme_auto: 'Simargl (auto)',
  select_store: 'Elegir almacén…', select_index: 'Elegir índice…',
  scope_choose: 'Elija un almacén y un índice arriba.',
  scope_none: 'Aún no hay índice: créelo en la página Index o inicie simargl en una carpeta de proyecto (la UI busca en {dir}). El conjunto de datos lo reúne mokosh: mokosh ui.',
  scope_on: 'Almacén <b>{name}</b> — {store}', scope_index: 'índice <b>{p}</b> · {m} · {d} dimensiones · {what}',
  has_units: 'tareas', has_files: 'código',
  choose_store_first: 'primero elija un almacén', choose_index_first: 'primero elija un índice',
  searching: 'buscando… (la primera búsqueda carga el modelo o consulta a Ollama)', computing: 'calculando…', loading: 'cargando…',
  none: 'nada', show: 'Mostrar', copy: 'Copiar', copied: 'copiado', starting: 'iniciando…', job_done: '— hecho',

  // search
  query_ph: 'Pegue una tarea: título y descripción…',
  mode: 'modo', mode_task: 'task — tareas pasadas similares', mode_file: 'file — fragmentos de código', mode_aggr: 'aggr — tareas + código',
  mode_refine: 'refine — tareas, luego código', sort: 'orden', sort_rank: 'rank — mayor similitud', sort_freq: 'freq — cuántas tareas similares',
  top_n: 'archivos', top_n_title: 'cuántos archivos devolver', top_k: 'tareas similares', top_k_title: 'cuántas tareas pasadas similares votan por los archivos',
  top_m: 'módulos', top_m_title: 'cuántos módulos devolver',
  score_blend: 'mezcla de puntuación', blend_title: '1 = solo similitud; un valor menor mezcla cuántas veces se cambió un archivo',
  coverage_penalty: 'penalización por cobertura', penalty_title: 'bajar los archivos que responden a demasiadas consultas (requiere puntuaciones de cobertura — página Agujeros negros)',
  refine_k: 'refine: tareas', refine_m: 'refine: módulos', include_diff: 'con diffs', exclude_bh: 'omitir agujeros negros',
  search_btn: 'Buscar', search_status: '{ms} ms · {f} archivos · {u} tareas similares',
  h_files: 'Archivos', h_modules: 'Módulos', h_units: 'Tareas pasadas similares', h_sources: 'Fuentes',
  h_answer_map: 'La respuesta como mapa',
  answer_map_note: 'Tareas pasadas similares (círculos, más grandes = más similares) y los archivos que cambiaron (cuadrados). Un archivo que muchas de ellas cambiaron es donde converge la respuesta; los archivos que devolvió simargl van coloreados.',
  lg_task: 'tarea similar', lg_file_found: 'archivo en la respuesta', lg_file_other: 'archivo cambiado por las tareas', lg_size_map: 'tamaño = similitud (tarea), cuántas tareas lo cambiaron (archivo)',
  lone_tasks: 'tareas similares sin archivos en común con las demás',
  tip_file_tasks: 'cambiado por {n} de estas tareas', tip_found: 'en la respuesta',
  changed_files: '{n} archivos cambiados', diff: 'diff',
  search_guide_t: 'Cómo funciona la búsqueda',
  search_guide_1: 'El texto de la tarea se convierte en un vector con el modelo propio del índice y se compara con los vectores de tareas pasadas (<b>task</b>) o de fragmentos de código (<b>file</b>). En modo task, las tareas pasadas más similares votan por los archivos que cambiaron: <b>rank</b> confía en las más similares, <b>freq</b> cuenta cuántas tareas similares cambiaron un archivo. <b>aggr</b> mezcla ambos; <b>refine</b> encuentra primero los módulos mediante las tareas y luego busca el código dentro de ellos.',
  search_guide_2: 'Los módulos son las primeras carpetas de las rutas, puntuadas por sus archivos. Los <b>agujeros negros</b> son archivos que salen para casi cualquier consulta (enormes archivos de configuración, código generado); pueden omitirse o bajarse. Una búsqueda siempre usa el modelo con el que se construyó el índice.',

  // rrf
  rrf_sources: 'Fuentes (modo : índice)', rrf_k_title: 'la k de la fusión por rango recíproco: puntuación = Σ 1 / (k + rango)',
  no_sources: 'Este almacén aún no tiene índice.',
  rrf_help: 'Ejecuta una búsqueda por fuente y las fusiona por posición en el ranking — <b>reciprocal rank fusion</b>: las puntuaciones brutas se descartan, de modo que pueden fusionarse índices construidos con modelos distintos. Un archivo encontrado por varias fuentes sube.',

  // retrieve
  top_n_chunks: 'fragmentos', source_dir: 'carpeta de origen (opcional)', source_dir_ph: 'dónde está el código ahora, para leer su texto actual',
  retrieve_btn: 'Recuperar', chars_n: '{n} caracteres',
  retrieve_help: 'Texto listo para pegar en el contexto de un LLM: los fragmentos de código más relevantes (modo file) o las tareas pasadas (modo task), con sus rutas. Con una carpeta de origen se lee el texto actual de los archivos en lugar del indexado.',

  // blackholes
  bh_method: 'método', bh_centroid: 'centroid — cerca del centro de todo', bh_coverage: 'coverage — responde a demasiadas consultas aleatorias',
  bh_float: 'puntuaciones de cobertura — reordenar, no marcar nada', bh_threshold: 'umbral', bh_queries: 'consultas de prueba',
  bh_detect: 'Detectar', bh_list: 'Listar marcados', bh_marked: 'Archivos marcados ({n})',
  bh_help: 'Un <b>agujero negro</b> es un archivo cuyos vectores están cerca de todo, así que aparece para casi cualquier tarea. <b>Centroid</b> marca los archivos cercanos al centro de todo el índice; <b>coverage</b> lanza consultas aleatorias y marca los archivos que responden a una proporción mayor que el umbral; las <b>puntuaciones de cobertura</b> solo guardan una puntuación por archivo para la penalización por cobertura.',

  // index
  models_t: 'Modelos de embedding', pull_title: 'un modelo ollama:// para descargar en Ollama (ollama://nombre u ollama://nombre@host)',
  pull_btn: 'Descargar en Ollama', host_ph: 'otro host de Ollama, p. ej. panteon.local', refresh_models: 'Comprobar de nuevo',
  model_default: 'Los índices nuevos usan {m}, salvo que se elija otro modelo.',
  torch_yes: 'torch está instalado: los modelos locales {list} se ejecutan aquí, rápidos para indexar muchas tareas.',
  torch_no: 'torch no está instalado: los modelos locales necesitan <code>pip install simargl[torch]</code>; los modelos de Ollama no necesitan nada aquí.',
  ollama_batch: '{n} textos por petición', ollama_none: 'sin modelos, o no accesible',
  units_t: 'Indexar el historial de tareas', index_name: 'nombre del índice', db_path: 'base de tareas (opcional)',
  db_ph: 'por defecto: la base de .mokosh/project.yaml', model: 'modelo', model_ph: 'por defecto: ollama://granite-embedding:30m',
  units_mode: 'unidades', index_btn: 'Indexar',
  files_t: 'Indexar el código', source_folder: 'carpeta de origen', chunk_size: 'tamaño del fragmento', full_rebuild: 'reconstruir todo',

  vacuum_btn: 'Compactar el índice elegido',
  index_help: 'Un índice recuerda su modelo, y cada búsqueda vuelve a usar ese modelo: un índice construido con Ollama busca mediante Ollama; uno construido con un modelo local necesita torch. Los modelos locales (<code>pip install simargl[torch]</code>) suelen ser más rápidos para indexar decenas de miles de tareas; Ollama no necesita nada en este dispositivo y puede ejecutarse en otra máquina (<code>ollama://granite-embedding:30m@host</code>). <b>Reunir</b> ejecuta mokosh: los commits del repositorio y las tareas del gestor en la base. <b>Compactar</b> elimina los vectores de los archivos borrados.',

  // status
  st_index: 'Índice {p}', st_store: 'Almacén', download_zip: 'descargar el índice (zip)',

  // triangulation
  tab_tri: 'Triangulación',
  x_none: '— ninguno —',
  x_code_project: 'código',
  x_depth: 'archivos por herramienta',
  x_btn: 'Triangular',
  x_status: '{ms} ms · {n} herramientas · {moved} rutas movidas resueltas con el mapa',
  x_tool_line: '{n} archivos · {s} s',
  x_idents: 'palabras de la tarea que llevan al código', x_word_title: '{i} identificadores · {f} archivos',
  x_top: 'La respuesta fusionada (top {n} bajo la franja)',
  x_group_3: 'las tres: {n}',
  x_group_2: 'dos de tres: {n}',
  x_group_1: 'una sola herramienta: {n}',
  x_was: 'en el historial de tareas como {p}',
  x_companion: 'compañero · {p} de las tareas pasadas', x_companion_title: 'Cambia con una gran parte de todas las tareas (un registro, un archivo de mensajes, el build). A menudo forma parte del cambio, rara vez es su núcleo — se queda en su sitio, solo marcado.',
  x_gone: 'no está en el código actual', x_gone_title: 'El historial de tareas recuerda esta ruta, pero el código actual (el mapa de svitovyd) no tiene ese archivo ni uno con el mismo nombre.',
  x_each: 'cada herramienta por separado',
  x_guide_t: 'Cómo funciona la triangulación',
  x_guide_1: 'Tres herramientas responden a la misma tarea por su cuenta: <b>simargl</b> por el significado (tareas pasadas parecidas y los archivos que cambiaron), <b>gamayun</b> por la estadística (palabras que llevan significativamente a archivos, cambios conjuntos), <b>svitovyd</b> por la estructura (las palabras de la tarea se convierten en los identificadores que nombran, y los identificadores llevan a los archivos que los definen). Las respuestas se fusionan con <b>reciprocal rank fusion</b> de pesos iguales — cada herramienta suma 1 / (60 + rango) a un archivo. En el experimento (simrgl exp10, SonarQube, 200 tareas reservadas) las herramientas compartían en sus top 10 alrededor de un archivo de cada quince, y la fusión superó a la mejor de ellas en todas las medidas (hit@10 0.62 → 0.755); los pesos ajustados no lo hicieron mejor.',
  x_guide_2: 'Los números de color son el rango del archivo en cada herramienta. Un archivo que nombran las tres es la apuesta más segura; uno que solo da el historial suele ser un compañero (una prueba, un archivo de mensajes); uno que solo da el código es terreno nuevo que ninguna tarea pasada tocó. El historial de tareas recuerda las rutas como eran: con un mapa de svitovyd elegido, una ruta que ya no existe se lee como el único archivo del código actual con el mismo nombre, así que los votos por un archivo movido se suman.',
};
