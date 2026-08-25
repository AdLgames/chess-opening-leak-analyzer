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
  mode: 'username',
  provider: 'chesscom',
  profile: null,
  lookupSeq: 0,
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
  view: 'dashboard',
  marks: {},
  treeSide: 'white',
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
  if (limits.max_fetch_games) {
    const games = $('optMaxGames');
    games.max = String(limits.max_fetch_games);
    if (Number(games.value) > limits.max_fetch_games) games.value = String(limits.max_fetch_games);
    $('maxGamesOut').textContent = games.value;
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
    $('engineNotice').hidden = e.available !== false && d.available !== false;
    $('engineNotice').innerHTML =
      [e.available === false ? e.explain : null, d.available === false ? d.explain : null]
        .filter(Boolean).map(explainHtml).join('');
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

/* ------------------------------------------------------------- source panel */
const PROVIDERS = {
  chesscom: { label: 'Chess.com', placeholder: 'e.g. hikaru', hint: 'your Chess.com username' },
  lichess: { label: 'Lichess', placeholder: 'e.g. DrNykterstein', hint: 'your Lichess username' },
};
/* The last account used, held in memory for this page view. Browser storage is not
   available in the hosted preview iframe, so persistence waits for user accounts. */
let lastAccount = null;

function remember(value) {
  lastAccount = value;
}
function recall() {
  return lastAccount;
}

function setMode(mode) {
  state.mode = mode;
  const panels = { username: 'panelAccount', upload: 'panelUpload', sample: 'panelDemo' };
  const tabs = { username: 'tabAccount', upload: 'tabUpload', sample: 'tabDemo' };
  Object.entries(panels).forEach(([key, id]) => ($(id).hidden = key !== mode));
  Object.entries(tabs).forEach(([key, id]) => {
    $(id).classList.toggle('is-active', key === mode);
    $(id).setAttribute('aria-selected', key === mode ? 'true' : 'false');
  });
}

function setProvider(provider) {
  state.provider = provider;
  const conf = PROVIDERS[provider];
  document.querySelectorAll('#providerSeg .seg-btn').forEach((b) => {
    const on = b.dataset.provider === provider;
    b.classList.toggle('is-active', on);
    b.setAttribute('aria-checked', on ? 'true' : 'false');
  });
  $('optUser').placeholder = conf.placeholder;
  $('userHint').textContent = conf.hint;
  $('tokenField').hidden = provider !== 'lichess';
  clearProfile();
}

function clearProfile() {
  state.profile = null;
  $('profileCard').hidden = true;
  $('profileCard').innerHTML = '';
  $('fetchNotice').hidden = true;
  updateRunLabel();
}

function updateRunLabel() {
  const name = $('optUser').value.trim();
  $('runBtn').textContent = name ? `Analyse ${name}'s games` : 'Analyse my games';
}

function showFetchProblem(message, hint, downloadUrl) {
  $('fetchNoticeTitle').textContent = message;
  $('fetchNoticeText').textContent = hint || '';
  const link = $('fetchNoticeLink');
  link.hidden = !downloadUrl;
  if (downloadUrl) link.href = downloadUrl;
  $('fetchNotice').hidden = false;
}

const speedList = () =>
  Array.from(document.querySelectorAll('#speedChips input:checked')).map((c) => c.value);

async function checkAccount({ quiet = false } = {}) {
  const username = $('optUser').value.trim();
  if (!username) return null;
  const seq = ++state.lookupSeq;
  $('checkBtn').disabled = true;
  $('checkBtn').textContent = 'Checking…';
  try {
    const res = await fetch(
      `${API}/api/lookup?provider=${encodeURIComponent(state.provider)}&username=${encodeURIComponent(username)}`,
    );
    const body = await res.json();
    if (seq !== state.lookupSeq) return null;          // a newer lookup already ran
    if (!body.found) {
      state.profile = null;
      $('profileCard').hidden = true;
      if (!quiet) showFetchProblem(body.error || 'Account not found', body.hint || '', '');
      return null;
    }
    renderProfile(body.profile);
    remember({ provider: state.provider, username: body.profile.username });
    return body.profile;
  } catch (err) {
    if (!quiet) showFetchProblem('Could not reach the lookup service', err.message, '');
    return null;
  } finally {
    $('checkBtn').disabled = false;
    $('checkBtn').textContent = 'Check';
  }
}

function renderProfile(profile) {
  state.profile = profile;
  $('fetchNotice').hidden = true;
  const ratings = Object.entries(profile.ratings || {})
    .map(([k, v]) => `<span class="rating"><i>${esc(k)}</i><b class="mono">${v}</b></span>`)
    .join('');
  const initial = (profile.username || '?').slice(0, 1).toUpperCase();
  const avatar = profile.avatar
    ? `<img src="${esc(profile.avatar)}" alt="" width="40" height="40" />`
    : `<span class="avatar-fallback">${esc(initial)}</span>`;
  $('profileCard').innerHTML = `
    <div class="profile-id">
      ${avatar}
      <span>
        <b>${profile.title ? `<i class="title">${esc(profile.title)}</i> ` : ''}${esc(profile.username)}</b>
        <em>${esc(profile.name || PROVIDERS[profile.provider].label)}${profile.country ? ' · ' + esc(profile.country) : ''}</em>
      </span>
    </div>
    <div class="ratings">${ratings || '<span class="muted small">no rated games yet</span>'}</div>
    <a class="link" href="${esc(profile.url)}" target="_blank" rel="noopener">Profile</a>`;
  $('profileCard').hidden = false;
  updateRunLabel();
}

/* ---------------------------------------------------------------- run panel */
function renderFiles() {
  const list = $('fileList');
  list.hidden = state.files.length === 0;
  list.innerHTML = state.files
    .map((f) => `<li><span>${esc(f.name)}</span><span>${(f.size / 1024).toFixed(0)} KB</span></li>`)
    .join('');
  $('runUploadBtn').textContent = state.files.length
    ? `Analyse ${state.files.length} file${state.files.length > 1 ? 's' : ''}`
    : 'Analyse my games';
}

function collectOptions(mode) {
  const fd = new FormData();
  fd.append('source', mode);
  fd.append('use_sample', mode === 'sample' ? 'true' : 'false');
  fd.append('player', $('optPlayer').value.trim());
  fd.append('color', $('optColor').value);
  fd.append('depth', $('optDepth').value);
  fd.append('max_moves', $('optMoves').value);
  fd.append('min_games', $('optMinGames').value);
  fd.append('eval_drop', $('optEvalDrop').value);
  fd.append('score_gap', $('optScoreGap').value);
  fd.append('min_db_games', $('optMinDb').value);
  fd.append('no_engine', $('optNoEngine').checked ? 'true' : 'false');
  if (mode === 'upload') state.files.forEach((f) => fd.append('files', f, f.name));
  if (mode === 'username') {
    fd.append('username', $('optUser').value.trim());
    fd.append('provider', state.provider);
    fd.append('max_games', $('optMaxGames').value);
    fd.append('time_classes', speedList().join(','));
    fd.append('include_unrated', $('optRated').checked ? 'false' : 'true');
    fd.append('since', $('optSince').value);
    fd.append('until', $('optUntil').value);
    fd.append('refresh', $('optRefresh').checked ? 'true' : 'false');
    if (state.provider === 'lichess') fd.append('lichess_token', $('optToken').value.trim());
  }
  return fd;
}

async function startRun(mode) {
  if (mode === 'upload' && !state.files.length) {
    $('dropzone').classList.add('is-over');
    setTimeout(() => $('dropzone').classList.remove('is-over'), 700);
    return;
  }
  if (mode === 'username') {
    const username = $('optUser').value.trim();
    if (!username) {
      $('optUser').focus();
      showFetchProblem('Enter a username first', `Whose games should I read from ${PROVIDERS[state.provider].label}?`, '');
      return;
    }
    if (!speedList().length) {
      showFetchProblem('Pick at least one time control', 'Blitz and rapid are the usual choice.', '');
      return;
    }
    $('fetchNotice').hidden = true;
  }
  setBusy(true);
  showKpiSkeleton();
  $('progressCard').hidden = false;
  $('spinner').className = 'spinner';
  $('progressTitle').textContent = {
    sample: 'Analysing demo archive',
    upload: 'Analysing your files',
    username: `Fetching ${$('optUser').value.trim() || 'your'} games`,
  }[mode];
  $('log').textContent = 'Queued…';
  $('barFill').style.width = '8%';
  $('barFill').classList.remove('is-error');
  $('headerSub').textContent = 'Run in progress — engine and book lookups are local.';

  try {
    if (state.serverless) return await runSynchronous(mode);
    const res = await fetch(`${API}/api/analyze`, { method: 'POST', body: collectOptions(mode) });
    if (!res.ok) throw new Error((await res.json()).detail || `HTTP ${res.status}`);
    state.jobId = (await res.json()).job_id;
    poll();
  } catch (err) {
    failRun(err.message);
  }
}

/* Hosted deployment: one request returns the finished report, so there is no job
   to poll. Animate the bar while the function works. */
async function runSynchronous(mode) {
  const started = Date.now();
  $('log').textContent = 'Running in the hosted function — engine and book are bundled with it.';
  const tick = setInterval(() => {
    const secs = (Date.now() - started) / 1000;
    $('progressElapsed').textContent = `${secs.toFixed(1)}s`;
    $('barFill').style.width = `${Math.min(90, 8 + secs * 3)}%`;
  }, 200);
  try {
    const res = await fetch(`${API}/api/analyze`, { method: 'POST', body: collectOptions(mode) });
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
    applyReport(body, { options: body.options, source: body.source || mode, account: body.account });
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
    if (job.status === 'error') {
      if (job.hint || job.download_url) showFetchProblem(job.error || 'Run failed', job.hint || '', job.download_url || '');
      return failRun([job.error, job.hint].filter(Boolean).join('\n'));
    }
    if (job.account && job.fetched) {
      $('progressTitle').textContent = `Analysing ${job.fetched.games} games for ${job.account.username}`;
    }
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
  ['runBtn', 'runUploadBtn', 'sampleBtn', 'runTop', 'checkBtn'].forEach((id) => ($(id).disabled = busy));
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
  const sourceLabel = job.source === 'sample'
    ? 'Demo archive'
    : job.source === 'username'
      ? `${(job.account && PROVIDERS[job.account.provider].label) || 'Fetched'} · ${(job.account && job.account.username) || state.player}`
      : 'Your upload';
  $('overviewHint').textContent = `${sourceLabel} · ${s.games} games`;
  $('footStatus').textContent = state.serverless
    ? `hosted run · ${s.leaks} leaks`
    : `job ${state.jobId} · ${s.leaks} leaks`;
  renderFixList(s);
  renderTree(s);
  renderCoverage(s);
  renderKpis(s);
  renderBaselineNote(s);
  renderCharts(s);
  renderTable();
  if (window.Study) window.Study.setRows(state.rows);
  const first = sortedRows()[0];
  if (first) selectRow(first);
  renderProgress();
  // A finished run should land on its findings rather than on the form that started it.
  if (state.view === 'dashboard' && (data.rows || []).length) showView('fixes');
}

/* The answer to "what do I do next", above the table rather than below it. The server has
   already collapsed each line down to the move that starts it, so three rows about one bad
   line show up here as one thing to fix. */
function renderFixList(s) {
  const groups = (s.groups || []).slice(0, 3);
  $('fixes').hidden = groups.length === 0;
  if (!groups.length) return;
  $('fixesHint').textContent =
    s.groups.length > 3
      ? `The 3 biggest of ${s.groups.length} — worst first`
      : 'Your most expensive habits, worst first';

  $('fixList').innerHTML = groups
    .map((g, i) => {
      const r = g.headline;
      const followers = g.followers
        ? `<span class="fix-follow">and ${g.followers} later ${g.followers === 1 ? 'mistake' : 'mistakes'} in the same line</span>`
        : '';
      return `<article class="fix-card" data-i="${i}">
        <div class="fix-rank">${i + 1}</div>
        <div class="fix-main">
          <h3>${esc(g.opening)} <span class="mono muted">${r.move_number}${r.player_color === 'white' ? '.' : '...'}${esc(r.your_move)}</span></h3>
          <p class="fix-why">${esc(g.explanation || '')}</p>
          ${followers}
        </div>
        <div class="fix-cost" title="What this line has cost you in total, and what it costs each time you play it">
          <b>${fmt(g.lost_points, 1)}</b>
          <span>points</span>
          <em>${g.games} games · ${fmt(g.cost_per_game, 2)} each</em>
        </div>
        <button class="btn btn-primary fix-go" data-i="${i}">Show me</button>
      </article>`;
    })
    .join('');

  $('fixList').querySelectorAll('.fix-go').forEach((btn) =>
    btn.addEventListener('click', () => {
      const g = groups[+btn.dataset.i];
      // The table may be filtered, so match on the row's own identity, not its index.
      const target = state.rows.find(
        (r) => r.fen === g.headline.fen && r.your_move === g.headline.your_move,
      );
      if (target) selectRow(target);
      $('position').scrollIntoView({ behavior: 'smooth' });
    }),
  );
}

/* The repertoire drawn as an indented tree. Deliberately a list rather than a graph: it
   stays readable on a phone, it is navigable by keyboard for free, and the shape of the
   trunk is what matters rather than the geometry. */
const TREE_STATUS = {
  strong: { cls: 'is-strong', why: 'Good results here.' },
  weak: { cls: 'is-weak', why: 'This move is flagged in your report.' },
  committed: { cls: 'is-committed', why: 'You have committed to this move.' },
  played: { cls: 'is-played', why: 'Played, with nothing to report either way.' },
};

function treeBranch(items, depth = 0) {
  if (!items.length) return '';
  return `<ul class="tree-level"${depth === 0 ? '' : ' role="group"'}>` + items.map((n) => {
    const meta = TREE_STATUS[n.status] || TREE_STATUS.played;
    const score = n.score_pct === null || n.score_pct === undefined
      ? ''
      : `<span class="tree-score">${Math.round(n.score_pct)}%</span>`;
    const games = n.games ? `<span class="tree-games">${n.games}</span>` : '';
    const gaps = n.gaps
      ? `<span class="tree-gaps" title="Likely replies from here you have barely faced">+${n.gaps} unmet</span>`
      : '';
    const cls = n.ours ? `tree-move is-ours ${meta.cls}` : 'tree-move';
    return `<li>
      <span class="${cls}" title="${esc(n.ours ? meta.why : "Your opponent's move")}" data-fen="${esc(n.fen || '')}">
        <b class="mono">${esc(n.san)}</b>${games}${score}${gaps}
      </span>
      ${treeBranch(n.children || [], depth + 1)}
    </li>`;
  }).join('') + '</ul>';
}

function renderTree(s) {
  const tree = s.tree || {};
  const sides = Object.keys(tree).filter((k) => (tree[k] || []).length);
  $('repertoire').hidden = sides.length === 0;
  if (!sides.length) return;

  // Only offer a side the player actually has games for.
  document.querySelectorAll('#repSide .seg').forEach((b) => {
    b.hidden = !sides.includes(b.dataset.side);
  });
  if (!sides.includes(state.treeSide)) state.treeSide = sides[0];
  document.querySelectorAll('#repSide .seg').forEach((b) =>
    b.classList.toggle('is-active', b.dataset.side === state.treeSide),
  );

  const totals = (s.tree_totals || {})[state.treeSide] || {};
  $('repHint').textContent =
    `${totals.strong || 0} doing well · ${totals.weak || 0} needing work · ` +
    `${totals.committed || 0} yours by choice · ${totals.gaps || 0} unmet replies`;
  $('repTree').innerHTML = treeBranch(tree[state.treeSide] || []);

  $('repTree').querySelectorAll('.tree-move.is-ours').forEach((el) =>
    el.addEventListener('click', () => {
      const row = state.rows.find((r) => r.fen === el.dataset.fen);
      if (row) {
        selectRow(row);
        $('position').scrollIntoView({ behavior: 'smooth' });
      }
    }),
  );
}

/* The lines the report cannot otherwise see: replies the player's own openings lead to,
   which they have barely met. Ranked by how often a real opponent reaches them. */
function renderCoverage(s) {
  const gaps = (s.coverage || []).filter((g) => g.decision !== 'ignored');
  $('coverage').hidden = gaps.length === 0;
  if (!gaps.length) return;
  const total = s.coverage_total || gaps.length;
  $('coverageHint').textContent =
    total > gaps.length
      ? `The ${gaps.length} most likely of ${total}`
      : `${gaps.length} to prepare`;

  $('gapList').innerHTML = gaps.map(gapCard).join('');
}

/* Three things you can do about a reply you have never met, rather than one link out to
   somebody else's site. "Ignore" is the one that makes the section trustworthy: a list
   that only ever grows is a list people stop opening. */
const GAP_STAGE = {
  learning: { label: 'Learning', cls: 'is-learning' },
  practising: { label: 'In your drills', cls: 'is-practising' },
};

function gapCard(g) {
  const faced =
    g.times_faced === 0
      ? '<span class="gap-never">never faced</span>'
      : `<span class="gap-rare">faced ${g.times_faced}×</span>`;
  const stage = GAP_STAGE[g.decision];
  const answer = g.answer_san
    ? `<span class="gap-answer">Book answer <b>${esc(g.answer_san)}</b>
         <span class="muted">${fmt(g.answer_score_pct, 0, '%')} over ${g.answer_games} games</span></span>`
    : '<span class="gap-answer muted">The book is too thin here to name an answer.</span>';
  const epd = (g.fen || '').split(' ').slice(0, 4).join(' ');
  const attrs = `data-epd="${esc(epd)}" data-color="${esc(g.player_color)}" data-fen="${esc(g.fen || '')}"`;
  return `<article class="gap-card${stage ? ' ' + stage.cls : ''}" ${attrs}>
    <div class="gap-reach" title="How often your games should reach this position">
      <b>${fmt(g.reach_pct, 0, '%')}</b><span>of games</span>
    </div>
    <div class="gap-main">
      <h3 class="mono">${esc(g.line)}</h3>
      <p>${esc(g.opening || 'Unnamed line')} · as ${esc(g.player_color)} ${faced}</p>
      ${answer}
    </div>
    <div class="gap-actions">
      ${stage ? `<span class="gap-stage">${esc(stage.label)}</span>` : ''}
      <button class="btn btn-ghost gap-do" data-do="learn">Learn</button>
      <button class="btn btn-ghost gap-do" data-do="practise"
        ${g.answer_uci ? '' : 'disabled title="No book answer to grade against"'}>Practise</button>
      <button class="btn btn-ghost gap-do" data-do="ignore">Ignore</button>
    </div>
  </article>`;
}

/* One listener on the list rather than one per button: the list is re-rendered on every
   decision, and per-card listeners would be re-attached each time. */
function wireGaps() {
  $('gapList').addEventListener('click', async (e) => {
    const btn = e.target.closest('.gap-do');
    if (!btn) return;
    const card = btn.closest('.gap-card');
    const row = (state.summary.coverage || []).find(
      (g) => (g.fen || '').split(' ').slice(0, 4).join(' ') === card.dataset.epd &&
        g.player_color === card.dataset.color,
    );
    if (!row) return;

    if (btn.dataset.do === 'learn') {
      // Show it on the board that is already here, with the local book and engine behind
      // it, rather than handing the position to another site.
      row.decision = 'learning';
      await saveGapDecision(row, 'learning');
      if (window.Study) window.Study.study(row);
      showView('repertoire');
      return;
    }
    if (btn.dataset.do === 'practise') {
      row.decision = 'practising';
      await saveGapDecision(row, 'practising');
      renderCoverage(state.summary);
      if (window.Study) window.Study.refreshDrills();
      return;
    }
    row.decision = 'ignored';
    await saveGapDecision(row, 'ignored');
    renderCoverage(state.summary);
  });
}

async function saveGapDecision(row, decision) {
  try {
    await fetch(`${API}/api/gaps`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        epd: (row.fen || '').split(' ').slice(0, 4).join(' '),
        color: row.player_color,
        decision,
        reply: row.reply || '',
        line: row.line || '',
        opening: row.opening || '',
        answer_uci: row.answer_uci || '',
        answer_san: row.answer_san || '',
      }),
    });
  } catch {
    // Local-first: the decision still applies to what is on screen. Worth saying so
    // rather than letting the button look like it worked and then forget by morning.
    $('coverageHint').textContent = 'Applied here, but not saved — the local API did not answer.';
  }
}

