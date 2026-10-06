'use strict';
// Building a whole new Store from a reset fixture or an export, and exporting
// one. Both builders validate everything before the caller swaps the result
// in, so a rejected reset/import changes nothing. Exports from the stage-1 and
// stage-2 services are accepted: their reservations start at revision 1 under
// policy 0 with a `created` history entry, exactly like seeded bookings.

const { invalid } = require('./errors');
const { isObject, isPositiveInt, isNonNegativeInt } = require('./fields');
const { parseRestaurant, findTable, declaredPair, isId } = require('./catalog');
const { parsePolicy, parseTerms, policyZero, termsOf } = require('./policy');
const { hashPassword } = require('./secrets');
const { changesBetween, withEntry } = require('./history');
const { Store } = require('./store');
const T = require('./time');

const TRACK = 'tablekeeper';
const FORMAT_VERSION = 1;
const STATUSES = ['confirmed', 'cancelled'];
const REFERENCE = /^[A-Z0-9]{6,12}$/;
const EMAIL = /^[^\s@]+@[^\s@]+$/;

function need(condition, message) {
  if (!condition) throw invalid(message);
}

const listOf = (v, name) => {
  if (v === undefined) return [];
  need(Array.isArray(v), `${name} must be an array`);
  return v;
};

function addRestaurants(store, list) {
  list.forEach((raw, i) => {
    const r = parseRestaurant(raw, i);
    need(!store.restaurants.has(r.id), `duplicate restaurant id ${r.id}`);
    need(r.manager_user_ids.every((id) => store.users.has(id)), `restaurants[${i}].manager_user_ids names an unknown user`);
    store.restaurants.set(r.id, r);
  });
}

function checkUserShape(u, where) {
  need(isObject(u), `${where} must be an object`);
  need(isId(u.id), `${where}.id must be 1..64 characters`);
  need(typeof u.email === 'string' && EMAIL.test(u.email), `${where}.email must look like local@domain`);
  need(typeof u.display_name === 'string', `${where}.display_name must be a string`);
}

function checkUniqueUser(store, u) {
  need(!store.users.has(u.id), `duplicate user id ${u.id}`);
  need(!store.emails.has(u.email.toLowerCase()), `duplicate email ${u.email}`);
}

// A stored reservation's tables: `table_ids`, or stage-1's single `table_id`.
// Returns them as a set in canonical order (pairs in `combinable` order).
function placeTables(restaurant, r, where) {
  need(!('table_id' in r && 'table_ids' in r), `${where} must not hold both table_id and table_ids`);
  const ids = 'table_ids' in r ? r.table_ids : [r.table_id];
  need(Array.isArray(ids) && ids.every((id) => typeof id === 'string'), `${where}.table_ids must be table ids`);
  need(ids.length >= 1 && ids.every((id) => findTable(restaurant, id)), `${where} names an unknown table`);
  if (ids.length === 1) return ids;
  const pair = ids.length === 2 ? declaredPair(restaurant, ids) : null;
  need(pair, `${where}.table_ids is not a declared pair`);
  return [...pair];
}

// Validates a reservation's links and timing against the store.
function placeReservation(store, r, where) {
  need(store.users.has(r.user_id), `${where}.user_id is unknown`);
  const restaurant = store.restaurants.get(r.restaurant_id);
  need(restaurant, `${where}.restaurant_id is unknown`);
  const tableIds = placeTables(restaurant, r, where);
  need(isPositiveInt(r.party_size), `${where}.party_size must be a positive integer`);
  const parsed = T.parseLocalMinute(r.starts_at_local);
  need(parsed, `${where}.starts_at_local must be YYYY-MM-DDTHH:MM`);
  const start = T.resolveLocal(restaurant.timezone, parsed.dayNaive + parsed.minute * T.MINUTE);
  need(start !== null, `${where}.starts_at_local does not exist`);
  need(r.reference === undefined || (typeof r.reference === 'string' && REFERENCE.test(r.reference)),
    `${where}.reference must be 6..12 of A-Z0-9`);
  need(r.reference === undefined || !store.references.has(r.reference), `${where}.reference is duplicated`);
  need(r.id === undefined || isId(r.id), `${where}.id must be 1..64 characters`);
  need(r.id === undefined || !store.reservations.has(r.id), `${where}.id is duplicated`);
  need(r.status === undefined || STATUSES.includes(r.status), `${where}.status is invalid`);
  need(r.created_at === undefined || typeof r.created_at === 'string', `${where}.created_at must be a string`);
  return { restaurant, start, tableIds };
}

