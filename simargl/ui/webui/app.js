// simargl UI — vanilla JS, no build step. Strings of the interface come from t() (i18n.js);
// task texts, paths, module names and server messages are data and are never translated.
const $ = id => document.getElementById(id);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
async function api(path, body) {
  const res = await fetch(path, body === undefined ? {} : {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data.error) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}
const errHtml = e => `<span class="err">${esc(e.message)}</span>`;
const base = f => String(f).split(/[\\/]/).pop();
const pct = x => `${(100 * x).toFixed(1)}%`;

// ── tabs ─────────────────────────────────────────────
let currentTab = 'search';
function showTab(name) {
  currentTab = name;
  document.querySelectorAll('.tab').forEach(b => b.classList.toggle('active', b.dataset.tab === name));
  document.querySelectorAll('.panel').forEach(p => p.classList.toggle('active', p.id === 'tab-' + name));
  const u = new URL(location.href);
  u.searchParams.set('tab', name);
  history.replaceState(null, '', u);
  if (name === 'index') loadModels();
  if (name === 'status' && store()) runStatus();
  if (name === 'rrf') fillSources();
  if (name === 'tri') loadTriSources();
}
document.querySelectorAll('.tab').forEach(b => b.onclick = () => showTab(b.dataset.tab));

// ── theme & language ─────────────────────────────────
const THEMES = ['simargl', 'ocean', 'dark', 'light', 'soft', 'summer', 'beach', 'mono-dark', 'mono-light'];
const themeTitle = n => n === 'simargl' ? t('theme_auto') : n.split('-').map(w => w[0].toUpperCase() + w.slice(1)).join(' ');
function setTheme(name) {
  const link = $('theme-link');
  if (name === 'simargl') { link.disabled = true; link.removeAttribute('href'); document.documentElement.removeAttribute('data-theme'); }
  else { link.href = `/ui/themes/${name}.css`; link.disabled = false; document.documentElement.setAttribute('data-theme', name); }
  try { localStorage.setItem('simargl-theme', name === 'simargl' ? '' : name); } catch {}
  $('theme').value = name;
}
function fillThemes() {
  let cur = '';
  try { cur = localStorage.getItem('simargl-theme') || ''; } catch {}
  $('theme').innerHTML = THEMES.map(n => `<option value="${n}">${esc(themeTitle(n))}</option>`).join('');
  $('theme').value = THEMES.includes(cur) ? cur : 'simargl';
}
fillThemes();
$('theme').onchange = () => setTheme($('theme').value);
$('lang').innerHTML = LANGS.map(([c, label]) => `<option value="${c}">${esc(label)}</option>`).join('');
$('lang').value = LANG;
$('lang').onchange = () => setLang($('lang').value);

// ── stores and indexes ───────────────────────────────
let stores = [], startDir = '';
const store = () => $('store').value;
const project = () => $('project').value;
const storeInfo = () => stores.find(s => s.store === store());
const indexInfo = () => (storeInfo()?.indexes || []).find(i => i.project === project());

async function loadStores() {
  const data = await api('/api/stores');
  stores = data.stores;
  startDir = data.start || '';
  renderStores();
}

function renderStores() {
  let keep = $('store').value;
  if (!keep) { try { keep = localStorage.getItem('simargl-store') || ''; } catch {} }
  $('store').innerHTML = `<option value="">${esc(t('select_store'))}</option>` +
    stores.map(s => `<option value="${esc(s.store)}">${esc(s.name)}</option>`).join('');
  $('store').value = stores.some(s => s.store === keep) ? keep : (stores.length === 1 ? stores[0].store : '');
  renderProjects();
}

function renderProjects() {
  const s = storeInfo();
  let keep = $('project').value;
  if (!keep) { try { keep = localStorage.getItem('simargl-project') || ''; } catch {} }
  const ix = s ? s.indexes : [];
  $('project').innerHTML = `<option value="">${esc(t('select_index'))}</option>` +
    ix.map(i => `<option value="${esc(i.project)}">${esc(i.project)} · ${esc(i.model_key)}</option>`).join('');
  $('project').value = ix.some(i => i.project === keep) ? keep : (ix.length ? ix[0].project : '');
  renderScope();
}

function renderScope() {
  const s = storeInfo(), i = indexInfo();
  if (!s) {
    $('scope').innerHTML = esc(stores.length ? t('scope_choose') : t('scope_none', { dir: startDir }));
    return;
  }
  $('scope').innerHTML = t('scope_on', { name: esc(s.name), store: esc(s.store) }) +
    (i ? ' · ' + t('scope_index', { p: esc(i.project), m: esc(i.model_key), d: esc(i.dim || '?'),
      what: esc([i.units ? t('has_units') : '', i.files ? t('has_files') : ''].filter(Boolean).join(' + ') || '—') }) : '');
}

function clearViews() {
  ['s-out', 'r-out', 'b-out', 'st-out'].forEach(id => { $(id).innerHTML = ''; });
  ['s-status', 'r-status', 't-status', 'b-status', 'st-status'].forEach(id => { $(id).textContent = ''; });
  $('t-out').hidden = true;
  lastSearch = lastRrf = lastBh = lastStatus = null;
}
$('store').onchange = () => {
  try { localStorage.setItem('simargl-store', store()); } catch {}
  clearViews(); renderProjects(); fillSources(); fillTriSources();
  if (currentTab === 'status') runStatus();
};
$('project').onchange = () => {
  try { localStorage.setItem('simargl-project', project()); } catch {}
  clearViews(); renderScope(); fillTriSources();
  if (currentTab === 'status') runStatus();
};
$('refresh').onclick = () => loadStores();

function need(statusId, withIndex = true) {
  if (!store()) { $(statusId).textContent = t('choose_store_first'); return false; }
  if (withIndex && !project()) { $(statusId).textContent = t('choose_index_first'); return false; }
  return true;
}

// ── search ───────────────────────────────────────────
$('s-mode').onchange = () => document.querySelectorAll('.refine-only').forEach(x => { x.hidden = $('s-mode').value !== 'refine'; });
let lastSearch = null;
async function runSearch() {
  if (!need('s-status')) return;
  const q = $('s-query').value.trim();
  if (!q) return;
  const st = store(), p = project();
  $('s-status').textContent = t('searching');
  try {
    const t0 = performance.now();
    const res = await api('/api/search', { store: st, project: p, query: q, mode: $('s-mode').value, sort: $('s-sort').value,
      top_n: +$('s-top-n').value, top_k: +$('s-top-k').value, top_m: +$('s-top-m').value,
      score_blend: +$('s-blend').value, coverage_penalty: +$('s-penalty').value,
      refine_top_k: +$('s-rk').value, refine_top_m: +$('s-rm').value,
      include_diff: $('s-diff').checked, exclude_blackholes: $('s-bh').checked });
    if (st !== store() || p !== project()) return;
    lastSearch = { res, ms: Math.round(performance.now() - t0) };
    drawSearch();
  } catch (e) { $('s-status').innerHTML = errHtml(e); }
}

function fileRows(files) {
  const max = Math.max(1e-9, ...files.map(f => f.score));
  return `<ol class="results flist">${files.map(f => `<li><span class="mono" title="${esc(f.path)}">${esc(f.path)}</span>
      <span class="dim">· ${esc(f.module || '')} · ${(+f.score).toFixed(3)}</span>
      <div class="scorebar"><span style="width:${Math.max(2, 100 * f.score / max)}%"></span></div></li>`).join('')}</ol>`;
}
function moduleRows(mods) {
  const max = Math.max(1e-9, ...mods.map(m => m.score));
  return `<ol class="results">${mods.map(m => `<li>${esc(m.module)} <span class="dim">${(+m.score).toFixed(3)}</span>
      <div class="scorebar"><span style="width:${Math.max(2, 100 * m.score / max)}%"></span></div></li>`).join('')}</ol>`;
}
function unitRows(units) {
  return units.map(u => `<div class="unit"><div class="head"><span class="sim">${(+u.similarity).toFixed(3)}</span>
      <b>${esc(u.unit_id)}</b> <span class="dim">${esc(u.unit_type || '')}</span></div>
      <div>${esc((u.text_preview || '').slice(0, 300))}</div>
      <div class="files dim">${esc(t('changed_files', { n: u.files.length }))}: ${u.files.slice(0, 8).map(f => `<span class="mono" title="${esc(f)}">${esc(base(f))}</span>`).join(', ')}${u.files.length > 8 ? ' …' : ''}</div>
      ${u.diff ? `<details><summary class="dim">${esc(t('diff'))}</summary><pre class="diff">${esc(u.diff.slice(0, 4000))}</pre></details>` : ''}</div>`).join('');
}

function drawSearch() {
  const { res, ms } = lastSearch;
  $('s-status').textContent = t('search_status', { ms, f: res.files.length, u: (res.units || []).length });
  const units = res.units || [];
  $('s-out').innerHTML = `<div class="res-grid">
      <div><h2>${esc(t('h_files'))}</h2>${res.files.length ? fileRows(res.files) : `<p class="dim">${esc(t('none'))}</p>`}</div>
      <div><h2>${esc(t('h_modules'))}</h2>${(res.modules || []).length ? moduleRows(res.modules) : `<p class="dim">${esc(t('none'))}</p>`}</div></div>
    ${units.length ? `<h2>${esc(t('h_answer_map'))}</h2><p class="dim">${esc(t('answer_map_note'))}</p>
      <div class="chart map" id="s-map"></div><div class="legend">${legendHtml()}</div>
      <h2>${esc(t('h_units'))}</h2>${unitRows(units)}` : ''}`;
  if (units.length) answerMap($('s-map'), units, res.files);
}
$('s-go').onclick = runSearch;
$('s-query').addEventListener('keydown', e => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) runSearch(); });

