// Turning API data into plain words for diners.

export function tableName(table) {
  if (!table) return "Table";
  const label = String(table.label ?? table.id);
  return /^\d+[a-z]?$/i.test(label) ? `Table ${label}` : label;
}

export function tablesPhrase(tables) {
  if (tables.length === 1) return tableName(tables[0]);
  const labels = tables.map((t) => String(t.label ?? t.id));
  return labels.every((l) => /^\d+[a-z]?$/i.test(l)) ? `Tables ${labels.join(" + ")}` : labels.join(" + ");
}

// "2026-09-24T19:00" -> "19:00"
export function hhmm(startsAtLocal) {
  return String(startsAtLocal || "").slice(11, 16);
}

function dateParts(ymd) {
  const [y, m, d] = String(ymd).slice(0, 10).split("-").map(Number);
  return new Date(Date.UTC(y, (m || 1) - 1, d || 1));
}

// The booking's own local time span: "19:00–20:30" (end from the server's ends_at, which
// carries the restaurant's offset, so its clock reading is local). Start alone if no end.
export function timeSpan(reservation) {
  const start = hhmm(reservation.starts_at_local);
  const end = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(reservation.ends_at || "") ? reservation.ends_at.slice(11, 16) : "";
  return end ? `${start}–${end}` : start;
}

// accepted_terms.cancellation_cutoff_minutes -> "2 hours" / "45 minutes" / "1 day"
export function cutoffPhrase(minutes) {
  if (!Number.isInteger(minutes) || minutes <= 0) return "";
  if (minutes % 1440 === 0) return `${minutes / 1440} ${minutes === 1440 ? "day" : "days"}`;
  if (minutes % 60 === 0) return `${minutes / 60} ${minutes === 60 ? "hour" : "hours"}`;
  return `${minutes} minutes`;
}

// "2026-09-24" -> "Thursday 24 September 2026"
export function longDate(ymd) {
  const date = dateParts(ymd);
  if (Number.isNaN(date.getTime())) return ymd;
  return date.toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long", year: "numeric", timeZone: "UTC" });
}

// "2026-09-24" -> "Thu 24 Sep"
export function shortDate(ymd) {
  const date = dateParts(ymd);
  if (Number.isNaN(date.getTime())) return ymd;
  return date.toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "short", timeZone: "UTC" });
}

export function todayLocal() {
  const now = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

export function seatCount(n) {
  return `${n} ${Number(n) === 1 ? "seat" : "seats"}`;
}

export function guests(n) {
  return `${n} ${Number(n) === 1 ? "guest" : "guests"}`;
}

const MESSAGES = {
  table_unavailable: "Someone else just took that table for this time. The times below are refreshed — pick another seat.",
  party_exceeds_capacity: "That party is larger than these seats allow. Choose a bigger table or a joined pair.",
  combination_not_allowed: "Those tables can't be joined at this restaurant.",
  outside_opening_hours: "The restaurant isn't open for the whole booking at that time.",
  not_on_slot_grid: "That isn't one of the restaurant's start times.",
  invalid_local_time: "That time doesn't exist on this date (the clocks change).",
  idempotency_key_reuse: "This request clashed with an earlier one. Change a detail and book again.",
  unauthenticated: "Your sign-in is no longer valid. Please sign in again.",
  forbidden: "You can't change this booking.",
  not_found: "We couldn't find that.",
  validation_failed: "Something in the details isn't valid. Check and try again.",
  malformed_request: "The request couldn't be read. Try again.",
  email_taken: "That email already has an account. Sign in instead.",
  cutoff_passed: "It's too close to the booking time to change it online. Please call the restaurant.",
  reservation_cancelled: "This booking is already cancelled.",
};

export function plainError(result, fallback = "That didn't work. Please try again.") {
  if (!result) return fallback;
  return MESSAGES[result.code] || result.message || fallback;
}
