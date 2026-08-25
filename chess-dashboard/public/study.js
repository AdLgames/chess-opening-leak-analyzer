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
  let apiBase = '';
  const state = {
    rows: [],
    review: null,
    drill: null,
    library: null,
    session: { seen: 0, best: 0, good: 0, missed: 0 },
  };

  /* ------------------------------------------------------------------ shared */
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
      this.board.setPosition(pos.fen, { legal: pos.legal, arrows, lastMove });
      $('fenText').textContent = pos.fen;
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

    async askEngine() {
      const btn = $('reviewEngineBtn');
      const target = $('reviewEngine');
      btn.disabled = true;
      target.innerHTML = '<p class="muted small">Stockfish is thinking…</p>';
      try {
        const result = await LB.engine(this.current.fen, { depth: DEPTH, multipv: 3 });
        LB.renderEngine(target, result, {
          onPlay: (uci) => {
            const move = this.current.legal.find((m) => m.uci === uci);
            if (move) this.play(move);
          },
        });
      } catch (err) {
        target.innerHTML = `<p class="muted small">Engine unavailable: ${esc(err.message)}</p>`;
      } finally {
        btn.disabled = false;
      }
    },
  };

  /* The review schedule lives on the server, so a session picked up tomorrow continues
     where this one left off. Failures come back twice: later in this sitting, and sooner
     in the day-scale schedule. */
  const epdOf = (fen) => String(fen || '').split(' ').slice(0, 4).join(' ');

  /* Mirror of `review.requeue_within_session`: a missed position moves a few places down
     the queue rather than off it — far enough that the answer is no longer on screen,
     near enough to be the same sitting. */
  function requeue(queue, index, gap = 3) {
    if (!queue.length || index < 0 || index >= queue.length) return queue;
    const item = queue[index];
    const rest = queue.slice(0, index).concat(queue.slice(index + 1));
    const target = Math.min(index + gap, rest.length);
    return rest.slice(0, target).concat([item], rest.slice(target));
  }

  async function postJSON(path, body) {
    const res = await fetch(`${apiBase}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }

  const reviewSchedule = {
    async enrol(rows) {
      const positions = rows.slice(0, 100).map((r) => ({
        epd: epdOf(r.fen), color: r.player_color, uci: r.engine_best_1_uci || '',
        san: r.engine_best_1 || '', opening: r.opening || r.eco || '', line: r.variation_line || '',
      }));
      try {
        const { progress } = await postJSON('/api/drills/enrol', { positions });
        return progress;
      } catch {
        return null; // the review cycle is an extra, not a prerequisite
      }
    },
    async attempt(row, playedUci, cpLoss, revealed) {
      try {
        return await postJSON('/api/drills/attempt', {
          epd: epdOf(row.fen), color: row.player_color, played_uci: playedUci,
          cp_loss: cpLoss === null || cpLoss === undefined ? null : Math.round(cpLoss),
          revealed: !!revealed,
        });
      } catch {
        return null;
      }
    },
  };

  /* ---------------------------------------------------------------- practice */
  const drill = {
    board: null,
    queue: [],
    index: 0,
    answered: false,
    progress: null,
    lastLoss: null,

    setRows(rows) {
      this.queue = rows
        .filter((r) => r.fen && r.your_move)
        .slice()
        .sort((a, b) => (num(b.priority) || 0) - (num(a.priority) || 0))
        .slice(0, 15);
      state.session = { seen: 0, best: 0, good: 0, missed: 0 };
      this.index = 0;
      $('practiceEmpty').hidden = this.queue.length > 0;
      $('practiceBody').hidden = this.queue.length === 0;
      $('practiceHint').textContent = this.queue.length
        ? `${this.queue.length} position${this.queue.length === 1 ? '' : 's'} from your own games`
        : 'Run an analysis to build a drill set';
      if (this.queue.length) {
        this.load(0);
        // Take these positions into the review cycle. Already-tracked ones keep their
        // schedule, so re-running the analysis never wipes out progress.
        reviewSchedule.enrol(this.queue).then((progress) => {
          this.progress = progress;
          this.renderScore();
        });
      }
      this.renderScore();
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
      const p = this.progress;
      const longView = p
        ? `<div class="stat"><div class="stat-label">Known</div><div class="stat-value">${p.known}</div></div>` +
          `<div class="stat"><div class="stat-label">Still learning</div><div class="stat-value">${p.learning}</div></div>` +
          `<div class="stat"><div class="stat-label">Due today</div><div class="stat-value">${p.due}</div></div>`
        : '';
      $('drillScore').innerHTML = longView +
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
        this.lastLoss = loss;
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
        this.renderScore();
        this.renderQueue();

        const result = await reviewSchedule.attempt(this.row, move.uci, this.lastLoss, false);
        if (result) {
          this.progress = result.progress;
          fb.innerHTML += `<span class="muted">You will see this ${esc(result.due)}.</span>`;
          this.renderScore();
        }
        // A position you just missed comes back before the session ends — that repetition
        // is what makes it stick at all.
        if (!this.row.solved) {
          this.queue = requeue(this.queue, this.index);
          this.renderQueue();
        }
      }
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
      } catch (err) {
        fb.innerHTML = `<b>Answer</b><span>Engine unavailable: ${esc(err.message)}</span>`;
      }
      // Asking to be shown is a lapse whether or not the engine answered: the player has
      // told us they could not recall it, and that is the thing being scheduled.
      if (!this.answered) {
        this.answered = true;
        state.session.seen += 1;
        state.session.missed += 1;
        this.renderScore();
        const res = await reviewSchedule.attempt(this.row, '', null, true);
        if (res) {
          this.progress = res.progress;
          fb.innerHTML += `<span class="muted">You will see this ${esc(res.due)}.</span>`;
          this.renderScore();
        }
        this.queue = requeue(this.queue, this.index);
        this.renderQueue();
      }
    },

    async retry() {
      this.board.setPosition(this.pos.fen, { legal: this.pos.legal });
      $('drillFeedback').hidden = true;
    },
  };

  /* ----------------------------------------------------------------- library */
  const library = {
    board: null,
    fromFen: null,
    moves: [],
    history: [],

    async init() {
      if (this.board) return;
      this.board = new LB.Board($('libBoard'), { onMove: (m) => this.play(m) });
      await this.load();
      await this.search('');
    },

    async load(lastMove = null) {
      const pos = this.fromFen
        ? await LB.position(this.fromFen, this.moves)
        : await LB.position(null, this.moves);
      this.pos = pos;
      this.board.setPosition(pos.fen, { legal: pos.legal, lastMove });
      $('libFen').textContent = pos.fen;
      $('libLichess').href = `https://lichess.org/analysis/standard/${encodeURIComponent(pos.fen.replace(/ /g, '_'))}`;
      $('libName').textContent =
        pos.opening && pos.opening.name
          ? `${pos.opening.eco} ${pos.opening.name}`
          : !this.fromFen && !this.moves.length
            ? 'Starting position'
            : 'Out of the named book';
      $('libTurn').textContent = `${pos.turn === 'white' ? 'White' : 'Black'} to move`;
      $('libStats').textContent = pos.book && pos.book.total
        ? `${pos.book.total.toLocaleString()} book games from here · ${pos.turn} scores ${pos.book.score === null ? '—' : pos.book.score.toFixed(1) + '%'}`
        : 'No games in the book from here';
      $('libLine').innerHTML = moveStrip(this.history, this.startNumber(), this.startTurn || 'white');
      wireStrip($('libLine'), this.history, (i) => this.jump(i));
      $('libBack').disabled = this.moves.length === 0;
      LB.renderBook($('libBook'), pos.book, {
        onPlay: (uci) => {
          const move = pos.legal.find((m) => m.uci === uci);
          if (move) this.play(move);
        },
        emptyText: 'Nobody in the book reached this position — you are on your own from here.',
      });
      $('libEngine').innerHTML = '<p class="muted small">Ask the engine for an independent verdict on this position.</p>';
    },

    startNumber() {
      if (!this.fromFen) return 1;
      const parts = String(this.fromFen).split(' ');
      return parseInt(parts[5], 10) || 1;
    },

    async play(move) {
      this.moves.push(move.uci);
      this.history.push({ san: move.san, uci: move.uci });
      await this.load(move);
    },

    async back() {
      this.moves.pop();
      this.history.pop();
      await this.load();
    },

    async jump(i) {
      this.moves = this.moves.slice(0, i);
      this.history = this.history.slice(0, i);
      await this.load();
    },

    async reset() {
      this.fromFen = null;
      this.startTurn = 'white';
      this.moves = [];
      this.history = [];
      await this.load();
    },

    async search(q) {
      const target = $('libResults');
      try {
        const { results } = await LB.searchOpenings(q, 24);
        if (!results.length) {
          target.innerHTML = '<p class="muted small">No opening in the book matches that.</p>';
          return;
        }
        target.innerHTML = results
          .map(
            (r, i) =>
              `<li data-i="${i}"><span class="eco mono">${esc(r.eco)}</span><span class="name">${esc(r.name)}</span>` +
              `<span class="games mono">${r.games.toLocaleString()}</span></li>`
          )
          .join('');
        target.querySelectorAll('li').forEach((li) => {
          li.addEventListener('click', async () => {
            const hit = results[+li.dataset.i];
            this.fromFen = hit.fen;
            this.startTurn = hit.fen.split(' ')[1] === 'b' ? 'black' : 'white';
            this.moves = [];
            this.history = [];
            target.querySelectorAll('li').forEach((n) => n.classList.remove('is-current'));
            li.classList.add('is-current');
            await this.load();
          });
        });
      } catch (err) {
        target.innerHTML = `<p class="muted small">Search unavailable: ${esc(err.message)}</p>`;
      }
    },

    async askEngine() {
      const btn = $('libEngineBtn');
      const target = $('libEngine');
      btn.disabled = true;
      target.innerHTML = '<p class="muted small">Stockfish is thinking…</p>';
      try {
        const result = await LB.engine(this.pos.fen, { depth: DEPTH, multipv: 3 });
        LB.renderEngine(target, result, {
          onPlay: (uci) => {
            const move = this.pos.legal.find((m) => m.uci === uci);
            if (move) this.play(move);
          },
        });
      } catch (err) {
        target.innerHTML = `<p class="muted small">Engine unavailable: ${esc(err.message)}</p>`;
      } finally {
        btn.disabled = false;
      }
    },
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
    $('reviewDrill').addEventListener('click', () => {
      const i = drill.queue.findIndex((r) => r === review.row);
      if (i >= 0) drill.load(i);
      document.getElementById('practice').scrollIntoView({ behavior: 'smooth' });
    });

    $('drillNext').addEventListener('click', () => drill.load(drill.index + 1));
    $('drillPrev').addEventListener('click', () => drill.load(drill.index - 1));
    $('nextBtn').addEventListener('click', () => drill.load(drill.index + 1));
    $('drillAnswer').addEventListener('click', () => drill.reveal());
    $('drillRetry').addEventListener('click', () => drill.retry());
    $('drillFlip').addEventListener('click', () => drill.board && drill.board.flip());

    $('libBack').addEventListener('click', () => library.back());
    $('libReset').addEventListener('click', () => library.reset());
    $('libFlip').addEventListener('click', () => library.board && library.board.flip());
    $('libEngineBtn').addEventListener('click', () => library.askEngine());
    let timer = null;
    $('libSearch').addEventListener('input', (e) => {
      clearTimeout(timer);
      const q = e.target.value.trim();
      timer = setTimeout(() => library.search(q), 300);
    });
  }

  window.Study = {
    init(base) {
      apiBase = base || '';
      LB.setApiBase(base);
      wire();
      library.init().catch(() => {
        $('libBook').innerHTML = '<p class="muted small">The board needs the local API — start api_server.py.</p>';
      });
    },
    review: (row) => review.open(row).catch((err) => {
      $('reviewStatus').textContent = `Could not load the board: ${err.message}`;
    }),
    setRows(rows) {
      state.rows = rows || [];
      drill.setRows(state.rows);
    },
  };
})();
