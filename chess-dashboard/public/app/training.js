/* A focused learning session on the existing board. All chess legality and
   computer moves come from the established APIs; lesson answers are authored. */
(function () {
  'use strict';
  const $ = (id) => document.getElementById(id);
  let C = window.OpeningCourses[0];
  let L = window.LearningStore;
  const LB = window.LeakBoard;
  const esc = LB.esc;
  let cards = new Map(C.cards.map((card) => [card.id, card]));
  const chapterById = (id) => C.chapters.find((c) => c.id === id);
  const label = (mode) => ({ learn: 'Learn', recall: 'Recall', play: 'Play from here', game: 'Model game' }[mode]);
  let session = null; let active = false; let busy = false; let pos = null;
  let generation = 0; let closing = Promise.resolve(); let selected = 'italian';
  let feedback = ''; let failure = ''; let saving = false;
  let returnHeading = null;
  const chapter = () => chapterById(session?.sourceChapter || session?.chapter) || C.chapters[0];
  const practiceCard = () => cards.get(session?.practiceCardId || chapter().cards.at(-1));
  const visualFrames = () => window.VisualLessons?.[`${C.id}/${card()?.id}`] || [];
  const card = () => cards.get(session?.queue[session.index]);
  const save = () => L.saveSession(session);
  const learnerSide = () => C.personal ? card()?.side || C.side : C.side;
  const dueText = (at) => at <= Date.now() ? 'Review due' : `Review ${new Date(at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}`;
  const button = (action, text, primary = false) => `<button type="button" class="btn ${primary ? 'btn-primary' : 'btn-ghost'}" data-training="${action}">${text}</button>`;
  function reviewSummary(results) {
    const independent = results.filter((result) => result === 'independent').length;
    const percent = results.length ? Math.round(100 * independent / results.length) : 0;
    const due = L.summary(C.cards).schedules.map((entry) => entry.due).filter(Number.isFinite);
    const minutes = due.length ? Math.max(1, Math.ceil((Math.min(...due) - Date.now()) / 60000)) : null;
    const next = minutes === null ? 'after your next lesson' : Math.min(...due) <= Date.now() ? 'now' : minutes >= 1440 ? `in ${Math.ceil(minutes / 1440)} day${Math.ceil(minutes / 1440) === 1 ? '' : 's'}` : minutes >= 60 ? `in ${Math.ceil(minutes / 60)} hour${Math.ceil(minutes / 60) === 1 ? '' : 's'}` : `in ${minutes} minute${minutes === 1 ? '' : 's'}`;
    return `<div class="review-summary"><strong>${percent}% first attempt recall</strong><progress class="recall-meter" max="${Math.max(results.length, 1)}" value="${independent}" aria-label="First attempt recall this session"></progress><h4>Your session</h4><ul><li>You practised <b>${results.length} positions</b></li><li>${independent} of ${results.length} answered first time without help</li><li>Your next review is due <b>${next}</b></li></ul><p class="course-note">Hints and retries will come back sooner.</p></div>`;
  }

  const catalog = () => [...window.OpeningCourses, window.Preparation?.personalCourse()].filter(Boolean);
  function selectCourse(id) {
    C = catalog().find((c) => c.id === id) || window.OpeningCourses[0];
    L = window.LearningStore.forCourse(C.id);
    cards = new Map(C.cards.map((c) => [c.id, c]));
  }
  const count = () => session.playerMoves ?? session.whiteMoves ?? 0;
  const model = () => window.ModelGames.find((g) => g.id === session.game);

  function overview(opening = selected) {
    selected = opening;
    const course = window.OpeningCourses.find((c) => c.opening === opening);
    const host = $('italianCourse');
    host.hidden = !course;
    if (!active && course) {
      selectCourse(course.id);
      const summary = L.summary(C.cards); const pending = L.session();
      const elsewhere = catalog().filter((other) => other.id !== C.id).map((other) => ({ course: other, session: window.LearningStore.forCourse(other.id).session() })).filter((other) => other.session).sort((a, b) => b.session.updated - a.session.updated)[0];
      host.innerHTML = `<div class="course-heading"><span class="course-kicker">${esc(C.title.toUpperCase())}</span><span class="course-tag">Guided course</span></div>
        <p class="course-intro">${C.chapters.length} chapters · ${C.cards.length} practice positions</p>
        ${pending ? `<div class="course-resume">${button('resume', `Resume ${label(pending.mode).toLowerCase()} →`, true)}</div>` : elsewhere ? `<div class="course-resume"><button class="btn btn-primary" data-resume-course="${elsewhere.course.id}">Resume ${esc(elsewhere.course.title)} →</button></div>` : ''}
        <ol class="course-chapters">${C.chapters.map((c, i) => `<li><button data-course-chapter="${c.id}"><span class="chapter-number">${L.completed(c.id) ? '✓' : String(i + 1).padStart(2, '0')}</span><span><strong>${esc(c.title)}</strong><small>${esc(c.subtitle)}</small></span><span class="chapter-state">${L.completed(c.id) ? 'Revisit' : L.saved('learn', c.id) ? 'Continue' : 'Learn'} →</span></button>${L.completed(c.id) ? `<div class="chapter-tools"><button class="btn btn-ghost" data-course-practice="${c.id}">Recall</button><button class="btn btn-ghost" data-course-play="${c.id}">Play from here →</button></div>` : ''}</li>`).join('')}</ol>
        <div class="course-review">${button('review', summary.due.length ? `Review ${summary.due.length} due →` : summary.schedules.length ? 'Practise learned moves →' : 'Start first lesson →', true)}
        <label class="course-length"><span>Session</span><select id="courseMinutes" aria-label="Practice session length">${[5,10,15].map((n) => `<option value="${n}" ${window.Store.prefs.get('italianSessionMinutes', 5) === n ? 'selected' : ''}>${n} min</option>`).join('')}</select></label></div>
        ${summary.schedules.length && !summary.due.length ? `<p class="course-note">${dueText(Math.min(...summary.schedules.map((s) => s.due)))} · Early practice is optional.</p>` : ''}
        <div class="model-game-list"><h3>See the plans in a game</h3>${window.ModelGames.filter((g) => g.course === C.id).map((g) => `<button class="model-game-link" data-model-game="${g.id}"><strong>${esc(g.title)}</strong><span>${esc(g.players)} · ${esc(g.event)}</span><span>Replay with your guide →</span></button>`).join('')}</div>`;
    }
    const enrolled = catalog().filter((c) => window.LearningStore.forCourse(c.id).summary(c.cards).schedules.length);
    $('repertoireCourse').hidden = !enrolled.length;
    $('repertoireCourse').innerHTML = enrolled.map((c) => {
      const learning = window.LearningStore.forCourse(c.id); const summary = learning.summary(c.cards);
      return `<div class="repertoire-course-row"><div><strong>${esc(c.title)}</strong><span>${c.personal ? `${summary.schedules.length} positions from games` : `${c.chapters.filter((ch) => learning.completed(ch.id)).length}/${c.chapters.length} chapters studied`} · ${summary.due.length} positions due</span></div><button class="btn btn-ghost" data-open-course="${c.id}">Open ${c.personal ? 'practice' : 'course'} →</button></div>`;
    }).join('');
  }
  function progress() {
    $('courseProgress').innerHTML = catalog().map((c) => {
      const summary = window.LearningStore.forCourse(c.id).summary(c.cards);
      return `<section class="course-progress-section"><div class="line-heading"><h3>${esc(c.title)}</h3><span>${summary.schedules.length}/${c.cards.length} ${c.personal ? 'exercises' : 'positions'} introduced</span></div>
        <p class="course-record">${summary.attempts.length ? `${summary.independent} of ${summary.attempts.length} recall attempts answered first time without help in the last 30 days.` : 'Learn a position, then practise without hints to build your recall record.'} ${summary.practical ? `${summary.practical} five-move practice sessions completed.` : ''}</p>
        ${summary.schedules.length ? `<details><summary>Review dates · ${summary.due.length} due</summary><ul class="review-records">${summary.schedules.map((s) => `<li><span>${esc(c.cards.find((card) => card.id === s.card).title)}</span><span>${dueText(s.due)}</span></li>`).join('')}</ul></details>` : ''}</section>`;
    }).join('');
  }

  function render() {
    if (!active) return;
    $('trainingPanel').classList.remove('is-daily-session', 'daily-complete');
    $('trainingPanel').classList.toggle('review-complete', session.mode === 'recall' && !!session.finished);
    if (session.mode === 'game') { renderGame(); return; }
    if (session.visualIndex != null && visualFrames().length) { renderVisual(); return; }
    const c = card(); const done = session.finished;
    const total = session.mode === 'play' ? 5 : session.mode === 'game' ? model().moves.length : session.queue.length;
    const index = session.mode === 'play' ? count() : session.index;
    const title = done ? session.mode === 'learn' ? 'Chapter studied' : session.mode === 'recall' ? 'Practice complete' : 'Position played' : session.mode === 'play' ? chapter().title : session.mode === 'recall' && !session.solved ? 'Find your repertoire move' : c.title;
    $('trainingBoardPrompt').textContent = done ? 'Take a moment to look at the position.' : session.mode === 'play' ? `${count()}/5 moves · ${chapter().goal}` : session.solved ? `${session.answer || c.move} played. ${session.mode === 'recall' ? 'Answer recorded.' : 'Look at the idea, then continue.'}` : session.mode === 'recall' ? `${learnerSide() === 'black' ? 'Black' : 'White'} to move. Play the move you prepared.` : c.prompt;
    const results = session.results || [];
    let body = done
      ? session.mode === 'learn' ? `<p>${esc(session.daily ? card()?.why || chapter().takeaway : chapter().takeaway)}</p><p class="course-note">${session.queue.length} positions saved for review. Lessons do not count as independent recall.</p>`
        : session.mode === 'recall' ? reviewSummary(results)
          : `<p>${esc(session.terminal || chapter().goal)}</p><p class="course-note">${count() >= 5 ? 'Five moves completed against Stockfish.' : 'The position reached the end of the game.'} This session records practice, without a pass/fail grade.</p>`
      : session.mode === 'play' ? `<p>${esc(chapter().goal)}</p><p class="course-note">You play ${learnerSide() === 'black' ? 'Black' : 'White'}. Stockfish plays ${learnerSide() === 'black' ? 'White' : 'Black'} at a fixed search depth.</p>`
        : session.mode === 'learn' ? `<p>${esc(c.idea)}</p>` : '<p class="course-note">Play the move from your repertoire. Other legal choices may also be sound.</p>';
    if (session.solved && !done) body = '';
    if (session.helped && !session.solved && c) body = `<p class="training-clue">${esc(c.hint)}</p>`;
    if (!done && !feedback) body = session.helped && c ? `<div class="training-clue">${window.Coach.bubble(c.hint)}</div>` : window.Coach.bubble(session.mode === 'learn' ? c.idea : session.mode === 'play' ? chapter().goal : 'Your turn. Play the move you prepared; use a hint if you need one.');
    if (feedback && !done) body = '';
    let controls = done
      ? (session.mode === 'learn' ? button('recall-chapter', 'Practise without hints', true) + (!C.personal && !session.focus ? button('play', 'Play from here') : '') + button('save-line', 'Save course line') : button('done', 'Done for today', true)) + (session.mode === 'learn' ? button('done', 'Back to course') : '')
      : session.mode === 'play' ? button('pause', 'Pause & exit')
        : session.solved ? button('next', session.index + 1 === total ? session.mode === 'recall' ? 'Finish practice' : 'Finish chapter' : 'Next position →', true) + button('pause', 'Pause & exit')
          : button('hint', 'Hint') + button('reveal', 'Show move') + button('pause', 'Pause & exit');
    if (!done && session.mode !== 'play' && !session.demonstration && visualFrames().length) controls += button('visual', session.mode === 'recall' && !session.solved ? 'Visual hint' : 'Explore the idea');
    if (!done && session.mode !== 'play' && session.lastWrong) controls += button('show-why', 'Show why');
    if (!done && C.personal && session.mode === 'learn' && session.reportMove && !session.lastWrong) controls += button('report-why', 'Explain my game move');
    if (session.explanation && !session.demonstration) controls += button('demonstrate', 'Play the continuation');
    if (!done && session.solved && session.mode === 'learn') controls += button('save-choice', 'Keep this move');
    if (session.demonstration) {
      $('trainingBoardPrompt').textContent = 'Look at the continuation, then return to your exercise.';
      body = ''; controls = button('back-task', 'Back to exercise', true) + button('pause', 'Pause & exit');
    }
    $('trainingPanel').innerHTML = `<div class="training-top"><span>${session.mode === 'play' ? 'Play · vs Stockfish' : label(session.mode)}</span><span>${Math.min(index + (session.solved || done ? 1 : 0), total)}/${total}</span></div>
      <progress class="training-progress" max="${total}" value="${done ? total : Math.min(index + (session.solved ? 1 : 0), total)}" aria-label="Session progress"></progress>
      <h3 tabindex="-1" id="trainingTitle">${esc(title)}</h3>${body}
      <div class="training-feedback" id="trainingFeedback" role="status" aria-live="polite">${feedback ? window.Coach.bubble(feedback, session.misses ? 'thoughtful' : 'encouraging') : ''}</div>
      ${session.explanation ? `<p class="coach-evidence">${esc(session.explanation.source)}</p>` : ''}
      ${failure ? `<p class="notice" role="alert">${esc(failure)}</p>${button('retry', 'Retry position', true)}` : ''}
      <div class="training-actions">${controls}</div><p class="training-storage">${L.durable() ? 'Progress saved on this device.' : 'Progress is kept in this tab only. Device storage is unavailable; keep this tab open.'}</p><div class="coach-options">${window.Coach.picker()}<button class="coach-toggle" data-training="toggle-coach">${window.Store.prefs.get('coachPortraitHidden', false) ? 'Show' : 'Hide'} coach portrait</button></div>`;
    if (done) window.Coach.hideBoard();
    else window.Coach.onBoard({
      event: failure ? 'error' : session.demonstration || session.explanation ? 'explain'
        : session.solved ? session.helped || session.misses ? 'assisted' : 'solved'
          : session.mode === 'play' ? 'practical' : session.helped ? 'hinted'
            : session.lastWrong ? 'retry' : session.mode,
      prompt: $('trainingBoardPrompt').textContent,
      key: `${session.id}:${session.index}:${session.demonstration ? 'demo' : ''}`,
      seed: session.index,
    });
    $('trainingPanel').querySelectorAll('button').forEach((b) => {
      const action = b.dataset.training;
      b.disabled = !['pause', 'done'].includes(action) && (busy || saving || (failure && action !== 'retry'));
    });
    window.DailySession?.decorate({ session, busy, saving, failure });
  }

  function renderVisual() {
    const frames = visualFrames(); const frame = frames[session.visualIndex];
    $('trainingBoardPrompt').textContent = `Visual guide ${session.visualIndex + 1}/${frames.length}: ${frame.title}. Look at the arrows and circles.`;
    $('trainingPanel').innerHTML = `<div class="training-top"><span>Visual guide</span><span>${session.visualIndex+1}/${frames.length}</span></div><h3 id="trainingTitle" tabindex="-1">${esc(frame.title)}</h3>${window.Coach.bubble(frame.text)}<p class="visual-legend">Arrows show the route or relationship. Circles mark the squares discussed. This diagram is read-only.<span class="sr-only"> Marked squares: ${esc(frame.circles.map((c)=>c.square).join(', '))}. ${esc(frame.arrows.map((a)=>`Arrow from ${a.from} to ${a.to}`).join('. '))}.</span></p>${session.mode === 'recall' && !session.solved ? '<p class="course-note">Visual help shown. This answer will count as assisted practice.</p>' : ''}${failure ? `<p role="alert">${esc(failure)}</p>${button('retry','Retry diagram')}` : ''}<div class="training-actions visual-actions">${session.visualIndex ? button('visual-back','← Previous') : ''}${session.visualIndex+1<frames.length ? button('visual-next','Next idea →',true) : button('visual-close',session.solved?'Back to exercise':'Try the move',true)}${session.visualIndex+1<frames.length ? button('visual-close','Back to exercise') : ''}${button('pause','Pause & exit')}</div>`;
    $('trainingPanel').querySelectorAll('button').forEach((b)=>{b.disabled=b.dataset.training!=='pause' && busy;});
    window.Coach.onBoard({event:failure?'error':'explain',prompt:frame.title,key:`${session.id}:visual:${session.index}:${session.visualIndex}`,seed:session.visualIndex});
    window.DailySession?.decorate({session,busy,saving,failure});
  }
  async function openVisual() {
    if (!visualFrames().length || busy) return;
    if (session.mode === 'recall' && !session.solved) session.helped = true;
    session.visualIndex = 0; save(); await load();
    $('trainingTitle')?.focus({preventScroll:true});
  }
  async function visualStep(delta) {
    session.visualIndex = Math.max(0,Math.min(visualFrames().length-1,session.visualIndex+delta));save();await load();
    $('trainingTitle')?.focus({preventScroll:true});
  }
  async function closeVisual() { session.visualIndex=null;save();await load();$('trainingBoardPrompt').focus({preventScroll:true}); }
  async function runDaily(task, dailyId) {
    await pause();
    if (window.App.currentView() !== 'today') return;
    selectCourse(task.course);
    if (!task.queue?.length || task.queue.some((id)=>!cards.has(id))) throw new Error('A saved training position is no longer available.');
    session=L.checkpoints().find((s)=>s.id===task.sessionId) || {id:task.sessionId,course:C.id,mode:task.mode,chapter:`daily:${dailyId}:${task.id}`,sourceChapter:task.sourceChapter,practiceCardId:task.practiceCardId,queue:task.queue,index:0,misses:0,helped:false,solved:false,firstPlayed:'',whiteMoves:0,playMoves:[],results:[],focus:true,daily:{id:dailyId,task:task.id},visualIndex:task.mode==='learn' && window.VisualLessons?.[`${C.id}/${task.queue[0]}`] ? 0 : null};
    activate();await load();
  }

  function present(next, options = {}) {
    pos = next;
    window.Study.training.present(pos, { enabled: !session.finished && !session.solved && !session.demonstration && session.mode !== 'game' && (session.mode !== 'play' || pos.turn === learnerSide()), orientation: learnerSide(), title: C.title, ...options });
  }
  function showError(err) {
    failure = `The position could not update: ${err.message}. Your progress is saved; retry when ready.`;
  }
  async function load() {
    if (!active) return;
    const token = ++generation;
    busy = true; failure = ''; render();
    try {
      if (session.visualIndex != null && visualFrames().length) {
        const frame = visualFrames()[session.visualIndex];
        const next = await LB.position(frame.fen);
        if (token !== generation || !active) return;
        present(next, { enabled: false, arrows: frame.arrows, circles: frame.circles });
      } else if (session.mode === 'game') {
        const next = await LB.position(null, null, model().moves.slice(0, session.index));
        if (token !== generation || !active) return;
        present(next, { enabled: false });
      } else if (session.demonstration) {
        const c = card();
        const next = await LB.position(c.fen || c.startFen, session.explanation.moves);
        if (token !== generation || !active) return;
        feedback = session.explanation.text; present(next, { enabled: false });
      } else if (session.mode === 'play') {
        const last = practiceCard();
        const next = await LB.position(null, session.playMoves, [...last.line, last.move]);
        if (token !== generation || !active) return;
        present(next); busy = false; render();
        if (!session.finished) await opponent(token);
      } else {
        const c = card();
        const next = await LB.position(c.startFen || null, null, session.solved ? [...c.line, c.move] : c.line);
        if (token !== generation || !active) return;
        const expected = next.legal.find((m) => m.san === c.move);
        if (C.personal && session.mode === 'learn' && !session.solved) {
          session.reportMove = next.legal.find((m) => m.san === c.report?.played) || null;
          save();
        }
        present(next, { arrows: session.helped && expected ? [{ from: expected.from, to: expected.to, kind: 'best' }] : [] });
        if (session.solved && !feedback) feedback = c.why;
      }
    } catch (err) { if (token === generation && active) showError(err); }
    finally { if (token === generation && active) { busy = false; render(); } }
  }

  async function start(mode, chapterId = 'essentials', ids = null, courseId = C.id, focus = false) {
    await pause();
    selectCourse(courseId);
    const prior = L.saved(mode, chapterId);
    session = prior || { id: L.uid(), mode, course: C.id, focus, chapter: chapterId, queue: ids || chapterById(chapterId).cards, index: 0, misses: 0, helped: false, solved: false, firstPlayed: '', whiteMoves: 0, playMoves: [], results: [] };
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
    $('libBoard').setAttribute('aria-label', `${C.title} training board`);
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
    active = false; generation += 1; busy = false; window.Coach.hideBoard();
    save();
    document.querySelector('.library-panel').classList.remove('is-training');
    $('trainingPanel').hidden = true; $('trainingBoardPrompt').hidden = true;
    $('libBoard').setAttribute('aria-label', 'Explorer board');
    $('libBoard').removeAttribute('aria-describedby');
    closing = window.Study.training.end().then(() => { if (!active) {
      if (returnHeading) { $('openingGuideTitle').textContent = returnHeading.title; $('guideMeta').textContent = returnHeading.meta; }
      window.Workspace.refreshGuide(); overview();
      if (window.App.currentView() === 'today') window.Coach.onBoard({ event: 'explore', key: 'explore', prompt: 'Pick an opening or play a move. Make yourself at home.' });
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
      if (pos.turn !== learnerSide()) return;
      const token = generation; busy = true; render();
      try {
        const next = await LB.position(move.fen_after);
        if (token !== generation || !active) return;
        session.playMoves.push(move.uci); session.playerMoves = count() + 1; if (learnerSide() === 'white') session.whiteMoves = count(); save();
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
      session.lastWrong = move; session.explanation = null; save();
      feedback = c.mistakes?.[move.san]?.text || `You played ${move.san}. A different legal move is not automatically a chess mistake. ${session.mode === 'learn' ? c.idea + ' ' : ''}Try again, or ask for a hint. Show why checks a concrete continuation.`;
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
      feedback = `${c.why}${session.mode === 'recall' ? result === 'independent' ? ' Answered without help.' : ' Recorded as assisted practice, not independent recall.' : ''}`;
      present(next, { lastMove: move });
    } catch (err) { if (token === generation && active) showError(err); }
    finally { if (token === generation && active) { busy = false; render(); } }
  }
  async function hint() {
    if (!active || session.solved) return;
    session.helped = true; save();
    const expected = pos?.legal.find((m) => m.san === card().move);
    if (expected) present(pos, { arrows: [{ from: expected.from, to: expected.to, kind: 'best' }] });
    feedback = `${card().hint} Hint shown. This answer will be recorded as assisted practice.`; render();
  }
  async function reveal() {
    if (!active || session.solved) return;
    const token = generation; session.helped = true; save(); busy = true; render();
    try {
      const next = await LB.position(card().startFen || null, null, [...card().line, card().move]);
      if (token !== generation || !active) return;
      resolved(session.misses ? 'missed' : 'revealed', card().move);
      feedback = `${card().why} Answer shown; this does not count as independent recall.`;
      present(next);
    } catch (err) { if (token === generation && active) showError(err); }
    finally { if (token === generation && active) { busy = false; render(); } }
  }
  async function next() {
    if (!session.solved) return;
    if (session.index + 1 >= session.queue.length) {
      session.finished = true;
      if (session.mode === 'learn' && !session.focus && !C.personal) L.complete(session.chapter);
      save(); feedback = ''; render(); overview(); return;
    }
    session.index += 1; session.misses = 0; session.helped = false; session.solved = false; session.answer = ''; session.firstPlayed = ''; session.lastWrong = null; session.explanation = null; session.demonstration = false; session.visualIndex = null;
    feedback = ''; save(); await load();
    if (active) $('trainingBoardPrompt').focus({ preventScroll: true });
  }
  function terminal() {
    return pos.checkmate ? 'Checkmate. Review the final position to see the decisive threat.' : pos.stalemate ? 'Stalemate. The side to move has no legal moves.' : pos.insufficient_material ? 'Draw by insufficient material.' : !pos.legal.length ? 'The game has ended.' : '';
  }
  async function opponent(token) {
    const ending = terminal();
    if (ending || (count() >= 5 && pos.turn === learnerSide())) {
      session.finished = true; session.terminal = ending;
      if (count() >= 5) L.practical(session.id, count());
      save(); feedback = ''; present(pos, { enabled: false }); render(); return;
    }
    if (pos.turn === learnerSide()) return;
    busy = true; feedback = `Stockfish is choosing ${learnerSide() === 'black' ? 'White' : 'Black'}’s reply…`; present(pos, { enabled: false }); render();
    const result = await LB.engine(pos.fen, { depth: 10, multipv: 1 });
    if (token !== generation || !active) return;
    const move = pos.legal.find((m) => m.uci === result.lines?.[0]?.uci);
    if (!move) throw new Error('Stockfish did not return a playable reply');
    const after = await LB.position(move.fen_after);
    if (token !== generation || !active) return;
    session.playMoves.push(move.uci); save();
    feedback = `${learnerSide() === 'black' ? 'White' : 'Black'} played ${move.san}. Your move.`; present(after, { lastMove: move });
    await opponent(token);
  }
  async function review(chapterId) {
    const summary = L.summary(C.cards);
    const minutes = window.Store.prefs.get('italianSessionMinutes', 5);
    const pool = chapterId ? (session?.focus ? session.queue : chapterById(chapterId).cards).filter((id) => L.schedule(id)) : (summary.due.length ? summary.due : summary.schedules).map((s) => s.card);
    if (!pool.length) return start('learn', chapterId || 'essentials');
    await start('recall', chapterId || 'reviews', pool.slice(0, minutes === 5 ? 6 : minutes === 10 ? 12 : 17));
  }
  async function saveLine() {
    if (saving) return;
    const token = generation; saving = true; render();
    try {
      const last = cards.get((session.focus ? session.queue : chapter().cards).at(-1));
      const before = await LB.position(last.startFen || null, null, last.line);
      if (token !== generation || !active) return;
      const key = `${window.Store.positionKey(before.fen)}|${last.move}`;
      const old = window.Store.repertoire.byKey(key);
      if (old?.status === 'committed') { feedback = 'This response is already in your repertoire. Your name and notes have been kept.'; return; }
      const entry = window.Store.repertoire.commitPrep({ fen: before.fen, move: last.move, color: learnerSide(), eco: C.eco || '', opening: C.title, line: last.line,
        moveNumber: before.move_number, name: chapter().title, notes: chapter().takeaway, startFen: last.startFen || '', explorePath: [...last.line, last.move] });
      feedback = window.Store.savedLocally(entry) ? 'Saved on this device. Open Repertoire to revisit or export the line.' : 'Kept in this tab only. Device storage is unavailable; export your repertoire before closing.';
    } catch (err) { if (token === generation && active) showError(err); }
    finally { saving = false; if (active) render(); }
  }

  async function saveCurrent() {
    const token = generation; const c = card();
    const before = await LB.position(c.startFen || null, null, c.line);
    if (token !== generation || !active) return;
    const key = `${window.Store.positionKey(before.fen)}|${c.move}`;
    const prior = window.Store.repertoire.byKey(key);
    if (prior?.status === 'committed') { feedback = 'Your existing response and notes are already saved.'; render(); return; }
    const entry = window.Store.repertoire.commitPrep({ fen: before.fen, move: c.move, color: learnerSide(), eco: C.eco || '', opening: C.title,
      line: c.line, moveNumber: before.move_number, name: c.title, notes: c.why, startFen: c.startFen || '', explorePath: [...c.line, c.move] });
    feedback = window.Store.savedLocally(entry) ? 'Saved on this device. This position now has your prepared response in Repertoire.' : 'Kept in this tab only. Export your repertoire before closing.';
    window.Preparation?.invalidate(); render();
  }
  async function showWhy() {
    if (!session.lastWrong || busy) return;
    const token = generation; busy = true; render();
    try {
      const c = card(); const before = await LB.position(c.startFen || null, null, c.line);
      const result = await window.Coach.explain(before, session.lastWrong, c);
      if (token !== generation || !active) return;
      session.explanation = result; feedback = result.text; save();
    } catch (err) { if (token === generation && active) feedback = `I could not verify the continuation: ${err.message}. You can still use the course hint or show its answer.`; }
    finally { if (token === generation && active) { busy = false; render(); } }
  }
  function renderGame() {
    const game = model();
    const note = game.notes.filter((n) => n.ply <= session.index).at(-1);
    $('trainingBoardPrompt').textContent = session.index ? `After ${game.moves[session.index - 1]} · ${pos?.turn === 'black' ? 'Black' : 'White'} to move` : 'Replay the game and stop at the important ideas.';
    $('trainingPanel').innerHTML = `<div class="training-top"><span>Model game</span><span>${session.index}/${game.moves.length} plies</span></div><h3 id="trainingTitle">${esc(game.title)}</h3><p class="model-players">${esc(game.players)}<br>${esc(game.event)}</p>
      <div id="trainingFeedback" role="status">${window.Coach.bubble(note.text)}</div><p class="course-note">Historical game · includes mistakes and alternatives to your course line.</p>
      ${failure ? `<p role="alert">${esc(failure)}</p>${button('retry','Retry position')}` : ''}
      <div class="training-actions">${button('game-back','← Previous')}${button('game-next','Next move →',true)}${button('game-key','Next key idea')}${button('pause','Pause & exit')}</div>
      <a class="model-source" href="${esc(game.source)}" target="_blank" rel="noopener">${esc(game.sourceLabel)} ↗</a>`;
    $('trainingPanel').querySelectorAll('button').forEach((b) => { b.disabled = b.dataset.training !== 'pause' && busy; });
    window.Coach.onBoard({ event: failure ? 'error' : 'model', prompt: $('trainingBoardPrompt').textContent, key: `${session.id}:${session.index}`, seed: session.index });
    $('trainingPanel').querySelector('[data-training="game-back"]').disabled ||= session.index === 0;
    $('trainingPanel').querySelector('[data-training="game-next"]').disabled ||= session.index === game.moves.length;
    $('trainingPanel').querySelector('[data-training="game-key"]').disabled ||= session.index === game.moves.length;
  }
  async function gameJump(index) {
    session.index = Math.max(0, Math.min(model().moves.length, index));
    if (session.index === model().moves.length) session.finished = true;
    else session.finished = false;
    save(); await load();
  }
  async function startGame(id) {
    const game = window.ModelGames.find((g) => g.id === id);
    await pause(); selectCourse(game.course);
    session = L.saved('game', id) || { id: L.uid(), course: C.id, mode: 'game', chapter: id, game: id, queue: [], index: 0 };
    activate(); await load();
  }
  async function openCourse(id) {
    const course = catalog().find((c) => c.id === id);
    if (course.personal) { await pause(); selectCourse(id); await review(); }
    else await window.Workspace.choose(course.opening);
  }

  const actions = {
    resume, hint, reveal, next, retry: load, pause, done: pause,
    visual: openVisual, 'visual-back':()=>visualStep(-1), 'visual-next':()=>visualStep(1), 'visual-close':closeVisual,
    review: () => review(),
    'recall-chapter': () => review(session.chapter),
    play: () => start('play', session.chapter),
    'save-line': saveLine,
    'save-choice': saveCurrent, 'show-why': showWhy,
    'report-why': async () => { session.lastWrong = session.reportMove; session.helped = true; save(); await showWhy(); },
    demonstrate: async () => { session.demonstration = true; save(); await load(); },
    'back-task': async () => { session.demonstration = false; feedback = ''; save(); await load(); },
    'toggle-coach': () => { window.Store.prefs.set('coachPortraitHidden', !window.Store.prefs.get('coachPortraitHidden', false)); render(); },
    'game-back': () => gameJump(session.index - 1), 'game-next': () => gameJump(session.index + 1),
    'game-key': () => gameJump(model().notes.find((n) => n.ply > session.index)?.ply ?? model().moves.length),
    course: async () => { await window.Workspace.choose('italian'); $('italianCourse').scrollIntoView({ block: 'nearest' }); },
  };
  document.addEventListener('click', (event) => {
    const b = event.target.closest('[data-training], [data-course-chapter], [data-course-practice], [data-course-play], [data-model-game], [data-open-course], [data-resume-course]');
    if (!b || b.disabled) return;
    const action = b.dataset.resumeCourse ? async () => { await pause(); selectCourse(b.dataset.resumeCourse); await resume(); } : b.dataset.modelGame ? () => startGame(b.dataset.modelGame) : b.dataset.openCourse ? () => openCourse(b.dataset.openCourse) : b.dataset.courseChapter ? () => start('learn', b.dataset.courseChapter)
      : b.dataset.coursePractice ? () => review(b.dataset.coursePractice)
        : b.dataset.coursePlay ? () => start('play', b.dataset.coursePlay) : actions[b.dataset.training];
    if (action) Promise.resolve().then(action).catch((err) => { if (active) { showError(err); busy = false; render(); } });
  });
  document.addEventListener('change', (event) => {
    if (event.target.id === 'courseMinutes') window.Store.prefs.set('italianSessionMinutes', Number(event.target.value));
  });
  window.addEventListener('learning:change', () => { if (!active) overview(); });
  window.addEventListener('storage', (event) => { if (event.key?.startsWith('leaklab:pref:learning:')) { if (!active) overview(); progress(); } });
  window.Training = { overview, progress, pause, runDaily, info:()=>session ? JSON.parse(JSON.stringify(session)) : null, refresh:render, active: () => active,
    focus: (course, id) => start('learn', 'focus:' + id, [id], course, true),
    personal: (id) => start('learn', 'focus:' + id, [id], 'personal-v1', true),
    leave(view) { if (view !== 'today' && active) pause(); },
  };
  overview(); progress();
}());
