"""Stage-4 look-ahead: the ticket and lookup must show the server's current seating after a
replan moves a booking. Simulated by routing GET /reservations/{ref} to a moved body.

Usage: python replan_sim.py <base-url>  (mock_api.py or a real service seeded with fixture.json)
"""
import json
import sys
from playwright.sync_api import sync_playwright, expect

BASE = sys.argv[1].rstrip("/")
results = []
with sync_playwright() as p:
    page = p.chromium.launch().new_page(viewport={"width": 1280, "height": 900})
    page.goto(f"{BASE}/login")
    page.get_by_test_id("login-email").fill("ada@example.com")
    page.get_by_test_id("login-password").fill("correct horse")
    page.get_by_test_id("login-submit").click()
    page.get_by_test_id("current-user").wait_for()
    page.get_by_test_id("restaurant-select").select_option("r_anker")
    page.get_by_test_id("date-input").fill("2026-10-08")
    page.get_by_test_id("party-size-input").fill("2")
    page.get_by_test_id("search-button").click()
    page.get_by_test_id("slot-t_2-18:00").click()
    page.get_by_test_id("booking-submit").click()
    expect(page.get_by_test_id("confirmation-tables")).to_contain_text("Table 2")
    ref = page.get_by_test_id("confirmation-reference").inner_text()

    def moved(route):
        resp = route.fetch()
        body = resp.json()
        body.update({"table_ids": ["t_3"], "table_id": "t_3", "revision": 2})
        route.fulfill(response=resp, body=json.dumps(body))
    page.route(f"**/reservations/{ref}", moved)
    page.get_by_test_id("booking-submit").click()   # replay: server returns the original receipt (Table 2)
    expect(page.get_by_test_id("confirmation-tables")).to_contain_text("Table 3")
    results.append(("ticket shows current seating after replay", True))
    results.append(("reference unchanged", page.get_by_test_id("confirmation-reference").inner_text() == ref))
    results.append(("no error / uncertain", page.get_by_test_id("booking-error").count() == 0
                    and page.get_by_test_id("booking-uncertain").count() == 0))
    page.get_by_role("link", name="Your booking").click()
    page.get_by_test_id("lookup-reference-input").fill(ref)
    page.get_by_test_id("lookup-submit").click()
    expect(page.get_by_test_id("reservation-tables")).to_contain_text("3")
    results.append(("lookup shows moved table", "2" not in page.get_by_test_id("reservation-tables").inner_text()))
for name, ok in results:
    print(("PASS " if ok else "FAIL ") + name)
print(f"{sum(bool(ok) for _, ok in results)}/{len(results)} passed")
