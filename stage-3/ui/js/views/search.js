// Search screen: restaurant / date / party, the timetable, and the booking panel.
// Only the latest search may change what is shown; late answers are discarded.
import { h, icon, clear, notice, announce } from "../dom.js";
import { api } from "../api.js";
import { session } from "../session.js";
import { longDate, guests, todayLocal, plainError } from "../format.js";
import { renderTimetable, legend } from "./grid.js";
import { createBooking } from "./booking.js";

const state = {
  restaurants: null, restaurantsFailed: false,
  form: { restaurantId: "", date: todayLocal(), party: "2" },
  seq: 0, refreshSeq: 0, phase: "idle", result: null, error: null,
  booking: null, authNeeded: false,
};
let view = null;

function loadRestaurants() {
  state.restaurantsFailed = false;
  api.restaurants().then((r) => {
    if (r.kind === "ok") {
      state.restaurants = (r.data && r.data.restaurants) || [];
      if (!state.form.restaurantId && state.restaurants[0]) state.form.restaurantId = state.restaurants[0].id;
    } else state.restaurantsFailed = true;
    if (view) view.fillRestaurants();
  });
}

async function runSearch() {
  const { restaurantId, date } = state.form;
  const party = Number(state.form.party);
  const seq = ++state.seq;
  closeBooking();
  state.authNeeded = false;
  state.phase = "loading";
  state.pending = { name: nameOf(restaurantId), date, party };
  if (view) view.renderResults();
  const [details, avail] = await Promise.all([api.restaurant(restaurantId), api.availability(restaurantId, date, party)]);
  if (seq !== state.seq) return; // a newer search owns the screen
  if (details.kind !== "ok" || avail.kind !== "ok") {
    const failed = details.kind !== "ok" ? details : avail;
    state.phase = "error";
    state.error = failed.kind === "lost" ? "We couldn't reach Tablekeeper. Check your connection and search again." : plainError(failed);
  } else {
    state.phase = "ready";
    state.result = { restaurant: details.data, date, party, slots: (avail.data && avail.data.slots) || [] };
    const open = state.result.slots.filter((s) => (s.available_table_ids || []).length || (s.available_options || []).length).length;
    announce(state.result.slots.length ? `${open} of ${state.result.slots.length} times have a table` : "No times that day");
  }
  if (view) view.renderResults();
}

// After a refused booking: refresh the times in place, keep the booking panel and its inputs.
async function refreshAvailability() {
  const result = state.result;
  if (!result || state.phase !== "ready") return;
  const seq = state.seq;
  const mine = ++state.refreshSeq;
  if (view) view.markBusy(true);
  const avail = await api.availability(result.restaurant.id, result.date, result.party);
  if (seq !== state.seq || mine !== state.refreshSeq || result !== state.result) return;
  if (view) view.markBusy(false);
  if (avail.kind === "ok") {
    result.slots = (avail.data && avail.data.slots) || [];
    if (view) view.renderGrid();
  }
}

function nameOf(id) {
  const r = (state.restaurants || []).find((x) => x.id === id);
  return r ? r.name : "the restaurant";
}

function closeBooking() {
  if (state.booking) state.booking.el.remove();
  state.booking = null;
  document.body.classList.remove("sheet-open");
  if (view) view.renderGrid();
}

function pick(choice) {
  if (!session.get()) {
    state.authNeeded = true;
    if (view) { view.renderResults(); view.focusAuth(); }
    return;
  }
  state.authNeeded = false;
  if (state.booking && state.booking.key === choice.key) { state.booking.focus(); return; }
  if (state.booking) state.booking.el.remove();
  const { restaurant, date, party } = state.result;
  const booking = createBooking({
    restaurant, date, pick: choice, party,
    onConflict: () => { if (state.booking === booking) refreshAvailability(); },
    onClose: () => { if (state.booking !== booking) return; closeBooking(); if (view) view.renderResults(); },
  });
  state.booking = booking;
  if (view) { view.renderResults(); state.booking.focus(); }
  announce(`Booking ${state.booking.describe()}`);
}

