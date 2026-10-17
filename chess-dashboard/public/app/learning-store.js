/* Immutable per-attempt records use the existing account preference transport.
   Lessons, independent recall and practical play remain separate evidence. */
(function () {
  'use strict';
  const S = window.Store;
  const root = 'learning:v2:italian-v1:';
  const day = 86400000;
  const spacing = [1, 3, 7, 14, 30];
  let persisted = true;
  const records = () => Object.fromEntries(Object.entries(S.prefs.all()).filter(([k, v]) => k.startsWith(root) && v));
  function put(key, value) {
    persisted = S.prefs.set(root + key, value) && persisted;
    window.dispatchEvent(new CustomEvent('learning:change'));
    return value;
  }
  const get = (key, fallback = null) => S.prefs.get(root + key, fallback);
  function schedule(cardId, data = records()) {
    const enrol = data[root + 'enrol:' + cardId];
    if (!enrol) return null;
    const events = Object.entries(data).filter(([k, e]) => k.startsWith(root + 'attempt:') && e.card === cardId).map(([, e]) => e).sort((a, b) => a.at - b.at || a.id.localeCompare(b.id));
    let due = enrol.at + day; let streak = 0;
    for (const event of events) {
      if (event.outcome === 'independent') {
        // Early practice builds history without artificially extending a review.
        if (event.at >= due) { due = event.at + spacing[Math.min(streak, spacing.length - 1)] * day; streak += 1; }
      } else {
        streak = 0;
        due = event.at + (event.outcome === 'hinted' ? 4 * 3600000 : 10 * 60000);
      }
    }
    return { card: cardId, due, streak, events };
  }
  window.LearningStore = {
    records, schedule,
    uid: () => window.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2)}`,
    session() {
      const pointer = get('session');
      const current = pointer?.id && get('checkpoint:' + pointer.id);
      return (current && !current.finished ? current : null) || this.checkpoints().filter((v) => !v.finished)[0] || null;
    },
    checkpoints: () => Object.entries(records()).filter(([k]) => k.startsWith(root + 'checkpoint:')).map(([, v]) => v).sort((a, b) => b.updated - a.updated),
    saved(mode, chapter) { return this.checkpoints().find((v) => v.mode === mode && v.chapter === chapter && !v.finished) || null; },
    saveSession(session) {
      if (!session) return put('session', null);
      const value = { ...session, updated: Date.now() };
      put(`checkpoint:${session.id}`, value);
      put('session', { id: session.id });
      return value;
    },
    completed: (chapter) => !!get('chapter:' + chapter),
    complete(chapter) { if (!this.completed(chapter)) put('chapter:' + chapter, { at: Date.now() }); },
    enrol(card) { if (!get('enrol:' + card)) put('enrol:' + card, { at: Date.now() }); },
    attempt(id, card, outcome, played) {
      if (!get('attempt:' + id)) put('attempt:' + id, { id, card, outcome, played, at: Date.now() });
    },
    practical(id, moves) { if (!get('practical:' + id)) put('practical:' + id, { id, moves, at: Date.now() }); },
    summary(cards, now = Date.now()) {
      const data = records();
      const schedules = cards.map((card) => schedule(card.id, data)).filter(Boolean);
      const attempts = schedules.flatMap((s) => s.events).filter((e) => e.at >= now - 30 * day);
      return { schedules, due: schedules.filter((s) => s.due <= now).sort((a, b) => a.due - b.due), attempts,
        independent: attempts.filter((e) => e.outcome === 'independent').length,
        practical: Object.keys(data).filter((k) => k.startsWith(root + 'practical:')).length };
    },
    durable: () => persisted && S.persistent(),
  };
}());
