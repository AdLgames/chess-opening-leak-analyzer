/* Small shared navigation; the reading pages do not load chess engines. */
(function () {
  "use strict";
  document.documentElement.classList.add("js");
  const nav = document.getElementById("publicNav");
  const toggle = document.getElementById("navToggle");
  if (!nav || !toggle) return;
  function close() {
    nav.classList.remove("is-open");
    toggle.setAttribute("aria-expanded", "false");
  }
  toggle.addEventListener("click", () => {
    const open = toggle.getAttribute("aria-expanded") !== "true";
    nav.classList.toggle("is-open", open);
    toggle.setAttribute("aria-expanded", String(open));
  });
  nav.addEventListener("click", (event) => {
    if (event.target.closest("a")) close();
  });
  document.addEventListener("keydown", (event) => {
    if (
      event.key === "Escape" &&
      toggle.getAttribute("aria-expanded") === "true"
    ) {
      close();
      toggle.focus();
    }
  });
})();
