/* Opening Leak Lab — interactive board.

   Legality, opening names and book statistics all come from the Python backend
   (python-chess + the local SQLite book), so this file only draws the position and
   collects clicks. window.LeakBoard is the whole surface used by study.js. */
(function () {
  'use strict';

  const GLYPHS = { k: '♚', q: '♛', r: '♜', b: '♝', n: '♞', p: '♟' };
  const FILES = 'abcdefgh';
  const NAMES = { q: 'Queen', r: 'Rook', b: 'Bishop', n: 'Knight' };
  const START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

  /* ------------------------------------------------------------------ backend */
  const positions = new Map();
  const evals = new Map();
  let apiBase = '';

  function setApiBase(base) {
    apiBase = base || '';
  }

  async function jsonOrThrow(res) {
    const body = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(body.detail || `${res.status} ${res.statusText}`);
    return body;
  }

  /** Legal moves, book statistics and the opening name for one position. Cached.

      `san` rebuilds the real move history from a report line, so the backend can name
      the opening and number the moves; without it a FEN carries no past. */
  async function position(fen, moves, san) {
    const parts = [];
    if (fen) parts.push(`fen=${encodeURIComponent(fen)}`);
    if (san && san.length) parts.push(`san=${encodeURIComponent(san.join(' '))}`);
    if (moves && moves.length) parts.push(`moves=${moves.join(',')}`);
    const path = parts.length ? parts.join('&') : `fen=${encodeURIComponent(START_FEN)}`;
    const key = `q:${path}`;
    if (positions.has(key)) return positions.get(key);
    const req = fetch(`${apiBase}/api/position?${path}`).then(jsonOrThrow);
    positions.set(key, req);
    try {
      return await req;
    } catch (err) {
      positions.delete(key);
      throw err;
    }
  }

  /** Stockfish's top continuations for a position. Cached per fen+depth+multipv. */
  async function engine(fen, { depth = 12, multipv = 3, pvLen = 6 } = {}) {
    const key = `${fen}|${depth}|${multipv}`;
    if (evals.has(key)) return evals.get(key);
    const req = fetch(`${apiBase}/api/engine`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ fen, depth, multipv, pv_len: pvLen }),
    }).then(jsonOrThrow);
    evals.set(key, req);
    try {
      return await req;
    } catch (err) {
      evals.delete(key);
      throw err;
    }
  }

  async function searchOpenings(q, limit = 24) {
    const res = await fetch(`${apiBase}/api/openings?q=${encodeURIComponent(q || '')}&limit=${limit}`);
    return jsonOrThrow(res);
  }

  /* ------------------------------------------------------------------ helpers */
  function parseFen(fen) {
    const [placement, turn] = String(fen || START_FEN).split(' ');
    const board = {};
    placement.split('/').forEach((rankStr, rankIdx) => {
      let fileIdx = 0;
      for (const ch of rankStr) {
        if (/\d/.test(ch)) {
          fileIdx += +ch;
        } else {
          board[`${FILES[fileIdx]}${8 - rankIdx}`] = ch;
          fileIdx += 1;
        }
      }
    });
    return { board, turn: turn === 'b' ? 'black' : 'white' };
  }

  const cpText = (cp) => {
    if (cp === null || cp === undefined) return '—';
    if (Math.abs(cp) >= 9800) {
      const n = Math.max(1, Math.floor((10000 - Math.abs(cp)) / 2) + 1);
      return (cp > 0 ? 'M' : '-M') + n;
    }
    return (cp >= 0 ? '+' : '') + (cp / 100).toFixed(2);
  };

  /* -------------------------------------------------------------------- board */
  class Board {
    constructor(el, opts = {}) {
      this.el = el;
      this.orientation = opts.orientation === 'black' ? 'black' : 'white';
      this.interactive = opts.interactive !== false;
      this.onMove = opts.onMove || (() => {});
      this.onSelect = opts.onSelect || (() => {});
      this.fen = opts.fen || START_FEN;
      this.legal = [];
      this.selected = null;
      this.arrows = [];
      this.marks = [];
      this.lastMove = null;
      this.pending = null;

      el.classList.add('cb');
      el.innerHTML =
        '<div class="cb-squares"></div>' +
        '<svg class="cb-arrows" viewBox="0 0 80 80" aria-hidden="true"></svg>' +
        '<div class="cb-promo" hidden></div>';
      this.squaresEl = el.querySelector('.cb-squares');
      this.arrowsEl = el.querySelector('.cb-arrows');
      this.promoEl = el.querySelector('.cb-promo');
      this.buildSquares();
      this.squaresEl.addEventListener('click', (e) => this.handleClick(e));
      el.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') this.clearSelection();
      });
      this.draw();
    }

    /* -- structure ------------------------------------------------------- */
    orderedSquares() {
      const ranks = this.orientation === 'white' ? [8, 7, 6, 5, 4, 3, 2, 1] : [1, 2, 3, 4, 5, 6, 7, 8];
      const files = this.orientation === 'white' ? FILES.split('') : FILES.split('').reverse();
      const out = [];
      ranks.forEach((rank) => files.forEach((file) => out.push(`${file}${rank}`)));
      return out;
    }

    buildSquares() {
      const squares = this.orderedSquares();
      this.squaresEl.innerHTML = squares
        .map((sq, i) => {
          const file = FILES.indexOf(sq[0]);
          const rank = +sq[1] - 1;
          const light = (file + rank) % 2 === 1;
          const row = Math.floor(i / 8);
          const col = i % 8;
          const showFile = row === 7;
          const showRank = col === 0;
          return (
            `<div class="cb-sq ${light ? 'is-light' : 'is-dark'}" data-square="${sq}" role="button" tabindex="-1">` +
            '<span class="cb-piece"></span><span class="cb-dot"></span>' +
            (showRank ? `<span class="cb-coord cb-rank">${sq[1]}</span>` : '') +
            (showFile ? `<span class="cb-coord cb-file">${sq[0]}</span>` : '') +
            '</div>'
          );
        })
        .join('');
      this.cells = {};
      this.squaresEl.querySelectorAll('.cb-sq').forEach((cell) => {
        this.cells[cell.dataset.square] = cell;
      });
    }

    /* -- state ----------------------------------------------------------- */
    setPosition(fen, { legal = [], lastMove = null, arrows = [], marks = [] } = {}) {
      this.fen = fen;
      this.legal = legal;
      this.lastMove = lastMove;
      this.arrows = arrows;
      this.marks = marks;
      this.selected = null;
      this.hidePromo();
      this.draw();
    }

    setLegal(legal) {
      this.legal = legal || [];
    }

    setArrows(arrows) {
      this.arrows = arrows || [];
      this.drawArrows();
    }

    setMarks(marks) {
      this.marks = marks || [];
      this.draw();
    }

    flip() {
      this.orientation = this.orientation === 'white' ? 'black' : 'white';
      this.buildSquares();
      this.draw();
    }

    setOrientation(side) {
      const next = side === 'black' ? 'black' : 'white';
      if (next === this.orientation) return;
      this.flip();
    }

    clearSelection() {
      this.selected = null;
      this.hidePromo();
      this.draw();
    }

    /* -- drawing --------------------------------------------------------- */
    draw() {
      const { board } = parseFen(this.fen);
      const targets = this.selected ? this.legal.filter((m) => m.from === this.selected) : [];
      const targetSquares = new Set(targets.map((m) => m.to));
      const movable = new Set(this.legal.map((m) => m.from));
      const markMap = {};
      (this.marks || []).forEach((m) => {
        markMap[m.square] = m.kind || 'note';
      });

      Object.entries(this.cells).forEach(([sq, cell]) => {
        const piece = board[sq];
        const glyph = cell.querySelector('.cb-piece');
        glyph.textContent = piece ? GLYPHS[piece.toLowerCase()] : '';
        glyph.className = `cb-piece${piece ? (piece === piece.toUpperCase() ? ' is-white' : ' is-black') : ''}`;
        cell.classList.toggle('is-selected', this.selected === sq);
        cell.classList.toggle('is-target', targetSquares.has(sq));
        cell.classList.toggle('is-capture', targetSquares.has(sq) && !!piece);
        cell.classList.toggle('is-last', !!this.lastMove && (this.lastMove.from === sq || this.lastMove.to === sq));
        cell.classList.toggle('can-move', this.interactive && movable.has(sq));
        cell.dataset.mark = markMap[sq] || '';
      });
      this.drawArrows();
    }

    drawArrows() {
      const unit = 10;
      const pos = (sq) => {
        const fileIdx = FILES.indexOf(sq[0]);
        const rankIdx = +sq[1] - 1;
        const col = this.orientation === 'white' ? fileIdx : 7 - fileIdx;
        const row = this.orientation === 'white' ? 7 - rankIdx : rankIdx;
        return { x: col * unit + unit / 2, y: row * unit + unit / 2 };
      };
      const defs =
        '<defs>' +
        ['played', 'best', 'book']
          .map(
            (kind) =>
              `<marker id="cb-head-${kind}" markerWidth="3.4" markerHeight="3.4" refX="2.2" refY="1.7" orient="auto">` +
              `<path d="M0,0 L3.2,1.7 L0,3.4 z" class="cb-head cb-${kind}"/></marker>`
          )
          .join('') +
        '</defs>';
      const shapes = (this.arrows || [])
        .filter((a) => a && a.from && a.to && a.from !== a.to)
        .map((a) => {
          const kind = a.kind || 'best';
          const s = pos(a.from);
          const e = pos(a.to);
          const dx = e.x - s.x;
          const dy = e.y - s.y;
          const len = Math.hypot(dx, dy) || 1;
          const trim = 2.6;
          const x2 = e.x - (dx / len) * trim;
          const y2 = e.y - (dy / len) * trim;
          return `<line x1="${s.x}" y1="${s.y}" x2="${x2}" y2="${y2}" class="cb-arrow cb-${kind}" marker-end="url(#cb-head-${kind})"/>`;
        })
        .join('');
      this.arrowsEl.innerHTML = defs + shapes;
      this.arrowsEl.setAttribute('viewBox', '0 0 80 80');
    }

    /* -- interaction ----------------------------------------------------- */
    handleClick(e) {
      if (!this.interactive) return;
      const cell = e.target.closest('.cb-sq');
      if (!cell) return;
      const sq = cell.dataset.square;
      if (this.selected) {
        const matches = this.legal.filter((m) => m.from === this.selected && m.to === sq);
        if (matches.length === 1) {
          this.selected = null;
          this.draw();
          this.onMove(matches[0]);
          return;
        }
        if (matches.length > 1) {
          this.showPromo(matches, sq);
          return;
        }
      }
      const canStart = this.legal.some((m) => m.from === sq);
      this.selected = canStart && this.selected !== sq ? sq : null;
      this.hidePromo();
      this.draw();
      this.onSelect(this.selected);
    }

    showPromo(moves, square) {
      this.promoEl.hidden = false;
      this.promoEl.innerHTML =
        '<div class="cb-promo-inner"><b>Promote to</b><div class="cb-promo-row">' +
        moves
          .map(
            (m) =>
              `<button type="button" data-uci="${m.uci}" title="${NAMES[m.promotion] || m.promotion}">` +
              `<span class="cb-piece ${parseFen(this.fen).turn === 'white' ? 'is-white' : 'is-black'}">${GLYPHS[m.promotion]}</span>` +
              `<i>${NAMES[m.promotion] || ''}</i></button>`
          )
          .join('') +
        '</div></div>';
      this.promoEl.querySelectorAll('button').forEach((btn) => {
        btn.addEventListener('click', () => {
          const move = moves.find((m) => m.uci === btn.dataset.uci);
          this.hidePromo();
          this.selected = null;
          this.draw();
          if (move) this.onMove(move);
        });
      });
      void square;
    }

    hidePromo() {
      this.promoEl.hidden = true;
      this.promoEl.innerHTML = '';
    }
  }

  /* ------------------------------------------------------- shared renderers */
  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  /** Book move table: popularity, score and the win/draw/loss split. */
  function renderBook(el, book, { onPlay, highlight = [], emptyText = 'No games in the book from here.' } = {}) {
    if (!book || !book.total) {
      el.innerHTML = `<p class="muted small">${esc(emptyText)}</p>`;
      return;
    }
    const rows = book.moves
      .slice(0, 12)
      .map((m) => {
        const hit = highlight.find((h) => h.san === m.san || h.uci === m.uci);
        const total = m.games || 1;
        const pct = (n) => Math.round((100 * n) / total);
        return (
          `<tr data-uci="${m.uci}" class="${hit ? `is-${hit.kind}` : ''}">` +
          `<td class="book-move">${esc(m.san)}${hit ? `<i class="tag tag-${hit.kind}">${esc(hit.label || hit.kind)}</i>` : ''}</td>` +
          `<td class="num">${m.games.toLocaleString()}</td>` +
          `<td class="num">${m.share.toFixed(1)}%</td>` +
          `<td class="num">${m.score === null ? '—' : m.score.toFixed(1) + '%'}</td>` +
          `<td class="wdl"><span class="wdl-bar" title="${m.white}W ${m.draws}D ${m.black}L">` +
          `<i class="w" style="width:${pct(m.white)}%"></i><i class="d" style="width:${pct(m.draws)}%"></i>` +
          `<i class="l" style="width:${pct(m.black)}%"></i></span></td></tr>`
        );
      })
      .join('');
    el.innerHTML =
      `<table class="book-table"><thead><tr><th>Move</th><th class="num">Games</th><th class="num">Played</th>` +
      `<th class="num">Score</th><th>W / D / L</th></tr></thead><tbody>${rows}</tbody></table>`;
    if (onPlay) {
      el.querySelectorAll('tbody tr').forEach((tr) => {
        tr.classList.add('is-clickable');
        tr.addEventListener('click', () => onPlay(tr.dataset.uci));
      });
    }
  }

  /** Engine panel: top lines with eval and the principal variation. */
  function renderEngine(el, result, { onPlay } = {}) {
    if (!result || !result.lines || !result.lines.length) {
      el.innerHTML = '<p class="muted small">The engine had nothing to say about this position.</p>';
      return;
    }
    el.innerHTML =
      `<ol class="eng-lines">` +
      result.lines
        .map(
          (l, i) =>
            `<li data-uci="${l.uci}"><span class="eng-eval ${l.cp >= 0 ? 'is-plus' : 'is-minus'}">${esc(l.eval || cpText(l.cp))}</span>` +
            `<b>${esc(l.san)}</b><span class="eng-pv mono">${esc((l.pv || []).slice(1).join(' '))}</span>` +
            `${i === 0 ? '<i class="tag tag-best">best</i>' : ''}</li>`
        )
        .join('') +
      `</ol><p class="muted small">Depth ${result.depth}, from ${esc(result.mover)}'s point of view.</p>`;
    if (onPlay) {
      el.querySelectorAll('li').forEach((li) => {
        li.classList.add('is-clickable');
        li.addEventListener('click', () => onPlay(li.dataset.uci));
      });
    }
  }

  window.LeakBoard = {
    Board,
    setApiBase,
    position,
    engine,
    searchOpenings,
    renderBook,
    renderEngine,
    parseFen,
    cpText,
    esc,
    START_FEN,
  };
})();
