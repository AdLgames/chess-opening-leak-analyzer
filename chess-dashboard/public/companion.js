/* A small, authored personality layer. Never grades a move or changes learning data. */
(function () {
  "use strict";
  const S = window.Store;
  const voices = {
    maya: {
      name: "Maya",
      explore: [
        "Shall we cause a little development?",
        "Big plans. Small wooden people.",
      ],
      learn: [
        "Let’s give those pieces a purpose.",
        "One idea. Then we make our move.",
      ],
      recall: [
        "Your memory is up. No pressure, brain.",
        "You’ve met this position before. Say hello.",
      ],
      retry: [
        "An interesting plot twist. Try your line?",
        "Legal? Yes. Your prepared move? Not quite.",
      ],
      hinted: [
        "A tiny nudge. Our little non-secret.",
        "Even good plans need a signpost.",
      ],
      revealed: [
        "Mystery solved. Let that move sink in.",
        "Now you’ve seen it. Next time, your turn.",
      ],
      solved: [
        "There it is. Your pieces got the memo.",
        "That’s the idea. Nicely done.",
      ],
      assisted: [
        "A little help. A little wiser.",
        "We found it together. That counts as practice.",
      ],
      explain: [
        "Let’s see what happens next.",
        "The board has receipts. Shall we look?",
      ],
      practical: [
        "Time to take the training wheels for a spin.",
        "Stockfish is here. I brought moral support.",
      ],
      model: [
        "A little chess history. With plot twists.",
        "Let’s see how the story unfolds.",
      ],
      error: [
        "A brief technical intermission.",
        "The connection blinked. Your move can wait.",
      ],
    },
    theo: {
      name: "Theo",
      explore: [
        "Chess pieces. Excellent little troublemakers.",
        "Pick a plan. Let’s make something happen.",
      ],
      learn: [
        "Tiny army. Big ambitions.",
        "Ready? Let’s put that idea on the board.",
      ],
      recall: [
        "Brain versus board. Friendly match.",
        "Your turn. I’ll resist shouting the answer.",
      ],
      retry: [
        "A creative detour! Back to your line?",
        "That’s legal. Let’s find your chosen move.",
      ],
      hinted: [
        "One tactical breadcrumb, coming up.",
        "A nudge. Not a whole shove.",
      ],
      revealed: [
        "Ta-da. Now give that move a proper look.",
        "Answer delivered. No speed-reading the idea!",
      ],
      solved: [
        "Oh, that’ll do nicely.",
        "Yes! Consider that a tiny board-side high five.",
      ],
      assisted: [
        "Team effort. Still useful practice.",
        "A nudge and a move. That’s how we learn.",
      ],
      explain: [
        "Roll the chess footage.",
        "Let’s see the reply. Popcorn optional.",
      ],
      practical: [
        "Five moves. One very serious fish.",
        "You bring the plan. I’ll bring the pep talk.",
      ],
      model: [
        "Cue the dramatic chess music. Silently.",
        "Let’s borrow a good idea from history.",
      ],
      error: [
        "Technical time-out. Not your fault.",
        "The internet has wandered off for a moment.",
      ],
    },
    inez: {
      name: "Inez",
      explore: [
        "A little curiosity. A little mischief.",
        "Let’s see what this position is hiding.",
      ],
      learn: [
        "A plan beats a very confident guess.",
        "First the idea. Then the theatrics.",
      ],
      recall: [
        "No peeking. Unless you ask for a hint.",
        "A familiar position. Let’s introduce your memory.",
      ],
      retry: [
        "An option. Just not your prepared one.",
        "A little detour. The board isn’t going anywhere.",
      ],
      hinted: [
        "One clue. I’m generous like that.",
        "A gentle nudge. Very dignified.",
      ],
      revealed: [
        "There we are. Give that idea a moment.",
        "The secret is out. Now make it familiar.",
      ],
      solved: [
        "Quietly excellent. We can be smug for a second.",
        "Very tidy. I do appreciate a plan.",
      ],
      assisted: [
        "With a little help. Still a useful step.",
        "Good. Let’s give that idea time to settle.",
      ],
      explain: [
        "Let’s inspect the evidence.",
        "One reply can tell quite a story.",
      ],
      practical: [
        "Let’s see what your plan does in company.",
        "The fish calculates. We shall think.",
      ],
      model: [
        "History has a few moves worth borrowing.",
        "Watch the plan. The score can wait.",
      ],
      error: [
        "A pause for the machinery.",
        "The connection needs a moment. How theatrical.",
      ],
    },
  };
  const bookLines = {
    maya: {book: ['{move}. Your pieces have done their homework!', 'Right out of the book. Looking well-read today.'], exploreMove: ['A new little adventure. Let’s see the plan.']},
    theo: {book: ['{move}! Somewhere, an opening manual just nodded.', 'Book move. Tiny army, excellent preparation.'], exploreMove: ['We’re taking the scenic route. What’s your idea?']},
    inez: {book: ['{move}. A familiar move with a plan to explore.', 'A book move. Now make the position your own.'], exploreMove: ['A different path. Let’s investigate before judging.']},
  };
  for (const id of Object.keys(bookLines)) Object.assign(voices[id], bookLines[id]);
  const puzzleLines = {
    maya: { puzzle: ['Take your time. The pieces aren’t going anywhere.', 'Checks, captures, threats. Let’s be nosy.'], pattern: ['One small idea. A whole new way to see the board.'], puzzleRetry: ['A plot twist! Let’s look for the puzzle’s continuation.'] },
    theo: { puzzle: ['Tiny army. Somewhere here, a big opportunity.', 'Detective hat on. Where’s the tactic?'], pattern: ['A little chess trick for your collection.'], puzzleRetry: ['The board has another plan. Let’s hunt it down.'] },
    inez: { puzzle: ['Look at the forcing moves first. No rush.', 'Check your king, then look for an opportunity.'], pattern: ['See the relationship. Then make the move.'], puzzleRetry: ['That move is legal. Look for the verified continuation.'] },
  };
  for (const id of Object.keys(puzzleLines)) Object.assign(voices[id], puzzleLines[id]);
  const planLines = {
    maya: {plan: ['The script changed. Your brain gets the starring role.', 'A little less autopilot. A little more plan.'], planRetry: ['A detour! What does the position need now?']},
    theo: {plan: ['Opening manual closed. Thinking cap very much open.', 'Tiny army. Time for a real decision.'], planRetry: ['New plot. Same pieces. Check their threat.']},
    inez: {plan: ['Read the board. Let the plan follow.', 'One position. A few good questions.'], planRetry: ['Take another look at the relationship on the board.']},
  };
  for (const id of Object.keys(planLines)) Object.assign(voices[id], planLines[id]);
  function current() {
    const id = S.prefs.get("studyCoach", "maya");
    return Object.hasOwn(voices, id) ? id : "maya";
  }
  const instances = new Set();
  function mount(host, { prompt = null } = {}) {
    let state = null;
    let variant = 0;
    let lastKey = "";
    let enabled = false;
    host.classList.add("companion-rail");
    host.innerHTML =
      '<div class="companion-scene"><button type="button" class="companion-person" aria-label=""><span class="companion-art" aria-hidden="true"></span><svg class="companion-spark" viewBox="0 0 24 24" aria-hidden="true"><path d="m12 1 3 8 8 3-8 3-3 8-3-8-8-3 8-3Z"/></svg></button><div class="companion-cloud"><span class="companion-byline"></span><p class="companion-quip" role="status" aria-live="polite" aria-atomic="true"></p><p class="companion-task"></p><button type="button" class="companion-dismiss" aria-label="Quiet mode: hide board character and speech bubble">×</button></div></div><button type="button" class="companion-show">Show guide</button>';
    const scene = host.querySelector(".companion-scene");
    const show = host.querySelector(".companion-show");
    const person = host.querySelector(".companion-person");
    const quip = host.querySelector(".companion-quip");
    function render(animate = false) {
      const id = current();
      const quiet = S.prefs.get("boardCompanionQuiet", false);
      const visible = enabled && !S.prefs.get("coachPortraitHidden", false);
      host.hidden = !visible;
      host.classList.toggle("is-quiet", !!quiet);
      scene.hidden = !!quiet;
      show.hidden = !quiet;
      if (prompt)
        prompt.classList.toggle("companion-prompt", visible && !quiet);
      if (!visible || !state) return;
      host.dataset.coach = id;
      host.dataset.reaction = state.event;
      person.setAttribute(
        "aria-label",
        `Say something else, ${voices[id].name}`,
      );
      show.textContent = `Show ${voices[id].name}`;
      host.querySelector(".companion-byline").textContent = voices[id].name;
      const options = voices[id][state.event] || voices[id].learn;
      const text = options[variant % options.length].replaceAll("{move}", state.move || "That move");
      if (quip.textContent !== text) quip.textContent = text;
      host.querySelector(".companion-task").textContent = state.prompt || "";
      if (animate && !quiet) {
        host.classList.remove("is-reacting");
        void host.offsetWidth;
        host.classList.add("is-reacting");
      }
    }
    person.addEventListener("click", () => {
      variant += 1;
      render(true);
    });
    host.querySelector(".companion-dismiss").addEventListener("click", () => {
      S.prefs.set("boardCompanionQuiet", true);
      render();
      show.focus({ preventScroll: true });
    });
    show.addEventListener("click", () => {
      S.prefs.set("boardCompanionQuiet", false);
      render(true);
      person.focus({ preventScroll: true });
    });
    const instance = {
      show(next) {
        const key = `${next.key || ""}|${next.event}`;
        const changed = key !== lastKey;
        state = next;
        enabled = true;
        if (changed) {
          variant = Math.abs(Number(next.seed) || 0);
          lastKey = key;
        }
        render(changed);
      },
      hide() {
        enabled = false;
        render();
      },
      refresh() {
        render();
      },
    };
    instances.add(instance);
    return instance;
  }
  function refresh() {
    instances.forEach((instance) => instance.refresh());
  }
  window.BoardCompanion = {
    mount,
    refresh,
    current,
    name: () => voices[current()].name,
  };
})();