/* What the player has decided about their own openings. A tool that keeps arguing with a
   deliberate choice is one people stop believing, so these decisions are read back on load
   and sent to the server the moment they are made. */
const markKey = (row) => `${(row.fen || '').split(' ').slice(0, 4).join(' ')}|${row.player_color}`;

async function loadMarks() {
  try {
    const { marks } = await (await fetch(`${API}/api/repertoire`)).json();
    state.marks = {};
    (marks || []).forEach((m) => {
      state.marks[`${m.epd}|${m.color}`] = m;
    });
  } catch {
    state.marks = {}; // no decisions is a perfectly good state
  }
}

/* A decision only applies to the move it was made about — if the player has since
   switched, the old decision is not theirs to hide behind. */
function currentMark(row) {
  if (!row) return null;
  const mark = state.marks[markKey(row)];
  return mark && mark.uci === row.your_move_uci ? mark : null;
}

function renderDecision(row) {
  const mark = currentMark(row);
  const label = $('decideState');
  const clear = $('clearDecision');
  if (!mark) {
    label.textContent = '';
    label.className = 'decide-state';
    clear.hidden = true;
    return;
  }
  label.textContent =
    mark.decision === 'committed'
      ? `${mark.san || 'This move'} is yours — only position problems will be reported`
      : 'Hidden from future reports';
  label.className = 'decide-state' + (mark.decision === 'ignored' ? ' is-ignored' : '');
  clear.hidden = false;
}

