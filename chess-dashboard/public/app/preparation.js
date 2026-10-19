/* Preparation uses real book replies and report findings. Coverage, learning
   and performance in games stay separate; all scope is shown beside the result. */
(function () {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const S = window.Store; const LB = window.LeakBoard; const esc = LB.esc;
  const root = 'learning:v2:personal-v1:exercise:';
  let ctx = {}; let gaps = []; let gapCourse = 'italian-v1'; let scan = 0; let scanning = false;
  const positionKey = S.positionKey;
  const exercises = () => Object.entries(S.prefs.all()).filter(([key, value]) => key.startsWith(root) && value).map(([, value]) => value);
  function personalCourse() {
    const cards = exercises();
    const title = cards.every((c) => c.report.demo) ? 'Practice from sample games' : cards.some((c) => c.report.demo) ? 'Practice from game reports' : 'Practice from your games';
    return cards.length ? { id: 'personal-v1', title, personal: true,
      side: cards[0].side, cards, chapters: [{ id: 'essentials', title: 'Your game positions', cards: cards.map((c) => c.id),
        takeaway: 'Return to the position and recall your prepared response.', goal: 'Find the response from your game review.' }] } : null;
  }
  function findings() {
    return (ctx.rows || S.lastReport.load()?.rows || []).filter((r) => r.fen && r.player_color && r.engine_best_1 && r.engine_best_1 !== r.your_move)
      .slice().sort((a, b) => Number(b.your_games || 0) * Math.max(Number(b.eval_drop_pawns || 0), 0.1) - Number(a.your_games || 0) * Math.max(Number(a.eval_drop_pawns || 0), 0.1));
  }
  function reportIsSample() { return Boolean(ctx.demo ?? S.lastReport.load()?.demo); }
  function renderPersonal() {
    const rows = findings().slice(0, 6); const sample = reportIsSample(); const cards = exercises();
    const host = $('personalTraining');
    host.innerHTML = `<div class="line-heading"><h3>${sample ? 'Sample game exercises' : 'From your games'}</h3><span>${cards.length} exercises saved</span></div>
      ${rows.length ? `<p class="course-note">${sample ? 'These positions come from the sample archive.' : 'Repeated opening decisions from your latest analysis.'} Turn a finding into a position you can learn and review.</p><div class="finding-list">${rows.map((row, index) => `<div class="finding-row"><div><strong>${esc(row.opening || row.eco || 'Opening position')}</strong><span>${Number(row.your_games || 0)} ${sample ? 'sample ' : ''}games · You played ${esc(row.your_move)} · ${esc(row.player_color)}</span></div><button class="btn btn-ghost" data-personal-finding="${index}">Practise position →</button></div>`).join('')}</div>` : '<p class="course-note">Import games to turn recurring opening mistakes into exercises. Courses and exploration work before importing.</p><a class="text-link" href="#progress/games">Connect an account or upload PGN →</a>'}
      ${cards.length ? `<details class="saved-exercises"><summary>Saved game exercises</summary>${cards.map((c) => `<button class="sidebar-line" data-personal-exercise="${esc(c.id)}"><strong>${esc(c.title)}</strong><span>${c.side === 'black' ? 'Black' : 'White'} · ${c.report.demo ? 'Sample archive' : 'Your analysis'}</span></button>`).join('')}</details>` : ''}<p id="personalTrainingStatus" role="status" class="course-note"></p>`;
    const today = $('todayFindings');
    today.hidden = !rows.length;
    today.innerHTML = rows.length ? `<h3>${sample ? 'From the sample games' : 'From your games'}</h3>${rows.slice(0, 2).map((r, i) => `<button class="sidebar-line" data-personal-finding="${i}"><strong>Revisit ${esc(r.your_move)} in ${esc(r.opening || 'this opening')}</strong><span>${Number(r.your_games || 0)} games · Practise the response →</span></button>`).join('')}` : '';
  }
  async function createExercise(index, button) {
    const row = findings()[index]; if (!row) return;
    const origin = window.App.currentView();
    button.disabled = true;
    const status = $('personalTrainingStatus');
    status.textContent = 'Checking the position and response…';
    try {
      const pos = await LB.position(row.fen);
      if (window.App.currentView() !== origin) return;
      const saved = S.repertoire.committed().filter((e) => e.position === positionKey(pos.fen)).sort((a, b) => b.decidedAt - a.decidedAt)[0];
      const preferred = saved?.status === 'committed' && saved.answer !== row.your_move ? saved.answer : row.engine_best_1;
      const move = pos.legal.find((m) => m.san === preferred);
      if (!move) throw new Error('The report response is not legal in this position. Run a fresh analysis.');
      if (pos.turn !== row.player_color) throw new Error('The report side does not match the position.');
      const sample = reportIsSample();
      const id = btoa(positionKey(pos.fen) + '|' + move.uci + '|' + (sample ? 'sample' : 'personal')).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
      const match = window.OpeningCourses.flatMap((c) => c.cards).find((c) => positionKey(c.fen) === positionKey(pos.fen) && c.move === move.san);
      const games = Math.max(0, Number(row.your_games) || 0);
      const measured = Number(row.eval_drop_pawns);
      const trace = `${sample ? 'The sample report' : 'Your report'} records ${row.your_move} in ${games} games.${Number.isFinite(measured) && measured > 0 ? ` Its engine analysis estimates an evaluation drop of ${measured.toFixed(1)} pawns.` : ''}`;
      const exercise = { id, title: `${row.opening || 'Opening'} · after ${row.your_move}`, side: row.player_color,
        startFen: pos.fen, fen: pos.fen, line: [], move: move.san, uci: move.uci, afterFen: move.fen_after,
        prompt: 'Find the response you want to use next time.', idea: `${trace} ${match?.idea || 'Compare the response on the board, then practise it without help.'}`,
        hint: `Start with the ${move.from} piece.`, why: match?.why || `${move.san} is ${saved?.answer === move.san ? 'your saved repertoire response' : 'the engine’s first alternative in this report'}. ${trace}`,
        mistakes: match?.mistakes || {}, report: { demo: sample, played: row.your_move, games, drop: measured || 0 } };
      if (!S.prefs.get(root + id)) S.prefs.set(root + id, exercise);
      renderPersonal();
      await window.Training.personal(id);
    } catch (err) { status.textContent = `Could not create the exercise: ${err.message}`; }
    finally { button.disabled = false; }
  }
  function renderGaps() {
    $('preparationGaps').innerHTML = `<div class="line-heading"><h3>What should I prepare next?</h3><span>Opening book</span></div>
      <div class="gap-controls"><label><span>Repertoire scope</span><select id="gapCourse">${window.OpeningCourses.map((c) => `<option value="${c.id}" ${c.id === gapCourse ? 'selected' : ''}>${esc(c.title)}</option>`).join('')}</select></label><button class="btn btn-ghost" id="scanGaps">Find missing replies</button></div>
      <p class="course-note">Checks the three most frequent replies at four selected course positions. A saved response counts as prepared; recall is measured separately.</p><div id="gapResults" aria-live="polite"></div>`;
    $('scanGaps').addEventListener('click', scanGaps);
    $('gapCourse').addEventListener('change', (e) => { gapCourse = e.target.value; gaps = []; $('gapResults').textContent = ''; });
  }
  async function scanGaps() {
    if (scanning) return;
    const token = ++scan; const course = window.OpeningCourses.find((c) => c.id === gapCourse);
    const host = $('gapResults'); scanning = true; $('scanGaps').disabled = true;
    host.textContent = 'Checking book replies against your saved responses…'; $('gapCourse').disabled = true;
    try {
      const anchors = await Promise.all(course.anchors.map(async (line) => ({ line, pos: await LB.position(null, null, line) })));
      if (token !== scan) return;
      const candidates = new Map(); let checked = 0; let prepared = 0; let available = 0;
      for (const { line, pos } of anchors) {
        if (!pos.book?.total) continue;
        available += 1;
        for (const reply of pos.book.moves.slice(0, 3)) {
          const legal = pos.legal.find((m) => m.uci === reply.uci); if (!legal) continue;
          const key = positionKey(legal.fen_after); if (candidates.has(key)) continue;
          checked += 1;
          const saved = S.repertoire.committed().find((e) => e.position === key && e.color === course.side);
          if (saved?.status === 'committed' && saved.color === course.side) { prepared += 1; candidates.set(key, null); continue; }
          const known = course.cards.find((c) => positionKey(c.fen) === key);
          candidates.set(key, { course: course.id, side: course.side, line: [...line, legal.san], fen: legal.fen_after, reply: legal.san,
            games: reply.games, share: reply.share, total: pos.book.total, card: known?.id });
        }
      }
      gaps = [...candidates.values()].filter(Boolean).sort((a, b) => b.games - a.games).slice(0, 6);
      host.innerHTML = available ? `<p class="gap-summary">${prepared} of ${checked} checked replies have a saved response · ${available}/4 positions had book data.</p>${gaps.length ? gaps.map((gap, index) => `<div class="gap-row"><div><strong>Prepare for ${esc(gap.reply)}</strong><span class="mono">${esc(gap.line.join(' '))}</span><small>${Number(gap.games).toLocaleString()} book games · ${gap.share}% at this position</small></div><div>${gap.card ? `<button class="btn btn-primary" data-gap-learn="${index}">Learn response</button>` : ''}<button class="btn btn-ghost" data-gap-explore="${index}">Explore & save →</button></div></div>`).join('') : '<p class="course-note">Every checked reply has a saved response. Other positions and less frequent replies remain outside this scope.</p>'}<p class="course-note">Counts describe the bundled book, without rating or time-control filters. They are not a probability that you will know the move in a game.</p>` : '<p class="course-note">No opening-book data is available for these positions. You can still study the courses and save your own replies.</p>';
    } catch (err) { if (token === scan) host.textContent = `Could not check the opening book: ${err.message}. Try again; saved lines are unchanged.`; }
    finally { scanning = false; if ($('scanGaps')) $('scanGaps').disabled = false; if ($('gapCourse')) $('gapCourse').disabled = false; }
  }
  document.addEventListener('click', (event) => {
    const target = event.target.closest('[data-personal-finding], [data-personal-exercise], [data-gap-learn], [data-gap-explore]');
    if (!target || target.disabled) return;
    if (target.dataset.personalFinding !== undefined) { createExercise(Number(target.dataset.personalFinding), target); return; }
    if (target.dataset.personalExercise) { window.Training.personal(target.dataset.personalExercise); return; }
    const gap = gaps[Number(target.dataset.gapLearn ?? target.dataset.gapExplore)]; if (!gap) return;
    if (target.dataset.gapLearn !== undefined) window.Training.focus(gap.course, gap.card);
    else window.Workspace.position(gap.line, gap.side, `Prepare for ${gap.reply}`);
  });
  window.addEventListener('chess:report', (event) => { ctx = event.detail; renderPersonal(); });
  window.Preparation = { personalCourse,
    practice(row, button) { const at = findings().findIndex(r => S.leakKey(r) === S.leakKey(row)); return at >= 0 ? createExercise(at, button) : Promise.reject(new Error("This finding is no longer in the current report.")); },
    invalidate() { scan += 1; gaps = []; if ($('gapResults')) $('gapResults').textContent = 'Your repertoire changed. Check again to refresh these gaps.'; },
    render(view, context) { ctx = context || ctx; if (['today','progress','repertoire'].includes(view)) renderPersonal(); if (view === 'repertoire') renderGaps(); },
  };
}());
