// Client-side routing over the four screen routes. Links keep real hrefs.
const routes = new Map();
const changeListeners = new Set();
let cleanup = null;

export function route(path, view) {
  routes.set(path, view);
}

export function onRouteChange(fn) {
  changeListeners.add(fn);
}

export function currentPath() {
  const path = window.location.pathname.replace(/\/+$/, "");
  return path === "" ? "/" : path;
}

export function navigate(href, { replace = false } = {}) {
  const url = new URL(href, window.location.origin);
  if (url.pathname + url.search !== window.location.pathname + window.location.search) {
    window.history[replace ? "replaceState" : "pushState"]({}, "", url.pathname + url.search);
  }
  render();
}

export function render() {
  const main = document.getElementById("main");
  if (typeof cleanup === "function") cleanup();
  cleanup = null;
  main.replaceChildren();
  const path = currentPath();
  const view = routes.get(path) || routes.get("*");
  cleanup = view(main) || null;
  changeListeners.forEach((fn) => fn(path));
  window.scrollTo(0, 0);
}

export function startRouter() {
  window.addEventListener("popstate", render);
  document.addEventListener("click", (event) => {
    const link = event.target.closest("a[data-link]");
    if (!link || event.defaultPrevented || event.button !== 0) return;
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    navigate(link.getAttribute("href"));
  });
  render();
}
