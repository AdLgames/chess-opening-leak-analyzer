/* Opening Leak Lab — dashboard client.

   The page has three states: `empty` asks for games and nothing else, `running`
   collapses that to one line plus progress, and `report` is the finished thing.
   Only one is ever in the document, which is what keeps the first screen to a
   single decision.

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
const V = window.Vocab;
const S = window.Store;

/* How many rows the table shows before "Show all". A 2,000-game archive should
   not open with 400 rows. */
const ROW_CAP = 25;

const VIEWS = {
  report: { title: 'Report', needsRun: false },
  repertoire: { title: 'Repertoire', needsRun: true },
  practice: { title: 'Practice', needsRun: true },
  progress: { title: 'Progress', needsRun: true },
  explorer: { title: 'Explorer', needsRun: false },
};

const state = {
  view: 'report',
  app: 'empty',
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
  source: '',
  account: null,
  options: null,
  demo: false,
  sort: { dir: -1 },
  filter: { flag: 'all', q: '' },
  showAll: false,
  selected: null,
  chart: null,
  chartKind: 'lost',
  meta: null,
};

const num = (v) => {
  const n = parseFloat(v);
  return Number.isFinite(n) ? n : null;
};
const fmt = (v, digits = 1, suffix = '') => (num(v) === null ? '—' : num(v).toFixed(digits) + suffix);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`;

/* ------------------------------------------------------------------- states */
function setAppState(next) {
  state.app = next;
  $('app').dataset.state = next;
  $('gate').hidden = next !== 'empty';
  $('runStrip').hidden = next !== 'running';
  $('report').hidden = next !== 'report';
  $('headerActions').hidden = next !== 'report';
  mountRunForm(next === 'empty' ? 'gateSlot' : 'dialogSlot');
  renderNav();
  renderViewHead();
}

/* The form has one instance; it moves between the empty screen and the dialog so
   no control is ever rendered twice. */
function mountRunForm(slotId) {
  const form = $('runForm');
  const slot = $(slotId);
  if (form && slot && form.parentNode !== slot) slot.appendChild(form);
}

function hasReport() {
  return state.rows.length > 0 || state.summary !== null;
}

function renderNav() {
  const unlocked = hasReport() || S.repertoire.all().length > 0;
  document.querySelectorAll('.nav-item').forEach((a) => {
    const view = a.dataset.view;
    a.hidden = VIEWS[view].needsRun && !unlocked;
    a.classList.toggle('is-active', view === state.view);
  });
}

function go(view) {
  if (!VIEWS[view]) view = 'report';
  if (VIEWS[view].needsRun && !hasReport() && !S.repertoire.all().length) view = 'report';
  state.view = view;
  Object.keys(VIEWS).forEach((name) => {
    $(`view${name[0].toUpperCase()}${name.slice(1)}`).hidden = name !== view;
  });
  if (location.hash !== `#${view}`) history.replaceState(null, '', `#${view}`);
  renderNav();
  renderViewHead();
  if (view === 'repertoire') window.Repertoire.renderRepertoire(reportContext());
  if (view === 'progress') window.Repertoire.renderProgress(reportContext());
  if (view === 'explorer') window.Explorer.render(reportContext());
  $('main').scrollTop = 0;
}

function reportContext() {
  return { rows: state.rows, summary: state.summary, player: state.player };
}

function renderViewHead() {
  $('viewTitle').textContent = VIEWS[state.view].title;
  $('viewSub').textContent = subtitle();
}

function subtitle() {
  if (state.view === 'repertoire') return 'The lines you have committed to, and the gaps left in them';
  if (state.view === 'practice') {
    const queued = window.Study ? window.Study.queue().length : 0;
    return queued
      ? `${plural(queued, 'position')} from your own games`
      : 'The positions your report turned into drills';
  }
  if (state.view === 'progress') return 'What has changed between runs';
  if (state.view === 'explorer') {
    return hasReport()
      ? 'Every opening you play, where it goes wrong, and what to play instead'
      : 'Walk any line and see what the book did with it';
  }
  if (state.app !== 'report' || !state.summary) return '';
  const s = state.summary;
  const engine = state.options && state.options.no_engine ? 'engine skipped' : `depth ${state.options ? state.options.depth : '—'}`;
  return `${state.player} · ${plural(s.games, 'game')} · ${plural(s.judged, 'repeated decision')} · ${plural(s.leaks, 'leak')} · ${engine}`;
}

/* --------------------------------------------------------------------- meta */
function applyHostedLimits(limits) {
  const depth = $('optDepth');
  if (limits.max_depth) {
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
    $('uploadHint').textContent = `Up to ${limits.max_upload_mb} MB per run · parsed with python-chess`;
  }
  $('hostedNoticeText').textContent =
    `Runs here are capped at depth ${limits.max_depth}, ${limits.max_games} games and `
    + `${limits.max_upload_mb} MB per upload, and the engine pass stops after `
    + `${limits.time_budget_s}s. Clone the repo for unlimited local runs.`;
  $('hostedNotice').hidden = false;
}

