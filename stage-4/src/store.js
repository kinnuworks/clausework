'use strict';
// The whole service state lives in one Store object. Reset and import build a
// complete new Store off to the side and then swap it in with one assignment,
// so a failed reset/import never leaves a half-replaced state behind
// (see persist.js).

const { newToken, tokenDigest, newReference } = require('./secrets');
const { selectPolicy } = require('./policy');

class Store {
  constructor() {
    this.users = new Map();        // id -> { id, email, display_name, password_hash }
    this.emails = new Map();       // lower-cased email -> user id
    this.tokens = new Map();       // token digest -> user id
    this.restaurants = new Map();  // id -> normalized restaurant, fixture order
    this.reservations = new Map(); // id -> reservation record
    this.references = new Map();   // reference -> reservation id
    this.receipts = new Map();     // idempotency scope -> { body, status, response }
    this.policies = new Map();     // restaurant id -> published policies, publication order
    this.revisions = new Map();    // restaurant id -> restaurant revision counter
    this.series = new Map();       // series id -> { id, user_id, interval_weeks, revision, occurrences }
    this.plans = new Map();        // plan id -> stored seating plan (preview), applied or not
    this.closures = new Map();     // restaurant id -> applied closures { table_id, from_ms, to_ms, plan_id }
    this.seq = 0;
  }

  policiesOf(restaurantId) {
    if (!this.policies.has(restaurantId)) this.policies.set(restaurantId, []);
    return this.policies.get(restaurantId);
  }

  // The policy that governs bookings starting on local date "YYYY-MM-DD".
  policyFor(restaurant, date) {
    return selectPolicy(restaurant, this.policiesOf(restaurant.id), date);
  }

  closuresOf(restaurantId) {
    return this.closures.get(restaurantId) || [];
  }

  revisionOf(restaurantId) {
    return this.revisions.get(restaurantId) || 0;
  }

  bumpRevision(restaurantId) {
    this.revisions.set(restaurantId, (this.revisions.get(restaurantId) || 0) + 1);
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

module.exports = { Store, getStore, replaceStore };