async function decide(decision) {
  const row = state.selected;
  if (!row) return;
  const epd = (row.fen || '').split(' ').slice(0, 4).join(' ');
  try {
    await fetch(`${API}/api/repertoire`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        epd,
        color: row.player_color,
        uci: row.your_move_uci || '',
        san: row.your_move || '',
        decision,
      }),
    });
    await loadMarks();
    renderDecision(row);
  } catch (err) {
    $('decideState').textContent = `Could not save that: ${err.message}`;
  }
}

/* Progress is the long view: not this session's score, but whether the fixes are bedding
   in. The review schedule already knows; this only asks it. */
async function renderProgress() {
  let progress = null;
  try {
    ({ progress } = await (await fetch(`${API}/api/drills`)).json());
  } catch {
    progress = null;
  }
  renderComparison();
  const has = progress && progress.tracked > 0;
  $('progress').hidden = false;
  $('progressEmpty').hidden = !!has;
  $('progressKpis').innerHTML = '';
  if (!has) {
    $('progressHint').textContent = 'Nothing tracked yet';
    return;
  }

  $('progressHint').textContent =
    progress.due ? `${progress.due} ready to review now` : 'Nothing due right now — come back tomorrow';
  const cards = [
    { label: 'Known', value: progress.known, cls: 'good', note: 'recalled repeatedly, weeks apart' },
    { label: 'Still learning', value: progress.learning, note: 'not yet reliable' },
    { label: 'Due now', value: progress.due, cls: 'accent', note: 'ready to be seen again' },
    { label: 'Attempts', value: progress.attempts, note: 'across every session' },
    {
      label: 'Recalled correctly',
      value: progress.accuracy_pct === null ? '—' : `${progress.accuracy_pct}%`,
      note: 'first-time and repeat attempts together',
    },
  ];
  $('progressKpis').innerHTML = cards
    .map((c) => `<div class="kpi ${c.cls || ''}">
      <div class="kpi-label">${esc(c.label)}</div>
      <div class="kpi-value">${esc(c.value)}</div>
      <div class="kpi-note">${esc(c.note)}</div></div>`)
    .join('');
}