async function loadMeta() {
  try {
    const meta = await (await fetch(`${API}/api/meta`)).json();
    state.meta = meta;
    state.serverless = meta.serverless === true;
    if (state.serverless) applyHostedLimits(meta.limits || {});
    const e = meta.engine || {};
    const d = meta.database || {};

    setStatus(
      e.available && d.available ? 'ok' : 'warn',
      e.available
        ? `${e.name.replace('Stockfish ', 'SF ')} · ${d.available ? `${(d.games / 1000).toFixed(0)}k book games` : 'no book'}`
        : 'no engine · statistics only',
    );

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

    if (meta.sample && !meta.sample.available) $('sampleBtn').disabled = true;
    $('engineNotice').hidden = e.available !== false;
    if (e.available === false) {
      $('optNoEngine').checked = true;
      $('optNoEngine').disabled = true;
    }
    renderPrivacy();
  } catch (err) {
    setStatus('bad', 'backend offline');
    renderPrivacy();
  }
}

function setStatus(kind, text) {
  $('statusDot').className = `status-dot is-${kind}`;
  $('statusText').textContent = text;
}

/* Step 11: say what this deployment actually does with the games, rather than
   describing a different one. */
function renderPrivacy() {
  const hosted = state.serverless;
  // Say which product this is in the first breath, not in a modal three clicks away.
  $('gateHosted').hidden = !hosted;
  if (hosted) {
    $('gateHosted').innerHTML =
      'This is a hosted instance of a local-first tool: the run happens on this server, and '
      + '<button type="button" class="link-btn" id="gatePrivacy">what it does with your games</button> '
      + 'is worth two sentences. To keep the games on your own machine, '
      + '<a href="https://github.com/AdLgames/chess-opening-leak-analyzer" target="_blank" rel="noopener">clone the repo</a> '
      + 'and run <code>make setup</code>.';
    $('gatePrivacy').addEventListener('click', () => openDialog('privacyDialog'));
  }
  $('privacyBody').innerHTML = hosted
    ? `<p>This is a hosted instance of a local-first tool. When you enter a username, this
         server fetches your public game archive from Chess.com or Lichess, analyses it
         inside the deployed function, and returns the report. Nothing is written to a
         database and there are no accounts; fetched archives sit in the function's
         temporary storage and go when the instance is recycled.</p>
       <p>Your repertoire decisions, your drill history and your last report are kept in
         this browser only — they are never sent anywhere.</p>
       <p>To keep the games on your own machine instead, clone
         <a href="https://github.com/AdLgames/chess-opening-leak-analyzer" target="_blank" rel="noopener">the repository</a>
         and run <code>make setup</code>: the local build does the same work with a local
         Stockfish and a local SQLite book, and makes no outbound requests beyond the
         archive fetch you ask for.</p>`
    : `<p>This is the local build. Your games are read on this machine, by a local
         Stockfish and a local SQLite opening book. The only outbound request is the
         archive fetch you ask for, straight to Chess.com or Lichess.</p>
       <p>Your repertoire decisions, your drill history and your last report are kept in
         this browser only.</p>`;
  $('costExplainer').textContent = `${V.METRICS.cost.definition} ${V.METRICS.cost.why}`;
  $('costFormula').textContent = V.METRICS.cost.formula;
  $('flagLegend').innerHTML = V.FLAG_ORDER.map(
    (k) => `<li><span class="chip chip-${V.FLAGS[k].tone}">${esc(V.FLAGS[k].label)}</span> ${esc(V.FLAGS[k].definition)}</li>`,
  ).join('');
}

/* --------------------------------------------------------------- run inputs */
const PROVIDERS = {
  chesscom: { label: 'Chess.com', placeholder: 'e.g. hikaru', hint: 'your Chess.com username' },
  lichess: { label: 'Lichess', placeholder: 'e.g. DrNykterstein', hint: 'your Lichess username' },
};
let lastAccount = null;

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
  $('runBtn').textContent = name ? `Analyse ${name}'s games` : V.ACTIONS.analyse.button;
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
  $('speedChips')
    ? Array.from(document.querySelectorAll('#speedChips input:checked')).map((c) => c.value)
    : ['blitz', 'rapid', 'classical'];

