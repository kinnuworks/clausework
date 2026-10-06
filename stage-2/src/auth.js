'use strict';
// Signup, login and bearer-token authentication (§6).

const { ApiError, invalid, unauthenticated } = require('./errors');
const { requireString } = require('./fields');
const { getStore } = require('./store');
const { hashPassword, verifyPassword } = require('./secrets');

const EMAIL = /^[^\s@]+@[^\s@]+$/;
const MIN_PASSWORD = 8;

function authenticate(store, req) {
  const header = req.headers.authorization;
  const match = typeof header === 'string' ? /^Bearer +(\S+) *$/i.exec(header) : null;
  if (!match) throw unauthenticated('a bearer token is required');
  const user = store.userForToken(match[1]);
  if (!user) throw unauthenticated('unknown token');
  return user;
}

function session(store, user) {
  return { user_id: user.id, display_name: user.display_name, token: store.issueToken(user.id) };
}

async function signup(body) {
  const email = requireString(body, 'email');
  const password = requireString(body, 'password');
  const displayName = requireString(body, 'display_name');
  if (!EMAIL.test(email)) throw invalid('email must look like local@domain');
  if ([...password].length < MIN_PASSWORD) throw invalid(`password must be at least ${MIN_PASSWORD} characters`);
  if (displayName.trim() === '') throw invalid('display_name must not be empty');
  const taken = () => new ApiError(409, 'email_taken', 'that email is already registered');
  if (getStore().emails.has(email.toLowerCase())) throw taken();
  const passwordHash = await hashPassword(password);
  // Re-read the live store after hashing: the check and the insert below run
  // in one synchronous step, so two signups for one email cannot both pass.
  const store = getStore();
  if (store.emails.has(email.toLowerCase())) throw taken();
  const user = { id: store.nextId('u_', store.users), email, display_name: displayName, password_hash: passwordHash };
  store.addUser(user);
  return { status: 201, body: session(store, user) };
}

async function login(body) {
  const email = requireString(body, 'email');
  const password = requireString(body, 'password');
  const before = getStore();
  const user = before.users.get(before.emails.get(email.toLowerCase()));
  const wrong = () => unauthenticated('wrong email or password');
  if (!user || !(await verifyPassword(password, user.password_hash))) throw wrong();
  const store = getStore();
  if (store.users.get(user.id) !== user) throw wrong();
  return { status: 200, body: session(store, user) };
}

module.exports = { authenticate, signup, login };
