/* Opening Leak Lab — dashboard client.
   Talks to a local FastAPI analyzer on :8000, or to a same-origin serverless API
   when hosted (the backend reports `serverless: true` from /api/meta). */
const PORT_PROXY = '__PORT_8000__';
const LOCAL_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0'];
// Three ways this page gets served:
//   1. Perplexity preview  -> the placeholder is rewritten to a proxy URL for port 8000
//   2. static dev server on :8080 (or opened from disk) -> talk to api_server.py on :8000
//   3. anything else, including the hosted serverless build -> same origin
const DETACHED = location.protocol === 'file:' || location.port === '8080';
const API = PORT_PROXY.startsWith('__')
  ? ((LOCAL_HOSTS.includes(location.hostname) || location.protocol === 'file:') && DETACHED
      ? 'http://localhost:8000'
      : '')
  : PORT_PROXY;

const $ = (id) => document.getElementById(id);
const state = {
  files: [],
  jobId: null,
  serverless: false,
  csvText: '',
  rows: [],
  summary: null,
  player: null,
  sort: { key: 'priority', dir: -1 },
  filter: { flag: 'all', color: 'all', q: '' },
  selected: null,
  charts: {},
  meta: null,
};

const num = (v) => {
  const n = parseFloat(v);
  return Number.isFinite(n) ? n : null;
};
const fmt = (v, digits = 1, suffix = '') => (num(v) === null ? '—' : num(v).toFixed(digits) + suffix);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

/* The hosted function has a time budget, so cap the controls it cannot honour. */
function applyHostedLimits(limits) {
  const depth = $('optDepth');
  if (limits.max_depth) {
    // setting max makes the browser clamp value for us, so mirror it into the label
    depth.max = String(limits.max_depth);
    if (Number(depth.value) > limits.max_depth) depth.value = String(limits.max_depth);
    $('depthOut').textContent = depth.value;
  }
  if (limits.max_upload_mb) {
    $('uploadHint').textContent =
      `Up to ${limits.max_upload_mb} MB per run · parsed with python-chess`;
  }
  $('sideFoot').textContent =
    'Everything runs inside the deployed function: a bundled Stockfish build and a bundled '
    + 'SQLite opening book. No API keys, no rate limits.';
  $('hostedNoticeText').textContent =
    `Runs here are capped at depth ${limits.max_depth}, ${limits.max_games} games and `
    + `${limits.max_upload_mb} MB per upload, and the engine pass stops after `
    + `${limits.time_budget_s}s. Clone the repo for unlimited local runs.`;
  $('hostedNotice').hidden = false;
}

/* --------------------------------------------------------------------- meta */
async function loadMeta() {
  try {
    const meta = await (await fetch(`${API}/api/meta`)).json();
    state.meta = meta;
    state.serverless = meta.serverless === true;
    if (state.serverless) applyHostedLimits(meta.limits || {});
    const e = meta.engine || {};
    const d = meta.database || {};

    $('pillEngine').className = 'pill ' + (e.available ? 'ok' : 'bad');
    $('pillEngine').lastChild.textContent = e.available ? e.name + (e.bundled ? ' · bundled' : '') : 'Engine missing';
    $('pillDb').className = 'pill ' + (d.available ? 'ok' : 'bad');
    $('pillDb').lastChild.textContent = d.available ? `${(d.games / 1000).toFixed(0)}k book games` : 'No book';
    $('sideEngine').textContent = e.available ? e.name.replace('Stockfish ', 'SF ') : 'missing';
    $('sideGames').textContent = d.available ? d.games.toLocaleString() : '—';
    $('sidePositions').textContent = d.available ? d.positions.toLocaleString() : '—';

    $('engineFacts').innerHTML = e.available
      ? `<dt>Build</dt><dd>${esc(e.name)}</dd><dt>Path</dt><dd>${esc(e.path)}</dd>
         <dt>Shipped</dt><dd>${e.bundled ? 'inside the package' : 'system install'}</dd>
         <dt>Protocol</dt><dd>UCI, MultiPV ${meta.defaults.multipv}</dd>`
      : '<dt>Status</dt><dd>not found</dd>';
    $('dbFacts').innerHTML = d.available
      ? `<dt>Games folded</dt><dd>${d.games.toLocaleString()}</dd>
         <dt>Positions</dt><dd>${d.positions.toLocaleString()}</dd>
         <dt>Move rows</dt><dd>${d.move_rows.toLocaleString()}</dd>
         <dt>Named lines</dt><dd>${d.named_openings.toLocaleString()}</dd>
         <dt>Filters</dt><dd>${esc(d.filters)}</dd>
         <dt>File size</dt><dd>${d.size_mb} MB</dd>`
      : '<dt>Status</dt><dd>not built</dd>';

    if (!meta.sample.available) {
      $('sampleBtn').disabled = true;
      $('sampleDl').style.display = 'none';
    }
    $('sampleDl').href = `${API}/api/sample-archive`;
    $('engineNotice').hidden = e.available !== false;
    if (e.available === false) {
      $('optNoEngine').checked = true;
      $('optNoEngine').disabled = true;
    }
    $('footStatus').textContent = e.available && d.available ? 'engine + book ready' : 'degraded';
  } catch (err) {
    $('pillEngine').className = 'pill bad';
    $('pillEngine').lastChild.textContent = 'Backend offline';
    $('footStatus').textContent = 'backend offline';
  }
}

