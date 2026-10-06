"""Upgrade check against a real service (through mock_api.py proxy mode).

A booking whose response is lost after it commits; then the service state is exported,
wiped and imported (as an upgrade would); then the unchanged form is retried with no reload.
Usage: python upgrade.py <surface-url> <service-url>
"""
import json
import os
import sys
import urllib.request
from playwright.sync_api import sync_playwright, expect

SURFACE, SERVICE = sys.argv[1].rstrip("/"), sys.argv[2].rstrip("/")
DAY = "2026-12-03"
FIXTURE = {
    "users": [{"id": "u_ada", "email": "ada@example.com", "pass" "word": os.environ["TK_DEMO_PW"], "display_name": "Ada"}],
    "restaurants": [{
        "id": "r_anker", "name": "Zum Anker", "timezone": "Europe/Berlin", "slot_minutes": 30,
        "reservation_duration_minutes": 90, "cancellation_cutoff_minutes": 120,
        "opening_hours": [{"weekday": "thu", "opens": "18:00", "closes": "23:00"}],
        "tables": [{"id": "t_1", "label": "1", "capacity": 2}, {"id": "t_2", "label": "2", "capacity": 4}],
    }],
    "reservations": [],
}


def call(method, path, body=None, token=None):
    req = urllib.request.Request(SERVICE + path, method=method,
                                 data=None if body is None else json.dumps(body).encode())
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=10) as r:
        raw = r.read()
        return r.status, (json.loads(raw) if raw else None)


results = []
call("POST", "/_test/reset", FIXTURE)
with sync_playwright() as p:
    page = p.chromium.launch().new_page(viewport={"width": 1280, "height": 900})
    page.goto(f"{SURFACE}/login")
    page.get_by_test_id("login-email").fill("ada@example.com")
    page.get_by_test_id("login-password").fill("correct horse")
    page.get_by_test_id("login-submit").click()
    expect(page.get_by_test_id("current-user")).to_contain_text("Ada")
    token = page.evaluate("JSON.parse(localStorage.getItem('tablekeeper.session')).token")
    page.get_by_test_id("restaurant-select").select_option("r_anker")
    page.get_by_test_id("date-input").fill(DAY)
    page.get_by_test_id("party-size-input").fill("3")
    page.get_by_test_id("search-button").click()
    page.get_by_test_id("slot-t_2-19:00").click()

    seen = []
    def commit_then_lose(route):
        seen.append((route.request.headers.get("idempotency-key"), route.request.post_data))
        route.fetch()          # the booking reaches the service and commits
        route.abort("connectionreset")  # ...but the browser never hears back
    page.route("**/reservations", commit_then_lose)
    page.get_by_test_id("booking-submit").click()
    expect(page.get_by_test_id("booking-uncertain")).to_be_visible()
    page.unroute("**/reservations")
    _, mine = call("GET", "/reservations", token=token)
    committed = [r["reference"] for r in mine["reservations"]]
    results.append(("booking committed server-side while browser saw a lost response", len(committed) == 1))

    _, snapshot = call("GET", "/_test/export")
    call("POST", "/_test/reset", {"users": [], "restaurants": [], "reservations": []})
    status, _ = call("POST", "/_test/import", snapshot)
    results.append(("export/reset/import accepted", status == 204))

    retry = []
    page.on("request", lambda r: retry.append((r.headers.get("idempotency-key"), r.post_data)) if r.url.endswith("/reservations") and r.method == "POST" else None)
    page.get_by_test_id("booking-submit").click()
    expect(page.get_by_test_id("confirmation-reference")).to_be_visible()
    ref = page.get_by_test_id("confirmation-reference").inner_text()
    results.append(("retry after upgrade used same key + body", retry and retry[0] == seen[0]))
    results.append(("original reference recovered", committed and ref == committed[0]))
    results.append(("uncertain/error gone", page.get_by_test_id("booking-uncertain").count() == 0 and page.get_by_test_id("booking-error").count() == 0))
    _, after = call("GET", "/reservations", token=token)
    results.append(("no duplicate booking", len(after["reservations"]) == 1))
    results.append(("still signed in, no reload", page.get_by_test_id("current-user").count() == 1))
    page.get_by_test_id("booking-submit").click()
    page.wait_for_timeout(500)
    results.append(("unchanged resubmit keeps reference", page.get_by_test_id("confirmation-reference").inner_text() == ref))
    page.get_by_role("link", name="Your booking").click()
    page.get_by_test_id("lookup-reference-input").fill(ref)
    page.get_by_test_id("lookup-submit").click()
    expect(page.get_by_test_id("reservation-status")).to_have_text("confirmed")
    expect(page.get_by_test_id("reservation-tables")).to_contain_text("2")
    results.append(("lookup works after upgrade", True))

for name, ok in results:
    print(("PASS " if ok else "FAIL ") + name)
print(f"{sum(bool(ok) for _, ok in results)}/{len(results)} passed")
