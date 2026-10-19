/* Lazy, complete named-route browsing; observed frequency is separate evidence. */
(function () {
  "use strict";
  const S = window.Store,
    LB = window.LeakBoard,
    $ = (id) => document.getElementById(id),
    esc = LB.esc;
  const root = "learning:v2:opening-lines-v1:bookmark:";
  let indexPromise = null,
    index = null,
    selected = null,
    pageSize = 30,
    filter = null,
    sequence = 0,
    opening = false,
    timer = null,
    playing = false;
  const packs = new Map(),
    forks = new Map();
  let bookMeta = null;
  const normal = (s) =>
    String(s || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .replace(/\d+\.(\.\.)?/g, " ")
      .replace(/[’']/g, "")
      .replace(/\s+/g, " ")
      .trim();
  const moveSearch = (query) =>
    query
      .split(" ")
      .every((word) =>
        /^(?:[kqrbn]?[a-h]?[1-8]?x?[a-h][1-8](?:=[qrbn])?[+#]?|o-o(?:-o)?)$/.test(
          word,
        ),
      );
  const queryMatches = (line, query) =>
    !query ||
    (moveSearch(query)
      ? (" " + normal(line.moves) + " ").includes(" " + query + " ")
      : query
          .split(" ")
          .every((word) =>
            normal(line.name + " " + line.eco + " " + line.moves).includes(
              word,
            ),
          ));
  const familiar = [
    "Italian Game",
    "Sicilian Defense",
    "Caro-Kann Defense",
    "French Defense",
    "Ruy Lopez",
    "Queen's Gambit",
    "King's Indian Defense",
    "English Opening",
  ];
  const familyRank = (line) => {
    const rank = familiar.findIndex((name) => line.name.startsWith(name));
    return rank < 0 ? familiar.length : rank;
  };
  function compareRoutes(a, b) {
    const order = $("deepOrder").value;
    if (order === "depth")
      return (
        b.plies - a.plies ||
        a.eco.localeCompare(b.eco) ||
        a.name.localeCompare(b.name)
      );
    if (order === "familiar")
      return (
        familyRank(a) - familyRank(b) ||
        a.plies - b.plies ||
        a.eco.localeCompare(b.eco) ||
        a.name.localeCompare(b.name)
      );
    return a.eco.localeCompare(b.eco) || a.name.localeCompare(b.name);
  }
  const saved = (id) => {
    const value = S.prefs.get(root + id);
    return value && !value.deleted ? value : null;
  };
  async function read(path) {
    const r = await fetch("/app/opening-lines/" + path);
    if (!r.ok)
      throw new Error(
        "The opening data could not load. Reconnect and try again.",
      );
    return r.json();
  }
  function loadIndex() {
    if (!indexPromise)
      indexPromise = read("index.json")
        .then((d) => {
          index = d;
          return d;
        })
        .catch((e) => {
          indexPromise = null;
          throw e;
        });
    return indexPromise;
  }
  async function pack(eco) {
    if (!packs.has(eco)) packs.set(eco, read(eco + ".json"));
    try {
      return await packs.get(eco);
    } catch (e) {
      packs.delete(eco);
      throw e;
    }
  }
  function shard(fen) {
    let n = 2166136261;
    for (const c of S.positionKey(fen))
      n = Math.imul(n ^ c.charCodeAt(0), 16777619) >>> 0;
    return (n % 64).toString(16).padStart(2, "0");
  }
  async function node(fen) {
    const id = shard(fen);
    if (!forks.has(id)) forks.set(id, read("forks-" + id + ".json"));
    try {
      return (
        (await forks.get(id))[S.positionKey(fen)] || { moves: [], names: [] }
      );
    } catch (e) {
      forks.delete(id);
      throw e;
    }
  }
  const matches = (s) =>
    selected &&
    s &&
    !s.fromFen &&
    s.history.every((m, i) => selected.uci[i] === m.uci) &&
    s.history.length <= selected.uci.length;
  function stop() {
    clearTimeout(timer);
    timer = null;
    playing = false;
  }
  async function toggleBookmark(id) {
    const row = index?.lines.find((l) => l.id === id);
    if (!row) return;
    const updated = Math.max(
      Date.now(),
      Number(S.prefs.get(root + id)?.updated || 0) + 1,
    );
    const durable = S.prefs.set(
      root + id,
      saved(id)
        ? { id, deleted: true, updated }
        : {
            id,
            eco: row.eco,
            name: row.name,
            at: Date.now(),
            updated,
          },
    );
    if (window.App.currentView() === "lines") await catalogue();
    if (!$("branchesPane").hidden) await renderBoard();
    if (!durable) {
      const host =
        window.App.currentView() === "lines"
          ? $("deepCatalogueStatus")
          : $("deepBoardStatus");
      if (host)
        host.textContent =
          "Kept in this tab only. Browser storage is unavailable.";
    }
  }
  async function catalogue() {
    $("deepCatalogueStatus").textContent =
      "Loading the named opening catalogue…";
    try {
      const d = await loadIndex(),
        query = normal($("deepQuery").value),
        first = $("deepFirst").value,
        onlySaved = $("deepSavedOnly").checked;
      const rows = d.lines
        .filter(
          (l) =>
            (!filter || filter.ids.has(l.id)) &&
            (!onlySaved || saved(l.id)) &&
            (!first ||
              (first === "other"
                ? !["e4", "d4", "c4", "Nf3"].includes(l.first)
                : l.first === first)) &&
            queryMatches(l, query),
        )
        .sort(compareRoutes);
      if (window.App.currentView() !== "lines") return;
      $("deepScope").innerHTML =
        `${rows.length.toLocaleString()} matching routes of ${d.count.toLocaleString()} · ${d.ecoCodes} ECO codes${filter ? " · " + esc(filter.title) + ' <button class="text-link" data-deep="clear">Clear position filter</button>' : ""}`;
      $("deepResults").innerHTML = rows.length
        ? `<ol class="deep-route-list">${rows
            .slice(0, pageSize)
            .map(
              (l) =>
                `<li><div><span class="deep-eco">${esc(l.eco)}</span><button class="deep-name" data-deep-line="${l.id}">${esc(l.name)}</button><p class="mono">${esc(l.moves)}</p><small>${Math.ceil(l.plies / 2)} move${l.plies > 2 ? "s" : ""} · reference move order</small></div><div><button class="btn btn-primary" data-deep-line="${l.id}" aria-label="Walk through ${esc(l.name)}">Walk through →</button><button class="btn btn-ghost" data-deep-save="${l.id}" aria-pressed="${!!saved(l.id)}">${saved(l.id) ? "Saved" : "Save route"}</button></div></li>`,
            )
            .join(
              "",
            )}</ol>${rows.length > pageSize ? '<button class="btn btn-ghost" data-deep="more">Show 30 more routes</button>' : ""}`
        : '<p class="deep-empty">No reference route matches. Try a name, ECO code or a shorter move sequence. Every legal move remains available on the board.</p>';
      $("deepCatalogueStatus").textContent = "";
    } catch (e) {
      $("deepCatalogueStatus").textContent = e.message;
      $("deepResults").innerHTML =
        '<button class="btn btn-ghost" data-deep="retry">Try loading the catalogue again</button>';
    }
  }
  async function open(id, at = 0) {
    if (opening) return;
    opening = true;
    stop();
    const origin = window.App.currentView();
    try {
      const d = await loadIndex(),
        meta = d.lines.find((l) => l.id === id);
      if (!meta) throw new Error("This named route is unavailable.");
      const line = (await pack(meta.eco)).lines.find((l) => l.id === id);
      if (!line) throw new Error("This named route is unavailable.");
      if (window.App.currentView() !== origin) return;
      await window.Training.pause();
      if (window.App.currentView() !== origin) return;
      await window.Study.knownLine(
        line.san,
        line.uci,
        Math.max(0, Math.min(line.san.length, at)),
      );
      if (window.App.currentView() !== origin || window.Training.active())
        return;
      selected = line;
      window.App.go("today");
      window.Workspace.custom(
        line.name,
        "A named reference route. Compare alternative replies at every position, then choose what you want to prepare.",
      );
      window.Workspace.setPanel("branches");
      await renderBoard();
    } catch (e) {
      const host =
        window.App.currentView() === "lines"
          ? $("deepCatalogueStatus")
          : $("exploreError");
      host.hidden = false;
      host.textContent = e.message;
    } finally {
      opening = false;
    }
  }
  async function jump(at) {
    const s = window.Study.snapshot();
    if (!matches(s) || s.busy) return;
    try {
      await window.Study.knownLine(
        selected.san,
        selected.uci,
        Math.max(0, Math.min(selected.san.length, at)),
      );
    } catch (e) {
      stop();
      if ($("deepBoardStatus")) $("deepBoardStatus").textContent = e.message;
    }
  }
  async function play(uci) {
    stop();
    try {
      await window.Study.playMove(uci);
    } catch (e) {
      if ($("deepBoardStatus")) $("deepBoardStatus").textContent = e.message;
    }
  }
  async function tick() {
    if (
      !playing ||
      document.hidden ||
      window.App.currentView() !== "today" ||
      window.Training.active()
    ) {
      stop();
      return;
    }
    const s = window.Study.snapshot();
    if (!matches(s) || s.history.length >= selected.san.length) {
      stop();
      renderBoard();
      return;
    }
    if (!s.busy) await jump(s.history.length + 1);
    if (playing) timer = setTimeout(tick, 1600);
  }
  async function renderBoard() {
    if ($("branchesPane").hidden || window.Training.active()) return;
    const snap = window.Study.snapshot();
    if (!snap?.pos) return;
    const token = ++sequence;
    $("deepBoardPanel").setAttribute("aria-busy", "true");
    try {
      const [d, n] = await Promise.all([loadIndex(), node(snap.pos.fen)]);
      if (
        token !== sequence ||
        $("branchesPane").hidden ||
        window.Training.active()
      )
        return;
      const inLine = matches(snap),
        ply = snap.history.length,
        book = snap.pos.book,
        byUci = new Map((book?.moves || []).map((m) => [m.uci, m]));
      const legal = [...snap.pos.legal].sort(
        (a, b) =>
          (byUci.get(b.uci)?.games || 0) - (byUci.get(a.uci)?.games || 0) ||
          a.san.localeCompare(b.san),
      );
      const most = book?.moves?.[0]?.games || 0;
      const reference = n.moves.filter((m) =>
        snap.pos.legal.some((l) => l.uci === m.uci),
      );
      const statsNote = book?.total
        ? `${book.total.toLocaleString()} games at this position. Most played means frequency in this sample, not best play.`
        : "No sample games at this position. Named reference moves and legal continuations are still available.";
      const row = (m) => {
        const observed = byUci.get(m.uci),
          named = reference.find((x) => x.uci === m.uci);
        return `<li><button data-deep-play="${m.uci}"><b>${esc(m.san)}</b><span>${observed?.games ? `${observed.games.toLocaleString()} games · ${observed.share}%` : "No sample games"}</span><small>${observed?.games === most && most ? "Most played in sample" : observed?.games ? "Alternative in sample" : "Legal continuation"}</small></button>${named ? `<button class="deep-named" data-deep-fork="${m.uci}">${named.routes.length} named ${named.routes.length === 1 ? "route" : "routes"} →</button>` : ""}</li>`;
      };
      const primary = legal.filter(
          (m) =>
            byUci.get(m.uci)?.games || reference.some((r) => r.uci === m.uci),
        ),
        other = legal.filter((m) => !primary.includes(m));
      $("deepBoardPanel").innerHTML =
        `<div class="deep-panel-heading"><span class="journey-eyebrow">OPENING RUNTHROUGH</span><a class="text-link" href="#explore/lines">All named routes →</a></div><h3>${selected ? esc(selected.name) : "Choose a reply. Follow an idea."}</h3>${selected ? `<p>${inLine ? `Step ${ply} of ${selected.san.length} in the reference route` : "You are exploring your own continuation."} · ${esc(selected.eco)}</p><div class="deep-walk-controls"><button class="btn btn-ghost" data-deep="back" ${!inLine || !ply ? "disabled" : ""}>← Back</button><button class="btn btn-primary" data-deep="next" ${!inLine || ply >= selected.san.length ? "disabled" : ""}>Next move →</button><button class="btn btn-ghost" data-deep="autoplay" ${!inLine || ply >= selected.san.length ? "disabled" : ""}>${playing ? "Pause runthrough" : "Play through"}</button><button class="btn btn-ghost" data-deep="restart">Reference start</button><button class="btn btn-ghost" data-deep-save="${selected.id}" aria-pressed="${!!saved(selected.id)}">${saved(selected.id) ? "Route saved" : "Save route"}</button></div><details class="deep-move-order"><summary>Full reference move order</summary><div>${selected.san.map((san, i) => `<button class="${inLine && ply === i + 1 ? "is-current" : ""}" data-deep-ply="${i + 1}">${i % 2 ? "" : `${i / 2 + 1}. `}${esc(san)}</button>`).join("")}</div></details>` : "<p>Search the full catalogue, or play any legal reply below.</p>"}<h4>Main choices and alternatives</h4><p class="course-note">${esc(statsNote)}</p><ul class="deep-replies">${primary.map(row).join("")}</ul>${other.length ? `<details><summary>Other legal replies (${other.length})</summary><ul class="deep-replies">${other.map(row).join("")}</ul></details>` : ""}<p id="deepBoardStatus" role="status"></p><p class="deep-scope">${bookMeta ? esc(bookMeta) : "Game statistics use the installed book; named routes are a separate CC0 reference catalogue."} A line ending here is the end of that reference entry, not the end of opening theory.</p>`;
      $("deepBoardPanel").setAttribute("aria-busy", "false");
      if (!bookMeta)
        LB.meta()
          .then((meta) => {
            const db = meta.database;
            if (db?.available)
              bookMeta = `Book sample: ${Number(db.games).toLocaleString()} games · ${db.filters}.`;
          })
          .catch(() => {});
    } catch (e) {
      if (token === sequence) {
        $("deepBoardPanel").innerHTML =
          `<p role="alert">${esc(e.message)}</p><button class="btn btn-ghost" data-deep="board-retry">Retry opening replies</button>`;
        $("deepBoardPanel").setAttribute("aria-busy", "false");
      }
    }
  }
  function render(view = window.App.currentView()) {
    if (view !== "today") stop();
    if (view === "lines") catalogue();
    if (view === "today" && !$("branchesPane").hidden) renderBoard();
  }
  document.addEventListener("click", (e) => {
    const b = e.target.closest(
      "[data-deep],[data-deep-line],[data-deep-save],[data-deep-play],[data-deep-fork],[data-deep-ply]",
    );
    if (!b || b.disabled) return;
    if (b.dataset.deepLine) return open(b.dataset.deepLine);
    if (b.dataset.deepSave) return toggleBookmark(b.dataset.deepSave);
    if (b.dataset.deepPlay) return play(b.dataset.deepPlay);
    if (b.dataset.deepPly) {
      stop();
      return jump(Number(b.dataset.deepPly));
    }
    if (b.dataset.deepFork) {
      stop();
      const s = window.Study.snapshot(),
        token = sequence;
      node(s.pos.fen)
        .then((n) => {
          if (
            token !== sequence ||
            window.App.currentView() !== "today" ||
            window.Training.active()
          )
            return;
          const fork = n.moves.find((m) => m.uci === b.dataset.deepFork);
          if (fork) {
            filter = {
              ids: new Set(fork.routes),
              title: "Named routes through " + fork.san,
            };
            pageSize = 30;
            $("deepQuery").value = "";
            $("deepFirst").value = "";
            $("deepSavedOnly").checked = false;
            window.App.go("lines");
          }
        })
        .catch((e) => {
          if (token === sequence && $("deepBoardStatus"))
            $("deepBoardStatus").textContent = e.message;
        });
      return;
    }
    const a = b.dataset.deep;
    if (a === "more") {
      pageSize += 30;
      catalogue();
    }
    if (a === "clear") {
      filter = null;
      pageSize = 30;
      catalogue();
    }
    if (a === "retry") catalogue();
    if (a === "board-retry") renderBoard();
    if (a === "back") {
      stop();
      jump(window.Study.snapshot().history.length - 1);
    }
    if (a === "next") {
      stop();
      jump(window.Study.snapshot().history.length + 1);
    }
    if (a === "restart") {
      stop();
      open(selected.id);
    }
    if (a === "autoplay") {
      if (playing) {
        stop();
        renderBoard();
      } else {
        playing = true;
        tick();
      }
    }
  });
  $("deepSearchForm").addEventListener("submit", (e) => {
    e.preventDefault();
    pageSize = 30;
    catalogue();
  });
  let debounce;
  $("deepQuery").addEventListener("input", () => {
    clearTimeout(debounce);
    debounce = setTimeout(() => {
      pageSize = 30;
      catalogue();
    }, 180);
  });
  for (const id of ["deepFirst", "deepOrder", "deepSavedOnly"])
    $(id).addEventListener("change", () => {
      pageSize = 30;
      catalogue();
    });
  window.addEventListener("chess:position", () => {
    if (playing && !matches(window.Study.snapshot())) stop();
    if (!$("branchesPane").hidden) renderBoard();
  });
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      stop();
      if (!$("branchesPane").hidden) renderBoard();
    }
  });
  window.DeepLines = {
    render,
    open,
    stop,
    loadIndex,
    search(query) {
      filter = null;
      pageSize = 30;
      $("deepQuery").value = query || "";
      $("deepFirst").value = "";
      $("deepSavedOnly").checked = false;
      window.App.go("lines");
    },
    info: () => (selected ? JSON.parse(JSON.stringify(selected)) : null),
  };
})();