/* Two runs answer the question one cannot: did last month's work do anything. The server
   decides what counts as changed; this only says it. */
function changeList(el, items, emptyNote) {
  el.innerHTML = items.length
    ? items.slice(0, 8).map((r) => `<li>
        <span class="ch-move">${esc(r.san || '?')}</span>
        <span class="ch-open">${esc(r.opening || 'Unnamed line')}</span>
        <span class="ch-cost">${fmt(r.lost_points, 1)}</span>
      </li>`).join('')
    : `<li class="empty-note">${esc(emptyNote)}</li>`;
}

async function renderComparison() {
  let comparison = null;
  try {
    ({ comparison } = await (await fetch(`${API}/api/history`)).json());
  } catch {
    comparison = null;
  }
  $('compareNotice').hidden = !comparison;
  $('changeGrid').hidden = !comparison;
  if (!comparison) return;

  $('compareHeadline').textContent = comparison.headline;
  $('compareDetail').textContent = comparison.comparable
    ? `Comparing ${comparison.current.games} games with the ${comparison.previous.games} ` +
      `you ran on ${comparison.previous.created_at}.`
    : '';
  changeList($('changeFixed'), comparison.fixed, 'Nothing cleared yet — keep at the drills.');
  changeList($('changeNew'), comparison.new, 'No new leaks. Good.');
}