async function checkAccount({ quiet = false } = {}) {
  const username = $('optUser').value.trim();
  if (!username) return null;
  const seq = ++state.lookupSeq;
  try {
    const res = await fetch(
      `${API}/api/lookup?provider=${encodeURIComponent(state.provider)}&username=${encodeURIComponent(username)}`,
    );
    const body = await res.json();
    if (seq !== state.lookupSeq) return null;
    if (!body.found) {
      state.profile = null;
      $('profileCard').hidden = true;
      if (!quiet) showFetchProblem(body.error || 'Account not found', body.hint || '', '');
      return null;
    }
    renderProfile(body.profile);
    lastAccount = { provider: state.provider, username: body.profile.username };
    S.prefs.set('account', lastAccount);
    return body.profile;
  } catch (err) {
    if (!quiet) showFetchProblem('Could not reach the lookup service', err.message, '');
    return null;
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

function renderFiles() {
  const list = $('fileList');
  list.hidden = state.files.length === 0;
  list.innerHTML = state.files
    .map((f) => `<li><span>${esc(f.name)}</span><span>${(f.size / 1024).toFixed(0)} KB</span></li>`)
    .join('');
  $('runUploadBtn').textContent = state.files.length
    ? `Analyse ${plural(state.files.length, 'file')}`
    : V.ACTIONS.analyse.button;
}

/* Advanced settings are optional chrome: read them defensively so a build that
   drops the whole block still runs on the defaults. */
function val(id, fallback) {
  const el = $(id);
  if (!el) return fallback;
  if (el.type === 'checkbox') return el.checked;
  const v = typeof el.value === 'string' ? el.value.trim() : el.value;
  return v === '' ? fallback : v;
}

function collectOptions(mode) {
  const fd = new FormData();
  fd.append('source', mode);
  fd.append('use_sample', mode === 'sample' ? 'true' : 'false');
  fd.append('player', val('optPlayer', ''));
  fd.append('color', val('optColor', 'both'));
  fd.append('depth', val('optDepth', 16));
  fd.append('max_moves', val('optMoves', 15));
  fd.append('min_games', val('optMinGames', 3));
  fd.append('eval_drop', val('optEvalDrop', 0.8));
  fd.append('score_gap', val('optScoreGap', 6));
  fd.append('min_db_games', val('optMinDb', 20));
  fd.append('no_engine', val('optNoEngine', false) ? 'true' : 'false');
  if (mode === 'upload') state.files.forEach((f) => fd.append('files', f, f.name));
  if (mode === 'username') {
    fd.append('username', $('optUser').value.trim());
    fd.append('provider', state.provider);
    fd.append('max_games', val('optMaxGames', 200));
    fd.append('time_classes', speedList().join(','));
    fd.append('include_unrated', val('optRated', true) ? 'false' : 'true');
    fd.append('since', val('optSince', ''));
    fd.append('until', val('optUntil', ''));
    fd.append('refresh', val('optRefresh', false) ? 'true' : 'false');
    if (state.provider === 'lichess') fd.append('lichess_token', val('optToken', ''));
  }
  return fd;
}

/* An estimate good enough to warn with: fetch and parse dominate, the engine pass
   is the part worth offering to skip. */
function estimateSeconds() {
  const games = Number(val('optMaxGames', 200));
  const depth = Number(val('optDepth', 16));
  if (val('optNoEngine', false)) return games * 0.05;
  return games * 0.05 + games * 0.02 * Math.pow(1.25, depth - 12);
}

function updateSpeedHint() {
  const secs = estimateSeconds();
  const hint = $('speedHint');
  hint.hidden = secs < 60 || val('optNoEngine', false);
  if (!hint.hidden) {
    hint.innerHTML =
      `About ${Math.round(secs / 60)} minute${secs >= 120 ? 's' : ''} at these settings. `
      + '<button type="button" class="link-btn" id="skipEngine">Run without the engine instead</button>';
    $('skipEngine').addEventListener('click', () => {
      if ($('optNoEngine')) $('optNoEngine').checked = true;
      updateSpeedHint();
    });
  }
}

/* ----------------------------------------------------------------- the run */
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
  closeDialog('runDialog');
  setBusy(true);
  setAppState('running');
  $('spinner').className = 'spinner';
  $('progressTitle').textContent = {
    sample: 'Analysing the sample archive',
    upload: 'Analysing your files',
    username: `Fetching ${$('optUser').value.trim() || 'your'} games`,
  }[mode];
  $('log').textContent = 'Queued…';
  $('barFill').style.width = '8%';
  $('barFill').classList.remove('is-error');

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

/* The sample archive answers from a cached report, so the demo is one click and
   no wait. If the backend has no cache it falls back to a real run. */
async function runDemo() {
  setBusy(true);
  setAppState('running');
  $('spinner').className = 'spinner';
  $('progressTitle').textContent = 'Loading the sample report';
  $('progressElapsed').textContent = '0.0s';
  $('log').textContent = 'Reading the cached sample run.';
  $('barFill').style.width = '40%';
  try {
    const res = await fetch(`${API}/api/demo-report`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const body = await res.json();
    $('barFill').style.width = '100%';
    $('spinner').className = 'spinner is-done';
    state.csvText = body.csv || '';
    applyReport(body, { options: body.options, source: 'sample', demo: true });
    setBusy(false);
  } catch (err) {
    startRun('sample');
  }
}

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
  // back to whichever screen the user can act on
  setAppState(hasReport() ? 'report' : 'empty');
  if (!hasReport()) showFetchProblem('The run did not finish', message, '');
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
    const data = await (await fetch(`${API}/api/report/${state.jobId}`)).json();
    state.csvText = '';
    applyReport(data, job);
    setBusy(false);
  };
  step();
}

function setBusy(busy) {
  ['runBtn', 'runUploadBtn', 'sampleBtn', 'runAgainBtn'].forEach((id) => {
    const el = $(id);
    if (el) el.disabled = busy;
  });
  $('runAgainBtn').textContent = busy ? 'Running…' : V.ACTIONS.rerun.button;
}

/* ------------------------------------------------------------------ report */
function applyReport(data, job, { cached = false } = {}) {
  state.rows = data.rows || [];
  state.summary = data.summary;
  state.player = data.player;
  state.options = (job && job.options) || data.options || null;
  state.source = (job && job.source) || data.source || '';
  state.account = (job && job.account) || data.account || null;
  state.demo = Boolean((job && job.demo) || data.demo || state.source === 'sample');
  state.showAll = false;
  state.selected = null;

  $('demoBanner').hidden = !state.demo;
  setAppState('report');
  renderSummaryBand();
  renderChart();
  renderFilters();
  renderTable();
  window.Explorer.render(reportContext());
  if (window.Study) window.Study.setRows(state.rows);

  const first = visibleRows().rows[0];
  if (first) selectRow(first);

  if (!cached) {
    S.lastReport.save({
      rows: state.rows,
      summary: state.summary,
      player: state.player,
      options: state.options,
      source: state.source,
      account: state.account,
      demo: state.demo,
      csv: state.csvText,
      at: Date.now(),
    });
    if (!state.demo) recordRun();
  }
  renderNav();
  renderViewHead();
}

/* One line per run, so Progress has something to plot. */
function recordRun() {
  const cov = window.Repertoire.coverage(reportContext());
  S.runs.record({
    id: `${state.player}:${Date.now()}`,
    at: Date.now(),
    player: state.player,
    games: state.summary.games,
    leaks: state.summary.leaks,
    cost: state.summary.cost || 0,
    coverage: cov.pct,
    keys: state.rows.map((r) => S.leakKey(r)),
    labels: Object.fromEntries(
      state.rows.map((r) => [S.leakKey(r), `${r.opening || r.eco || 'Opening'} · ${r.your_move}`]),
    ),
    perGame: state.rows.map((r) => ({ key: S.leakKey(r), lost: num(r.lost_points) || 0 })),
  });
}

function renderSummaryBand() {
  const s = state.summary;
  const cov = window.Repertoire.coverage(reportContext());
  const worst = s.by_opening[0];
  const cards = [
    { label: V.METRICS.coverage.label, value: `${cov.pct}%`, note: cov.note, cls: 'accent', title: V.METRICS.coverage.definition },
    { label: 'Leaks', value: s.leaks, note: `${s.white_leaks} white · ${s.black_leaks} black` },
    { label: 'Points shed', value: s.lost_points.toFixed(1), note: 'against the book expectation' },
    { label: 'Games read', value: s.games, note: `${plural(s.judged, 'repeated decision')}` },
    { label: 'Worst opening', value: worst ? worst.lost_points.toFixed(1) : '0', note: worst ? worst.opening : 'nothing flagged' },
  ];
  $('summaryBand').innerHTML = cards
    .map(
      (c) => `<div class="kpi ${c.cls || ''}"${c.title ? ` title="${esc(c.title)}"` : ''}>
        <div class="kpi-label">${esc(c.label)}</div>
        <div class="kpi-value">${esc(c.value)}</div>
        <div class="kpi-note">${esc(c.note)}</div></div>`,
    )
    .join('');
}

/* One chart panel, one chart, a toggle between the two readings of it. */
const CHART_FONT = { family: "'Inter', sans-serif", size: 11 };
function renderChart() {
  // the chart library is a CDN script: without it the panel has nothing to say,
  // so it does not render at all rather than leaving an empty frame
  $('chartPanel').hidden = !window.Chart;
  if (!window.Chart || !state.summary) return;
  Chart.defaults.color = getComputedStyle(document.body).getPropertyValue('--text-muted').trim() || '#51637A';
  Chart.defaults.font = CHART_FONT;
  Chart.defaults.borderColor = getComputedStyle(document.body).getPropertyValue('--border').trim() || '#DCE2EA';
  const items = state.summary.by_opening.slice(0, 8);
  const labels = items.map((o) => (o.opening.length > 30 ? o.opening.slice(0, 29) + '…' : o.opening));
  const accent = getComputedStyle(document.body).getPropertyValue('--accent').trim() || '#B8935A';
  const quiet = getComputedStyle(document.body).getPropertyValue('--neutral-bar').trim() || '#3E5265';
  if (state.chart) state.chart.destroy();

  if (state.chartKind === 'lost') {
    $('chartNote').textContent = 'Half-points shed against the book expectation, by opening.';
    state.chart = new Chart($('chartCanvas'), {
      type: 'bar',
      data: { labels, datasets: [{ label: 'Points shed', data: items.map((o) => o.lost_points), backgroundColor: accent, borderRadius: 2, barThickness: 16 }] },
      options: {
        indexAxis: 'y',
        maintainAspectRatio: false,
        animation: prefersReducedMotion() ? false : undefined,
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { afterLabel: (c) => `${plural(items[c.dataIndex].leaks, 'leak')} · ${plural(items[c.dataIndex].games, 'game')}` } },
        },
        scales: { x: { ticks: { precision: 1 } }, y: { grid: { display: false } } },
      },
    });
  } else {
    $('chartNote').textContent = `${V.METRICS.score.definition} Your score against the book's, by opening.`;
    state.chart = new Chart($('chartCanvas'), {
      type: 'bar',
      data: {
        labels,
        datasets: [
          { label: 'You', data: items.map((o) => o.your_score), backgroundColor: accent, borderRadius: 2 },
          { label: 'Book', data: items.map((o) => o.db_score), backgroundColor: quiet, borderRadius: 2 },
        ],
      },
      options: {
        maintainAspectRatio: false,
        animation: prefersReducedMotion() ? false : undefined,
        plugins: { legend: { position: 'bottom', labels: { boxWidth: 10, boxHeight: 10 } } },
        scales: {
          x: { grid: { display: false }, ticks: { maxRotation: 40, minRotation: 40, autoSkip: false, font: { ...CHART_FONT, size: 9.5 } } },
          y: { beginAtZero: true, max: 100, ticks: { callback: (v) => v + '%' } },
        },
      },
    });
  }
}

