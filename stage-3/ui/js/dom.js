// Tiny DOM helpers and the inline icon set (drawn for this product; no external assets).

export function h(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props || {})) {
    if (value === undefined || value === null || value === false) continue;
    if (key === "class") node.className = value;
    else if (key === "testid") node.setAttribute("data-testid", value);
    else if (key === "style" && typeof value === "object") {
      for (const [prop, v] of Object.entries(value)) node.style.setProperty(prop, v);
    } else if (key.startsWith("on") && typeof value === "function") {
      node.addEventListener(key.slice(2).toLowerCase(), value);
    } else if (key === "html") node.innerHTML = value;
    else if (value === true) node.setAttribute(key, "");
    else node.setAttribute(key, String(value));
  }
  append(node, children);
  return node;
}

function append(node, children) {
  for (const child of children) {
    if (child === null || child === undefined || child === false) continue;
    if (Array.isArray(child)) append(node, child);
    else node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
}

export function clear(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
  return node;
}

export function announce(text) {
  const live = document.getElementById("announcer");
  if (!live) return;
  live.textContent = "";
  window.setTimeout(() => { live.textContent = text; }, 30);
}

const PATHS = {
  flame: '<path d="M12 2.5c2.9 3.6 4.2 6 4.2 8.3a4.2 4.2 0 0 1-8.4 0c0-1.3.5-2.6 1.4-3.9.3 1.2 1 2 1.9 2.3C10.6 7.2 11 5 12 2.5z" fill="currentColor"/><path d="M6 17.5h12M8 21h8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>',
  check: '<path d="M5 12.5l4.2 4.2L19 7" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>',
  blocked: '<circle cx="12" cy="12" r="8" fill="none" stroke="currentColor" stroke-width="2"/><path d="M6.5 17.5l11-11" stroke="currentColor" stroke-width="2"/>',
  small: '<path d="M4 12h16M8 8l-4 4 4 4M16 8l4 4-4 4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>',
  open: '<circle cx="12" cy="12" r="5" fill="currentColor"/>',
  link: '<path d="M9.5 14.5l5-5M8 11l-2 2a3.5 3.5 0 0 0 5 5l2-2M16 13l2-2a3.5 3.5 0 0 0-5-5l-2 2" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
  warn: '<path d="M12 3.5L2.8 19.5h18.4z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/><path d="M12 10v4.2M12 16.8v.2" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/>',
  question: '<circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="2" stroke-dasharray="3.2 2.4"/><path d="M9.6 9.4a2.5 2.5 0 1 1 3.4 2.3c-.7.3-1 .8-1 1.5v.6M12 16.8v.2" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
  close: '<path d="M6 6l12 12M18 6L6 18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
  copy: '<rect x="8" y="8" width="11" height="12" rx="2" fill="none" stroke="currentColor" stroke-width="2"/><path d="M5 15V6a2 2 0 0 1 2-2h8" fill="none" stroke="currentColor" stroke-width="2"/>',
  lantern: '<path d="M9 4h6M10 4v2M14 4v2M7.5 8.5h9l-1 10h-7z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/><path d="M12 11.3c1.2 1.4 1.6 2.3 1.6 3.1a1.6 1.6 0 0 1-3.2 0c0-.8.4-1.7 1.6-3.1z" fill="currentColor"/><path d="M7 20.5h10" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>',
  door: '<path d="M6 21V4h12v17M4 21h16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/><circle cx="14.5" cy="12.5" r="1.1" fill="currentColor"/>',
  key: '<circle cx="8" cy="14" r="4" fill="none" stroke="currentColor" stroke-width="2"/><path d="M11 11l8-8M16 6l2.5 2.5M14 8l2 2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
  clock: '<circle cx="12" cy="12" r="8.5" fill="none" stroke="currentColor" stroke-width="2"/><path d="M12 7.5V12l3 2" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
  ticket: '<path d="M3.5 7.5a2 2 0 0 0 0 4v5h17v-5a2 2 0 0 1 0-4v-3h-17z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/><path d="M14 5v12" stroke="currentColor" stroke-width="1.6" stroke-dasharray="2 2"/>',
};

export function icon(name, cls = "icon") {
  const span = document.createElement("span");
  span.innerHTML = `<svg class="${cls}" viewBox="0 0 24 24" aria-hidden="true" focusable="false">${PATHS[name] || ""}</svg>`;
  return span.firstChild;
}

export function notice(kind, title, body, extra = {}) {
  const icons = { refused: "warn", uncertain: "question", success: "check", info: "lantern" };
  return h("div", { class: `notice notice-${kind} fade-in`, role: kind === "info" ? "status" : "alert", ...extra },
    icon(icons[kind] || "lantern"),
    h("div", {}, h("strong", {}, title), body ? h("span", { class: "notice-body" }, body) : null));
}
