'use strict';
// Booking rules shared by create, amend, batch moves and series: resolving a
// local start under a policy, capacity, cutoff, occupancy and the public view.
// A booking keeps the terms it accepted; its end comes from those terms.

const { ApiError, invalid, notFound } = require('./errors');
const { findTable, declaredPair, windowsFor } = require('./catalog');
const T = require('./time');

// starts_at_local -> start instant (ms) under `policy`, applying §8/§9 rules in order.
function resolveStart(restaurant, policy, startsAtLocal) {
  const parsed = T.parseLocalMinute(startsAtLocal);
  if (!parsed) throw invalid('starts_at_local must be a local YYYY-MM-DDTHH:MM');
  const tz = restaurant.timezone;
  const start = T.resolveLocal(tz, parsed.dayNaive + parsed.minute * T.MINUTE);
  if (start === null) throw new ApiError(422, 'invalid_local_time', 'that local time does not exist');
  const windows = windowsFor(policy, T.weekdayOf(parsed.dayNaive));
  const window = windows.find((w) => parsed.minute >= w.opens && parsed.minute < w.closes);
  if (!window) throw new ApiError(422, 'outside_opening_hours', 'the restaurant is not open then');
  if ((parsed.minute - window.opens) % policy.slot_minutes !== 0) {
    throw new ApiError(422, 'not_on_slot_grid', 'start is not on the slot grid');
  }
  const closes = T.resolveLocalLenient(tz, parsed.dayNaive + window.closes * T.MINUTE);
  if (start + durationMs(policy) > closes) {
    throw new ApiError(422, 'outside_opening_hours', 'the reservation would end after closing');
  }
  return start;
}

// Duration of a policy or of accepted terms.
function durationMs(terms) {
  return terms.reservation_duration_minutes * T.MINUTE;
}

function endOf(rec) {
  return rec.start_ms + durationMs(rec.terms);
}

// A set of 1..n distinct table ids -> its ids, pairs in `combinable` order.
// Unknown table: 404. More than two, or an undeclared pair: combination_not_allowed.
function resolveTables(restaurant, ids) {
  if (ids.some((id) => !findTable(restaurant, id))) throw notFound('unknown table');
  if (ids.length === 1) return [...ids];
  const pair = ids.length === 2 ? declaredPair(restaurant, ids) : null;
  if (!pair) throw new ApiError(422, 'combination_not_allowed', 'those tables cannot be combined');
  return [...pair];
}

// Seats of a table set under a policy's capacities.
function capacityOf(policy, tableIds) {
  return tableIds.reduce((sum, id) => sum + policy.capacities[id], 0);
}

function checkCapacity(policy, tableIds, partySize) {
  if (partySize > capacityOf(policy, tableIds)) {
    throw new ApiError(422, 'party_exceeds_capacity', 'party is larger than the tables seat');
  }
}

// The accepted cutoff, measured against the current start.
function checkCutoff(rec, now) {
  if (now >= rec.start_ms - rec.terms.cancellation_cutoff_minutes * T.MINUTE) {
    throw new ApiError(409, 'cutoff_passed', 'too close to the start to change this booking');
  }
}

function checkNotCancelled(rec) {
  if (rec.status !== 'confirmed') throw new ApiError(409, 'reservation_cancelled', 'the reservation is cancelled');
}

// Two bookings overlap when they share any table for overlapping intervals.
// Each side is { restaurant_id, table_ids, start_ms, end_ms }.
function overlaps(a, b) {
  return a.restaurant_id === b.restaurant_id && a.table_ids.some((id) => b.table_ids.includes(id)) &&
    a.start_ms < b.end_ms && b.start_ms < a.end_ms;
}

const span = (rec) => ({ restaurant_id: rec.restaurant_id, table_ids: rec.table_ids, start_ms: rec.start_ms, end_ms: endOf(rec) });

// Throws 409 table_unavailable unless every candidate is free of every other
// candidate and of every confirmed booking not being replaced.
function checkOccupancy(store, candidates) {
  const spans = candidates.map(span);
  const replaced = new Set(candidates.map((c) => c.id));
  const conflict = () => new ApiError(409, 'table_unavailable', 'the table is taken at that time');
  spans.forEach((c, i) => {
    for (let j = i + 1; j < spans.length; j++) if (overlaps(c, spans[j])) throw conflict();
  });
  for (const rec of store.reservations.values()) {
    if (rec.status !== 'confirmed' || replaced.has(rec.id)) continue;
    const other = span(rec);
    if (spans.some((c) => overlaps(c, other))) throw conflict();
  }
}

function areTablesFree(store, restaurantId, tableIds, startMs, endMs) {
  const probe = { restaurant_id: restaurantId, table_ids: tableIds, start_ms: startMs, end_ms: endMs };
  for (const rec of store.reservations.values()) {
    if (rec.status === 'confirmed' && overlaps(probe, span(rec))) return false;
  }
  return true;
}

function view(store, rec) {
  const tz = store.restaurants.get(rec.restaurant_id).timezone;
  return {
    reservation_id: rec.id,
    reference: rec.reference,
    restaurant_id: rec.restaurant_id,
    ...(rec.table_ids.length === 1 ? { table_id: rec.table_ids[0] } : {}),
    table_ids: [...rec.table_ids],
    party_size: rec.party_size,
    status: rec.status,
    starts_at_local: rec.starts_at_local,
    starts_at: T.formatInstant(tz, rec.start_ms),
    ends_at: T.formatInstant(tz, endOf(rec)),
    created_at: rec.created_at,
    revision: rec.revision,
    accepted_terms: JSON.parse(JSON.stringify(rec.terms)),
  };
}

module.exports = {
  resolveStart, resolveTables, capacityOf, checkCapacity, checkCutoff, checkNotCancelled, checkOccupancy,
  areTablesFree, durationMs, view,
};
