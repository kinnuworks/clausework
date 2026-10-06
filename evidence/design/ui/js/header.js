// Site header: brand, primary navigation and the signed-in diner — identical on every route.
import { h, icon, clear, announce } from "./dom.js";
import { session } from "./session.js";
import { currentPath, onRouteChange } from "./router.js";

function initials(name) {
  const parts = String(name || "?").trim().split(/\s+/).filter(Boolean);
  return ((parts[0] || "?")[0] + (parts.length > 1 ? parts[parts.length - 1][0] : "")).toUpperCase();
}

function navLink(href, text, path) {
  return h("a", { href, "data-link": true, "aria-current": path === href ? "page" : null }, text);
}

export function renderHeader() {
  const root = document.getElementById("site-header");
  const path = currentPath();
  const user = session.get();
  const account = user
    ? h("div", { class: "account" },
        h("span", { class: "current-user", testid: "current-user", title: `Signed in as ${user.display_name}` },
          h("span", { class: "avatar", "aria-hidden": "true" }, initials(user.display_name)),
          h("span", { class: "sr-only" }, "Signed in as "),
          user.display_name),
        h("button", {
          class: "btn btn-ghost btn-small", type: "button", testid: "logout-button",
          onclick: () => { session.clear(); announce("Signed out"); },
        }, "Sign out"))
    : h("div", { class: "account" },
        navLink("/login", "Sign in", path),
        h("a", { class: "btn btn-primary btn-small", href: "/signup", "data-link": true },
          h("span", { class: "label-long" }, "Create account"), h("span", { class: "label-short" }, "Sign up")));

  clear(root).append(
    h("div", { class: "header-inner" },
      h("a", { class: "brand", href: "/", "data-link": true, "aria-label": "Tablekeeper — find a table" },
        icon("flame", "flame"), "Tablekeeper"),
      h("nav", { class: "nav", "aria-label": "Main" },
        navLink("/", "Find a table", path),
        navLink("/lookup", "Your booking", path)),
      account));
}

export function startHeader() {
  session.subscribe(renderHeader);
  onRouteChange(renderHeader);
}
