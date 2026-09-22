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

/* Three destinations: what is wrong, how to fix it, and what you have built.
   Macro and micro no longer share a page. */
const VIEWS = {
  dashboard: { title: 'Dashboard', needsRun: false },
  clinic: { title: 'Clinic', needsRun: true },
  repertoire: { title: 'Repertoire', needsRun: false },
  // Prep needs no run: building the lines you mean to play is the one thing here
  // you can do before the analyser has ever seen a game of yours.
  prep: { title: 'Prep', needsRun: false },
};

const state = {
  view: 'dashboard',
  clinicMode: 'study',
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
  chartKind: 'lost',
  costMetric: null,
  theme: 'system',
  selectedFen: '',
  libFen: '',
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
  document.querySelectorAll('.nav-item, .tab-item').forEach((a) => {
    const view = a.dataset.view;
    a.hidden = VIEWS[view].needsRun && !unlocked;
    a.classList.toggle('is-active', view === state.view);
    if (view === state.view) a.setAttribute('aria-current', 'page');
    else a.removeAttribute('aria-current');
  });
}

function go(view) {
  if (!VIEWS[view]) view = 'dashboard';
  if (VIEWS[view].needsRun && !hasReport() && !S.repertoire.all().length) view = 'dashboard';
  state.view = view;
  Object.keys(VIEWS).forEach((name) => {
    $(`view${name[0].toUpperCase()}${name.slice(1)}`).hidden = name !== view;
  });
  if (location.hash !== `#${view}`) history.replaceState(null, '', `#${view}`);
  renderNav();
  renderViewHead();
  if (view === 'clinic') renderClinic();
  if (view === 'repertoire') {
    window.Repertoire.renderRepertoire(reportContext());
    window.Repertoire.renderProgress(reportContext());
    window.Explorer.render(reportContext());
  }
  if (view === 'prep' && window.Prep) window.Prep.render();
  $('main').scrollTop = 0;
}

function reportContext() {
  // `tree` is everything you play; `rows` is the subset that leaks.
  return { rows: state.rows, tree: state.tree, summary: state.summary, player: state.player };
}

function renderViewHead() {
  $('viewTitle').textContent = VIEWS[state.view].title;
  $('viewSub').textContent = subtitle();
}