// Capacity under the booking's terms, and no overlap between confirmed bookings.
function checkConsistency(store) {
  const confirmed = [...store.reservations.values()].filter((r) => r.status === 'confirmed');
  const end = (r) => r.start_ms + r.terms.reservation_duration_minutes * T.MINUTE;
  for (const r of store.reservations.values()) {
    const seats = r.table_ids.reduce((sum, id) => sum + r.terms.capacities[id], 0);
    need(r.party_size <= seats, `reservation ${r.id} exceeds its tables' capacity`);
  }
  confirmed.forEach((a, i) => {
    for (const b of confirmed.slice(i + 1)) {
      need(!(a.restaurant_id === b.restaurant_id && a.table_ids.some((id) => b.table_ids.includes(id)) &&
        a.start_ms < end(b) && b.start_ms < end(a)), `reservations ${a.id} and ${b.id} overlap on one table`);
    }
  });
}

// A booking as first seeded (or imported from stage 1/2): revision 1, policy 0.
function seededRecord(store, r, placed, createdAt) {
  const rec = {
    id: r.id === undefined ? store.nextId('res_', store.reservations) : r.id,
    reference: r.reference === undefined ? store.nextReference() : r.reference,
    user_id: r.user_id,
    restaurant_id: r.restaurant_id,
    table_ids: placed.tableIds,
    party_size: r.party_size,
    status: r.status || 'confirmed',
    starts_at_local: r.starts_at_local,
    start_ms: placed.start,
    created_at: createdAt,
    revision: 1,
    terms: termsOf(policyZero(placed.restaurant)),
    history: [],
    series_id: null,
  };
  return withEntry(rec, 'created', changesBetween(null, rec), createdAt);
}

// POST /_test/reset body -> new Store (422 on an invalid fixture).
async function storeFromFixture(fixture) {
  const store = new Store();
  const users = listOf(fixture.users, 'users');
  users.forEach((u, i) => {
    checkUserShape(u, `users[${i}]`);
    need(typeof u.password === 'string', `users[${i}].password must be a string`);
    checkUniqueUser(store, u);
    store.addUser({ id: u.id, email: u.email, display_name: u.display_name, password_hash: null });
  });
  addRestaurants(store, listOf(fixture.restaurants, 'restaurants'));
  const now = T.formatUtc(Date.now());
  listOf(fixture.reservations, 'reservations').forEach((r, i) => {
    need(isObject(r), `reservations[${i}] must be an object`);
    const placed = placeReservation(store, r, `reservations[${i}]`);
    store.addReservation(seededRecord(store, r, placed, r.created_at || now));
  });
  checkConsistency(store);
  const hashes = await Promise.all(users.map((u) => hashPassword(u.password)));
  users.forEach((u, i) => { store.users.get(u.id).password_hash = hashes[i]; });
  return store;
}

function exportStore(store) {
  return {
    track: TRACK,
    format_version: FORMAT_VERSION,
    state: {
      seq: store.seq,
      users: [...store.users.values()],
      tokens: [...store.tokens.entries()].map(([digest, userId]) => ({ digest, user_id: userId })),
      restaurants: [...store.restaurants.values()].map((r) => ({
        ...r,
        policies: store.policiesOf(r.id),
        revision: store.revisions.get(r.id) || 0,
      })),
      reservations: [...store.reservations.values()],
      series: [...store.series.values()],
      receipts: [...store.receipts.entries()].map(([scope, r]) => ({ scope, ...r })),
    },
  };
}

function importRestaurantExtras(store, raw, i) {
  const where = `state.restaurants[${i}]`;
  const restaurant = store.restaurants.get(raw.id);
  listOf(raw.policies, `${where}.policies`).forEach((p, j) => {
    need(isObject(p) && p.policy_version === j + 1, `${where}.policies[${j}] is out of order`);
    store.policiesOf(restaurant.id).push({ ...parsePolicy(p, restaurant), policy_version: j + 1 });
  });
  need(raw.revision === undefined || isNonNegativeInt(raw.revision), `${where}.revision is invalid`);
  store.revisions.set(restaurant.id, raw.revision || 0);
}