const prefersReducedMotion = () =>
  window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

/* ------------------------------------------------------------------- table */
function renderFilters() {
  const counts = {};
  state.rows.forEach((r) => V.flagKeys(r.flag).forEach((k) => (counts[k] = (counts[k] || 0) + 1)));
  const chips = [{ key: 'all', label: 'All', n: state.rows.length }].concat(
    V.FLAG_ORDER.filter((k) => counts[k]).map((k) => ({ key: k, label: V.FLAGS[k].label, n: counts[k] })),
  );
  $('flagFilter').innerHTML = chips
    .map(
      (c) => `<button class="seg ${state.filter.flag === c.key ? 'is-active' : ''}" data-flag="${c.key}"
        ${c.key === 'all' ? '' : `title="${esc(V.FLAGS[c.key].definition)}"`}>${esc(c.label)} <i>${c.n}</i></button>`,
    )
    .join('');
  $('flagFilter').querySelectorAll('.seg').forEach((b) =>
    b.addEventListener('click', () => {
      state.filter.flag = b.dataset.flag;
      state.showAll = false;
      renderFilters();
      renderTable();
    }),
  );
  $('rankNote').innerHTML =
    `Ranked by <b>cost</b>: how often you play the move, times how much it costs you, held back `
    + `while the sample is thin — so a habit seen three times cannot outrank one seen thirty. `
    + '<button type="button" class="link-btn" id="rankMore">How cost is worked out</button>';
  $('rankMore').addEventListener('click', () => openDialog('dataDialog'));
}

