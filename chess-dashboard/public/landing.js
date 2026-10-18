/* Public pages: real, local lesson previews and a smooth hand-off to the workspace.
   The preview never writes a training attempt or claims recall credit. */
(function () {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const S = window.Store;
  const LB = window.LeakBoard;
  const profiles = {
    maya: {
      name: "Maya",
      line: "Let’s find the idea.",
      text: "Bring your pieces into the game before asking them to attack. Want to try the bishop move together?",
    },
    theo: {
      name: "Theo",
      line: "Your turn. You’ve got this.",
      text: "One move at a time. Try the response you prepared; a hint is there if you need it.",
    },
    inez: {
      name: "Inez",
      line: "Pause. What changed?",
      text: "Before your next move, take a breath. Which piece is your opponent attacking?",
    },
  };
  const savedCoach = () => {
    const id = S.prefs.get("studyCoach", "maya");
    return profiles[id] ? id : "maya";
  };
  const courses =
    window.PublicCourses ||
    window.OpeningCourses.map((c) => ({
      opening: c.opening,
      side: c.side,
      chapters: c.chapters.length,
      positions: c.cards.length,
    }));
  const surface =
    location.pathname === "/"
      ? "home"
      : location.pathname.startsWith("/learn/")
        ? "course"
        : "guide";
  const metric = (name) =>
    window.LeakMetrics?.track(
      name,
      { course: preview.id, surface },
      preview.id,
    );
  let preview = window.LessonPreviews[0];
  let board;
  let companion;
  let completed = false;
  if ($("previewBoard")) {
    companion = window.BoardCompanion.mount($("previewCompanion"));
    board = new LB.Board($("previewBoard"), {
      onMove(move) {
        if (completed) return;
        metric("Preview started");
        if (move.uci !== preview.answer) {
          companion.show({ event: "retry", key: preview.id });
          board.clearSelection();
          $("demoFeedback").textContent =
            `${move.san} is legal. This lesson is practising ${preview.move}. Try that move, or ask for a hint.`;
          return;
        }
        completed = true;
        metric("Preview completed");
        companion.show({ event: "solved", key: preview.id });
        board.setPosition(preview.after.fen, {
          lastMove: { from: move.from, to: move.to },
        });
        $("demoPrompt").textContent = `${preview.move}. That’s the idea.`;
        $("demoFeedback").textContent = preview.idea;
        $("demoSide").textContent = "Idea explored";
        $("demoContinue").hidden = false;
        $("demoHint").hidden = true;
      },
    });
    function showPreview(id) {
      preview =
        window.LessonPreviews.find((p) => p.id === id) ||
        window.LessonPreviews[0];
      completed = false;
      companion.show({ event: "learn", key: preview.id });
      board.setOrientation(preview.side);
      board.setPosition(preview.position.fen, {
        legal: preview.position.legal,
      });
      const prompts = {
        italian: "Bring your bishop into the game.",
        caro: "Build your centre with …d5.",
        queens: "Give your centre some support.",
      };
      $("demoPrompt").textContent = prompts[preview.id];
      $("demoFeedback").textContent =
        preview.id === "italian"
          ? "Tap the bishop on f1, then c4. You’re playing White."
          : `You’re playing Black. Try ${preview.move}, or ask for a little hint.`;
      $("demoSide").textContent =
        `${preview.side === "white" ? "White" : "Black"} to move`;
      $("demoContinue").href =
        `/app/?opening=${preview.id}${document.body.dataset.initialPreview ? "&chapter=essentials" : ""}#today`;
      $("demoContinue").hidden = true;
      $("demoHint").hidden = false;
      document
        .querySelectorAll("[data-preview]")
        .forEach((b) =>
          b.setAttribute(
            "aria-pressed",
            String(b.dataset.preview === preview.id),
          ),
        );
    }
    document
      .querySelectorAll("[data-preview]")
      .forEach((b) =>
        b.addEventListener("click", () => showPreview(b.dataset.preview)),
      );
    $("demoReset").addEventListener("click", () => showPreview(preview.id));
    $("demoHint").addEventListener("click", () => {
      const move = preview.position.legal.find((m) => m.uci === preview.answer);
      board.setArrows([{ from: move.from, to: move.to, kind: "best" }]);
      $("demoFeedback").textContent = preview.hint;
      companion.show({ event: "hinted", key: preview.id });
    });
    showPreview(document.body.dataset.initialPreview || preview.id);
    if (surface === "course") metric("Course opened");
  }
  document.querySelectorAll("[data-thumb]").forEach((el) => {
    const p = window.LessonPreviews.find((p) => p.id === el.dataset.thumb);
    const pieces = LB.parseFen(p.position.fen).board;
    const squares = Array.from(
      { length: 64 },
      (_, i) => "abcdefgh"[i % 8] + (8 - Math.floor(i / 8)),
    );
    if (p.side === "black") squares.reverse();
    el.innerHTML = squares
      .map(
        (sq, i) =>
          `<span class="thumb-square ${(Math.floor(i / 8) + (i % 8)) % 2 ? "dark" : "light"}">${LB.pieceSvg(pieces[sq])}</span>`,
      )
      .join("");
  });
  document.querySelectorAll("[data-course-count]").forEach((el) => {
    const c = courses.find((c) => c.opening === el.dataset.courseCount);
    if (c) el.textContent = `${c.chapters} chapters · ${c.positions} positions`;
  });
  document.querySelectorAll("#courseFilter button").forEach((button) =>
    button.addEventListener("click", () => {
      const side = button.dataset.side;
      document
        .querySelectorAll("#courseFilter button")
        .forEach((b) => b.setAttribute("aria-pressed", String(b === button)));
      const visible = courses.filter((c) => side === "all" || c.side === side);
      document.querySelectorAll("[data-course-side]").forEach((row) => {
        row.hidden = side !== "all" && row.dataset.courseSide !== side;
      });
      $("courseCount").textContent =
        `${visible.length} guided ${visible.length === 1 ? "course" : "courses"} · ${visible.reduce((n, c) => n + c.chapters, 0)} chapters · ${visible.reduce((n, c) => n + c.positions, 0)} training positions`;
    }),
  );
  function refreshCoach(id, announce = false, persisted = true) {
    const profile = profiles[id];
    window.BoardCompanion.refresh();
    document
      .querySelectorAll("[data-choose-coach]")
      .forEach((b) =>
        b.setAttribute("aria-pressed", String(b.dataset.chooseCoach === id)),
      );
    document.querySelectorAll(".demo-coach,.welcome-portrait").forEach((el) => {
      el.dataset.coach = id;
    });
    if ($("demoCoachName"))
      $("demoCoachName").textContent = `${profile.name} · Your study guide`;
    if ($("welcomeName")) {
      $("welcomeName").textContent = `${profile.name} · Study guide`;
      $("welcomeLine").textContent = `“${profile.line}”`;
      $("welcomeText").textContent = profile.text;
      if (announce)
        $("coachChoiceStatus").textContent =
          `${profile.name} is selected for your study sessions.${persisted ? "" : " Storage is unavailable; this choice lasts for this visit."}`;
    }
  }
  document.querySelectorAll("[data-choose-coach]").forEach((b) =>
    b.addEventListener("click", () => {
      const persisted = S.prefs.set("studyCoach", b.dataset.chooseCoach);
      refreshCoach(b.dataset.chooseCoach, true, persisted);
    }),
  );
  refreshCoach(savedCoach());

  const form = $("start");
  if (form) {
    let provider =
      S.prefs.get("landingProvider", "lichess") === "chesscom"
        ? "chesscom"
        : "lichess";
    function updateConnect() {
      const link=$("startConnect");
      if(!link)return;
      const query=new URLSearchParams({connect:provider});
      const user=$("user")?.value.trim();
      if(user)query.set('user',user);
      link.href='/app/?'+query.toString()+'#progress/games';
    }
    $("user")?.addEventListener('input',updateConnect);
    function setProvider(value) {
      provider = value;
      updateConnect();
      document
        .querySelectorAll("[data-provider]")
        .forEach((b) =>
          b.setAttribute(
            "aria-pressed",
            String(b.dataset.provider === provider),
          ),
        );
    }
    setProvider(provider);
    document.querySelectorAll("[data-provider]").forEach((b) =>
      b.addEventListener("click", () => {
        setProvider(b.dataset.provider);
        S.prefs.set("landingProvider", provider);
        $("user").focus();
      }),
    );
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const user = $("user").value.trim();
      if (!user) {
        $("user").focus();
        return;
      }
      location.href = `/app/?${new URLSearchParams({ provider, user, run: "1" })}`;
    });
  }
})();
