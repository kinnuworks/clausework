'use strict';
// Request-field checks shared by bookings, amendments, moves and series.
// Wrong JSON types are 400 malformed_request; bad values are 422.

const { ApiError, malformed, invalid } = require('./errors');
const { checkId } = require('./fields');

function checkTypes(body, names) {
  for (const name of names) {
    if (name in body && typeof body[name] !== 'string') throw malformed(`${name} must be a string`);
  }
}

function checkStartFormat(value) {
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(value)) throw invalid('starts_at_local must be a local YYYY-MM-DDTHH:MM');
}

// Type check of a table selection: table_id a string, table_ids an array of strings.
function checkTableTypes(body) {
  checkTypes(body, ['table_id']);
  if ('table_ids' in body && !(Array.isArray(body.table_ids) && body.table_ids.every((id) => typeof id === 'string'))) {
    throw malformed('table_ids must be an array of strings');
  }
}

// Value check of a table selection -> the ids as a list, or undefined when
// neither field was sent. Both fields, an empty set or a repeated id are 422.
function readTableIds(body) {
  const hasOne = 'table_id' in body;
  const hasMany = 'table_ids' in body;
  if (hasOne && hasMany) throw invalid('send table_id or table_ids, not both');
  if (!hasOne && !hasMany) return undefined;
  const ids = hasOne ? [body.table_id] : body.table_ids;
  if (ids.length === 0) throw invalid('table_ids must not be empty');
  if (new Set(ids).size !== ids.length) throw invalid('table_ids must not repeat a table');
  ids.forEach((id) => checkId(id, 'table_ids'));
  return ids;
}

// Optional expected_revision: a positive integer (422 otherwise) that must
// equal the current revision (409 stale_revision otherwise).
function checkExpectedRevision(body, rec) {
  if (!('expected_revision' in body)) return;
  const v = body.expected_revision;
  if (typeof v !== 'number' || !Number.isInteger(v) || v < 1) throw invalid('expected_revision must be a positive integer');
  if (v !== rec.revision) throw new ApiError(409, 'stale_revision', 'the reservation has changed since that revision');
}

module.exports = { checkTypes, checkStartFormat, checkTableTypes, readTableIds, checkExpectedRevision };
