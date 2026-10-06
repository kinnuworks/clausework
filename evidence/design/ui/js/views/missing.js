// Fallback for an unknown client route.
import { h, icon } from "../dom.js";

export function mountMissing(main) {
  main.append(h("div", { class: "page" },
    h("div", { class: "state-panel" }, icon("door", "big-icon"),
      h("div", {}, h("h1", {}, "This page isn't on the menu"),
        h("p", {}, h("a", { href: "/", "data-link": true }, "Find a table"), " or ",
          h("a", { href: "/lookup", "data-link": true }, "look up your booking"), ".")))));
}
