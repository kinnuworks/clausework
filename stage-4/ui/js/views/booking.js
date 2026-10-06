// Booking panel: summary, party size, submit, outcome, ticket.
// The outcome shown always comes from the server's answer. A lost answer leaves the
// attempt (idempotency key + exact body) in place so the unchanged form retries safely.
import { h, icon, notice, announce } from "../dom.js";
import { api, newKey } from "../api.js";
import { session } from "../session.js";
import { hhmm, shortDate, longDate, tablesPhrase, plainError, seatCount } from "../format.js";
import { renderTicket, reservationTables } from "./ticket.js";

export function createBooking({ restaurant, date, pick, party, onConflict, onClose }) {
  const state = { attempt: null, status: "idle", confirmation: null, error: null };
  const time = hhmm(pick.slot.starts_at_local);
  const tablesText = tablesPhrase(pick.tables);

  const partyInput = h("input", {
    class: "input", id: "booking-party", type: "number", min: "1", step: "1", inputmode: "numeric",
    value: String(party), testid: "booking-party-size",
  });
  const outcome = h("div", { class: "outcome", "aria-live": "polite" });
  const submit = h("button", { class: "btn btn-primary", type: "submit", testid: "booking-submit" }, "Book this table");
  const ticketSlot = h("div", {});
  const heading = h("h2", { tabindex: "-1" }, pick.ids.length > 1 ? "Joined tables" : "Your table");

  const form = h("form", { class: "booking-form", testid: "booking-form", novalidate: true },
    h("div", { class: "summary", testid: "booking-summary" },
      h("span", { class: "summary-time" }, time),
      h("span", { class: "summary-line" }, `${tablesText} · ${seatCount(pick.capacity)}`),
      h("span", { class: "summary-meta" }, `${restaurant.name} · ${shortDate(date)} · ${time}`)),
    h("div", { class: "row" },
      h("div", { class: "field" }, h("label", { for: "booking-party" }, "Party size"), partyInput),
      h("p", { class: "fine" }, pick.ids.length > 1
        ? "Both tables are held together for your whole booking."
        : `Seats up to ${pick.capacity}.`)),
    outcome,
    submit);

  const panel = h("section", { class: "booking-panel", "aria-label": "Book a table" },
    h("div", { class: "panel-grip", "aria-hidden": "true" }),
    h("div", { class: "panel-head" },
      h("div", {}, h("p", { class: "eyebrow" }, "Book"), heading),
      h("button", { class: "panel-close", type: "button", "aria-label": "Close booking panel", onclick: () => onClose() }, icon("close"))),
    h("div", { class: "panel-body" }, ticketSlot, form));

  panel.addEventListener("keydown", (event) => { if (event.key === "Escape") onClose(); });

  function body() {
    const raw = partyInput.value.trim();
    const size = /^\d+$/.test(raw) ? Number(raw) : NaN;
    const payload = { restaurant_id: restaurant.id };
    if (pick.ids.length === 1) payload.table_id = pick.ids[0];
    else payload.table_ids = pick.ids.slice();
    payload.starts_at_local = pick.slot.starts_at_local;
    payload.party_size = size;
    return { size, text: JSON.stringify(payload) };
  }

  function labelSubmit() {
    const unchanged = state.attempt && state.attempt.text === body().text;
    if (state.status === "sending") submit.textContent = "Booking…";
    else if (state.status === "uncertain" && unchanged) submit.textContent = "Check & retry booking";
    else if (state.status === "success" && unchanged) submit.textContent = "Book again (same booking)";
    else submit.textContent = pick.ids.length > 1 ? "Book these tables" : "Book this table";
  }

  function render() {
    outcome.replaceChildren();
    if (state.status === "refused") {
      outcome.append(notice("refused", "Not booked", state.error, { testid: "booking-error" }));
    } else if (state.status === "uncertain") {
      outcome.append(notice("uncertain", "Outcome unknown",
        "We didn't hear back, so this booking may or may not have gone through. Press the button again — it resends the very same request, so you can't end up booked twice.",
        { testid: "booking-uncertain" }));
    }
    ticketSlot.replaceChildren();
    if (state.confirmation && (state.status === "success" || state.status === "sending")) {
      if (state.seatingNote) ticketSlot.append(notice("info", "Seating changed", state.seatingNote));
      ticketSlot.append(renderTicket(state.confirmation, restaurant));
      if (state.status === "success") panel.scrollTop = 0;
    }
    if (state.status === "sending") submit.setAttribute("aria-busy", "true");
    else submit.removeAttribute("aria-busy");
    labelSubmit();
  }

  // A replay returns the original receipt, but seating may have changed since (a manager's
  // replan, an amendment). Read the booking's current state from the server for the ticket;
  // the reference never changes. If the read fails, the receipt stays as the server sent it.
  async function refreshTicket(reference) {
    const current = await api.reservation(reference);
    if (current.kind !== "ok" || !current.data || state.status !== "success") return;
    if (!state.confirmation || state.confirmation.reference !== reference) return;
    state.confirmation = { ...state.confirmation, ...current.data, reference };
    const now = reservationTables(state.confirmation, restaurant).map((t) => t.id);
    const moved = now.length > 0 && (now.length !== pick.ids.length || now.some((id) => !pick.ids.includes(id)));
    state.seatingNote = moved ? `The restaurant has since moved this booking to ${tablesPhrase(reservationTables(state.confirmation, restaurant))}.` : null;
    render();
    if (moved) onConflict();   // refresh the times so the grid shows today's seating
  }

  function refuse(text) {
    state.status = "refused"; state.error = text; state.confirmation = null;
    render();
    announce(`Not booked. ${text}`);
  }

  partyInput.addEventListener("input", labelSubmit);

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (state.status === "sending") return;
    const { size, text } = body();
    if (!Number.isInteger(size) || size < 1) { refuse("Enter a party size of 1 or more."); partyInput.focus(); return; }
    if (!session.get()) { refuse("Sign in or create an account to book."); return; }
    if (!state.attempt || state.attempt.text !== text) {
      state.attempt = { key: newKey(), text };
      state.confirmation = null;
      state.seatingNote = null;
    }
    const attempt = state.attempt;
    state.status = "sending"; state.error = null;
    render();
    const result = await api.book(attempt.text, attempt.key);
    if (result.kind === "ok") {
      state.status = "success"; state.confirmation = result.data;
      render();
      announce(`Booked. Reference ${result.data.reference}.`);
      refreshTicket(result.data.reference);
    } else if (result.kind === "lost") {
      state.status = "uncertain"; state.confirmation = null;
      render();
      announce("Outcome unknown. You can safely try again.");
    } else {
      refuse(plainError(result));
      if (result.code === "table_unavailable") onConflict();
    }
  });

  render();
  return {
    el: panel,
    key: pick.key,
    focus() { heading.focus({ preventScroll: true }); },
    describe() { return `${tablesText} at ${time} on ${longDate(date)}`; },
  };
}