// ── the answer as a map: similar tasks (circles) and the files they changed (squares) ──
function legendHtml() {
  return `<span><svg width="14" height="14"><circle cx="7" cy="7" r="6" fill="var(--accent)"/></svg>${esc(t('lg_task'))}</span>
    <span><svg width="14" height="14"><rect x="1" y="1" width="12" height="12" rx="2" fill="var(--z-evolution)"/></svg>${esc(t('lg_file_found'))}</span>
    <span><svg width="14" height="14"><rect x="1" y="1" width="12" height="12" rx="2" fill="var(--dim)"/></svg>${esc(t('lg_file_other'))}</span>
    <span>${esc(t('lg_size_map'))}</span>`;
}

function answerMap(box, units, files) {
  const W = 1000, H = 520, SVG = 'http://www.w3.org/2000/svg';
  const found = new Set(files.map(f => f.path));
  const fileCount = new Map();
  const real = f => f && f !== 'unknown';                        // a placeholder path of the data, not a file
  units.forEach(u => u.files.filter(real).forEach(f => fileCount.set(f, (fileCount.get(f) || 0) + 1)));
  // the files at least two similar tasks share, plus the found ones; capped for legibility
  const keepFiles = [...fileCount.entries()].filter(([f, n]) => n >= 2 || found.has(f))
    .sort((a, b) => b[1] - a[1]).slice(0, 60).map(([f]) => f);
  const keep = new Set(keepFiles);
  const maxSim = Math.max(...units.map(u => u.similarity)), minSim = Math.min(...units.map(u => u.similarity));
  const nodes = [
    ...units.map((u, i) => ({ id: 'u:' + u.unit_id, kind: 'u', u, r: 7 + 9 * ((u.similarity - minSim) / Math.max(1e-9, maxSim - minSim)), i })),
    ...keepFiles.map(f => ({ id: 'f:' + f, kind: 'f', f, n: fileCount.get(f), r: Math.min(14, 4 + 3 * Math.sqrt(fileCount.get(f))), found: found.has(f) })),
  ];
  const idx = new Map(nodes.map((n, i) => [n.id, i]));
  const edges = [];
  units.forEach(u => u.files.forEach(f => { if (keep.has(f)) edges.push([idx.get('u:' + u.unit_id), idx.get('f:' + f)]); }));
  // tasks that share no kept file wait in a band at the bottom instead of drifting to the edges
  const linked = new Set(edges.flat());
  const lone = nodes.filter((n, i) => !linked.has(i));
  const band = lone.length ? 50 : 0;
  // force layout, deterministic start
  const AH = H - band;
  nodes.forEach((n, i) => { const a = i * 2.399; const r = 40 + 8 * Math.sqrt(i) * 6; n.x = W / 2 + r * Math.cos(a); n.y = AH / 2 + r * Math.sin(a) * 0.6; });
  const k = Math.sqrt(W * H / Math.max(1, nodes.length)) * 0.7;
  let temp = 60;
  for (let it = 0; it < 400; it++) {
    const dx = new Float64Array(nodes.length), dy = new Float64Array(nodes.length);
    for (let i = 0; i < nodes.length; i++) for (let j = i + 1; j < nodes.length; j++) {
      let x = nodes[i].x - nodes[j].x, y = nodes[i].y - nodes[j].y; const d = Math.hypot(x, y) || 0.01;
      let f = k * k / d; const min = nodes[i].r + nodes[j].r + 8; if (d < min) f += (min - d) * 6;
      x /= d; y /= d; dx[i] += x * f; dy[i] += y * f; dx[j] -= x * f; dy[j] -= y * f;
    }
    for (const [a, b] of edges) {
      let x = nodes[a].x - nodes[b].x, y = nodes[a].y - nodes[b].y; const d = Math.hypot(x, y) || 0.01, f = d * d / k * 0.5;
      x /= d; y /= d; dx[a] -= x * f; dy[a] -= y * f; dx[b] += x * f; dy[b] += y * f;
    }
    nodes.forEach((n, i) => {
      if (!linked.has(i)) return;
      dx[i] += (W / 2 - n.x) * 0.05; dy[i] += (AH / 2 - n.y) * 0.08;
      const d = Math.hypot(dx[i], dy[i]) || 1, s = Math.min(d, temp) / d; n.x += dx[i] * s; n.y += dy[i] * s;
    });
    temp = Math.max(0.5, temp * 0.985);
  }
  const net = nodes.filter((n, i) => linked.has(i));
  if (net.length) {
    const xs = net.map(n => n.x), ys = net.map(n => n.y);
    const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
    const sc = Math.min((W - 200) / Math.max(1, x1 - x0), (AH - 70) / Math.max(1, y1 - y0), 1.5);
    net.forEach(n => { n.x = W / 2 + (n.x - (x0 + x1) / 2) * sc; n.y = AH / 2 + (n.y - (y0 + y1) / 2) * sc; });
  }
  lone.forEach((n, j) => { n.x = 60 + j * ((W - 120) / Math.max(1, lone.length - 1 || 1)); n.y = AH + 18; });

  const el = (name, attrs, parent) => { const e = document.createElementNS(SVG, name); for (const [a, v] of Object.entries(attrs)) e.setAttribute(a, v); parent.appendChild(e); return e; };
  box.innerHTML = '';
  const svg = el('svg', { viewBox: `0 0 ${W} ${H}`, class: 'map-svg', role: 'img', 'aria-label': t('h_answer_map') }, box);
  const gE = el('g', {}, svg), gN = el('g', {}, svg), gL = el('g', {}, svg);
  const lines = edges.map(([a, b]) => el('line', { x1: nodes[a].x, y1: nodes[a].y, x2: nodes[b].x, y2: nodes[b].y, class: 'edge', 'stroke-width': 1.2 }, gE));
  const tip = document.createElement('div'); tip.className = 'tip'; tip.hidden = true; box.appendChild(tip);
  const placed = [];
  if (band) { const bt = el('text', { x: 40, y: AH - 8, class: 'band' }, gE); bt.textContent = t('lone_tasks'); }
  nodes.forEach((n, i) => {
    const g = el('g', { class: 'node', transform: `translate(${n.x},${n.y})` }, gN);
    if (n.kind === 'u') el('circle', { r: n.r, fill: 'var(--accent)', class: 'dot' }, g);
    else el('rect', { x: -n.r, y: -n.r, width: 2 * n.r, height: 2 * n.r, rx: 2, fill: n.found ? 'var(--z-evolution)' : 'var(--dim)', class: 'dot' }, g);
    const label = n.kind === 'u' ? n.u.unit_id : base(n.f);
    if (n.kind === 'u' || n.found) {
      const w = label.length * 6.2, x = n.x - w / 2, y = n.y + n.r + 2;
      if (!placed.some(b => x < b.x + b.w && b.x < x + w && y < b.y + 13 && b.y < y + 13)) {
        placed.push({ x, y, w });
        const tx = el('text', { x: n.x, y: n.y + n.r + 12, class: 'lab', 'text-anchor': 'middle' }, gL); tx.textContent = label;
      }
    }
    g.addEventListener('mouseenter', () => {
      svg.classList.add('focus');
      const mine = new Set(); edges.forEach(([a, b], j) => { const on = a === i || b === i; lines[j].classList.toggle('on', on); if (on) { mine.add(a); mine.add(b); } });
      gN.childNodes.forEach((c, j) => c.classList.toggle('on', mine.has(j) || j === i));
    });
    g.addEventListener('mousemove', ev => {
      const bb = box.getBoundingClientRect();
      tip.innerHTML = n.kind === 'u'
        ? `<b>${esc(n.u.unit_id)}</b> · ${(+n.u.similarity).toFixed(3)}<div>${esc((n.u.text_preview || '').slice(0, 140))}</div><div class="dim">${esc(t('changed_files', { n: n.u.files.length }))}</div>`
        : `<b>${esc(base(n.f))}</b><div class="dim">${esc(n.f)}</div><div>${esc(t('tip_file_tasks', { n: n.n }))}${n.found ? ' · ' + esc(t('tip_found')) : ''}</div>`;
      tip.style.left = `${Math.min(ev.clientX - bb.left + 14, bb.width - 300)}px`; tip.style.top = `${ev.clientY - bb.top + 14}px`; tip.hidden = false;
    });
    g.addEventListener('mouseleave', () => { tip.hidden = true; svg.classList.remove('focus'); lines.forEach(l => l.classList.remove('on')); gN.childNodes.forEach(c => c.classList.remove('on')); });
  });
}

