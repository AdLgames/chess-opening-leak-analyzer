/* A resumable daily plan orchestrates existing course checkpoints.
   It never awards a result itself: the existing lesson/recall/play flows do that. */
(function () {
  "use strict";
  const S = window.Store;
  const L = window.LearningStore.forCourse("daily-v1");
  const esc = window.LeakBoard.esc;
  const $ = (id) => document.getElementById(id);
  const catalog = () =>
    [...window.OpeningCourses, window.Preparation?.personalCourse()].filter(
      Boolean,
    );
  const storeFor = (course) => window.LearningStore.forCourse(course);
  const record = (id) => L.checkpoints().find((p) => p.id === id);
  const pending = () => L.session();
  const snapshot = (task) =>
    storeFor(task.course)
      .checkpoints()
      .find((c) => c.id === task.sessionId);
  const safeMinutes = (n) => ([5, 10, 15].includes(Number(n)) ? Number(n) : 5);
  const phase = (task) =>
    task.mode === "recall"
      ? "Review"
      : task.mode === "learn"
        ? task.refresher
          ? "Revisit an idea"
          : "New idea"
        : "Practical challenge";
  function focusCourse() {
    const preferred = S.prefs.get("dailyFocus", null);
    const learned = window.OpeningCourses.filter(
      (c) => storeFor(c.id).summary(c.cards).schedules.length,
    );
    return (
      window.OpeningCourses.find((c) => c.id === preferred) ||
      learned[0] ||
      window.OpeningCourses[0]
    );
  }
  function build(
    minutes = safeMinutes(S.prefs.get("dailyMinutes", 5)),
    now = Date.now(),
  ) {
    minutes = safeMinutes(minutes);
    const focus = focusCourse();
    const cap = minutes === 5 ? 3 : minutes === 10 ? 6 : 10;
    const due = catalog()
      .flatMap((c) =>
        storeFor(c.id)
          .summary(c.cards, now)
          .due.map((d) => ({ ...d, course: c.id })),
      )
      .sort((a, b) => a.due - b.due || a.course.localeCompare(b.course))
      .slice(0, cap);
    const groups = new Map();
    due.forEach((d) => {
      if (!groups.has(d.course)) groups.set(d.course, []);
      groups.get(d.course).push(d.card);
    });
    const steps = [...groups].map(([course, queue]) => ({
      course,
      queue,
      mode: "recall",
    }));
    const count = minutes === 5 ? 1 : minutes === 10 ? 2 : 3;
    const unseen = focus.cards.filter(
      (c) => !storeFor(focus.id).schedule(c.id),
    );
    const chosen = (unseen.length ? unseen : focus.cards).slice(0, count);
    const sourceChapter = focus.chapters.find((ch) =>
      ch.cards.includes(chosen[0].id),
    ).id;
    steps.push({
      course: focus.id,
      queue: chosen.map((c) => c.id),
      mode: "learn",
      sourceChapter,
      refresher: !unseen.length,
    });
    steps.push({
      course: focus.id,
      queue: [chosen.at(-1).id],
      mode: "play",
      practiceCardId: chosen.at(-1).id,
      sourceChapter: focus.chapters.find((ch) =>
        ch.cards.includes(chosen.at(-1).id),
      ).id,
    });
    return {
      minutes,
      focus: focus.id,
      steps,
      reviews: due.length,
      newPositions: unseen.length ? chosen.length : 0,
      refresher: !unseen.length,
    };
  }
  function save(plan) {
    L.saveSession(plan);
  }
  function render() {
    const host = $("dailyInvite");
    if (!host) return;
    const focused = host.contains(document.activeElement)
      ? document.activeElement.id
      : null;
    host.hidden = !!window.Training?.active();
    document.documentElement.classList.toggle(
      "has-daily-invite",
      !host.hidden && window.App?.currentView() === "today",
    );
    if (host.hidden) return;
    const plan = pending();
    const draft = build();
    const latest = L.checkpoints().find((p) => p.finished);
    const settingsOpen =
      document.getElementById("dailySettings")?.open || false;
    host.innerHTML = `<div><div class="daily-meta"><span class="daily-eyebrow">YOUR DAILY SESSION</span>${latest ? `<button class="daily-last" data-daily="recap" data-plan="${latest.id}">Last recap →</button>` : ""}</div><h2>${plan ? "Pick up where you left off." : "A little practice. A clearer plan."}</h2><p>${plan ? `${phase(plan.steps[plan.index])} · step ${plan.index + 1} of ${plan.steps.length} · about ${plan.minutes} minutes planned` : `${draft.reviews ? `${draft.reviews} due reviews` : "No reviews due"} · ${draft.newPositions ? `${draft.newPositions} new ${draft.newPositions === 1 ? "position" : "positions"}` : "an idea to revisit"} · 5 practical moves`}</p></div><div class="daily-invite-actions">${!plan ? `<details id="dailySettings" class="daily-settings" ${settingsOpen ? "open" : ""}><summary>About ${draft.minutes} min · ${esc(window.OpeningCourses.find((c) => c.id === draft.focus).title)} <span>Change</span></summary><div><label>Time<select id="dailyMinutes">${[5, 10, 15].map((n) => `<option value="${n}" ${draft.minutes === n ? "selected" : ""}>About ${n} min</option>`).join("")}</select></label><label>Focus<select id="dailyFocus">${window.OpeningCourses.map((c) => `<option value="${c.id}" ${c.id === draft.focus ? "selected" : ""}>${esc(c.title)}</option>`).join("")}</select></label></div></details>` : ""}<button class="btn btn-primary" data-daily="${plan ? "resume" : "start"}">${plan ? "Resume session" : "Start today’s session"} →</button></div><p id="dailyStatus" role="status"></p>`;
    if (focused)
      document.getElementById(focused)?.focus({ preventScroll: true });
  }
  async function launch(plan) {
    const task = plan.steps[Math.min(plan.index, plan.steps.length - 1)];
    if (!task) throw new Error("This saved session has no task to resume.");
    await window.Training.runDaily(task, plan.id);
  }
  async function start() {
    if (pending()) return launch(pending());
    await window.Training.pause();
    const plan = {
      ...build(),
      id: L.uid(),
      created: Date.now(),
      index: 0,
      finished: false,
    };
    plan.steps = plan.steps.map((s, i) => ({
      ...s,
      id: `task-${i}`,
      sessionId: L.uid(),
    }));
    save(plan);
    await launch(plan);
  }
  function stats(plan) {
    let reviewed = 0,
      independent = 0,
      learned = 0,
      moves = 0,
      completed = 0;
    plan.steps.forEach((task) => {
      const s = snapshot(task);
      if (!s) return;
      if (s.finished && !s.stoppedEarly) completed++;
      if (task.mode === "recall") {
        const results = (s.results || []).filter(Boolean);
        reviewed += results.length;
        independent += results.filter((r) => r === "independent").length;
      }
      if (task.mode === "learn")
        learned += Math.min(s.queue.length, s.index + (s.solved ? 1 : 0));
      if (task.mode === "play") moves += s.playerMoves ?? s.whiteMoves ?? 0;
    });
    const schedules = catalog().flatMap(
      (c) => storeFor(c.id).summary(c.cards).schedules,
    );
    const next = schedules.length
      ? Math.min(...schedules.map((s) => s.due))
      : null;
    return {
      reviewed,
      independent,
      learned,
      moves,
      completed,
      next,
      due: schedules.filter((s) => s.due <= Date.now()).length,
    };
  }
  function recap(plan) {
    const s = stats(plan);
    const next =
      s.next === null
        ? "Learn a position to schedule your first review."
        : s.next <= Date.now()
          ? `${s.due} ${s.due === 1 ? "position is" : "positions are"} still due. Take another short session when you like.`
          : `Next review: ${new Date(s.next).toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })}.`;
    return `<div class="daily-recap">${window.Coach.bubble(plan.endedEarly ? "A useful stopping point. Here’s what you actually practised." : "Session complete. A few small steps, properly taken.")}<ul><li><b>${s.reviewed}</b> review ${s.reviewed === 1 ? "answer" : "answers"} · <b>${s.independent}</b> first time without help</li><li><b>${s.learned}</b> ${s.learned === 1 ? "position" : "positions"} studied</li><li><b>${s.moves}</b> practical ${s.moves === 1 ? "move" : "moves"} played against Stockfish</li></ul><p>${esc(next)}</p>${plan.endedEarly ? '<p class="course-note">You finished early. Unfinished tasks were not counted as completed.</p>' : ""}<p class="course-note">Hints, visual guides and retries stay separate from first-attempt recall.</p><button class="btn btn-primary" data-daily="done">Done for today</button></div>`;
  }
  function decorate({ session, busy, saving, failure }) {
    render();
    if (!session.daily) return;
    const plan = record(session.daily.id);
    if (!plan) return;
    const panel = $("trainingPanel");
    const task = plan.steps.find((t) => t.id === session.daily.task);
    if (!task) return;
    panel.classList.add("is-daily-session");
    const top = panel.querySelector(".training-top span");
    if (top)
      top.textContent = `Today · ${phase(task)} · ${Math.min(plan.index + 1, plan.steps.length)}/${plan.steps.length}`;
    if (plan.finished) {
      panel.classList.add("daily-complete");
      panel.innerHTML = `<h3 id="trainingTitle" tabindex="-1">${plan.endedEarly ? "Session saved" : new Date(plan.ended).toDateString() === new Date().toDateString() ? "Today’s session complete" : "Session complete"}</h3>${recap(plan)}`;
      $("trainingBoardPrompt").textContent =
        "Your daily session is saved. Here is your recap.";
      window.Coach.hideBoard();
      return;
    }
    if (session.visualIndex != null) return;
    if (session.finished) {
      const actions = panel.querySelector(".training-actions");
      actions.innerHTML = `<button class="btn btn-primary" data-daily="advance">${plan.index + 1 === plan.steps.length ? "See my recap" : `Next: ${phase(plan.steps[plan.index + 1])}`} →</button><button class="btn btn-ghost" data-training="pause">Pause & exit</button>`;
      actions.querySelectorAll("button").forEach((b) => {
        b.disabled = busy || saving;
      });
    } else {
      const end = document.createElement("button");
      end.type = "button";
      end.className = "daily-end";
      end.dataset.daily = "finish";
      end.textContent = failure
        ? "Finish without this task"
        : "Finish session here";
      end.disabled = busy || saving;
      panel.append(end);
    }
  }
  async function advance() {
    const info = window.Training.info();
    const plan = info?.daily && record(info.daily.id);
    if (!plan || plan.finished) return;
    const task = plan.steps[plan.index];
    if (!snapshot(task)?.finished) return;
    if (plan.index + 1 === plan.steps.length) {
      plan.finished = true;
      plan.ended = Date.now();
      save(plan);
      window.Training.refresh();
      return;
    }
    plan.index++;
    save(plan);
    await launch(plan);
  }
  async function finish() {
    const info = window.Training.info();
    const plan = info?.daily && record(info.daily.id);
    if (!plan || plan.finished) return;
    await window.Training.pause();
    const task = plan.steps[plan.index];
    const s = snapshot(task);
    if (s && !s.finished)
      storeFor(task.course).saveSession({
        ...s,
        finished: true,
        stoppedEarly: true,
        visualIndex: null,
      });
    plan.finished = true;
    plan.endedEarly = true;
    plan.ended = Date.now();
    save(plan);
    await launch(plan);
  }
  let running = false;
  document.addEventListener("click", (event) => {
    const b = event.target.closest("[data-daily]");
    if (!b || b.disabled || running) return;
    const actions = {
      start,
      resume: () => launch(pending()),
      advance,
      finish,
      recap: () => launch(record(b.dataset.plan)),
      done: async () => {
        await window.Training.pause();
        render();
      },
    };
    if (!actions[b.dataset.daily]) return;
    running = true;
    Promise.resolve()
      .then(actions[b.dataset.daily])
      .catch((error) => {
        const status = $("dailyStatus");
        if (status)
          status.textContent = `Could not update the session: ${error.message}. Your progress is kept; try Resume.`;
      })
      .finally(() => {
        running = false;
      });
  });
  document.addEventListener("change", (event) => {
    if (event.target.id === "dailyMinutes") {
      S.prefs.set("dailyMinutes", safeMinutes(event.target.value));
      render();
    }
    if (event.target.id === "dailyFocus") {
      S.prefs.set("dailyFocus", event.target.value);
      render();
    }
  });
  window.addEventListener("learning:change", () => {
    if (!window.Training?.active()) render();
  });
  window.DailySession = { build, render, decorate, stats, pending, record };
})();
