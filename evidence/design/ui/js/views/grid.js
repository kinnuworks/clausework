// Availability timetable: one row per start time, one seating tile per table,
// one linked tile per approved pair. Tile width follows the seats it holds.
import { h, icon } from "../dom.js";
import { hhmm, tableName, tablesPhrase } from "../format.js";

const MAX_DOTS = 12;
// Seat-columns per time row (search.css must match): one column per seat, at least two.
const WIDE_COLUMNS = 8;
const PHONE_COLUMNS = 6;
const phoneQuery = window.matchMedia("(max-width: 560px)");
const spanOf = (capacity, columns) => Math.min(Math.max(capacity, 2), columns);

function sameSet(a, b) {
  return a.length === b.length && a.every((id) => b.includes(id));
}

// Seat counts the server itself reported for this search (available_options carry capacity).
function reportedCapacities(slots) {
  const caps = new Map();
  for (const slot of slots || []) {
    for (const o of slot.available_options || []) {
      if (Array.isArray(o.table_ids) && Number.isInteger(o.capacity)) caps.set([...o.table_ids].sort().join("+"), o.capacity);
    }
  }
  return caps;
}

// Every seating option to draw in each row: all single tables (fixture order), then declared
// pairs (combinable order) that are offered in any slot or whose combined seats fit the party.
export function seatingOptions(restaurant, party, slots = []) {
  const reported = reportedCapacities(slots);
  const capOf = (ids, fallback) => reported.get([...ids].sort().join("+")) ?? fallback;
  const byId = new Map((restaurant.tables || []).map((t) => [t.id, t]));
  const singles = (restaurant.tables || []).map((t) => ({ ids: [t.id], tables: [t], capacity: capOf([t.id], Number(t.capacity) || 0) }));
  const pairs = [];
  for (const pair of restaurant.combinable || []) {
    if (!Array.isArray(pair) || pair.length !== 2) continue;
    const tables = pair.map((id) => byId.get(id));
    if (tables.some((t) => !t)) continue;
    const key = [...pair].sort().join("+");
    const summed = pair.reduce((sum, id) => sum + capOf([id], Number(byId.get(id).capacity) || 0), 0);
    const capacity = capOf(pair, summed);
    if (reported.has(key) || capacity >= party) pairs.push({ ids: pair.slice(), tables, capacity });
  }
  return { singles, pairs, byId };
}

function optionAvailable(option, slot) {
  if (option.ids.length === 1) return (slot.available_table_ids || []).includes(option.ids[0]);
  return (slot.available_options || []).some((o) => Array.isArray(o.table_ids) && sameSet(o.table_ids, option.ids));
}

export function optionKey(ids, startsAtLocal) {
  return `${ids.join("+")}@${startsAtLocal}`;
}

function seats(capacity, cls = "seats") {
  const dots = [];
  for (let i = 0; i < Math.min(capacity, MAX_DOTS); i += 1) dots.push(h("span", { class: "seat" }));
  return h("span", { class: cls, "aria-hidden": "true" }, dots);
}

// "Table 2" on wide screens; the "Table" prefix folds away on phones, leaving "2".
function singleLabel(table) {
  const name = tableName(table);
  const label = String(table.label ?? table.id);
  return name === label ? [label] : [h("span", { class: "prefix" }, "Table "), label];
}

// Why an option is unavailable. With the server's explanation (explain=true) a booked
// member means "Taken" and a failed capacity rule means "Too small"; otherwise infer from seats.
function reasonFor(option, slot, party) {
  const rows = Array.isArray(slot.explain) ? slot.explain : null;
  if (rows) {
    const rules = option.ids.map((id) => rows.find((r) => r && r.table_id === id)).filter(Boolean);
    const holds = (name) => rules.every((r) => (r.rules || []).every((x) => x.rule !== name || x.holds));
    if (rules.length === option.ids.length) {
      if (!holds("no_overlap")) return "taken";
      if (option.ids.length === 1 && !holds("capacity")) return "small";
      if (option.ids.length === 2) return "small";
    }
  }
  return option.capacity < party ? "small" : "taken";
}

function statusOf(option, slot, available, chosen, party) {
  if (chosen) return { state: "chosen", word: "Chosen", icon: "check" };
  if (available) return { state: "open", word: "Open", icon: "open" };
  if (reasonFor(option, slot, party) === "small") return { state: "small", word: "Too small", icon: "small" };
  return { state: "taken", word: "Taken", icon: "blocked" };
}