export function mountSearch(main) {
  const select = h("select", { class: "select", id: "f-restaurant", testid: "restaurant-select" });
  const date = h("input", { class: "input", id: "f-date", type: "date", value: state.form.date, testid: "date-input" });
  const party = h("input", { class: "input", id: "f-party", type: "number", min: "1", step: "1", inputmode: "numeric", value: state.form.party, testid: "party-size-input" });
  const searchBtn = h("button", { class: "btn btn-primary", type: "submit", testid: "search-button" }, "Find a table");
  const formError = h("div", { class: "field-error" });
  const results = h("section", { class: "results", "aria-label": "Availability" });

  select.addEventListener("change", () => { state.form.restaurantId = select.value; });
  date.addEventListener("input", () => { state.form.date = date.value; });
  party.addEventListener("input", () => { state.form.party = party.value; });

  const form = h("form", { class: "search-card", role: "search", novalidate: true },
    h("div", { class: "field field-restaurant" }, h("label", { for: "f-restaurant" }, "Restaurant"), select),
    h("div", { class: "field" }, h("label", { for: "f-date" }, "Date"), date),
    h("div", { class: "field" }, h("label", { for: "f-party" }, "Party size"), party),
    h("div", { class: "search-actions" }, searchBtn),
    formError);

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    state.form = { restaurantId: select.value, date: date.value, party: party.value.trim() };
    const problems = [];
    if (!state.form.restaurantId) problems.push("Choose a restaurant.");
    if (!/^\d{4}-\d{2}-\d{2}$/.test(state.form.date)) problems.push("Choose a date.");
    if (!/^\d+$/.test(state.form.party) || Number(state.form.party) < 1) problems.push("Party size must be 1 or more.");
    party.setAttribute("aria-invalid", problems.some((p) => p.startsWith("Party")) ? "true" : "false");
    formError.replaceChildren(problems.length ? notice("refused", "Check your search", problems.join(" ")) : "");
    if (!problems.length) runSearch();
  });

  main.append(h("div", { class: "page" },
    h("div", { class: "search-hero" },
      h("div", {}, h("p", { class: "eyebrow" }, "Evening service"), h("h1", {}, "Find a table"),
        h("p", { class: "lede" }, "Pick a night and your party. Every table is drawn to size — joined tables seat larger groups."))),
    form, results));

  view = {
    fillRestaurants() {
      clear(select);
      if (state.restaurantsFailed) {
        select.append(h("option", { value: "" }, "Couldn't load restaurants"));
        formError.replaceChildren(notice("refused", "Restaurants unavailable", "We couldn't load the list. ",
          {}));
        formError.querySelector(".notice-body").append(h("button", { class: "btn btn-ghost btn-small", type: "button", onclick: () => { formError.replaceChildren(); loadRestaurants(); } }, "Try again"));
        return;
      }
      if (!state.restaurants) { select.append(h("option", { value: "" }, "Loading restaurants…")); return; }
      for (const r of state.restaurants) select.append(h("option", { value: r.id }, r.name));
      select.value = state.form.restaurantId;
    },
    markBusy(busy) {
      const grid = results.querySelector('[data-testid="availability-grid"]');
      if (grid) grid.setAttribute("aria-busy", busy ? "true" : "false");
    },
    focusAuth() {
      const n = results.querySelector('[data-testid="auth-error"]');
      if (n) { n.scrollIntoView({ block: "nearest" }); n.focus({ preventScroll: true }); }
    },
    renderGrid() {
      const col = results.querySelector(".grid-column");
      const r = state.result;
      if (!col || !r || state.phase !== "ready" || !r.slots.length) return;
      const grid = renderTimetable({ restaurant: r.restaurant, slots: r.slots, party: r.party,
        selectedKey: state.booking ? state.booking.key : null, onPick: pick });
      const old = col.querySelector('[data-testid="availability-grid"]');
      if (old) old.replaceWith(grid); else col.append(grid);
      positionPanel();
    },
    renderResults() { renderResults(results); },
  };
  view.fillRestaurants();
  if (!state.restaurants) loadRestaurants();
  view.renderResults();
  const onResize = () => positionPanel();
  window.addEventListener("resize", onResize);
  const unsub = session.subscribe(() => { if (state.authNeeded && session.get()) { state.authNeeded = false; view.renderResults(); } });
  return () => {
    view = null; unsub(); window.removeEventListener("resize", onResize);
    document.body.classList.remove("sheet-open");
  };
}

