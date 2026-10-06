'use strict';
// How ordinary writes touch recurring series: a real change marks the
// occurrence as a permanent exception, and a change or cancellation raises
// the series revision once per operation.

function seriesOf(store, rec) {
  return rec.series_id ? store.series.get(rec.series_id) || null : null;
}

// After one operation changed `recs`: exceptions marked, each series +1 once.
function noteChanged(store, recs) {
  const touched = new Set();
  for (const rec of recs) {
    const s = seriesOf(store, rec);
    if (!s) continue;
    s.occurrences.find((o) => o.reservation_id === rec.id).exception = true;
    touched.add(s);
  }
  for (const s of touched) s.revision += 1;
}

function noteCancelled(store, rec) {
  const s = seriesOf(store, rec);
  if (s) s.revision += 1;
}

module.exports = { noteChanged, noteCancelled };