/* ---------------------------------------------------------------- run panel */
function renderFiles() {
  const list = $('fileList');
  list.hidden = state.files.length === 0;
  list.innerHTML = state.files
    .map((f) => `<li><span>${esc(f.name)}</span><span>${(f.size / 1024).toFixed(0)} KB</span></li>`)
    .join('');
  $('runBtn').textContent = state.files.length ? `Analyse ${state.files.length} file${state.files.length > 1 ? 's' : ''}` : 'Analyse my games';
}

function collectOptions(useSample) {
  const fd = new FormData();
  fd.append('use_sample', useSample ? 'true' : 'false');
  fd.append('player', $('optPlayer').value.trim());
  fd.append('color', $('optColor').value);
  fd.append('depth', $('optDepth').value);
  fd.append('max_moves', $('optMoves').value);
  fd.append('min_games', $('optMinGames').value);
  fd.append('eval_drop', $('optEvalDrop').value);
  fd.append('score_gap', $('optScoreGap').value);
  fd.append('min_db_games', $('optMinDb').value);
  fd.append('no_engine', $('optNoEngine').checked ? 'true' : 'false');
  if (!useSample) state.files.forEach((f) => fd.append('files', f, f.name));
  return fd;
}

async function startRun(useSample) {
  if (!useSample && !state.files.length) {
    $('dropzone').classList.add('is-over');
    setTimeout(() => $('dropzone').classList.remove('is-over'), 700);
    return;
  }
  setBusy(true);
  showKpiSkeleton();
  $('progressCard').hidden = false;
  $('spinner').className = 'spinner';
  $('progressTitle').textContent = useSample ? 'Analysing demo archive' : 'Analysing your games';
  $('log').textContent = 'Queued…';
  $('barFill').style.width = '8%';
  $('barFill').classList.remove('is-error');
  $('headerSub').textContent = 'Run in progress — engine and book lookups are local.';

  try {
    if (state.serverless) return await runSynchronous(useSample);
    const res = await fetch(`${API}/api/analyze`, { method: 'POST', body: collectOptions(useSample) });
    if (!res.ok) throw new Error((await res.json()).detail || `HTTP ${res.status}`);
    state.jobId = (await res.json()).job_id;
    poll();
  } catch (err) {
    failRun(err.message);
  }
}

/* Hosted deployment: one request returns the finished report, so there is no job
   to poll. Animate the bar while the function works. */
