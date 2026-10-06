'use strict';
// Time-zone arithmetic on top of the runtime's IANA database (Intl).
// Local wall-clock values are handled as "naive" millisecond counts: the UTC
// epoch value that the same wall-clock reading would have in UTC.

const MINUTE = 60000;
const DAY = 24 * 60 * MINUTE;
const WEEKDAYS = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat'];

const formatters = new Map();

function formatterFor(tz) {
  let f = formatters.get(tz);
  if (!f) {
    f = new Intl.DateTimeFormat('en-US', {
      timeZone: tz, hourCycle: 'h23',
      year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit', second: '2-digit',
    });
    formatters.set(tz, f);
  }
  return f;
}

function isValidTimeZone(tz) {
  if (typeof tz !== 'string' || tz.length === 0) return false;
  try {
    formatterFor(tz);
    return true;
  } catch {
    return false;
  }
}

// Offset of `tz` from UTC at instant `ms`, in minutes.
function offsetMinutes(tz, ms) {
  const whole = ms - (((ms % 1000) + 1000) % 1000);
  const parts = {};
  for (const p of formatterFor(tz).formatToParts(new Date(whole))) parts[p.type] = p.value;
  const asUtc = Date.UTC(+parts.year, +parts.month - 1, +parts.day, +parts.hour, +parts.minute, +parts.second);
  return Math.round((asUtc - whole) / MINUTE);
}

// Instant for a naive local value. Skipped (spring-forward) times give null;
// repeated (fall-back) times give the first occurrence.
function resolveLocal(tz, naive) {
  const offsets = new Set([naive - DAY, naive, naive + DAY].map((t) => offsetMinutes(tz, t)));
  let best = null;
  for (const off of offsets) {
    const t = naive - off * MINUTE;
    if (offsetMinutes(tz, t) === off && (best === null || t < best)) best = t;
  }
  return best;
}

// Like resolveLocal, but a skipped time maps to the instant the clock passed it.
function resolveLocalLenient(tz, naive) {
  const exact = resolveLocal(tz, naive);
  if (exact !== null) return exact;
  return naive - offsetMinutes(tz, naive - DAY) * MINUTE;
}

const pad = (n, w = 2) => String(n).padStart(w, '0');

function formatOffset(off) {
  const sign = off < 0 ? '-' : '+';
  const abs = Math.abs(off);
  return `${sign}${pad(Math.floor(abs / 60))}:${pad(abs % 60)}`;
}

// RFC 3339 rendering of instant `ms` in zone `tz`, with explicit offset.
function formatInstant(tz, ms) {
  const off = offsetMinutes(tz, ms);
  const d = new Date(ms + off * MINUTE);
  return `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())}` +
    `T${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}:${pad(d.getUTCSeconds())}${formatOffset(off)}`;
}

function formatUtc(ms) {
  return formatInstant('UTC', ms);
}

function formatNaiveMinute(naive) {
  const d = new Date(naive);
  return `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())}` +
    `T${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}`;
}

// "YYYY-MM-DD" -> naive midnight, or null when not a real calendar date.
function parseDate(text) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(text);
  if (!m) return null;
  const [y, mo, d] = [+m[1], +m[2], +m[3]];
  const naive = Date.UTC(y, mo - 1, d);
  const check = new Date(naive);
  if (check.getUTCFullYear() !== y || check.getUTCMonth() !== mo - 1 || check.getUTCDate() !== d) return null;
  return naive;
}

// "HH:MM" -> minutes after midnight, or null. `allowEndOfDay` admits "24:00".
function parseClock(text, allowEndOfDay = false) {
  if (typeof text !== 'string') return null;
  const m = /^(\d{2}):(\d{2})$/.exec(text);
  if (!m) return null;
  const minutes = +m[1] * 60 + +m[2];
  if (+m[2] > 59) return null;
  if (minutes < 24 * 60 || (allowEndOfDay && minutes === 24 * 60)) return minutes;
  return null;
}

// "YYYY-MM-DDTHH:MM" -> { dayNaive, minute } or null.
function parseLocalMinute(text) {
  if (typeof text !== 'string' || text.length !== 16 || text[10] !== 'T') return null;
  const dayNaive = parseDate(text.slice(0, 10));
  const minute = parseClock(text.slice(11));
  if (dayNaive === null || minute === null) return null;
  return { dayNaive, minute };
}

function weekdayOf(dayNaive) {
  return WEEKDAYS[new Date(dayNaive).getUTCDay()];
}

module.exports = {
  MINUTE, WEEKDAYS, isValidTimeZone, resolveLocal, resolveLocalLenient,
  formatInstant, formatUtc, formatNaiveMinute, parseDate, parseClock, parseLocalMinute, weekdayOf,
};