// ── triangulation: simargl, gamayun, svitovyd on one task, fused by rank ──
let triSources = null, lastTri = null;
const TOOLS = ['simargl', 'gamayun', 'svitovyd'];
const nameOf = p => String(p || '').replace(/[\\/]+$/, '').split(/[\\/]/).pop().toLowerCase();

async function loadTriSources() {
  try { triSources = await api('/api/tri/sources'); } catch (e) { $('x-status').innerHTML = errHtml(e); return; }
  fillTriSources();
}
// pick the gamayun project and the svitovyd map of the same repository as the chosen store
function fillTriSources() {
  if (!triSources) return;
  const s = storeInfo(), repo = s ? nameOf(s.root) : '';
  $('x-sim').value = s && project() ? `${s.name} · ${project()}` : t('x_none');
  const keepG = $('x-gam').value, keepS = $('x-svi').value;
  $('x-gam').innerHTML = `<option value="">${esc(t('x_none'))}</option>` + triSources.gamayun.map(g =>
    `<option value="${esc(g.dir)}">${esc(g.project)}${g.kind === 'files' ? ' · ' + esc(t('x_code_project')) : ''}</option>`).join('');
  $('x-svi').innerHTML = `<option value="">${esc(t('x_none'))}</option>` + triSources.svitovyd.map(m =>
    `<option value="${esc(m.map)}">${esc(m.name)}</option>`).join('');
  const g = triSources.gamayun.find(x => x.kind === 'tasks' && (nameOf(x.repo) === repo || x.project === repo))
    || triSources.gamayun.find(x => x.kind === 'tasks' && repo.includes(x.project));
  const m = triSources.svitovyd.find(x => nameOf(x.root) === repo || x.name.toLowerCase() === repo);
  $('x-gam').value = keepG && triSources.gamayun.some(x => x.dir === keepG) ? keepG : (g ? g.dir : '');
  $('x-svi').value = keepS && triSources.svitovyd.some(x => x.map === keepS) ? keepS : (m ? m.map : '');
}

