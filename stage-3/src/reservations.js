'use strict';
// Reservation endpoints (§8, stage 3). Every handler here is synchronous: it
// validates against the current state and, only when everything passes,
// commits the record, its history entry, its revision and every counter it
// touches. Node runs one such handler at a time, so no two writes interleave.

const { invalid, notFound } = require('./errors');
const { checkId, checkPartySize } = require('./fields');
const I = require('./input');
const B = require('./booking');
const H = require('./history');
const series = require('./series-links');
const { termsOf } = require('./policy');
const T = require('./time');

const dateOf = (startsAtLocal) => startsAtLocal.slice(0, 10);

function stamp(store, restaurantId, now) {
  return T.formatInstant(store.restaurants.get(restaurantId).timezone, now.ms);
}

// A new confirmed booking under the policy for its local start date, with its
// `created` history entry. Not committed; occupancy is the caller's.
function planBooking(store, user, restaurant, tableIds, startsAtLocal, partySize, now) {
  const policy = store.policyFor(restaurant, dateOf(startsAtLocal));
  const start = B.resolveStart(restaurant, policy, startsAtLocal);
  B.checkCapacity(policy, tableIds, partySize);
  const rec = {
    id: null,
    reference: null,
    user_id: user.id,
    restaurant_id: restaurant.id,
    table_ids: tableIds,
    party_size: partySize,
    status: 'confirmed',
    starts_at_local: startsAtLocal,
    start_ms: start,
    created_at: now.text,
    revision: 1,
    terms: termsOf(policy),
    history: [],
    series_id: null,
  };
  return H.withEntry(rec, 'created', H.changesBetween(null, rec), stamp(store, restaurant.id, now));
}

// Gives a planned booking its identity and stores it.
function commitNew(store, rec) {
  const stored = { ...rec, id: store.nextId('res_', store.reservations), reference: store.nextReference() };
  store.addReservation(stored);
  return stored;
}

function create(store, user, body, now) {
  I.checkTypes(body, ['restaurant_id', 'starts_at_local']);
  I.checkTableTypes(body);
  for (const name of ['restaurant_id', 'starts_at_local', 'party_size']) {
    if (!(name in body)) throw invalid(`${name} is required`);
  }
  if (!('table_id' in body) && !('table_ids' in body)) throw invalid('table_id or table_ids is required');
  checkId(body.restaurant_id, 'restaurant_id');
  const tableIds = I.readTableIds(body);
  I.checkStartFormat(body.starts_at_local);
  checkPartySize(body.party_size);
  const restaurant = store.restaurants.get(body.restaurant_id);
  if (!restaurant) throw notFound('unknown restaurant');
  const tables = B.resolveTables(restaurant, tableIds);
  const planned = planBooking(store, user, restaurant, tables, body.starts_at_local, body.party_size, now);
  B.checkOccupancy(store, [planned]);
  const rec = commitNew(store, planned);
  store.bumpRevision(restaurant.id);
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
  const rec = user && store.reservationByReference(reference);
  if (!rec || rec.user_id !== user.id) throw notFound('no such reservation');
  return rec;
}

function show(store, user, reference) {
  return { status: 200, body: B.view(store, ownReservation(store, user, reference)) };
}

function history(store, user, reference) {
  const rec = ownReservation(store, user, reference);
  return { status: 200, body: { reference: rec.reference, entries: JSON.parse(JSON.stringify(rec.history)) } };
}

function decision(store, user, reference) {
  const rec = ownReservation(store, user, reference);
  return { status: 200, body: { reference: rec.reference, revision: rec.revision, accepted_terms: termsOf(rec.terms) } };
}

function cancel(store, user, reference, now) {
  const rec = ownReservation(store, user, reference);
  if (rec.status === 'cancelled') return { status: 200, body: B.view(store, rec) };
  B.checkCutoff(rec, now.ms);
  const next = H.withEntry({ ...rec, status: 'cancelled', revision: rec.revision + 1 }, 'cancelled', [],
    stamp(store, rec.restaurant_id, now));
  store.addReservation(next);
  series.noteCancelled(store, next);
  store.bumpRevision(rec.restaurant_id);
  return { status: 200, body: B.view(store, next) };
}

// Type-checks an amendment's fields (400 on a wrong JSON type).
function readAmendment(body) {
  I.checkTypes(body, ['starts_at_local']);
  I.checkTableTypes(body);
  return body;
}

// -> { next, changed }. Order: stale revision, cancelled, accepted cutoff,
// field values, tables; a no-op stops there. A real change then validates
// every resulting field under the resulting date's policy and gains new
// terms, one revision and one `changed` entry. Occupancy is the caller's.
function planAmendment(store, rec, change, now) {
  const restaurant = store.restaurants.get(rec.restaurant_id);
  I.checkExpectedRevision(change, rec);
  B.checkNotCancelled(rec);
  B.checkCutoff(rec, now.ms);
  const tableIds = I.readTableIds(change);
  if (change.starts_at_local !== undefined) I.checkStartFormat(change.starts_at_local);
  if (change.party_size !== undefined) checkPartySize(change.party_size);
  const result = {
    ...rec,
    table_ids: B.resolveTables(restaurant, tableIds === undefined ? rec.table_ids : tableIds),
    starts_at_local: change.starts_at_local === undefined ? rec.starts_at_local : change.starts_at_local,
    party_size: change.party_size === undefined ? rec.party_size : change.party_size,
  };
  const changes = H.changesBetween(rec, result);
  if (changes.length === 0) return { next: rec, changed: false };
  const policy = store.policyFor(restaurant, dateOf(result.starts_at_local));
  result.start_ms = B.resolveStart(restaurant, policy, result.starts_at_local);
  B.checkCapacity(policy, result.table_ids, result.party_size);
  const next = { ...result, terms: termsOf(policy), revision: rec.revision + 1 };
  return { next: H.withEntry(next, 'changed', changes, stamp(store, rec.restaurant_id, now)), changed: true };
}

function amend(store, user, reference, body, now) {
  const change = readAmendment(body);
  const rec = ownReservation(store, user, reference);
  const { next, changed } = planAmendment(store, rec, change, now);
  if (changed) {
    B.checkOccupancy(store, [next]);
    store.addReservation(next);
    series.noteChanged(store, [next]);
    store.bumpRevision(rec.restaurant_id);
  }
  return { status: 200, body: B.view(store, next) };
}

module.exports = {
  create, list, show, history, decision, cancel, amend,
  ownReservation, readAmendment, planAmendment, planBooking, commitNew, dateOf,
};