function tile(option, slot, ctx) {
  const time = hhmm(slot.starts_at_local);
  const available = optionAvailable(option, slot);
  const key = optionKey(option.ids, slot.starts_at_local);
  const chosen = available && ctx.selectedKey === key;
  const st = statusOf(option, slot, available, chosen, ctx.party);
  const pair = option.ids.length === 2;
  const name = pair ? tablesPhrase(option.tables) : tableName(option.tables[0]);

  const label = pair
    ? h("span", { class: "pair-parts" },
        h("span", { class: "part" }, String(option.tables[0].label ?? option.ids[0])),
        icon("link", "link"),
        h("span", { class: "part" }, String(option.tables[1].label ?? option.ids[1])))
    : h("span", { class: "tile-label" }, ...singleLabel(option.tables[0]));

  const button = h("button", {
    type: "button",
    class: `tile${pair ? " tile-pair" : ""}`,
    testid: `slot-${option.ids.join("+")}-${time}`,
    "data-available": available ? "true" : "false",
    "data-state": st.state,
    "aria-pressed": available ? (chosen ? "true" : "false") : null,
    "aria-label": `${name}${pair ? ", joined" : ""}, ${option.capacity} seats, ${time}: ${st.word}`,
    style: { "--span": String(spanOf(option.capacity, WIDE_COLUMNS)), "--span-sm": String(spanOf(option.capacity, PHONE_COLUMNS)) },
    onclick: () => { if (available) ctx.onPick({ ids: option.ids, tables: option.tables, capacity: option.capacity, slot, key }); },
  },
    h("span", { class: "tile-top" }, label, h("span", { class: "count-text" }, `${option.capacity} seats`), seats(option.capacity, "seats seats-sm")),
    pair ? h("span", { class: "pair-note" }, "Joined tables") : null,
    h("span", { class: "tile-foot" },
      h("span", { class: "tile-status" }, icon(st.icon), h("span", { class: "word" }, st.word)),
      seats(option.capacity)));
  return { button, available };
}

// Packing order: first-fit decreasing into rows of `columns` seats, so no tile is stranded
// alone on a line. Applied to the DOM itself, so visual, reading and tab order agree.
function packOrder(options, columns) {
  const spans = options.map((o) => spanOf(o.capacity, columns));
  const byWidth = spans.map((span, i) => ({ span, i })).sort((a, b) => b.span - a.span || a.i - b.i);
  const rows = [];
  for (const item of byWidth) {
    const row = rows.find((r) => r.free >= item.span);
    if (row) { row.items.push(item.i); row.free -= item.span; } else rows.push({ free: columns - item.span, items: [item.i] });
  }
  rows.forEach((r) => r.items.sort((a, b) => a - b));
  rows.sort((a, b) => a.items[0] - b.items[0]);
  const order = new Array(options.length);
  rows.flatMap((r) => r.items).forEach((index, position) => { order[index] = position; });
  return order;
}

export function renderTimetable({ restaurant, slots, party, selectedKey, onPick }) {
  const { singles, pairs } = seatingOptions(restaurant, party, slots);
  const all = [...singles, ...pairs];
  const order = packOrder(all, phoneQuery.matches ? PHONE_COLUMNS : WIDE_COLUMNS);
  const options = all.map((option, i) => ({ option, at: order[i] })).sort((a, b) => a.at - b.at).map((x) => x.option);
  const rows = slots.map((slot) => {
    const tiles = options.map((option) => tile(option, slot, { party, selectedKey, onPick }));
    const open = tiles.filter((t) => t.available).length;
    const chosen = selectedKey && selectedKey.endsWith(`@${slot.starts_at_local}`);
    const time = hhmm(slot.starts_at_local);
    return h("div", {
      class: `slot-row${open === 0 ? " is-full" : ""}${chosen ? " is-chosen" : ""}`,
      role: "group", "aria-label": `${time}, ${open ? `${open} open` : "fully booked"}`,
      "data-time": time,
    },
      h("div", { class: "slot-time" },
        h("time", { datetime: slot.starts_at || slot.starts_at_local }, time),
        h("span", { class: "slot-count" }, open ? `${open} open` : "Fully booked")),
      h("div", { class: "tiles" }, tiles.map((t) => t.button)));
  });
  return h("div", { class: "timetable", testid: "availability-grid" }, rows);
}

// Re-pack when the layout crosses the phone breakpoint.
export function onLayoutChange(fn) {
  phoneQuery.addEventListener("change", fn);
  return () => phoneQuery.removeEventListener("change", fn);
}

export function legend() {
  const item = (cls, text) => h("li", {}, h("span", { class: `swatch ${cls}`, "aria-hidden": "true" }), text);
  return h("ul", { class: "legend", "aria-label": "Key" },
    item("", "Open — tap to book"), item("taken", "Taken or too small"),
    item("chosen", "Chosen"), item("pair", "Joined tables"));
}