async function runTri() {
  const q = $('x-query').value.trim();
  if (!q) return;
  $('x-status').textContent = t('searching');
  try {
    const t0 = performance.now();
    const res = await api('/api/triangulate', { store: store(), project: project(), gamayun: $('x-gam').value,
      map: $('x-svi').value, query: q, k: +$('x-k').value || 50, sort: $('x-sort').value });
    lastTri = { res, ms: Math.round(performance.now() - t0) };
    drawTri();
  } catch (e) { $('x-status').innerHTML = errHtml(e); }
}

function drawTri() {
  const { res, ms } = lastTri;
  const used = TOOLS.filter(x => res.tools[x]);
  $('x-status').textContent = t('x_status', { ms, n: used.length, moved: res.moved || 0 });
  const errs = Object.entries(res.errors || {}).map(([k, v]) => `<div class="err">${esc(k)}: ${esc(v)}</div>`).join('');
  const top = res.fused.slice(0, res.top);
  const groups = [3, 2, 1].map(n => top.filter(f => f.tools === n).length);
  const total = Math.max(1, top.length);
  const strip = `<div class="agree">${groups.map((g, i) => g ? `<span style="width:${100 * g / total}%;background:color-mix(in oklab, var(--accent) ${[100, 60, 25][i]}%, var(--panel))" title="${esc(t('x_group_' + (3 - i), { n: g }))}"></span>` : '').join('')}</div>
    <div class="legend">${groups.map((g, i) => `<span>${esc(t('x_group_' + (3 - i), { n: g }))}</span>`).join('')}
      ${Object.entries(res.overlap || {}).map(([k, v]) => `<span>${esc(k.replace('|', ' ∩ '))} ${pct(v)}</span>`).join('')}</div>`;
  const per = used.map(x => `<span class="tdot ${x}"></span> ${x} <span class="dim">${esc(t('x_tool_line', { n: res.tools[x].length, s: res.times[x] }))}</span>`).join(' &nbsp; ');
  const rows = res.fused.map((f, i) => `<tr><td class="r">${i + 1}</td>
      <td class="r">${TOOLS.map(x => `<span class="trank ${x}${f.ranks[x] ? ' on' : ''}" title="${esc(x)}">${f.ranks[x] || '·'}</span>`).join('')}</td>
      <td><span class="mono" title="${esc(f.file)}">${esc(f.file)}</span>${f.share ? ` <span class="badge comp" title="${esc(t('x_companion_title'))}">${esc(t('x_companion', { p: pct(f.share) }))}</span>` : ''}${f.gone ? ` <span class="badge gone" title="${esc(t('x_gone_title'))}">${esc(t('x_gone'))}</span>` : ''}${f.was ? `<div class="moved">${esc(t('x_was', { p: f.was.join(', ') }))}</div>` : ''}</td></tr>`).join('');
  const idents = (res.identifiers || []).length ? `<div class="dim">${esc(t('x_idents'))}: ${res.identifiers.map(x => `<code title="${esc(t('x_word_title', { i: x.identifiers, f: x.files }))}">${esc(x.word)}</code>`).join(', ')}</div>` : '';
  $('x-out').innerHTML = `${errs}<div class="row">${per}</div>${idents}
    <h2>${esc(t('x_top', { n: res.top }))}</h2>${strip}
    <table class="h fused"><tr><th>#</th><th>${TOOLS.map(x => `<span class="tdot ${x}"></span>`).join(' ')}</th><th>${esc(t('h_files'))}</th></tr>${rows}</table>
    <details><summary class="dim">${esc(t('x_each'))}</summary><div class="res-grid" style="grid-template-columns:repeat(${Math.max(1, used.length)}, minmax(0,1fr))">
      ${used.map(x => `<div><h3><span class="tdot ${x}"></span> ${x}</h3><ol class="results">${res.tools[x].slice(0, 20).map(f =>
        `<li><span class="mono" title="${esc(f.file)}">${esc(base(f.file))}</span> <span class="dim">${esc(f.why || '')}</span></li>`).join('')}</ol></div>`).join('')}
    </div></details>`;
}
$('x-go').onclick = runTri;
$('x-query').addEventListener('keydown', e => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) runTri(); });