async function runSynchronous(useSample) {
  const started = Date.now();
  $('log').textContent = 'Running in the hosted function — engine and book are bundled with it.';
  const tick = setInterval(() => {
    const secs = (Date.now() - started) / 1000;
    $('progressElapsed').textContent = `${secs.toFixed(1)}s`;
    $('barFill').style.width = `${Math.min(90, 8 + secs * 3)}%`;
  }, 200);
  try {
    const res = await fetch(`${API}/api/analyze`, { method: 'POST', body: collectOptions(useSample) });
    const body = await res.json();
    if (!res.ok) throw new Error(body.detail || `HTTP ${res.status}`);
    clearInterval(tick);
    $('barFill').style.width = '100%';
    $('spinner').className = 'spinner is-done';
    $('progressTitle').textContent = `Done in ${body.elapsed}s`;
    $('progressElapsed').textContent = `${body.elapsed}s`;
    const lines = (body.log || []).slice();
    (body.notes || []).forEach((n) => lines.push(`note: ${n}`));
    $('log').textContent = lines.join('\n');
    $('log').scrollTop = $('log').scrollHeight;
    state.csvText = body.csv || '';
    applyReport(body, { options: body.options, source: useSample ? 'sample' : 'upload' });
    setBusy(false);
  } catch (err) {
    clearInterval(tick);
    failRun(err.message);
  }
}

function failRun(message) {
  setBusy(false);
  $('spinner').className = 'spinner is-error';
  $('progressTitle').textContent = 'Run failed';
  $('log').textContent = message;
  $('barFill').style.width = '100%';
  $('barFill').classList.add('is-error');
  $('headerSub').textContent = 'Last run failed — see the log.';
  $('kpis').innerHTML = '';
}

async function poll() {
  let ticks = 0;
  const step = async () => {
    ticks += 1;
    let job;
    try {
      job = await (await fetch(`${API}/api/jobs/${state.jobId}`)).json();
    } catch (err) {
      return failRun('Lost contact with the backend');
    }
    $('log').textContent = (job.log || []).join('\n');
    $('log').scrollTop = $('log').scrollHeight;
    $('progressElapsed').textContent = `${job.elapsed}s`;
    $('barFill').style.width = `${Math.min(92, 8 + ticks * 4)}%`;
    if (job.status === 'error') return failRun(job.error || 'Unknown error');
    if (job.status !== 'done') return setTimeout(step, 1200);

    $('barFill').style.width = '100%';
    $('spinner').className = 'spinner is-done';
    $('progressTitle').textContent = `Done in ${job.elapsed}s`;
    await loadReport(job);
    setBusy(false);
  };
  step();
}

function setBusy(busy) {
  ['runBtn', 'sampleBtn', 'runTop'].forEach((id) => ($(id).disabled = busy));
  $('runTop').textContent = busy ? 'Running…' : 'Run analysis';
}

/* ------------------------------------------------------------------ reports */
async function loadReport(job) {
  const data = await (await fetch(`${API}/api/report/${state.jobId}`)).json();
  state.csvText = '';
  applyReport(data, job);
}

function applyReport(data, job) {
  state.rows = data.rows;
  state.summary = data.summary;
  state.player = data.player;
  $('csvBtn').disabled = false;
  const s = data.summary;
  const engineNote = job.options.no_engine ? 'engine skipped' : `depth ${job.options.depth}`;
  $('headerSub').textContent = `${state.player} · ${s.games} games · ${s.judged} repeated decisions · ${s.leaks} leaks · ${engineNote}`;
  $('overviewHint').textContent = `${job.source === 'sample' ? 'Demo archive' : 'Your upload'} · ${s.games} games`;
  $('footStatus').textContent = state.serverless
    ? `hosted run · ${s.leaks} leaks`
    : `job ${state.jobId} · ${s.leaks} leaks`;
  renderKpis(s);
  renderCharts(s);
  renderTable();
  const first = sortedRows()[0];
  if (first) selectRow(first);
}

function showKpiSkeleton() {
  $('kpis').innerHTML = Array.from({ length: 6 })
    .map(() => '<div class="kpi kpi-skeleton"><div class="kpi-label">loading</div><div class="kpi-value">0.0</div><div class="kpi-note">loading</div></div>')
    .join('');
}

