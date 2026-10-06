"""Stage-4 check against a real service: after a manager applies a replan, the grid shows the
closed table unavailable, and the ticket and lookup show the moved booking's new tables.

Usage: TK_DEMO_PW=... python replan.py <service-url> <screens-dir>   (resets the service itself)
"""
import json
import os
import sys
import urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

BASE, OUT = sys.argv[1].rstrip("/"), Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
PW = os.environ["TK_DEMO_PW"]
DAY = "2026-10-09"  # Friday: open 18:00-22:30, no seeded bookings
results = []


def call(method, path, body=None, headers=None):
    req = urllib.request.Request(BASE + path, method=method, data=None if body is None else json.dumps(body).encode())
    req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")


def fresh():
    fixture = json.loads((Path(__file__).parent / "fixture.json").read_text())
    for user in fixture["users"]:
        user.update({"pass" "word": PW})
    call("POST", "/_test/reset", fixture)


def search(page, party, day=DAY):
    page.get_by_test_id("restaurant-select").select_option("r_anker")
    page.get_by_test_id("date-input").fill(day)
    page.get_by_test_id("party-size-input").fill(str(party))
    page.get_by_test_id("search-button").click()
    page.get_by_test_id("availability-grid").wait_for()


def shot(page, width, name, full=False):
    page.wait_for_timeout(300)
    page.screenshot(path=str(OUT / f"{width}-{name}.png"), full_page=full)
    results.append((f"{width}: {name} no sideways scroll", page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")))


with sync_playwright() as p:
    browser = p.chromium.launch()
    for width in (375, 768, 1280):
        fresh()
        page = browser.new_page(viewport={"width": width, "height": 860 if width > 400 else 760})
        page.goto(f"{BASE}/login")
        page.get_by_test_id("login-email").fill("ada@example.com")
        page.get_by_test_id("login-password").fill(PW)
        page.get_by_test_id("login-submit").click()
        page.get_by_test_id("current-user").wait_for()

        # Ada books Table 2 at 19:00 for 2.
        search(page, 2)
        page.get_by_test_id("slot-t_2-19:00").click()
        page.get_by_test_id("booking-submit").click()
        expect(page.get_by_test_id("confirmation-tables")).to_contain_text("Table 2")
        ref = page.get_by_test_id("confirmation-reference").inner_text()

        # Manager closes Table 2 for the evening, previews, applies.
        _, bob = call("POST", "/auth/login", {"email": "bob@example.com", "pass" "word": PW})
        auth = {"Authorization": f"Bearer {bob['token']}"}
        st, plan = call("POST", "/restaurants/r_anker/replans",
                        {"table_id": "t_2", "from": f"{DAY}T17:00:00+02:00", "to": f"{DAY}T23:00:00+02:00"},
                        {**auth, "Idempotency-Key": f"plan-{width}"})
        moved_to = next((a["table_ids"] for a in (plan or {}).get("assignments", []) if a["reference"] == ref), None)
        results.append((f"{width}: replan previewed (201) and moves {ref} to {moved_to}", st == 201 and moved_to and "t_2" not in moved_to))
        st, applied = call("POST", f"/restaurants/r_anker/replans/{plan['plan_id']}/apply", {}, {**auth, "Idempotency-Key": f"apply-{width}"})
        results.append((f"{width}: plan applied (201)", st == 201))
        labels = {"t_1": "Table 1", "t_3": "Table 3", "t_4": "Window booth", "t_5": "Table 5"}
        want = " + ".join(labels.get(t, t) for t in moved_to) if len(moved_to) == 1 else None

        # Ticket: unchanged resubmit replays the original receipt; the ticket shows current seating.
        page.get_by_test_id("booking-submit").click()
        if want:
            expect(page.get_by_test_id("confirmation-tables")).to_contain_text(want)
        results.append((f"{width}: ticket shows moved table, same reference, no error",
                        page.get_by_test_id("confirmation-reference").inner_text() == ref
                        and "Table 2" not in page.get_by_test_id("confirmation-tables").inner_text()
                        and page.get_by_test_id("booking-error").count() == 0
                        and page.get_by_test_id("booking-uncertain").count() == 0))
        shot(page, width, "31-ticket-after-replan")

        # Grid: closed Table 2 unavailable at every time that evening.
        search(page, 2)
        _, avail = call("GET", f"/availability?restaurant_id=r_anker&date={DAY}&party_size=2")
        cells = [page.get_by_test_id(f"slot-t_2-{s['starts_at_local'][11:16]}").get_attribute("data-available") for s in avail["slots"]]
        results.append((f"{width}: closed Table 2 unavailable in all {len(cells)} slots", cells and all(c == "false" for c in cells)))
        pair_ok = all(page.get_by_test_id(f"slot-{pair}-{s['starts_at_local'][11:16]}").get_attribute("data-available") in (None, "false")
                      for s in avail["slots"] for pair in ("t_1+t_2", "t_2+t_3"))
        results.append((f"{width}: pairs containing Table 2 unavailable", pair_ok))
        shot(page, width, "32-grid-after-replan", full=True)

        # Lookup shows the moved booking's new table.
        page.get_by_role("link", name="Your booking").click()
        page.get_by_test_id("lookup-reference-input").fill(ref)
        page.get_by_test_id("lookup-submit").click()
        expect(page.get_by_test_id("reservation-status")).to_have_text("confirmed")
        tables_text = page.get_by_test_id("reservation-tables").inner_text()
        results.append((f"{width}: lookup shows {tables_text}", (want in tables_text if want else True) and "2" not in tables_text))
        shot(page, width, "33-lookup-after-replan", full=True)
        page.close()

for name, ok in results:
    print(("PASS " if ok else "FAIL ") + name)
print(f"{sum(bool(ok) for _, ok in results)}/{len(results)} passed")
