'use strict';
// Route table: maps method + path to a handler. Each handler receives a
// request context and returns { status, body } or throws ApiError.

const { malformed, invalid } = require('./errors');
const { isObject } = require('./fields');
const S = require('./store');
const auth = require('./auth');
const browse = require('./browse');
const R = require('./reservations');
const { readKey, once } = require('./idempotency');
const { formatUtc } = require('./time');
const screens = require('./screens');

function jsonObject(ctx) {
  let value;
  try {
    value = JSON.parse(ctx.rawBody);
  } catch {
    throw malformed('request body is not valid JSON');
  }
  if (!isObject(value)) throw malformed('request body must be a JSON object');
  return value;
}

function now() {
  const ms = Date.now();
  return { ms, text: formatUtc(ms) };
}

// Authenticated handler over the live store.
const authed = (fn) => (ctx) => {
  const store = S.getStore();
  return fn(store, auth.authenticate(store, ctx.req), ctx);
};

// Authenticated, idempotent write: auth, key, body, then receipt lookup —
// all before any field validation.
const idempotent = (fn) => authed((store, user, ctx) => {
  const key = readKey(ctx.req);
  const body = jsonObject(ctx);
  const request = { user, method: ctx.method, path: ctx.path, key, body };
  return once(store, request, () => fn(store, user, body, now()));
});

async function reset(ctx) {
  S.replaceStore(await S.storeFromFixture(jsonObject(ctx)));
  return { status: 204 };
}

function importState(ctx) {
  const doc = jsonObject(ctx);
  if (!('track' in doc) || !('format_version' in doc) || !('state' in doc)) {
    throw invalid('track, format_version and state are required');
  }
  S.replaceStore(S.storeFromExport(doc));
  return { status: 204 };
}

const routes = [
  ['GET', /^\/(signup|login|lookup)?$/, screens.screen],
  ['GET', /^\/static\/(.+)$/, (ctx) => screens.staticFile(ctx.params[0])],
  ['GET', /^\/health$/, () => ({ status: 200, body: { status: 'ok' } })],
  ['POST', /^\/_test\/reset$/, reset],
  ['GET', /^\/_test\/export$/, () => ({ status: 200, body: S.exportStore(S.getStore()) })],
  ['POST', /^\/_test\/import$/, importState],
  ['POST', /^\/auth\/signup$/, (ctx) => auth.signup(jsonObject(ctx))],
  ['POST', /^\/auth\/login$/, (ctx) => auth.login(jsonObject(ctx))],
  ['GET', /^\/restaurants$/, () => browse.listRestaurants(S.getStore())],
  ['GET', /^\/restaurants\/([^/]+)$/, (ctx) => browse.showRestaurant(S.getStore(), ctx.params[0])],
  ['GET', /^\/availability$/, (ctx) => browse.availability(S.getStore(), ctx.query)],
  ['POST', /^\/reservations$/, idempotent(R.create)],
  ['GET', /^\/reservations$/, authed((store, user) => R.list(store, user))],
  ['GET', /^\/reservations\/([^/]+)$/, authed((store, user, ctx) => R.show(store, user, ctx.params[0]))],
  ['PATCH', /^\/reservations\/([^/]+)$/,
    authed((store, user, ctx) => R.amend(store, user, ctx.params[0], jsonObject(ctx), now()))],
  ['POST', /^\/reservations\/([^/]+)\/cancel$/,
    authed((store, user, ctx) => R.cancel(store, user, ctx.params[0], now()))],
  ['POST', /^\/reservation-moves$/, idempotent(R.moveBatch)],
];

// -> { handler, params } or null.
function match(method, path) {
  for (const [m, pattern, handler] of routes) {
    const found = m === method && pattern.exec(path);
    if (found) return { handler, params: found.slice(1) };
  }
  return null;
}

module.exports = { match };