function renderKpis(s) {
  const worst = s.by_opening[0];
  const cards = [
    { label: 'Games parsed', value: s.games, note: `${s.decisions} distinct decisions` },
    { label: 'Repeated decisions', value: s.judged, note: 'played often enough to judge' },
    { label: 'Leaks flagged', value: s.leaks, cls: 'accent', note: `${s.white_leaks} white · ${s.black_leaks} black` },
    { label: 'Points shed', value: s.lost_points.toFixed(1), cls: 'bad', note: 'vs book expectation' },
    { label: 'Engine drops', value: s.blunders, cls: 'bad', note: '≥0.8 pawns lost on the spot' },
    { label: 'Worst opening', value: worst ? worst.lost_points.toFixed(1) : '0', cls: 'accent', note: worst ? worst.opening : 'nothing flagged' },
  ];
  $('kpis').innerHTML = cards
    .map(
      (c) => `<div class="kpi ${c.cls || ''}">
        <div class="kpi-label">${esc(c.label)}</div>
        <div class="kpi-value" data-target="${typeof c.value === 'number' ? c.value : ''}">${esc(c.value)}</div>
        <div class="kpi-note">${esc(c.note)}</div></div>`
    )
    .join('');
  countUp();
}

function countUp() {
  document.querySelectorAll('.kpi-value[data-target]').forEach((el) => {
    const target = parseFloat(el.dataset.target);
    if (!Number.isFinite(target) || target === 0) return;
    const started = performance.now();
    const tick = (now) => {
      const t = Math.min(1, (now - started) / 550);
      el.textContent = Math.round(target * (1 - Math.pow(1 - t, 3)));
      if (t < 1) requestAnimationFrame(tick);
      else el.textContent = target;
    };
    requestAnimationFrame(tick);
  });
}

/* ------------------------------------------------------------------- charts */
const CHART_FONT = { family: "'Inter', sans-serif", size: 11 };
function chartBase() {
  Chart.defaults.color = '#949c9f';
  Chart.defaults.font = CHART_FONT;
  Chart.defaults.borderColor = '#252d33';
}

function renderCharts(s) {
  if (!window.Chart) return;
  document.querySelectorAll('.chart-empty').forEach((el) => el.remove());
  chartBase();
  const items = s.by_opening.slice(0, 8);
  const labels = items.map((o) => (o.opening.length > 30 ? o.opening.slice(0, 29) + '…' : o.opening));

  Object.values(state.charts).forEach((c) => c.destroy());
  state.charts.lost = new Chart($('chartLost'), {
    type: 'bar',
    data: {
      labels,
      datasets: [{ label: 'Points lost', data: items.map((o) => o.lost_points), backgroundColor: '#e3a44b', borderRadius: 3, barThickness: 16 }],
    },
    options: {
      indexAxis: 'y',
      maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { callbacks: { afterLabel: (c) => `${items[c.dataIndex].leaks} leaks · ${items[c.dataIndex].games} games` } } },
      scales: { x: { grid: { color: '#1c2327' }, ticks: { precision: 1 } }, y: { grid: { display: false } } },
    },
  });

  state.charts.vs = new Chart($('chartVs'), {
    type: 'bar',
    data: {
      labels,
      datasets: [
        { label: 'Your score %', data: items.map((o) => o.your_score), backgroundColor: '#e06a5f', borderRadius: 3 },
        { label: 'Book score %', data: items.map((o) => o.db_score), backgroundColor: '#79a9c9', borderRadius: 3 },
      ],
    },
    options: {
      maintainAspectRatio: false,
      plugins: { legend: { position: 'bottom', labels: { boxWidth: 10, boxHeight: 10 } } },
      scales: {
        x: { grid: { display: false }, ticks: { maxRotation: 40, minRotation: 40, autoSkip: false, font: { ...CHART_FONT, size: 9.5 } } },
        y: { beginAtZero: true, max: 100, grid: { color: '#1c2327' }, ticks: { callback: (v) => v + '%' } },
      },
    },
  });
}

/* -------------------------------------------------------------------- table */
function sortedRows() {
  const { key, dir } = state.sort;
  const q = state.filter.q.toLowerCase();
  return state.rows
    .filter((r) => {
      if (state.filter.flag !== 'all' && !(r.flag || '').includes(state.filter.flag)) return false;
      if (state.filter.color !== 'all' && r.player_color !== state.filter.color) return false;
      if (q && !`${r.opening} ${r.eco} ${r.your_move} ${r.variation_line}`.toLowerCase().includes(q)) return false;
      return true;
    })
    .slice()
    .sort((a, b) => {
      const av = num(a[key]);
      const bv = num(b[key]);
      if (av !== null && bv !== null) return (av - bv) * dir;
      return String(a[key] ?? '').localeCompare(String(b[key] ?? '')) * dir;
    });
}

