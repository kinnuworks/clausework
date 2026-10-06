'use strict';
// Public read endpoints (§8): restaurants and availability.

const { invalid, notFound } = require('./errors');
const { parseDigits } = require('./fields');
const { windowsFor } = require('./catalog');
const { areTablesFree, capacityOf } = require('./booking');
const { findTable } = require('./catalog');
const T = require('./time');

function listRestaurants(store) {
  const restaurants = [...store.restaurants.values()].map((r) => ({ id: r.id, name: r.name, timezone: r.timezone }));
  return { status: 200, body: { restaurants } };
}

function showRestaurant(store, id) {
  const r = store.restaurants.get(id);
  if (!r) throw notFound('unknown restaurant');
  return { status: 200, body: r };
}

function availability(store, query) {
  for (const name of ['restaurant_id', 'date', 'party_size']) {
    if (query.get(name) === null) throw invalid(`${name} is required`);
  }
  const dayNaive = T.parseDate(query.get('date'));
  if (dayNaive === null) throw invalid('date must be a calendar date YYYY-MM-DD');
  const partySize = parseDigits(query.get('party_size'), 'party_size');
  if (partySize < 1) throw invalid('party_size must be at least 1');
  const restaurant = store.restaurants.get(query.get('restaurant_id'));
  if (!restaurant) throw notFound('unknown restaurant');

  const tz = restaurant.timezone;
  const duration = restaurant.reservation_duration_minutes * T.MINUTE;
  // Every seating option that fits the party: singles in fixture order, then pairs.
  const options = [
    ...restaurant.tables.map((t) => [t]),
    ...restaurant.combinable.map((pair) => pair.map((id) => findTable(restaurant, id))),
  ].filter((tables) => capacityOf(tables) >= partySize);
  const slots = [];
  for (const w of windowsFor(restaurant, T.weekdayOf(dayNaive))) {
    const closes = T.resolveLocalLenient(tz, dayNaive + w.closes * T.MINUTE);
    for (let minute = w.opens; minute < w.closes; minute += restaurant.slot_minutes) {
      const naive = dayNaive + minute * T.MINUTE;
      const start = T.resolveLocal(tz, naive);
      if (start === null || start + duration > closes) continue;
      const free = options
        .map((tables) => tables.map((t) => t.id))
        .filter((ids) => areTablesFree(store, restaurant, ids, start));
      slots.push({
        starts_at_local: T.formatNaiveMinute(naive),
        starts_at: T.formatInstant(tz, start),
        available_table_ids: free.filter((ids) => ids.length === 1).map((ids) => ids[0]),
        available_options: free.map((ids) => ({
          table_ids: ids,
          capacity: capacityOf(ids.map((id) => findTable(restaurant, id))),
        })),
      });
    }
  }
  return {
    status: 200,
    body: { restaurant_id: restaurant.id, date: query.get('date'), timezone: tz, slots },
  };
}

module.exports = { listRestaurants, showRestaurant, availability };
