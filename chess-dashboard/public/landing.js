/* Opening Leak Lab — the landing page's only behaviour.

   Two jobs: remember which site the visitor plays on, and hand the username to
   the app at /app/ so the run starts on arrival rather than asking for it a
   second time. Everything else on this page is static. */
(function () {
  'use strict';

  const $ = (id) => document.getElementById(id);
  const form = $('start');
  const input = $('user');
  const platform = $('platform');
  let provider = 'lichess';

  /* --------------------------------------------------------- where you play */
  function setProvider(next) {
    provider = next;
    platform.querySelectorAll('button').forEach((b) => {
      b.setAttribute('aria-pressed', b.dataset.provider === next ? 'true' : 'false');
    });
    input.placeholder = next === 'chesscom' ? 'your Chess.com username' : 'your username';
    try {
      localStorage.setItem('leaklab:pref:landingProvider', JSON.stringify(next));
    } catch (err) {
      /* a private window is not a reason to fail */
    }
  }

  platform.querySelectorAll('button').forEach((b) =>
    b.addEventListener('click', () => {
      setProvider(b.dataset.provider);
      input.focus();
    }),
  );

  try {
    const saved = JSON.parse(localStorage.getItem('leaklab:pref:landingProvider') || '""');
    if (saved === 'chesscom' || saved === 'lichess') setProvider(saved);
  } catch (err) {
    /* ignore */
  }

  /* ------------------------------------------------------- into the report */
  form.addEventListener('submit', (event) => {
    event.preventDefault();
    const user = input.value.trim();
    if (!user) {
      input.focus();
      return;
    }
    const params = new URLSearchParams({ provider, user, run: '1' });
    location.href = `/app/?${params}`;
  });

  /* Say what the run will actually read, rather than a number that might not be
     this deployment's. The hosted function caps games per run; the local build
     does not, and reports no limits at all. */
  fetch('/api/meta')
    .then((res) => (res.ok ? res.json() : null))
    .then((meta) => {
      const cap = meta && meta.limits && meta.limits.max_fetch_games;
      if (!cap) return;
      const note = $('startNote');
      note.firstChild.textContent =
        `Free · runs on your last ${cap} games · sign in to keep your progress · `;
    })
    .catch(() => {
      /* the page is worth reading with or without the backend */
    });
})();
