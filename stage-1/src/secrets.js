'use strict';
// Password hashing (scrypt, run on the libuv pool) and bearer-token handling.
// Only token digests are stored, so an export never needs plaintext tokens to
// keep existing sessions valid.

const crypto = require('crypto');

const SCRYPT = { N: 16384, r: 8, p: 1, maxmem: 64 * 1024 * 1024 };
const KEYLEN = 32;

function scrypt(password, salt) {
  return new Promise((resolve, reject) => {
    crypto.scrypt(password, salt, KEYLEN, SCRYPT, (err, key) => (err ? reject(err) : resolve(key)));
  });
}

async function hashPassword(password) {
  const salt = crypto.randomBytes(16);
  const key = await scrypt(password, salt);
  return `scrypt$${salt.toString('base64')}$${key.toString('base64')}`;
}

async function verifyPassword(password, stored) {
  const [scheme, saltText, keyText] = String(stored).split('$');
  if (scheme !== 'scrypt' || !saltText || !keyText) return false;
  const expected = Buffer.from(keyText, 'base64');
  const actual = await scrypt(password, Buffer.from(saltText, 'base64'));
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
