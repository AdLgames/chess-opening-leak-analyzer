/* One working board, an opening library, and the established user-data store. */
(function () {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const S = window.Store;
  const LB = window.LeakBoard;
  const esc = LB.esc;
  const openings = window.OpeningGuides;
  let selected = openings[0];
  let selectedLine = 0;
  let side = 'all';
  let panel = 'study';
  const saved = () => S.repertoire.committed().slice().sort((a, b) => b.decidedAt - a.decidedAt);
  const pathOf = (entry) => entry.explorePath?.length ? entry.explorePath : [...(entry.line || []), entry.answer].filter(Boolean);
  const notation = (moves) => moves.map((m, i) => `${i % 2 ? '' : `${i / 2 + 1}. `}${m}`).join(' ');
  const lines = () => selected ? [{ name: 'Starting line', line: selected.line }, ...selected.branches] : [];

  function thumbnail(fen, colour = 'white') {
    const pieces = LB.parseFen(fen).board;
    const files = colour === 'white' ? 'abcdefgh' : 'hgfedcba';
    const ranks = colour === 'white' ? [8,7,6,5,4,3,2,1] : [1,2,3,4,5,6,7,8];
    return `<span class="board-thumbnail" aria-hidden="true">${ranks.map((rank) => [...files].map((file) => `<span class="thumb-square ${(file.charCodeAt(0) - 97 + rank) % 2 ? 'dark' : 'light'}">${LB.pieceSvg(pieces[file + rank])}</span>`).join('')).join('')}</span>`;
  }
  function card(o) {
    const course = window.OpeningCourses.find((c) => c.opening === o.id);
    return `<button class="opening-card" data-opening="${o.id}">${thumbnail(o.fen, o.side)}<span class="opening-card-content"><span class="opening-card-top"><strong>${esc(o.name)}</strong><span class="opening-code">${o.eco}</span></span><span class="opening-card-description">${esc(o.idea)}</span><span class="opening-card-foot"><span>${o.side === 'white' ? 'White' : 'Black'} · ${course ? `${course.chapters.length} guided chapters` : `${1 + o.branches.length} lines`}</span><span>${course ? 'Learn & explore' : 'Study opening'} →</span></span></span></button>`;
  }
  function renderOpenings() {
    const q = $('libSearch').value.trim().toLowerCase();
    const found = openings.filter((o) => (side === 'all' || o.side === side)
      && `${o.name} ${o.eco} ${o.line.join(' ')} ${notation(o.line)}`.toLowerCase().includes(q));
    $('exploreOpenings').innerHTML = found.length ? found.map(card).join('') : '<p class="catalog-empty">No study guide matches these filters. Database matches appear below.</p>';
    $('catalogCount').textContent = `${found.length} opening${found.length === 1 ? '' : 's'} · ${found.reduce((n, o) => n + 1 + o.branches.length, 0)} lines${q ? ' matching your search' : ' to explore'}`;
    $('databaseSearchTitle').hidden = !q;
    $('exploreOpenings').querySelectorAll('[data-opening]').forEach((button) => button.addEventListener('click', () => choose(button.dataset.opening)));
  }
  function setPanel(next, focus = false) {
    if (next === 'saved') renderSaved();
    panel = next;
    document.querySelectorAll('[data-panel]').forEach((button) => {
      const active = button.dataset.panel === next;
      button.classList.toggle('is-active', active);
      button.setAttribute('aria-selected', String(active));
      button.tabIndex = active ? 0 : -1;
      $(`${button.dataset.panel}Pane`).hidden = !active;
      if (active && focus) button.focus();
    });
  }
  function renderGuide() {
    window.Training?.overview(selected?.id || null);
    if (!selected) return;
    $('openingGuideTitle').textContent = selected.name;
    $('guideMeta').textContent = `${selected.eco} · ${selected.side === 'white' ? 'White' : 'Black'} · Opening study`;
    $('openingGuideText').textContent = selected.idea;
    $('openingPlan').textContent = selected.plan;
    $('guideReplay').hidden = false;
    $('guideLineCount').textContent = `${lines().length} lines`;
    $('guideLines').innerHTML = lines().map((line, index) => `<button class="study-line ${index === selectedLine ? 'is-active' : ''}" data-guide-line="${index}"><span class="line-number">${String(index + 1).padStart(2, '0')}</span><span><strong>${esc(line.name)}</strong><span class="mono">${esc(notation(line.line))}</span></span><span class="line-open" aria-hidden="true">→</span></button>`).join('');
    $('guideLines').querySelectorAll('button').forEach((button) => button.addEventListener('click', async () => {
      selectedLine = Number(button.dataset.guideLine);
      renderGuide();
      await window.Study.explore(lines()[selectedLine].line, null, { orientation: selected.side });
    }));
  }
  async function choose(id) {
    const opening = openings.find((o) => o.id === id);
    if (!opening) return;
    await window.Training?.pause();
    selected = opening; selectedLine = 0;
    window.App.go('today');
    renderGuide(); setPanel('study');
    $('saveLineSide').value = opening.side;
    $('saveLineName').value = opening.name;
    $('saveLineNote').value = '';
    await window.Study.explore(opening.line, null, { orientation: opening.side });
  }
  function custom(title, note = '') {
    selected = null;
    window.Training?.overview(null);
    $('openingGuideTitle').textContent = title;
    $('guideMeta').textContent = 'Position study';
    $('openingGuideText').textContent = note || 'Explore the position on the board. The Moves panel shows replies from the opening book.';
    $('openingPlan').textContent = 'Compare the replies, play a continuation and save the response you want to use.';
    $('guideLines').innerHTML = '<p class="muted small">Play moves on the board to build a line from this position.</p>';
    $('guideLineCount').textContent = '';
    $('guideReplay').hidden = true;
    setPanel('study');
  }
  async function reopen(entry) {
    if (!entry) return;
    await window.Training?.pause();
    window.App.go('today');
    custom(entry.name || entry.opening || 'Saved line', entry.notes);
    $('saveLineSide').value = entry.color;
    $('saveLineName').value = entry.name || entry.opening || '';
    $('saveLineNote').value = entry.notes || '';
    await window.Study.explore(pathOf(entry), entry.startFen || null, { fromPosition: true, orientation: entry.color });
  }
  function entryCard(entry) {
    return `<button class="saved-line-card" data-entry="${esc(entry.key)}">${thumbnail(entry.fen, entry.color)}<span class="saved-line-content"><strong>${esc(entry.name || entry.opening || 'Opening line')}</strong><span class="mono">${esc(notation(pathOf(entry)))}</span>${entry.notes ? `<span class="saved-note">${esc(entry.notes)}</span>` : ''}<span class="card-action">${entry.color === 'black' ? 'Black' : 'White'} · Open line →</span></span></button>`;
  }
  function wireEntries(host) {
    host.querySelectorAll('[data-entry]').forEach((button) => button.addEventListener('click', () => reopen(S.repertoire.byKey(button.dataset.entry))));
  }
  function renderSaved() {
    const entries = saved();
    $('savedLineCards').innerHTML = entries.length ? ['white', 'black'].map((colour) => `<section class="saved-side"><h3>${colour === 'white' ? 'White' : 'Black'} <span>${entries.filter((e) => e.color === colour).length}</span></h3><div class="saved-line-list">${entries.filter((e) => e.color === colour).map(entryCard).join('') || '<p class="muted small">No saved lines for this side.</p>'}</div></section>`).join('') : '<div class="empty-workspace"><p>No lines saved yet.</p><a class="btn btn-primary" href="#explore">Browse openings</a><a class="text-link" href="#repertoire/edit">Build a line from scratch →</a></div>';
    wireEntries($('savedLineCards'));
    $('sidebarSaved').innerHTML = entries.length ? entries.slice(0, 8).map((entry) => `<button class="sidebar-line" data-entry="${esc(entry.key)}"><strong>${esc(entry.name || entry.opening || 'Opening line')}</strong><span class="mono">${esc(pathOf(entry).join(' '))}</span></button>`).join('') : '<p class="muted">Play a line and press Save line to keep it here.</p>';
    wireEntries($('sidebarSaved'));
  }
  function renderProgress(ctx) {
    const entries = saved(); const drills = Object.values(S.drills.all()); const runs = S.runs.all();
    const attempts = drills.reduce((n, d) => n + d.right + d.wrong, 0);
    $('progressPanel').hidden = !runs.length && !drills.length;
    document.querySelector('.personal-details').hidden = !ctx.summary?.explorer;
    $('progressSummary').textContent = attempts ? `${attempts} practice attempts across ${drills.length} positions.` : 'Your saved lines, practice record and game analysis.';
    $('progressEvidence').innerHTML = [
      ['Repertoire', `${entries.length} saved ${entries.length === 1 ? 'response' : 'responses'}`, 'The opening choices you have prepared.'],
      ['Practice', attempts ? `${attempts} attempts` : 'No attempts yet', 'Your results and review dates appear below after practice.'],
      ['Game analysis', runs.length ? `${runs.length} runs` : 'No games imported', 'Compare your preparation with your own games.'],
    ].map(([title, value, note]) => `<article class="evidence-card"><h3>${title}</h3><strong>${value}</strong><p>${note}</p></article>`).join('');
  }
  $('todayBoardSlot').append(document.querySelector('.library-panel'));
  $('progressSlot').append($('progressPanel'));
  $('personalSlot').append($('explorerPersonal'));
  $('openingSide').querySelectorAll('button').forEach((button) => button.addEventListener('click', () => {
    side = button.dataset.side;
    $('openingSide').querySelectorAll('button').forEach((b) => { b.classList.toggle('is-active', b === button); b.setAttribute('aria-pressed', String(b === button)); });
    renderOpenings();
  }));
  $('libSearch').addEventListener('input', renderOpenings);
  document.querySelectorAll('[data-panel]').forEach((button) => button.addEventListener('click', () => setPanel(button.dataset.panel)));
  document.querySelector('.study-tabs').addEventListener('keydown', (event) => {
    const keys = ['study','moves','saved'];
    if (!['ArrowLeft','ArrowRight','Home','End'].includes(event.key)) return;
    event.preventDefault();
    const index = keys.indexOf(panel);
    setPanel(event.key === 'Home' ? 'study' : event.key === 'End' ? 'saved' : keys[(index + (event.key === 'ArrowRight' ? 1 : 2)) % 3], true);
  });
  $('guideReplay').addEventListener('click', () => { if (selected) window.Study.replay(lines()[selectedLine].line, selected.side); });
  window.addEventListener('chess:position', (event) => {
    if (window.Training?.active()) return;
    const { line, turn, opening } = event.detail;
    if (selected && line.length && !lines().some((known) => {
      const overlap = Math.min(line.length, known.line.length);
      return line.slice(0, overlap).every((move, index) => move === known.line[index]);
    })) custom(opening?.name || 'Your continuation', 'Explore replies in Moves, or save this continuation to your repertoire.');
    $('studyLineLabel').textContent = `${line.length ? `After ${line[line.length - 1]}` : 'Starting position'} · ${turn === 'white' ? 'White' : 'Black'} to move`;
  });
  renderOpenings(); renderGuide(); renderSaved(); setPanel('study');
  function boardPalette() {
    const value = S.prefs.get('boardPalette', 'green') === 'wood' ? 'wood' : 'green';
    document.documentElement.dataset.board = value; $('boardPalette').value = value;
  }
  $('boardPalette').addEventListener('change', (event) => { S.prefs.set('boardPalette', event.target.value); boardPalette(); });
  boardPalette(); window.Coach.refresh();
  window.Workspace = {
    choose, reopen, custom, setPanel, refreshGuide: renderGuide,
    async position(line, side, title) {
      await window.Training.pause(); window.App.go('today'); custom(title);
      $('saveLineSide').value = side; $('saveLineName').value = title;
      await window.Study.explore(line, null, { orientation: side });
    },
    render(view, ctx = {}) {
      boardPalette();
      window.Coach.refresh();
      window.Training?.leave(view);
      window.Training?.overview(selected?.id || null);
      window.Preparation?.render(view, ctx);
      if (view === 'today' || view === 'repertoire') renderSaved();
      if (view === 'progress') { renderProgress(ctx); window.Training?.progress(); }
    },
  };
}());
