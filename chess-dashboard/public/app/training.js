/* A focused learning session on the existing board. All chess legality and
   computer moves come from the established APIs; lesson answers are authored. */
(function () {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const C = window.ItalianCourse;
  const L = window.LearningStore;
  const LB = window.LeakBoard;
  const esc = LB.esc;
  const cards = new Map(C.cards.map((card) => [card.id, card]));
  const chapterById = (id) => C.chapters.find((c) => c.id === id);
  const label = (mode) => ({ learn: 'Learn', recall: 'Recall', play: 'Play from here' }[mode]);
  let session = null; let active = false; let busy = false; let pos = null;
  let generation = 0; let closing = Promise.resolve(); let selected = 'italian';
  let feedback = ''; let failure = ''; let saving = false;
  let returnHeading = null;
  const chapter = () => chapterById(session?.chapter) || C.chapters[0];
  const card = () => cards.get(session?.queue[session.index]);
  const save = () => L.saveSession(session);
  const dueText = (at) => at <= Date.now() ? 'Review due' : `Review ${new Date(at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}`;
  const button = (action, text, primary = false) => `<button type="button" class="btn ${primary ? 'btn-primary' : 'btn-ghost'}" data-training="${action}">${text}</button>`;

  function overview(opening = selected) {
    selected = opening;
    const host = $('italianCourse');
    host.hidden = opening !== 'italian';
    const summary = L.summary(C.cards);
    const pending = L.session();
    if (!active) host.innerHTML = `<div class="course-heading"><span class="course-kicker">ITALIAN FOR WHITE</span><span class="course-tag">Pilot course</span></div>
      <p class="course-intro">4 chapters · 17 practice positions</p>
      ${pending ? `<div class="course-resume">${button('resume', `Resume ${label(pending.mode).toLowerCase()} →`, true)}</div>` : ''}
      <ol class="course-chapters">${C.chapters.map((c, i) => `<li><button data-course-chapter="${c.id}"><span class="chapter-number">${L.completed(c.id) ? '✓' : String(i + 1).padStart(2, '0')}</span><span><strong>${esc(c.title)}</strong><small>${esc(c.subtitle)}</small></span><span class="chapter-state">${L.completed(c.id) ? 'Revisit' : L.saved('learn', c.id) ? 'Continue' : 'Learn'} →</span></button>${L.completed(c.id) ? `<div class="chapter-tools"><button class="btn btn-ghost" data-course-practice="${c.id}">Recall</button><button class="btn btn-ghost" data-course-play="${c.id}">Play from here →</button></div>` : ''}</li>`).join('')}</ol>
      <div class="course-review">${button('review', summary.due.length ? `Review ${summary.due.length} due →` : summary.schedules.length ? 'Practise learned moves →' : 'Start first lesson →', true)}
      <label class="course-length"><span>Session</span><select id="courseMinutes" aria-label="Practice session length">${[5,10,15].map((n) => `<option value="${n}" ${window.Store.prefs.get('italianSessionMinutes', 5) === n ? 'selected' : ''}>${n} min</option>`).join('')}</select></label></div>
      ${summary.schedules.length && !summary.due.length ? `<p class="course-note">${dueText(Math.min(...summary.schedules.map((s) => s.due)))} · Early practice is optional.</p>` : ''}`;
    const repertoire = $('repertoireCourse');
    repertoire.hidden = !summary.schedules.length;
    repertoire.innerHTML = `<div><strong>Italian for White</strong><span>${C.chapters.filter((c) => L.completed(c.id)).length}/4 chapters studied · ${summary.due.length} positions due</span></div>${button('course', 'Open course →')}`;
  }

  function progress() {
    const summary = L.summary(C.cards);
    $('courseProgress').innerHTML = `<div class="line-heading"><h3>Italian training</h3><span>${summary.schedules.length}/17 positions introduced</span></div>
      <p class="course-record">${summary.attempts.length ? `${summary.independent} of ${summary.attempts.length} recall attempts answered first time without help in the last 30 days.` : 'Complete a lesson, then practise without hints to build your recall record.'} ${summary.practical ? `${summary.practical} five-move practice ${summary.practical === 1 ? 'session' : 'sessions'} completed.` : ''}</p>
      <p class="course-note">Lesson completion, recall and practical play are recorded separately. Playing Stockfish does not establish a win rate or opening mastery.</p>
      ${summary.schedules.length ? `<ul class="review-records">${summary.schedules.map((s) => `<li><span>${esc(cards.get(s.card).title)}</span><span>${dueText(s.due)}</span></li>`).join('')}</ul>` : ''}`;
  }

  function render() {
    if (!active) return;
    const c = card(); const done = session.finished;
    const total = session.mode === 'play' ? 5 : session.queue.length;
    const index = session.mode === 'play' ? session.whiteMoves : session.index;
    const title = done ? session.mode === 'learn' ? 'Chapter studied' : session.mode === 'recall' ? 'Practice complete' : 'Position played' : session.mode === 'play' ? chapter().title : session.mode === 'recall' && !session.solved ? 'Find your repertoire move' : c.title;
    $('trainingBoardPrompt').textContent = done ? 'Take a moment to look at the position.' : session.mode === 'play' ? `${session.whiteMoves}/5 moves · ${chapter().goal}` : session.solved ? `${session.answer || c.move} played. ${session.mode === 'recall' ? 'Answer recorded.' : 'Look at the idea, then continue.'}` : session.mode === 'recall' ? 'White to move. Play the move you prepared.' : c.prompt;
    const results = session.results || [];
    let body = done
      ? session.mode === 'learn' ? `<p>${esc(chapter().takeaway)}</p><p class="course-note">${chapter().cards.length} positions saved for review. Lessons do not count as independent recall.</p>`
        : session.mode === 'recall' ? `<p>${results.filter((r) => r === 'independent').length} of ${results.length} answered first time without help.</p><p class="course-note">Hinted answers and retries return sooner. Early practice keeps your existing review date.</p>`
          : `<p>${esc(session.terminal || chapter().goal)}</p><p class="course-note">${session.whiteMoves >= 5 ? 'Five moves completed against Stockfish.' : 'The position reached the end of the game.'} This session records practice, without a pass/fail grade.</p>`
      : session.mode === 'play' ? `<p>${esc(chapter().goal)}</p><p class="course-note">You play White. Stockfish plays Black at a fixed search depth; no human rating is implied.</p>`
        : session.mode === 'learn' ? `<p>${esc(c.idea)}</p>` : '<p class="course-note">Play the move from your Italian course. Other legal choices may also be sound.</p>';
    if (session.solved && !done) body = '';
    if (session.helped && !session.solved && c) body = `<p class="training-clue">${esc(c.hint)}</p>`;
    const controls = done
      ? (session.mode === 'learn' ? button('recall-chapter', 'Practise without hints', true) + button('play', 'Play from here') + button('save-line', 'Save course line') : button('done', 'Done for today', true)) + (session.mode === 'learn' ? button('done', 'Back to course') : '')
      : session.mode === 'play' ? button('pause', 'Pause & exit')
        : session.solved ? button('next', session.index + 1 === total ? session.mode === 'recall' ? 'Finish practice' : 'Finish chapter' : 'Next position →', true) + button('pause', 'Pause & exit')
          : button('hint', 'Hint') + button('reveal', 'Show move') + button('pause', 'Pause & exit');
    $('trainingPanel').innerHTML = `<div class="training-top"><span>${label(session.mode)}</span><span>${Math.min(index + (session.solved || done ? 1 : 0), total)}/${total}</span></div>
      <progress class="training-progress" max="${total}" value="${done ? total : index}" aria-label="Session progress"></progress>
      <h3 tabindex="-1" id="trainingTitle">${esc(title)}</h3>${body}
      <div class="training-feedback" id="trainingFeedback" role="status" aria-live="polite">${esc(feedback)}</div>
      ${failure ? `<p class="notice" role="alert">${esc(failure)}</p>${button('retry', 'Retry position', true)}` : ''}
      <div class="training-actions">${controls}</div><p class="training-storage">${L.durable() ? 'Progress saved on this device.' : 'Progress is kept in this tab only. Device storage is unavailable; keep this tab open.'}</p>`;
    $('trainingPanel').querySelectorAll('button').forEach((b) => {
      const action = b.dataset.training;
      b.disabled = !['pause', 'done'].includes(action) && (busy || saving || (failure && action !== 'retry'));
    });
  }

  function present(next, options = {}) {
    pos = next;
    window.Study.training.present(pos, { enabled: !session.finished && !session.solved && (session.mode !== 'play' || pos.turn === 'white'), ...options });
  }
  function showError(err) {
    failure = `The position could not update: ${err.message}. Your progress is saved; retry when ready.`;
  }
  async function load() {
    if (!active) return;
    const token = ++generation;
    busy = true; failure = ''; render();
    try {
      if (session.mode === 'play') {
        const last = cards.get(chapter().cards.at(-1));
        const next = await LB.position(null, session.playMoves, [...last.line, last.move]);
        if (token !== generation || !active) return;
        present(next); busy = false; render();
        if (!session.finished) await opponent(token);
      } else {
        const c = card();
        const next = await LB.position(null, null, session.solved ? [...c.line, c.move] : c.line);
        if (token !== generation || !active) return;
        const expected = next.legal.find((m) => m.san === c.move);
        present(next, { arrows: session.helped && expected ? [{ from: expected.from, to: expected.to, kind: 'best' }] : [] });
        if (session.solved && !feedback) feedback = `${c.move}. ${c.why}`;
      }
    } catch (err) { if (token === generation && active) showError(err); }
    finally { if (token === generation && active) { busy = false; render(); } }
  }

  async function start(mode, chapterId = 'essentials', ids = null) {
    await pause();
    const prior = L.saved(mode, chapterId);
    session = prior || { id: L.uid(), mode, chapter: chapterId, queue: ids || chapterById(chapterId).cards, index: 0, misses: 0, helped: false, solved: false, firstPlayed: '', whiteMoves: 0, playMoves: [], results: [] };
    activate(); await load();
  }
  function activate() {
    returnHeading = { title: $('openingGuideTitle').textContent, meta: $('guideMeta').textContent };
    active = true; busy = false; feedback = ''; failure = '';
    save();
    window.App.go('today');
    window.Workspace.setPanel('study');
    $('openingGuideTitle').textContent = C.title;
    $('guideMeta').textContent = `${label(session.mode)} · ${chapterById(session.chapter)?.title || 'Your learned positions'}`;
    document.querySelector('.library-panel').classList.add('is-training');
    $('trainingPanel').hidden = false; $('trainingBoardPrompt').hidden = false;
    $('libBoard').setAttribute('aria-label', 'Italian training board');
    $('libBoard').setAttribute('aria-describedby', 'trainingBoardPrompt');
    window.Study.training.begin((move) => attempt(move));
  }
  async function resume() {
    const prior = L.session();
    if (!prior) return start('learn');
    await pause(); session = prior; activate(); await load();
  }
  function pause() {
    if (!active) return closing;
    active = false; generation += 1; busy = false;
    save();
    document.querySelector('.library-panel').classList.remove('is-training');
    $('trainingPanel').hidden = true; $('trainingBoardPrompt').hidden = true;
    $('libBoard').setAttribute('aria-label', 'Explorer board');
    $('libBoard').removeAttribute('aria-describedby');
    closing = window.Study.training.end().then(() => { if (!active) {
      if (returnHeading) { $('openingGuideTitle').textContent = returnHeading.title; $('guideMeta').textContent = returnHeading.meta; }
      window.Workspace.refreshGuide(); overview();
    } });
    return closing;
  }
  function outcome() { return session.misses ? 'missed' : session.helped ? 'hinted' : 'independent'; }
  function resolved(result, played) {
    if (session.mode === 'learn') L.enrol(card().id);
    else {
      L.attempt(`${session.id}:${session.index}`, card().id, result, session.firstPlayed || (result === 'revealed' ? '' : played));
      session.results[session.index] = result;
    }
    session.solved = true; session.answer = card().move; save();
  }
  async function attempt(move) {
    if (!active || busy || session.finished || session.solved || failure) return;
    if (session.mode === 'play') {
      if (pos.turn !== 'white') return;
      const token = generation; busy = true; render();
      try {
        const next = await LB.position(move.fen_after);
        if (token !== generation || !active) return;
        session.playMoves.push(move.uci); session.whiteMoves += 1; save();
        present(next, { lastMove: move });
        await opponent(token);
      } catch (err) { if (token === generation && active) showError(err); }
      finally { if (token === generation && active) { busy = false; render(); } }
      return;
    }
    const c = card();
    if (!session.firstPlayed) { session.firstPlayed = move.san; save(); }
    if (move.san !== c.move) {
      session.misses += 1; save();
      feedback = `You played ${move.san}. This exercise asks for a particular repertoire move; a different legal move is not automatically a chess mistake. ${session.misses >= 2 ? 'Use Hint or Show move to continue with help.' : 'Try again, or ask for a hint.'}`;
      render();
      if (session.misses >= 2) await reveal();
      return;
    }
    const token = generation; busy = true; render();
    try {
      const next = await LB.position(move.fen_after);
      if (token !== generation || !active) return;
      const result = outcome();
      resolved(result, move.san);
      feedback = `${move.san}. ${c.why}${session.mode === 'recall' ? result === 'independent' ? ' Answered without help.' : ' Recorded as assisted practice, not independent recall.' : ''}`;
      present(next, { lastMove: move });
    } catch (err) { if (token === generation && active) showError(err); }
    finally { if (token === generation && active) { busy = false; render(); } }
  }
  async function hint() {
    if (!active || session.solved) return;
    session.helped = true; save();
    const expected = pos?.legal.find((m) => m.san === card().move);
    if (expected) present(pos, { arrows: [{ from: expected.from, to: expected.to, kind: 'best' }] });
    feedback = 'Hint shown. This answer will be recorded as assisted practice.'; render();
  }
  async function reveal() {
    if (!active || session.solved) return;
    const token = generation; session.helped = true; save(); busy = true; render();
    try {
      const next = await LB.position(null, null, [...card().line, card().move]);
      if (token !== generation || !active) return;
      resolved(session.misses ? 'missed' : 'revealed', card().move);
      feedback = `${card().move}. ${card().why} Answer shown; this does not count as independent recall.`;
      present(next);
    } catch (err) { if (token === generation && active) showError(err); }
    finally { if (token === generation && active) { busy = false; render(); } }
  }
  async function next() {
    if (!session.solved) return;
    if (session.index + 1 >= session.queue.length) {
      session.finished = true;
      if (session.mode === 'learn') L.complete(session.chapter);
      save(); feedback = ''; render(); overview(); return;
    }
    session.index += 1; session.misses = 0; session.helped = false; session.solved = false; session.answer = ''; session.firstPlayed = '';
    feedback = ''; save(); await load();
    if (active) $('trainingBoardPrompt').focus({ preventScroll: true });
  }
  function terminal() {
    return pos.checkmate ? 'Checkmate. Review the final position to see the decisive threat.' : pos.stalemate ? 'Stalemate. The side to move has no legal moves.' : pos.insufficient_material ? 'Draw by insufficient material.' : !pos.legal.length ? 'The game has ended.' : '';
  }
  async function opponent(token) {
    const ending = terminal();
    if (ending || (session.whiteMoves >= 5 && pos.turn === 'white')) {
      session.finished = true; session.terminal = ending;
      if (session.whiteMoves >= 5) L.practical(session.id, session.whiteMoves);
      save(); feedback = ''; present(pos, { enabled: false }); render(); return;
    }
    if (pos.turn !== 'black') return;
    busy = true; feedback = 'Stockfish is choosing Black’s reply…'; present(pos, { enabled: false }); render();
    const result = await LB.engine(pos.fen, { depth: 10, multipv: 1 });
    if (token !== generation || !active) return;
    const move = pos.legal.find((m) => m.uci === result.lines?.[0]?.uci);
    if (!move) throw new Error('Stockfish did not return a playable reply');
    const after = await LB.position(move.fen_after);
    if (token !== generation || !active) return;
    session.playMoves.push(move.uci); save();
    feedback = `Black played ${move.san}. Your move.`; present(after, { lastMove: move });
    await opponent(token);
  }
  async function review(chapterId) {
    const summary = L.summary(C.cards);
    const minutes = window.Store.prefs.get('italianSessionMinutes', 5);
    const pool = chapterId ? chapterById(chapterId).cards.filter((id) => L.schedule(id)) : (summary.due.length ? summary.due : summary.schedules).map((s) => s.card);
    if (!pool.length) return start('learn', chapterId || 'essentials');
    await start('recall', chapterId || 'reviews', pool.slice(0, minutes === 5 ? 6 : minutes === 10 ? 12 : 17));
  }
  async function saveLine() {
    if (saving) return;
    const token = generation; saving = true; render();
    try {
      const last = cards.get(chapter().cards.at(-1));
      const before = await LB.position(null, null, last.line);
      if (token !== generation || !active) return;
      const key = `${window.Store.positionKey(before.fen)}|${last.move}`;
      const old = window.Store.repertoire.byKey(key);
      if (old?.status === 'committed') { feedback = 'This response is already in your repertoire. Your name and notes have been kept.'; return; }
      const entry = window.Store.repertoire.commitPrep({ fen: before.fen, move: last.move, color: 'white', eco: 'C50', opening: C.title, line: last.line,
        moveNumber: before.move_number, name: chapter().title, notes: chapter().takeaway, explorePath: [...last.line, last.move] });
      feedback = window.Store.savedLocally(entry) ? 'Saved on this device. Open Repertoire to revisit or export the line.' : 'Kept in this tab only. Device storage is unavailable; export your repertoire before closing.';
    } catch (err) { if (token === generation && active) showError(err); }
    finally { saving = false; if (active) render(); }
  }

  const actions = {
    resume, hint, reveal, next, retry: load, pause, done: pause,
    review: () => review(),
    'recall-chapter': () => review(session.chapter),
    play: () => start('play', session.chapter),
    'save-line': saveLine,
    course: async () => { await window.Workspace.choose('italian'); $('italianCourse').scrollIntoView({ block: 'nearest' }); },
  };
  document.addEventListener('click', (event) => {
    const b = event.target.closest('[data-training], [data-course-chapter], [data-course-practice], [data-course-play]');
    if (!b || b.disabled) return;
    const action = b.dataset.courseChapter ? () => start('learn', b.dataset.courseChapter)
      : b.dataset.coursePractice ? () => review(b.dataset.coursePractice)
        : b.dataset.coursePlay ? () => start('play', b.dataset.coursePlay) : actions[b.dataset.training];
    if (action) Promise.resolve().then(action).catch((err) => { if (active) { showError(err); busy = false; render(); } });
  });
  document.addEventListener('change', (event) => {
    if (event.target.id === 'courseMinutes') window.Store.prefs.set('italianSessionMinutes', Number(event.target.value));
  });
  window.addEventListener('learning:change', () => { if (!active) overview(); });
  window.addEventListener('storage', (event) => { if (event.key?.startsWith('leaklab:pref:learning:')) { if (!active) overview(); progress(); } });
  window.Training = { overview, progress, pause, active: () => active,
    leave(view) { if (view !== 'today' && active) pause(); },
  };
  overview(); progress();
}());
