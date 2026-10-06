'use strict';
// The whole service state lives in one Store object. Reset and import build a
// complete new Store off to the side and then swap it in with one assignment,
// so a failed reset/import never leaves a half-replaced state behind.

const { invalid } = require('./errors');
const { isObject, isPositiveInt, isNonNegativeInt } = require('./fields');
const { parseRestaurant, findTable, isId } = require('./catalog');
const { hashPassword, newToken, tokenDigest, newReference } = require('./secrets');
const T = require('./time');

const TRACK = 'tablekeeper';
const FORMAT_VERSION = 1;
const STATUSES = ['confirmed', 'cancelled'];

class Store {
  constructor() {
    this.users = new Map();        // id -> { id, email, display_name, password_hash }
    this.emails = new Map();       // lower-cased email -> user id
    this.tokens = new Map();       // token digest -> user id
    this.restaurants = new Map();  // id -> normalized restaurant, fixture order
    this.reservations = new Map(); // id -> reservation record
    this.references = new Map();   // reference -> reservation id
    this.receipts = new Map();     // idempotency scope -> { body, status, response }
    this.seq = 0;
  }

  nextId(prefix, taken) {
    let id;
    do id = `${prefix}${++this.seq}`; while (taken.has(id));
    return id;
  }

  nextReference() {
    let ref;
    do ref = newReference(); while (this.references.has(ref));
    return ref;
  }

  addUser(user) {
    this.users.set(user.id, user);
    this.emails.set(user.email.toLowerCase(), user.id);
  }

  issueToken(userId) {
    const token = newToken();
    this.tokens.set(tokenDigest(token), userId);
    return token;
  }

  userForToken(token) {
    return this.users.get(this.tokens.get(tokenDigest(token))) || null;
  }

  addReservation(rec) {
    this.reservations.set(rec.id, rec);
    this.references.set(rec.reference, rec.id);
  }

  reservationByReference(reference) {
    return this.reservations.get(this.references.get(reference)) || null;
  }
}

let current = new Store();

const getStore = () => current;
const replaceStore = (next) => { current = next; };

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
    store.restaurants.set(r.id, r);
  });
}

function checkUserShape(u, where) {
  need(isObject(u), `${where} must be an object`);
  need(isId(u.id), `${where}.id must be 1..64 characters`);
  need(typeof u.email === 'string' && u.email.length > 0, `${where}.email must be a string`);
  need(typeof u.display_name === 'string', `${where}.display_name must be a string`);
}

function checkUniqueUser(store, u) {
  need(!store.users.has(u.id), `duplicate user id ${u.id}`);
  need(!store.emails.has(u.email.toLowerCase()), `duplicate email ${u.email}`);
}

// Validates a reservation's links and timing against the store; returns its start instant.
function placeReservation(store, r, where) {
  need(store.users.has(r.user_id), `${where}.user_id is unknown`);
  const restaurant = store.restaurants.get(r.restaurant_id);
  need(restaurant, `${where}.restaurant_id is unknown`);
  need(typeof r.table_id === 'string' && findTable(restaurant, r.table_id), `${where}.table_id is unknown`);
  need(isPositiveInt(r.party_size), `${where}.party_size must be a positive integer`);
  const parsed = T.parseLocalMinute(r.starts_at_local);
  need(parsed, `${where}.starts_at_local must be YYYY-MM-DDTHH:MM`);
  const start = T.resolveLocal(restaurant.timezone, parsed.dayNaive + parsed.minute * T.MINUTE);
  need(start !== null, `${where}.starts_at_local does not exist`);
  need(r.reference === undefined || (isId(r.reference)), `${where}.reference must be 1..64 characters`);
  need(r.reference === undefined || !store.references.has(r.reference), `${where}.reference is duplicated`);
  need(r.id === undefined || isId(r.id), `${where}.id must be 1..64 characters`);
  need(r.id === undefined || !store.reservations.has(r.id), `${where}.id is duplicated`);
  need(r.status === undefined || STATUSES.includes(r.status), `${where}.status is invalid`);
  need(r.created_at === undefined || typeof r.created_at === 'string', `${where}.created_at must be a string`);
  return start;
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
    const start = placeReservation(store, r, `reservations[${i}]`);
    store.addReservation({
      id: r.id === undefined ? store.nextId('res_', store.reservations) : r.id,
      reference: r.reference === undefined ? store.nextReference() : r.reference,
      user_id: r.user_id,
      restaurant_id: r.restaurant_id,
      table_id: r.table_id,
      party_size: r.party_size,
      status: r.status || 'confirmed',
      starts_at_local: r.starts_at_local,
      start_ms: start,
      created_at: r.created_at || now,
    });
  });
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
      restaurants: [...store.restaurants.values()],
      reservations: [...store.reservations.values()],
      receipts: [...store.receipts.entries()].map(([scope, r]) => ({ scope, ...r })),
    },
  };
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
  addRestaurants(store, listOf(s.restaurants, 'state.restaurants'));
  listOf(s.reservations, 'state.reservations').forEach((r, i) => {
    const where = `state.reservations[${i}]`;
    need(isObject(r) && isId(r.id) && isId(r.reference), `${where} needs id and reference`);
    need(STATUSES.includes(r.status) && typeof r.created_at === 'string', `${where} needs status and created_at`);
    const start = placeReservation(store, r, where);
    need(r.start_ms === start, `${where}.start_ms does not match starts_at_local`);
    store.addReservation({
      id: r.id, reference: r.reference, user_id: r.user_id, restaurant_id: r.restaurant_id,
      table_id: r.table_id, party_size: r.party_size, status: r.status,
      starts_at_local: r.starts_at_local, start_ms: r.start_ms, created_at: r.created_at,
    });
  });
  listOf(s.receipts, 'state.receipts').forEach((r, i) => {
    need(isObject(r) && typeof r.scope === 'string' && typeof r.body === 'string', `state.receipts[${i}] is invalid`);
    need(isPositiveInt(r.status) && isObject(r.response), `state.receipts[${i}] is invalid`);
    need(!store.receipts.has(r.scope), `state.receipts[${i}] is duplicated`);
    store.receipts.set(r.scope, { body: r.body, status: r.status, response: r.response });
  });
  return store;
}

module.exports = { Store, getStore, replaceStore, storeFromFixture, storeFromExport, exportStore };
