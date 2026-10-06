'use strict';
// Restaurant configuration: validation of fixture/import input and lookups.

const { invalid } = require('./errors');
const { MAX_ID, isObject, isPositiveInt, isNonNegativeInt } = require('./fields');
const { isValidTimeZone, parseClock, WEEKDAYS } = require('./time');

function need(condition, message) {
  if (!condition) throw invalid(message);
}

function isId(v) {
  return typeof v === 'string' && v.length >= 1 && v.length <= MAX_ID;
}

function parseHours(raw, where) {
  need(isObject(raw), `${where}: opening hour entry must be an object`);
  need(WEEKDAYS.includes(raw.weekday), `${where}: weekday must be one of ${WEEKDAYS.join(' ')}`);
  const opens = parseClock(raw.opens);
  const closes = parseClock(raw.closes, true);
  need(opens !== null && closes !== null, `${where}: opens/closes must be HH:MM`);
  need(closes > opens, `${where}: closes must be later than opens`);
  return { weekday: raw.weekday, opens: raw.opens, closes: raw.closes };
}

function parseTable(raw, where) {
  need(isObject(raw), `${where}: table must be an object`);
  need(isId(raw.id), `${where}: table id must be 1..${MAX_ID} characters`);
  need(isPositiveInt(raw.capacity), `${where}: capacity must be a positive integer`);
  const label = raw.label === undefined ? raw.id : raw.label;
  need(typeof label === 'string' || typeof label === 'number', `${where}: label must be a string`);
  return { id: raw.id, label, capacity: raw.capacity };
}

// Fixture-shaped restaurant -> normalized restaurant (throws 422 on bad input).
function parseRestaurant(raw, index) {
  const where = `restaurants[${index}]`;
  need(isObject(raw), `${where} must be an object`);
  need(isId(raw.id), `${where}.id must be 1..${MAX_ID} characters`);
  need(typeof raw.name === 'string', `${where}.name must be a string`);
  need(isValidTimeZone(raw.timezone), `${where}.timezone must be an IANA zone`);
  need(isPositiveInt(raw.slot_minutes), `${where}.slot_minutes must be a positive integer`);
  need(isPositiveInt(raw.reservation_duration_minutes), `${where}.reservation_duration_minutes must be a positive integer`);
  need(isNonNegativeInt(raw.cancellation_cutoff_minutes), `${where}.cancellation_cutoff_minutes must be a non-negative integer`);
  const hours = raw.opening_hours === undefined ? [] : raw.opening_hours;
  need(Array.isArray(hours), `${where}.opening_hours must be an array`);
  need(Array.isArray(raw.tables), `${where}.tables must be an array`);
  const tables = raw.tables.map((t, i) => parseTable(t, `${where}.tables[${i}]`));
  need(new Set(tables.map((t) => t.id)).size === tables.length, `${where}: table ids must be unique`);
  return {
    id: raw.id,
    name: raw.name,
    timezone: raw.timezone,
    slot_minutes: raw.slot_minutes,
    reservation_duration_minutes: raw.reservation_duration_minutes,
    cancellation_cutoff_minutes: raw.cancellation_cutoff_minutes,
    opening_hours: hours.map((h, i) => parseHours(h, `${where}.opening_hours[${i}]`)),
    tables,
  };
}

function findTable(restaurant, tableId) {
  return restaurant.tables.find((t) => t.id === tableId) || null;
}

// Opening windows for a weekday as minute ranges, in fixture order.
function windowsFor(restaurant, weekday) {
  return restaurant.opening_hours
    .filter((h) => h.weekday === weekday)
    .map((h) => ({ opens: parseClock(h.opens), closes: parseClock(h.closes, true) }));
}

module.exports = { parseRestaurant, findTable, windowsFor, isId };