// An exported reservation; stage-1/2 records (no revision) are upgraded.
function importReservation(store, r, where) {
  need(isObject(r) && isId(r.id) && typeof r.reference === 'string', `${where} needs id and reference`);
  need(STATUSES.includes(r.status) && typeof r.created_at === 'string', `${where} needs status and created_at`);
  const placed = placeReservation(store, r, where);
  need(r.start_ms === placed.start, `${where}.start_ms does not match starts_at_local`);
  if (r.revision === undefined) return seededRecord(store, r, placed, r.created_at);
  need(isPositiveInt(r.revision), `${where}.revision is invalid`);
  need(Array.isArray(r.history) && r.history.every(isObject), `${where}.history is invalid`);
  need(r.series_id === null || typeof r.series_id === 'string', `${where}.series_id is invalid`);
  return {
    id: r.id, reference: r.reference, user_id: r.user_id, restaurant_id: r.restaurant_id,
    table_ids: placed.tableIds, party_size: r.party_size, status: r.status,
    starts_at_local: r.starts_at_local, start_ms: r.start_ms, created_at: r.created_at,
    revision: r.revision, terms: parseTerms(r.terms, placed.restaurant), history: r.history, series_id: r.series_id,
  };
}

function importSeries(store, s, where) {
  need(isObject(s) && isId(s.id) && !store.series.has(s.id) && store.users.has(s.user_id), `${where} is invalid`);
  need(isPositiveInt(s.interval_weeks) && isPositiveInt(s.revision) && Array.isArray(s.occurrences), `${where} is invalid`);
  const occurrences = s.occurrences.map((o, i) => {
    const rec = isObject(o) && store.reservations.get(o.reservation_id);
    need(rec && rec.series_id === s.id && o.index === i && typeof o.exception === 'boolean', `${where}.occurrences[${i}] is invalid`);
    return { index: i, reservation_id: o.reservation_id, exception: o.exception };
  });
  store.series.set(s.id, { id: s.id, user_id: s.user_id, interval_weeks: s.interval_weeks, revision: s.revision, occurrences });
}

// POST /_test/import body -> new Store (422 on anything this service did not export).
function storeFromExport(doc) {
  need(doc.track === TRACK, 'track must be "tablekeeper"');
  need(doc.format_version === FORMAT_VERSION, 'unsupported format_version');
  const s = doc.state;
  need(isObject(s), 'state must be an object');
  const store = new Store();
  need(isNonNegativeInt(s.seq), 'state.seq must be a non-negative integer');
  store.seq = s.seq;
  listOf(s.users, 'state.users').forEach((u, i) => {
    checkUserShape(u, `state.users[${i}]`);
    need(typeof u.password_hash === 'string', `state.users[${i}].password_hash must be a string`);
    checkUniqueUser(store, u);
    store.addUser({ id: u.id, email: u.email, display_name: u.display_name, password_hash: u.password_hash });
  });
  listOf(s.tokens, 'state.tokens').forEach((t, i) => {
    need(isObject(t) && typeof t.digest === 'string' && store.users.has(t.user_id), `state.tokens[${i}] is invalid`);
    store.tokens.set(t.digest, t.user_id);
  });
  const restaurants = listOf(s.restaurants, 'state.restaurants');
  addRestaurants(store, restaurants);
  restaurants.forEach((raw, i) => importRestaurantExtras(store, raw, i));
  listOf(s.reservations, 'state.reservations').forEach((r, i) => {
    store.addReservation(importReservation(store, r, `state.reservations[${i}]`));
  });
  checkConsistency(store);
  listOf(s.series, 'state.series').forEach((x, i) => importSeries(store, x, `state.series[${i}]`));
  for (const r of store.reservations.values()) {
    need(r.series_id === null || store.series.has(r.series_id), `reservation ${r.id} names an unknown series`);
  }
  listOf(s.receipts, 'state.receipts').forEach((r, i) => {
    need(isObject(r) && typeof r.scope === 'string' && typeof r.body === 'string', `state.receipts[${i}] is invalid`);
    need(isPositiveInt(r.status) && isObject(r.response), `state.receipts[${i}] is invalid`);
    need(!store.receipts.has(r.scope), `state.receipts[${i}] is duplicated`);
    store.receipts.set(r.scope, { body: r.body, status: r.status, response: r.response });
  });
  return store;
}

module.exports = { storeFromFixture, storeFromExport, exportStore };
