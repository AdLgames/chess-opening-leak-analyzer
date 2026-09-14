/* Opening Leak Lab — the words the product uses.

   One name per concept. Filters, table cells, the detail panel, the legend,
   exports and tooltips all read their strings from here; nothing downstream
   writes a category name of its own. */
(function () {
  'use strict';

  /* Leak flags, keyed exactly as the analyzer emits them (chessopening/analyze.py). */
  const FLAGS = {
    blunder: {
      key: 'blunder',
      label: 'Loses ground',
      short: 'loses ground',
      tone: 'bad',
      definition:
        'The move itself is the problem — it gives up material or the advantage. Learn the right move.',
    },
    underperforming: {
      key: 'underperforming',
      label: 'Not working for you',
      short: 'not working for you',
      tone: 'warn',
      definition:
        'Playable, but your results are well below what the position is worth. Consider a different line.',
    },
    unfamiliar: {
      key: 'unfamiliar',
      label: 'Unfamiliar',
      short: 'unfamiliar',
      tone: 'book',
      definition: 'A position you will meet but have barely played. Prepare for it.',
    },
    thin: {
      key: 'thin',
      label: 'Worth watching',
      short: 'worth watching',
      tone: 'quiet',
      definition: 'Too few games to be sure. Play more before acting on it.',
    },
  };
  const FLAG_ORDER = ['blunder', 'underperforming', 'unfamiliar', 'thin'];

  /* Metrics. `cost` is the sort key for everything the product ranks. */
  const METRICS = {
    cost: {
      label: 'Cost',
      definition:
        'Frequency × severity, with a cautious estimate on thin samples. The sort key for everything.',
      formula:
        'cost = (score points shed per game + ¼ × eval drop) × games × games ÷ (games + 4)',
      why: 'The shrinkage is what stops a habit seen three times outranking one seen thirty.',
    },
    score: { label: 'Score', definition: 'Win% + half of draw%, as on Lichess.' },
    scoreGap: {
      label: 'You vs book',
      definition: "Your score with this move against the book's score with the same move.",
    },
    evalDrop: { label: 'Eval drop', definition: 'Engine evaluation change, in pawns.' },
    coverage: {
      label: 'Coverage',
      definition:
        'The share of your opening decisions — weighted by how often you play them — that '
        + 'are not an open leak. Committing an answer or dismissing a finding moves it.',
    },
  };

  /* Same verb from button to confirmation, every time. */
  const ACTIONS = {
    analyse: { button: 'Analyse my games', done: (n) => `Analysed ${n} games` },
    commit: { button: 'Commit this move', done: 'Committed' },
    dismiss: { button: 'Not interested', done: 'Dismissed' },
    drill: { button: 'Drill this', done: 'Added to practice' },
    rerun: { button: 'Run again', done: 'Re-analysed' },
  };

  /* Names this product used to have. Listed so the retirement is documented in one
     place, and so a grep for an old string lands here rather than in live code. */
  const RETIRED = ['Rare move', 'Not working', 'Offbeat', 'Lost', 'Swing', 'Priority', 'Score gap flag (%)'];

  const flag = (key) => FLAGS[key] || null;
  const flagKeys = (raw) =>
    String(raw || '')
      .split('+')
      .map((f) => f.trim())
      .filter((f) => FLAGS[f]);

  /* The chips shown in the table and the detail panel. */
  function chips(raw) {
    return flagKeys(raw)
      .map((k) => `<span class="chip chip-${FLAGS[k].tone}" title="${FLAGS[k].definition}">${FLAGS[k].label}</span>`)
      .join(' ');
  }

  /* The one flag that best describes a finding: the most actionable one present. */
  function leadFlag(raw) {
    const keys = flagKeys(raw);
    return FLAG_ORDER.find((k) => keys.includes(k)) || null;
  }

  window.Vocab = { FLAGS, FLAG_ORDER, METRICS, ACTIONS, RETIRED, flag, flagKeys, chips, leadFlag };
})();
