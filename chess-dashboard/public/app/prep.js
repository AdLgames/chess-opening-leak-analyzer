/* Opening Leak Lab — prep: the lines you mean to play.

   The Dashboard finds what went wrong and the Clinic drills it, so until now a
   line could only enter the repertoire by way of a mistake. This is the other
   half: walk the book from the start, commit the move you intend to play, and
   keep going. A line you have never botched is still a line you need to know.

   One branch at a time, on purpose. The book's most popular reply is followed
   by default, and any earlier position can be returned to and answered
   differently — which keeps the drill queue finishable and the holes visible in
   the coverage figure the Repertoire tab already draws. */
(function () {
  'use strict';

  const LB = window.LeakBoard;
  const $ = (id) => document.getElementById(id);
  const S = window.Store;
  const esc = LB.esc;

  const START = LB.START_FEN;

  const state = {
    board: null,
    colour: 'white',
    san: [],        // the line so far, in SAN
    pos: null,      // the last /api/position payload
    busy: false,
  };

  const mine = () => state.pos && state.pos.turn === state.colour;

  /* ------------------------------------------------------------------ walking */
  async function load() {
    state.busy = true;
    try {
      state.pos = await LB.position(null, null, state.san);
    } catch (err) {
      $('prepBook').innerHTML = LB.explainHtml(err);
      state.busy = false;
      return;
    }
    state.busy = false;
    render();
  }

  function play(san) {
    state.san = state.san.concat([san]);
    load();
  }

  function back() {
    if (!state.san.length) return;
    state.san = state.san.slice(0, -1);
    load();
  }

  function reset() {
    state.san = [];
    load();
  }

  /* ----------------------------------------------------------------- committing */
  function commit(move) {
    const pos = state.pos;
    if (!pos || !move) return;
    S.repertoire.commitPrep({
      fen: pos.fen,
      move: move.san,
      color: state.colour,
      eco: (pos.opening && pos.opening.eco) || (pos.book && pos.book.eco) || '',
      opening: (pos.opening && pos.opening.name) || (pos.book && pos.book.name) || '',
      line: state.san.slice(),
      moveNumber: pos.move_number,
    });
    // Committing is also how you move on: the line continues from the move you
    // just chose, so building a repertoire is one gesture per move rather than
    // two. The opponent's most popular reply follows automatically below.
    play(move.san);
  }

  function committedHere() {
    // Only an answer of *this* side's, and only where it is this side to move.
    // The same position is reachable while preparing either colour, and showing
    // White's answer to someone building a Black repertoire reads as though they
    // had already covered it.
    if (!state.pos || !mine()) return null;
    const entry = S.repertoire.forPosition(state.pos.fen);
    if (!entry || entry.status !== 'committed') return null;
    return entry.color === state.colour ? entry : null;
  }

  /* -------------------------------------------------------------------- render */
  function render() {
    if (!state.pos) return;
    const pos = state.pos;
    const legal = pos.legal || [];
    if (!state.board) {
      state.board = new LB.Board($('prepBoard'), {
        orientation: state.colour,
        onMove: (m) => {
          const found = legalFor(m);
          if (found) (mine() ? commit(found) : play(found.san));
        },
      });
    }
    state.board.setOrientation(state.colour);
    state.board.setPosition(pos.fen, { legal });

    $('prepLine').innerHTML = state.san.length
      ? state.san.map((m, i) => (i % 2 ? '' : `<b>${Math.floor(i / 2) + 1}.</b> `) + esc(m)).join(' ')
      : '<span class="muted">the starting position</span>';
    $('prepOpening').textContent = pos.opening && pos.opening.name
      ? `${pos.opening.eco ? pos.opening.eco + ' · ' : ''}${pos.opening.name}`
      : '';
    $('prepBack').disabled = !state.san.length;

    renderTurn();
    renderBook();
    renderSaved();
  }

  function legalFor(m) {
    const legal = (state.pos && state.pos.legal) || [];
    return legal.find((l) => l.uci === m || l.san === m
      || (m && m.from && l.from === m.from && l.to === m.to)) || null;
  }

  function renderTurn() {
    const saved = committedHere();
    if (saved) {
      $('prepTurn').innerHTML =
        `<span class="prep-saved">Your move here: <b>${esc(saved.answer)}</b></span>`;
    } else if (mine()) {
      $('prepTurn').innerHTML = '<b>Your move.</b> Pick the one you mean to play.';
    } else {
      $('prepTurn').innerHTML =
        '<b>Their move.</b> Choose the reply you want to be ready for.';
    }
  }

  function renderBook() {
    const book = state.pos.book || {};
    const moves = (book.moves || []).slice(0, 12);
    if (!moves.length) {
      $('prepBook').innerHTML =
        '<p class="muted small">The book does not know this position. '
        + 'You can still play a move on the board to continue.</p>';
      return;
    }
    const isMine = mine();
    const total = book.total || 0;
    $('prepBook').innerHTML = `
      <p class="muted small">${total.toLocaleString()} games reached this position.</p>
      <div class="prep-head" aria-hidden="true">
        <span>Move</span><span></span>
        <span title="Share of games in which this move was chosen">Played</span>
        <span title="Average score for the side to move after this move">Scores</span>
      </div>
      <ul class="prep-moves">
        ${moves.map((m) => `
          <li>
            <button class="prep-move" data-san="${esc(m.san)}">
              <span class="prep-move-san">${esc(m.san)}</span>
              <span class="prep-move-bar"><i style="width:${Math.max(2, Math.min(100, m.share))}%"></i></span>
              <span class="prep-move-share mono">${m.share.toFixed(1)}%</span>
              <span class="prep-move-score mono">${m.score.toFixed(1)}%</span>
            </button>
          </li>`).join('')}
      </ul>
      <p class="muted small">${isMine
        ? 'Choosing a move saves it as your answer here and continues the line.'
        : 'Choosing a move continues the line without saving anything.'}</p>`;
    $('prepBook').querySelectorAll('.prep-move').forEach((b) => {
      b.addEventListener('click', () => {
        const m = moves.find((x) => x.san === b.dataset.san);
        if (!m) return;
        if (isMine) commit(m);
        else play(m.san);
      });
    });
  }

  function renderSaved() {
    const prep = S.repertoire.prep();
    $('prepCount').textContent = String(prep.length);
    if (!prep.length) {
      $('prepSaved').innerHTML =
        '<p class="muted small">Nothing saved yet. Walk a line and pick your move.</p>';
      return;
    }
    $('prepSaved').innerHTML = `
      <ul class="prep-list">
        ${prep.slice(0, 40).map((e) => `
          <li>
            <button class="prep-jump" data-key="${esc(e.key)}">
              <span class="prep-jump-line">${esc((e.line || []).join(' ') || 'start')}</span>
              <b>${esc(e.answer)}</b>
              <span class="muted small">${esc(e.opening || '')}</span>
            </button>
            <button class="btn btn-ghost prep-drop" data-key="${esc(e.key)}"
                    aria-label="Remove ${esc(e.answer)}">Remove</button>
          </li>`).join('')}
      </ul>`;
    $('prepSaved').querySelectorAll('.prep-jump').forEach((b) => {
      b.addEventListener('click', () => {
        const e = prep.find((x) => x.key === b.dataset.key);
        if (!e) return;
        state.colour = e.color === 'black' ? 'black' : 'white';
        syncColourButtons();
        state.san = (e.line || []).slice();
        load();
      });
    });
    $('prepSaved').querySelectorAll('.prep-drop').forEach((b) => {
      b.addEventListener('click', () => {
        S.repertoire.remove(b.dataset.key);
        render();
      });
    });
  }

  function syncColourButtons() {
    document.querySelectorAll('[data-prep-colour]').forEach((b) => {
      b.classList.toggle('is-active', b.dataset.prepColour === state.colour);
    });
  }

  /* ---------------------------------------------------------------------- wire */
  function init() {
    if (!$('prepBoard')) return;
    document.querySelectorAll('[data-prep-colour]').forEach((b) => {
      b.addEventListener('click', () => {
        state.colour = b.dataset.prepColour === 'black' ? 'black' : 'white';
        syncColourButtons();
        reset();
      });
    });
    $('prepBack').addEventListener('click', back);
    $('prepReset').addEventListener('click', reset);
    syncColourButtons();
  }

  window.Prep = {
    init,
    render() {
      if (!state.pos) load();
      else render();
    },
    START,
  };
}());
