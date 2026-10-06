'use strict';
// Public read endpoints (§8, stage 3): restaurants and availability. Slots,
// durations and capacities come from the policy selected for the date.

const { invalid, notFound } = require('./errors');
const { parseDigits } = require('./fields');
const { windowsFor } = require('./catalog');
const { areTablesFree, capacityOf, durationMs } = require('./booking');
const T = require('./time');

function listRestaurants(store) {
  const restaurants = [...store.restaurants.values()].map((r) => ({ id: r.id, name: r.name, timezone: r.timezone }));
  return { status: 200, body: { restaurants } };
}

// The original fixture configuration (policies never change it).
function showRestaurant(store, id) {
  const r = store.restaurants.get(id);
  if (!r) throw notFound('unknown restaurant');
  const { manager_user_ids: _managers, ...config } = r;
  return { status: 200, body: config };
}

function readQuery(query) {
  for (const name of ['restaurant_id', 'date', 'party_size']) {
    if (query.get(name) === null) throw invalid(`${name} is required`);
  }
  const dayNaive = T.parseDate(query.get('date'));
  if (dayNaive === null) throw invalid('date must be a calendar date YYYY-MM-DD');
  const partySize = parseDigits(query.get('party_size'), 'party_size');
  if (partySize < 1) throw invalid('party_size must be at least 1');
  const explain = query.get('explain');
  if (explain !== null && explain !== 'true') throw invalid('explain accepts only true');
  return { dayNaive, partySize, explain: explain === 'true' };
}

// One slot: availability by the two rules, for every single table and pair.
function slotAt(store, restaurant, policy, start, partySize, explain) {
  const end = start + durationMs(policy);
  const fits = (ids) => capacityOf(policy, ids) >= partySize;
  const free = (ids) => areTablesFree(store, restaurant.id, ids, start, end);
  const options = [...restaurant.tables.map((t) => [t.id]), ...restaurant.combinable]
    .filter((ids) => fits(ids) && free(ids));
  const slot = {
    starts_at_local: null,
    starts_at: T.formatInstant(restaurant.timezone, start),
    available_table_ids: options.filter((ids) => ids.length === 1).map((ids) => ids[0]),
    available_options: options.map((ids) => ({ table_ids: [...ids], capacity: capacityOf(policy, ids) })),
  };
  if (explain) {
    slot.explain = restaurant.tables.map((t) => {
      const rules = [{ rule: 'capacity', holds: fits([t.id]) }, { rule: 'no_overlap', holds: free([t.id]) }];
      return { table_id: t.id, policy_version: policy.policy_version, available: rules.every((r) => r.holds), rules };
    });
  }
  return slot;
}

function availability(store, query) {
  const { dayNaive, partySize, explain } = readQuery(query);
  const restaurant = store.restaurants.get(query.get('restaurant_id'));
  if (!restaurant) throw notFound('unknown restaurant');
  const tz = restaurant.timezone;
  const policy = store.policyFor(restaurant, query.get('date'));
  const slots = [];
  for (const w of windowsFor(policy, T.weekdayOf(dayNaive))) {
    const closes = T.resolveLocalLenient(tz, dayNaive + w.closes * T.MINUTE);
    for (let minute = w.opens; minute < w.closes; minute += policy.slot_minutes) {
      const naive = dayNaive + minute * T.MINUTE;
      const start = T.resolveLocal(tz, naive);
      if (start === null || start + durationMs(policy) > closes) continue;
      slots.push({ ...slotAt(store, restaurant, policy, start, partySize, explain), starts_at_local: T.formatNaiveMinute(naive) });
    }
  }
  return { status: 200, body: { restaurant_id: restaurant.id, date: query.get('date'), timezone: tz, slots } };
}

module.exports = { listRestaurants, showRestaurant, availability };