function showKpiSkeleton() {
  $('kpis').innerHTML = Array.from({ length: 6 })
    .map(() => '<div class="kpi kpi-skeleton"><div class="kpi-label">loading</div><div class="kpi-value">0.0</div><div class="kpi-note">loading</div></div>')
    .join('');
}

/* Who the numbers compare you against. "The book scores 54%" means nothing until the
   reader knows whose book — a 1400 measured against a pool set largely by players two
   classes above them is being told something untrue about their own openings. */
function renderBaselineNote(s) {
  const el = $('baselineNote');
  if (!el) return;
  if (s.book_has_bands && s.player_rating) {
    el.textContent = `Compared against players rated ${esc(s.player_band_label)}, ` +
      `since your games put you around ${Math.round(s.player_rating)}.`;
    el.hidden = false;
    return;
  }
  if (s.player_rating) {
    el.textContent = 'Compared against every rating together — this opening book has no ' +
      'rating bands. Rebuilding it compares you with players at your own strength.';
    el.hidden = false;
    return;
  }
  el.hidden = true;
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


/* A failure, said for the person in front of it. The command the maintainer wants is kept
   in the details, because the sentence that helps one of them is not the sentence that
   helps the other — and hiding the technical text entirely just means a worse bug report. */
function explainHtml(x) {
  if (!x) return '';
  return `<div class="explain-fail">
    <b>${esc(x.headline)}</b>
    <span>${esc(x.detail)}</span>
    ${x.technical ? `<details><summary>What the program reported</summary>
      <code>${esc(x.technical)}</code></details>` : ''}
  </div>`;
}

/* ------------------------------------------------------------------- charts */
function renderCharts(s) {
  if (window.LeakCharts) window.LeakCharts.render(s.by_opening);
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

/* Four kinds of problem, because they call for four different responses: learn the right
   move, reconsider the line, prepare for something unmet, or simply play more games. The
   server decides which; this is only how it looks. */
const CATEGORIES = {
  objective: { label: 'Loses ground', cls: 'cat-objective', why: 'The move itself is the problem: it hands over material or the advantage.' },
  practical: { label: 'Not working for you', cls: 'cat-practical', why: 'Playable, but your results with it are well below what the position is worth.' },
  knowledge: { label: 'Unfamiliar', cls: 'cat-knowledge', why: 'A position you will meet but have barely played.' },
  unproven: { label: 'Worth watching', cls: 'cat-unproven', why: 'Too few games so far to be sure this is real.' },
};

function categoryChip(row) {
  const meta = CATEGORIES[row.category] || CATEGORIES.unproven;
  const label = row.category_label || meta.label;
  return `<span class="chip ${meta.cls}" title="${esc(meta.why)}">${esc(label)}</span>`;
}

function renderTable() {
  const rows = sortedRows();
  $('tableEmpty').hidden = rows.length > 0;
  $('leakBody').innerHTML = rows
    .map((r, i) => {
      const book = num(r.baseline_pct);
      const gap = num(r.score_gap_vs_db_pct);
      const drop = num(r.eval_drop_pawns);
      const you = num(r.your_score_pct);
      return `<tr data-i="${i}" class="${state.selected && state.selected.fen === r.fen && state.selected.your_move === r.your_move ? 'is-selected' : ''}">
        <td class="num">${fmt(r.priority, 1)}</td>
        <td>${categoryChip(r)}</td>
        <td class="opening-cell"><span class="truncate" title="${esc(r.opening)}">${esc(r.opening || r.eco || '—')}</span></td>
        <td class="line-cell"><span class="truncate" title="${esc(r.variation_line)}">${esc(r.variation_line)}</span></td>
        <td class="move-cell">${r.move_number}${r.player_color === 'white' ? '.' : '…'} ${esc(r.your_move)}</td>
        <td class="num">${esc(r.your_games)}</td>
        <td class="num ${gap !== null && gap < 0 ? 'delta-bad' : ''}" title="${r.your_wins}W ${r.your_draws}D ${r.your_losses}L${r.confidence === 'low' ? ' — few games, treat with caution' : ''}">${you === null ? '—' : Math.round(you) + '%'}${r.confidence === 'low' ? ' <span class="confidence is-low">?</span>' : ''}</td>
        <td class="num book-val" title="${esc(r.baseline_source === 'move' ? 'this move in the book' : 'position average — too few book games with this move')}">${book === null ? '—' : Math.round(book) + '%'}</td>
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
/* Kept for the no-JS-module fallback path: study.js owns the interactive board. */
function renderBoardStatic(fen) {
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
  $('detailFlag').outerHTML = categoryChip(r).replace('<span class="chip', '<span id="detailFlag" class="chip');
  $('detailOpening').textContent = r.opening || r.eco || 'Unclassified';
  $('detailLine').textContent = r.variation_line;
  // The server writes one plain sentence per finding, so the CLI, the API and both
  // dashboards say the same thing in the same words.
  $('detailExplain').textContent = r.explanation || '';
  $('fenText').textContent = r.fen;
  $('lichessLink').href = `https://lichess.org/analysis/standard/${encodeURIComponent(r.fen.replace(/ /g, '_'))}`;
  renderDecision(r);
  if (window.Study) window.Study.review(r);
  else renderBoardStatic(r.fen);

  const gap = num(r.score_gap_vs_db_pct);
  // A score over a handful of games does not deserve a decimal place, and no percentage
  // is shown without the sample size that produced it.
  const whole = (v, suffix = '%') => (num(v) === null ? '—' : Math.round(num(v)) + suffix);
  const baselineNote = r.baseline_source === 'move'
    ? `${(+r.baseline_games || 0).toLocaleString()} games with this move`
    : num(r.baseline_games)
      ? `position average · ${(+r.baseline_games).toLocaleString()} games`
      : 'not in book';
  const stats = [
    { label: 'Your score', value: whole(r.your_score_pct), note: `${r.your_wins}W ${r.your_draws}D ${r.your_losses}L over ${r.your_games}` },
    { label: 'Compared to', value: whole(r.baseline_pct), note: baselineNote },
    { label: 'Gap', value: gap === null ? '—' : (gap < 0 ? '−' : '+') + Math.abs(gap).toFixed(1) + '%', note: 'you vs book' },
    { label: 'Eval swing', value: num(r.eval_drop_pawns) ? '−' + fmt(r.eval_drop_pawns, 2) : '—', note: `${cpText(r.eval_before_cp)} → ${cpText(r.eval_after_cp)}` },
    { label: 'Points shed', value: fmt(r.lost_points, 1), note: `at least ${fmt(r.lost_points_conservative, 1)} on the cautious reading` },
    { label: 'Confidence', value: (r.confidence || '—'), note: r.confidence === 'low' ? 'few games — a hint, not a verdict' : 'from sample sizes on both sides' },
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
function bootAccount() {
  const saved = recall();
  setProvider(saved && PROVIDERS[saved.provider] ? saved.provider : 'chesscom');
  setMode('username');
  if (saved && saved.username) {
    $('optUser').value = saved.username;
    updateRunLabel();
    checkAccount({ quiet: true });
  }
}

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

  $('runBtn').addEventListener('click', () => startRun('username'));
  $('runUploadBtn').addEventListener('click', () => startRun('upload'));
  $('sampleBtn').addEventListener('click', () => startRun('sample'));
  $('runTop').addEventListener('click', () => startRun(state.mode));

  // source tabs
  $('tabAccount').addEventListener('click', () => setMode('username'));
  $('tabUpload').addEventListener('click', () => setMode('upload'));
  $('tabDemo').addEventListener('click', () => setMode('sample'));

  // account panel
  document.querySelectorAll('#providerSeg .seg-btn').forEach((b) =>
    b.addEventListener('click', () => setProvider(b.dataset.provider))
  );
  let lookupTimer = null;
  $('optUser').addEventListener('input', () => {
    clearProfile();
    clearTimeout(lookupTimer);
    const value = $('optUser').value.trim();
    updateRunLabel();
    if (value.length >= 3) lookupTimer = setTimeout(() => checkAccount({ quiet: true }), 700);
  });
  $('optUser').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      startRun('username');
    }
  });
  $('checkBtn').addEventListener('click', () => checkAccount());
  $('optMaxGames').addEventListener('input', (e) => ($('maxGamesOut').textContent = e.target.value));
  $('optSince').max = new Date().toISOString().slice(0, 10);
  $('optUntil').max = $('optSince').max;
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
  document.querySelectorAll('#repSide .seg').forEach((b) =>
    b.addEventListener('click', () => {
      state.treeSide = b.dataset.side;
      renderTree(state.summary || {});
    }),
  );
  $('commitMove').addEventListener('click', () => decide('committed'));
  $('ignoreFinding').addEventListener('click', () => decide('ignored'));
  $('clearDecision').addEventListener('click', () => decide('clear'));
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
  $('menuBtn').addEventListener('click', () => setDrawer(!$('sidebar').classList.contains('is-open')));
  $('drawerClose').addEventListener('click', () => setDrawer(false));
  $('scrim').addEventListener('click', () => setDrawer(false));
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') setDrawer(false);
  });

  wireViews();
  wireGaps();

  const sheet = $('privacySheet');
  $('privacyBtn').addEventListener('click', () => sheet.showModal());
  $('privacyClose').addEventListener('click', () => sheet.close());
  // Clicking the backdrop closes it: the dialog element reports clicks outside the content
  // box as landing on the dialog itself.
  sheet.addEventListener('click', (e) => {
    if (e.target === sheet) sheet.close();
  });
}

