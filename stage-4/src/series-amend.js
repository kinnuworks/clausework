'use strict';
// POST /series/{id}/amend (stage 4): moves the clock time of every eligible
// occurrence from `from_index` on. Each occurrence is planned like an
// individual PATCH, in index order (an occurrence already at that time is a
// no-op and is left alone, cutoff included); occupancy is checked for the whole
// result; then everything commits in one step, or nothing does.

const { ApiError, invalid, notFound } = require('./errors');
const B = require('./booking');
const R = require('./reservations');
const { parseClock } = require('./time');

function intAtLeast(value, lo, hi, name) {
  if (typeof value !== 'number' || !Number.isInteger(value) || value < lo || value > hi) {
    throw invalid(`${name} must be an integer ${lo}..${hi}`);
  }
  return value;
}

function readBody(body, s) {
  const expected = intAtLeast(body.expected_revision, 1, Number.MAX_SAFE_INTEGER, 'expected_revision');
  const fromIndex = intAtLeast(body.from_index, 0, s.occurrences.length - 1, 'from_index');
  if (typeof body.local_time !== 'string' || parseClock(body.local_time) === null) {
    throw invalid('local_time must be HH:MM between 00:00 and 23:59');
  }
  return { expected, fromIndex, localTime: body.local_time };
}

function amend(store, user, body, now, seriesId, view) {
  const s = store.series.get(seriesId);
  if (!s || s.user_id !== user.id) throw notFound('no such series');
  const { expected, fromIndex, localTime } = readBody(body, s);
  if (expected !== s.revision) throw new ApiError(409, 'stale_revision', 'the series has changed since that revision');
  const planned = s.occurrences
    .filter((o) => o.index >= fromIndex && !o.exception)
    .map((o) => store.reservations.get(o.reservation_id))
    .filter((rec) => rec.status === 'confirmed')
    .map((rec) => ({ rec, startsAtLocal: `${rec.starts_at_local.slice(0, 10)}T${localTime}` }))
    .filter(({ rec, startsAtLocal }) => startsAtLocal !== rec.starts_at_local)
    .map(({ rec, startsAtLocal }) => R.planAmendment(store, rec, { starts_at_local: startsAtLocal }, now));
  const changed = planned.filter((p) => p.changed).map((p) => p.next);
  if (changed.length > 0) {
    B.checkOccupancy(store, changed);
    changed.forEach((next) => store.addReservation(next));
    s.revision += 1;
    store.bumpRevision(changed[0].restaurant_id);
  }
  return { status: 201, body: view(store, s) };
}

module.exports = { amend };
