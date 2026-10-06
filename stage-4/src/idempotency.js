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
// Iterative, so arbitrarily deep request bodies cannot exhaust the stack.
function canonical(value) {
  const out = [];
  const pending = [{ value }];
  while (pending.length > 0) {
    const item = pending.pop();
    if ('text' in item) {
      out.push(item.text);
      continue;
    }
    const v = item.value;
    if (v === null || typeof v !== 'object') {
      out.push(JSON.stringify(v));
      continue;
    }
    const isArray = Array.isArray(v);
    const keys = isArray ? null : Object.keys(v).sort();
    const parts = isArray
      ? v.map((element) => [{ value: element }])
      : keys.map((k) => [{ text: `${JSON.stringify(k)}:` }, { value: v[k] }]);
    const sequence = [{ text: isArray ? '[' : '{' }];
    parts.forEach((part, i) => {
      if (i > 0) sequence.push({ text: ',' });
      sequence.push(...part);
    });
    sequence.push({ text: isArray ? ']' : '}' });
    for (let i = sequence.length - 1; i >= 0; i--) pending.push(sequence[i]);
  }
  return out.join('');
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
