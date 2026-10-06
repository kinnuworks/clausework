'use strict';
// Field-level checks shared by every entry point. Wrong JSON types are 400
// malformed_request; well-typed but invalid values are 422 validation_failed.

const { malformed, invalid } = require('./errors');

const MAX_ID = 64;

function isObject(v) {
  return v !== null && typeof v === 'object' && !Array.isArray(v);
}

// Required string: absent -> 422, wrong type -> 400.
function requireString(body, name) {
  if (!(name in body) || body[name] === undefined) throw invalid(`${name} is required`);
  if (typeof body[name] !== 'string') throw malformed(`${name} must be a string`);
  return body[name];
}

// Optional string: absent -> undefined, wrong type -> 400.
function optionalString(body, name) {
  if (!(name in body)) return undefined;
  if (typeof body[name] !== 'string') throw malformed(`${name} must be a string`);
  return body[name];
}

function checkId(value, name) {
  if (value.length === 0 || value.length > MAX_ID) throw invalid(`${name} must be 1..${MAX_ID} characters`);
  return value;
}

// party_size: any value that is not an integer >= 1 is 422, whatever its type.
function checkPartySize(value) {
  if (typeof value !== 'number' || !Number.isInteger(value) || value < 1) {
    throw invalid('party_size must be an integer of at least 1');
  }
  return value;
}

// Integer query parameter written as plain decimal digits.
function parseDigits(text, name) {
  if (typeof text !== 'string' || !/^[0-9]+$/.test(text)) throw invalid(`${name} must be a whole number`);
  return Number(text);
}

function isPositiveInt(v) {
  return typeof v === 'number' && Number.isInteger(v) && v >= 1;
}

function isNonNegativeInt(v) {
  return typeof v === 'number' && Number.isInteger(v) && v >= 0;
}

module.exports = {
  MAX_ID, isObject, requireString, optionalString, checkId, checkPartySize, parseDigits,
  isPositiveInt, isNonNegativeInt,
};
