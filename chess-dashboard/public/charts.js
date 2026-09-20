/* Two charts, drawn as inline SVG.

   This replaced Chart.js, which was 200KB fetched from a CDN by a page whose whole
   pitch is that nothing leaves the machine. Two bar charts do not justify either the
   weight or the contradiction. Drawing them here also fixes the thing a <canvas>
   cannot do: every chart carries a real table underneath it, so the numbers are
   available to a screen reader, to Ctrl-F, and to anyone who would rather read them.

   Colours are validated against the dark surface for contrast and colour-vision
   separation rather than picked by eye — see IMPROVEMENT_PLAN.md. */
(() => {
  const GRID = '#1c2327';
  const INK = '#949c9f';
  const INK_DIM = '#6a7276';
  const AMBER = '#bd7f28'; // magnitude, single series
  const YOURS = '#e06a5f'; // you
  const BOOK = '#4f9ad4';  // the database

  const esc = (s) =>
    String(s).replace(/[&<>"']/g, (c) =>
      ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  /* Nice round axis maxima, so ticks land on numbers a person would choose. */
  function niceMax(value) {
    if (value <= 0) return 1;
    const pow = 10 ** Math.floor(Math.log10(value));
    const norm = value / pow;
    const step = norm <= 1 ? 1 : norm <= 2 ? 2 : norm <= 5 ? 5 : 10;
    return step * pow;
  }

  function ticks(max, count = 4) {
    return Array.from({ length: count + 1 }, (_, i) => (max / count) * i);
  }

  /* A bar with a rounded data-end and a square baseline: the shape says which end is
     the measurement and which is the origin. */
  function barPath(x, y, w, h, r, horizontal) {
    const rr = Math.max(0, Math.min(r, horizontal ? w : h));
    if (horizontal) {
      return `M${x},${y} H${x + w - rr} a${rr},${rr} 0 0 1 ${rr},${rr} V${y + h - rr}` +
        ` a${rr},${rr} 0 0 1 ${-rr},${rr} H${x} Z`;
    }
    return `M${x},${y + rr} a${rr},${rr} 0 0 1 ${rr},${-rr} H${x + w - rr}` +
      ` a${rr},${rr} 0 0 1 ${rr},${rr} V${y + h} H${x} Z`;
  }

  /* Openings share long prefixes — "King's Knight Opening: Normal Variation" and
     "...: Konstantinopolsky" differ only at the end, so a head-truncation labels two
     different bars identically. Keep the distinguishing tail. */
  function truncate(s, n) {
    if (s.length <= n) return s;
    const colon = s.indexOf(':');
    if (colon > 0 && s.length - colon - 2 <= n - 2) return '…' + s.slice(colon + 2);
    return s.slice(0, n - 1) + '…';
  }

  /* ------------------------------------------------------ points lost by opening */
  function lostByOpening(el, items) {
    const H = 300, PAD_L = 132, PAD_R = 44, PAD_T = 8, PAD_B = 26;
    const W = Math.max(el.clientWidth || 420, 320);
    const plotW = W - PAD_L - PAD_R;
    const rows = items.length;
    const band = (H - PAD_T - PAD_B) / Math.max(rows, 1);
    const thickness = Math.min(24, band - 8); // cap it; the leftover is deliberate air
    const max = niceMax(Math.max(...items.map((o) => o.lost_points), 0.1));
    const x = (v) => (v / max) * plotW;

    const grid = ticks(max).map((t) => `
      <line x1="${PAD_L + x(t)}" y1="${PAD_T}" x2="${PAD_L + x(t)}" y2="${H - PAD_B}"
            stroke="${GRID}" stroke-width="1" />
      <text x="${PAD_L + x(t)}" y="${H - PAD_B + 15}" fill="${INK_DIM}" font-size="10.5"
            text-anchor="middle">${t % 1 ? t.toFixed(1) : t}</text>`).join('');

    const bars = items.map((o, i) => {
      const y = PAD_T + i * band + (band - thickness) / 2;
      const w = Math.max(x(o.lost_points), 1);
      return `<g class="ch-bar" tabindex="0" role="listitem"
              aria-label="${esc(o.opening)}: ${o.lost_points.toFixed(1)} points lost across ${o.games} games"
              data-tip="${esc(o.opening)} — ${o.lost_points.toFixed(1)} points · ${o.leaks} leaks · ${o.games} games">
        <rect x="0" y="${PAD_T + i * band}" width="${W}" height="${band}" fill="transparent" />
        <text x="${PAD_L - 10}" y="${y + thickness / 2 + 4}" fill="${INK}" font-size="11"
              text-anchor="end">${esc(truncate(o.opening, 20))}</text>
        <path d="${barPath(PAD_L, y, w, thickness, 4, true)}" fill="${AMBER}" />
        <text x="${PAD_L + w + 7}" y="${y + thickness / 2 + 4}" fill="${INK}" font-size="10.5"
              >${o.lost_points.toFixed(1)}</text>
      </g>`;
    }).join('');

    return `<svg viewBox="0 0 ${W} ${H}" width="100%" height="${H}" role="list"
                 aria-label="Points lost by opening">${grid}${bars}</svg>`;
  }

  /* ------------------------------------------------------------- you vs the book */
  function youVsBook(el, items) {
    const H = 300, PAD_L = 34, PAD_R = 8, PAD_T = 8, PAD_B = 74;
    const W = Math.max(el.clientWidth || 420, 320);
    const plotW = W - PAD_L - PAD_R, plotH = H - PAD_T - PAD_B;
    const band = plotW / Math.max(items.length, 1);
    const GAP = 2; // surface gap: the pair reads as two marks, with no stroke drawn
    const barW = Math.min(11, (band - 14 - GAP) / 2);
    const y = (pct) => PAD_T + plotH - (Math.max(0, Math.min(100, pct)) / 100) * plotH;

    const grid = [0, 25, 50, 75, 100].map((t) => `
      <line x1="${PAD_L}" y1="${y(t)}" x2="${W - PAD_R}" y2="${y(t)}" stroke="${GRID}" stroke-width="1" />
      <text x="${PAD_L - 6}" y="${y(t) + 3.5}" fill="${INK_DIM}" font-size="10.5"
            text-anchor="end">${t}%</text>`).join('');

    const cols = items.map((o, i) => {
      const cx = PAD_L + i * band + band / 2;
      const left = cx - barW - GAP / 2;
      const label = truncate(o.opening, 16);
      const pair = [[o.your_score, YOURS, left], [o.db_score, BOOK, cx + GAP / 2]];
      return `<g class="ch-bar" tabindex="0" role="listitem"
              aria-label="${esc(o.opening)}: you score ${Math.round(o.your_score)} percent, the book scores ${Math.round(o.db_score)} percent"
              data-tip="${esc(o.opening)} — you ${Math.round(o.your_score)}% · book ${Math.round(o.db_score)}%">
        <rect x="${PAD_L + i * band}" y="${PAD_T}" width="${band}" height="${plotH}" fill="transparent" />
        ${pair.map(([v, fill, bx]) =>
          `<path d="${barPath(bx, y(v), barW, PAD_T + plotH - y(v), 4, false)}" fill="${fill}" />`).join('')}
        <text transform="translate(${cx},${H - PAD_B + 12}) rotate(-40)" text-anchor="end"
              fill="${INK_DIM}" font-size="9.5">${esc(label)}</text>
      </g>`;
    }).join('');

    return `<svg viewBox="0 0 ${W} ${H}" width="100%" height="${H}" role="list"
                 aria-label="Your score against the book score, by opening">${grid}${cols}</svg>`;
  }

  /* ------------------------------------------------------------ shared furniture */
  function legend(series) {
    return `<div class="ch-legend">${series.map(([name, colour]) =>
      `<span class="ch-key"><i style="background:${colour}"></i>${esc(name)}</span>`).join('')}</div>`;
  }

  /* The table is the accessible view and the precise one — never a fallback that only
     appears when something fails. It is collapsed, not hidden. */
  function table(caption, headers, rows, open) {
    return `<details class="ch-table"${open ? ' open' : ''}>
      <summary>Show the numbers</summary>
      <table><caption class="sr-only">${esc(caption)}</caption>
        <thead><tr>${headers.map((h) => `<th scope="col">${esc(h)}</th>`).join('')}</tr></thead>
        <tbody>${rows.map((r) =>
          `<tr><th scope="row">${esc(r[0])}</th>${r.slice(1).map((c) =>
            `<td>${esc(c)}</td>`).join('')}</tr>`).join('')}</tbody>
      </table></details>`;
  }

  /* One tooltip element, moved around — a node per bar would be hundreds of nodes for
     something only ever shown once at a time. */
  function attachTips(root) {
    let tip = root.querySelector('.ch-tip');
    if (!tip) {
      tip = document.createElement('div');
      tip.className = 'ch-tip';
      tip.hidden = true;
      root.appendChild(tip);
    }
    const show = (target) => {
      const box = target.getBoundingClientRect();
      const host = root.getBoundingClientRect();
      tip.textContent = target.dataset.tip;
      tip.hidden = false;
      tip.style.left = `${Math.min(box.left - host.left + box.width / 2, host.width - 12)}px`;
      tip.style.top = `${box.top - host.top - 6}px`;
    };
    const hide = () => { tip.hidden = true; };
    root.querySelectorAll('.ch-bar').forEach((bar) => {
      bar.addEventListener('mouseenter', () => show(bar));
      bar.addEventListener('focus', () => show(bar));
      bar.addEventListener('mouseleave', hide);
      bar.addEventListener('blur', hide);
    });
    root.addEventListener('mouseleave', hide);
  }

  const isOpen = (el) => !!el.querySelector('.ch-table[open]');

  function render(byOpening) {
    const items = (byOpening || []).slice(0, 8);
    const lost = document.getElementById('chartLost');
    const vs = document.getElementById('chartVs');
    if (!lost || !vs) return;
    document.querySelectorAll('.chart-empty').forEach((el) => el.remove());
    if (!items.length) return;

    // A redraw must not close a table the reader opened — a resize or a view switch
    // silently undoing their action is worse than not redrawing at all.
    const wasOpen = { lost: isOpen(lost), vs: isOpen(vs) };

    lost.innerHTML = lostByOpening(lost, items) +
      table('Points lost by opening', ['Opening', 'Points lost', 'Leaks', 'Games'],
        items.map((o) => [o.opening, o.lost_points.toFixed(1), o.leaks, o.games]), wasOpen.lost);

    vs.innerHTML = legend([['You', YOURS], ['The book', BOOK]]) + youVsBook(vs, items) +
      table('Your score against the book, by opening',
        ['Opening', 'Your score', 'Book score'],
        items.map((o) => [o.opening, `${Math.round(o.your_score)}%`, `${Math.round(o.db_score)}%`]),
        wasOpen.vs);

    attachTips(lost);
    attachTips(vs);
  }

  let last = null;
  /* A view switch, a drawer opening, a window resize — all of them change the box the
     SVG has to fit, and a chart rendered while its section was hidden measured zero.
     One observer covers every case; a window resize listener covered only one. */
  let observed = false;
  let pending = null;
  function observe() {
    if (observed || typeof ResizeObserver === 'undefined') return;
    const ro = new ResizeObserver((entries) => {
      if (!last) return;
      const grew = entries.some((e) => e.contentRect.width > 0);
      if (!grew) return;
      clearTimeout(pending);
      pending = setTimeout(() => render(last), 80);
    });
    ['chartLost', 'chartVs'].forEach((id) => {
      const el = document.getElementById(id);
      if (el) ro.observe(el);
    });
    observed = true;
  }

  window.LeakCharts = {
    render(byOpening) {
      last = byOpening;
      render(byOpening);
      observe();
    },
  };
})();
