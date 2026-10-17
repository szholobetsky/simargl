I18N.pt = {
  // header, scope
  tagline: 'encontrar o código de uma tarefa no histórico de tarefas',
  tab_search: 'Busca', tab_rrf: 'RRF', tab_retrieve: 'Contexto', tab_blackhole: 'Buracos negros', tab_index: 'Índice',
  tab_status: 'Estado', 
  store_title: 'Armazém: uma pasta .simargl de um projeto', project_title: 'Índice do armazém (e o modelo com que foi construído)',
  theme_title: 'Tema — os mesmos temas do vyrii, alkonost, gamayun e svitovyd', lang_title: 'Idioma',
  refresh_title: 'Procurar armazéns novamente', theme_auto: 'Simargl (auto)',
  select_store: 'Escolher armazém…', select_index: 'Escolher índice…',
  scope_choose: 'Escolha um armazém e um índice acima.',
  scope_none: 'Ainda não há índice — construa-o na página Index ou inicie o simargl numa pasta de projeto (a UI procura em {dir}). O conjunto de dados é reunido pelo mokosh: mokosh ui.',
  scope_on: 'Armazém <b>{name}</b> — {store}', scope_index: 'índice <b>{p}</b> · {m} · {d} dimensões · {what}',
  has_units: 'tarefas', has_files: 'código',
  choose_store_first: 'escolha um armazém primeiro', choose_index_first: 'escolha um índice primeiro',
  searching: 'buscando… (a primeira busca carrega o modelo ou consulta o Ollama)', computing: 'calculando…', loading: 'carregando…',
  none: 'nada', show: 'Mostrar', copy: 'Copiar', copied: 'copiado', starting: 'iniciando…', job_done: '— concluído',

  // search
  query_ph: 'Cole uma tarefa: título e descrição…',
  mode: 'modo', mode_task: 'task — tarefas passadas semelhantes', mode_file: 'file — trechos de código', mode_aggr: 'aggr — tarefas + código',
  mode_refine: 'refine — tarefas, depois código', sort: 'ordem', sort_rank: 'rank — maior semelhança', sort_freq: 'freq — quantas tarefas semelhantes',
  top_n: 'arquivos', top_n_title: 'quantos arquivos retornar', top_k: 'tarefas semelhantes', top_k_title: 'quantas tarefas passadas semelhantes votam nos arquivos',
  top_m: 'módulos', top_m_title: 'quantos módulos retornar',
  score_blend: 'mistura da pontuação', blend_title: '1 = só semelhança; valores menores misturam quantas vezes um arquivo foi alterado',
  coverage_penalty: 'penalidade de cobertura', penalty_title: 'rebaixar arquivos que respondem a consultas demais (precisa das pontuações de cobertura — página Buracos negros)',
  refine_k: 'refine: tarefas', refine_m: 'refine: módulos', include_diff: 'com diffs', exclude_bh: 'ignorar buracos negros',
  search_btn: 'Buscar', search_status: '{ms} ms · {f} arquivos · {u} tarefas semelhantes',
  h_files: 'Arquivos', h_modules: 'Módulos', h_units: 'Tarefas passadas semelhantes', h_sources: 'Fontes',
  h_answer_map: 'A resposta como mapa',
  answer_map_note: 'Tarefas passadas semelhantes (círculos, maiores = mais semelhantes) e os arquivos que elas alteraram (quadrados). Um arquivo alterado por muitas delas é onde a resposta converge; os arquivos que o simargl retornou são coloridos.',
  lg_task: 'tarefa semelhante', lg_file_found: 'arquivo na resposta', lg_file_other: 'arquivo alterado pelas tarefas', lg_size_map: 'tamanho = semelhança (tarefa), quantas tarefas o alteraram (arquivo)',
  lone_tasks: 'tarefas semelhantes sem arquivo em comum com as outras',
  tip_file_tasks: 'alterado por {n} destas tarefas', tip_found: 'na resposta',
  changed_files: '{n} arquivos alterados', diff: 'diff',
  search_guide_t: 'Como a busca funciona',
  search_guide_1: 'O texto da tarefa vira um vetor pelo modelo próprio do índice e é comparado com os vetores das tarefas passadas (<b>task</b>) ou dos trechos de código (<b>file</b>). No modo task, as tarefas passadas mais semelhantes votam nos arquivos que alteraram: <b>rank</b> confia nas mais semelhantes, <b>freq</b> conta quantas tarefas semelhantes alteraram um arquivo. <b>aggr</b> mistura os dois; <b>refine</b> encontra primeiro os módulos pelas tarefas e depois busca no código deles.',
  search_guide_2: 'Módulos são as primeiras pastas dos caminhos, pontuadas pelos seus arquivos. <b>Buracos negros</b> são arquivos que aparecem para quase qualquer consulta (arquivos de configuração enormes, código gerado); podem ser ignorados ou rebaixados. Uma busca usa sempre o modelo com que o índice foi construído.',

  // rrf
  rrf_sources: 'Fontes (modo : índice)', rrf_k_title: 'o k da fusão por posição recíproca: pontuação = Σ 1 / (k + posição)',
  no_sources: 'Este armazém ainda não tem índice.',
  rrf_help: 'Executa uma busca por fonte e as funde pela posição no ranking — <b>reciprocal rank fusion</b>: as pontuações brutas são descartadas, então índices construídos com modelos diferentes podem ser fundidos. Um arquivo encontrado por várias fontes sobe.',

  // retrieve
  top_n_chunks: 'trechos', source_dir: 'pasta de origem (opcional)', source_dir_ph: 'onde o código está agora, para ler o texto atual',
  retrieve_btn: 'Recuperar', chars_n: '{n} caracteres',
  retrieve_help: 'Texto pronto para colar no contexto de um LLM: os trechos de código mais relevantes (modo file) ou as tarefas passadas (modo task), com seus caminhos. Com uma pasta de origem, lê-se o texto atual dos arquivos em vez do indexado.',

  // blackholes
  bh_method: 'método', bh_centroid: 'centroid — perto do centro de tudo', bh_coverage: 'coverage — responde a consultas aleatórias demais',
  bh_float: 'pontuações de cobertura — reordenar, não marcar nada', bh_threshold: 'limiar', bh_queries: 'consultas de teste',
  bh_detect: 'Detectar', bh_list: 'Listar marcados', bh_marked: 'Arquivos marcados ({n})',
  bh_help: 'Um <b>buraco negro</b> é um arquivo cujos vetores ficam perto de tudo, então ele aparece para quase qualquer tarefa. <b>Centroid</b> marca arquivos perto do centro de todo o índice; <b>coverage</b> faz consultas aleatórias e marca os arquivos que respondem a uma fração acima do limiar; as <b>pontuações de cobertura</b> só guardam uma pontuação por arquivo para a penalidade de cobertura.',

  // index
  models_t: 'Modelos de embedding', pull_title: 'um modelo ollama:// para baixar no Ollama (ollama://nome ou ollama://nome@host)',
  pull_btn: 'Baixar no Ollama', host_ph: 'outro host do Ollama, p. ex. panteon.local', refresh_models: 'Verificar de novo',
  model_default: 'Índices novos usam {m}, a menos que outro modelo seja escolhido.',
  torch_yes: 'o torch está instalado: os modelos locais {list} rodam aqui, rápidos para indexar muitas tarefas.',
  torch_no: 'o torch não está instalado: modelos locais precisam de <code>pip install simargl[torch]</code>; modelos do Ollama não precisam de nada aqui.',
  ollama_batch: '{n} textos por requisição', ollama_none: 'sem modelos, ou inacessível',
  units_t: 'Indexar o histórico de tarefas', index_name: 'nome do índice', db_path: 'base de tarefas (opcional)',
  db_ph: 'padrão: a base do .mokosh/project.yaml', model: 'modelo', model_ph: 'padrão: ollama://granite-embedding:30m',
  units_mode: 'unidades', index_btn: 'Indexar',
  files_t: 'Indexar o código', source_folder: 'pasta de origem', chunk_size: 'tamanho do trecho', full_rebuild: 'reconstruir tudo',

  vacuum_btn: 'Compactar o índice escolhido',
  index_help: 'Um índice lembra o seu modelo, e cada busca usa esse modelo de novo — um índice construído com o Ollama busca pelo Ollama; um construído com um modelo local precisa do torch. Modelos locais (<code>pip install simargl[torch]</code>) costumam ser mais rápidos para indexar dezenas de milhares de tarefas; o Ollama não precisa de nada neste dispositivo e pode rodar em outra máquina (<code>ollama://granite-embedding:30m@host</code>). <b>Reunir</b> executa o mokosh: os commits do repositório e as tarefas do gerenciador na base. <b>Compactar</b> remove os vetores de arquivos excluídos.',

  // status
  st_index: 'Índice {p}', st_store: 'Armazém', download_zip: 'baixar o índice (zip)',

  // triangulation
  tab_tri: 'Triangulação',
  x_none: '— nenhum —',
  x_code_project: 'código',
  x_depth: 'arquivos por ferramenta',
  x_btn: 'Triangular',
  x_status: '{ms} ms · {n} ferramentas · {moved} caminhos movidos resolvidos pelo mapa',
  x_tool_line: '{n} arquivos · {s} s',
  x_idents: 'palavras da tarefa que levam ao código', x_word_title: '{i} identificadores · {f} arquivos',
  x_top: 'A resposta fundida (top {n} abaixo da faixa)',
  x_group_3: 'as três: {n}',
  x_group_2: 'duas de três: {n}',
  x_group_1: 'só uma ferramenta: {n}',
  x_was: 'no histórico de tarefas como {p}',
  x_companion: 'companheiro · {p} das tarefas passadas', x_companion_title: 'Muda com uma grande parte de todas as tarefas (um registro, um arquivo de mensagens, o build). Muitas vezes faz parte da mudança, raramente é o seu núcleo — fica no lugar, apenas marcado.',
  x_gone: 'não está no código atual', x_gone_title: 'O histórico de tarefas lembra este caminho, mas o código atual (o mapa do svitovyd) não tem esse arquivo nem um com o mesmo nome.',
  x_each: 'cada ferramenta separadamente',
  x_guide_t: 'Como a triangulação funciona',
  x_guide_1: 'Três ferramentas respondem à mesma tarefa por conta própria: <b>simargl</b> pelo significado (tarefas passadas parecidas e os arquivos que alteraram), <b>gamayun</b> pela estatística (palavras que levam significativamente a arquivos, mudanças conjuntas), <b>svitovyd</b> pela estrutura (as palavras da tarefa tornam-se os identificadores que nomeiam, e os identificadores levam aos arquivos que os definem). As respostas são fundidas por <b>reciprocal rank fusion</b> com pesos iguais — cada ferramenta soma 1 / (60 + posição) a um arquivo. No experimento (simrgl exp10, SonarQube, 200 tarefas reservadas) as ferramentas compartilhavam nos seus top 10 cerca de um arquivo em quinze, e a fusão superou a melhor delas em todas as medidas (hit@10 0.62 → 0.755); pesos ajustados não foram melhores.',
  x_guide_2: 'Os números coloridos são a posição do arquivo em cada ferramenta. Um arquivo que as três nomeiam é a aposta mais segura; um que só o histórico traz costuma ser um companheiro (um teste, um arquivo de mensagens); um que só o código traz é terreno novo que nenhuma tarefa passada tocou. O histórico de tarefas lembra os caminhos como eram: com um mapa do svitovyd escolhido, um caminho que não existe mais é lido como o único arquivo do código atual com o mesmo nome, então os votos para um arquivo movido se somam.',
};
