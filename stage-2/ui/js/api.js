// Same-origin JSON API client. Every call resolves to one of three outcomes:
//   { kind: "ok", status, data }            — the server answered 2xx
//   { kind: "refused", status, code, message } — the server answered 4xx (a confirmed "no")
//   { kind: "lost", reason }                — no trustworthy answer (network, timeout, 5xx)
import { session } from "./session.js";

const TIMEOUT_MS = 8000;

export async function request(method, path, { body, headers = {}, auth = false } = {}) {
  const init = { method, headers: { Accept: "application/json", ...headers } };
  if (body !== undefined) {
    init.headers["Content-Type"] = "application/json";
    init.body = typeof body === "string" ? body : JSON.stringify(body);
  }
  const current = session.get();
  if (auth && current) init.headers.Authorization = `Bearer ${current.token}`;

  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), TIMEOUT_MS);
  init.signal = controller.signal;

  let response;
  try {
    response = await fetch(path, init);
  } catch (err) {
    window.clearTimeout(timer);
    return { kind: "lost", reason: controller.signal.aborted ? "timeout" : "network" };
  }
  let data = null;
  try {
    const text = await response.text();
    data = text ? JSON.parse(text) : null;
  } catch (err) {
    window.clearTimeout(timer);
    if (response.ok || response.status >= 500) return { kind: "lost", reason: "unreadable" };
    data = null;
  }
  window.clearTimeout(timer);

  if (response.status >= 500 || response.status === 408) return { kind: "lost", reason: `status ${response.status}` };
  if (response.ok) return { kind: "ok", status: response.status, data };
  const error = (data && data.error) || {};
  return {
    kind: "refused",
    status: response.status,
    code: error.code || `http_${response.status}`,
    message: error.message || "",
  };
}

export const api = {
  restaurants: () => request("GET", "/restaurants"),
  restaurant: (id) => request("GET", `/restaurants/${encodeURIComponent(id)}`),
  availability: (restaurantId, date, partySize) => {
    const q = new URLSearchParams({ restaurant_id: restaurantId, date, party_size: String(partySize) });
    return request("GET", `/availability?${q}`);
  },
  signup: (body) => request("POST", "/auth/signup", { body }),
  login: (body) => request("POST", "/auth/login", { body }),
  book: (bodyText, key) => request("POST", "/reservations", { body: bodyText, auth: true, headers: { "Idempotency-Key": key } }),
  reservation: (ref) => request("GET", `/reservations/${encodeURIComponent(ref)}`, { auth: true }),
  cancel: (ref) => request("POST", `/reservations/${encodeURIComponent(ref)}/cancel`, { auth: true }),
};

// Idempotency keys: random, works outside secure contexts (no crypto.randomUUID needed).
export function newKey() {
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  return "tk-" + Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}