function flagChips(flag) {
  return (flag || '')
    .split('+')
    .filter(Boolean)
    .map((f) => {
      const cls = f === 'EVAL_DROP' ? 'chip-eval' : f === 'WINRATE_DECLINE' ? 'chip-win' : 'chip-off';
      const label = f === 'EVAL_DROP' ? 'eval' : f === 'WINRATE_DECLINE' ? 'win-rate' : 'offbeat';
      return `<span class="chip ${cls}">${label}</span>`;
    })
    .join(' ');
}

function renderTable() {
  const rows = sortedRows();
  $('tableEmpty').hidden = rows.length > 0;
  $('leakBody').innerHTML = rows
    .map((r, i) => {
      const book = num(r.db_move_score_pct);
      const gap = num(r.score_gap_vs_db_pct);
      const drop = num(r.eval_drop_pawns);
      return `<tr data-i="${i}" class="${state.selected && state.selected.fen === r.fen && state.selected.your_move === r.your_move ? 'is-selected' : ''}">
        <td class="num">${fmt(r.priority, 1)}</td>
        <td>${flagChips(r.flag)}</td>
        <td class="opening-cell"><span class="truncate" title="${esc(r.opening)}">${esc(r.opening || r.eco || '—')}</span></td>
        <td class="line-cell"><span class="truncate" title="${esc(r.variation_line)}">${esc(r.variation_line)}</span></td>
        <td class="move-cell">${r.move_number}${r.player_color === 'white' ? '.' : '…'} ${esc(r.your_move)}</td>
        <td class="num">${esc(r.your_games)}</td>
        <td class="num ${gap !== null && gap < 0 ? 'delta-bad' : ''}">${fmt(r.your_score_pct, 1, '%')}</td>
        <td class="num book-val">${book === null ? '—' : book.toFixed(1) + '%'}</td>
        <td class="num">${fmt(r.lost_points, 1)}</td>
        <td class="num ${drop && drop >= 0.8 ? 'delta-bad' : ''}">${drop === null || drop === 0 ? '—' : '−' + drop.toFixed(2)}</td>
        <td class="engine-cell">${esc(r.engine_best_1 || '—')}</td>
      </tr>`;
    })
    .join('');
  $('leakBody').querySelectorAll('tr').forEach((tr) => {
    tr.addEventListener('click', () => selectRow(rows[+tr.dataset.i]));
  });
}

/* ------------------------------------------------------------------- detail */
const GLYPH = { k: '♚', q: '♛', r: '♜', b: '♝', n: '♞', p: '♟' };
function renderBoard(fen) {
  const [placement, turn] = fen.split(' ');
  const files = 'abcdefgh';
  let html = '';
  placement.split('/').forEach((rankStr, rankIdx) => {
    let fileIdx = 0;
    for (const ch of rankStr) {
      if (/\d/.test(ch)) {
        for (let k = 0; k < +ch; k++, fileIdx++) html += square(fileIdx, rankIdx, '');
      } else {
        html += square(fileIdx, rankIdx, ch);
        fileIdx += 1;
      }
    }
  });
  $('board').innerHTML = html;
  $('board').setAttribute('aria-label', `Position with ${turn === 'w' ? 'white' : 'black'} to move`);

  function square(f, r, piece) {
    const light = (f + r) % 2 === 0;
    const glyph = piece ? `<span class="piece ${piece === piece.toUpperCase() ? 'w' : 'b'}">${GLYPH[piece.toLowerCase()]}</span>` : '';
    const coord = r === 7 ? `<span class="coord">${files[f]}${8 - r}</span>` : '';
    return `<div class="sq ${light ? 'light' : 'dark'}">${glyph}${coord}</div>`;
  }
}

