"""Stage-3 truth check: after a published policy, the grid, seat counts, ticket and lookup
must follow /availability and the booking's own terms, not the original restaurant detail.

Usage: TK_DEMO_PW=... python policy.py <service-url> <screens-dir>   (resets the service itself)
"""
import json
import os
import sys
import urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

BASE, OUT = sys.argv[1].rstrip("/"), Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
DAY, BEFORE = "2026-10-09", "2026-10-08"   # policy effective Friday 9 Oct; Thursday keeps policy 0
POLICY = {"effective_from": DAY, "slot_minutes": 45, "reservation_duration_minutes": 120,
          "cancellation_cutoff_minutes": 60,
          "opening_hours": [{"weekday": d, "opens": "17:00", "closes": "23:00"} for d in ("thu", "fri", "sat")],
          "capacities": {"t_1": 4, "t_2": 4, "t_3": 4, "t_4": 8, "t_5": 6}}
results = []


def call(method, path, body=None, headers=None):
    req = urllib.request.Request(BASE + path, method=method, data=None if body is None else json.dumps(body).encode())
    req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=10) as r:
        raw = r.read()
        return r.status, (json.loads(raw) if raw else None)


def fresh_state(width):
    fixture = json.loads((Path(__file__).parent / "fixture.json").read_text())
    for user in fixture["users"]:
        user.update({"pass" "word": os.environ["TK_DEMO_PW"]})
    call("POST", "/_test/reset", fixture)
    _, bob = call("POST", "/auth/login", {"email": "bob@example.com", "pass" "word": os.environ["TK_DEMO_PW"]})
    status, published = call("POST", "/restaurants/r_anker/policies", POLICY,
                             {"Authorization": f"Bearer {bob['token']}", "Idempotency-Key": "finisher-policy-1"})
    results.append((f"{width}: policy published", status == 201 and published.get("policy_version") == 1))


def grid_truth(page, party, day):
    _, avail = call("GET", f"/availability?restaurant_id=r_anker&date={day}&party_size={party}")
    times = [s["starts_at_local"][11:16] for s in avail["slots"]]
    shown = page.locator(".slot-row").evaluate_all("rows => rows.map(r => r.dataset.time)")
    ok_rows = shown == times
    ok_cells = True
    for s in avail["slots"]:
        t = s["starts_at_local"][11:16]
        for tid in ("t_1", "t_2", "t_3", "t_4", "t_5"):
            want = "true" if tid in s["available_table_ids"] else "false"
            ok_cells &= page.get_by_test_id(f"slot-{tid}-{t}").get_attribute("data-available") == want
        for o in s.get("available_options", []):
            if len(o["table_ids"]) == 2:
                cell = page.get_by_test_id(f"slot-{'+'.join(o['table_ids'])}-{t}")
                ok_cells &= cell.count() == 1 and cell.get_attribute("data-available") == "true"
    return ok_rows, ok_cells, times


def search(page, party, day):
    page.get_by_test_id("restaurant-select").select_option("r_anker")
    page.get_by_test_id("date-input").fill(day)
    page.get_by_test_id("party-size-input").fill(str(party))
    page.get_by_test_id("search-button").click()
    page.get_by_test_id("availability-grid").wait_for()


with sync_playwright() as p:
    browser = p.chromium.launch()
    for width in (375, 768, 1280):
        fresh_state(width)
        page = browser.new_page(viewport={"width": width, "height": 860 if width > 400 else 760})
        page.goto(f"{BASE}/login")
        page.get_by_test_id("login-email").fill("ada@example.com")
        page.get_by_test_id("login-password").fill(os.environ["TK_DEMO_PW"])
        page.get_by_test_id("login-submit").click()
        page.get_by_test_id("current-user").wait_for()

        search(page, 5, DAY)
        rows, cells, times = grid_truth(page, 5, DAY)
        results.append((f"{width}: rows follow policy slot grid {times}", rows))
        results.append((f"{width}: every cell matches /availability under policy", cells))
        t5 = page.get_by_test_id(f"slot-t_5-{times[0]}")
        results.append((f"{width}: t_5 seats from policy (6), open", t5.get_attribute("data-available") == "true"
                        and "6 seats" in t5.get_attribute("aria-label")))
        page.screenshot(path=str(OUT / f"{width}-21-policy-grid-party5.png"), full_page=True)

        search(page, 7, DAY)
        rows, cells, _ = grid_truth(page, 7, DAY)
        results.append((f"{width}: party 7 cells (pairs only fit under policy) match", rows and cells))
        pair = page.get_by_test_id(f"slot-t_1+t_2-{times[0]}")
        results.append((f"{width}: pair 1+2 shown as 8 seats", pair.count() == 1 and "8 seats" in pair.get_attribute("aria-label")))

        search(page, 2, BEFORE)
        rows, cells, before_times = grid_truth(page, 2, BEFORE)
        results.append((f"{width}: day before policy keeps policy 0 grid", rows and cells and before_times[0] == "18:00"))
        results.append((f"{width}: t_5 shows 2 seats before policy",
                        "2 seats" in page.get_by_test_id("slot-t_5-18:00").get_attribute("aria-label")))

        search(page, 5, DAY)
        slot = times[2]
        page.get_by_test_id(f"slot-t_5-{slot}").click()
        expect(page.get_by_test_id("booking-summary")).to_contain_text("6 seats")
        page.get_by_test_id("booking-submit").click()
        expect(page.get_by_test_id("confirmation-reference")).to_be_visible()
        ref = page.get_by_test_id("confirmation-reference").inner_text()
        h, m = map(int, slot.split(":"))
        end = f"{(h * 60 + m + 120) // 60:02d}:{(h * 60 + m + 120) % 60:02d}"
        details = page.get_by_test_id("confirmation-details").inner_text()
        results.append((f"{width}: ticket shows {slot}–{end} (policy duration 120)", f"{slot}–{end}" in details))
        page.screenshot(path=str(OUT / f"{width}-22-policy-ticket.png"))
        page.get_by_role("link", name="Your booking").click()
        page.get_by_test_id("lookup-reference-input").fill(ref)
        page.get_by_test_id("lookup-submit").click()
        expect(page.get_by_test_id("reservation-status")).to_have_text("confirmed")
        detail = page.get_by_test_id("reservation-detail").inner_text()
        results.append((f"{width}: lookup shows end time and accepted 1-hour cutoff", f"{slot}–{end}" in detail and "1 hour" in detail))
        page.screenshot(path=str(OUT / f"{width}-23-policy-lookup.png"), full_page=True)
        overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
        results.append((f"{width}: no sideways scroll", overflow <= 0))
        page.close()

for name, ok in results:
    print(("PASS " if ok else "FAIL ") + name)
print(f"{sum(bool(ok) for _, ok in results)}/{len(results)} passed")
