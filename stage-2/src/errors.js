'use strict';
// One error type for every 4xx/5xx; the server renders it as
// { "error": { "code", "message" } }.

class ApiError extends Error {
  constructor(status, code, message) {
    super(message || code);
    this.status = status;
    this.code = code;
  }
}

const malformed = (msg) => new ApiError(400, 'malformed_request', msg || 'request body is malformed');
const invalid = (msg) => new ApiError(422, 'validation_failed', msg || 'validation failed');
const notFound = (msg) => new ApiError(404, 'not_found', msg || 'not found');
const unauthenticated = (msg) => new ApiError(401, 'unauthenticated', msg || 'authentication required');

module.exports = { ApiError, malformed, invalid, notFound, unauthenticated };