const setDrawer = (open) => {
  $('sidebar').classList.toggle('is-open', open);
  $('scrim').hidden = !open;
};

/* Five destinations rather than eleven pipeline stages. The sections themselves are
   unchanged; each view simply shows the ones that belong to the question being asked, so
   nobody scrolls past a chart to reach the thing they came for. */
const VIEWS = {
  dashboard: ['run', 'overview', 'charts'],
  repertoire: ['repertoire', 'coverage', 'library'],
  fixes: ['fixes', 'leaks', 'position'],
  practice: ['practice'],
  progress: ['progress', 'provenance'],
};

function showView(name) {
  const wanted = VIEWS[name] || VIEWS.dashboard;
  state.view = name;
  document.querySelectorAll('.section').forEach((section) => {
    // A section that has hidden itself for lack of data stays hidden; the view only
    // decides which are eligible.
    section.dataset.inView = wanted.includes(section.id) ? 'yes' : 'no';
  });
  document.querySelectorAll('.nav-item').forEach((a) =>
    a.classList.toggle('is-active', a.dataset.view === name),
  );
  $('main').scrollTop = 0;
  // The numbers move every time a drill is answered, so read them on arrival rather than
  // trusting whatever they were when the page loaded.
  if (name === 'progress') renderProgress();
}

function wireViews() {
  document.querySelectorAll('.nav-item').forEach((a) =>
    a.addEventListener('click', (e) => {
      e.preventDefault();
      showView(a.dataset.view);
      setDrawer(false);
    }),
  );
  showView('dashboard');
}

wire();
if (window.Study) window.Study.init(API);
bootAccount();
loadMeta();
loadMarks();
renderProgress();
