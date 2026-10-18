/* A player model built from traceable evidence and optional self-report. */
(function () {
  "use strict";
  const S = window.Store,
    LB = window.LeakBoard,
    $ = (id) => document.getElementById(id),
    esc = LB.esc;
  const root = "learning:v2:decision-lab-v1:";
  const reasons = {
    forgot: "I forgot a line",
    threat: "I missed a threat",
    plan: "I was unsure of the plan",
    clock: "I felt short of time",
    experiment: "I was trying an idea",
    unsure: "I do not remember",
  };
  const goals = {
    plans: "Understand the plans",
    recall: "Remember my opening lines",
    threats: "Notice threats before moving",
    clock: "Make more deliberate decisions",
  };
  let ctx = {},
    rows = [],
    generation = 0;
  const contexts = new Map();
  const sample = () => Boolean(ctx.demo);
  const key = (r) => S.leakKey(r);
  const recordKey = (r) =>
    root +
    "reflection:" +
    btoa(key(r)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "") +
    ":" +
    (sample() ? "sample" : "personal");
  const reflection = (r) => {
    const v = S.prefs.get(recordKey(r));
    return v && !v.deleted ? v : null;
  };
  function saveVersioned(key, value) {
    const updated = Math.max(
      Date.now(),
      Number(S.prefs.get(key)?.updated || 0) + 1,
    );
    return S.prefs.set(key, { ...value, updated });
  }
  const pref = () => S.prefs.get(root + "preferences", {});
  const evidence = (r) =>
    ctx.summary?.decision_evidence?.decisions?.find((d) => d.key === key(r));
  const validNumber = (n) =>
    n !== "" && n !== null && n !== undefined && Number.isFinite(Number(n));
  const count = (n) => Math.max(0, Math.floor(Number(n) || 0));
  const clock = (n) =>
    validNumber(n)
      ? `${Math.floor(Number(n) / 60)}:${String(Math.floor(Number(n) % 60)).padStart(2, "0")}`
      : "not recorded";
  function sourceLabel(source) {
    const label = esc(source.game || "Imported game");
    try {
      const url = new URL(source.game);
      if (
        ["https:", "http:"].includes(url.protocol) &&
        [
          "lichess.org",
          "www.lichess.org",
          "chess.com",
          "www.chess.com",
        ].includes(url.hostname)
      )
        return `<a href="${esc(url.href)}" rel="noopener" target="_blank">${label}</a>`;
    } catch (e) {}
    return `<span>${label}</span>`;
  }
  function stats() {
    const refs = rows.map(reflection).filter(Boolean),
      counts = {};
    refs
      .filter((r) => r.reason)
      .forEach((r) => (counts[r.reason] = (counts[r.reason] || 0) + 1));
    const top = Object.entries(counts).sort((a, b) => b[1] - a[1])[0];
    const decisions = rows.map(evidence).filter(Boolean),
      captures = decisions.filter((d) =>
        d.context.tags.includes("capture-available"),
      ).length;
    const attempts = Object.entries(S.prefs.all()).filter(
      ([k, v]) =>
        /^learning:v2:(italian-v1|caro-v1|qgd-v1|personal-v1):attempt:/.test(
          k,
        ) && v,
    );
    return `${refs.length} of ${rows.length} displayed decisions have your reflection.${top ? " Most recorded: “" + esc(reasons[top[0]] || top[0]) + "” (" + top[1] + ")." : ""}${captures ? " Legal captures were available after " + captures + " displayed decisions; this does not establish the cause of a mistake." : ""}${attempts.length ? " Separately, " + attempts.length + " opening recall attempts are saved; " + attempts.filter(([, v]) => v.outcome === "independent").length + " were independent." : ""}`;
  }
  function render(view = window.App.currentView(), context) {
    if (context) ctx = context;
    const seen = new Set();
    rows = (ctx.rows || [])
      .filter((r) => {
        if (!r.fen || !r.your_move || seen.has(key(r))) return false;
        seen.add(key(r));
        return true;
      })
      .slice(0, 20);
    const focus = $("playerFocus"),
      p = pref(),
      reasonFor = {
        plans: "plan",
        recall: "forgot",
        threats: "threat",
        clock: "clock",
      };
    const next =
        rows.find(
          (r) =>
            reasonFor[p.goal] && reflection(r)?.reason === reasonFor[p.goal],
        ) ||
        rows.find((r) => !reflection(r)) ||
        rows[0],
      nextIndex = rows.indexOf(next);
    focus.hidden = !rows.length && !p.goal;
    focus.innerHTML = `<div><span class="journey-eyebrow">${sample() ? "SAMPLE REVIEW" : "YOUR NEXT FOCUS"}</span><strong>${esc(goals[p.goal] || (rows.length ? "Understand one recurring decision" : "Choose what you want to improve"))}</strong><span>${next ? `Revisit ${esc(next.your_move)} in ${esc(next.opening || next.eco || "this opening")} · ${count(next.your_games)} ${sample() ? "sample " : ""}reported occurrences.${reflection(next)?.reason ? " You recorded: " + esc(reasons[reflection(next).reason] || "a reflection") + "." : ""}` : "Your focus is saved. Add games when you are ready."}</span></div><button class="btn btn-ghost" data-player-focus="${nextIndex}">Review ${next ? "this decision" : "decisions"} →</button>`;
    if (view !== "progress") return;
    generation++;
    $("playerLab").innerHTML =
      `<div class="player-lab-heading"><div><span class="journey-eyebrow">${sample() ? "SAMPLE GAME EVIDENCE" : "YOUR GAME → YOUR NEXT PRACTICE"}</span><h3>Understand the decision.</h3><p>Look at the position. Compare the response. Add what you remember.</p></div><a class="text-link" href="#progress/games">${rows.length ? "Refresh game analysis" : "Bring your games"} →</a></div>
      <form id="decisionPreferences" class="decision-preferences"><label for="decisionGoal">What do you want to improve?<select id="decisionGoal" name="goal"><option value="">Choose a focus</option>${Object.entries(
        goals,
      )
        .map(
          ([k, v]) =>
            `<option value="${k}" ${p.goal === k ? "selected" : ""}>${esc(v)}</option>`,
        )
        .join(
          "",
        )}</select></label><button class="btn btn-ghost" type="submit">Save focus</button><span id="decisionPreferenceStatus" role="status"></span></form>
      <p id="decisionPatternSummary" class="course-note">${stats()}</p>
      ${rows.length ? `<p class="course-note">${sample() ? "These are sample games, not your playing profile." : "Decisions from your latest imported report."} Showing ${rows.length} distinct positions and played moves${(ctx.rows || []).length > rows.length ? " from " + ctx.rows.length + " flagged rows" : ""}. A game can contribute more than one position. Engine estimates, board facts and your reflections remain separate.</p><div class="decision-list">${rows.map((r, i) => `<details class="decision-row" data-decision-row="${i}"><summary><span><strong>${esc(r.opening || r.eco || "Opening decision")}</strong><small>${esc(r.player_color)} · You played ${esc(r.your_move)} · ${count(r.your_games)} reported occurrences${reflection(r) ? " · Reflection saved" : ""}</small></span><span aria-hidden="true">+</span></summary><div class="decision-body" data-decision-body="${i}"></div></details>`).join("")}</div>` : '<p class="player-empty">Your review starts with your games. Connect Lichess or Chess.com, or upload a PGN. You can explore the complete named opening library and practise courses straight away.</p><a class="btn btn-primary" href="#explore/lines">Explore opening routes →</a>'}
      <p class="deep-scope">Recorded context can suggest what to review. It cannot tell us what you were thinking. Clock evidence requires a fresh analysis of PGNs with clock annotations. Older reports can still show legal board facts.</p>`;
  }
  async function contextFor(row) {
    const data = evidence(row);
    if (data?.context) return data.context;
    const id = key(row) + "|" + (row.engine_best_1 || "");
    if (!contexts.has(id))
      contexts.set(
        id,
        LB.decisionContext(row.fen, row.your_move, row.engine_best_1 || ""),
      );
    try {
      return await contexts.get(id);
    } catch (e) {
      contexts.delete(id);
      throw e;
    }
  }
  async function expand(details) {
    if (!details.open) return;
    const i = Number(details.dataset.decisionRow),
      row = rows[i],
      host = details.querySelector(".decision-body"),
      token = generation;
    host.textContent = "Reading the position…";
    try {
      const facts = await contextFor(row);
      if (!host.isConnected || token !== generation) return;
      const e = evidence(row),
        r = reflection(row),
        drop = validNumber(row.eval_drop_pawns)
          ? Number(row.eval_drop_pawns)
          : null;
      host.innerHTML = `<div class="decision-facts"><h4>What the position shows</h4><ul>${facts.facts.map((f) => `<li>${esc(f.text)}</li>`).join("") || "<li>No extra board context is available for this move.</li>"}</ul>${drop !== null ? `<p>The report estimates an evaluation drop of <strong>${drop.toFixed(1)} pawns</strong>. Engine depth and available analysis affect this estimate.</p>` : ""}</div><div class="decision-actions"><button class="btn btn-primary" data-decision-board="${i}">Show decision on board →</button>${row.engine_best_1 && row.engine_best_1 !== row.your_move ? `<button class="btn btn-ghost" data-decision-practice="${i}">Practise the response</button>` : ""}<button class="btn btn-ghost" data-decision-lines="${i}">Explore opening branches</button></div>
      <details class="decision-sources"><summary>Source games & clock evidence</summary>${e?.sources?.length ? `<p>${e.uniqueSourceGames} distinct source games · ${e.sourceDecisions} recorded decisions. ${e.clockSamples ? `${e.under60Seconds}/${e.clockSamples} recorded clocks had under 1 minute remaining after the move; that alone does not show time pressure.` : "No clock annotations for this position."}${e.sourcesTruncated ? " Showing the first 8 source decisions." : ""}</p><ul>${e.sources.map((s) => `<li>${sourceLabel(s)}<span>${esc(s.date || "Date not recorded")} · ply ${count(s.ply)} · clock after: ${clock(s.clockAfter)}${validNumber(s.spent) ? " · spent " + Number(s.spent).toFixed(1) + "s (" + esc(s.spentSource) + ")" : ""}</span></li>`).join("")}</ul>` : "<p>This older report has no detailed source or clock annotations. Run a fresh import for traceable game evidence. Board facts above are calculated from the saved position.</p>"}</details>
      <form class="decision-reflection" data-decision-reflection="${i}"><label for="decisionReason${i}">What do you remember about this decision?<select id="decisionReason${i}" name="reason"><option value="">Optional: choose what fits</option>${Object.entries(
        reasons,
      )
        .map(
          ([k, v]) =>
            `<option value="${k}" ${r?.reason === k ? "selected" : ""}>${esc(v)}</option>`,
        )
        .join(
          "",
        )}</select></label><label for="decisionNote${i}">Your note <span>(optional, 280 characters)</span><textarea id="decisionNote${i}" name="note" maxlength="280" rows="2" placeholder="What will you look for next time?">${esc(r?.note || "")}</textarea></label><div><button class="btn btn-ghost" type="submit">Save reflection</button>${r ? '<button class="btn btn-ghost" type="button" data-decision-clear="' + i + '">Remove reflection</button>' : ""}<span role="status" class="decision-status"></span></div><small>Your reflection is self-reported, not a diagnosis. It is stored with your learning data${sample() ? " separately from personal-game reflections" : ""}.</small></form>`;
    } catch (err) {
      if (host.isConnected && token === generation)
        host.innerHTML = `<p role="alert">${esc(err.message)}</p><button class="btn btn-ghost" data-decision-retry="${i}">Retry position review</button>`;
    }
  }
  document.addEventListener(
    "toggle",
    (e) => {
      if (e.target.matches("[data-decision-row]")) expand(e.target);
    },
    true,
  );
  document.addEventListener("submit", (e) => {
    if (e.target.id === "decisionPreferences") {
      e.preventDefault();
      const goal = e.target.elements.goal.value;
      const ok = saveVersioned(root + "preferences", {
        goal,
      });
      $("decisionPreferenceStatus").textContent = ok
        ? "Focus saved."
        : "Could not save on this device.";
      return;
    }
    if (!e.target.matches("[data-decision-reflection]")) return;
    e.preventDefault();
    const form = e.target,
      row = rows[Number(form.dataset.decisionReflection)],
      reason = form.elements.reason.value,
      note = form.elements.note.value.trim().slice(0, 280);
    if (!reason && !note) {
      form.querySelector("[role=status]").textContent =
        "Choose a reflection or add a note first.";
      return;
    }
    const ok = saveVersioned(recordKey(row), {
      position: key(row),
      reason,
      note,
      sample: sample(),
    });
    form.querySelector("[role=status]").textContent = ok
      ? "Reflection saved."
      : "Could not save on this device.";
    $("decisionPatternSummary").innerHTML = stats();
  });
  document.addEventListener("click", async (e) => {
    const focus = e.target.closest("[data-player-focus]");
    if (focus) {
      const i = Number(focus.dataset.playerFocus);
      window.App.go("progress");
      const details = $("playerLab").querySelector(
        '[data-decision-row="' + i + '"]',
      );
      if (details) {
        details.open = true;
        details.scrollIntoView({ block: "start" });
      }
      return;
    }
    const b = e.target.closest(
      "[data-decision-board],[data-decision-practice],[data-decision-lines],[data-decision-clear],[data-decision-retry]",
    );
    if (!b || b.disabled) return;
    const raw =
        b.dataset.decisionBoard ??
        b.dataset.decisionPractice ??
        b.dataset.decisionLines ??
        b.dataset.decisionClear ??
        b.dataset.decisionRetry,
      i = Number(raw),
      row = rows[i];
    if (!row) return;
    if (b.dataset.decisionRetry !== undefined)
      return expand(b.closest("details[data-decision-row]"));
    if (b.dataset.decisionClear !== undefined) {
      saveVersioned(recordKey(row), {
        position: key(row),
        deleted: true,
      });
      $("decisionPatternSummary").innerHTML = stats();
      return expand(b.closest("details[data-decision-row]"));
    }
    if (b.dataset.decisionLines !== undefined)
      return window.DeepLines.search(
        row.eco || String(row.opening || "").split(":")[0],
      );
    b.disabled = true;
    const origin = window.App.currentView(),
      token = generation;
    try {
      if (b.dataset.decisionPractice !== undefined) {
        await window.Preparation.practice(row, b);
        return;
      }
      const facts = await contextFor(row);
      if (origin !== window.App.currentView() || token !== generation) return;
      await window.Training.pause();
      if (origin !== window.App.currentView() || token !== generation) return;
      const capture = facts.captures[0],
        arrows = capture
          ? [{ from: capture.from, to: capture.to, kind: "played" }]
          : [];
      await window.Study.showFacts(facts.after, {
        orientation: row.player_color,
        arrows,
        circles: capture ? [{ square: capture.square, kind: "played" }] : [],
      });
      if (origin !== window.App.currentView() || token !== generation) return;
      window.App.go("today");
      window.Workspace.custom(
        "After " + row.your_move + " · " + (row.opening || "Your decision"),
        capture
          ? `${capture.san} is a legal capture, shown by the arrow. This is a threat to examine, not a claim that the capture wins material.`
          : "Play continuations, compare the report response, and return to Progress to record what you noticed.",
      );
      window.Workspace.setPanel("moves");
      window.Workspace.explain(
        capture
          ? `Look at ${capture.san}: it legally captures your ${capture.piece} on ${capture.square}. Can you find the continuation? Check it before deciding whether it wins material.`
          : `You played ${row.your_move}. Compare continuations, then record what you noticed in Progress.`,
        key(row),
      );
    } catch (err) {
      const host = b
        .closest(".decision-body")
        ?.querySelector(".decision-status");
      if (host) host.textContent = err.message;
    } finally {
      b.disabled = false;
    }
  });
  window.addEventListener("chess:report", (e) =>
    render(window.App.currentView(), e.detail),
  );
  window.PlayerLab = { render };
})();