function positionPanel() {
  const panel = state.booking && state.booking.el;
  if (!panel || !panel.isConnected) return;
  const layout = panel.closest(".results-layout");
  const row = layout && layout.querySelector(".slot-row.is-chosen");
  const column = panel.parentElement;
  if (!row || window.innerWidth < 960) { column.style.removeProperty("--panel-offset"); return; }
  const top = row.getBoundingClientRect().top - layout.getBoundingClientRect().top;
  const room = layout.offsetHeight - panel.offsetHeight;
  column.style.setProperty("--panel-offset", `${Math.max(0, Math.min(top, room))}px`);
}

function renderResults(results) {
  clear(results);
  results.removeAttribute("aria-busy");
  if (state.phase === "idle") {
    results.append(h("div", { class: "state-panel" }, icon("lantern", "big-icon"),
      h("div", {}, h("h2", {}, "Where would you like to sit tonight?"),
        h("p", {}, "Choose a restaurant, a date and your party size, then find a table."))));
    return;
  }
  if (state.phase === "loading") {
    const p = state.pending;
    results.setAttribute("aria-busy", "true");
    const ghostRow = () => h("div", { class: "ghost-row", "aria-hidden": "true" }, h("div", { class: "ghost time" }),
      h("div", { class: "ghost-tiles" }, h("div", { class: "ghost", style: { width: "7rem" } }), h("div", { class: "ghost", style: { width: "10rem" } }), h("div", { class: "ghost", style: { width: "5.5rem" } })));
    results.append(h("div", { class: "state-panel loading", role: "status" }, icon("clock", "big-icon"),
      h("div", {}, h("h2", {}, "Checking tables…"), h("p", {}, `${p.name} · ${longDate(p.date)} · ${guests(p.party)}`))),
      h("div", { class: "timetable", style: { "margin-top": "var(--s4)" } }, ghostRow(), ghostRow(), ghostRow()));
    return;
  }
  if (state.phase === "error") {
    const retry = h("button", { class: "btn btn-ghost btn-small", type: "button", onclick: () => runSearch() }, "Search again");
    const n = notice("refused", "Search didn't finish", state.error);
    n.querySelector(".notice-body").append(" ", retry);
    results.append(n);
    return;
  }
  const r = state.result;
  if (!r.slots.length) {
    results.append(h("div", { class: "state-panel", testid: "no-slots", role: "status" }, icon("door", "big-icon"),
      h("div", {}, h("h2", {}, "No tables on this day"),
        h("p", {}, `${r.restaurant.name} has no start times on ${longDate(r.date)} — it may be closed. Try another date.`))));
    return;
  }
  if (state.authNeeded) {
    results.append(h("div", { class: "notice notice-refused fade-in", role: "alert", tabindex: "-1", testid: "auth-error" },
      icon("key"), h("div", {}, h("strong", {}, "Sign in to book"),
        h("span", {}, "Your seat is waiting. ", h("a", { href: "/login?next=/", "data-link": true }, "Sign in"), " or ",
          h("a", { href: "/signup?next=/", "data-link": true }, "create an account"), " — your search stays here."))));
  }
  const head = h("div", { class: "results-head" },
    h("div", {}, h("h2", {}, `${r.restaurant.name}`),
      h("p", { class: "meta" }, `${longDate(r.date)} · ${guests(r.party)} · times local to ${r.restaurant.timezone || "the restaurant"}`)),
    legend());
  const gridCol = h("div", { class: "grid-column" }, head);
  const layout = h("div", { class: `results-layout${state.booking ? " has-panel" : ""}`, style: { position: "relative" } }, gridCol);
  if (state.booking) {
    layout.append(h("div", { class: "panel-column" }, state.booking.el));
    document.body.classList.add("sheet-open");
  }
  results.append(layout);
  view.renderGrid();
}
