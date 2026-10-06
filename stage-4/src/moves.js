'use strict';
// POST /reservation-moves (§11, stage 3). Each item is resolved and planned
// completely, in input order, with PATCH semantics; occupancy is checked
// once for the whole result; only then is anything written. Either every
// move commits (with its revision, history and series effects) or nothing.

const { invalid } = require('./errors');
const { isObject } = require('./fields');
const B = require('./booking');
const R = require('./reservations');
const series = require('./series-links');

function checkShape(moves) {
  if (!Array.isArray(moves) || moves.length < 1 || moves.length > 8) throw invalid('moves must hold 1..8 items');
  if (!moves.every((m) => isObject(m) && typeof m.reference === 'string')) {
    throw invalid('each move needs a string reference');
  }
  if (new Set(moves.map((m) => m.reference)).size !== moves.length) throw invalid('references must be distinct');
}

function moveBatch(store, user, body, now) {
  checkShape(body.moves);
  let restaurantId = null;
  const planned = body.moves.map((m) => {
    const rec = R.ownReservation(store, user, m.reference);
    restaurantId = restaurantId || rec.restaurant_id;
    if (rec.restaurant_id !== restaurantId) throw invalid('all bookings must be at one restaurant');
    return R.planAmendment(store, rec, R.readAmendment(m), now);
  });
  B.checkOccupancy(store, planned.map((p) => p.next));
  const changed = planned.filter((p) => p.changed).map((p) => p.next);
  changed.forEach((next) => store.addReservation(next));
  if (changed.length > 0) {
    series.noteChanged(store, changed);
    store.bumpRevision(restaurantId);
  }
  return { status: 201, body: { reservations: planned.map((p) => B.view(store, p.next)) } };
}

module.exports = { moveBatch };
