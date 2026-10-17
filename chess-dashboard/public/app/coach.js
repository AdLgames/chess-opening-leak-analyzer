/* Maya, Theo and Inez are original illustrated guides. No invented chess titles.
   Authored feedback and engine feedback carry distinct, inspectable evidence. */
(function () {
  'use strict';
  const LB = window.LeakBoard;
  const names = { p: 'pawn', n: 'knight', b: 'bishop', r: 'rook', q: 'queen', k: 'king' };
  const profiles = { maya: 'Maya', theo: 'Theo', inez: 'Inez' };
  function current() { const id = window.Store.prefs.get('studyCoach', 'maya'); return profiles[id] ? id : 'maya'; }
  function picker() {
    return `<label class="coach-choice">Guide <select id="trainingCoach">${Object.entries(profiles).map(([id, name]) => `<option value="${id}" ${id === current() ? 'selected' : ''}>${name}</option>`).join('')}</select></label>`;
  }
  function refresh() {
    const id = current();
    document.querySelectorAll('.coach-portrait').forEach((el) => { el.dataset.coach = id; });
    document.querySelectorAll('.coach-name').forEach((el) => { el.innerHTML = `${profiles[id]} <span>· Study coach</span>`; });
    if (document.getElementById('studyCoach')) document.getElementById('studyCoach').value = id;
    if (document.getElementById('trainingCoach')) document.getElementById('trainingCoach').value = id;
  }
  document.addEventListener('change', (event) => {
    if (['studyCoach', 'trainingCoach'].includes(event.target.id) && profiles[event.target.value]) { window.Store.prefs.set('studyCoach', event.target.value); refresh(); }
  });
  function bubble(text, mood = 'calm') {
    const hidden = window.Store.prefs.get('coachPortraitHidden', false);
    return `<div class="coach-speech ${hidden ? 'portrait-hidden' : ''}" data-mood="${mood}"><span class="coach-portrait" data-coach="${current()}" aria-hidden="true"></span><div><span class="coach-name">${profiles[current()]} <span>· Study coach</span></span><p>${LB.esc(text)}</p></div></div>`;
  }
  async function explain(pos, move, card) {
    const authored = card?.mistakes?.[move.san];
    if (authored) {
      const next = await LB.position(pos.fen, [move.uci]);
      const reply = next.legal.find((m) => m.san === authored.line[1]);
      if (!reply) throw new Error('The teaching continuation could not be verified');
      return { text: authored.text, moves: [move.uci, reply.uci], source: 'Course continuation' };
    }
    const [before, after, next] = await Promise.all([
      LB.engine(pos.fen, { depth: 12, multipv: 1 }),
      LB.engine(move.fen_after, { depth: 12, multipv: 1 }),
      LB.position(move.fen_after),
    ]);
    const best = before.lines?.[0]; const response = after.lines?.[0];
    const reply = next.legal.find((m) => m.uci === response?.uci);
    if (!Number.isFinite(best?.cp) || !Number.isFinite(response?.cp) || !reply) throw new Error('No verified engine comparison is available for this move');
    const loss = Math.max(0, best.cp + response.cp);
    const captured = LB.parseFen(next.fen).board[reply.to];
    const consequence = reply.mate ? 'delivering checkmate' : captured ? `capturing your ${names[captured.toLowerCase()]} on ${reply.to}` : reply.check ? 'giving check' : 'continuing the position';
    const comparison = loss <= 60
      ? `${move.san} is close to the engine’s preferred move at this depth. It is a different choice from this exercise’s answer.`
      : `After ${move.san}, the engine finds ${reply.san}, ${consequence}.${Math.abs(best.cp) >= 9800 || Math.abs(response.cp) >= 9800 ? '' : ` Its evaluation falls by about ${(loss / 100).toFixed(1)} pawns compared with ${best.san}.`}`;
    return { text: comparison, moves: [move.uci, reply.uci], source: 'Stockfish · depth 12' };
  }
  window.Coach = { bubble, explain, refresh, picker };
}());
