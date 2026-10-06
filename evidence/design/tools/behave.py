"""Behaviour self-check of the surface against the stage-2 UI rules (mock API).

Usage: python behave.py <base-url>
"""
import json
import sys
from playwright.sync_api import sync_playwright, expect

BASE = sys.argv[1].rstrip("/")
DAY = "2026-10-08"
results = []


def check(name, cond):
    results.append((name, bool(cond)))


with sync_playwright() as p:
    page = p.chromium.launch().new_page(viewport={"width": 1280, "height": 900})
    page.goto(f"{BASE}/login")
    page.get_by_test_id("login-email").fill("ada@example.com")
    page.get_by_test_id("login-password").fill("correct horse")
    page.get_by_test_id("login-submit").click()
    expect(page.get_by_test_id("current-user")).to_contain_text("Ada Lovelace")
    check("redirected to / after login", page.url.rstrip("/") == BASE)

    # Out-of-order: search A (party 2) held, search B (party 6) answers first; A released late.
    held = []
    page.route("**/availability?*party_size=2*", lambda r: held.append(r))
    page.get_by_test_id("restaurant-select").select_option("r_anker")
    page.get_by_test_id("date-input").fill(DAY)
    page.get_by_test_id("party-size-input").fill("2")
    page.get_by_test_id("search-button").click()
    page.wait_for_timeout(200)
    page.get_by_test_id("party-size-input").fill("6")
    page.get_by_test_id("search-button").click()
    expect(page.get_by_test_id("slot-t_1+t_2-18:00")).to_be_visible()
    for r in held:
        r.continue_()
    page.unroute("**/availability?*party_size=2*")
    page.wait_for_timeout(600)
    check("late search A did not restore A (t_1 still unavailable for 6)",
          page.get_by_test_id("slot-t_1-18:00").get_attribute("data-available") == "false")
    check("pair cell present for B", page.get_by_test_id("slot-t_1+t_2-18:00").count() == 1)
    check("non-declared pair absent", page.get_by_test_id("slot-t_1+t_3-18:00").count() == 0)

    # Unavailable click does nothing.
    page.get_by_test_id("slot-t_1-18:00").click()
    check("unavailable click opens no form", page.get_by_test_id("booking-form").count() == 0)

    # Combination booking with lost response then retry (same key + body).
    keys, bodies = [], []
    def lose(route):
        keys.append(route.request.headers.get("idempotency-key")); bodies.append(route.request.post_data)
        route.continue_() if len(keys) > 1 else route.abort("connectionreset")
    page.route("**/reservations", lose)
    page.get_by_test_id("slot-t_1+t_2-18:00").click()
    expect(page.get_by_test_id("booking-summary")).to_contain_text("1")
    expect(page.get_by_test_id("booking-party-size")).to_have_value("6")
    page.get_by_test_id("booking-submit").click()
    expect(page.get_by_test_id("booking-uncertain")).to_be_visible()
    check("no error/confirmation while uncertain",
          page.get_by_test_id("booking-error").count() == 0 and page.get_by_test_id("confirmation").count() == 0)
    page.get_by_test_id("booking-submit").click()
    expect(page.get_by_test_id("confirmation-reference")).to_be_visible()
    check("retry used same key and body", len(keys) == 2 and keys[0] == keys[1] and bodies[0] == bodies[1])
    check("body uses table_ids for pair", json.loads(bodies[0]).get("table_ids") == ["t_1", "t_2"])
    check("uncertain removed after success", page.get_by_test_id("booking-uncertain").count() == 0)
    ref = page.get_by_test_id("confirmation-reference").inner_text()
    check("reference text exact", ref.isalnum() and ref.isupper())
    expect(page.get_by_test_id("confirmation-tables")).to_contain_text("1")
    expect(page.get_by_test_id("confirmation-tables")).to_contain_text("2")
    expect(page.get_by_test_id("confirmation-details")).to_contain_text("Zum Anker")
    expect(page.get_by_test_id("confirmation-details")).to_contain_text("18:00")

    # Unchanged resubmit -> same reference; changed field -> new key.
    page.get_by_test_id("booking-submit").click()
    page.wait_for_timeout(400)
    check("resubmit same reference", page.get_by_test_id("confirmation-reference").inner_text() == ref)
    check("resubmit same key", keys[-1] == keys[0])
    page.unroute("**/reservations")

    # 409: form and inputs preserved, availability refreshed, no confirmation.
    page.get_by_test_id("slot-t_2+t_3-19:00").count()
    page.get_by_test_id("party-size-input").fill("2")
    page.get_by_test_id("search-button").click()
    page.get_by_test_id("slot-t_3-19:00").click()
    page.get_by_test_id("booking-party-size").fill("3")
    avail_calls = []
    page.on("request", lambda r: avail_calls.append(r.url) if "/availability" in r.url else None)
    page.route("**/reservations", lambda r: r.fulfill(status=409, content_type="application/json",
               body='{"error":{"code":"table_unavailable","message":"x"}}'))
    page.get_by_test_id("booking-submit").click()
    expect(page.get_by_test_id("booking-error")).to_be_visible()
    page.wait_for_timeout(400)
    check("409 keeps form and input", page.get_by_test_id("booking-party-size").input_value() == "3")
    check("409 shows no confirmation", page.get_by_test_id("confirmation").count() == 0)
    check("409 refreshed availability", len(avail_calls) >= 1)
    page.unroute("**/reservations")

    # Lookup.
    page.goto(f"{BASE}/lookup")
    page.get_by_test_id("lookup-reference-input").fill(ref)
    page.get_by_test_id("lookup-submit").click()
    expect(page.get_by_test_id("reservation-status")).to_have_text("confirmed")
    expect(page.get_by_test_id("reservation-tables")).to_contain_text("2")
    page.get_by_test_id("reservation-cancel-button").click()
    expect(page.get_by_test_id("reservation-status")).to_have_text("cancelled")
    check("cancel button gone", page.get_by_test_id("reservation-cancel-button").count() == 0)
    page.get_by_test_id("logout-button").click()
    check("signed out hides current-user", page.get_by_test_id("current-user").count() == 0)
    for path in ("/", "/signup", "/login", "/lookup"):
        r = page.request.get(f"{BASE}{path}")
        check(f"{path} returns HTML", r.status == 200 and "text/html" in r.headers.get("content-type", ""))

for name, ok in results:
    print(("PASS " if ok else "FAIL ") + name)
print(f"{sum(ok for _, ok in results)}/{len(results)} passed")
