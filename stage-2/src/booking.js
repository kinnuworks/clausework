'use strict';
// Booking rules shared by create, amend and batch moves: resolving a local
// start against a restaurant, capacity, cutoff, occupancy and the public view.

const { ApiError, invalid } = require('./errors');
const { windowsFor } = require('./catalog');
const T = require('./time');

// starts_at_local -> start instant (ms), applying §8/§9 rules in order.
function resolveStart(restaurant, startsAtLocal) {
  const parsed = T.parseLocalMinute(startsAtLocal);
  if (!parsed) throw invalid('starts_at_local must be a local YYYY-MM-DDTHH:MM');
  const tz = restaurant.timezone;
  const start = T.resolveLocal(tz, parsed.dayNaive + parsed.minute * T.MINUTE);
  if (start === null) throw new ApiError(422, 'invalid_local_time', 'that local time does not exist');
  const windows = windowsFor(restaurant, T.weekdayOf(parsed.dayNaive));
  const window = windows.find((w) => parsed.minute >= w.opens && parsed.minute < w.closes);
  if (!window) throw new ApiError(422, 'outside_opening_hours', 'the restaurant is not open then');
  if ((parsed.minute - window.opens) % restaurant.slot_minutes !== 0) {
    throw new ApiError(422, 'not_on_slot_grid', 'start is not on the slot grid');
  }
  const closes = T.resolveLocalLenient(tz, parsed.dayNaive + window.closes * T.MINUTE);
  if (start + durationMs(restaurant) > closes) {
    throw new ApiError(422, 'outside_opening_hours', 'the reservation would end after closing');
  }
  return start;
}

function durationMs(restaurant) {
  return restaurant.reservation_duration_minutes * T.MINUTE;
}

function checkCapacity(table, partySize) {
  if (partySize > table.capacity) throw new ApiError(422, 'party_exceeds_capacity', 'party is larger than the table');
}

function checkCutoff(restaurant, rec, now) {
  if (now >= rec.start_ms - restaurant.cancellation_cutoff_minutes * T.MINUTE) {
    throw new ApiError(409, 'cutoff_passed', 'too close to the start to change this booking');
  }
}

function checkNotCancelled(rec) {
  if (rec.status !== 'confirmed') throw new ApiError(409, 'reservation_cancelled', 'the reservation is cancelled');
}

function overlaps(a, b, duration) {
  return a.restaurant_id === b.restaurant_id && a.table_id === b.table_id &&
    a.start_ms < b.start_ms + duration && b.start_ms < a.start_ms + duration;
}

// Throws 409 table_unavailable unless every candidate is free of every other
// candidate and of every confirmed booking not being replaced.
function checkOccupancy(store, restaurant, candidates) {
  const duration = durationMs(restaurant);
  const replaced = new Set(candidates.map((c) => c.id).filter(Boolean));
  const conflict = () => new ApiError(409, 'table_unavailable', 'the table is taken at that time');
  candidates.forEach((c, i) => {
    for (let j = i + 1; j < candidates.length; j++) if (overlaps(c, candidates[j], duration)) throw conflict();
  });
  for (const rec of store.reservations.values()) {
    if (rec.status !== 'confirmed' || replaced.has(rec.id)) continue;
    if (candidates.some((c) => overlaps(c, rec, duration))) throw conflict();
  }
}

function isTableFree(store, restaurant, tableId, startMs) {
  const duration = durationMs(restaurant);
  const probe = { restaurant_id: restaurant.id, table_id: tableId, start_ms: startMs };
  for (const rec of store.reservations.values()) {
    if (rec.status === 'confirmed' && overlaps(probe, rec, duration)) return false;
  }
  return true;
}

function view(store, rec) {
  const restaurant = store.restaurants.get(rec.restaurant_id);
  const tz = restaurant.timezone;
  return {
    reservation_id: rec.id,
    reference: rec.reference,
    restaurant_id: rec.restaurant_id,
    table_id: rec.table_id,
    party_size: rec.party_size,
    status: rec.status,
    starts_at_local: rec.starts_at_local,
    starts_at: T.formatInstant(tz, rec.start_ms),
    ends_at: T.formatInstant(tz, rec.start_ms + durationMs(restaurant)),
    created_at: rec.created_at,
  };
}

module.exports = { resolveStart, checkCapacity, checkCutoff, checkNotCancelled, checkOccupancy, isTableFree, view };
