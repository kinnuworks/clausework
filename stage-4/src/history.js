'use strict';
// Reservation history (stage 3): which fields a write changed, and the
// entries appended to a reservation's own record.

const sameSet = (a, b) => a.length === b.length && a.every((id, i) => id === b[i]);

// Table change: `table_id` between single tables, `table_ids` (full lists)
// whenever a pair is involved. `before` is null at creation.
function tableChange(before, after) {
  const single = after.length === 1 && (before === null || before.length === 1);
  if (single) return { field: 'table_id', from: before === null ? null : before[0], to: after[0] };
  return { field: 'table_ids', from: before === null ? null : [...before], to: [...after] };
}

// Changes from `before` (null for a creation) to `after`, in the order
// table, starts_at_local, party_size. Empty means nothing changed.
function changesBetween(before, after) {
  const changes = [];
  if (before === null || !sameSet(before.table_ids, after.table_ids)) {
    changes.push(tableChange(before && before.table_ids, after.table_ids));
  }
  for (const field of ['starts_at_local', 'party_size']) {
    if (before === null || before[field] !== after[field]) {
      changes.push({ field, from: before === null ? null : before[field], to: after[field] });
    }
  }
  return changes;
}

// `rec` with one more history entry describing its current revision and terms;
// `extra` adds event-specific fields (a reassignment's plan_id).
function withEntry(rec, event, changes, at, extra = {}) {
  const entry = {
    seq: rec.history.length + 1,
    at,
    event,
    changes,
    revision: rec.revision,
    accepted_terms: JSON.parse(JSON.stringify(rec.terms)),
    ...extra,
  };
  return { ...rec, history: [...rec.history, entry] };
}

module.exports = { changesBetween, withEntry };
