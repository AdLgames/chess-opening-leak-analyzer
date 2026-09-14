/* Opening Leak Lab — what the app remembers between runs.

   Everything here is the user's own data and stays in their browser: the lines
   they have committed, the findings they have dismissed, how their drills went,
   the runs they have done, and the last report so a reload does not start from
   an empty screen.

   localStorage is not always available (a private window, or an embedded
   preview), so every access falls back to an in-memory copy for the page view. */
(function () {
  'use strict';

  const PREFIX = 'leaklab:';
  const memory = new Map();
  let backing = null;

  function store() {
    if (backing !== null) return backing;
    try {
      const probe = `${PREFIX}probe`;
      window.localStorage.setItem(probe, '1');
      window.localStorage.removeItem(probe);
      backing = window.localStorage;
    } catch (err) {
      backing = false;
    }
    return backing;
  }

  function read(key, fallback) {
    const raw = store() ? store().getItem(PREFIX + key) : memory.get(key);
    if (raw == null) return fallback;
    try {
      return JSON.parse(raw);
    } catch (err) {
      return fallback;
    }
  }

  function write(key, value) {
    const raw = JSON.stringify(value);
    memory.set(key, raw);
    if (!store()) return false;
    try {
      store().setItem(PREFIX + key, raw);
      return true;
    } catch (err) {
      return false; // quota: the in-memory copy still serves this page view
    }
  }

  /* A position key that survives move-order transpositions and clock fields. */
  const positionKey = (fen) => String(fen || '').split(' ').slice(0, 4).join(' ');
  const leakKey = (row) => `${positionKey(row.fen)}|${row.your_move || ''}`;

  const lineBefore = (row) => String(row.variation_line || '').trim().split(/\s+/).filter(Boolean).slice(0, -1);

  /* ------------------------------------------------------------- repertoire */
  const repertoire = {
    all() {
      return read('repertoire', []);
    },
    byKey(key) {
      return this.all().find((e) => e.key === key) || null;
    },
    forPosition(fen) {
      const pos = positionKey(fen);
      return this.all().find((e) => e.position === pos) || null;
    },
    /** Record the move the user intends to play in this position from now on. */
    commit(row, move) {
      return this._put(row, { status: 'committed', answer: move || row.your_move });
    },
    /** Record that this finding is not worth acting on. */
    dismiss(row) {
      return this._put(row, { status: 'dismissed', answer: '' });
    },
    remove(key) {
      write('repertoire', this.all().filter((e) => e.key !== key));
    },
    _put(row, patch) {
      const entry = {
        key: leakKey(row),
        position: positionKey(row.fen),
        fen: row.fen,
        color: row.player_color,
        eco: row.eco || '',
        opening: row.opening || '',
        line: lineBefore(row),
        played: row.your_move || '',
        moveNumber: Number(row.move_number) || 0,
        games: Number(row.your_games) || 0,
        cost: Number(row.cost) || 0,
        flag: row.flag || '',
        decidedAt: Date.now(),
        ...patch,
      };
      const rest = this.all().filter((e) => e.key !== entry.key);
      rest.push(entry);
      write('repertoire', rest);
      return entry;
    },
    committed() {
      return this.all().filter((e) => e.status === 'committed');
    },
  };

  /* ------------------------------------------------------------------ runs */
  const runs = {
    all() {
      return read('runs', []);
    },
    /** One line per completed run: enough to plot progress, not the whole report. */
    record(entry) {
      const kept = this.all().filter((r) => r.id !== entry.id);
      kept.push(entry);
      kept.sort((a, b) => a.at - b.at);
      write('runs', kept.slice(-40));
      return entry;
    },
    latest() {
      const all = this.all();
      return all.length ? all[all.length - 1] : null;
    },
    clear() {
      write('runs', []);
    },
  };

  /* ---------------------------------------------------------------- drills */
  const SPACING_DAYS = [1, 3, 7, 16, 35];
  const drills = {
    all() {
      return read('drills', {});
    },
    stats(key) {
      return this.all()[key] || null;
    },
    /** Log one attempt and schedule the next review. */
    attempt(key, correct, label) {
      const all = this.all();
      const cur = all[key] || { key, right: 0, wrong: 0, streak: 0, label: label || '', due: 0 };
      if (correct) {
        cur.right += 1;
        cur.streak += 1;
      } else {
        cur.wrong += 1;
        cur.streak = 0;
      }
      if (label) cur.label = label;
      cur.last = Date.now();
      const step = SPACING_DAYS[Math.min(cur.streak, SPACING_DAYS.length - 1)];
      cur.due = cur.last + (correct ? step : 0.5) * 86400000;
      all[key] = cur;
      write('drills', all);
      return cur;
    },
    due(now = Date.now()) {
      return Object.values(this.all()).filter((d) => d.due <= now);
    },
  };

  /* --------------------------------------------------------- the last report */
  const lastReport = {
    load() {
      return read('report', null);
    },
    save(payload) {
      // rows carry the whole report; trim to what the views read back
      return write('report', payload);
    },
    clear() {
      write('report', null);
    },
  };

  const prefs = {
    get(key, fallback) {
      return read(`pref:${key}`, fallback);
    },
    set(key, value) {
      write(`pref:${key}`, value);
    },
  };

  window.Store = {
    repertoire,
    runs,
    drills,
    lastReport,
    prefs,
    positionKey,
    leakKey,
    lineBefore,
    persistent: () => store() !== false,
  };
})();