function visibleRows() {
  const q = state.filter.q.toLowerCase();
  const rows = state.rows
    .filter((r) => {
      if (state.filter.flag !== 'all' && !V.flagKeys(r.flag).includes(state.filter.flag)) return false;
      if (q && !`${r.opening} ${r.eco} ${r.your_move} ${r.variation_line}`.toLowerCase().includes(q)) return false;
      return true;
    })
    .slice()
    .sort((a, b) => ((num(a.cost) || 0) - (num(b.cost) || 0)) * state.sort.dir);
  return { rows, shown: state.showAll ? rows : rows.slice(0, ROW_CAP) };
}

function renderTable() {
  const { rows, shown } = visibleRows();
  const worst = Math.max(1, ...state.rows.map((r) => num(r.cost) || 0));
  $('tableEmpty').hidden = rows.length > 0;
  $('costHead').classList.toggle('is-asc', state.sort.dir === 1);
  $('leakBody').innerHTML = shown
    .map((r, i) => {
      const cost = num(r.cost) || 0;
      const you = num(r.your_score_pct);
      const book = num(r.db_move_score_pct);
      const gap = num(r.score_gap_vs_db_pct);
      const decided = S.repertoire.byKey(S.leakKey(r));
      const selected = state.selected && state.selected.fen === r.fen && state.selected.your_move === r.your_move;
      return `<tr data-i="${i}" tabindex="0" class="${selected ? 'is-selected' : ''} ${decided ? 'is-decided' : ''}">
        <td class="col-cost" data-label="Cost">
          <span class="cost"><b class="mono">${cost.toFixed(1)}</b>
          <span class="cost-bar"><i style="width:${Math.max(3, (cost / worst) * 100).toFixed(1)}%"></i></span></span>
        </td>
        <td class="col-opening" data-label="Opening">
          <span class="opening-name">${esc([r.eco, r.opening].filter(Boolean).join(' ') || 'Unclassified')}</span>
          <span class="opening-line mono">${esc(r.variation_line)}</span>
        </td>
        <td class="col-move" data-label="Your move">
          <span class="mono move">${r.move_number}${r.player_color === 'white' ? '.' : '…'} ${esc(r.your_move)}</span>
          ${V.chips(r.flag)}
          ${decided ? `<span class="chip chip-done">${esc(decided.status === 'committed' ? V.ACTIONS.commit.done : V.ACTIONS.dismiss.done)}</span>` : ''}
        </td>
        <td class="num col-gap" data-label="You vs book">
          <span class="${gap !== null && gap < 0 ? 'delta-bad' : ''}">${you === null ? '—' : you.toFixed(0) + '%'}</span>
          <span class="muted"> vs ${book === null ? '—' : book.toFixed(0) + '%'}</span>
        </td>
        <td class="num" data-label="Games">${esc(r.your_games)}</td>
      </tr>`;
    })
    .join('');
  $('leakBody').querySelectorAll('tr').forEach((tr) => {
    const row = shown[+tr.dataset.i];
    tr.addEventListener('click', () => selectRow(row));
    tr.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        selectRow(row);
      }
    });
  });
  const more = rows.length - shown.length;
  $('showAll').hidden = more <= 0;
  $('showAll').textContent = `Show all ${rows.length}`;
}

