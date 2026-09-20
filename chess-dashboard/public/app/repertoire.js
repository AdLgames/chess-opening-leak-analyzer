/* Opening Leak Lab — the repertoire the user is building, and how it moves.

   The report diagnoses; this file is the thing being built. It owns three
   readings of the same store: the committed tree, the holes still in it, and
   the coverage figure that ties them together — plus the Progress view, whose
   spine is that same figure plotted per run. */
(function () {
  'use strict';

  const $ = (id) => document.getElementById(id);
  const S = window.Store;
  const V = window.Vocab;
  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const num = (v) => {
    const n = parseFloat(v);
    return Number.isFinite(n) ? n : null;
  };
  const plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`;

  let colour = 'white';
  let playedFilter = 'all';

  /* ---------------------------------------------------------------- coverage */
  /** The share of the user's opening decisions, weighted by how often they play
      them, that are not an open leak. Committing or dismissing moves it. */
  function coverage({ rows = [], summary = null } = {}) {
    const decided = new Set(S.repertoire.all().map((e) => e.key));
    const open = rows.filter((r) => !decided.has(S.leakKey(r)));
    const leakedGames = open.reduce((sum, r) => sum + (num(r.your_games) || 0), 0);
    const total = (summary && summary.judged_games)
      || rows.reduce((sum, r) => sum + (num(r.your_games) || 0), 0);
    if (!total) return { pct: 100, note: 'nothing judged yet', open: 0, total: 0 };
    const pct = Math.max(0, Math.round((1 - leakedGames / total) * 100));
    return {
      pct,
      open: open.length,
      total,
      note: open.length
        ? `${plural(open.length, 'leak')} still open`
        : 'every finding answered',
    };
  }

  /* -------------------------------------------------------------- move tree */
  function buildTree(entries) {
    const root = { san: '', children: [], games: 0, status: '' };
    entries.forEach((entry) => {
      const path = [...(entry.line || []), entry.answer].filter(Boolean);
      let node = root;
      path.forEach((san, i) => {
        let child = node.children.find((c) => c.san === san);
        if (!child) {
          child = { san, children: [], games: 0, status: '', ply: i };
          node.children.push(child);
        }
        child.games = Math.max(child.games, entry.games || 0);
        if (i === path.length - 1) {
          child.status = entry.status === 'dismissed' ? 'dismissed' : 'committed';
          child.entry = entry;
        }
        node = child;
      });
    });
    return root;
  }

  /* A line is a row of moves; the tree only indents where it actually branches. */
  function renderTree(root) {
    if (!root.children.length) return '';
    return `<ul class="tree-root">${root.children.map(renderBranch).join('')}</ul>`;
  }

  function renderBranch(node) {
    const run = [node];
    let last = node;
    while (last.children.length === 1) {
      last = last.children[0];
      run.push(last);
    }
    const moves = run
      .map((n) => {
        const label = `${Math.floor(n.ply / 2) + 1}${n.ply % 2 === 0 ? '.' : '…'} ${n.san}`;
        const tail = n.status
          ? `<span class="tree-games">${n.games ? plural(n.games, 'game') : ''}</span>`
            + `<span class="tree-status">${esc(n.status)}</span>`
          : '';
        return `<span class="tree-move ${n.status ? `is-${esc(n.status)}` : ''}">`
          + `<span class="mono move">${esc(label)}</span>${tail}</span>`;
      })
      .join('');
    return `<li>
      <div class="tree-line">${moves}</div>
      ${last.children.length ? `<ul>${last.children.map(renderBranch).join('')}</ul>` : ''}
    </li>`;
  }

  /* -------------------------------------------------------- everything played
     The leak table is a strict filter, so a line handled well left no trace in
     the report at all. This is the unfiltered reading: every decision the run
     saw you repeat, with the ones that leak marked rather than the ones that
     do not being dropped. */
  function renderPlayed(ctx) {
    const body = $('playedBody');
    if (!body) return;
    const all = (ctx.tree || []).filter((r) => r.player_color === colour);
    document.querySelectorAll('#playedFilter .seg').forEach((b) =>
      b.classList.toggle('is-active', b.dataset.played === playedFilter),
    );

    if (!all.length) {
      body.innerHTML = `<p class="invite">Nothing recorded as ${colour} yet. Run the
        analyser and every line you repeat shows up here, whether or not it leaks.</p>`;
      return;
    }
    const shown = all.filter((r) => (playedFilter === 'leaking' ? r.flag
      : playedFilter === 'clean' ? !r.flag && r.eligible === 'yes' : true));
    const leaking = all.filter((r) => r.flag).length;
    const clean = all.filter((r) => !r.flag && r.eligible === 'yes').length;
    const watching = all.filter((r) => r.eligible === 'no').length;

    const rows = shown.slice(0, 120).map((r) => {
      const gap = num(r.score_gap_vs_db_pct);
      const state = r.flag ? 'leak' : r.eligible === 'no' ? 'watch' : 'clean';
      const label = r.flag
        ? esc(r.flag.split('+').map((f) => (V.FLAGS[f] ? V.FLAGS[f].label : f)).join(' · '))
        : r.eligible === 'no' ? `seen ${plural(num(r.your_games) || 0, 'time')}` : 'holding up';
      return `<li class="played-row is-${state}">
        <span class="played-main">
          <b>${esc([r.eco, r.opening].filter(Boolean).join(' ') || 'Unclassified')}</b>
          <span class="mono muted">${esc(r.variation_line)} <b>${esc(r.your_move)}</b></span>
        </span>
        <span class="played-figs mono">
          <span title="games you played this decision in">${esc(r.your_games)}g</span>
          <span title="your score against the book's">${r.your_score_pct === '' ? '—' : `${esc(r.your_score_pct)}%`}${
            gap === null ? '' : ` <i class="${gap < 0 ? 'is-down' : 'is-up'}">${gap > 0 ? '+' : ''}${esc(r.score_gap_vs_db_pct)}</i>`}</span>
        </span>
        <span class="played-state">${label}</span>
      </li>`;
    }).join('');

    body.innerHTML = `
      <p class="played-legend small muted">${plural(all.length, 'decision')} as ${colour}:
        ${leaking} leaking, ${clean} holding up${watching ? `, ${watching} seen too few times to judge` : ''}.</p>
      <ol class="played-list">${rows || '<li class="invite">Nothing in this filter.</li>'}</ol>
      ${shown.length > 120 ? `<p class="small muted">Showing the first 120 of ${shown.length}.</p>` : ''}`;
  }

  /* ------------------------------------------------------------------ views */
  function renderRepertoire(ctx) {
    const cov = coverage(ctx);
    $('coverageCard').innerHTML = `
      <div class="coverage-figure">
        <b class="mono">${cov.pct}%</b>
        <span>${esc(V.METRICS.coverage.label)}</span>
      </div>
      <p class="coverage-note" title="${esc(V.METRICS.coverage.definition)}">
        ${esc(V.METRICS.coverage.definition)}
      </p>`;

    renderPlayed(ctx);

    const entries = S.repertoire.all().filter((e) => e.color === colour);
    const committed = entries.filter((e) => e.status === 'committed');
    document.querySelectorAll('#repColor .seg').forEach((b) =>
      b.classList.toggle('is-active', b.dataset.color === colour),
    );
    $('repTree').innerHTML = committed.length
      ? renderTree(buildTree(committed))
      : `<p class="invite">Nothing committed as ${colour} yet. Open a leak in the report and
           choose the move you would rather play — it lands here.</p>`;

    const decided = new Set(S.repertoire.all().map((e) => e.key));
    const holes = (ctx.rows || [])
      .filter((r) => !decided.has(S.leakKey(r)))
      .slice()
      .sort((a, b) => (num(b.your_games) || 0) - (num(a.your_games) || 0))
      .slice(0, 20);
    $('repHoles').innerHTML = holes.length
      ? holes
          .map(
            (r, i) => `<li data-i="${i}">
              <span class="hole-main">
                <b>${esc([r.eco, r.opening].filter(Boolean).join(' ') || 'Unclassified')}</b>
                <span class="mono muted">${esc(r.variation_line)}</span>
              </span>
              <span class="hole-meta">
                ${V.chips(r.flag)}
                <span class="mono">${plural(+r.your_games, 'game')}</span>
              </span>
            </li>`,
          )
          .join('')
      : `<li class="invite">Every finding in the last report has an answer. Run again after a
           few dozen more games to see what turns up next.</li>`;
    $('repHoles').querySelectorAll('li[data-i]').forEach((li) => {
      li.addEventListener('click', () => {
        const row = holes[+li.dataset.i];
        window.App.go('report');
        window.App.select(row);
      });
    });
  }

  /* --------------------------------------------------------------- progress */
  function sparkline(points, { width = 560, height = 120 } = {}) {
    if (points.length < 2) return '';
    const max = 100;
    const step = width / (points.length - 1);
    const path = points
      .map((p, i) => `${i === 0 ? 'M' : 'L'}${(i * step).toFixed(1)},${(height - (p.value / max) * height).toFixed(1)}`)
      .join(' ');
    const dots = points
      .map((p, i) => `<circle cx="${(i * step).toFixed(1)}" cy="${(height - (p.value / max) * height).toFixed(1)}" r="3" />`)
      .join('');
    return `<svg class="spark" viewBox="0 0 ${width} ${height}" role="img"
        aria-label="Coverage per run: ${points.map((p) => `${p.value}%`).join(', ')}">
        <path class="spark-line" d="${path}" />
        <g class="spark-dots">${dots}</g>
      </svg>`;
  }

  function renderProgress(ctx) {
    const runs = S.runs.all();
    const drills = Object.values(S.drills.all());

    if (runs.length < 2) {
      $('progressBody').innerHTML = `
        <section class="panel">
          <div class="panel-head"><h2>After your next run</h2></div>
          <p class="invite">
            Progress compares one run against the next, and ${runs.length === 1 ? 'only one is' : 'none is'}
            recorded so far. Run again once you have played more games and this
            page will show your coverage over time, the leaks you have closed and what they were
            costing you, and how your drills are holding up.
          </p>
        </section>
        ${drills.length ? retentionPanel(drills) : ''}`;
      return;
    }

    const latest = runs[runs.length - 1];
    const previous = runs[runs.length - 2];
    const closed = (previous.keys || []).filter((k) => !(latest.keys || []).includes(k));
    const lostByKey = Object.fromEntries((previous.perGame || []).map((p) => [p.key, p.lost]));
    const recovered = closed.reduce((sum, k) => sum + (lostByKey[k] || 0), 0);
    const perGame = previous.games ? recovered / previous.games : 0;

    $('progressBody').innerHTML = `
      <section class="panel">
        <div class="panel-head">
          <h2>Coverage over time</h2>
          <span class="hint">${esc(V.METRICS.coverage.definition)}</span>
        </div>
        ${sparkline(runs.map((r) => ({ value: r.coverage || 0 })))}
        <div class="spark-scale">
          <span>${new Date(runs[0].at).toLocaleDateString()}</span>
          <span class="mono">${latest.coverage}%</span>
          <span>${new Date(latest.at).toLocaleDateString()}</span>
        </div>
      </section>

      <section class="panel">
        <div class="panel-head">
          <h2>Leaks closed</h2>
          <span class="hint">In the run before last, gone from the latest one</span>
        </div>
        ${closed.length
          ? `<p class="panel-note">${plural(closed.length, 'leak')} closed, worth
               <b>${perGame.toFixed(3)}</b> points a game at the rate they were costing you.</p>
             <ul class="closed-list">${closed
               .map((k) => `<li><span>${esc((previous.labels || {})[k] || k)}</span>
                 <span class="mono">${(lostByKey[k] || 0).toFixed(1)}</span></li>`)
               .join('')}</ul>`
          : '<p class="invite">Nothing from the previous run has gone yet. Committing an answer is the first half; playing it is the second.</p>'}
      </section>

      ${retentionPanel(drills)}`;
  }

  function retentionPanel(drills) {
    if (!drills.length) {
      return `<section class="panel">
        <div class="panel-head"><h2>Drill retention</h2></div>
        <p class="invite">Solve a drill in Practice and its success rate and next review date appear here.</p>
      </section>`;
    }
    const rows = drills
      .slice()
      .sort((a, b) => (a.due || 0) - (b.due || 0))
      .map((d) => {
        const tries = d.right + d.wrong;
        const rate = tries ? Math.round((d.right / tries) * 100) : 0;
        const due = d.due ? new Date(d.due) : null;
        const overdue = due && due.getTime() <= Date.now();
        return `<li>
          <span class="drill-label">${esc(d.label || d.key)}</span>
          <span class="mono">${rate}%<i class="muted"> of ${tries} ${tries === 1 ? 'try' : 'tries'}</i></span>
          <span class="mono ${overdue ? 'is-due' : 'muted'}">${due ? (overdue ? 'due now' : due.toLocaleDateString()) : '—'}</span>
        </li>`;
      })
      .join('');
    return `<section class="panel">
      <div class="panel-head">
        <h2>Drill retention</h2>
        <span class="hint">Success rate and the next time each position is worth revisiting</span>
      </div>
      <ul class="retention">${rows}</ul>
    </section>`;
  }

  /* ---------------------------------------------------------------- exports */
  /* Standard PGN movetext: the first child continues the line, the rest become
     nested variations. A black move only takes a number when something — the
     start of a line, or the variation just closed — broke the sequence. */
  function movetext(children, ply, forceNumber) {
    if (!children.length) return '';
    const [first, ...rest] = children;
    const out = [numbered(first.san, ply, forceNumber)];
    rest.forEach((sib) => {
      out.push(`(${numbered(sib.san, ply, true)}${prefixed(movetext(sib.children, ply + 1, false))})`);
    });
    const cont = movetext(first.children, ply + 1, rest.length > 0);
    if (cont) out.push(cont);
    return out.join(' ');
  }

  const numbered = (san, ply, force) =>
    ply % 2 === 0 ? `${ply / 2 + 1}. ${san}` : force ? `${(ply - 1) / 2 + 1}... ${san}` : san;
  const prefixed = (text) => (text ? ` ${text}` : '');

  /** The committed tree as PGN, one game per colour, variations nested. */
  function pgn(player) {
    const committed = S.repertoire.committed();
    if (!committed.length) return '';
    const games = ['white', 'black']
      .map((side) => {
        const entries = committed.filter((e) => e.color === side);
        if (!entries.length) return '';
        const body = movetext(buildTree(entries).children, 0, true);
        const who = player || 'Me';
        return [
          '[Event "Opening Leak Lab repertoire"]',
          `[Site "opening-leak-lab"]`,
          `[Date "${new Date().toISOString().slice(0, 10).replace(/-/g, '.')}"]`,
          `[White "${side === 'white' ? who : '?'}"]`,
          `[Black "${side === 'black' ? who : '?'}"]`,
          '[Result "*"]',
          `[Annotator "Opening Leak Lab"]`,
          '',
          `${body} *`,
          '',
        ].join('\n');
      })
      .filter(Boolean);
    return games.join('\n');
  }

  /** The drill set as PGN with a FEN per position, for drilling in another tool. */
  function drillPgn(rows) {
    const list = (rows || []).filter((r) => r && r.fen);
    if (!list.length) return '';
    return list
      .map((r) => {
        const answer = r.engine_best_1 || '';
        const white = r.player_color === 'white';
        const move = answer
          ? `${r.move_number}${white ? '.' : '...'} ${answer}`
          : '';
        const lead = V.leadFlag(r.flag);
        const note = `{${(r.opening || r.eco || 'Unclassified')} — you played ${r.your_move} here `
          + `${plural(+r.your_games, 'time')}${lead ? `; ${V.FLAGS[lead].short}` : ''}. `
          + `Cost ${Number(r.cost || 0).toFixed(1)}.}`;
        return [
          '[Event "Opening Leak Lab drill"]',
          '[Result "*"]',
          '[SetUp "1"]',
          `[FEN "${r.fen}"]`,
          `[Annotator "Opening Leak Lab"]`,
          '',
          `${note}${move ? ` ${move}` : ''} *`,
          '',
        ].join('\n');
      })
      .join('\n');
  }

  /** Lichess's import page accepts a PGN in the query string, up to a point. */
  function studyUrl() {
    const text = pgn();
    if (!text) return 'https://lichess.org/study';
    const url = `https://lichess.org/paste?pgn=${encodeURIComponent(text)}`;
    return url.length > 7000 ? 'https://lichess.org/paste' : url;
  }

  function wire() {
    document.querySelectorAll('#repColor .seg').forEach((b) =>
      b.addEventListener('click', () => {
        colour = b.dataset.color;
        renderRepertoire(window.App ? window.App.reportContext() : {});
      }),
    );
    document.querySelectorAll('#playedFilter .seg').forEach((b) =>
      b.addEventListener('click', () => {
        playedFilter = b.dataset.played;
        renderPlayed(window.App ? window.App.reportContext() : {});
      }),
    );
  }

  wire();

  window.Repertoire = {
    coverage,
    renderRepertoire,
    renderProgress,
    pgn,
    drillPgn,
    studyUrl,
    buildTree,
  };
})();
