/* Opening Leak Lab — the learning half of the dashboard.

   Three panes share one board component (board.js):
     review   — the flagged position, your move, the better moves, then play it on
     practice — the same positions as drills: find the improvement yourself
     library  — free exploration of the local opening book from any position
*/
(function () {
  'use strict';

  const LB = window.LeakBoard;
  const $ = (id) => document.getElementById(id);
  const esc = LB.esc;
  const num = (v) => {
    const n = parseFloat(v);
    return Number.isFinite(n) ? n : null;
  };

  const DEPTH = 12;
  const state = {
    rows: [],
    review: null,
    drill: null,
    library: null,
    session: { seen: 0, best: 0, good: 0, missed: 0 },
    onQueueChange: null,
  };

  /* ------------------------------------------------------------------ shared */
  /* One "Ask the engine" everywhere: same label, same states, same output.
     Callers supply the button, the pane, and where the position comes from. */
  const ENGINE_LABEL = 'Ask the engine';

  async function askEngine({ button, pane, position, onPlay }) {
    const btn = $(button);
    const target = $(pane);
    btn.disabled = true;
    btn.textContent = 'Thinking…';
    target.innerHTML = '<p class="muted small">Stockfish is thinking…</p>';
    try {
      const pos = position();
      if (!pos) throw new Error('no position on the board yet');
      const result = await LB.engine(pos.fen, { depth: DEPTH, multipv: 3 });
      LB.renderEngine(target, result, {
        onPlay: (uci) => {
          const move = pos.legal.find((m) => m.uci === uci);
          if (move && onPlay) onPlay(move);
        },
      });
    } catch (err) {
      target.innerHTML = `<p class="muted small">Engine unavailable: ${esc(err.message)}</p>`;
    } finally {
      btn.disabled = false;
      btn.textContent = ENGINE_LABEL;
    }
  }

  function sanToMove(legal, san) {
    if (!san) return null;
    const clean = String(san).replace(/[!?]+$/, '');
    return legal.find((m) => m.san === clean) || legal.find((m) => m.san.replace(/[+#]/g, '') === clean.replace(/[+#]/g, '')) || null;
  }

  /** SAN strip with real move numbers, given the first mover and move number. */
  function moveStrip(history, startNumber = 1, startTurn = 'white') {
    if (!history.length) return '<span class="muted">start of the line</span>';
    let number = startNumber;
    let turn = startTurn;
    return history
      .map((h, i) => {
        const label = turn === 'white' ? `${number}.` : i === 0 ? `${number}…` : '';
        const html = `<button type="button" class="ply" data-i="${i + 1}">${label}${esc(h.san)}</button>`;
        if (turn === 'black') number += 1;
        turn = turn === 'white' ? 'black' : 'white';
        return html;
      })
      .join(' ');
  }

  function wireStrip(el, history, onJump) {
    el.querySelectorAll('.ply').forEach((btn) => {
      btn.addEventListener('click', () => onJump(+btn.dataset.i));
    });
    void history;
  }

  function verdictFor(lossCp) {
    if (lossCp <= 20) return { kind: 'best', label: 'Best move' };
    if (lossCp <= 60) return { kind: 'good', label: 'Strong — as good as the engine\'s pick for practical purposes' };
    if (lossCp <= 150) return { kind: 'ok', label: 'Playable, but there is more on offer' };
    return { kind: 'bad', label: 'This gives ground away' };
  }

  /* ------------------------------------------------------------------ review */
  const review = {
    board: null,
    row: null,
    base: null,
    history: [],
    auto: true,
    thinking: false,

    async open(row) {
      state.review = row;
      this.row = row;
      this.history = [];
      const startNumber = num(row.move_number) || 1;
      this.startNumber = startNumber;
      if (!this.board) {
        this.board = new LB.Board($('board'), {
          orientation: row.player_color === 'black' ? 'black' : 'white',
          onMove: (m) => this.play(m),
        });
      }
      this.board.setOrientation(row.player_color === 'black' ? 'black' : 'white');
      this.base = await this.loadBase(row);
      await this.show(this.base, { arrows: [], marks: [] });
      this.hintYourMove();
      $('reviewEngine').innerHTML = '<p class="muted small">Ask the engine when you want the full picture from this position.</p>';
    },

    /** The position before the flagged move, rebuilt from the report line when possible
        so the opening name and move numbers are real rather than guessed from a FEN. */
    async loadBase(row) {
      const line = String(row.variation_line || '').trim().split(/\s+/).filter(Boolean);
      if (line.length) {
        try {
          const pos = await LB.position(null, null, line.slice(0, -1));
          if (pos.fen === row.fen) return pos;
        } catch (err) {
          /* the line did not replay — fall back to the bare FEN below */
        }
      }
      return LB.position(row.fen);
    },

    async show(pos, { arrows = [], lastMove = null } = {}) {
      this.current = pos;
      if (window.App) window.App.setFen(pos.fen);
      this.board.setPosition(pos.fen, { legal: pos.legal, arrows, lastMove });
      $('lichessLink').href = `https://lichess.org/analysis/standard/${encodeURIComponent(pos.fen.replace(/ /g, '_'))}`;
      $('reviewLine').innerHTML = moveStrip(this.history, this.startNumber, this.base ? this.base.turn : 'white');
      wireStrip($('reviewLine'), this.history, (i) => this.jump(i));
      const mine = sanToMove(pos.legal, this.row.your_move);
      const best = sanToMove(pos.legal, this.row.engine_best_1);
      const highlight = [];
      if (this.history.length === 0) {
        if (mine) highlight.push({ uci: mine.uci, kind: 'leak', label: 'your move' });
        if (best && (!mine || best.uci !== mine.uci)) highlight.push({ uci: best.uci, kind: 'best', label: 'engine' });
      }
      LB.renderBook($('reviewBook'), pos.book, {
        highlight,
        onPlay: (uci) => {
          const move = pos.legal.find((m) => m.uci === uci);
          if (move) this.play(move);
        },
        emptyText: 'This position is past the end of the book — the engine panel still works.',
      });
      const name = pos.opening && pos.opening.name ? `${pos.opening.eco} ${pos.opening.name}` : '';
      $('reviewName').textContent = name || this.row.opening || this.row.eco || 'Not a named opening';
      $('reviewTurn').textContent = `${pos.turn === 'white' ? 'White' : 'Black'} to move`;
    },

    hintYourMove() {
      const yours = this.row.your_move;
      const gap = num(this.row.score_gap_vs_db_pct);
      const drop = num(this.row.eval_drop_pawns);
      const bits = [`You played <b>${esc(yours)}</b> here in ${this.row.your_games} game${+this.row.your_games === 1 ? '' : 's'}`];
      if (num(this.row.your_score_pct) !== null) bits.push(`scoring ${num(this.row.your_score_pct).toFixed(0)}%`);
      if (gap !== null && gap < 0) bits.push(`${Math.abs(gap).toFixed(1)}% below the book`);
      if (drop) bits.push(`and the engine evaluation falls ${drop.toFixed(2)} pawns`);
      $('reviewStatus').innerHTML = `${bits.join(', ')}. Play a move on the board to try something else.`;
      $('reviewStatus').className = 'board-status';
    },

    async play(move) {
      if (this.thinking) return;
      const pos = await LB.position(move.fen_after);
      this.history.push({ san: move.san, uci: move.uci, fen: move.fen_after });
      await this.show(pos, { lastMove: move });
      const flagged = this.history.length === 1 && move.san === this.row.your_move;
      const isBest = this.history.length === 1 && move.san === this.row.engine_best_1;
      if (flagged) {
        $('reviewStatus').innerHTML = `<b>${esc(move.san)}</b> is the move the report flagged. Step back and try one of the alternatives.`;
        $('reviewStatus').className = 'board-status is-bad';
      } else if (isBest) {
        $('reviewStatus').innerHTML = `<b>${esc(move.san)}</b> is the engine's first choice here. Keep going and the book will answer.`;
        $('reviewStatus').className = 'board-status is-good';
      } else {
        const bookMove = (pos.book && this.previousBookEntry(move)) || null;
        $('reviewStatus').innerHTML = bookMove
          ? `<b>${esc(move.san)}</b> — ${bookMove.games.toLocaleString()} book games, scoring ${bookMove.score === null ? '—' : bookMove.score.toFixed(1) + '%'}.`
          : `<b>${esc(move.san)}</b> played. The book has no games with it from here.`;
        $('reviewStatus').className = 'board-status';
      }
      if (this.auto) await this.bookReply(pos);
    },

    previousBookEntry(move) {
      const before = this.history.length > 1 ? null : this.base;
      if (!before || !before.book) return null;
      return before.book.moves.find((m) => m.uci === move.uci) || null;
    },

    async bookReply(pos) {
      const mySide = this.row.player_color === 'black' ? 'black' : 'white';
      if (pos.turn === mySide || !pos.book || !pos.book.moves.length) return;
      const reply = pos.book.moves[0];
      const move = pos.legal.find((m) => m.uci === reply.uci);
      if (!move) return;
      this.thinking = true;
      await new Promise((r) => setTimeout(r, 420));
      const next = await LB.position(move.fen_after);
      this.history.push({ san: move.san, uci: move.uci, fen: move.fen_after });
      await this.show(next, { lastMove: move });
      $('reviewStatus').innerHTML += ` The book replies <b>${esc(move.san)}</b> (${reply.share.toFixed(0)}% of games).`;
      this.thinking = false;
    },

    async jump(i) {
      this.history = this.history.slice(0, i);
      const fen = i === 0 ? this.row.fen : this.history[i - 1].fen;
      const pos = await LB.position(fen);
      await this.show(pos, { lastMove: null });
      if (i === 0) this.hintYourMove();
    },

    async reset() {
      this.history = [];
      await this.show(this.base, {});
      this.hintYourMove();
    },

    async showMine() {
      await this.reset();
      const move = sanToMove(this.base.legal, this.row.your_move);
      if (!move) return;
      this.board.setArrows([{ from: move.from, to: move.to, kind: 'played' }]);
      $('reviewStatus').innerHTML = `Red arrow: <b>${esc(move.san)}</b>, the move that costs you points here.`;
      $('reviewStatus').className = 'board-status is-bad';
    },

    async showBest() {
      await this.reset();
      const arrows = [];
      const mine = sanToMove(this.base.legal, this.row.your_move);
      if (mine) arrows.push({ from: mine.from, to: mine.to, kind: 'played' });
      const names = [this.row.engine_best_1, this.row.engine_best_2, this.row.engine_best_3].filter(Boolean);
      const shown = [];
      names.forEach((san, i) => {
        const move = sanToMove(this.base.legal, san);
        if (!move || (mine && move.uci === mine.uci)) return;
        arrows.push({ from: move.from, to: move.to, kind: i === 0 ? 'best' : 'book' });
        shown.push(san);
      });
      this.board.setArrows(arrows);
      $('reviewStatus').innerHTML = shown.length
        ? `Green: <b>${esc(shown[0])}</b>, the engine's pick${shown.length > 1 ? `; amber: ${shown.slice(1).map(esc).join(', ')}` : ''}. Click the piece to play it.`
        : 'The report has no engine alternatives for this position — run with the engine enabled.';
      $('reviewStatus').className = 'board-status is-good';
    },

    askEngine() {
      return askEngine({
        button: 'reviewEngineBtn',
        pane: 'reviewEngine',
        position: () => this.current,
        onPlay: (move) => this.play(move),
      });
    },

    /* The move the user has actually put on the board, if any: what "Commit this
       move" commits. Falls back to the engine's first choice. */
    currentAnswer() {
      if (this.history.length) return this.history[0].san;
      return this.row ? this.row.engine_best_1 || '' : '';
    },
  };

  /* ---------------------------------------------------------------- practice */
  const drill = {
    board: null,
    queue: [],
    index: 0,
    answered: false,

    setRows(rows) {
      this.queue = rows
        .filter((r) => r.fen && r.your_move)
        .slice()
        .sort((a, b) => (num(b.cost) || 0) - (num(a.cost) || 0))
        .slice(0, 15);
      state.session = { seen: 0, best: 0, good: 0, missed: 0 };
      this.index = 0;
      this.announce();
      if (this.queue.length) this.load(0);
      this.renderScore();
    },

    /** Put one position at the front of the queue — the "Drill this" button. */
    add(row) {
      const at = this.queue.findIndex((r) => r.fen === row.fen && r.your_move === row.your_move);
      if (at >= 0) {
        this.announce();
        this.load(at);
        return at;
      }
      this.queue.unshift(row);
      this.announce();
      this.load(0);
      return 0;
    },

    /* The practice view owns its own headings, so tell it what is in the queue
       rather than writing into elements that only exist on one screen. */
    announce() {
      $('practiceBody').hidden = this.queue.length === 0;
      if (state.onQueueChange) state.onQueueChange(this.queue.slice());
    },

    async load(i) {
      this.index = Math.max(0, Math.min(i, this.queue.length - 1));
      const row = this.queue[this.index];
      this.row = row;
      this.answered = false;
      const side = row.player_color === 'black' ? 'black' : 'white';
      if (!this.board) {
        this.board = new LB.Board($('drillBoard'), { orientation: side, onMove: (m) => this.attempt(m) });
      }
      this.board.setOrientation(side);
      this.pos = await LB.position(row.fen);
      this.board.setPosition(this.pos.fen, { legal: this.pos.legal });
      const scored = num(row.your_score_pct);
      $('drillPrompt').innerHTML =
        `<b>${esc(row.opening || row.eco || 'Unnamed opening')}</b> · move ${row.move_number} as ${esc(side)}<br />` +
        `<span class="mono">${esc(row.variation_line || '')}</span><br />` +
        `You have played <b>${esc(row.your_move)}</b> here ${row.your_games} time${+row.your_games === 1 ? '' : 's'}` +
        `${scored === null ? '' : `, scoring ${scored.toFixed(0)}%`}. Find something better.`;
      $('drillFeedback').hidden = true;
      $('drillFeedback').className = 'drill-feedback';
      $('drillCount').textContent = `${this.index + 1} / ${this.queue.length}`;
      $('nextBtn').disabled = this.index >= this.queue.length - 1;
      this.renderQueue();
    },

    renderQueue() {
      $('drillQueue').innerHTML = this.queue
        .map(
          (r, i) =>
            `<li class="${i === this.index ? 'is-current' : ''}" data-i="${i}">` +
            `<span class="q-move mono">${esc(r.your_move)}</span>` +
            `<span class="q-open">${esc(r.opening || r.eco || '—')}</span>` +
            `<span class="q-lost mono">${num(r.lost_points) ? '−' + num(r.lost_points).toFixed(1) : ''}</span>` +
            (r.solved ? '<span class="q-tick" aria-label="solved">✓</span>' : '') +
            '</li>'
        )
        .join('');
      $('drillQueue').querySelectorAll('li').forEach((li) => {
        li.addEventListener('click', () => this.load(+li.dataset.i));
      });
    },

    renderScore() {
      const s = state.session;
      $('drillScore').innerHTML =
        `<div class="stat"><div class="stat-label">Attempted</div><div class="stat-value">${s.seen}</div></div>` +
        `<div class="stat"><div class="stat-label">Engine's pick</div><div class="stat-value">${s.best}</div></div>` +
        `<div class="stat"><div class="stat-label">Close enough</div><div class="stat-value">${s.good}</div></div>` +
        `<div class="stat"><div class="stat-label">Missed</div><div class="stat-value">${s.missed}</div></div>`;
    },

    async attempt(move) {
      const fb = $('drillFeedback');
      fb.hidden = false;
      fb.className = 'drill-feedback';
      fb.innerHTML = `<b>${esc(move.san)}</b> — checking with Stockfish…`;
      this.board.setPosition(this.pos.fen, {
        legal: this.pos.legal,
        arrows: [{ from: move.from, to: move.to, kind: 'played' }],
      });
      let verdict;
      let bestLine = null;
      try {
        const [before, after] = await Promise.all([
          LB.engine(this.pos.fen, { depth: DEPTH, multipv: 3 }),
          LB.engine(move.fen_after, { depth: DEPTH, multipv: 1 }),
        ]);
        bestLine = before.lines[0] || null;
        const bestCp = bestLine ? bestLine.cp : 0;
        const mineCp = after.lines && after.lines.length ? -after.lines[0].cp : bestCp;
        const loss = Math.max(0, bestCp - mineCp);
        verdict = verdictFor(loss);
        verdict.detail =
          `${esc(move.san)} keeps ${LB.cpText(mineCp)}, the engine's ${esc(bestLine ? bestLine.san : '—')} keeps ${LB.cpText(bestCp)}` +
          ` (${(loss / 100).toFixed(2)} pawns apart, depth ${before.depth}).`;
        if (bestLine) {
          const bestMove = this.pos.legal.find((m) => m.uci === bestLine.uci);
          if (bestMove && bestMove.uci !== move.uci) {
            this.board.setArrows([
              { from: move.from, to: move.to, kind: 'played' },
              { from: bestMove.from, to: bestMove.to, kind: 'best' },
            ]);
          }
        }
      } catch (err) {
        verdict = { kind: 'ok', label: 'Engine unavailable', detail: esc(err.message) };
      }

      const bookEntry = this.pos.book ? this.pos.book.moves.find((m) => m.uci === move.uci) : null;
      const bookNote = bookEntry
        ? `The book has ${bookEntry.games.toLocaleString()} games with it, scoring ${bookEntry.score === null ? '—' : bookEntry.score.toFixed(1) + '%'}.`
        : 'The book has no games with this move from here.';
      const repeated = move.san === this.row.your_move ? ' That is the move the report flagged.' : '';
      fb.className = `drill-feedback is-${verdict.kind}`;
      fb.innerHTML = `<b>${esc(verdict.label)}</b><span>${verdict.detail}${repeated}</span><span class="muted">${bookNote}</span>`;

      if (!this.answered) {
        this.answered = true;
        state.session.seen += 1;
        if (verdict.kind === 'best') state.session.best += 1;
        else if (verdict.kind === 'good') state.session.good += 1;
        else state.session.missed += 1;
        this.row.solved = verdict.kind === 'best' || verdict.kind === 'good';
        this.record(this.row, this.row.solved);
        this.renderScore();
        this.renderQueue();
      }
    },

    /** One attempt, kept so Progress can show retention and a review date. */
    record(row, correct) {
      if (!window.Store || !row) return;
      const label = `${row.opening || row.eco || 'Opening'} · ${row.variation_line || row.your_move}`;
      window.Store.drills.attempt(window.Store.leakKey(row), correct, label);
    },

    async reveal() {
      const fb = $('drillFeedback');
      fb.hidden = false;
      fb.className = 'drill-feedback is-best';
      fb.innerHTML = '<b>Answer</b><span>Asking the engine…</span>';
      try {
        const result = await LB.engine(this.pos.fen, { depth: DEPTH, multipv: 3 });
        const arrows = result.lines.slice(0, 3).map((l, i) => {
          const move = this.pos.legal.find((m) => m.uci === l.uci);
          return move ? { from: move.from, to: move.to, kind: i === 0 ? 'best' : 'book' } : null;
        });
        this.board.setArrows(arrows.filter(Boolean));
        fb.innerHTML =
          '<b>Answer</b><span>' +
          result.lines
            .slice(0, 3)
            .map((l) => `${esc(l.san)} (${esc(l.eval || LB.cpText(l.cp))})`)
            .join(', ') +
          `</span><span class="muted">Depth ${result.depth}. Your move here was ${esc(this.row.your_move)}.</span>`;
        if (!this.answered) {
          this.answered = true;
          state.session.seen += 1;
          state.session.missed += 1;
          this.record(this.row, false);
          this.renderScore();
        }
      } catch (err) {
        fb.innerHTML = `<b>Answer</b><span>Engine unavailable: ${esc(err.message)}</span>`;
      }
    },

    async retry() {
      this.board.setPosition(this.pos.fen, { legal: this.pos.legal });
      $('drillFeedback').hidden = true;
    },
  };

  /* ----------------------------------------------------------------- library */
  const library = {
    board: null, fromFen: null, moves: [], history: [], future: [], pos: null,
    seq: 0, searchSeq: 0, busy: false,
    async init() {
      if (!this.board) this.board = new LB.Board($('libBoard'), { onMove: (m) => this.run(() => this.play(m)) });
      await this.load();
    },
    async run(action) {
      try { await action(); }
      catch (err) { this.error(err); }
    },
    error(err) {
      $('exploreError').hidden = false;
      $('exploreError').textContent = `The board could not update. Your line is unchanged. ${err.message}`;
      $('exploreRetry').hidden = false;
    },
    async load(lastMove = null, candidate = {}) {
      const seq = ++this.seq;
      const next = { fromFen: this.fromFen, moves: this.moves, history: this.history, future: this.future, ...candidate };
      this.busy = true;
      $('libBoard').setAttribute('aria-busy', 'true');
      $('saveExplorerLine').disabled = true;
      $('openSaveLine').disabled = true;
      try {
        const pos = await LB.position(next.fromFen, next.moves);
        if (seq !== this.seq) return;
        Object.assign(this, next, { pos });
        this.board.setPosition(pos.fen, { legal: pos.legal, lastMove });
        if (window.App) window.App.setLibFen(pos.fen);
        $('libLichess').href = `https://lichess.org/analysis/standard/${encodeURIComponent(pos.fen.replace(/ /g, '_'))}`;
        $('libName').textContent = pos.opening?.name ? `${pos.opening.eco} ${pos.opening.name}` : !this.fromFen && !this.moves.length ? 'Starting position' : 'Your explored position';
        $('libTurn').textContent = `${pos.turn === 'white' ? 'White' : 'Black'} to move`;
        $('libStats').textContent = pos.book?.total
          ? `${pos.book.total.toLocaleString()} book games · ${pos.turn} scores ${pos.book.score == null ? '—' : pos.book.score.toFixed(1) + '%'}. Observed results, not a move recommendation.`
          : 'Outside the book. You can still play legal moves and save your line.';
        const timeline = [...this.history, ...this.future];
        $('libLine').innerHTML = timeline.length ? moveStrip(timeline, this.startNumber(), this.startTurn()) : '<span class="muted">Select a piece to see its legal moves.</span>';
        $('libLine').querySelectorAll('.ply').forEach((button) => {
          button.classList.toggle('is-future', Number(button.dataset.i) > this.history.length);
          button.classList.toggle('is-current', Number(button.dataset.i) === this.history.length);
        });
        wireStrip($('libLine'), timeline, (i) => this.run(() => this.jump(i)));
        $('libForward').disabled = !this.future.length;
        $('libRestart').disabled = !this.history.length;
        window.dispatchEvent(new CustomEvent('chess:position', { detail: { line: this.history.map((m) => m.san), turn: pos.turn, opening: pos.opening } }));
        $('libBack').disabled = this.moves.length === 0;
        LB.renderBook($('libBook'), pos.book, {
          onPlay: (uci) => { const move = this.pos.legal.find((m) => m.uci === uci); if (move) this.run(() => this.play(move)); },
          emptyText: 'No book games at this position. Try another line, or keep exploring on the board.',
        });
        $('libEngine').innerHTML = '<p class="muted small">Ask the engine for an independent verdict on this position.</p>';
        $('exploreError').hidden = true; $('exploreRetry').hidden = true;
        $('saveLineStatus').textContent = '';
      } finally {
        if (seq === this.seq) {
          this.busy = false;
          $('libBoard').setAttribute('aria-busy', 'false');
          $('saveExplorerLine').disabled = !this.history.length;
          $('openSaveLine').disabled = !this.history.length;
        }
      }
    },
    startNumber() { return this.fromFen ? parseInt(this.fromFen.split(' ')[5], 10) || 1 : 1; },
    startTurn() { return this.fromFen?.split(' ')[1] === 'b' ? 'black' : 'white'; },
    async play(move) {
      if (this.busy) return;
      if (this.controller) return this.controller(move);
      await this.load(move, { moves: [...this.moves, move.uci], history: [...this.history, { san: move.san, uci: move.uci }], future: this.future[0]?.uci === move.uci ? this.future.slice(1) : [] });
    },
    async back() { if (this.history.length) await this.jump(this.history.length - 1); },
    async forward() { if (this.future.length) await this.jump(this.history.length + 1); },
    async jump(i) {
      if (this.busy) return;
      const timeline = [...this.history, ...this.future];
      const prefix = timeline.slice(0, i);
      await this.load(null, { moves: prefix.map((h) => h.uci), history: prefix, future: timeline.slice(i) });
    },
    async reset() {
      await this.load(null, { fromFen: null, moves: [], history: [], future: [] });
      window.Workspace?.custom('Opening board');
      $('saveLineName').value = ''; $('saveLineNote').value = '';
    },
    async openLine(san, fen) {
      // Rebuild the complete history from the supplied starting position. Saving
      // and back navigation must retain the user's actual move order.
      const seq = ++this.seq;
      let pos = null;
      const history = [];
      const moves = [];
      this.busy = true;
      try {
        for (const notation of san || []) {
          pos = await LB.position(fen || null, moves);
          if (seq !== this.seq) return;
          const move = sanToMove(pos.legal, notation);
          if (!move) throw new Error(`Could not replay ${notation}.`);
          history.push({ san: move.san, uci: move.uci }); moves.push(move.uci);
        }
        if (seq !== this.seq) return;
        await this.load(null, { fromFen: fen || null, moves, history, future: [] });
      } finally { if (seq === this.seq) this.busy = false; }
    },
    async search(q) {
      const seq = ++this.searchSeq;
      const target = $('libResults');
      if (!q.trim()) { target.innerHTML = ''; return; }
      target.innerHTML = '<li class="muted small">Searching openings…</li>';
      try {
        const { results } = await LB.searchOpenings(q, 12);
        if (seq !== this.searchSeq) return;
        target.innerHTML = results.length ? results.map((r, i) => `<li><button class="opening-search-hit" data-i="${i}"><span class="eco mono">${esc(r.eco)}</span><span class="name">${esc(r.name)}</span><span class="games mono">${r.games.toLocaleString()} games</span></button></li>`).join('') : '<li class="muted small">No named opening matches. Try another name or ECO code, or enter moves below.</li>';
        target.querySelectorAll('button').forEach((button) => button.addEventListener('click', () => this.run(async () => {
          const hit = results[+button.dataset.i];
          await this.openLine([], hit.fen);
          window.App.go('today');
          window.Workspace.custom(hit.name, 'A position from the opening database. Compare replies in Moves, or try a continuation on the board.');
          $('saveLineName').value = hit.name;
          $('saveLineNote').value = '';
        })));
      } catch (err) { if (seq === this.searchSeq) target.innerHTML = `<li class="muted small">Search unavailable: ${esc(err.message)}. You can still try a starting-point card.</li>`; }
    },
    async save() {
      if (this.busy || !this.history.length) return;
      const side = $('saveLineSide').value;
      const startWhite = this.startTurn() === 'white';
      let i = this.history.length - 1;
      while (i >= 0 && ((i % 2 === 0) === startWhite ? 'white' : 'black') !== side) i -= 1;
      if (i < 0) { $('saveLineStatus').textContent = `Play a ${side} move before saving a choice for this side.`; return; }
      this.busy = true;
      $('saveExplorerLine').disabled = true;
      $('openSaveLine').disabled = true;
      try {
        const pos = await LB.position(this.fromFen, this.moves.slice(0, i));
        const move = this.history[i];
        const entry = window.Store.repertoire.commitPrep({
          fen: pos.fen, move: move.san, color: side,
          eco: this.pos.opening?.eco || '', opening: this.pos.opening?.name || '',
          line: this.history.slice(0, i).map((h) => h.san), moveNumber: pos.move_number,
          name: $('saveLineName').value.trim() || this.pos.opening?.name || 'My opening line',
          notes: $('saveLineNote').value.trim(), startFen: this.fromFen || '',
          explorePath: this.history.map((h) => h.san),
        });
        const persisted = window.Store.savedLocally(entry);
        $('saveLineStatus').innerHTML = persisted ? 'Saved on this device. <a href="#repertoire">See it in Repertoire →</a>' : 'Kept in this tab only. Device storage is unavailable; export your repertoire before closing.';
      } finally { this.busy = false; $('saveExplorerLine').disabled = !this.history.length;
          $('openSaveLine').disabled = !this.history.length; }
    },
    askEngine() { return askEngine({ button: 'libEngineBtn', pane: 'libEngine', position: () => this.pos, onPlay: (move) => this.play(move) }); },
  };
  /* ------------------------------------------------------------------ wiring */
  function wire() {
    $('reviewMine').addEventListener('click', () => review.showMine());
    $('reviewBest').addEventListener('click', () => review.showBest());
    $('reviewReset').addEventListener('click', () => review.reset());
    $('reviewFlip').addEventListener('click', () => review.board && review.board.flip());
    $('reviewEngineBtn').addEventListener('click', () => review.askEngine());
    $('reviewAuto').addEventListener('change', (e) => {
      review.auto = e.target.checked;
    });
    $('drillBtn').addEventListener('click', () => {
      if (!review.row) return;
      drill.add(review.row);
      if (window.App) window.App.drill();
    });

    $('drillNext').addEventListener('click', () => drill.load(drill.index + 1));
    $('drillPrev').addEventListener('click', () => drill.load(drill.index - 1));
    $('nextBtn').addEventListener('click', () => drill.load(drill.index + 1));
    $('drillAnswer').addEventListener('click', () => drill.reveal());
    $('drillRetry').addEventListener('click', () => drill.retry());
    $('drillFlip').addEventListener('click', () => drill.board && drill.board.flip());

    $('libBack').addEventListener('click', () => library.run(() => library.back()));
    $('libForward').addEventListener('click', () => library.run(() => library.forward()));
    $('libRestart').addEventListener('click', () => library.run(() => library.jump(0)));
    $('libReset').addEventListener('click', () => library.run(() => library.reset()));
    $('libFlip').addEventListener('click', () => library.board && library.board.flip());
    $('libEngineBtn').addEventListener('click', () => library.run(() => library.askEngine()));
    $('saveExplorerLine').addEventListener('click', () => library.run(() => library.save()));
    $('openSaveLine').addEventListener('click', () => {
      if (!$('saveLineName').value.trim()) $('saveLineName').value = library.pos?.opening?.name || 'My opening line';
      $('saveLineDialog').showModal();
    });
    $('saveLineClose').addEventListener('click', () => $('saveLineDialog').close());
    $('exploreRetry').addEventListener('click', () => library.run(() => library.init()));
    $('explorePositionForm').addEventListener('submit', async (event) => {
      event.preventDefault();
      const value = $('explorePositionInput').value.trim();
      $('explorePositionError').textContent = '';
      try {
        if (value.includes('/')) await library.openLine([], value);
        else await library.openLine(value.replace(/\d+\.(?:\.\.)?/g, ' ').trim().split(/\s+/).filter(Boolean), null);
        window.Workspace.custom('Your position');
      } catch (err) { $('explorePositionError').textContent = `Could not open that position: ${err.message}`; }
    });
    let timer = null;
    $('libSearch').addEventListener('input', (e) => {
      clearTimeout(timer);
      const q = e.target.value.trim();
      timer = setTimeout(() => library.search(q), 300);
    });
  }

  window.Study = {
    training: {
      begin(onMove) {
        library.trainingOrientation = library.board?.orientation || 'white';
        library.seq += 1;
        library.busy = false;
        library.controller = onMove;
      },
      present(pos, { enabled = true, arrows = [], lastMove = null, orientation = 'white', title = 'Italian' } = {}) {
        if (!library.controller || !library.board) return;
        library.board.setOrientation(orientation);
        library.board.setPosition(pos.fen, { legal: enabled ? pos.legal : [], arrows, lastMove });
        $('libBoard').setAttribute('aria-busy', 'false');
        $('libTurn').textContent = `${pos.turn === 'white' ? 'White' : 'Black'} to move`;
        $('libName').textContent = title;
        window.App?.setLibFen(pos.fen);
      },
      async end() { library.controller = null; library.board?.setOrientation(library.trainingOrientation || 'white'); await library.run(() => library.load()); },
    },
    init(apiBase) {
      LB.setApiBase(apiBase);
      wire();
      library.run(() => library.init());
    },
    review: (row) => review.open(row).catch((err) => {
      $('reviewStatus').textContent = `Could not load the board: ${err.message}`;
    }),
    setRows(rows) {
      state.rows = rows || [];
      drill.setRows(state.rows);
    },
    /** Called with the drill queue whenever it changes, so the practice view can
        render its own heading and empty state. */
    onQueueChange(fn) {
      state.onQueueChange = fn;
      if (state.rows.length || drill.queue.length) drill.announce();
    },
    queue: () => drill.queue.slice(),
    /** Put one leak on the drill board — the clinic's Drill tab. */
    drillRow(row) {
      const at = drill.queue.findIndex((r) => r.fen === row.fen && r.your_move === row.your_move);
      if (at >= 0) drill.load(at);
      else drill.add(row);
    },
    /** Put a line on the explorer board (used by the openings explorer). */
    explore: async (san, fen, { fromPosition = false, orientation } = {}) => {
      if (orientation) library.board?.setOrientation(orientation);
      try {
        await library.openLine(san, fromPosition ? fen : null);
      } catch (err) {
        if (fen && !fromPosition) {
          try { await library.openLine([], fen); return; } catch (fallback) { library.error(fallback); }
        } else library.error(err);
      }
    },
    replay: (san, orientation) => library.run(async () => {
      library.board?.setOrientation(orientation);
      await library.openLine(san, null);
      await library.jump(0);
    }),
    /** The move currently on the board in the fix panel. */
    currentAnswer: () => review.currentAnswer(),
    currentRow: () => review.row || null,
  };
})();