/* ------------------------------------------------------------------ detail */
function cpText(cp) {
  const v = num(cp);
  if (v === null) return '—';
  const pawns = v / 100;
  return (pawns >= 0 ? '+' : '') + pawns.toFixed(2);
}

function selectRow(r) {
  if (!r) return;
  state.selected = r;
  $('posHint').textContent = `${r.eco || '—'} · move ${r.move_number} as ${r.player_color}`;
  $('detailFlag').innerHTML = V.chips(r.flag);
  $('detailOpening').textContent = r.opening || r.eco || 'Unclassified';
  $('detailLine').textContent = r.variation_line;
  $('fenText').textContent = r.fen;
  $('lichessLink').href = `https://lichess.org/analysis/standard/${encodeURIComponent(r.fen.replace(/ /g, '_'))}`;
  if (window.Study) window.Study.review(r);

  const gap = num(r.score_gap_vs_db_pct);
  const stats = [
    { label: V.METRICS.score.label, value: fmt(r.your_score_pct, 1, '%'), note: `${r.your_wins}W ${r.your_draws}D ${r.your_losses}L` },
    { label: 'Book score', value: fmt(r.db_move_score_pct, 1, '%'), note: num(r.db_move_games) ? `${(+r.db_move_games).toLocaleString()} games` : 'not in the book' },
    { label: V.METRICS.scoreGap.label, value: gap === null ? '—' : (gap < 0 ? '−' : '+') + Math.abs(gap).toFixed(1) + '%', note: 'your score against the book' },
    { label: V.METRICS.evalDrop.label, value: num(r.eval_drop_pawns) ? '−' + fmt(r.eval_drop_pawns, 2) : '—', note: `${cpText(r.eval_before_cp)} → ${cpText(r.eval_after_cp)}` },
    { label: V.METRICS.cost.label, value: fmt(r.cost, 1), note: `over ${plural(+r.your_games, 'game')}` },
    { label: 'Engine rank', value: r.engine_rank_of_your_move || '—', note: 'of the move you played' },
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
        <td class="mono">${esc(a.move)}</td>
        <td class="num">${cpText(a.cp)}</td>
        <td class="num">${num(a.db) === null ? '—' : fmt(a.db, 1, '%')}</td>
        <td class="muted">${esc(a.verdict)}</td></tr>`,
    )
    .join('');
  const games = (r.sample_games || '').split('; ').filter(Boolean);
  $('detailGames').innerHTML = games.length
    ? `Seen in ${games.length} of your games — ${games
        .slice(0, 3)
        .map((g, i) => (g.startsWith('http') ? `<a href="${esc(g)}" target="_blank" rel="noopener">game ${i + 1}</a>` : esc(g)))
        .join(', ')}`
    : '';
  renderCommitBar();
  renderTable();
}

function renderCommitBar() {
  const r = state.selected;
  if (!r) return;
  const answer = (window.Study && window.Study.currentAnswer()) || r.engine_best_1 || '';
  const decided = S.repertoire.byKey(S.leakKey(r));
  $('commitBtn').textContent = answer ? `Commit ${answer}` : V.ACTIONS.commit.button;
  $('commitBtn').disabled = !answer;
  $('dismissBtn').textContent = V.ACTIONS.dismiss.button;
  $('drillBtn').textContent = V.ACTIONS.drill.button;
  $('commitState').textContent = decided
    ? decided.status === 'committed'
      ? `${V.ACTIONS.commit.done}: ${decided.answer}`
      : V.ACTIONS.dismiss.done
    : '';
  $('commitState').className = `commit-state ${decided ? `is-${decided.status}` : ''}`;
  $('commitHint').textContent = answer
    ? 'Committing writes this line into your repertoire and takes it off the holes list.'
    : 'Play the move you would rather have here on the board, then commit it.';
}

function commitSelected() {
  const r = state.selected;
  if (!r) return;
  const answer = (window.Study && window.Study.currentAnswer()) || r.engine_best_1 || '';
  if (!answer) return;
  S.repertoire.commit(r, answer);
  afterDecision();
}

function dismissSelected() {
  if (!state.selected) return;
  S.repertoire.dismiss(state.selected);
  afterDecision();
}

function afterDecision() {
  renderCommitBar();
  renderTable();
  renderSummaryBand();
  renderNav();
  if (state.view === 'repertoire') window.Repertoire.renderRepertoire(reportContext());
}

/* ----------------------------------------------------------------- exports */
function download(name, text, type) {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const a = document.createElement('a');
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

function exportCsv() {
  if (state.csvText) return download('opening_leaks.csv', state.csvText, 'text/csv');
  if (state.jobId) return window.open(`${API}/api/report/${state.jobId}/csv`, '_blank');
  const rows = state.rows;
  if (!rows.length) return;
  const cols = Object.keys(rows[0]);
  const body = rows.map((r) => cols.map((c) => `"${String(r[c] ?? '').replace(/"/g, '""')}"`).join(','));
  download('opening_leaks.csv', [cols.join(','), ...body].join('\n'), 'text/csv');
}