// ── RRF ──────────────────────────────────────────────
function fillSources() {
  const s = storeInfo();
  const keep = new Set([...document.querySelectorAll('#r-sources input:checked')].map(i => i.value));
  const opts = [];
  (s ? s.indexes : []).forEach(i => {
    if (i.units) opts.push(`task:${i.project}`);
    if (i.files) { opts.push(`file:${i.project}`); }
    if (i.units && i.files) opts.push(`aggr:${i.project}`);
  });
  $('r-sources').innerHTML = opts.length ? opts.map((o, n) => `<label><input type="checkbox" value="${esc(o)}" ${keep.size ? (keep.has(o) ? 'checked' : '') : (n < 2 ? 'checked' : '')}>${esc(o)}</label>`).join('')
    : `<span class="dim">${esc(t('no_sources'))}</span>`;
}
let lastRrf = null;
async function runRrf() {
  if (!need('r-status', false)) return;
  const q = $('r-query').value.trim();
  const sources = [...document.querySelectorAll('#r-sources input:checked')].map(i => i.value).join(',');
  if (!q) return;
  $('r-status').textContent = t('searching');
  try {
    const res = await api('/api/rrf', { store: store(), query: q, sources, top_n: +$('r-top-n').value, top_k: +$('r-top-k').value,
      k: +$('r-k').value, sort: $('r-sort').value, score_blend: +$('r-blend').value, coverage_penalty: +$('r-penalty').value });
    lastRrf = { res };
    drawRrf();
  } catch (e) { $('r-status').innerHTML = errHtml(e); }
}
function drawRrf() {
  const { res } = lastRrf;
  $('r-status').textContent = '';
  $('r-out').innerHTML = `<div class="res-grid"><div><h2>${esc(t('h_files'))}</h2>${res.files.length ? fileRows(res.files) : `<p class="dim">${esc(t('none'))}</p>`}</div>
    <div><h2>${esc(t('h_modules'))}</h2>${(res.modules || []).length ? moduleRows(res.modules) : `<p class="dim">${esc(t('none'))}</p>`}</div></div>
    <h2>${esc(t('h_sources'))}</h2>${(res.sources || []).map(s => `<div class="unit"><b>${esc(s.mode)}:${esc(s.project_id)}</b>
      ${s.error ? ` <span class="err">${esc(s.error)}</span>` : `<div class="files">${(s.files || []).slice(0, 8).map(f => `<span class="mono" title="${esc(f.path)}">${esc(base(f.path))}</span>`).join(', ')}</div>`}</div>`).join('')}`;
}
$('r-go').onclick = runRrf;

