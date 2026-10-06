// Signed-in diner, kept in localStorage so a session outlives reloads and server upgrades.
const STORE = "tablekeeper.session";
const listeners = new Set();

function read() {
  try {
    const raw = window.localStorage.getItem(STORE);
    const value = raw ? JSON.parse(raw) : null;
    return value && value.token ? value : null;
  } catch (err) {
    return null;
  }
}

export const session = {
  get: read,
  set(value) {
    const record = { token: value.token, user_id: value.user_id, display_name: value.display_name };
    try { window.localStorage.setItem(STORE, JSON.stringify(record)); } catch (err) { /* private mode */ }
    listeners.forEach((fn) => fn(record));
  },
  clear() {
    try { window.localStorage.removeItem(STORE); } catch (err) { /* ignore */ }
    listeners.forEach((fn) => fn(null));
  },
  subscribe(fn) {
    listeners.add(fn);
    return () => listeners.delete(fn);
  },
};
