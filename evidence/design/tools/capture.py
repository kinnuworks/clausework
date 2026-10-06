"""Capture every screen state at 375 / 768 / 1280 px and check for sideways scrolling.

Usage: python capture.py <base-url> <out-dir>
Failure states are produced with Playwright request routing (lost response, 409, slow search).
"""
import json
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = sys.argv[1].rstrip("/")
OUT = Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
WIDTHS = [375, 768, 1280]
DAY, MONDAY = "2026-10-08", "2026-10-12"
REPORT = []


def shot(page, width, name, full=True):
    page.wait_for_timeout(250)
    overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
    path = OUT / f"{width}-{name}.png"
    page.screenshot(path=str(path), full_page=full)
    REPORT.append({"width": width, "screen": name, "sideways_overflow_px": overflow})


def search(page, party="2", day=DAY):
    page.get_by_test_id("restaurant-select").select_option("r_anker")
    page.get_by_test_id("date-input").fill(day)
    page.get_by_test_id("party-size-input").fill(party)
    page.get_by_test_id("search-button").click()


def sign_in(page):
    page.goto(f"{BASE}/login")
    page.get_by_test_id("login-email").fill("ada@example.com")
    page.get_by_test_id("login-password").fill("correct horse")
    page.get_by_test_id("login-submit").click()
    page.get_by_test_id("current-user").wait_for()


def run(width, browser):
    ctx = browser.new_context(viewport={"width": width, "height": 860 if width > 400 else 760})
    page = ctx.new_page()
    page.goto(f"{BASE}/")
    page.get_by_test_id("restaurant-select").locator("option[value=r_anker]").wait_for(state="attached")
    shot(page, width, "01-search-empty")

    held = []
    page.route("**/availability?*", lambda route: held.append(route))
    search(page)
    page.wait_for_timeout(300)
    shot(page, width, "02-search-loading", full=False)
    for route in held:
        route.continue_()
    page.unroute("**/availability?*")
    page.get_by_test_id("availability-grid").wait_for()
    shot(page, width, "03-grid-signed-out")
    page.get_by_test_id("slot-t_3-18:00").click()
    page.get_by_test_id("auth-error").wait_for()
    shot(page, width, "04-grid-auth-needed", full=False)

    search(page, day=MONDAY)
    page.get_by_test_id("no-slots").wait_for()
    shot(page, width, "05-no-slots")

    page.goto(f"{BASE}/signup")
    shot(page, width, "06-signup")
    page.goto(f"{BASE}/login")
    page.get_by_test_id("login-email").fill("ada@example.com")
    page.get_by_test_id("login-password").fill("wrong password")
    page.get_by_test_id("login-submit").click()
    page.get_by_test_id("auth-error").wait_for()
    shot(page, width, "07-login-error")

    sign_in(page)
    search(page)
    page.get_by_test_id("slot-t_3-19:00").click()
    page.get_by_test_id("booking-form").wait_for()
    shot(page, width, "08-booking-chosen", full=False)

    page.route("**/reservations", lambda route: route.abort("connectionreset"))
    page.get_by_test_id("booking-submit").click()
    page.get_by_test_id("booking-uncertain").wait_for()
    shot(page, width, "09-booking-uncertain", full=False)
    page.unroute("**/reservations")
    page.get_by_test_id("booking-submit").click()
    page.get_by_test_id("confirmation-reference").wait_for()
    ref = page.get_by_test_id("confirmation-reference").inner_text()
    shot(page, width, "10-booking-confirmed", full=False)

    page.route("**/reservations", lambda route: route.fulfill(status=409, content_type="application/json",
               body=json.dumps({"error": {"code": "table_unavailable", "message": "taken"}})))
    page.get_by_test_id("slot-t_5-20:00").click()
    page.get_by_test_id("booking-submit").click()
    page.get_by_test_id("booking-error").wait_for()
    shot(page, width, "11-booking-refused", full=False)
    page.unroute("**/reservations")

    search(page, party="6")
    page.get_by_test_id("slot-t_1+t_2-18:00").click()
    page.get_by_test_id("booking-form").wait_for()
    shot(page, width, "12-combo-chosen", full=False)
    shot(page, width, "13-combo-grid-full")

    page.goto(f"{BASE}/lookup")
    page.get_by_test_id("lookup-reference-input").fill("NOPE42")
    page.get_by_test_id("lookup-submit").click()
    page.get_by_test_id("reservation-error").wait_for()
    shot(page, width, "14-lookup-not-found")
    page.get_by_test_id("lookup-reference-input").fill(ref)
    page.get_by_test_id("lookup-submit").click()
    page.get_by_test_id("reservation-detail").wait_for()
    shot(page, width, "15-lookup-confirmed")
    page.get_by_test_id("reservation-cancel-button").click()
    page.get_by_test_id("reservation-status").filter(has_text="cancelled").wait_for()
    shot(page, width, "16-lookup-cancelled")
    ctx.close()


with sync_playwright() as p:
    browser = p.chromium.launch()
    for w in WIDTHS:
        run(w, browser)
    browser.close()
(OUT / "capture-report.json").write_text(json.dumps(REPORT, indent=1))
bad = [r for r in REPORT if r["sideways_overflow_px"] > 0]
print(f"{len(REPORT)} captures, sideways overflow on {len(bad)}: {bad}")
