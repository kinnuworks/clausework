'use strict';
// Password hashing (scrypt, run on the libuv pool) and bearer-token handling.
// Only token digests are stored, so an export never needs plaintext tokens to
// keep existing sessions valid.

const crypto = require('crypto');

// N = 2^12 keeps reset of a few hundred seeded users well inside its time
// limit; the cost is recorded in each hash so it can be raised later.
const SCRYPT_N = 4096;
const KEYLEN = 32;

function scrypt(password, salt, N) {
  const options = { N, r: 8, p: 1, maxmem: 256 * N * 8 + 1024 * 1024 };
  return new Promise((resolve, reject) => {
    crypto.scrypt(password, salt, KEYLEN, options, (err, key) => (err ? reject(err) : resolve(key)));
  });
}

async function hashPassword(password) {
  const salt = crypto.randomBytes(16);
  const key = await scrypt(password, salt, SCRYPT_N);
  return `scrypt$${SCRYPT_N}$${salt.toString('base64')}$${key.toString('base64')}`;
}

async function verifyPassword(password, stored) {
  const [scheme, costText, saltText, keyText] = String(stored).split('$');
  const N = Number(costText);
  if (scheme !== 'scrypt' || !/^[0-9]+$/.test(costText || '') || N < 2 || (N & (N - 1)) !== 0 || N > 1 << 16) return false;
  if (!saltText || !keyText) return false;
  const expected = Buffer.from(keyText, 'base64');
  const actual = await scrypt(password, Buffer.from(saltText, 'base64'), N);
  return expected.length === actual.length && crypto.timingSafeEqual(expected, actual);
}

function newToken() {
  return crypto.randomBytes(32).toString('base64url');
}

function tokenDigest(token) {
  return crypto.createHash('sha256').update(token).digest('hex');
}

const REFERENCE_ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';

function newReference() {
  let out = '';
  for (let i = 0; i < 8; i++) out += REFERENCE_ALPHABET[crypto.randomInt(REFERENCE_ALPHABET.length)];
  return out;
}

module.exports = { hashPassword, verifyPassword, newToken, tokenDigest, newReference };
