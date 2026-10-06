'use strict';
// Booking policies (stage 3): validation of a published policy, policy 0
// derived from the fixture, selection by local start date, and the
// accepted-terms snapshot a booking keeps.

const { invalid } = require('./errors');
const { isObject } = require('./fields');
const { parseClock, parseDate, WEEKDAYS } = require('./time');

const isInt = (v) => typeof v === 'number' && Number.isInteger(v);
const inRange = (v, lo, hi) => isInt(v) && v >= lo && v <= hi;

function need(condition, message) {
  if (!condition) throw invalid(message);
}

function parseHours(raw) {
  need(Array.isArray(raw), 'opening_hours must be an array');
  const seen = new Set();
  return raw.map((h, i) => {
    need(isObject(h) && WEEKDAYS.includes(h.weekday), `opening_hours[${i}].weekday is invalid`);
    need(!seen.has(h.weekday), `opening_hours names ${h.weekday} twice`);
    seen.add(h.weekday);
    const opens = parseClock(h.opens);
    const closes = parseClock(h.closes, true);
    need(opens !== null && closes !== null && closes > opens, `opening_hours[${i}] needs opens < closes as HH:MM`);
    return { weekday: h.weekday, opens: h.opens, closes: h.closes };
  });
}

function parseCapacities(raw, restaurant) {
  need(isObject(raw), 'capacities must be an object');
  const ids = restaurant.tables.map((t) => t.id);
  need(Object.keys(raw).length === ids.length && ids.every((id) => id in raw), 'capacities must name exactly the restaurant tables');
  const out = {};
  for (const id of ids) {
    need(inRange(raw[id], 1, 100), `capacities.${id} must be an integer 1..100`);
    out[id] = raw[id];
  }
  return out;
}

// The rule fields shared by a published policy and accepted terms.
function parseRules(body, restaurant) {
  need(inRange(body.slot_minutes, 1, 1440), 'slot_minutes must be an integer 1..1440');
  need(inRange(body.reservation_duration_minutes, 1, 1440), 'reservation_duration_minutes must be an integer 1..1440');
  need(inRange(body.cancellation_cutoff_minutes, 0, 10080), 'cancellation_cutoff_minutes must be an integer 0..10080');
  return {
    slot_minutes: body.slot_minutes,
    reservation_duration_minutes: body.reservation_duration_minutes,
    cancellation_cutoff_minutes: body.cancellation_cutoff_minutes,
    opening_hours: parseHours(body.opening_hours),
    capacities: parseCapacities(body.capacities, restaurant),
  };
}

// POST body -> policy without its version (422 on anything invalid).
function parsePolicy(body, restaurant) {
  need(typeof body.effective_from === 'string' && parseDate(body.effective_from) !== null,
    'effective_from must be a date YYYY-MM-DD');
  return { effective_from: body.effective_from, ...parseRules(body, restaurant) };
}

// Stored accepted terms (export/import) -> validated copy.
function parseTerms(raw, restaurant) {
  need(isObject(raw) && isInt(raw.policy_version) && raw.policy_version >= 0, 'accepted_terms is invalid');
  return { policy_version: raw.policy_version, ...parseRules(raw, restaurant) };
}

function policyZero(restaurant) {
  return {
    policy_version: 0,
    effective_from: null,
    slot_minutes: restaurant.slot_minutes,
    reservation_duration_minutes: restaurant.reservation_duration_minutes,
    cancellation_cutoff_minutes: restaurant.cancellation_cutoff_minutes,
    opening_hours: restaurant.opening_hours,
    capacities: Object.fromEntries(restaurant.tables.map((t) => [t.id, t.capacity])),
  };
}

// The policy for a local date "YYYY-MM-DD": greatest effective_from not
// later than the date, ties to the greatest version; policy 0 otherwise.
function selectPolicy(restaurant, policies, date) {
  let best = null;
  for (const p of policies) {
    if (p.effective_from > date) continue;
    if (!best || p.effective_from > best.effective_from ||
      (p.effective_from === best.effective_from && p.policy_version > best.policy_version)) best = p;
  }
  return best || policyZero(restaurant);
}

// Accepted terms: the whole policy except effective_from (a fresh copy).
function termsOf(policy) {
  return JSON.parse(JSON.stringify({
    policy_version: policy.policy_version,
    slot_minutes: policy.slot_minutes,
    reservation_duration_minutes: policy.reservation_duration_minutes,
    cancellation_cutoff_minutes: policy.cancellation_cutoff_minutes,
    opening_hours: policy.opening_hours,
    capacities: policy.capacities,
  }));
}

function publicPolicy(p) {
  return {
    effective_from: p.effective_from,
    slot_minutes: p.slot_minutes,
    reservation_duration_minutes: p.reservation_duration_minutes,
    cancellation_cutoff_minutes: p.cancellation_cutoff_minutes,
    opening_hours: p.opening_hours,
    capacities: p.capacities,
    policy_version: p.policy_version,
  };
}

module.exports = { parsePolicy, parseTerms, policyZero, selectPolicy, termsOf, publicPolicy };
