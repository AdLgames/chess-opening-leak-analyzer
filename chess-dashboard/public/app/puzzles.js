/* Offline legal-move packs, honest assisted outcomes, exact decision-boundary resume. */
(function () {
  "use strict";
  const D = window.PuzzleCatalog,
    S = window.Store,
    LB = window.LeakBoard;
  const SL = window.LearningStore.forCourse("puzzle-sessions-v1"),
    TL = window.LearningStore.forCourse("tactics-v1"),
    PL = window.LearningStore.forCourse("patterns-v1");
  const $ = (id) => document.getElementById(id),
    esc = LB.esc;
  const packs = new Map();
  let session = null,
    puzzle = null,
    active = false,
    loading = false,
    sequence = 0,
    message = "",
    reaction = "puzzle";
  const board = new LB.Board($("puzzleBoard"), {
    onMove: move,
    onSelect: select,
  });
  const companion = window.BoardCompanion.mount($("puzzleCompanion"), {
    prompt: $("puzzlePrompt"),
  });
  const theme = () => D.themes.find((t) => t.id === puzzle?.theme);
  const lesson = () => D.lessons.find((l) => l.id === session?.lesson);
  const scene = () => puzzle.scenes[session.ply];
  const guided = () => session.mode === "lesson";
  const learning = () => (session.lesson ? PL : TL);
  const save = () => {
    SL.saveSession(session);
  };
  const action = (id, text, primary = false) =>
    `<button type="button" class="btn ${primary ? "btn-primary" : "btn-ghost"}" data-puzzle-action="${id}">${text}</button>`;
  function latest() {
    return D.puzzles
      .map((p) => ({ p, events: TL.schedule(p.id)?.events || [] }))
      .map(({ p, events }) => ({ p, event: events[events.length - 1] }));
  }
  function daily(now = Date.now()) {
    return D.puzzles[Math.floor(now / 86400000) % D.puzzles.length];
  }
  function thumbnail(fen) {
    const pieces = LB.parseFen(fen).board;
    return `<span class="puzzle-mini" aria-hidden="true">${Array.from(
      { length: 64 },
      (_, i) => {
        const f = i % 8,
          r = 8 - Math.floor(i / 8),
          sq = "abcdefgh"[f] + r;
        return `<i class="${(f + r) % 2 ? "light" : "dark"}">${pieces[sq] ? LB.pieceSvg(pieces[sq]) : ""}</i>`;
      },
    ).join("")}</span>`;
  }
  function renderLibrary() {
    if (active || loading) return;
    $("puzzleSession").hidden = true;
    $("puzzleLibrary").hidden = false;
    const due = latest().filter(
        (v) => v.event && v.event.outcome !== "independent",
      ),
      pending = SL.session(),
      day = daily();
    const studied = D.lessons.filter((l) => PL.completed(l.id)),
      scheduled = PL.summary(studied).due.length;
    $("puzzleLibrary").innerHTML =
      `<div class="library-heading"><div><span class="journey-eyebrow">A LITTLE CHALLENGE, A NEW INSTINCT</span><h2 id="puzzleLibraryTitle" tabindex="-1">Your move.</h2><p>150 positions · six themes · all the time you need</p></div></div>
      ${pending ? `<div class="puzzle-resume"><span>You have a position waiting.</span>${action("resume", "Resume your position →", true)}</div>` : ""}
      <section class="daily-puzzle-feature">${thumbnail(day.fen)}<div><span class="journey-eyebrow">TODAY’S PUZZLE</span><h3>${esc(D.themes.find((t) => t.id === day.theme).title)}</h3><p>One board. One good idea. Can you spot it?</p><button class="btn btn-primary" data-puzzle-queue="daily">Play the daily puzzle →</button><small>New position at midnight UTC · ${new Date().toLocaleDateString(undefined, { month: "long", day: "numeric", timeZone: "UTC" })}</small></div></section>
      <div class="puzzle-practice-heading"><h3>What would you like to spot?</h3><a href="#explore/path">Learn the patterns first →</a></div>
      <div class="puzzle-themes">${D.themes
        .map((t) => {
          const first = D.lessons.find((l) => l.theme === t.id),
            total = latest().filter(
              (v) => v.p.theme === t.id && v.event,
            ).length;
          return `<button class="puzzle-theme" data-puzzle-theme="${t.id}">${thumbnail(first.frames[0].fen)}<span><strong>${esc(t.title)}</strong><small>${esc(t.tagline)}</small><span>${total ? `${total} explored · ` : ""}25 positions <b aria-hidden="true">→</b></span></span></button>`;
        })
        .join("")}</div>
      <div class="puzzle-revisit"><div><h3>Give an idea another go</h3><p>${due.length ? `${due.length} positions where you used help or tried again.` : "Positions you find tricky will wait here for another try."}</p></div><button class="btn btn-ghost" data-puzzle-queue="missed" ${due.length ? "" : "disabled"}>Revisit positions${due.length ? ` (${due.length})` : ""} →</button></div>
      ${studied.length ? `<div class="puzzle-revisit"><div><h3>Your learned patterns</h3><p>${scheduled} due · ${studied.length} introduced. Later-day recall helps the idea stick.</p></div><button class="btn btn-ghost" data-puzzle-queue="patterns">${scheduled ? "Review due patterns" : "Practise early"} →</button></div>` : ""}
      <p class="puzzle-source">Positions from the <a href="https://database.lichess.org/#puzzles" target="_blank" rel="noopener">Lichess CC0 puzzle database</a>. Teaching notes are original. General tactics, independent of your imported games.</p>`;
  }
  async function load(meta) {
    if (!packs.has(meta.theme)) {
      const request = fetch(`./puzzle-packs/${meta.theme}.json`).then((r) => {
        if (!r.ok)
          throw new Error(
            "Could not download this puzzle pack. Reconnect and try again.",
          );
        return r.json();
      });
      packs.set(meta.theme, request);
      try {
        await request;
      } catch (e) {
        packs.delete(meta.theme);
        throw e;
      }
    }
    return (await packs.get(meta.theme)).find((p) => p.id === meta.id);
  }
  async function start(
    id,
    { lessonId = null, mode = "puzzle", resume = null, queue = "theme" } = {},
  ) {
    const meta = D.puzzles.find((p) => p.id === id);
    if (!meta) return;
    resume ||=
      SL.checkpoints().find(
        (s) =>
          !s.finished &&
          s.puzzle === id &&
          s.mode === mode &&
          (s.lesson || null) === lessonId,
      ) || null;
    const token = ++sequence;
    loading = true;
    active = false;
    await window.Training.pause();
    if (token !== sequence) return;
    window.App.go("puzzles");
    $("puzzleLibrary").hidden = false;
    $("puzzleSession").hidden = true;
    $("puzzleLibrary").innerHTML =
      '<p role="status" class="puzzle-loading">Setting up your board…</p>';
    try {
      const loaded = await load(meta);
      if (token !== sequence || window.App.currentView() !== "puzzles") return;
      puzzle = loaded;
      if (resume && resume.version !== puzzle.version) {
        SL.saveSession({ ...resume, finished: true });
        resume = null;
        message =
          "This position has been updated. Your earlier practice record is safe; start with the updated board.";
      } else
        message = resume
          ? "Welcome back. Your position is exactly where you left it."
          : "";
      session = resume || {
        id: SL.uid(),
        puzzle: id,
        version: puzzle.version,
        mode,
        lesson: lessonId,
        queue,
        ply: 0,
        stage: mode === "lesson" ? "question" : "solve",
        help: 0,
        misses: 0,
        started: Date.now(),
        played: [],
      };
      if (!guided()) learning().enrol(session.lesson || puzzle.id);
      active = true;
      reaction = guided() ? "pattern" : "puzzle";
      save();
      board.setOrientation(session.orientation || puzzle.side);
      render();
    } catch (e) {
      if (token !== sequence) return;
      active = false;
      $("puzzleLibrary").innerHTML =
        `<p role="alert">${esc(e.message)}</p>${action("retry-load", "Try again", true)} <a href="#explore/path">Back to path</a>`;
      session = resume || { puzzle: id, lesson: lessonId, mode, queue };
    } finally {
      if (token === sequence) loading = false;
    }
  }
  function select(sq) {
    if (!active || session.stage !== "question" || !sq) return;
    if (sq === lesson().square) {
      session.stage = "frame0";
      message = "That’s the piece. Follow its legal move.";
      reaction = "explain";
      save();
      render();
    } else {
      message = "Have another look at the named square.";
      render();
    }
  }
  function finish(outcome = null) {
    session.finished = true;
    session.stage = "recap";
    if (guided()) {
      PL.enrol(session.lesson);
      PL.complete(session.lesson);
    } else
      learning().attempt(
        session.id,
        session.lesson || puzzle.id,
        outcome || (session.help || session.misses ? "hinted" : "independent"),
        session.played.join(" "),
      );
    save();
    reaction =
      guided() || session.help || session.misses ? "assisted" : "solved";
    render();
    window.Journey.achievements();
  }
  function move(m) {
    if (!active || session.stage !== "solve" || session.finished) return;
    const current = scene();
    if (!current.accepted.includes(m.uci)) {
      session.misses++;
      message = `${m.san} is legal, but it is not an accepted solution in this puzzle. Look for a forcing continuation. Your retry is recorded as supported practice.`;
      reaction = "puzzleRetry";
      save();
      render();
      return;
    }
    session.played.push(m.san);
    session.ply++;
    session.lastMove = { from: m.from, to: m.to };
    if (current.ends?.[m.uci]) session.finalFen = current.ends[m.uci];
    // Resolve the authored opponent response in the same saved transaction.
    // Reloading never replays a previously applied reply or skips a learner turn.
    if (session.ply < puzzle.scenes.length - 1) {
      const reply = scene();
      session.played.push(reply.san);
      session.lastMove = {
        from: reply.answer.slice(0, 2),
        to: reply.answer.slice(2, 4),
      };
      session.ply++;
      message = `${m.san}. The opponent replies ${reply.san}. Your move again.`;
    } else message = `${m.san}. You’ve reached the end of this puzzle’s line.`;
    if (session.ply === puzzle.scenes.length - 1) finish();
    else {
      save();
      reaction = "puzzle";
      render();
    }
  }
  function render() {
    if (!active) return;
    $("puzzleLibrary").hidden = true;
    $("puzzleSession").hidden = false;
    const idea = lesson(),
      t = theme(),
      frame = session.stage.startsWith("frame")
        ? idea.frames[Number(session.stage.slice(-1))]
        : null;
    const current = scene(),
      question = session.stage === "question";
    let fen = session.finalFen || current.fen,
      arrows = [],
      circles = [];
    if (frame) {
      fen = frame.fen;
      arrows = frame.arrows;
      circles = frame.circles;
    }
    if (session.help >= 2 && !session.finished && session.stage === "solve") {
      circles = [{ square: current.answer.slice(0, 2), kind: "book" }];
    }
    board.setPosition(fen, {
      legal:
        !session.finished && (question || session.stage === "solve")
          ? current.legal
          : [],
      arrows,
      circles,
      lastMove: frame ? null : session.lastMove,
    });
    $("puzzleLabel").textContent = guided()
      ? "Learn an idea"
      : session.mode === "recall"
        ? "Recall a learned pattern"
        : session.queue === "daily"
          ? "Daily puzzle"
          : t.title;
    const prompt = session.finished
      ? guided()
        ? "Idea introduced. Ready to use it?"
        : "Position complete. Take a look at your line."
      : question
        ? idea.question
        : frame
          ? frame.text
          : `${puzzle.side === "white" ? "White" : "Black"} to move. Find the continuation.${session.help >= 2 ? " The marked square shows which piece to use." : ""}`;
    $("puzzlePrompt").textContent = prompt;
    let body = "",
      controls = "";
    if (question) {
      body = `<p>${esc(idea.idea)}</p><p>${esc(idea.question)}</p>`;
      controls = `<button class="btn btn-ghost" data-puzzle-action="select-piece">Select ${esc(idea.square)} on the board</button>`;
    } else if (frame) {
      body = `<p>${esc(frame.text)}</p>`;
      controls = action(
        session.stage === "frame0" ? "frame-next" : "try-idea",
        session.stage === "frame0" ? "See the effect →" : "Now play the move →",
        true,
      );
    } else if (session.finished) {
      const independent = !guided() && !session.help && !session.misses;
      body = `<p class="puzzle-result">${guided() ? "You’ve met the idea." : independent ? "Solved first time, without help." : session.revealed ? "Solution explored with your guide." : "You found it with a little support."}</p><ol class="puzzle-line">${session.played.map((san) => `<li>${esc(san)}</li>`).join("")}</ol><p>${guided() ? "Your pattern is saved for later recall. Learning with a guide is separate from solving alone." : independent ? "One position, one piece of evidence. Keep exploring the pattern." : "Hints and retries help you learn. This result stays separate from unassisted solutions."}</p>`;
      controls = guided()
        ? `<button class="btn btn-primary" data-related-theme="${t.id}">Try a related puzzle →</button><a class="btn btn-ghost" href="#explore/path">Back to path</a>`
        : session.queue === "patterns"
          ? action("exit", "Back to puzzles", true)
          : action("next", "Another position →", true) +
            action("exit", "Back to puzzles");
    } else {
      body = `<p>${session.help ? esc(t.idea) : "Look for checks, captures and threats. Try a move on the board."}</p>${session.help >= 2 ? `<p class="puzzle-clue">Start with the piece on <b>${esc(current.answer.slice(0, 2))}</b>.</p>` : ""}`;
      controls =
        action("hint", session.help ? "Mark a piece" : "A small hint") +
        action("reveal", "Show the solution") +
        action("exit", "Pause & exit");
    }
    $("puzzleInstruction").innerHTML =
      `<span class="journey-eyebrow">${guided() ? "A TWO-MINUTE IDEA" : session.mode === "recall" ? "REMEMBER THE PATTERN" : esc(t.title.toUpperCase())}</span><h2 id="puzzleTitle" tabindex="-1">${guided() ? esc(idea.title) : session.finished ? "Nicely explored." : session.mode === "recall" ? esc(idea.title) : "What do you see?"}</h2>${body}<p id="puzzleFeedback" role="status" class="puzzle-feedback">${esc(message)}</p><div class="puzzle-actions">${controls}</div><p class="puzzle-storage">${SL.durable() && learning().durable() ? "Position saved on this device." : "Storage unavailable: keep this tab open to retain your position."}</p><a class="puzzle-credit" href="${puzzle.source}" target="_blank" rel="noopener">Source position · Lichess ${esc(puzzle.id)}</a>`;
    companion.show({
      event: reaction,
      key:
        session.id +
        ":" +
        session.stage +
        ":" +
        session.ply +
        ":" +
        session.misses,
      prompt: session.finished
        ? guided()
          ? "Try a new position to use the same idea."
          : independentMessage()
        : prompt,
    });
  }
  function independentMessage() {
    return session.help || session.misses
      ? "A helpful nudge today. A fresh try another day."
      : "Take the pattern with you to your next game.";
  }
  function choose(themeId, exclude = null) {
    const choices = D.puzzles.filter(
      (p) => p.theme === themeId && p.id !== exclude,
    );
    const records = latest();
    return (
      choices.find((p) => !records.find((v) => v.p.id === p.id)?.event) ||
      choices.sort(
        (a, b) =>
          (TL.schedule(a.id)?.events.at(-1)?.at || 0) -
          (TL.schedule(b.id)?.events.at(-1)?.at || 0),
      )[0]
    );
  }
  function queue(kind) {
    if (kind === "daily") return start(daily().id, { queue: "daily" });
    if (kind === "missed") {
      const item = latest()
        .filter((v) => v.event && v.event.outcome !== "independent")
        .sort((a, b) => a.event.at - b.event.at)[0];
      if (item) return start(item.p.id, { queue: "missed" });
    }
    if (kind === "patterns") {
      const studied = D.lessons.filter((l) => PL.completed(l.id)),
        due = PL.summary(studied).due;
      const idea = D.lessons.find((l) => l.id === due[0]?.card) || studied[0];
      if (idea)
        return start(idea.puzzle, {
          lessonId: idea.id,
          mode: "recall",
          queue: "patterns",
        });
      window.App.go("path");
    }
  }
  function exit() {
    sequence++;
    loading = false;
    active = false;
    companion.hide();
    session = null;
    puzzle = null;
    renderLibrary();
    $("main").scrollTop = 0;
    $("puzzleLibraryTitle")?.focus({ preventScroll: true });
  }
  async function dispatch(id) {
    if (id === "resume") {
      const saved = SL.session();
      if (saved) return start(saved.puzzle, { resume: saved });
    }
    if (id === "retry-load")
      return start(session.puzzle, {
        lessonId: session.lesson,
        mode: session.mode,
        queue: session.queue,
      });
    if (id === "exit") {
      exit();
      return;
    }
    if (!session || !active) return;
    if (id === "flip") {
      board.flip();
      session.orientation = board.orientation;
      save();
      return;
    }
    if (id === "select-piece") {
      board.activate(lesson().square);
      return;
    }
    if (id === "frame-next") {
      session.stage = "frame1";
      message = "";
      reaction = "explain";
    }
    if (id === "try-idea") {
      session.stage = "solve";
      message = "Your turn. Play the move you just explored.";
      reaction = "pattern";
    }
    if (id === "hint") {
      session.help = Math.min(2, session.help + 1);
      reaction = "hinted";
      message =
        session.help === 1
          ? theme().idea
          : "The marked square is your next moving piece.";
    }
    if (id === "reveal") {
      session.help = 3;
      session.revealed = true;
      session.played = puzzle.scenes.slice(0, -1).map((s) => s.san);
      session.ply = puzzle.scenes.length - 1;
      message =
        "Follow the solution moves above. Try the pattern again on another day.";
      finish("revealed");
      return;
    }
    if (id === "next") {
      if (session.queue === "patterns") {
        exit();
        return queue("patterns");
      }
      if (session.queue === "missed") {
        exit();
        return queue("missed");
      }
      const chosen = choose(puzzle.theme, puzzle.id);
      return start(chosen.id);
    }
    save();
    render();
    if (["frame-next", "try-idea"].includes(id))
      $("puzzleTitle").focus({ preventScroll: true });
  }
  document.addEventListener("click", (event) => {
    const b = event.target.closest(
      "[data-idea],[data-puzzle-theme],[data-puzzle-queue],[data-puzzle-action],[data-related-theme]",
    );
    if (!b) return;
    if (b.dataset.idea) {
      const idea = D.lessons.find((l) => l.id === b.dataset.idea);
      if (idea) start(idea.puzzle, { lessonId: idea.id, mode: "lesson" });
    }
    if (b.dataset.puzzleTheme) start(choose(b.dataset.puzzleTheme).id);
    if (b.dataset.puzzleQueue) queue(b.dataset.puzzleQueue);
    if (b.dataset.puzzleAction) dispatch(b.dataset.puzzleAction);
    if (b.dataset.relatedTheme)
      start(choose(b.dataset.relatedTheme, puzzle?.id).id);
  });
  window.Puzzles = {
    renderLibrary,
    daily,
    start,
    queue,
    info: () => (session ? JSON.parse(JSON.stringify(session)) : null),
    leave(view) {
      if (view !== "puzzles") {
        sequence++;
        loading = false;
        active = false;
        companion.hide();
        session = null;
        puzzle = null;
      }
    },
  };
})();
