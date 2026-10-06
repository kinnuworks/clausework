// Lookup screen: find a booking by reference, see it in words, cancel it.
import { h, icon, notice, announce } from "../dom.js";
import { api } from "../api.js";
import { session } from "../session.js";
import { hhmm, longDate, tablesPhrase, guests, plainError } from "../format.js";
import { reservationTables } from "./ticket.js";

const restaurantCache = new Map();

async function restaurantFor(id) {
  if (restaurantCache.has(id)) return restaurantCache.get(id);
  const r = await api.restaurant(id);
  if (r.kind !== "ok") return { id, name: "Restaurant", tables: [] };
  restaurantCache.set(id, r.data);
  return r.data;
}

export function mountLookup(main) {
  let seq = 0;
  const input = h("input", {
    class: "input ref-input", id: "lookup-ref", type: "text", autocomplete: "off", spellcheck: "false",
    autocapitalize: "characters", placeholder: "e.g. K3P7QW", testid: "lookup-reference-input",
  });
  const submit = h("button", { class: "btn btn-primary", type: "submit", testid: "lookup-submit" }, "Find booking");
  const out = h("div", { class: "lookup-result", "aria-live": "polite" });
  const form = h("form", { class: "lookup-form", novalidate: true },
    h("div", { class: "field" }, h("label", { for: "lookup-ref" }, "Booking reference"), input), submit);

  function showError(title, text) {
    out.replaceChildren(notice("refused", title, text, { testid: "reservation-error" }));
  }

  function renderDetail(res, restaurant, problem) {
    const cancelled = res.status === "cancelled";
    const tables = reservationTables(res, restaurant);
    const local = res.starts_at_local || "";
    const actions = h("div", { class: "res-actions" });
    if (!cancelled) {
      const cancelBtn = h("button", { class: "btn btn-danger", type: "button", testid: "reservation-cancel-button" }, "Cancel booking");
      cancelBtn.addEventListener("click", async () => {
        if (cancelBtn.getAttribute("aria-busy") === "true") return;
        cancelBtn.setAttribute("aria-busy", "true");
        cancelBtn.textContent = "Cancelling…";
        const r = await api.cancel(res.reference);
        if (!cancelBtn.isConnected) return;
        if (r.kind === "ok") {
          announce("Booking cancelled");
          renderDetail({ ...res, ...r.data }, restaurant, null);
        } else {
          const text = r.kind === "lost"
            ? "We couldn't hear back. Look the booking up again to see whether it was cancelled."
            : plainError(r);
          renderDetail(res, restaurant, text);
        }
      });
      actions.append(cancelBtn, h("span", { class: "fine" }, "Free cancellation until the restaurant's cut-off before your time."));
    } else {
      actions.append(h("span", { class: "fine" }, "This booking is cancelled. The table has been released."));
    }

    const card = h("article", { class: `res-card fade-in${cancelled ? " is-cancelled" : ""}`, testid: "reservation-detail" },
      h("div", { class: "res-top" },
        h("div", {}, h("p", { class: "eyebrow" }, "Reference"), h("p", { class: "res-ref" }, res.reference)),
        h("span", { class: `status-pill ${cancelled ? "cancelled" : "confirmed"}` },
          icon(cancelled ? "blocked" : "check"),
          h("span", { testid: "reservation-status" }, cancelled ? "cancelled" : "confirmed"))),
      h("dl", { class: "res-facts" },
        h("div", {}, h("dt", {}, "Restaurant"), h("dd", {}, restaurant.name)),
        h("div", {}, h("dt", {}, "When"), h("dd", {}, h("span", { class: "time-big" }, hhmm(local)), h("br"), longDate(local.slice(0, 10)))),
        h("div", {}, h("dt", {}, "Seating"), h("dd", { testid: "reservation-tables" }, tablesPhrase(tables))),
        h("div", {}, h("dt", {}, "Party"), h("dd", {}, guests(res.party_size)))),
      actions);
    out.replaceChildren(card);
    if (problem) out.append(notice("refused", "Not cancelled", problem, { testid: "reservation-error" }));
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const ref = input.value.trim().toUpperCase();
    if (!ref) { showError("Enter a reference", "Your reference is on your confirmation, e.g. K3P7QW."); return; }
    if (!session.get()) {
      out.replaceChildren(h("div", { class: "notice notice-refused fade-in", role: "alert", testid: "auth-error" },
        icon("key"), h("div", {}, h("strong", {}, "Sign in to see your booking"),
          h("span", {}, "Bookings are private. ", h("a", { href: "/login?next=/lookup", "data-link": true }, "Sign in"), " with the account you booked with."))));
      return;
    }
    const mine = ++seq;
    submit.setAttribute("aria-busy", "true");
    submit.textContent = "Looking…";
    const r = await api.reservation(ref);
    const restaurant = r.kind === "ok" ? await restaurantFor(r.data.restaurant_id) : null;
    if (mine !== seq || !out.isConnected) return;
    submit.removeAttribute("aria-busy");
    submit.textContent = "Find booking";
    if (r.kind === "ok") renderDetail(r.data, restaurant, null);
    else if (r.kind === "lost") showError("Lookup didn't finish", "We couldn't reach Tablekeeper. Try again.");
    else if (r.code === "not_found") showError("No booking found", `We couldn't find ${ref} on your account. Check the reference and try again.`);
    else showError("Lookup failed", plainError(r));
  });

  const signedOut = !session.get();
  main.append(h("div", { class: "page" },
    h("div", { class: "narrow", style: { "max-width": "40rem" } },
      h("section", { class: "card" },
        h("p", { class: "eyebrow" }, "Your booking"),
        h("h1", {}, "Look up a reservation"),
        h("p", { class: "lede" }, "Enter the reference from your confirmation to see or cancel the booking."),
        signedOut ? h("p", { class: "auth-aside" }, icon("key"), "You'll need to be signed in with the account you booked with.") : null,
        h("div", { style: { "margin-top": "var(--s5)" } }, form),
        out))));
}