function subtitle() {
  if (state.view === 'repertoire') {
    return 'What you have committed, how it is moving, and every opening you play';
  }
  if (state.view === 'clinic') {
    const r = state.selected;
    if (!r) return 'One leak at a time: the board, the cost, and the fix';
    return `${r.opening || r.eco || 'Unclassified'} · move ${r.move_number} as ${r.player_color}`;
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

    // the calculation describes itself: prefer the served text over our copy
    if (meta.metrics && meta.metrics.cost) state.costMetric = meta.metrics.cost;
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
         inside the deployed function, and returns the report. The games themselves are
         not kept: fetched archives sit in the function's temporary storage and go when
         the instance is recycled.</p>
       <p>What <em>is</em> kept, once you are signed in, is your progress — the leaks that
         have been found for you, which of them you committed a reply to, how your drills
         went, one line per run, and your most recent report. It also keeps which games
         each run read and which of your decisions appeared in which game — identifiers
         only, so evidence can add up across runs without counting the same game twice.
         That is the point of an account: without it, a second run cannot tell you which
         leaks you fixed, and a line you meet twice a month can never be judged at all.
         It is
         stored in this deployment's database, alongside your email address or your
         Lichess account id. No passwords are stored, and if you sign in with Lichess the
         access token is encrypted before it is written.</p>
       <p><b>Download my data</b> in the account menu gives you all of it as one JSON file,
         and <b>Delete my account</b> erases it — the account row and everything that hangs
         off it, with nothing kept back. Your browser also keeps a working copy so the app
         is fast and still readable offline; signing out clears it.</p>
       <p>To keep the games on your own machine instead, clone
         <a href="https://github.com/AdLgames/chess-opening-leak-analyzer" target="_blank" rel="noopener">the repository</a>
         and run <code>make setup</code>: the local build does the same work with a local
         Stockfish and a local SQLite book, and makes no outbound requests beyond the
         archive fetch you ask for.</p>`
    : `<p>This is the local build. Your games are read on this machine, by a local
         Stockfish and a local SQLite opening book. The only outbound request is the
         archive fetch you ask for, straight to Chess.com or Lichess.</p>
       <p>Your repertoire decisions, your drill history and your last report are kept in
         this browser only. The local build has no accounts and no database.</p>`;
  const cost = state.costMetric || V.METRICS.cost;
  $('costExplainer').textContent = `${cost.definition} ${cost.why || V.METRICS.cost.why}`;
  $('costFormula').textContent = cost.formula;
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
  renderSpeedChips(provider);
  clearProfile();
}

/* The two sites do not have the same time controls, and offering one that
   cannot match is how a run quietly comes back short. Chess.com has no
   "classical" at all — its long games are "daily". */
const PROVIDER_SPEEDS = {
  chesscom: ['bullet', 'blitz', 'rapid', 'daily'],
  lichess: ['bullet', 'blitz', 'rapid', 'classical', 'daily'],
};

function renderSpeedChips(provider) {
  const field = $('speedChips');
  if (!field) return;
  const allowed = PROVIDER_SPEEDS[provider] || PROVIDER_SPEEDS.lichess;
  field.querySelectorAll('.chip-check').forEach((label) => {
    const box = label.querySelector('input');
    const ok = allowed.includes(box.value);
    label.hidden = !ok;
    // An unticked box for a control this site does not have would still be
    // sent, so clear it rather than just hiding it.
    if (!ok) box.checked = false;
  });
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
  $('runError').hidden = true;

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

  // Stay on the failure with the reason in plain sight. This used to jump
  // straight back to whatever report was already loaded and say nothing, so a
  // second run for a different player showed the first player's results and no
  // error — indistinguishable from the app having ignored the request.
  $('runErrorText').textContent = message;
  $('runErrorBack').hidden = !hasReport();
  $('runError').hidden = false;
  if ($('logWrap')) $('logWrap').open = true;
  setAppState('running');
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
  state.tree = data.tree || [];
  state.gameIds = data.game_ids || [];
  state.summary = data.summary;
  state.player = data.player;
  state.options = (job && job.options) || data.options || null;
  state.source = (job && job.source) || data.source || '';
  state.account = (job && job.account) || data.account || null;
  state.demo = Boolean((job && job.demo) || data.demo || state.source === 'sample');
  state.showAll = false;
  state.selected = null;

  $('demoBanner').hidden = !state.demo;
  renderShortfall();
  setAppState('report');
  renderSummaryBand();
  renderChart();
  renderFamilies();
  renderFilters();
  renderTable();
  window.Explorer.render(reportContext());
  if (window.Study) window.Study.setRows(state.rows);

  const first = visibleRows().rows[0];
  if (first) selectRow(first, { open: false });
  renderTrainCta();

  if (!cached) {
    S.lastReport.save({
      rows: state.rows,
      tree: state.tree,
      gameIds: state.gameIds,
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

/* When a run came back with fewer games than were asked for, say so where it
   will be read. The reason was already in the log, but the log is collapsed by
   default, so the visible result was a number that looked like the request had
   been ignored. */
function renderShortfall() {
  const banner = $('shortBanner');
  if (!banner) return;
  const account = state.account || {};
  const note = account.shortfall || '';
  banner.hidden = !note || state.demo;
  if (banner.hidden) return;
  $('shortText').innerHTML =
    `<b>${esc(account.games || 0)} of the ${esc(account.requested || 0)} games you asked for.</b> `
    + esc(note.replace(/^Found [^—]*—\s*/, ''));
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
    // Who the baseline came from belongs next to the number it produced: "6%
    // below the book" means something different if the book is everybody.
    { label: 'Points shed', value: s.lost_points.toFixed(1),
      note: s.banded ? `against ${esc(s.band)} players` : 'against the book expectation',
      title: s.banded
        ? `Your games read as about ${s.band} strength, so the book's figures here are that band's, not everybody's.`
        : 'This opening book has no rating bands, so the comparison is against players of every strength at once.' },
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

/* One chart panel, one chart, a toggle between the two readings of it.

   Drawn as SVG rather than through a chart library: these are two small, fixed
   forms, and hand-drawing them buys the mark specs (thin bars, a rounded data
   end, hairline axes, labels that never collide) and removes a CDN the panel
   used to disappear without.

   Colour does one job in each. "Points shed" is a single series, so every bar is
   the same brass — length already carries the magnitude, and colouring bars by
   their own value would burn the only free channel on information the chart
   already shows. "You vs book" is two marks per row, so the book takes a
   recessive slate and your score the brass: the subject reads, the reference
   recedes. Both pairs are steps of the brand hues, checked for colour-vision
   separation and contrast against each surface. */
const CHART_ROW = 30;           // band per category
const CHART_BAR = 14;           // <= 24px, leaving the rest of the band as air
const CHART_PAD = { top: 10, right: 58, bottom: 26, left: 148 };
const chartPad = (width) => (width < 560
  ? { top: 10, right: 44, bottom: 26, left: 96 }
  : CHART_PAD);

const truncate = (s, n) => (String(s).length > n ? `${String(s).slice(0, n - 1)}…` : String(s));

function chartItems() {
  return (state.summary ? state.summary.by_opening : []).slice(0, 8);
}

/* Drawn at the width the panel actually has, so the geometry is exact and the
   text is never scaled: a viewBox that matches the pixels, redrawn on resize. */
function renderChart() {
  const items = chartItems();
  const wrap = $('chartWrap');
  $('chartPanel').hidden = !items.length;
  if (!items.length) return;
  const width = Math.max(320, Math.round(wrap.clientWidth || 640));
  wrap.innerHTML = state.chartKind === 'lost'
    ? pointsShedChart(items, width)
    : youVsBookChart(items, width);
  $('chartNote').textContent = state.chartKind === 'lost'
    ? 'Half-points shed against the book expectation, by opening. The table below has every row.'
    : `${V.METRICS.score.definition} Your score against the book's from the same positions.`;
  $('chartKey').hidden = state.chartKind !== 'vs';
  wireChartHover(items);
}

const plotWidth = (width) => width - chartPad(width).left - chartPad(width).right;

function chartOpen(width, height, label) {
  return `<svg class="chart" viewBox="0 0 ${width} ${height}" width="100%" height="${height}"
    role="img" aria-label="${esc(label)}">`;
}

/* --- magnitude: one series, so one colour and a value at every tip ---------- */
function pointsShedChart(items, width) {
  const max = Math.max(...items.map((o) => o.lost_points), 0.1);
  const pad = chartPad(width);
  const plot = plotWidth(width);
  const height = pad.top + items.length * CHART_ROW + 6;
  const rows = items
    .map((o, i) => {
      const y = pad.top + i * CHART_ROW;
      const w = Math.max(2, (o.lost_points / max) * plot);
      return `<g class="ch-row" data-i="${i}">
        <rect class="ch-hit" x="0" y="${y}" width="${width}" height="${CHART_ROW}" />
        <text class="ch-cat" x="${pad.left - 12}" y="${y + CHART_ROW / 2}">${esc(truncate(o.opening, width < 560 ? 12 : 22))}</text>
        <rect class="ch-bar" x="${pad.left}" y="${y + (CHART_ROW - CHART_BAR) / 2}"
              width="${w.toFixed(1)}" height="${CHART_BAR}" rx="4" />
        <text class="ch-val" x="${(pad.left + w + 9).toFixed(1)}" y="${y + CHART_ROW / 2}">${o.lost_points.toFixed(1)}</text>
      </g>`;
    })
    .join('');
  const label = `Points shed by opening: ${items.map((o) => `${o.opening}, ${o.lost_points.toFixed(1)}`).join('; ')}`;
  return `${chartOpen(width, height, label)}<g class="ch-plot">${rows}</g></svg>`;
}

/* --- two values per row: the gap is the story, so a dumbbell --------------- */
function youVsBookChart(items, width) {
  const pad = chartPad(width);
  const plot = plotWidth(width);
  const height = pad.top + items.length * CHART_ROW + pad.bottom;
  const at = (pct) => pad.left + (Math.max(0, Math.min(100, pct)) / 100) * plot;
  const axisBottom = pad.top + items.length * CHART_ROW;
  const ticks = [0, 50, 100]
    .map((t) => `<g class="ch-tick"><line x1="${at(t).toFixed(1)}" x2="${at(t).toFixed(1)}"
        y1="${pad.top - 6}" y2="${axisBottom}" /><text x="${at(t).toFixed(1)}"
        y="${height - 8}">${t}%</text></g>`)
    .join('');
  const rows = items
    .map((o, i) => {
      const y = pad.top + i * CHART_ROW + CHART_ROW / 2;
      const you = at(o.your_score);
      const book = at(o.db_score);
      // only the first row is labelled, and only where the label fits without
      // being clipped: the axis, the tooltip and the table carry the rest
      const label = i === 0 && width >= 560
        ? `<text class="ch-val" x="${(Math.max(you, book) + 12).toFixed(1)}" y="${y}">${o.your_score.toFixed(0)}% vs ${o.db_score.toFixed(0)}%</text>`
        : '';
      return `<g class="ch-row" data-i="${i}">
        <rect class="ch-hit" x="0" y="${y - CHART_ROW / 2}" width="${width}" height="${CHART_ROW}" />
        <text class="ch-cat" x="${pad.left - 12}" y="${y}">${esc(truncate(o.opening, width < 560 ? 12 : 22))}</text>
        <line class="ch-link" x1="${Math.min(you, book).toFixed(1)}" x2="${Math.max(you, book).toFixed(1)}" y1="${y}" y2="${y}" />
        <circle class="ch-dot ch-ref" cx="${book.toFixed(1)}" cy="${y}" r="5" />
        <circle class="ch-dot ch-you" cx="${you.toFixed(1)}" cy="${y}" r="5" />
        ${label}
      </g>`;
    })
    .join('');
  const label = `Your score against the book by opening: ${items
    .map((o) => `${o.opening}, you ${o.your_score.toFixed(0)} percent, book ${o.db_score.toFixed(0)} percent`)
    .join('; ')}`;
  return `${chartOpen(width, height, label)}<g class="ch-axis">${ticks}</g><g class="ch-plot">${rows}</g></svg>`;
}

/* A tooltip per mark: what makes the rows this chart does not label readable
   without leaving the page. */
function wireChartHover(items) {
  const wrap = $('chartWrap');
  const tip = $('chartTip');
  wrap.querySelectorAll('.ch-row').forEach((row) => {
    const o = items[+row.dataset.i];
    const show = (event) => {
      tip.innerHTML = `<b>${esc(o.opening)}</b>`
        + `<span>${o.lost_points.toFixed(1)} points shed · ${plural(o.leaks, 'leak')} · ${plural(o.games, 'game')}</span>`
        + `<span>you ${o.your_score.toFixed(0)}% · book ${o.db_score.toFixed(0)}%</span>`;
      const box = wrap.getBoundingClientRect();
      tip.style.left = `${Math.max(60, Math.min(box.width - 60, event.clientX - box.left))}px`;
      tip.style.top = `${Math.max(38, event.clientY - box.top - 10)}px`;
      tip.hidden = false;
    };
    row.addEventListener('pointerenter', show);
    row.addEventListener('pointermove', show);
    row.addEventListener('pointerleave', () => (tip.hidden = true));
  });
}

const prefersReducedMotion = () =>
  window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

/* ------------------------------------------------------------------- table */
/* The leak table is one row per decision, which is the right grain for fixing a
   move and the wrong one for deciding what to work on. This is the same rows a
   level up: the family, then the variations inside it, ranked by cost so a
   well-evidenced problem outranks a thin one that happens to have shed more
   points. Choosing a row drives the existing search filter rather than adding a
   second, so the table below always explains itself. */
function renderFamilies() {
  const fams = (state.summary && state.summary.by_family) || [];
  $('familyPanel').hidden = fams.length < 2;
  if (fams.length < 2) return;
  const worst = Math.max(...fams.map((f) => f.cost)) || 1;
  const costLabel = (state.costMetric && state.costMetric.label) || 'Cost';
  $('familyList').innerHTML = `
    <div class="fam-head" aria-hidden="true">
      <span>Opening</span><span></span><span>${esc(costLabel)}</span><span></span><span></span>
    </div>
    <ul class="fam-list">
      ${fams.map((f) => `
        <li>
          <details ${f.variations.length > 1 ? '' : 'data-leaf="1"'}>
            <summary>
              <span class="fam-name">${esc(f.family)}</span>
              <span class="fam-bar"><i style="width:${Math.max(3, (f.cost / worst) * 100)}%"></i></span>
              <span class="fam-cost mono">${f.cost.toFixed(1)}</span>
              <span class="fam-meta muted small">${f.leaks} leak${f.leaks === 1 ? '' : 's'}
                · ${f.lost_points.toFixed(1)} shed</span>
              <button class="fam-pick" data-q="${esc(f.family)}">Show</button>
            </summary>
            <ul class="fam-vars">
              ${f.variations.map((v) => `
                <li>
                  <button class="fam-var" data-q="${esc(v.opening)}">
                    <span>${esc(v.opening)}</span>
                    <span class="mono">${v.cost.toFixed(1)}</span>
                  </button>
                </li>`).join('')}
            </ul>
          </details>
        </li>`).join('')}
    </ul>`;
  $('familyList').querySelectorAll('[data-q]').forEach((b) => {
    b.addEventListener('click', (ev) => {
      ev.preventDefault();
      ev.stopPropagation();
      $('search').value = b.dataset.q;
      state.filter.q = b.dataset.q;
      state.showAll = false;
      renderTable();
      $('tablePanel').scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });
}

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
  const cost = state.costMetric || V.METRICS.cost;
  $('costHelp').title = `${cost.definition} ${cost.formula}`;
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

/* High, medium or low, by share of the worst leak in this report. Colour never
   carries it alone: the flag chip next to it says the same thing in words. */
function severity(cost, worst) {
  const share = worst ? cost / worst : 0;
  if (share >= 0.6) return 'high';
  if (share >= 0.25) return 'mid';
  return 'low';
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
          <span class="cost is-${severity(cost, worst)}"><b class="mono">${cost.toFixed(1)}</b>
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

/* ------------------------------------------------------------------ clinic */
/* The queue the clinic walks: the leaks as the table has them ordered, so
   "next" means the next most expensive thing to fix. */
function clinicQueue() {
  return visibleRows().rows;
}

function renderClinic() {
  const queue = clinicQueue();
  const has = queue.length > 0;
  $('clinicHead').hidden = !has;
  $('clinicEmpty').hidden = has;
  $('fixPanel').hidden = !has || state.clinicMode !== 'study';
  $('practiceBody').hidden = !has || state.clinicMode !== 'drill';
  if (!has) return;
  if (!state.selected || !queue.some((r) => S.leakKey(r) === S.leakKey(state.selected))) {
    selectRow(queue[0], { open: false });
  }
  const at = queue.findIndex((r) => S.leakKey(r) === S.leakKey(state.selected));
  $('clinicCount').textContent = `${at + 1} of ${queue.length}`;
  $('clinicPrev').disabled = at <= 0;
  $('clinicNext').disabled = at >= queue.length - 1;
  document.querySelectorAll('#clinicMode .seg').forEach((b) =>
    b.classList.toggle('is-active', b.dataset.mode === state.clinicMode));
  if (state.clinicMode === 'drill' && window.Study) window.Study.drillRow(state.selected);
  renderViewHead();
}

function stepClinic(delta) {
  const queue = clinicQueue();
  const at = queue.findIndex((r) => S.leakKey(r) === S.leakKey(state.selected));
  const next = queue[Math.max(0, Math.min(queue.length - 1, at + delta))];
  if (next) {
    selectRow(next, { open: false });
    renderClinic();
  }
}

/* The dashboard's single call to action. */
function renderTrainCta() {
  const decided = new Set(S.repertoire.all().map((e) => e.key));
  const open = state.rows.filter((r) => !decided.has(S.leakKey(r)));
  $('trainCta').hidden = !state.rows.length;
  if (!state.rows.length) return;
  $('trainCtaText').innerHTML = open.length
    ? `You have <b>${plural(open.length, 'open leak')}</b>. The costliest is `
      + `${esc(open[0].opening || open[0].eco || 'an unclassified line')}.`
    : 'Every leak in this report has an answer. Run again after a few dozen more games.';
  $('trainBtn').textContent = open.length ? 'Start training' : 'Review them again';
  $('trainBtn').onclick = () => {
    const target = open[0] || state.rows[0];
    if (target) selectRow(target, { open: false });
    state.clinicMode = 'study';
    go('clinic');
  };
}

/* ------------------------------------------------------------------ detail */
function cpText(cp) {
  const v = num(cp);
  if (v === null) return '—';
  const pawns = v / 100;
  return (pawns >= 0 ? '+' : '') + pawns.toFixed(2);
}

function selectRow(r, { open = true } = {}) {
  if (!r) return;
  state.selected = r;
  $('posHint').textContent = `${r.eco || '—'} · move ${r.move_number} as ${r.player_color}`;
  $('detailFlag').innerHTML = V.chips(r.flag);
  $('detailOpening').textContent = r.opening || r.eco || 'Unclassified';
  $('detailLine').textContent = r.variation_line;
  state.selectedFen = r.fen;
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
  if (open) {
    state.clinicMode = 'study';
    go('clinic');
  }
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
  renderTrainCta();
  renderNav();
  if (state.view === 'clinic') renderClinic();
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
/* Light is the default. `system` follows the OS; an explicit choice is stamped on
   the root element and remembered, so the tokens are the only thing that changes. */
function applyTheme(choice) {
  const root = document.documentElement;
  if (choice === 'system') root.removeAttribute('data-theme');
  else root.setAttribute('data-theme', choice);
  const dark = choice === 'dark'
    || (choice === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches);
  $('themeBtn').textContent = dark ? 'Light' : 'Dark';
  $('themeBtn').setAttribute('aria-pressed', dark ? 'true' : 'false');
  $('themeBtn').setAttribute('aria-label', dark ? 'Switch to the light theme' : 'Switch to the dark theme');
  document.querySelector('meta[name="theme-color"]').content = dark ? '#1B2430' : '#F8FAFC';
  state.theme = choice;
}

function restoreTheme() {
  applyTheme(S.prefs.get('theme', 'system'));
  $('themeBtn').addEventListener('click', () => {
    const dark = document.documentElement.getAttribute('data-theme') === 'dark'
      || (!document.documentElement.hasAttribute('data-theme')
          && window.matchMedia('(prefers-color-scheme: dark)').matches);
    const next = dark ? 'light' : 'dark';
    S.prefs.set('theme', next);
    applyTheme(next);
  });
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
    if (state.theme === 'system') applyTheme('system');
  });
}

function restoreAdvanced() {
  const box = $('advanced');
  if (!box) return;
  box.open = S.prefs.get('advancedOpen', false) === true;
  box.addEventListener('toggle', () => S.prefs.set('advancedOpen', box.open));
}

/* Accounts, where they touch the run form.

   A run needs somewhere to hang its results, so when this deployment has
   accounts and nobody is signed in, the sign-in card takes the gate and the run
   form waits behind it. A deployment without a database is unchanged: there is
   nothing to sign in to, and refusing to run would help nobody. */
function renderAuthGate() {
  const A = window.Auth;
  const host = $('authGate');
  const form = $('gateSlot');
  if (!A || !host) return;
  A.renderHeader($('headerAccount'));
  const blocked = A.required();
  host.hidden = !blocked;
  if (blocked) A.renderGate(host, '/app/');
  else host.innerHTML = '';
  if (form) form.hidden = blocked;
  // The demo is a canned sample archive, not anybody's games, so it stays open:
  // there is nothing to keep and nothing to sign in for.
  ['runBtn', 'runUploadBtn'].forEach((id) => {
    const btn = $(id);
    if (btn) btn.disabled = blocked;
  });
}

/* Lichess and the magic-link verifier both bounce back here; say so if it failed. */
function reportAuthError(code) {
  if (!code) return;
  const said = code === 'expired'
    ? 'That sign-in link had already been used or had expired. Ask for another one.'
    : `Sign-in did not complete: ${code}`;
  showFetchProblem('Sign-in did not complete', said, '');
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

/* The landing page hands work over in the query string: a username to run, the
   sample archive, or the privacy note. Acted on once, then cleared, so a reload
   does not run it all again. */
function bootFromQuery() {
  const q = new URLSearchParams(location.search);
  if (!q.toString()) return;
  const user = (q.get('user') || '').trim();
  const provider = q.get('provider') === 'chesscom' ? 'chesscom' : 'lichess';
  const wanted = { demo: q.get('demo'), run: q.get('run'), privacy: q.get('privacy'),
    authError: q.get('auth_error') };
  history.replaceState(null, '', location.pathname + location.hash);

  reportAuthError(wanted.authError);
  if (wanted.privacy) openDialog('privacyDialog');
  if (wanted.demo) return runDemo();
  if (!user) return;
  setProvider(provider);
  $('optUser').value = user;
  updateRunLabel();
  if (wanted.run) startRun('username');
  else checkAccount({ quiet: true });
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
  // Straight to the controls that decide how many games a run reads.
  $('shortFix').addEventListener('click', () => {
    mountRunForm('dialogSlot');
    const advanced = $('advanced');
    if (advanced) advanced.open = true;   // the time controls live in there
    openDialog('runDialog');
  });
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
  // Only offered when there is something to go back to, so a failure never
  // silently hands the previous player's report back as if it were this run's.
  $('runErrorBack').addEventListener('click', () => {
    $('runError').hidden = true;
    setAppState('report');
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
  if (window.ResizeObserver) {
    let last = 0;
    new ResizeObserver(() => {
      const w = $('chartWrap').clientWidth;
      if (state.summary && Math.abs(w - last) > 12) {
        last = w;
        renderChart();
      }
    }).observe($('chartWrap'));
  }
  document.querySelectorAll('#chartToggle .seg').forEach((b) =>
    b.addEventListener('click', () => {
      document.querySelectorAll('#chartToggle .seg').forEach((x) => x.classList.remove('is-active'));
      b.classList.add('is-active');
      state.chartKind = b.dataset.chart;
      renderChart();
    }),
  );
  $('clinicPrev').addEventListener('click', () => stepClinic(-1));
  $('clinicNext').addEventListener('click', () => stepClinic(1));
  document.querySelectorAll('#clinicMode .seg').forEach((b) =>
    b.addEventListener('click', () => {
      state.clinicMode = b.dataset.mode;
      renderClinic();
    }),
  );
  $('commitBtn').addEventListener('click', commitSelected);
  $('dismissBtn').addEventListener('click', dismissSelected);
  const copyFen = async (btn, fen) => {
    try {
      await navigator.clipboard.writeText(fen || '');
      btn.textContent = 'Copied';
    } catch {
      btn.textContent = 'Could not copy';
    }
    setTimeout(() => (btn.textContent = 'Copy FEN'), 1500);
  };
  $('libCopyFen').addEventListener('click', () => copyFen($('libCopyFen'), state.libFen));
  $('copyFen').addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(state.selectedFen || '');
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
  $('authDialogClose').addEventListener('click', () => closeDialog('authDialog'));

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

  document.querySelectorAll('.nav-item, .tab-item').forEach((a) =>
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

window.App = {
  go,
  /* study.js asks for the drill tab when "Drill this" is pressed. */
  drill: () => {
    state.clinicMode = 'drill';
    go('clinic');
  },
  reportContext: () => reportContext(),
  select: selectRow,
  /* The board panes report the position they are showing, so "Copy FEN" copies
     what is on the board rather than what the row started on. */
  setFen: (fen) => { state.selectedFen = fen; },
  setLibFen: (fen) => { state.libFen = fen; },
};

// the form is a template so it can be parented into either the empty screen or
// the Run again dialog; materialise it before anything looks its controls up
$('runFormTemplate').replaceWith($('runFormTemplate').content);
mountRunForm('gateSlot');
wire();
restoreTheme();
restoreAdvanced();
if (window.Study) window.Study.init(API);
if (window.Prep) window.Prep.init();
bootAccount();
setAppState('empty');
bootReport();           // a cached run boots straight into `report`
go(location.hash.slice(1) || 'dashboard');
// The session decides whether the run form is usable and what the local copy
// holds, so the gate is drawn as soon as /api/auth/me answers — and again on
// any later change, such as signing out from the account menu.
if (window.Auth) {
  window.Auth.onChange(renderAuthGate);
  window.Auth.boot().then(() => {
    renderAuthGate();
    if (window.Auth.signedIn() && !state.rows.length) bootReport();
  });
}
// `serverless` decides how a run is driven, so the handoff waits for /api/meta
loadMeta().then(bootFromQuery);
