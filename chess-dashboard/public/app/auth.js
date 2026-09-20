/* Opening Leak Lab — accounts.

   The analyser was stateless, and a stateless analyser can tell you what is
   leaking today but never whether you fixed it. An account is what turns a
   report into progress: the same leak key, run after run, with a lifecycle.

   Two ways in, for a reason. Lichess players get OAuth, because Lichess issues
   public clients a PKCE flow and one tap is the whole ceremony. Chess.com has
   no public OAuth at all, so its players get a single-use emailed link. No
   passwords are stored by this app either way.

   This module owns the session, the sign-in UI, and the mirror from the
   browser's working copy (Store) to the server. Everything the rest of the app
   reads still comes from Store — sign-in changes where that data is *kept*,
   not where the views read it from. */
(function () {
  'use strict';

  const S = window.Store;
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  const state = {
    ready: false,      // /api/auth/me has answered
    enabled: false,    // this deployment has a database behind it
    user: null,
    methods: { lichess: false, email: false },
    busy: false,
  };
  const listeners = [];

  async function api(path, options) {
    const res = await fetch(path, { credentials: 'same-origin', ...options });
    const text = await res.text();
    let body = null;
    try {
      body = text ? JSON.parse(text) : null;
    } catch (err) {
      body = null;
    }
    if (!res.ok) {
      const detail = (body && (body.detail || body.error)) || text || `HTTP ${res.status}`;
      const error = new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
      error.status = res.status;
      throw error;
    }
    return body;
  }

  function emit() {
    listeners.forEach((fn) => {
      try {
        fn(state);
      } catch (err) {
        /* one bad listener must not stop the others */
      }
    });
  }

  /* -------------------------------------------------------------- the mirror */
  /* Each local write is echoed to the server. Failures are swallowed on purpose:
     the write already happened locally, and losing a sync is not losing data —
     the next successful run re-sends the lot. */
  function leakRows() {
    const report = S.lastReport.load();
    const rows = (report && report.rows) || [];
    return rows.map((r) => ({
      key: S.leakKey(r),
      position: S.positionKey(r.fen),
      fen: r.fen,
      color: r.player_color,
      eco: r.eco || '',
      opening: r.opening || '',
      played: r.your_move || '',
      moveNumber: Number(r.move_number) || 0,
      cost: Number(r.cost) || 0,
      games: Number(r.your_games) || 0,
      flag: r.flag || '',
    }));
  }

  const SINKS = {
    repertoire: (entry) => api('/api/state/repertoire', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ entry }),
    }),
    'repertoire:remove': (payload) => api('/api/state/repertoire/remove', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
    drill: (payload) => api('/api/state/drill', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
    pref: (payload) => api('/api/state/pref', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
    // A run is the moment every leak's status moves, so it carries the findings
    // and the report with it. `applyReport` has already saved the report locally
    // by the time the run is recorded, so the rows are there to read.
    run: (entry) => api('/api/state/run', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ run: entry, leaks: leakRows(), report: S.lastReport.load() }),
    }),
  };

  function connect() {
    S.connect((kind, payload) => {
      const send = SINKS[kind];
      if (send) send(payload).catch(() => {});
    });
  }

  /* ------------------------------------------------------------ session boot */
  async function pull() {
    const remote = await api('/api/state');
    const local = S.snapshot();
    const empty = !remote.runs.length && !remote.repertoire.length
      && !Object.keys(remote.drills).length;
    const haveLocal = local.runs.length || local.repertoire.length
      || Object.keys(local.drills).length;
    // People used this app before it had accounts. Signing in must look like
    // picking their work up, not like starting over, so a first sign-in adopts
    // whatever the browser was already holding.
    if (empty && haveLocal) {
      S.adopt(await api('/api/state/import', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(local),
      }));
    } else {
      S.adopt(remote);
    }
    state.progress = remote.progress || null;
  }

  async function boot() {
    let me = null;
    try {
      me = await api('/api/auth/me');
    } catch (err) {
      state.ready = true;          // no accounts endpoint: an older deployment
      emit();
      return state;
    }
    state.enabled = Boolean(me && me.database);
    state.methods = (me && me.methods) || state.methods;
    state.user = (me && me.user) || null;
    if (state.user) {
      connect();
      try {
        await pull();
      } catch (err) {
        /* offline, or the state endpoint is unhappy: the local copy still works */
      }
    }
    state.ready = true;
    emit();
    return state;
  }

  /* ------------------------------------------------------------------- views */
  function methodMarkup(redirect) {
    const parts = [];
    if (state.methods.lichess) {
      parts.push(
        `<a class="btn btn-primary auth-lichess" href="/api/auth/lichess/start?redirect=${encodeURIComponent(redirect)}">`
        + 'Continue with Lichess</a>');
    }
    if (state.methods.email) {
      parts.push(
        '<form class="auth-email" id="authEmailForm">'
        + '<label class="field"><span>Email</span>'
        + '<input type="email" id="authEmail" placeholder="you@example.com" autocomplete="email" required />'
        + '</label>'
        + '<button class="btn" type="submit" id="authEmailBtn">Email me a sign-in link</button>'
        + '</form>');
    }
    if (!parts.length) {
      parts.push('<p class="muted small">Sign-in is not configured on this deployment.</p>');
    }
    return parts.join(state.methods.lichess && state.methods.email
      ? '<p class="auth-or"><span>or</span></p>' : '');
  }

  function wireEmailForm(scope) {
    const form = scope.querySelector('#authEmailForm');
    if (!form) return;
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      if (state.busy) return;
      const input = form.querySelector('#authEmail');
      const button = form.querySelector('#authEmailBtn');
      const note = document.createElement('p');
      note.className = 'small';
      state.busy = true;
      button.disabled = true;
      button.textContent = 'Sending…';
      try {
        const out = await api('/api/auth/email/request', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: input.value.trim(), redirect: '/app/' }),
        });
        note.className = 'small ok';
        note.innerHTML = out && out.link
          // preview deployments with no mail provider show the link instead
          ? `Mail is not configured here, so use this link: <a href="${esc(out.link)}">sign in</a>.`
          : 'Check your email — the link works once and lasts 20 minutes.';
      } catch (err) {
        note.className = 'small bad';
        note.textContent = err.message;
      } finally {
        state.busy = false;
        button.disabled = false;
        button.textContent = 'Email me a sign-in link';
        const old = form.parentNode.querySelector('.auth-note');
        if (old) old.remove();
        note.classList.add('auth-note');
        form.parentNode.appendChild(note);
      }
    });
  }

  /** The sign-in card that stands where the run form would be. */
  function renderGate(host, redirect = '/app/') {
    host.innerHTML =
      '<div class="auth-card">'
      + '<h3>Sign in to run an analysis</h3>'
      + '<p class="muted small">Your leaks are tracked across runs, so the next report can '
      + 'tell you which ones you actually fixed. No password — and you can export or '
      + 'delete everything at any time.</p>'
      + methodMarkup(redirect)
      // Requiring an account costs the try-before-you-sign-up path, so the one
      // thing that needs no account stays one click away: the sample archive is
      // nobody's games, so there is nothing to keep and nothing to sign in for.
      + '<p class="auth-demo small"><a href="/app/?demo=1">Or look around a finished '
      + 'report on the sample archive</a> — no account needed.</p>'
      + '</div>';
    wireEmailForm(host);
  }

  function renderHeader(host) {
    if (!state.enabled) {
      host.hidden = true;
      return;
    }
    host.hidden = false;
    if (!state.user) {
      host.innerHTML = '<button class="btn btn-ghost" id="signInBtn">Sign in</button>';
      host.querySelector('#signInBtn').addEventListener('click', () => openSignIn());
      return;
    }
    const who = state.user.name || state.user.email || 'Account';
    const lichess = (state.user.accounts || []).find((a) => a.provider === 'lichess');
    host.innerHTML =
      '<details class="menu" id="accountMenu">'
      + `<summary class="btn btn-ghost">${esc(who)}</summary>`
      + '<div class="menu-body">'
      + `<p class="menu-note">${esc(state.user.email || (lichess ? `Lichess · ${lichess.username}` : ''))}</p>`
      + '<a class="menu-item" href="/api/auth/export">Download my data</a>'
      + '<button class="menu-item" id="signOutBtn">Sign out</button>'
      + '<button class="menu-item is-danger" id="deleteAccountBtn">Delete my account</button>'
      + '</div></details>';
    host.querySelector('#signOutBtn').addEventListener('click', signOut);
    host.querySelector('#deleteAccountBtn').addEventListener('click', deleteAccount);
  }

  function openSignIn() {
    const dialog = $('authDialog');
    if (!dialog) return;
    renderGate($('authDialogBody'), location.pathname + location.hash);
    if (typeof dialog.showModal === 'function') dialog.showModal();
    else dialog.setAttribute('open', '');
  }

  async function signOut() {
    try {
      await api('/api/auth/logout', { method: 'POST' });
    } catch (err) {
      /* the cookie is gone either way as far as this page is concerned */
    }
    S.disconnect();
    // The working copy belongs to the account that just left this browser.
    S.forget();
    state.user = null;
    emit();
    location.assign('/app/');
  }

  async function deleteAccount() {
    const typed = window.prompt(
      'This erases your account and every run, leak, repertoire decision and drill '
      + 'attempt on the server. It cannot be undone.\n\nType DELETE to confirm:');
    if (!typed || typed.trim().toUpperCase() !== 'DELETE') return;
    try {
      await api('/api/auth/delete', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confirm: 'DELETE' }),
      });
    } catch (err) {
      window.alert(`Could not delete the account: ${err.message}`);
      return;
    }
    S.disconnect();
    S.forget();
    state.user = null;
    emit();
    location.assign('/?deleted=1');
  }

  window.Auth = {
    boot,
    state,
    signedIn: () => Boolean(state.user),
    required: () => state.enabled && !state.user,
    renderGate,
    renderHeader,
    openSignIn,
    signOut,
    onChange: (fn) => { listeners.push(fn); },
  };
})();
