'use strict';
// Reservation endpoints (§8). Every handler here is synchronous: it validates
// against the current state and, only when everything passes, commits. Node
// runs one such handler at a time, so the check-then-write sequence can never
// interleave with another write — that is what keeps occupancy overlap-free.

const { malformed, invalid, notFound } = require('./errors');
const { isObject, checkId, checkPartySize } = require('./fields');
const { findTable } = require('./catalog');
const B = require('./booking');

const FIELDS = ['restaurant_id', 'table_id', 'starts_at_local'];

// Wrong JSON types for the string fields are 400; party_size is always 422.
function checkTypes(body, names) {
  for (const name of names) {
    if (name in body && typeof body[name] !== 'string') throw malformed(`${name} must be a string`);
  }
}

function checkStartFormat(value) {
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(value)) throw invalid('starts_at_local must be a local YYYY-MM-DDTHH:MM');
}

function create(store, user, body, now) {
  checkTypes(body, FIELDS);
  for (const name of [...FIELDS, 'party_size']) {
    if (!(name in body)) throw invalid(`${name} is required`);
  }
  checkId(body.restaurant_id, 'restaurant_id');
  checkId(body.table_id, 'table_id');
  checkStartFormat(body.starts_at_local);
  checkPartySize(body.party_size);
  const restaurant = store.restaurants.get(body.restaurant_id);
  if (!restaurant) throw notFound('unknown restaurant');
  const table = findTable(restaurant, body.table_id);
  if (!table) throw notFound('unknown table');
  const start = B.resolveStart(restaurant, body.starts_at_local);
  B.checkCapacity(table, body.party_size);
  const rec = {
    id: store.nextId('res_', store.reservations),
    reference: store.nextReference(),
    user_id: user.id,
    restaurant_id: restaurant.id,
    table_id: table.id,
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
  checkTypes(body, ['table_id', 'starts_at_local']);
  return { table_id: body.table_id, starts_at_local: body.starts_at_local, party_size: body.party_size };
}

// The amended record for `rec`, validated but not committed. Order: cancelled,
// cutoff, field values, table, time rules, capacity. Occupancy is the caller's.
function planAmendment(store, rec, change, nowMs) {
  const restaurant = store.restaurants.get(rec.restaurant_id);
  B.checkNotCancelled(rec);
  B.checkCutoff(restaurant, rec, nowMs);
  if (change.table_id !== undefined) checkId(change.table_id, 'table_id');
  if (change.starts_at_local !== undefined) checkStartFormat(change.starts_at_local);
  if (change.party_size !== undefined) checkPartySize(change.party_size);
  const tableId = change.table_id === undefined ? rec.table_id : change.table_id;
  const table = findTable(restaurant, tableId);
  if (!table) throw notFound('unknown table');
  const next = { ...rec, table_id: tableId };
  if (change.starts_at_local !== undefined) {
    next.start_ms = B.resolveStart(restaurant, change.starts_at_local);
    next.starts_at_local = change.starts_at_local;
  }
  if (change.party_size !== undefined) next.party_size = change.party_size;
  if (change.table_id !== undefined || change.party_size !== undefined) B.checkCapacity(table, next.party_size);
  return next;
}

function moved(before, after) {
  return before.table_id !== after.table_id || before.start_ms !== after.start_ms;
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
  const current = moves.map((m) => ownReservation(store, user, m.reference));
  const restaurantId = current[0].restaurant_id;
  if (current.some((r) => r.restaurant_id !== restaurantId)) throw invalid('all bookings must be at one restaurant');
  const planned = moves.map((m, i) => planAmendment(store, current[i], readAmendment(m), now.ms));
  B.checkOccupancy(store, store.restaurants.get(restaurantId), planned);
  planned.forEach((next) => store.addReservation(next));
  return { status: 201, body: { reservations: planned.map((r) => B.view(store, r)) } };
}

module.exports = { create, list, show, cancel, amend, moveBatch };