/* ----------------------------------------------------------------- dialogs */
function openDialog(id) {
  const d = $(id);
  if (typeof d.showModal === 'function') d.showModal();
  else d.setAttribute('open', '');
}
function closeDialog(id) {
  const d = $(id);
  if (typeof d.close === 'function') d.close();
  else d.removeAttribute('open');
}

/* -------------------------------------------------------------------- boot */
function restoreAdvanced() {
  const box = $('advanced');
  if (!box) return;
  box.open = S.prefs.get('advancedOpen', false) === true;
  box.addEventListener('toggle', () => S.prefs.set('advancedOpen', box.open));
}

function bootAccount() {
  const saved = S.prefs.get('account', null) || lastAccount;
  setProvider(saved && PROVIDERS[saved.provider] ? saved.provider : 'chesscom');
  if (saved && saved.username) {
    $('optUser').value = saved.username;
    updateRunLabel();
    checkAccount({ quiet: true });
  }
}

function bootReport() {
  const cached = S.lastReport.load();
  if (!cached || !cached.rows || !cached.rows.length) return false;
  state.csvText = cached.csv || '';
  applyReport(cached, { options: cached.options, source: cached.source, account: cached.account, demo: cached.demo }, { cached: true });
  return true;
}

/* Listeners on controls that only exist when Advanced is present. */
function on(id, event, fn) {
  const el = $(id);
  if (el) el.addEventListener(event, fn);
}