function cpText(cp, color) {
  const v = num(cp);
  if (v === null) return '—';
  const pawns = v / 100;
  const signed = (pawns >= 0 ? '+' : '') + pawns.toFixed(2);
  return signed + (color === 'black' ? ' (yours)' : '');
}

function selectRow(r) {
  if (!r) return;
  state.selected = r;
  $('detailEmpty').hidden = true;
  $('detailBody').hidden = false;
  $('posHint').textContent = `${r.eco || '—'} · move ${r.move_number} as ${r.player_color}`;
  $('detailFlag').outerHTML = `<span class="chip" id="detailFlag">${flagChips(r.flag) || '—'}</span>`;
  $('detailOpening').textContent = r.opening || r.eco || 'Unclassified';
  $('detailLine').textContent = r.variation_line;
  renderBoard(r.fen);
  $('fenText').textContent = r.fen;
  $('lichessLink').href = `https://lichess.org/analysis/standard/${encodeURIComponent(r.fen.replace(/ /g, '_'))}`;

  const gap = num(r.score_gap_vs_db_pct);
  const stats = [
    { label: 'Your score', value: fmt(r.your_score_pct, 1, '%'), note: `${r.your_wins}W ${r.your_draws}D ${r.your_losses}L` },
    { label: 'Book score', value: num(r.db_move_score_pct) === null ? '—' : fmt(r.db_move_score_pct, 1, '%'), note: num(r.db_move_games) ? `${(+r.db_move_games).toLocaleString()} games` : 'not in book' },
    { label: 'Gap', value: gap === null ? '—' : (gap < 0 ? '−' : '+') + Math.abs(gap).toFixed(1) + '%', note: 'you vs book' },
    { label: 'Eval swing', value: num(r.eval_drop_pawns) ? '−' + fmt(r.eval_drop_pawns, 2) : '—', note: `${cpText(r.eval_before_cp)} → ${cpText(r.eval_after_cp)}` },
    { label: 'Points shed', value: fmt(r.lost_points, 1), note: `over ${r.your_games} games` },
    { label: 'Engine rank', value: r.engine_rank_of_your_move || '—', note: 'of your move' },
  ];
  $('detailStats').innerHTML = stats
    .map((s) => `<div class="stat"><div class="stat-label">${esc(s.label)}</div><div class="stat-value">${esc(s.value)}</div><div class="kpi-note">${esc(s.note)}</div></div>`)
    .join('');

  const alts = [
    { move: r.your_move, cp: r.eval_after_cp, db: r.db_move_score_pct, verdict: 'your move', mine: true },
    ...[1, 2, 3]
      .map((i) => ({
        move: r[`engine_best_${i}`],
        cp: r[`engine_best_${i}_cp`],
        db: r[`engine_best_${i}_db_score_pct`],
        verdict: i === 1 ? 'engine first choice' : `engine #${i}`,
      }))
      .filter((a) => a.move),
  ];
  $('altBody').innerHTML = alts
    .map(
      (a) => `<tr class="${a.mine ? 'is-yours' : ''}">
        <td>${esc(a.move)}</td>
        <td class="num">${cpText(a.cp)}</td>
        <td class="num book-val">${num(a.db) === null ? '—' : fmt(a.db, 1, '%')}</td>
        <td class="muted">${esc(a.verdict)}</td></tr>`
    )
    .join('');
  const games = (r.sample_games || '').split('; ').filter(Boolean);
  $('detailGames').innerHTML = games.length
    ? `Seen in ${games.length} of your games — ${games
        .slice(0, 3)
        .map((g, i) => (g.startsWith('http') ? `<a href="${esc(g)}" target="_blank" rel="noopener">game ${i + 1}</a>` : esc(g)))
        .join(', ')}`
    : '';
  renderTable();
}