// ── retrieve ─────────────────────────────────────────
$('t-go').onclick = async () => {
  if (!need('t-status')) return;
  const q = $('t-query').value.trim();
  if (!q) return;
  $('t-status').textContent = t('searching');
  try {
    const r = await api('/api/retrieve', { store: store(), project: project(), query: q, mode: $('t-mode').value,
      top_n: +$('t-top-n').value, score_blend: +$('t-blend').value, coverage_penalty: +$('t-penalty').value,
      exclude_blackholes: $('t-bh').checked, source_dir: $('t-src').value.trim() });
    $('t-out').hidden = false;
    $('t-out').textContent = r.text || t('none');
    $('t-status').textContent = t('chars_n', { n: (r.text || '').length.toLocaleString() });
  } catch (e) { $('t-status').innerHTML = errHtml(e); }
};
$('t-copy').onclick = () => { try { navigator.clipboard.writeText($('t-out').textContent); $('t-status').textContent = t('copied'); } catch {} };

// ── blackholes ───────────────────────────────────────
let lastBh = null;
async function runBh(listOnly) {
  if (!need('b-status')) return;
  $('b-status').textContent = t('computing');
  try {
    const r = await api('/api/blackhole', { store: store(), project: project(), list_only: listOnly, method: $('b-method').value,
      threshold: +$('b-thr').value, n_queries: +$('b-n').value, top_k: +$('b-k').value });
    lastBh = { r, listOnly };
    drawBh();
  } catch (e) { $('b-status').innerHTML = errHtml(e); }
}
function drawBh() {
  const { r, listOnly } = lastBh;
  $('b-status').textContent = '';
  const head = listOnly ? '' : `<div class="kpis">${Object.entries(r).filter(([k, v]) => k !== 'paths' && typeof v !== 'object')
    .map(([k, v]) => `<span>${esc(k)} <b>${esc(typeof v === 'number' ? (+v).toLocaleString() : v)}</b></span>`).join('')}</div>`;
  $('b-out').innerHTML = head + `<h3>${esc(t('bh_marked', { n: r.paths.length }))}</h3>` +
    (r.paths.length ? `<ul class="tree">${r.paths.map(p => `<li class="mono">${esc(p)}</li>`).join('')}</ul>` : `<p class="dim">${esc(t('none'))}</p>`);
}
$('b-go').onclick = () => runBh(false);
$('b-list').onclick = () => runBh(true);

