'use strict';
// Seating changes after a table closure (stage 4). A preview finds the best
// plan and stores it; nothing else changes. Applying it records the closure
// and every reassignment in one synchronous step, guarded by the restaurant
// revision the plan was computed at.

const { ApiError, malformed, invalid, notFound } = require('./errors');
const { managedRestaurant } = require('./policies');
const { bestPlan } = require('./optimizer');
const B = require('./booking');
const H = require('./history');
const T = require('./time');

const LIMITS = { tables: 6, pairs: 4, bookings: 6 };
const INSTANT = /^(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2})(?::(\d{2})(?:\.\d+)?)?(Z|[+-]\d{2}:\d{2})$/;

// RFC 3339 instant with an explicit offset -> ms, or 422.
function parseInstant(value, name) {
  const m = typeof value === 'string' ? INSTANT.exec(value) : null;
  const ms = m && T.parseDate(m[1]) !== null && +m[2] < 24 && +m[3] < 60 && +(m[4] || 0) < 60 ? Date.parse(value) : NaN;
  if (Number.isNaN(ms)) throw invalid(`${name} must be an RFC 3339 instant with an offset`);
  return ms;
}

function readClosure(body, restaurant) {
  for (const name of ['table_id', 'from', 'to']) {
    if (name in body && typeof body[name] !== 'string') throw malformed(`${name} must be a string`);
    if (!(name in body)) throw invalid(`${name} is required`);
  }
  const fromMs = parseInstant(body.from, 'from');
  const toMs = parseInstant(body.to, 'to');
  if (fromMs >= toMs) throw invalid('from must be before to');
  if (!restaurant.tables.some((t) => t.id === body.table_id)) throw notFound('unknown table');
  return { table_id: body.table_id, from: body.from, to: body.to, from_ms: fromMs, to_ms: toMs };
}

const byReference = (a, b) => (a.reference < b.reference ? -1 : a.reference > b.reference ? 1 : 0);

// Confirmed bookings overlapping the closure, in reference order.
function considered(store, restaurant, closure) {
  return [...store.reservations.values()]
    .filter((r) => r.restaurant_id === restaurant.id && r.status === 'confirmed' &&
      r.start_ms < closure.to_ms && closure.from_ms < B.endOf(r))
    .sort(byReference);
}

// Planning input for one booking: seats under its own terms; an option is
// allowed unless it meets the proposed or an applied closure or a fixed booking.
function planningInput(store, restaurant, closure, rec, consideredIds) {
  const span = B.span(rec);
  const fixed = [...store.reservations.values()].filter((r) => r.restaurant_id === restaurant.id &&
    r.status === 'confirmed' && !consideredIds.has(r.id)).map(B.span);
  return {
    current: rec.table_ids,
    party: rec.party_size,
    start_ms: span.start_ms,
    end_ms: span.end_ms,
    seats: (ids) => ids.reduce((sum, id) => sum + rec.terms.capacities[id], 0),
    allowed: (ids) => {
      const s = { ...span, table_ids: ids };
      if (ids.includes(closure.table_id) && s.start_ms < closure.to_ms && closure.from_ms < s.end_ms) return false;
      return !B.closed(store, s) && !fixed.some((f) => B.overlaps(s, f));
    },
  };
}

function preview(store, user, body, now, restaurantId) {
  const restaurant = managedRestaurant(store, user, restaurantId);
  const closure = readClosure(body, restaurant);
  const recs = considered(store, restaurant, closure);
  if (restaurant.tables.length > LIMITS.tables || restaurant.combinable.length > LIMITS.pairs ||
    recs.length > LIMITS.bookings) {
    throw new ApiError(422, 'planning_limit', 'too many tables, pairs or bookings to plan');
  }
  const options = [...restaurant.tables.map((t) => [t.id]), ...restaurant.combinable].map((ids, rank) => ({ ids, rank }));
  const consideredIds = new Set(recs.map((r) => r.id));
  const plan = bestPlan(recs.map((r) => planningInput(store, restaurant, closure, r, consideredIds)), options);
  if (!plan) throw new ApiError(409, 'no_feasible_plan', 'no seating arrangement fits around that closure');
  const assignments = recs.map((r, i) => ({ reference: r.reference, table_ids: [...plan.picks[i].ids], changed: plan.picks[i].changed }));
  const stored = {
    id: store.nextId('plan_', store.plans),
    restaurant_id: restaurant.id,
    revision: store.revisionOf(restaurant.id),
    closure,
    assignments: recs.map((r, i) => ({ reservation_id: r.id, ...assignments[i] })),
    applied: false,
  };
  store.plans.set(stored.id, stored);
  return {
    status: 201,
    body: {
      plan_id: stored.id,
      restaurant_revision: stored.revision,
      closure: { table_id: closure.table_id, from: closure.from, to: closure.to },
      assignments,
      moved_count: plan.moved,
      unused_seats: plan.unused,
    },
  };
}

function apply(store, user, body, now, restaurantId, planId) {
  const restaurant = managedRestaurant(store, user, restaurantId);
  const plan = store.plans.get(planId);
  if (!plan || plan.restaurant_id !== restaurant.id) throw notFound('no such plan');
  if (plan.applied) throw new ApiError(409, 'plan_already_applied', 'that plan has already been applied');
  if (plan.revision !== store.revisionOf(restaurant.id)) {
    throw new ApiError(409, 'stale_plan', 'the restaurant changed since this plan was made');
  }
  const at = T.formatInstant(restaurant.timezone, now.ms);
  const touchedSeries = new Set();
  const results = plan.assignments.map((a) => {
    const rec = store.reservations.get(a.reservation_id);
    if (!a.changed) return rec;
    const moved = { ...rec, table_ids: [...a.table_ids], revision: rec.revision + 1 };
    const change = { field: 'table_ids', from: [...rec.table_ids], to: [...a.table_ids] };
    const next = H.withEntry(moved, 'reassigned', [change], at, { plan_id: plan.id });
    store.addReservation(next);
    if (next.series_id && store.series.has(next.series_id)) touchedSeries.add(store.series.get(next.series_id));
    return next;
  });
  for (const s of touchedSeries) s.revision += 1;
  const { table_id: tableId, from_ms: fromMs, to_ms: toMs } = plan.closure;
  store.closures.set(restaurant.id, [...store.closuresOf(restaurant.id), { table_id: tableId, from_ms: fromMs, to_ms: toMs, plan_id: plan.id }]);
  plan.applied = true;
  store.bumpRevision(restaurant.id);
  return {
    status: 201,
    body: { plan_id: plan.id, restaurant_revision: store.revisionOf(restaurant.id), reservations: results.map((r) => B.view(store, r)) },
  };
}

module.exports = { preview, apply };
