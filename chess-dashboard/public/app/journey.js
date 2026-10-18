/* One learning journey, backed by existing immutable course evidence. */
(function () {
  "use strict";
  const S = window.Store,
    D = window.PuzzleCatalog,
    L = window.LearningStore;
  const $ = (id) => document.getElementById(id),
    esc = window.LeakBoard.esc;
  const root = "learning:v2:journey-v3:";
  const arrowIcon =
    '<svg viewBox="0 0 24 24" width="24" height="24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 18 18 6M6 6h12v12"/></svg>';
  const get = (key, fallback) => S.prefs.get(root + key, fallback);
  const settings = () =>
    get("preferences", {
      goal: 3,
      nickname: "",
      avatar: "n",
      timezone: S.prefs.get(
        "journeyTimezone",
        Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
      ),
    });
  function dateKey(at, timezone = settings().timezone) {
    const parts = new Intl.DateTimeFormat("en-US", {
      timeZone: timezone || "UTC",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    }).formatToParts(at);
    const p = Object.fromEntries(parts.map((v) => [v.type, v.value]));
    return `${p.year}-${p.month}-${p.day}`;
  }
  function week(now = Date.now()) {
    const date = new Date(dateKey(now) + "T12:00:00Z");
    date.setUTCDate(date.getUTCDate() - ((date.getUTCDay() + 6) % 7));
    return Array.from({ length: 7 }, (_, i) => {
      const d = new Date(date);
      d.setUTCDate(d.getUTCDate() + i);
      return d.toISOString().slice(0, 10);
    });
  }
  function evidence() {
    return Object.entries(S.prefs.all())
      .filter(
        ([key, v]) =>
          key.startsWith("learning:v2:") &&
          v &&
          /:(attempt|chapter|practical):/.test(key),
      )
      .map(([key, value]) => ({ key, ...value }));
  }
  function weekly(now = Date.now()) {
    const dates = week(now),
      days = new Set(
        evidence()
          .filter((e) => e.at)
          .map((e) => dateKey(e.at)),
      );
    return {
      dates,
      days,
      count: dates.filter((d) => days.has(d)).length,
      goal: Math.max(1, Math.min(7, Number(settings().goal) || 3)),
    };
  }
  function achievements() {
    const events = evidence().sort(
        (a, b) => a.at - b.at || a.key.localeCompare(b.key),
      ),
      awards = [];
    const chapter = events
      .filter((e) => e.key.includes(":chapter:"))
      .sort((a, b) => a.at - b.at)[0];
    if (chapter)
      awards.push([
        "first-idea",
        "First idea",
        "Completed your first chapter or micro-lesson.",
        chapter.at,
      ]);
    const puzzles = events.filter((e) =>
      e.key.startsWith("learning:v2:tactics-v1:attempt:"),
    );
    if (puzzles.length)
      awards.push([
        "first-puzzle",
        "Puzzle explorer",
        "Finished your first tactical position.",
        Math.min(...puzzles.map((e) => e.at)),
      ]);
    const independent = events.filter(
      (e) => e.key.includes(":attempt:") && e.outcome === "independent",
    );
    const later = independent.find((e) => {
      const course = e.key.split(":")[2];
      const enrol = S.prefs.get(`learning:v2:${course}:enrol:${e.card}`);
      return enrol && dateKey(enrol.at) !== dateKey(e.at) && e.at > enrol.at;
    });
    if (later)
      awards.push([
        "later-recall",
        "Back with a better memory",
        "Recalled a position without help on a later day.",
        later.at,
      ]);
    const distinct = new Map();
    for (const event of events) {
      if (event.card) {
        const key = event.key.split(":")[2] + ":" + event.card;
        if (!distinct.has(key)) distinct.set(key, event);
      }
    }
    if (distinct.size >= 10)
      awards.push([
        "ten-positions",
        "Ten positions explored",
        "Practised ten different positions.",
        Array.from(distinct.values())[9].at,
      ]);
    for (const [id, title, description, at] of awards)
      if (!get("reward:" + id))
        S.prefs.set(root + "reward:" + id, { id, title, description, at });
    return Object.entries(S.prefs.all())
      .filter(([k, v]) => k.startsWith(root + "reward:") && v)
      .map(([, v]) => v)
      .sort((a, b) => a.at - b.at);
  }
  function calendar() {
    const w = weekly(),
      today = dateKey(Date.now());
    return `<div class="week-heading"><div><strong>${w.count} of ${w.goal} training days</strong><span>${settings().nickname ? esc(settings().nickname) + "’s week" : "Your week"} · no streak to lose</span></div><button class="btn btn-ghost" data-journey="profile">Edit goal</button></div><ol class="week-days" aria-label="Training days this week">${w.dates.map((date, i) => `<li class="${w.days.has(date) ? "has-practice" : ""} ${date === today ? "is-today" : ""}"><span>${["M", "T", "W", "T", "F", "S", "S"][i]}</span><b aria-hidden="true">${w.days.has(date) ? "✓" : "·"}</b><span class="sr-only">${date}: ${w.days.has(date) ? "practised" : "no completed practice"}${date === today ? ", today" : ""}</span></li>`).join("")}</ol>`;
  }
  const learned = () =>
    D.lessons.filter((l) => L.forCourse("patterns-v1").completed(l.id));
  const patternStatus = (id) => {
    const schedule = L.forCourse("patterns-v1").schedule(id);
    return !schedule
      ? "Learn · try · recall later"
      : schedule.due <= Date.now()
        ? "Review due"
        : schedule.events.some((e) => e.outcome === "independent")
          ? "Recalled without help"
          : "Introduced · recall later";
  };
  const lessonDone = (id) => L.forCourse("patterns-v1").completed(id);
  function nextLesson() {
    return D.lessons.find((l) => !lessonDone(l.id)) || D.lessons[0];
  }
  function path() {
    const next = nextLesson(),
      list = !!S.prefs.get("journeyList", false);
    $("learningPath").innerHTML =
      `<div class="journey-intro"><div><span class="journey-eyebrow">YOUR LEARNING PATH</span><h2>Good instincts start here.</h2><p>One idea, a few moves, a little more confidence.</p></div><div class="path-guide" data-coach="${esc(window.BoardCompanion.current())}" aria-hidden="true"><span class="companion-art"></span></div></div>
      <div class="path-next"><span class="path-next-icon" aria-hidden="true">${arrowIcon}</span><div><small>YOUR NEXT IDEA · ABOUT 2 MIN</small><h3>${esc(next.title)}</h3></div><button class="btn btn-primary" data-idea="${next.id}">Learn this idea <span aria-hidden="true">→</span></button></div>
      <div class="journey-columns"><section class="pattern-path ${list ? "is-list" : ""}" aria-label="Tactical ideas"><div class="line-heading"><h3>Build your chess instincts</h3><button class="btn btn-ghost" data-journey="list" aria-pressed="${list}">${list ? "Journey view" : "Simple list"}</button></div><ol class="path-route">${D.themes
        .map(
          (theme, i) =>
            `<li class="path-chapter"><div class="path-chapter-heading"><span>${String(i + 1).padStart(2, "0")}</span><div><h4>${esc(theme.title)}</h4><p>${esc(theme.tagline)}</p></div></div><ol>${D.lessons
              .filter((l) => l.theme === theme.id)
              .map(
                (lesson, j) =>
                  `<li class="path-stop ${lesson.id === next.id ? "is-next" : ""} ${lessonDone(lesson.id) ? "is-studied" : ""}"><button data-idea="${lesson.id}" class="path-node" aria-label="${esc(lesson.title)}: ${lessonDone(lesson.id) ? "studied, revisit" : "learn"}"><span aria-hidden="true">${lessonDone(lesson.id) ? "✓" : window.LeakBoard.pieceSvg(j === 0 ? "n" : "p")}</span></button><div><strong>${esc(lesson.title)}</strong><span>${patternStatus(lesson.id)}</span></div></li>`,
              )
              .join("")}</ol></li>`,
        )
        .join("")}</ol></section>
      <aside class="path-courses"><h3>Bring it to your openings</h3><p class="muted">Follow a course, or jump to the chapter you need.</p>${window.OpeningCourses.map(
        (c) => {
          const learning = L.forCourse(c.id);
          return `<details class="path-course"><summary><span>${window.LeakBoard.pieceSvg(c.side === "black" ? "p" : "P")}</span><div><strong>${esc(c.title)}</strong><small>${c.chapters.filter((ch) => learning.completed(ch.id)).length} of ${c.chapters.length} chapters studied</small></div></summary><ol>${c.chapters.map((ch) => `<li><button data-path-opening="${c.opening}" data-path-chapter="${ch.id}"><span>${learning.completed(ch.id) ? "✓" : "○"}</span>${esc(ch.title)}<span aria-hidden="true">→</span></button></li>`).join("")}</ol></details>`;
        },
      ).join(
        "",
      )}<a href="#explore">Browse all 20 openings <span aria-hidden="true">→</span></a><div class="path-recall"><h4>Make the idea stick</h4><p>Come back on another day to recall a learned pattern. Opening reviews stay in your daily session.</p><button class="btn btn-ghost" data-puzzle-queue="patterns">Review learned patterns →</button></div></aside></div>`;
  }
  function today() {
    const next = nextLesson(),
      due = L.forCourse("patterns-v1").summary(learned()).due.length;
    $("todayJourney").innerHTML =
      `<div class="today-week">${calendar()}${due ? `<button class="btn btn-ghost pattern-review-invite" data-puzzle-queue="patterns">Review ${due} learned pattern${due === 1 ? "" : "s"} →</button>` : ""}</div><div class="today-discover"><a href="#explore/path"><span class="journey-eyebrow">YOUR NEXT IDEA</span><strong>${esc(next.title)}</strong><span>Learn it with your guide <b aria-hidden="true">→</b></span></a><button data-puzzle-queue="daily"><span class="journey-eyebrow">A FRESH POSITION EACH DAY</span><strong>The daily puzzle</strong><span>Untimed. Take your time. <b aria-hidden="true">→</b></span></button></div>`;
  }
  function progress() {
    const all = evidence(),
      attempts = all.filter(
        (e) =>
          e.key.startsWith("learning:v2:tactics-v1:attempt:") &&
          e.at >= Date.now() - 30 * 86400000,
      );
    const awards = achievements();
    $("journeyProgress").innerHTML =
      `<div class="journey-progress-week">${calendar()}</div><div class="line-heading"><h3>Your tactical practice</h3><a href="#explore/puzzles">Find a puzzle →</a></div><p class="muted">${attempts.length ? `${attempts.filter((e) => e.outcome === "independent").length} of ${attempts.length} positions solved first time without help in the last 30 days.` : "Your first puzzle is a good place to begin. There’s no timer and hints are always available."}</p><ul class="skill-lines">${D.themes
        .map((t) => {
          const entries = attempts.filter(
            (e) => D.puzzles.find((p) => p.id === e.card)?.theme === t.id,
          );
          return `<li><span>${esc(t.title)}</span><span>${entries.length ? `${entries.filter((e) => e.outcome === "independent").length} / ${entries.length} without help` : "Ready to explore"}</span></li>`;
        })
        .join(
          "",
        )}</ul><h3>Little milestones, real effort</h3>${awards.length ? `<ul class="earned-milestones">${awards.map((a) => `<li><span aria-hidden="true">✦</span><div><strong>${esc(a.title)}</strong><p>${esc(a.description)}</p><small>${new Date(a.at).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })}</small></div></li>`).join("")}</ul>` : '<p class="muted">Finish an idea or a puzzle to earn your first milestone.</p>'}`;
  }
  function games() {
    $("journeyGames").innerHTML =
      `<div class="library-heading"><div><h2>See the ideas in action.</h2><p>Three classic games. Play through the moves with your guide.</p></div></div><ol class="journey-game-list">${window.ModelGames.map((g, i) => `<li><span class="game-number">${String(i + 1).padStart(2, "0")}</span><div><h3>${esc(g.title)}</h3><p>${esc(g.players)}</p><small>${esc(g.event)}</small></div><button class="btn btn-primary" data-model-game="${g.id}">Replay game →</button></li>`).join("")}</ol>`;
  }
  function applyPreferences() {
    const prefs = settings();
    $("profileAvatar").innerHTML = window.LeakBoard.pieceSvg(
      ["n", "p", "r", "b"].includes(prefs.avatar)
        ? prefs.avatar.toUpperCase()
        : "N",
    );
    document.documentElement.dataset.motion = S.prefs.get("reduceMotion", false)
      ? "reduce"
      : "system";
  }
  function openProfile() {
    const f = $("learningProfileForm"),
      p = settings();
    for (const [key, value] of Object.entries({
      nickname: p.nickname || "",
      avatar: p.avatar || "n",
      goal: p.goal || 3,
      guide: S.prefs.get("studyCoach", "maya"),
      palette: S.prefs.get("boardPalette", "green"),
    }))
      f.elements[key].value = value;
    f.elements.quiet.checked = !!S.prefs.get("boardCompanionQuiet", false);
    f.elements.motion.checked = !!S.prefs.get("reduceMotion", false);
    $("profileStorage").textContent = S.persistent()
      ? `Saved on this device${window.Auth?.state?.user ? " and queued for your account" : ""}. Weekly goal uses ${p.timezone || "your local timezone"}.`
      : "Storage is unavailable. Preferences last for this tab only.";
    $("learningProfile").showModal();
  }
  function render(view = window.App?.currentView?.()) {
    applyPreferences();
    const exploring = ["explore", "path", "puzzles", "games"].includes(view);
    $("exploreSections").hidden = !exploring;
    $("exploreSections")
      .querySelectorAll("a")
      .forEach((a) => {
        if (a.hash === location.hash) a.setAttribute("aria-current", "page");
        else a.removeAttribute("aria-current");
      });
    window.Puzzles?.leave(view);
    if (view === "path") path();
    if (view === "today") today();
    if (view === "progress") progress();
    if (view === "repertoire") {
      const patterns = learned(),
        due = L.forCourse("patterns-v1").summary(patterns).due.length;
      $("repertoirePatterns").hidden = !patterns.length;
      $("repertoirePatterns").innerHTML =
        `<div class="puzzle-revisit"><div><h3>Your tactical patterns</h3><p>${patterns.length} ideas introduced · ${due} due for recall</p></div><button class="btn btn-ghost" data-puzzle-queue="patterns">${due ? "Review patterns" : "Practise early"} →</button></div>`;
    }
    if (view === "games") games();
    if (view === "puzzles") window.Puzzles?.renderLibrary();
  }
  document.addEventListener("click", (event) => {
    const b = event.target.closest("[data-journey],[data-path-chapter]");
    if (!b) return;
    if (b.dataset.journey === "profile") openProfile();
    if (b.dataset.journey === "list") {
      S.prefs.set("journeyList", !S.prefs.get("journeyList", false));
      path();
      document
        .querySelector('[data-journey="list"]')
        .focus({ preventScroll: true });
    }
    if (b.dataset.pathChapter)
      window.Training.openChapter(b.dataset.pathOpening, b.dataset.pathChapter);
  });
  $("openLearningProfile").addEventListener("click", openProfile);
  $("closeLearningProfile").addEventListener("click", () =>
    $("learningProfile").close(),
  );
  $("learningProfileForm").addEventListener("submit", (event) => {
    event.preventDefault();
    const f = event.currentTarget;
    S.prefs.set(root + "preferences", {
      ...settings(),
      nickname: f.elements.nickname.value.trim(),
      avatar: f.elements.avatar.value,
      goal: Number(f.elements.goal.value),
      updated: Date.now(),
    });
    S.prefs.set("studyCoach", f.elements.guide.value);
    S.prefs.set("boardPalette", f.elements.palette.value);
    S.prefs.set("boardCompanionQuiet", f.elements.quiet.checked);
    S.prefs.set("reduceMotion", f.elements.motion.checked);
    $("learningProfile").close();
    window.Coach.refresh();
    window.Workspace.render(window.App.currentView());
    render();
  });
  let timer;
  window.addEventListener("learning:change", () => {
    clearTimeout(timer);
    timer = setTimeout(() => {
      achievements();
      render();
    }, 50);
  });
  window.addEventListener("storage", (event) => {
    if (event.key?.startsWith("leaklab:pref:")) render();
  });
  window.Journey = {
    render,
    weekly,
    dateKey,
    nextLesson,
    achievements,
    settings,
    lessonDone,
  };
  if (!S.prefs.get("journeyTimezone"))
    S.prefs.set("journeyTimezone", settings().timezone);
  applyPreferences();
})();
