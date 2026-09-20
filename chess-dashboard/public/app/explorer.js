/* Opening Leak Lab — the openings explorer, read through the player's own games.

   The book half of this screen is the same for everyone: any opening, its moves,
   its statistics. The half above it is not — it is one profile per opening this
   player actually plays, saying how they do in it, at which move their line
   stops holding, which known traps have caught them there, and what to play
   instead. Everything here comes from `summary.explorer`, which the analyzer
   builds in profiles.py and traps.py. */
(function () {
  'use strict';

  const $ = (id) => document.getElementById(id);
  const V = window.Vocab;
  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const num = (v) => {
    const n = parseFloat(v);
    return Number.isFinite(n) ? n : null;
  };
  const plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`;
  const pct = (v) => (num(v) === null ? '—' : `${num(v).toFixed(0)}%`);

  const state = { data: null, colour: 'all', selected: null };

  const payload = (ctx) => (ctx && ctx.summary && ctx.summary.explorer) || null;
  const openings = () => (state.data ? state.data.openings || [] : []);
  const traps = () => (state.data && state.data.traps ? state.data.traps.traps || [] : []);
  const trapByKey = (key) => traps().find((t) => t.key === key) || null;

  const label = (p) => `${p.eco ? `${p.eco} ` : ''}${p.family}`;
  /* A leak's line ends with the move that costs points; the interesting position
     is the one before it. */
  const beforeMove = (line) => String(line || '').trim().split(/\s+/).slice(0, -1).join(' ');
  const sideWord = (colour) => (colour === 'white' ? 'as White' : 'as Black');

  /* ------------------------------------------------------------------ render */
  function render(ctx) {
    state.data = payload(ctx);
    const has = state.data && (openings().length || traps().length);
    $('explorerPersonal').hidden = !has;
    if (!has) return;
    renderBand();
    renderOpenings();
    renderTraps();
    if (!state.selected || !openings().some((p) => p.key === state.selected)) {
      const first = visibleOpenings()[0];
      state.selected = first ? first.key : null;
    }
    renderDetail();
  }

  /* The one-line answer to "where do I go wrong", above everything else. */
  function renderBand() {
    const breaks = state.data.break_moves || [];
    const worst = breaks.slice().sort((a, b) => b.games - a.games)[0];
    const fell = state.data.traps ? state.data.traps.fell || 0 : 0;
    const met = state.data.traps ? state.data.traps.met || 0 : 0;
    const trouble = (state.data.worst_against || [])
      .map((key) => openings().find((p) => p.key === key))
      .filter(Boolean)[0];

    $('breakBand').innerHTML = [
      {
        label: 'Trouble starts at',
        value: worst ? `move ${worst.move_number}` : '—',
        note: worst ? `${plural(worst.games, 'game')} go wrong there` : 'no break point yet',
        cls: 'accent',
      },
      {
        label: 'Openings profiled',
        value: openings().length,
        note: (state.data.worst_against || []).length
          ? `${(state.data.worst_against || []).length} of them giving you real trouble`
          : 'none of them standing out as weak',
      },
      {
        label: 'Worst against',
        title: V.METRICS.trouble.definition,
        value: trouble ? trouble.family : '—',
        note: trouble ? `${sideWord(trouble.colour)}, ${trouble.gap_pct}% below the book` : 'nothing stands out',
      },
      {
        label: 'Traps walked into',
        value: fell,
        note: met ? `out of ${plural(met, 'trap line')} you have met` : 'none of the known lines met',
      },
    ]
      .map(
        (c) => `<div class="kpi ${c.cls || ''}"${c.title ? ` title="${esc(c.title)}"` : ''}>
          <div class="kpi-label">${esc(c.label)}</div>
          <div class="kpi-value">${esc(c.value)}</div>
          <div class="kpi-note">${esc(c.note)}</div></div>`,
      )
      .join('');

    if (breaks.length > 1) {
      $('openingNote').innerHTML = `Where your openings break down, by move number: ${spread(breaks)}`;
    } else {
      $('openingNote').textContent =
        'Ranked by what each opening costs you. "Holds to" is the move your line first goes wrong on.';
    }
  }

  /* A bar per move number — small enough to sit inside a line of text. */
  function spread(breaks) {
    const top = Math.max(...breaks.map((b) => b.games), 1);
    return `<span class="spread">${breaks
      .map(
        (b) => `<span class="spread-bar" title="${plural(b.games, 'game')} go wrong on move ${b.move_number}">
          <i style="height:${Math.max(8, (b.games / top) * 100).toFixed(0)}%"></i>
          <b>${b.move_number}</b></span>`,
      )
      .join('')}</span>`;
  }

  function visibleOpenings() {
    return openings().filter((p) => state.colour === 'all' || p.colour === state.colour);
  }

  function renderOpenings() {
    const rows = visibleOpenings();
    const worstCost = Math.max(1, ...openings().map((p) => p.cost || 0));
    $('openingBody').innerHTML = rows
      .map((p, i) => {
        const gap = num(p.gap_pct);
        const cost = p.cost || 0;
        return `<tr data-i="${i}" tabindex="0" class="${p.key === state.selected ? 'is-selected' : ''}">
          <td class="col-opening" data-label="Opening">
            <span class="opening-name">${esc(label(p))}</span>
            <span class="opening-line">${esc(sideWord(p.colour))}${p.traps.length ? ` · ${plural(p.traps.length, 'trap')}` : ''}</span>
          </td>
          <td class="num" data-label="Games">${p.games || '—'}</td>
          <td class="num col-gap" data-label="You vs book">
            <span class="${gap !== null && gap < 0 ? 'delta-bad' : ''}">${pct(p.score_pct)}</span>
            <span class="muted"> vs ${pct(p.book_score_pct)}</span>
          </td>
          <td class="num" data-label="Holds to" title="${esc(V.METRICS.breakPoint.definition)}">
            ${p.first_break ? `move ${p.first_break}` : '—'}
          </td>
          <td class="num" data-label="Cost">
            <span class="cost"><b class="mono">${cost.toFixed(1)}</b>
            <span class="cost-bar"><i style="width:${Math.max(3, (cost / worstCost) * 100).toFixed(1)}%"></i></span></span>
          </td>
        </tr>`;
      })
      .join('');
    $('openingBody').querySelectorAll('tr').forEach((tr) => {
      const open = rows[+tr.dataset.i];
      const pick = () => {
        state.selected = open.key;
        renderOpenings();
        renderDetail();
        $('openingDetail').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      };
      tr.addEventListener('click', pick);
      tr.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          pick();
        }
      });
    });
  }

  function renderDetail() {
    const open = openings().find((p) => p.key === state.selected);
    $('openingDetail').hidden = !open;
    if (!open) return;
    const gap = num(open.gap_pct);
    const stats = [
      { label: 'Your score', value: pct(open.score_pct), note: `${open.wins}W ${open.draws}D ${open.losses}L` },
      { label: 'Book score', value: pct(open.book_score_pct), note: 'from the same positions' },
      { label: V.METRICS.scoreGap.label, value: gap === null ? '—' : `${gap > 0 ? '+' : ''}${gap}%`,
        note: 'across this whole opening', title: V.METRICS.trouble.definition },
      { label: V.METRICS.breakPoint.label, value: open.first_break ? `move ${open.first_break}` : '—',
        note: 'where the line first goes wrong', title: V.METRICS.breakPoint.definition },
      { label: V.METRICS.cost.label, value: (open.cost || 0).toFixed(1), note: `over ${plural(open.games, 'game')}` },
    ];

    const leaks = (open.leaks || []).slice(0, 8);
    $('openingDetail').innerHTML = `
      <div class="panel-head">
        <h2>${esc(open.name || open.family)}</h2>
        <span class="hint">${esc(sideWord(open.colour))} · ${esc(plural(open.games, 'game'))}</span>
      </div>
      <div class="stat-row">
        ${stats.map((s) => `<div class="stat"${s.title ? ` title="${esc(s.title)}"` : ''}>
          <div class="stat-label">${esc(s.label)}</div>
          <div class="stat-value">${esc(s.value)}</div><div class="kpi-note">${esc(s.note)}</div></div>`).join('')}
      </div>
      ${open.breaks && open.breaks.length > 1 ? `<p class="panel-note">Where this opening breaks down: ${spread(open.breaks)}</p>` : ''}
      <h4 class="detail-heading">What to play instead</h4>
      ${leaks.length
        ? `<ol class="fixes">${leaks
            .map(
              (leak, i) => `<li data-i="${i}">
                <span class="fix-where">
                  <b>Move ${leak.move_number}</b>
                  <span class="mono muted">${esc(beforeMove(leak.line))}</span>
                </span>
                <span class="fix-swap">
                  <span class="mono was">${esc(leak.your_move)}</span>
                  <span class="fix-arrow" aria-hidden="true">→</span>
                  <span class="mono now">${esc(leak.play_instead || '—')}</span>
                </span>
                <span class="fix-why">
                  ${V.chips(leak.flag)}
                  <span class="muted">${esc(whyText(leak))}</span>
                </span>
                <button type="button" class="link-btn fix-open">Show it</button>
              </li>`,
            )
            .join('')}</ol>`
        : '<p class="invite">Nothing in this opening is costing you points — it is holding up.</p>'}
      ${renderOpeningTraps(open)}`;

    $('openingDetail').querySelectorAll('.fixes li').forEach((li) => {
      const leak = leaks[+li.dataset.i];
      // the line ends with the move that costs points, so stop one short of it
      li.querySelector('.fix-open').addEventListener('click', () => showLine(beforeMove(leak.line), leak.fen));
    });
    $('openingDetail').querySelectorAll('[data-trap]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const trap = trapByKey(btn.dataset.trap);
        if (trap) showLine(trap.line, '');
      });
    });
  }

  function whyText(leak) {
    const you = num(leak.score_pct);
    const book = num(leak.book_score_pct);
    const instead = num(leak.instead_score_pct);
    const bits = [];
    if (you !== null) bits.push(`you score ${you.toFixed(0)}% over ${plural(leak.games, 'game')}`);
    if (book !== null) bits.push(`the book gets ${book.toFixed(0)}% with the same move`);
    if (instead !== null) bits.push(`${leak.play_instead} gets ${instead.toFixed(0)}%`);
    else if (leak.instead_source === 'engine') bits.push(`${leak.play_instead} is the engine's pick`);
    return bits.join(' · ');
  }

  function renderOpeningTraps(open) {
    const list = (open.traps || []).map(trapByKey).filter(Boolean);
    if (!list.length) return '';
    return `<h4 class="detail-heading">Traps in this opening</h4>
      <ul class="traps">${list.map(trapItem).join('')}</ul>`;
  }

  function trapItem(trap) {
    const caught = trap.fell > 0;
    return `<li class="${caught ? 'is-caught' : ''}">
      <span class="trap-main">
        <b>${esc(trap.name)}</b>
        <span class="mono muted">${esc(trap.line)}</span>
        <span class="muted small">${esc(trap.note)}</span>
      </span>
      <span class="trap-verdict">
        <span class="${caught ? 'delta-bad' : 'muted'}">
          ${caught
            ? `walked in ${trap.fell} of ${plural(trap.met, 'time')}`
            : `met ${plural(trap.met, 'time')}, held every time`}
        </span>
        <span class="mono">move ${trap.move_number}:
          <span class="was">${esc((trap.losing || []).join('/'))}</span> →
          <span class="now">${esc(trap.instead)}</span></span>
      </span>
      <button type="button" class="link-btn" data-trap="${esc(trap.key)}">Show it</button>
    </li>`;
  }

  function renderTraps() {
    const met = traps();
    $('trapPanel').hidden = !met.length;
    if (!met.length) return;
    const fell = met.filter((t) => t.fell);
    $('trapPanel').innerHTML = `
      <div class="panel-head">
        <h2>Traps</h2>
        <span class="hint">Known trap lines you have actually faced, move for move</span>
      </div>
      <p class="panel-note">
        ${fell.length
          ? `${plural(fell.length, 'trap')} caught you; the rest you met and held.`
          : 'You have met these and held every time.'}
        A line only counts here when your game followed it exactly, so a transposition into the
        same position is not claimed as a hit.
      </p>
      <ul class="traps">${met.map(trapItem).join('')}</ul>`;
    $('trapPanel').querySelectorAll('[data-trap]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const trap = trapByKey(btn.dataset.trap);
        if (trap) showLine(trap.line, '');
      });
    });
  }

  /* Put a line on the explorer board below: the position before the move that
     matters, with the history that names the opening. */
  function showLine(line, fen) {
    const san = String(line || '').trim().split(/\s+/).filter(Boolean);
    if (!window.Study || !san.length) return;
    window.Study.explore(san, fen);
    $('libBoard').scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  function wire() {
    document.querySelectorAll('#explorerColour .seg').forEach((b) =>
      b.addEventListener('click', () => {
        document.querySelectorAll('#explorerColour .seg').forEach((x) => x.classList.remove('is-active'));
        b.classList.add('is-active');
        state.colour = b.dataset.colour;
        state.selected = null;
        render(window.App ? window.App.reportContext() : {});
      }),
    );
  }

  wire();

  window.Explorer = { render, showLine };
})();
