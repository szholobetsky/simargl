I18N.fr = {
  // header, scope
  tagline: 'trouver le code d\'une tâche dans l\'historique des tâches',
  tab_search: 'Recherche', tab_rrf: 'RRF', tab_retrieve: 'Contexte', tab_blackhole: 'Trous noirs', tab_index: 'Index',
  tab_status: 'État', 
  store_title: 'Stockage : un dossier .simargl d\'un projet', project_title: 'Index du stockage (et le modèle avec lequel il a été construit)',
  theme_title: 'Thème — les mêmes thèmes que vyrii, alkonost, gamayun et svitovyd', lang_title: 'Langue',
  refresh_title: 'Rechercher à nouveau les stockages', theme_auto: 'Simargl (auto)',
  select_store: 'Choisir un stockage…', select_index: 'Choisir un index…',
  scope_choose: 'Choisissez un stockage et un index ci-dessus.',
  scope_none: 'Pas encore d’index — construisez-en un sur la page Index, ou lancez simargl dans un dossier de projet (l’UI cherche sous {dir}). Le jeu de données est rassemblé par mokosh : mokosh ui.',
  scope_on: 'Stockage <b>{name}</b> — {store}', scope_index: 'index <b>{p}</b> · {m} · {d} dimensions · {what}',
  has_units: 'tâches', has_files: 'code',
  choose_store_first: 'choisissez d\'abord un stockage', choose_index_first: 'choisissez d\'abord un index',
  searching: 'recherche… (la première recherche charge le modèle ou interroge Ollama)', computing: 'calcul…', loading: 'chargement…',
  none: 'rien', show: 'Afficher', copy: 'Copier', copied: 'copié', starting: 'démarrage…', job_done: '— terminé',

  // search
  query_ph: 'Collez une tâche : titre et description…',
  mode: 'mode', mode_task: 'task — tâches passées similaires', mode_file: 'file — extraits de code', mode_aggr: 'aggr — tâches + code',
  mode_refine: 'refine — tâches, puis code', sort: 'tri', sort_rank: 'rank — meilleure similarité', sort_freq: 'freq — combien de tâches similaires',
  top_n: 'fichiers', top_n_title: 'combien de fichiers renvoyer', top_k: 'tâches similaires', top_k_title: 'combien de tâches passées similaires votent pour les fichiers',
  top_m: 'modules', top_m_title: 'combien de modules renvoyer',
  score_blend: 'mélange du score', blend_title: '1 = similarité seule ; plus bas, on mêle la fréquence de modification d\'un fichier',
  coverage_penalty: 'pénalité de couverture', penalty_title: 'faire descendre les fichiers qui répondent à trop de requêtes (nécessite les scores de couverture — page Trous noirs)',
  refine_k: 'refine : tâches', refine_m: 'refine : modules', include_diff: 'avec les diffs', exclude_bh: 'ignorer les trous noirs',
  search_btn: 'Rechercher', search_status: '{ms} ms · {f} fichiers · {u} tâches similaires',
  h_files: 'Fichiers', h_modules: 'Modules', h_units: 'Tâches passées similaires', h_sources: 'Sources',
  h_answer_map: 'La réponse sous forme de carte',
  answer_map_note: 'Les tâches passées similaires (cercles, plus grands = plus similaires) et les fichiers qu\'elles ont modifiés (carrés). Un fichier modifié par beaucoup d\'entre elles est l\'endroit où la réponse converge ; les fichiers renvoyés par simargl sont colorés.',
  lg_task: 'tâche similaire', lg_file_found: 'fichier dans la réponse', lg_file_other: 'fichier modifié par les tâches', lg_size_map: 'taille = similarité (tâche), nombre de tâches qui l\'ont modifié (fichier)',
  lone_tasks: 'tâches similaires sans fichier commun avec les autres',
  tip_file_tasks: 'modifié par {n} de ces tâches', tip_found: 'dans la réponse',
  changed_files: '{n} fichiers modifiés', diff: 'diff',
  search_guide_t: 'Comment fonctionne la recherche',
  search_guide_1: 'Le texte de la tâche est transformé en vecteur par le modèle propre à l\'index et comparé aux vecteurs des tâches passées (<b>task</b>) ou des extraits de code (<b>file</b>). En mode task, les tâches passées les plus similaires votent pour les fichiers qu\'elles ont modifiés : <b>rank</b> fait confiance aux plus similaires, <b>freq</b> compte combien de tâches similaires ont modifié un fichier. <b>aggr</b> mêle les deux ; <b>refine</b> trouve d\'abord les modules par les tâches, puis cherche dans leur code.',
  search_guide_2: 'Les modules sont les premiers dossiers des chemins, notés d\'après leurs fichiers. Les <b>trous noirs</b> sont des fichiers qui sortent pour presque n\'importe quelle requête (énormes fichiers de configuration, code généré) ; on peut les ignorer ou les faire descendre. Une recherche utilise toujours le modèle avec lequel l\'index a été construit.',

  // rrf
  rrf_sources: 'Sources (mode : index)', rrf_k_title: 'le k de la fusion par rang réciproque : score = Σ 1 / (k + rang)',
  no_sources: 'Ce stockage n\'a pas encore d\'index.',
  rrf_help: 'Lance une recherche par source et les fusionne par position de rang — <b>reciprocal rank fusion</b> : les scores bruts sont écartés, donc des index construits avec des modèles différents peuvent être fusionnés. Un fichier trouvé par plusieurs sources monte.',

  // retrieve
  top_n_chunks: 'extraits', source_dir: 'dossier source (facultatif)', source_dir_ph: 'où se trouve le code maintenant, pour lire son texte actuel',
  retrieve_btn: 'Récupérer', chars_n: '{n} caractères',
  retrieve_help: 'Du texte prêt à coller dans le contexte d\'un LLM : les extraits de code les plus pertinents (mode file) ou les tâches passées (mode task), avec leurs chemins. Avec un dossier source, le texte actuel des fichiers est lu à la place du texte indexé.',

  // blackholes
  bh_method: 'méthode', bh_centroid: 'centroid — proche du centre de tout', bh_coverage: 'coverage — répond à trop de requêtes aléatoires',
  bh_float: 'scores de couverture — reclasser, ne rien marquer', bh_threshold: 'seuil', bh_queries: 'requêtes de test',
  bh_detect: 'Détecter', bh_list: 'Lister les marqués', bh_marked: 'Fichiers marqués ({n})',
  bh_help: 'Un <b>trou noir</b> est un fichier dont les vecteurs sont proches de tout, si bien qu\'il apparaît pour presque n\'importe quelle tâche. <b>Centroid</b> marque les fichiers proches du centre de tout l\'index ; <b>coverage</b> pose des requêtes aléatoires et marque les fichiers qui répondent à une part supérieure au seuil ; les <b>scores de couverture</b> ne stockent qu\'un score par fichier pour la pénalité de couverture.',

  // index
  models_t: 'Modèles d\'embedding', pull_title: 'un modèle ollama:// à télécharger dans Ollama (ollama://nom ou ollama://nom@hôte)',
  pull_btn: 'Télécharger dans Ollama', host_ph: 'un autre hôte Ollama, p. ex. panteon.local', refresh_models: 'Vérifier à nouveau',
  model_default: 'Les nouveaux index utilisent {m}, sauf si un autre modèle est choisi.',
  torch_yes: 'torch est installé : les modèles locaux {list} tournent ici, rapides pour indexer beaucoup de tâches.',
  torch_no: 'torch n\'est pas installé : les modèles locaux nécessitent <code>pip install simargl[torch]</code> ; les modèles Ollama n\'ont besoin de rien ici.',
  ollama_batch: '{n} textes par requête', ollama_none: 'aucun modèle, ou injoignable',
  units_t: 'Indexer l\'historique des tâches', index_name: 'nom de l\'index', db_path: 'base de tâches (facultatif)',
  db_ph: 'par défaut : la base de .mokosh/project.yaml', model: 'modèle', model_ph: 'par défaut : ollama://granite-embedding:30m',
  units_mode: 'unités', index_btn: 'Indexer',
  files_t: 'Indexer le code', source_folder: 'dossier source', chunk_size: 'taille d\'extrait', full_rebuild: 'tout reconstruire',

  vacuum_btn: 'Compacter l\'index choisi',
  index_help: 'Un index retient son modèle, et chaque recherche réutilise ce modèle — un index construit avec Ollama cherche via Ollama, un index construit avec un modèle local a besoin de torch. Les modèles locaux (<code>pip install simargl[torch]</code>) sont en général plus rapides pour indexer des dizaines de milliers de tâches ; Ollama n\'a besoin de rien sur cet appareil et peut tourner sur une autre machine (<code>ollama://granite-embedding:30m@hôte</code>). <b>Rassembler</b> lance mokosh : les commits du dépôt et les tâches du gestionnaire dans la base. <b>Compacter</b> supprime les vecteurs des fichiers supprimés.',

  // status
  st_index: 'Index {p}', st_store: 'Stockage', download_zip: 'télécharger l\'index (zip)',

  // triangulation
  tab_tri: 'Triangulation',
  x_none: '— aucun —',
  x_code_project: 'code',
  x_depth: 'fichiers par outil',
  x_btn: 'Trianguler',
  x_status: '{ms} ms · {n} outils · {moved} chemins déplacés résolus par la carte',
  x_tool_line: '{n} fichiers · {s} s',
  x_idents: 'mots de la tâche qui mènent au code', x_word_title: '{i} identifiants · {f} fichiers',
  x_top: 'La réponse fusionnée (top {n} sous la bande)',
  x_group_3: 'les trois : {n}',
  x_group_2: 'deux sur trois : {n}',
  x_group_1: 'un seul outil : {n}',
  x_was: 'dans l\'historique des tâches sous {p}',
  x_companion: 'compagnon · {p} des tâches passées', x_companion_title: 'Change avec une grande part de toutes les tâches (un registre, un fichier de messages, le build). Souvent dans la modification, rarement son cœur — gardé à sa place, seulement marqué.',
  x_gone: 'absent du code actuel', x_gone_title: 'L’historique des tâches connaît ce chemin, mais le code actuel (la carte svitovyd) n’a ni ce fichier ni un fichier du même nom.',
  x_each: 'chaque outil séparément',
  x_guide_t: 'Comment fonctionne la triangulation',
  x_guide_1: 'Trois outils répondent séparément à la même tâche : <b>simargl</b> par le sens (des tâches passées semblables et les fichiers qu\'elles ont modifiés), <b>gamayun</b> par la statistique (des mots qui mènent significativement à des fichiers, les modifications conjointes), <b>svitovyd</b> par la structure (les mots de la tâche deviennent les identifiants qu’ils nomment, et les identifiants mènent aux fichiers qui les définissent). Les réponses sont fusionnées par <b>reciprocal rank fusion</b> à poids égaux — chaque outil ajoute 1 / (60 + rang) à un fichier. Dans l\'expérience (simrgl exp10, SonarQube, 200 tâches mises de côté), les outils partageaient environ un fichier sur quinze dans leurs top 10, et la fusion battait le meilleur d\'entre eux sur toutes les mesures (hit@10 0.62 → 0.755) ; des poids ajustés n\'ont pas fait mieux.',
  x_guide_2: 'Les nombres colorés sont le rang du fichier chez chaque outil. Un fichier nommé par les trois est le pari le plus sûr ; un fichier venu seulement de l\'historique est souvent un compagnon (un test, un fichier de messages) ; un fichier venu seulement du code est un terrain neuf qu\'aucune tâche passée n\'a touché. L\'historique des tâches retient les chemins tels qu\'ils étaient : si une carte svitovyd est choisie, un chemin qui n\'existe plus est lu comme l\'unique fichier du code actuel portant le même nom, et les votes pour un fichier déplacé s\'additionnent.',
};
