// Confirmation ticket: the reference large, a copy control, and the booking in words.
import { h, icon, announce } from "../dom.js";
import { longDate, tablesPhrase, guests, timeSpan } from "../format.js";

export function reservationTables(reservation, restaurant) {
  const ids = Array.isArray(reservation.table_ids) && reservation.table_ids.length
    ? reservation.table_ids
    : [reservation.table_id].filter(Boolean);
  const byId = new Map(((restaurant && restaurant.tables) || []).map((t) => [t.id, t]));
  return ids.map((id) => byId.get(id) || { id, label: id });
}

async function copyText(text) {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch (err) { /* fall through */ }
  const area = h("textarea", { "aria-hidden": "true", style: { position: "fixed", opacity: "0", top: "0", left: "0" } });
  area.value = text;
  document.body.append(area);
  area.select();
  let ok = false;
  try { ok = document.execCommand("copy"); } catch (err) { ok = false; }
  area.remove();
  return ok;
}

export function renderTicket(reservation, restaurant) {
  const tables = reservationTables(reservation, restaurant);
  const local = reservation.starts_at_local || "";
  const stateLine = h("span", { class: "copy-state", "aria-live": "polite" });
  const copy = h("button", {
    class: "btn btn-ghost btn-small", type: "button",
    "aria-label": `Copy reference ${reservation.reference}`,
    onclick: async () => {
      const ok = await copyText(reservation.reference);
      stateLine.textContent = ok ? "Copied" : "Select the reference to copy it";
      if (ok) announce("Reference copied");
    },
  }, icon("copy"), "Copy");

  return h("article", { class: "ticket fade-in", testid: "confirmation", "aria-label": "Booking confirmed" },
    h("div", { class: "ticket-top" }, icon("check"), "Booked · confirmed"),
    h("div", { class: "ticket-ref-wrap" },
      h("div", {},
        h("span", { class: "ticket-ref-label" }, "Your reference"),
        h("span", { class: "ticket-ref", testid: "confirmation-reference", style: { "--ref-len": String(String(reservation.reference).length) } }, reservation.reference)),
      h("div", {}, copy, stateLine)),
    h("div", { class: "ticket-tear", "aria-hidden": "true" }),
    h("div", { class: "ticket-details", testid: "confirmation-details" },
      h("span", { class: "d-name" }, restaurant.name),
      h("span", { class: "d-when" }, `${longDate(local.slice(0, 10))} · ${timeSpan(reservation)}`),
      h("span", { class: "d-tables", testid: "confirmation-tables" },
        `${tablesPhrase(tables)} · ${guests(reservation.party_size)}`)));
}
