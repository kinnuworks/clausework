"""Inspector F1 smallest input: under a policy that raises capacities, the grid must draw every
pair /availability offers, with seat counts from the policy; a 1-seat table reads "1 seat".

Usage: TK_DEMO_PW=... python f1_check.py <service-url>   (resets the service itself)
"""
import json
import os
import sys
import urllib.request
from playwright.sync_api import sync_playwright

BASE = sys.argv[1].rstrip("/")
PW = os.environ["TK_DEMO_PW"]
FIXTURE = {
    "users": [{"id": "u_d", "email": "d@example.com", "pass" "word": PW, "display_name": "Dina"},
              {"id": "u_m", "email": "m@example.com", "pass" "word": PW, "display_name": "Max"}],
    "restaurants": [{"id": "r", "name": "Rand", "timezone": "Europe/Berlin", "slot_minutes": 30,
                     "reservation_duration_minutes": 90, "cancellation_cutoff_minutes": 120,
                     "opening_hours": [{"weekday": d, "opens": "17:00", "closes": "23:00"} for d in ("mon", "tue", "wed", "thu", "fri", "sat", "sun")],
                     "tables": [{"id": "t_1", "label": "Window", "capacity": 2}, {"id": "t_2", "label": "Bar", "capacity": 4},
                                {"id": "t_3", "label": "Nook", "capacity": 4}],
                     "combinable": [["t_2", "t_1"]], "manager_user_ids": ["u_m"]}],
    "reservations": []}
POLICY = {"effective_from": "2027-03-01", "slot_minutes": 45, "reservation_duration_minutes": 90,
          "cancellation_cutoff_minutes": 120,
          "opening_hours": [{"weekday": d, "opens": "17:00", "closes": "22:00"} for d in ("mon", "tue", "wed", "thu", "fri", "sat", "sun")],
          "capacities": {"t_1": 6, "t_2": 6, "t_3": 1}}


def call(method, path, body=None, headers=None):
    req = urllib.request.Request(BASE + path, method=method, data=None if body is None else json.dumps(body).encode())
    req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=10) as r:
        raw = r.read()
        return r.status, (json.loads(raw) if raw else None)


call("POST", "/_test/reset", FIXTURE)
_, m = call("POST", "/auth/login", {"email": "m@example.com", "pass" "word": PW})
call("POST", "/restaurants/r/policies", POLICY, {"Authorization": f"Bearer {m['token']}", "Idempotency-Key": "f1"})
results = []
with sync_playwright() as p:
    page = p.chromium.launch().new_page(viewport={"width": 1280, "height": 900})
    page.goto(BASE + "/")
    for party in (10, 5, 1):
        page.get_by_test_id("restaurant-select").select_option("r")
        page.get_by_test_id("date-input").fill("2027-03-05")
        page.get_by_test_id("party-size-input").fill(str(party))
        page.get_by_test_id("search-button").click()
        page.get_by_test_id("availability-grid").wait_for()
        _, avail = call("GET", f"/availability?restaurant_id=r&date=2027-03-05&party_size={party}")
        bad = 0
        for s in avail["slots"]:
            t = s["starts_at_local"][11:16]
            for tid in ("t_1", "t_2", "t_3"):
                bad += page.get_by_test_id(f"slot-{tid}-{t}").get_attribute("data-available") != ("true" if tid in s["available_table_ids"] else "false")
            for o in s["available_options"]:
                if len(o["table_ids"]) == 2:
                    cell = page.get_by_test_id(f"slot-{'+'.join(o['table_ids'])}-{t}")
                    bad += not (cell.count() == 1 and cell.get_attribute("data-available") == "true"
                                and f"{o['capacity']} seats" in cell.get_attribute("aria-label"))
        results.append((f"party {party}: grid matches /availability ({len(avail['slots'])} slots), 0 mismatches", bad == 0))
    nook = page.get_by_test_id("slot-t_3-17:00")
    results.append(("1-seat table reads '1 seat'", "1 seat," in nook.get_attribute("aria-label") and "1 seats" not in nook.inner_text()
                    and "1 seat" in nook.inner_text()))
for name, ok in results:
    print(("PASS " if ok else "FAIL ") + name)
print(f"{sum(bool(ok) for _, ok in results)}/{len(results)} passed")