/* -------------------------------------------------------------------- wiring */
function wire() {
  $('fileInput').addEventListener('change', (e) => {
    state.files = Array.from(e.target.files);
    renderFiles();
  });
  const dz = $('dropzone');
  dz.addEventListener('click', () => $('fileInput').click());
  dz.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') $('fileInput').click();
  });
  ['dragenter', 'dragover'].forEach((ev) =>
    dz.addEventListener(ev, (e) => {
      e.preventDefault();
      dz.classList.add('is-over');
    })
  );
  ['dragleave', 'drop'].forEach((ev) =>
    dz.addEventListener(ev, (e) => {
      e.preventDefault();
      dz.classList.remove('is-over');
    })
  );
  dz.addEventListener('drop', (e) => {
    state.files = Array.from(e.dataTransfer.files).filter((f) => f.name.toLowerCase().endsWith('.pgn'));
    renderFiles();
  });

  $('runBtn').addEventListener('click', () => startRun(false));
  $('runTop').addEventListener('click', () => (state.files.length ? startRun(false) : startRun(true)));
  $('sampleBtn').addEventListener('click', () => startRun(true));
  $('csvBtn').addEventListener('click', () => {
    if (state.csvText) {
      const url = URL.createObjectURL(new Blob([state.csvText], { type: 'text/csv' }));
      const a = document.createElement('a');
      a.href = url;
      a.download = 'opening_leaks.csv';
      a.click();
      URL.revokeObjectURL(url);
    } else if (state.jobId) {
      window.open(`${API}/api/report/${state.jobId}/csv`, '_blank');
    }
  });
  $('optDepth').addEventListener('input', (e) => ($('depthOut').textContent = e.target.value));
  $('optMoves').addEventListener('input', (e) => ($('movesOut').textContent = `${e.target.value} moves`));

  document.querySelectorAll('#flagFilter .seg').forEach((b) =>
    b.addEventListener('click', () => {
      document.querySelectorAll('#flagFilter .seg').forEach((x) => x.classList.remove('is-active'));
      b.classList.add('is-active');
      state.filter.flag = b.dataset.flag;
      renderTable();
    })
  );
  document.querySelectorAll('#colorFilter .seg').forEach((b) =>
    b.addEventListener('click', () => {
      document.querySelectorAll('#colorFilter .seg').forEach((x) => x.classList.remove('is-active'));
      b.classList.add('is-active');
      state.filter.color = b.dataset.color;
      renderTable();
    })
  );
  $('search').addEventListener('input', (e) => {
    state.filter.q = e.target.value;
    renderTable();
  });
  document.querySelectorAll('th.sortable').forEach((th) =>
    th.addEventListener('click', () => {
      const key = th.dataset.sort;
      state.sort = { key, dir: state.sort.key === key ? -state.sort.dir : -1 };
      document.querySelectorAll('th.sortable').forEach((x) => x.classList.remove('is-sorted', 'asc'));
      th.classList.add('is-sorted');
      if (state.sort.dir === 1) th.classList.add('asc');
      renderTable();
    })
  );
  $('copyFen').addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText($('fenText').textContent);
      $('copyFen').textContent = 'Copied';
      setTimeout(() => ($('copyFen').textContent = 'Copy FEN'), 1400);
    } catch {
      $('copyFen').textContent = 'Select the FEN above';
      setTimeout(() => ($('copyFen').textContent = 'Copy FEN'), 1800);
    }
  });
  const setDrawer = (open) => {
    $('sidebar').classList.toggle('is-open', open);
    $('scrim').hidden = !open;
  };
  $('menuBtn').addEventListener('click', () => setDrawer(!$('sidebar').classList.contains('is-open')));
  $('drawerClose').addEventListener('click', () => setDrawer(false));
  $('scrim').addEventListener('click', () => setDrawer(false));
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') setDrawer(false);
  });

  const links = Array.from(document.querySelectorAll('.nav-item'));
  links.forEach((a) =>
    a.addEventListener('click', () => {
      links.forEach((x) => x.classList.remove('is-active'));
      a.classList.add('is-active');
      setDrawer(false);
    })
  );
  const spy = new IntersectionObserver(
    (entries) => {
      entries.forEach((en) => {
        if (!en.isIntersecting) return;
        links.forEach((x) => x.classList.toggle('is-active', x.getAttribute('href') === `#${en.target.id}`));
      });
    },
    { root: $('main'), rootMargin: '-30% 0px -60% 0px' }
  );
  document.querySelectorAll('.section').forEach((s) => spy.observe(s));
}

wire();
loadMeta();
