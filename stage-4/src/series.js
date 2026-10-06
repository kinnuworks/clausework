'use strict';
// Recurring reservations (stage 3): POST /series adopts a booking as
// occurrence zero and plans every further occurrence under its own date's
// policy. Nothing is written until all occurrences pass, in index order.

const { ApiError, malformed, invalid, notFound } = require('./errors');
const B = require('./booking');
const R = require('./reservations');
const T = require('./time');

const WEEK = 7 * 24 * 60 * T.MINUTE;

function intIn(value, lo, hi, name) {
  if (typeof value !== 'number' || !Number.isInteger(value) || value < lo || value > hi) {
    throw invalid(`${name} must be an integer ${lo}..${hi}`);
  }
  return value;
}

function readBody(body) {
  if ('anchor_reference' in body && typeof body.anchor_reference !== 'string') {
    throw malformed('anchor_reference must be a string');
  }
  if (!('anchor_reference' in body)) throw invalid('anchor_reference is required');
  return {
    reference: body.anchor_reference,
    count: intIn(body.count, 2, 12, 'count'),
    intervalWeeks: intIn(body.interval_weeks, 1, 4, 'interval_weeks'),
  };
}

// Local start of occurrence i: the anchor's date + i weeks * interval, same clock.
function occurrenceStart(anchor, i, intervalWeeks) {
  const day = T.parseDate(anchor.starts_at_local.slice(0, 10)) + i * intervalWeeks * WEEK;
  return `${T.formatNaiveMinute(day).slice(0, 10)}${anchor.starts_at_local.slice(10)}`;
}

function view(store, s) {
  return {
    series_id: s.id,
    revision: s.revision,
    interval_weeks: s.interval_weeks,
    occurrences: s.occurrences.map((o) => {
      const rec = store.reservations.get(o.reservation_id);
      return { index: o.index, reference: rec.reference, exception: o.exception, reservation: B.view(store, rec) };
    }),
  };
}

function create(store, user, body, now) {
  const { reference, count, intervalWeeks } = readBody(body);
  const anchor = R.ownReservation(store, user, reference);
  B.checkNotCancelled(anchor);
  if (anchor.series_id) throw new ApiError(409, 'already_in_series', 'that booking is already in a series');
  B.checkCutoff(anchor, now.ms);
  const restaurant = store.restaurants.get(anchor.restaurant_id);
  const planned = [];
  for (let i = 1; i < count; i++) {
    const rec = R.planBooking(store, user, restaurant, anchor.table_ids,
      occurrenceStart(anchor, i, intervalWeeks), anchor.party_size, now);
    planned.push({ ...rec, id: `planned:${i}` });
    B.checkOccupancy(store, planned);
  }
  const seriesId = store.nextId('ser_', store.series);
  const generated = planned.map((rec) => R.commitNew(store, { ...rec, series_id: seriesId }));
  store.addReservation({ ...anchor, series_id: seriesId });
  const s = {
    id: seriesId,
    user_id: user.id,
    interval_weeks: intervalWeeks,
    revision: 1,
    occurrences: [anchor, ...generated].map((rec, index) => ({ index, reservation_id: rec.id, exception: false })),
  };
  store.series.set(seriesId, s);
  store.bumpRevision(restaurant.id);
  return { status: 201, body: view(store, s) };
}

function show(store, user, id) {
  const s = store.series.get(id);
  if (!s || !user || s.user_id !== user.id) throw notFound('no such series');
  return { status: 200, body: view(store, s) };
}

module.exports = { create, show };