// ── index: models, jobs ──────────────────────────────
let models = null;
async function loadModels() {
  try {
    models = await api('/api/models', { host: $('m-host').value.trim() });
    drawModels();
  } catch (e) { $('m-info').innerHTML = errHtml(e); }
}
function drawModels() {
  if (!models) return;
  const m = models;
  const ollama = m.ollama.map(h => `<div><code>${esc(h.host)}</code> — ${h.models.length ? h.models.map(x => `<code>${esc(x)}</code>`).join(', ')
    : esc(t('ollama_none'))}</div>`).join('');
  $('m-info').innerHTML = `<div>${t('model_default', { m: `<code>${esc(m.default)}</code>` })}</div>
    <div>${m.torch ? t('torch_yes', { list: m.local.map(x => `<code>${esc(x)}</code>`).join(', ') }) : t('torch_no')}</div>
    <div style="margin-top:6px"><b>Ollama</b> <span class="dim">${esc(t('ollama_batch', { n: m.ollama_batch }))}</span></div>${ollama}`;
  const opts = [m.default, ...m.ollama.flatMap(h => h.models.map(x => 'ollama://' + x + (h.host.includes('localhost') ? '' : '@' + h.host.replace(/^https?:\/\//, '')))),
    ...(m.torch ? m.local : [])];
  $('model-list').innerHTML = [...new Set(opts)].map(o => `<option value="${esc(o)}">`).join('');
}
$('m-refresh').onclick = loadModels;

async function runJob(promise) {
  const log = $('job-log');
  log.hidden = false;
  log.textContent = t('starting');
  try {
    const { job } = await promise;
    while (true) {
      const j = await api('/api/jobs/' + job);
      log.textContent = j.log.join('\n') + (j.error ? '\n' + j.error : '') + (j.status === 'done' ? '\n' + t('job_done') : '');
      log.scrollTop = log.scrollHeight;
      if (j.status !== 'running') { if (j.status === 'done') { await loadStores(); loadModels(); } return; }
      await new Promise(r => setTimeout(r, 1000));
    }
  } catch (e) { log.textContent = e.message; }
}
$('m-pull-go').onclick = () => runJob(api('/api/pull', { model: $('m-pull').value.trim() }));
function needStore() {
  if (store()) return true;
  $('job-log').hidden = false; $('job-log').textContent = t('choose_store_first');
  return false;
}
$('u-go').onclick = () => { if (needStore()) runJob(api('/api/admin', { store: store(), action: 'units',
  project: $('u-project').value.trim(), db: $('u-db').value.trim(), model: $('u-model').value.trim(), mode: $('u-mode').value })); };
$('f-go').onclick = () => { if (needStore()) runJob(api('/api/admin', { store: store(), action: 'files', project: $('f-project').value.trim(),
  source: $('f-src').value.trim(), model: $('f-model').value.trim(), chunk_size: +$('f-chunk').value, full: $('f-full').checked })); };
$('v-go').onclick = () => { if (needStore() && project()) runJob(api('/api/admin', { store: store(), action: 'vacuum', project: project() })); };

// ── status ───────────────────────────────────────────
let lastStatus = null;
async function runStatus() {
  if (!need('st-status', false)) return;
  $('st-status').textContent = t('loading');
  try {
    lastStatus = await api('/api/status', { store: store(), project: project() });
    drawStatus();
  } catch (e) { $('st-status').innerHTML = errHtml(e); }
}
function drawStatus() {
  const r = lastStatus;
  $('st-status').textContent = '';
  const stats = r.stats ? `<div class="kpis">${Object.entries(r.stats).filter(([, v]) => typeof v !== 'object')
    .map(([k, v]) => `<span>${esc(k)} <b>${esc(typeof v === 'number' ? (+v).toLocaleString() : v)}</b></span>`).join('')}</div>
    <div class="row"><a class="small ent" href="/api/download?store=${encodeURIComponent(r.store)}&project=${encodeURIComponent(project())}">${esc(t('download_zip'))}</a></div>` : '';
  $('st-out').innerHTML = `<h2>${esc(project() ? t('st_index', { p: project() }) : t('st_store'))}</h2>${stats}`;
}
$('st-go').onclick = runStatus;

// a new language: redraw what JS drew, from the answers in hand
langHooks.push(() => {
  fillThemes();
  renderStores();
  fillSources();
  if (lastSearch && $('s-out').innerHTML) drawSearch();
  fillTriSources();
  if (lastTri && $('x-out').innerHTML) drawTri();
  if (lastRrf && $('r-out').innerHTML) drawRrf();
  if (lastBh && $('b-out').innerHTML) drawBh();
  if (lastStatus && $('st-out').innerHTML) drawStatus();
  drawModels();
});

// ?tab=…&store=…&project=…&q=… open straight to a view
loadStores().then(() => {
  const u = new URLSearchParams(location.search);
  if (u.get('store') && stores.some(s => s.store === u.get('store'))) { $('store').value = u.get('store'); renderProjects(); }
  if (u.get('project')) { $('project').value = u.get('project'); renderScope(); }
  const tab = u.get('tab') || 'search';
  showTab(tab);
  if (u.get('q')) {
    $('s-query').value = u.get('q');
    if (u.get('mode')) $('s-mode').value = u.get('mode');
    if (tab === 'search') runSearch();
    if (tab === 'tri') { $('x-query').value = u.get('q'); loadTriSources().then(runTri); }
  }
}).catch(e => { $('scope').innerHTML = errHtml(e); });
