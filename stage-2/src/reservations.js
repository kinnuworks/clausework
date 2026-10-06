'use strict';
// Reservation endpoints (§8). Every handler here is synchronous: it validates
// against the current state and, only when everything passes, commits. Node
// runs one such handler at a time, so the check-then-write sequence can never
// interleave with another write — that is what keeps occupancy overlap-free.

const { malformed, invalid, notFound } = require('./errors');
const { isObject, checkId, checkPartySize } = require('./fields');
const B = require('./booking');

// Wrong JSON types for the string fields are 400; party_size is always 422.
function checkTypes(body, names) {
  for (const name of names) {
    if (name in body && typeof body[name] !== 'string') throw malformed(`${name} must be a string`);
  }
}

function checkStartFormat(value) {
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(value)) throw invalid('starts_at_local must be a local YYYY-MM-DDTHH:MM');
}

// Type check of a table selection: table_id a string, table_ids an array of strings.
function checkTableTypes(body) {
  checkTypes(body, ['table_id']);
  if ('table_ids' in body && !(Array.isArray(body.table_ids) && body.table_ids.every((id) => typeof id === 'string'))) {
    throw malformed('table_ids must be an array of strings');
  }
}

// Value check of a table selection -> the ids as a list, or undefined when
// neither field was sent. Both fields, an empty set or a repeated id are 422.
function readTableIds(body) {
  const hasOne = 'table_id' in body;
  const hasMany = 'table_ids' in body;
  if (hasOne && hasMany) throw invalid('send table_id or table_ids, not both');
  if (!hasOne && !hasMany) return undefined;
  const ids = hasOne ? [body.table_id] : body.table_ids;
  if (ids.length === 0) throw invalid('table_ids must not be empty');
  if (new Set(ids).size !== ids.length) throw invalid('table_ids must not repeat a table');
  ids.forEach((id) => checkId(id, 'table_ids'));
  return ids;
}

function create(store, user, body, now) {
  checkTypes(body, ['restaurant_id', 'starts_at_local']);
  checkTableTypes(body);
  for (const name of ['restaurant_id', 'starts_at_local', 'party_size']) {
    if (!(name in body)) throw invalid(`${name} is required`);
  }
  if (!('table_id' in body) && !('table_ids' in body)) throw invalid('table_id or table_ids is required');
  checkId(body.restaurant_id, 'restaurant_id');
  const tableIds = readTableIds(body);
  checkStartFormat(body.starts_at_local);
  checkPartySize(body.party_size);
  const restaurant = store.restaurants.get(body.restaurant_id);
  if (!restaurant) throw notFound('unknown restaurant');
  const tables = B.resolveTables(restaurant, tableIds);
  const start = B.resolveStart(restaurant, body.starts_at_local);
  B.checkCapacity(tables, body.party_size);
  const rec = {
    id: store.nextId('res_', store.reservations),
    reference: store.nextReference(),
    user_id: user.id,
    restaurant_id: restaurant.id,
    table_ids: tables.map((t) => t.id),
    party_size: body.party_size,
    status: 'confirmed',
    starts_at_local: body.starts_at_local,
    start_ms: start,
    created_at: now.text,
  };
  B.checkOccupancy(store, restaurant, [rec]);
  store.addReservation(rec);
  return { status: 201, body: B.view(store, rec) };
}

function list(store, user) {
  const mine = [...store.reservations.values()]
    .filter((r) => r.user_id === user.id)
    .sort((a, b) => b.start_ms - a.start_ms);
  return { status: 200, body: { reservations: mine.map((r) => B.view(store, r)) } };
}

// The caller's reservation, or 404 whether it is missing or someone else's.
function ownReservation(store, user, reference) {
  const rec = store.reservationByReference(reference);
  if (!rec || rec.user_id !== user.id) throw notFound('no such reservation');
  return rec;
}

function show(store, user, reference) {
  return { status: 200, body: B.view(store, ownReservation(store, user, reference)) };
}

function cancel(store, user, reference, now) {
  const rec = ownReservation(store, user, reference);
  if (rec.status === 'cancelled') return { status: 200, body: B.view(store, rec) };
  B.checkCutoff(store.restaurants.get(rec.restaurant_id), rec, now.ms);
  const next = { ...rec, status: 'cancelled' };
  store.addReservation(next);
  return { status: 200, body: B.view(store, next) };
}

// Type-checks an amendment's fields (400 on a wrong JSON type).
function readAmendment(body) {
  checkTypes(body, ['starts_at_local']);
  checkTableTypes(body);
  return body;
}

// The amended record for `rec`, validated but not committed. Order: cancelled,
// cutoff, field values, tables, time rules, capacity. Occupancy is the caller's.
function planAmendment(store, rec, change, nowMs) {
  const restaurant = store.restaurants.get(rec.restaurant_id);
  B.checkNotCancelled(rec);
  B.checkCutoff(restaurant, rec, nowMs);
  const tableIds = readTableIds(change);
  if (change.starts_at_local !== undefined) checkStartFormat(change.starts_at_local);
  if (change.party_size !== undefined) checkPartySize(change.party_size);
  const tables = B.resolveTables(restaurant, tableIds === undefined ? rec.table_ids : tableIds);
  const next = { ...rec, table_ids: tables.map((t) => t.id) };
  if (change.starts_at_local !== undefined) {
    next.start_ms = B.resolveStart(restaurant, change.starts_at_local);
    next.starts_at_local = change.starts_at_local;
  }
  if (change.party_size !== undefined) next.party_size = change.party_size;
  if (tableIds !== undefined || change.party_size !== undefined) B.checkCapacity(tables, next.party_size);
  return next;
}

function moved(before, after) {
  return before.table_ids.join('\n') !== after.table_ids.join('\n') || before.start_ms !== after.start_ms;
}

function amend(store, user, reference, body, now) {
  const change = readAmendment(body);
  const rec = ownReservation(store, user, reference);
  const next = planAmendment(store, rec, change, now.ms);
  if (moved(rec, next)) B.checkOccupancy(store, store.restaurants.get(rec.restaurant_id), [next]);
  store.addReservation(next);
  return { status: 200, body: B.view(store, next) };
}

// POST /reservation-moves (§11): all items are planned and checked before
// any is written, so either every move commits or nothing changes.
function moveBatch(store, user, body, now) {
  const moves = body.moves;
  if (!Array.isArray(moves) || moves.length < 1 || moves.length > 8) throw invalid('moves must hold 1..8 items');
  if (!moves.every((m) => isObject(m) && typeof m.reference === 'string')) {
    throw invalid('each move needs a string reference');
  }
  if (new Set(moves.map((m) => m.reference)).size !== moves.length) throw invalid('references must be distinct');
  // Each item is resolved and planned completely before the next, so the
  // first failing item in input order decides the error.
  let restaurantId = null;
  const planned = moves.map((m) => {
    const rec = ownReservation(store, user, m.reference);
    restaurantId = restaurantId || rec.restaurant_id;
    if (rec.restaurant_id !== restaurantId) throw invalid('all bookings must be at one restaurant');
    return planAmendment(store, rec, readAmendment(m), now.ms);
  });
  B.checkOccupancy(store, store.restaurants.get(restaurantId), planned);
  planned.forEach((next) => store.addReservation(next));
  return { status: 201, body: { reservations: planned.map((r) => B.view(store, r)) } };
}

module.exports = { create, list, show, cancel, amend, moveBatch };
