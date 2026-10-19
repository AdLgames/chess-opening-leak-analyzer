/* The invitation leads into existing account/import tools; it never starts a run. */
(function () {
  "use strict";
  const $ = (id) => document.getElementById(id),
    esc = window.LeakBoard.esc;
  const arrow =
    '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M5 12h14m-6-6 6 6-6 6"/></svg>';
  function render(view = window.App?.currentView()) {
    const host = $("accountInvite"),
      auth = window.Auth?.state;
    const imported =
      window.Store.runs.all().some((run) => !run.demo) ||
      (window.App?.reportContext()?.summary &&
        !window.App.reportContext().demo);
    host.hidden =
      !auth?.ready ||
      imported ||
      !["today", "explore", "repertoire", "progress", "path", "games"].includes(
        view,
      ) ||
      !!window.Training?.active();
    if (host.hidden) return;
    const title = auth.user
      ? "Your games have a story. Let’s find the next idea."
      : "Your next good move starts with your games.";
    const canJoin =
      auth.enabled && (auth.methods.email || auth.methods.lichess);
    host.innerHTML = `<div class="connect-banner-art" data-coach="maya" aria-hidden="true"><span class="companion-art"></span></div><div class="connect-banner-copy"><span class="connect-eyebrow">YOUR GAMES. YOUR CHESS CORNER.</span><h2 id="connectBannerTitle">${title}</h2><p>Bring your Lichess or Chess.com games, spot the opening decisions worth a second look, and turn a finding into practice.</p><div class="connect-actions"><button type="button" class="connect-primary" data-connect-provider="lichess">Bring my Lichess games ${arrow}</button><button type="button" class="connect-secondary" data-connect-provider="chesscom">Bring my Chess.com games ${arrow}</button></div><p class="connect-small">${canJoin && !auth.user ? '<button type="button" data-join-account>Create an account or sign in</button> to keep your learning across devices.' : auth.user ? "Your account is ready. You choose the games and settings before analysis." : "Explore and learn without an account. Device storage keeps your local progress."}</p><p class="connect-provider-note">Lichess supports sign-in · Chess.com imports use your public username · No chess-site password needed</p></div>`;
    const target = $("view" + view[0].toUpperCase() + view.slice(1));
    if (view === "today") target.insertBefore(host, $("todayJourney"));
    else if (view === "progress")
      target.insertBefore(host, $("progressEvidence"));
    else target.appendChild(host);
  }
  function renderImport(provider) {
    const host = $("importWelcome"),
      auth = window.Auth.state,
      label = provider === "chesscom" ? "Chess.com" : "Lichess";
    host.hidden = false;
    const accountNote = auth.user
      ? "Your account is ready to keep the results."
      : auth.enabled
        ? "Create an Opening Leak Lab account or sign in using the options below."
        : "This deployment keeps progress on your device.";
    host.innerHTML = `<div class="import-welcome-top"><div><span class="connect-eyebrow">BRING YOUR CHESS LIFE TOGETHER</span><h2 id="importWelcomeTitle">Let’s bring in your ${label} games.</h2><p>${provider === "chesscom" ? "We read public games by Chess.com username." : "Choose public games by Lichess username; Lichess sign-in can also fill it for you."} ${accountNote}</p></div><a class="btn btn-ghost" href="#explore">Keep exploring →</a></div><ol class="import-steps" aria-label="Import steps"><li class="${auth.user || !auth.enabled ? "is-done" : "is-current"}"><span>${auth.user ? "✓" : "1"}</span>${auth.enabled ? "Your account" : "Local workspace"}</li><li class="${auth.user || !auth.enabled ? "is-current" : ""}"><span>2</span>Choose your games</li><li><span>3</span>Choose your practice</li></ol><div class="import-providers" aria-label="Game provider"><button class="btn btn-ghost" type="button" data-connect-provider="lichess" aria-pressed="${provider === "lichess"}">Lichess</button><button class="btn btn-ghost" type="button" data-connect-provider="chesscom" aria-pressed="${provider === "chesscom"}">Chess.com</button><span>Review the settings below. Analysis starts when you choose.</span></div>`;
  }
  document.addEventListener("click", (event) => {
    const connect = event.target.closest("[data-connect-provider]");
    if (connect) {
      if ($("sidebar").classList.contains("is-open")) $("drawerClose").click();
      document
        .querySelectorAll("details.menu[open]")
        .forEach((menu) => (menu.open = false));
      window.App.openImport(connect.dataset.connectProvider);
    }
    if (event.target.closest("[data-join-account]"))
      window.Auth.openSignIn({ purpose: "account" });
  });
  document.addEventListener(
    "click",
    (event) => {
      if (document.querySelector("dialog[open]")) return;
      document.querySelectorAll("details.menu[open]").forEach((menu) => {
        if (!menu.contains(event.target)) menu.open = false;
      });
    },
    true,
  );
  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape" || document.querySelector("dialog[open]"))
      return;
    const open = Array.from(document.querySelectorAll("details.menu[open]")).at(
      -1,
    );
    if (open) {
      open.open = false;
      open.querySelector("summary").focus();
    }
  });
  window.Clubhouse = { render, renderImport };
})();
