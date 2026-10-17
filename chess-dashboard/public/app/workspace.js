/* The learning workspace composes existing boards and persistence; no parallel store. */
(function () {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const S = window.Store;
  const LB = window.LeakBoard;
  const esc = LB.esc;
  const openings = [
    { id: 'italian', name: 'Italian Game', eco: 'C50', side: 'white', mark: '♘', line: ['e4', 'e5', 'Nf3', 'Nc6', 'Bc4'], text: 'Develop naturally, aim at the centre and bring your king to safety.', idea: 'The bishop on c4 puts pressure on f7. Develop your remaining pieces and look to castle; c3 and d4 can help you challenge the centre.' },
    { id: 'caro', name: 'Caro-Kann Defence', eco: 'B10', side: 'black', mark: '♟', line: ['e4', 'c6', 'd4', 'd5'], text: 'Challenge the centre with a solid, patient structure against 1.e4.', idea: 'With …c6 supporting …d5, Black challenges White’s centre. Watch how White resolves the pawn tension before choosing where to develop your pieces.' },
    { id: 'queens', name: 'Queen’s Gambit Declined', eco: 'D30', side: 'black', mark: '♜', line: ['d4', 'd5', 'c4', 'e6'], text: 'Meet 1.d4 with a dependable centre and harmonious development.', idea: 'The pawn on e6 supports d5. Develop with …Nf6 and …Be7, then castle. Your light-squared bishop needs a plan as the centre opens.' },
  ];
  // Move existing nodes, preserving IDs, listeners, boards and all legacy tools.
  $('exploreBoardSlot').append(document.querySelector('.library-panel'));
  $('progressSlot').append($('progressPanel'));
  $('personalSlot').append($('explorerPersonal'));
  const saved = () => S.repertoire.committed().slice().sort((a, b) => b.decidedAt - a.decidedAt);
  const pathOf = (entry) => entry.explorePath?.length ? entry.explorePath : [...(entry.line || []), entry.answer].filter(Boolean);
  const card = (o) => `<button class="opening-card" data-opening="${o.id}"><span class="opening-card-top"><span class="opening-symbol" aria-hidden="true">${o.mark}</span><span class="tag">${o.side === 'white' ? 'White' : 'Black vs ' + (o.id === 'caro' ? '1.e4' : '1.d4')}</span></span><span class="opening-card-title">${o.name}</span><span class="opening-card-description">${o.text}</span><span class="opening-card-foot">${o.eco} · Opening guide <span aria-hidden="true">→</span></span></button>`;
  function wireCards(host) {
    host.querySelectorAll('[data-opening]').forEach((button) => button.addEventListener('click', () => choose(button.dataset.opening)));
  }
  function renderOpenings(side = 'all') {
    $('exploreOpenings').innerHTML = openings.filter((o) => side === 'all' || o.side === side).map(card).join('');
    wireCards($('exploreOpenings'));
  }
  async function choose(id) {
    const o = openings.find((item) => item.id === id);
    if (!o) return;
    window.App.go('explore');
    $('openingGuideTitle').textContent = o.name;
    $('openingGuideText').textContent = o.idea;
    $('saveLineSide').value = o.side;
    $('saveLineName').value = o.name;
    $('saveLineNote').value = '';
    await window.Study.explore(o.line, null, { orientation: o.side });
    document.querySelector('.explore-heading').scrollIntoView({ block: 'start', behavior: 'smooth' });
  }
  async function reopen(entry) {
    window.App.go('explore');
    $('openingGuideTitle').textContent = entry.name || entry.opening || 'Your saved line';
    $('openingGuideText').textContent = entry.notes || 'Your saved move order. Continue exploring, or step back to try another response.';
    $('saveLineSide').value = entry.color;
    $('saveLineName').value = entry.name || entry.opening || '';
    $('saveLineNote').value = entry.notes || '';
    await window.Study.explore(pathOf(entry), entry.startFen || null, { fromPosition: true, orientation: entry.color });
  }
  function entryCard(entry) {
    return `<button class="saved-line-card" data-entry="${esc(entry.key)}"><span class="tag">${entry.color === 'black' ? 'Black' : 'White'} · Saved choice</span><strong>${esc(entry.name || entry.opening || 'My opening line')}</strong><span class="mono">${esc(pathOf(entry).join(' '))}</span>${entry.notes ? `<span class="small muted">${esc(entry.notes)}</span>` : ''}<span class="card-action">Open on the board →</span></button>`;
  }
  function wireEntries(host) {
    host.querySelectorAll('[data-entry]').forEach((button) => button.addEventListener('click', () => reopen(S.repertoire.byKey(button.dataset.entry))));
  }
  function renderToday(ctx) {
    const entries = saved();
    const hasFindings = (ctx.rows || []).length > 0;
    $('todayNext').textContent = entries.length ? 'Pick up where you left off.' : hasFindings ? 'Understand your next opening decision.' : 'Find your opening.';
    $('todayDescription').textContent = entries.length ? `Return to ${entries[0].name || entries[0].opening || 'your saved line'}, explore a common reply and make your next choice.` : hasFindings ? 'Your game analysis has positions worth a closer look. Explore the alternatives on the board.' : 'Start with a position, discover the ideas and save the moves you want to play. Your games can come later.';
    $('todayStart').innerHTML = `${entries.length ? 'Continue your line' : hasFindings ? 'Review a position' : 'Explore openings'} <span aria-hidden="true">→</span>`;
    $('todayStart').onclick = () => entries.length ? reopen(entries[0]) : window.App.go(hasFindings ? 'clinic' : 'explore');
    $('todayFootnote').textContent = entries.length ? (S.persistent() ? 'Your choices are kept on this device.' : 'Storage is unavailable. Keep this tab open to retain your choices.') : 'No import or account needed.';
    $('continueTitle').textContent = entries.length ? 'Continue your repertoire' : 'A good place to start';
    $('todayOpenings').innerHTML = entries.length ? entries.slice(0, 2).map(entryCard).join('') : openings.slice(0, 2).map(card).join('');
    wireCards($('todayOpenings')); wireEntries($('todayOpenings'));
  }
  function renderSaved() {
    const entries = saved();
    $('savedLineCards').innerHTML = entries.length ? ['white', 'black'].map((side) => `<section class="saved-side"><h3>As ${side === 'white' ? 'White' : 'Black'}</h3><div class="opening-cards">${entries.filter((e) => e.color === side).map(entryCard).join('') || '<p class="muted small">No choices saved for this side yet.</p>'}</div></section>`).join('') : '<div class="empty-workspace"><span class="empty-symbol" aria-hidden="true">♘</span><h3>Your repertoire starts with one choice.</h3><p>Explore an opening and save a line you would like to play. Everything you already saved stays here.</p><a class="btn btn-primary" href="#explore">Find your first opening</a></div>';
    wireEntries($('savedLineCards'));
  }
  function renderProgress(ctx) {
    const entries = saved(); const drills = Object.values(S.drills.all());
    const attempts = drills.reduce((n, d) => n + d.right + d.wrong, 0);
    const runs = S.runs.all();
    $('progressPanel').hidden = !runs.length && !drills.length;
    document.querySelector('.personal-details').hidden = !ctx.summary?.explorer;
    $('progressSummary').textContent = attempts ? `You have recorded ${attempts} practice attempts across ${drills.length} positions. Keep returning to build a reliable picture.` : entries.length ? 'You have made a start. Saved moves show your intentions; practice will add evidence over time.' : 'Start by saving a line. Your progress will grow from the choices you make and the positions you practise.';
    $('progressEvidence').innerHTML = [
      ['Your preparation', entries.length ? `${entries.length} saved ${entries.length === 1 ? 'choice' : 'choices'}` : 'A fresh start', 'Saved responses, not a measure of full opening coverage.'],
      ['Practice', attempts ? `${attempts} ${attempts === 1 ? 'attempt' : 'attempts'}` : 'Ready when you are', 'Existing drill history is kept. Independent recall needs a separate learning flow.'],
      ['In your games', runs.length ? `${runs.length} analysis ${runs.length === 1 ? 'run' : 'runs'}` : 'Optional', 'Import games to see personal opening patterns. No game evidence is inferred from practice.'],
    ].map(([title, value, note]) => `<article class="evidence-card"><p class="eyebrow">${title}</p><h3>${value}</h3><p>${note}</p></article>`).join('');
  }
  let todayBoard;
  function render(view, ctx = {}) {
    if (view === 'today') {
      renderToday(ctx);
      if (!todayBoard) {
        todayBoard = new LB.Board($('todayBoard'));
        todayBoard.setPosition('r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3', { legal: [] });
      }
    }
    if (view === 'repertoire') renderSaved();
    if (view === 'progress') renderProgress(ctx);
  }
  $('openingSide').querySelectorAll('button').forEach((button) => button.addEventListener('click', () => {
    $('openingSide').querySelectorAll('button').forEach((b) => { b.classList.toggle('is-active', b === button); b.setAttribute('aria-pressed', b === button ? 'true' : 'false'); });
    renderOpenings(button.dataset.side);
  }));
  renderOpenings();
  window.Workspace = { render, reopen };
}());