function wire() {
  // ---- run form
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
    }),
  );
  ['dragleave', 'drop'].forEach((ev) =>
    dz.addEventListener(ev, (e) => {
      e.preventDefault();
      dz.classList.remove('is-over');
    }),
  );
  dz.addEventListener('drop', (e) => {
    state.files = Array.from(e.dataTransfer.files).filter((f) => f.name.toLowerCase().endsWith('.pgn'));
    renderFiles();
  });

  $('runBtn').addEventListener('click', () => startRun('username'));
  $('runUploadBtn').addEventListener('click', () => startRun('upload'));
  $('sampleBtn').addEventListener('click', () => runDemo());
  $('uploadToggle').addEventListener('click', () => {
    const open = $('panelUpload').hidden;
    $('panelUpload').hidden = !open;
    $('panelAccount').hidden = open;
    state.mode = open ? 'upload' : 'username';
    $('uploadToggle').textContent = open ? 'Use my account instead' : 'Upload a PGN instead';
  });
  $('runAgainBtn').addEventListener('click', () => {
    mountRunForm('dialogSlot');
    openDialog('runDialog');
  });
  $('runDialogClose').addEventListener('click', () => closeDialog('runDialog'));
  $('demoExit').addEventListener('click', () => {
    S.lastReport.clear();
    state.rows = [];
    state.summary = null;
    state.demo = false;
    setAppState('empty');
    go('report');
    $('optUser').focus();
  });

  document.querySelectorAll('#providerSeg .seg-btn').forEach((b) =>
    b.addEventListener('click', () => setProvider(b.dataset.provider)),
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
  $('optMaxGames').addEventListener('input', (e) => {
    $('maxGamesOut').textContent = e.target.value;
    updateSpeedHint();
  });
  on('optDepth', 'input', (e) => {
    $('depthOut').textContent = e.target.value;
    updateSpeedHint();
  });
  on('optMoves', 'input', (e) => ($('movesOut').textContent = `${e.target.value} moves`));
  on('optNoEngine', 'change', updateSpeedHint);
  const today = new Date().toISOString().slice(0, 10);
  ['optSince', 'optUntil'].forEach((id) => {
    if ($(id)) $(id).max = today;
  });

  // ---- report
  $('search').addEventListener('input', (e) => {
    state.filter.q = e.target.value;
    state.showAll = false;
    renderTable();
  });
  $('costHead').title = `${V.METRICS.cost.definition}\n${V.METRICS.cost.formula}`;
  $('costHead').addEventListener('click', () => {
    state.sort.dir = -state.sort.dir;
    renderTable();
  });
  $('showAll').addEventListener('click', () => {
    state.showAll = true;
    renderTable();
  });
  document.querySelectorAll('#chartToggle .seg').forEach((b) =>
    b.addEventListener('click', () => {
      document.querySelectorAll('#chartToggle .seg').forEach((x) => x.classList.remove('is-active'));
      b.classList.add('is-active');
      state.chartKind = b.dataset.chart;
      renderChart();
    }),
  );
  $('commitBtn').addEventListener('click', commitSelected);
  $('dismissBtn').addEventListener('click', dismissSelected);
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

  // ---- exports
  $('exportCsv').addEventListener('click', exportCsv);
  $('exportRepertoire').addEventListener('click', () => {
    const pgn = window.Repertoire.pgn(state.player);
    if (pgn) download('repertoire.pgn', pgn, 'application/x-chess-pgn');
  });
  $('exportDrills').addEventListener('click', () => {
    const pgn = window.Repertoire.drillPgn(window.Study ? window.Study.queue() : state.rows);
    if (pgn) download('drill_set.pgn', pgn, 'application/x-chess-pgn');
  });
  $('exportStudy').addEventListener('click', (e) => {
    e.target.href = window.Repertoire.studyUrl();
  });
  $('exportMenu').addEventListener('click', (e) => {
    if (e.target.classList.contains('menu-item')) $('exportMenu').open = false;
  });

  // ---- chrome
  $('dataBtn').addEventListener('click', () => openDialog('dataDialog'));
  $('statusBtn').addEventListener('click', () => openDialog('dataDialog'));
  $('dataDialogClose').addEventListener('click', () => closeDialog('dataDialog'));
  $('privacyBtn').addEventListener('click', () => openDialog('privacyDialog'));
  $('privacyDialogClose').addEventListener('click', () => closeDialog('privacyDialog'));

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

  document.querySelectorAll('.nav-item').forEach((a) =>
    a.addEventListener('click', (e) => {
      e.preventDefault();
      go(a.dataset.view);
      setDrawer(false);
    }),
  );
  window.addEventListener('hashchange', () => go(location.hash.slice(1)));

  if (window.Study) {
    window.Study.onQueueChange((queue) => {
      $('practiceInvite').hidden = queue.length > 0;
      renderViewHead();
    });
  }
}

window.App = { go, reportContext: () => reportContext(), select: selectRow };

// the form is a template so it can be parented into either the empty screen or
// the Run again dialog; materialise it before anything looks its controls up
$('runFormTemplate').replaceWith($('runFormTemplate').content);
mountRunForm('gateSlot');
wire();
restoreAdvanced();
if (window.Study) window.Study.init(API);
bootAccount();
setAppState('empty');
bootReport();           // a cached run boots straight into `report`
go(location.hash.slice(1) || 'report');
loadMeta();
