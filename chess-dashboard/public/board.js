/* Opening Leak Lab — interactive board.

   Legality, opening names and book statistics all come from the Python backend
   (python-chess + the local SQLite book), so this file only draws the position and
   collects clicks. window.LeakBoard is the whole surface used by study.js. */
(function () {
  'use strict';

  /* Pieces as inline SVG rather than Unicode glyphs.

     A glyph came from whichever system font happened to have one — Segoe UI Symbol on
     Windows, which draws them as monochrome outlines. Colouring an outline glyph white
     leaves a white piece as a white outline: on a light square, invisible. Filled shapes
     with a contrasting stroke depend on no font being installed and read as well at 22px
     as at 60px. Original artwork, so there is nothing here to attribute. */
  const PIECE_BASE =
    '<rect x="10" y="34.6" width="25" height="5" rx="1.6"/>' +
    '<rect x="13" y="30.6" width="19" height="4.2" rx="1.4"/>';

  const PIECE_SHAPES = {
    p: '<circle cx="22.5" cy="12.4" r="5"/>' +
       '<path d="M16.4 17.6h12.2c0 5.8-3.9 8.6-4.1 13h-4c-.2-4.4-4.1-7.2-4.1-13z"/>',
    r: '<path d="M12 8.5h4.6v3.2h3.6V8.5h4.6v3.2h3.6V8.5H33v7.6H12z"/>' +
       '<path d="M14.6 16.1h15.8l-1.7 14.5H16.3z"/>',
    n: '<path d="M15 31c0-7 2-11 6-14.2 1.5-1.2 2-2.6 1.5-4.2l-3 1.8-2.2-2.6 3.6-3.4 3-1 1-3 2.6 2.4c4.6 2 7.5 6.8 7.5 12.6V31z"/>' +
       '<circle cx="26.6" cy="12.4" r="1.05" class="cb-eye"/>',
    b: '<circle cx="22.5" cy="5.4" r="2.1"/>' +
       '<path d="M22.5 8c3.1 3.1 6.4 7 6.4 10.9 0 3.5-2.9 6-6.4 6s-6.4-2.5-6.4-6C16.1 15 19.4 11.1 22.5 8z"/>' +
       '<path d="M21.6 11.4h1.8v7.4h-1.8z" class="cb-cut"/>' +
       '<path d="M17.2 25.4h10.6l1.4 5.2H15.8z"/>',
    q: '<circle cx="11.6" cy="12" r="2.3"/><circle cx="22.5" cy="7.4" r="2.5"/>' +
       '<circle cx="33.4" cy="12" r="2.3"/>' +
       '<path d="M11.6 13.2 15.2 22h14.6l3.6-8.8-5.4 3.9-5.5-8.5-5.5 8.5z"/>' +
       '<path d="M15.4 22.6h14.2l-1.2 8H16.6z"/>',
    k: '<path d="M21.2 4.4h2.6v3h3v2.6h-3v3h-2.6v-3h-3V7.4h3z"/>' +
       '<path d="M12.2 16.6c3-3.1 6.2-4.4 10.3-4.4s7.3 1.3 10.3 4.4L30.6 23H14.4z"/>' +
       '<path d="M14.9 23.6h15.2l-1.2 7H16.1z"/>',
  };

  const PIECE_NAMES = { k: 'king', q: 'queen', r: 'rook', b: 'bishop', n: 'knight', p: 'pawn' };

  function pieceSvg(letter) {
    const shape = PIECE_SHAPES[(letter || '').toLowerCase()];
    if (!shape) return '';
    const white = letter === letter.toUpperCase();
    return `<svg class="cb-svg ${white ? 'is-white' : 'is-black'}" viewBox="0 0 45 45"` +
      ` aria-hidden="true" focusable="false"><g>${PIECE_BASE}${shape}</g></svg>`;
  }

  /* What a screen reader should hear for one square. */
  function squareLabel(sq, letter) {
    if (!letter) return `${sq[0]} ${sq[1]}, empty`;
    const colour = letter === letter.toUpperCase() ? 'white' : 'black';
    return `${sq[0]} ${sq[1]}, ${colour} ${PIECE_NAMES[letter.toLowerCase()]}`;
  }
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
        '<div class="cb-squares" role="grid" aria-label="Chess board"></div>' +
        '<svg class="cb-arrows" viewBox="0 0 80 80" aria-hidden="true"></svg>' +
        '<div class="cb-promo" hidden></div>';
      this.squaresEl = el.querySelector('.cb-squares');
      this.arrowsEl = el.querySelector('.cb-arrows');
      this.promoEl = el.querySelector('.cb-promo');
      this.buildSquares();
      this.squaresEl.addEventListener('click', (e) => this.handleClick(e));
      this.squaresEl.addEventListener('keydown', (e) => this.handleKey(e));
      // Focus follows the arrow keys, so the roving tabindex has to follow focus too —
      // otherwise tabbing away and back returns to wherever the cursor started.
      this.squaresEl.addEventListener('focusin', (e) => {
        const cell = e.target.closest('.cb-sq');
        if (cell) this.setCursor(cell.dataset.square, false);
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
            `<div class="cb-sq ${light ? 'is-light' : 'is-dark'}" data-square="${sq}"` +
            ` role="gridcell" tabindex="-1" aria-label="${sq[0]} ${sq[1]}, empty">` +
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
      // One square is in the tab order at a time; the arrow keys move which one. Sixty-four
      // tab stops to cross a board is not keyboard support, it is a punishment.
      this.cursor = squares.includes(this.cursor) ? this.cursor : squares[squares.length - 8];
      this.cells[this.cursor].tabIndex = 0;
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
        const wanted = piece || '';
        if (glyph.dataset.piece !== wanted) {
          glyph.innerHTML = piece ? pieceSvg(piece) : '';
          glyph.dataset.piece = wanted;
        }
        glyph.className = 'cb-piece';
        // The name has to carry what the colours carry, including whether this square is a
        // legal destination — that is the whole state a sighted player reads off the dots.
        const role = this.selected === sq ? ', selected'
          : targetSquares.has(sq) ? (piece ? ', can capture here' : ', can move here') : '';
        cell.setAttribute('aria-label', squareLabel(sq, piece) + role);
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
      const cell = e.target.closest('.cb-sq');
      if (!cell) return;
      this.activate(cell.dataset.square);
    }

    /* Selecting, moving, or deselecting — whichever the square means right now. Both the
       mouse and the keyboard land here, so the two can never drift apart. */
    activate(sq) {
      if (!this.interactive) return;
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

    /* Where the keyboard cursor is. Kept separate from `selected`: moving the cursor over
       a square is not the same as picking the piece up, exactly as with a mouse. */
    setCursor(square, focus = true) {
      if (!this.cells[square]) return;
      const prev = this.cells[this.cursor];
      if (prev) prev.tabIndex = -1;
      this.cursor = square;
      this.cells[square].tabIndex = 0;
      if (focus) this.cells[square].focus();
    }

    handleKey(e) {
      const step = { ArrowUp: [0, 1], ArrowDown: [0, -1], ArrowLeft: [-1, 0], ArrowRight: [1, 0] }[e.key];
      if (step) {
        e.preventDefault();
        // The board can be seen from either side, and "up" means up the screen, not up
        // the board — arrows that invert when you flip would be unusable.
        const flip = this.orientation === 'black' ? -1 : 1;
        const file = FILES.indexOf(this.cursor[0]) + step[0] * flip;
        const rank = Number(this.cursor[1]) + step[1] * flip;
        if (file < 0 || file > 7 || rank < 1 || rank > 8) return;
        this.setCursor(`${FILES[file]}${rank}`);
        return;
      }
      if (e.key === 'Enter' || e.key === ' ' || e.key === 'Spacebar') {
        e.preventDefault();
        this.activate(this.cursor);
        return;
      }
      if (e.key === 'Escape') {
        this.clearSelection();
        return;
      }
      if (e.key === 'Home' || e.key === 'End') {
        e.preventDefault();
        this.setCursor(e.key === 'Home' ? `a${this.cursor[1]}` : `h${this.cursor[1]}`);
      }
    }

    showPromo(moves, square) {
      this.promoEl.hidden = false;
      this.promoEl.innerHTML =
        '<div class="cb-promo-inner"><b>Promote to</b><div class="cb-promo-row">' +
        moves
          .map(
            (m) =>
              `<button type="button" data-uci="${m.uci}" title="${NAMES[m.promotion] || m.promotion}">` +
              `<span class="cb-piece">${pieceSvg(parseFen(this.fen).turn === 'white'
                ? m.promotion.toUpperCase() : m.promotion)}</span>` +
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
