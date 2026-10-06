// Signup and login screens.
import { h, icon, announce } from "../dom.js";
import { api } from "../api.js";
import { session } from "../session.js";
import { navigate } from "../router.js";
import { plainError } from "../format.js";

function nextPath() {
  const next = new URLSearchParams(window.location.search).get("next") || "/";
  return next.startsWith("/") && !next.startsWith("//") ? next : "/";
}

function field(id, labelText, input, hint) {
  return h("div", { class: "field" },
    h("label", { for: id }, labelText), input,
    hint ? h("span", { class: "hint", id: `${id}-hint` }, hint) : null);
}

function authScreen(main, cfg) {
  const errorSlot = h("div", { class: "error-slot" });
  const submit = h("button", { class: "btn btn-primary", type: "submit", testid: cfg.submitId }, cfg.submitText);
  const form = h("form", { class: "stack", novalidate: true }, ...cfg.fields, errorSlot, submit);

  function showError(text) {
    errorSlot.replaceChildren(h("div", { class: "notice notice-refused fade-in", role: "alert", testid: "auth-error" },
      icon("warn"), h("div", {}, h("strong", {}, cfg.errorTitle), h("span", {}, text))));
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (submit.getAttribute("aria-busy") === "true") return;
    const problem = cfg.check();
    if (problem) { showError(problem); return; }
    errorSlot.replaceChildren();
    submit.setAttribute("aria-busy", "true");
    submit.textContent = cfg.busyText;
    const result = await cfg.send();
    submit.removeAttribute("aria-busy");
    submit.textContent = cfg.submitText;
    if (result.kind === "ok") {
      session.set(result.data);
      announce(`Signed in as ${result.data.display_name}`);
      navigate(nextPath());
    } else if (result.kind === "lost") {
      showError("We couldn't reach Tablekeeper. Check your connection and try again.");
    } else {
      showError(cfg.explain(result));
    }
  });

  main.append(h("div", { class: "page" },
    h("div", { class: "narrow" },
      h("section", { class: "card" },
        h("p", { class: "eyebrow" }, cfg.eyebrow),
        h("h1", {}, cfg.title),
        h("p", { class: "lede" }, cfg.lede),
        h("div", { style: { "margin-top": "var(--s5)" } }, form),
        h("p", { class: "form-foot", style: { "margin-top": "var(--s5)" } }, ...cfg.foot)))));
  const first = form.querySelector("input");
  if (first) first.focus({ preventScroll: true });
}

export function mountSignup(main) {
  const email = h("input", { class: "input", id: "su-email", type: "email", autocomplete: "email", required: true, testid: "signup-email" });
  const name = h("input", { class: "input", id: "su-name", type: "text", autocomplete: "name", required: true, testid: "signup-display-name" });
  const password = h("input", { class: "input", id: "su-password", type: "password", autocomplete: "new-password", required: true, minlength: "8", "aria-describedby": "su-password-hint", testid: "signup-password" });
  authScreen(main, {
    eyebrow: "New here",
    title: "Save a seat for yourself",
    lede: "One account keeps every booking and its reference in one place.",
    fields: [field("su-name", "Your name", name), field("su-email", "Email", email),
      field("su-password", "Password", password, "At least 8 characters.")],
    submitId: "signup-submit", submitText: "Create account", busyText: "Creating account…",
    errorTitle: "Account not created",
    check: () => {
      if (!name.value.trim()) return "Tell us your name so the restaurant knows who to expect.";
      if (!/^[^\s@]+@[^\s@]+$/.test(email.value.trim())) return "Enter an email like name@example.com.";
      if (password.value.length < 8) return "Your password needs at least 8 characters.";
      return null;
    },
    send: () => api.signup({ email: email.value.trim(), password: password.value, display_name: name.value.trim() }),
    explain: (r) => r.code === "email_taken" ? "That email already has an account. Sign in instead." : plainError(r),
    foot: ["Already have an account? ", h("a", { href: `/login${window.location.search}`, "data-link": true }, "Sign in")],
  });
}

export function mountLogin(main) {
  const email = h("input", { class: "input", id: "li-email", type: "email", autocomplete: "email", required: true, testid: "login-email" });
  const password = h("input", { class: "input", id: "li-password", type: "password", autocomplete: "current-password", required: true, testid: "login-password" });
  authScreen(main, {
    eyebrow: "Welcome back",
    title: "Sign in to book",
    lede: "Your table is a click away. Sign in to book and to look up your reservations.",
    fields: [field("li-email", "Email", email), field("li-password", "Password", password)],
    submitId: "login-submit", submitText: "Sign in", busyText: "Signing in…",
    errorTitle: "Not signed in",
    check: () => (!email.value.trim() || !password.value ? "Enter your email and password." : null),
    send: () => api.login({ email: email.value.trim(), password: password.value }),
    explain: (r) => r.code === "unauthenticated" ? "That email and password don't match an account." : plainError(r),
    foot: ["New to Tablekeeper? ", h("a", { href: `/signup${window.location.search}`, "data-link": true }, "Create an account")],
  });
}
