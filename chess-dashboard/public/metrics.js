/* Optional, explicitly allowed, coarse usage counts. Never pass user content. */
(function () {
  "use strict";
  const key = "leaklab:measurement";
  const domain = window.LeakSiteConfig?.analyticsDomain;
  const configured = domain === "chessleaklab.co.uk";
  const production = ["chessleaklab.co.uk", "www.chessleaklab.co.uk"].includes(
    location.hostname,
  );
  const blocked = () =>
    navigator.globalPrivacyControl === true || navigator.doNotTrack === "1";
  let choice = "deny";
  try {
    choice = localStorage.getItem(key) || "deny";
  } catch (_) {
    /* page-only choice */
  }
  const seen = new Set();
  const events = new Set([
    "pageview",
    "Preview started",
    "Preview completed",
    "Course opened",
    "Training started",
    "Training completed",
    "Daily completed",
  ]);
  const courses = new Set(["italian", "caro", "queens", "personal"]);
  const modes = new Set(["learn", "recall", "play", "game"]);
  const surfaces = new Set(["home", "course", "guide", "workspace"]);
  function publicPath() {
    const path = location.pathname;
    if (path === "/app/" || path === "/app/index.html") return "/app/";
    if (
      /^\/(learn|guides|coaches|about|contact|privacy|openings)\/(?:[a-z0-9-]+\/)?$/.test(
        path,
      )
    )
      return path;
    return "/";
  }
  function track(name, props = {}, once = "") {
    if (!events.has(name)) return;
    if (once && seen.has(name + ":" + once)) return;
    if (once) seen.add(name + ":" + once);
    const safe = {};
    if (courses.has(props.course)) safe.course = props.course;
    if (modes.has(props.mode)) safe.mode = props.mode;
    if (surfaces.has(props.surface)) safe.surface = props.surface;
    const event = { name, props: safe, path: publicPath() };
    window.dispatchEvent(new CustomEvent("leaklab:metric", { detail: event }));
    if (!configured || !production || blocked() || choice !== "allow") return;
    fetch("https://plausible.io/api/event", {
      method: "POST",
      credentials: "omit",
      referrerPolicy: "no-referrer",
      keepalive: true,
      headers: { "Content-Type": "text/plain" },
      body: JSON.stringify({
        name,
        domain,
        url: "https://chessleaklab.co.uk" + event.path,
        props: safe,
      }),
    }).catch(() => {});
  }
  function render() {
    const controls = document.getElementById("measurementControls");
    if (!controls) return;
    controls.hidden = !configured;
    document.getElementById("measurementDescription").textContent = configured
      ? "You can allow optional Plausible usage counts to help improve the lessons. They are off until you choose to allow them. Learning works either way."
      : "Optional usage counts are not currently enabled on this site. Learning does not require analytics.";
    document.getElementById("measurementStatus").textContent = blocked()
      ? "Usage counts are off because your browser requests privacy protection."
      : choice === "allow"
        ? "You allow optional usage counts. You can turn them off here."
        : "Optional usage counts are off.";
  }
  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-measurement]");
    if (!button || !configured) return;
    choice = button.dataset.measurement === "allow" ? "allow" : "deny";
    try {
      localStorage.setItem(key, choice);
    } catch (_) {
      /* page-only choice */
    }
    render();
    if (choice === "allow") track("pageview");
  });
  window.addEventListener("storage", (event) => {
    if (event.key === key) {
      choice = event.newValue || "deny";
      render();
    }
  });
  window.LeakMetrics = { track };
  render();
  track("pageview");
})();
