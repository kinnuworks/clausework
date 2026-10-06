'use strict';
// Exactly-once writes (§7). A receipt is looked up and, on success, stored
// inside the same synchronous run as the write it guards, so concurrent
// identical requests cannot both reach the write: the first stores its
// receipt before any other request is processed. Failed (4xx) runs throw
// before storing, which leaves the key free for reuse.

const { ApiError, invalid } = require('./errors');

const MAX_KEY = 255;

function readKey(req) {
  const key = req.headers['idempotency-key'];
  if (key === undefined || key === '') {
    throw new ApiError(400, 'missing_idempotency_key', 'Idempotency-Key header is required');
  }
  if ([...key].length > MAX_KEY) throw invalid(`Idempotency-Key must be 1..${MAX_KEY} characters`);
  return key;
}

// JSON text with object keys sorted, so equal JSON values compare equal.
function canonical(value) {
  if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
  if (value !== null && typeof value === 'object') {
    const keys = Object.keys(value).sort();
    return `{${keys.map((k) => `${JSON.stringify(k)}:${canonical(value[k])}`).join(',')}}`;
  }
  return JSON.stringify(value);
}

// `run` must be synchronous and return { status, body } or throw ApiError.
function once(store, { user, method, path, key, body }, run) {
  const scope = JSON.stringify([user.id, method, path, key]);
  const text = canonical(body);
  const prior = store.receipts.get(scope);
  if (prior) {
    if (prior.body !== text) throw new ApiError(409, 'idempotency_key_reuse', 'key already used with a different body');
    return { status: 200, body: prior.response };
  }
  const result = run();
  store.receipts.set(scope, { body: text, status: result.status, response: result.body });
  return result;
}

module.exports = { readKey, once };
