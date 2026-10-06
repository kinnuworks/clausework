"""Stage-2 screens (S2-50..S2-80) through Playwright/Chromium, using the spec's data-testids and routes."""
import asyncio
import json
import re
import uuid

import pytest
from playwright.async_api import async_playwright, expect

from conftest import BASE, H, THU_S, WED_S, avail, login, my_res, now_slot, reset
from s2lib import GAR, LAT, s2_fixture

T = lambda tid: f'[data-testid="{tid}"]'
REF = re.compile(r"^[A-Z0-9]{6,12}$")


def run(coro_fn, width=1280):
    async def main():
        async with async_playwright() as p:
            b = await p.chromium.launch()
            ctx = await b.new_context(viewport={"width": width, "height": 900})
            page = await ctx.new_page()
            page.set_default_timeout(8000)
            try:
                await coro_fn(page)
            finally:
                await b.close()
    asyncio.run(main())


@pytest.fixture
def ui(http):
    reset(http, s2_fixture())
    return http


async def ui_login(page, email="ada@example.com", pw="correct horse", name="Ada"):
    await page.goto(BASE + "/login")
    await page.fill(T("login-email"), email)
    await page.fill(T("login-password"), pw)
    await page.click(T("login-submit"))
    await expect(page.locator(T("current-user"))).to_contain_text(name)


async def search(page, rest="r_lat", date=THU_S, party=2):
    if await page.locator(T("restaurant-select")).count() == 0:
        await page.goto(BASE + "/")
    await page.select_option(T("restaurant-select"), rest)
    await page.fill(T("date-input"), date)
    await page.fill(T("party-size-input"), str(party))
    await page.click(T("search-button"))


async def cell(page, tid):
    loc = page.locator(T(tid))
    await expect(loc).to_have_count(1)
    return loc


def test_routes_are_html(http):  # S2-01
    for r in ["/", "/signup", "/login", "/lookup"]:
        x = http.get(r)
        assert x.status_code == 200 and "text/html" in x.headers.get("content-type", ""), r


def test_signup_login_logout(ui):  # S2-50..S2-53
    async def go(page):
        await page.goto(BASE + "/signup")
        await page.fill(T("signup-email"), "dora@example.com")
        await page.fill(T("signup-password"), "dorapass1")
        await page.fill(T("signup-display-name"), "Dora Diner")
        await page.click(T("signup-submit"))
        await expect(page.locator(T("current-user"))).to_contain_text("Dora Diner")
        for r in ["/", "/lookup", "/login", "/signup"]:
            await page.goto(BASE + r)
            await expect(page.locator(T("current-user"))).to_contain_text("Dora Diner")
        await page.click(T("logout-button"))
        await expect(page.locator(T("current-user"))).to_have_count(0)
        await page.goto(BASE + "/login")
        await expect(page.locator(T("auth-error"))).to_have_count(0)
        await page.fill(T("login-email"), "dora@example.com")
        await page.fill(T("login-password"), "wrong-pass")
        await page.click(T("login-submit"))
        await expect(page.locator(T("auth-error"))).to_be_visible()
        await page.fill(T("login-password"), "dorapass1")
        await page.click(T("login-submit"))
        await expect(page.locator(T("current-user"))).to_contain_text("Dora Diner")
    run(go)
    assert login(ui, "dora@example.com", "dorapass1")


def test_grid_matches_api(ui):  # S2-55..S2-58
    async def go(page):
        await page.goto(BASE + "/")
        for party in (2, 5):
            await search(page, party=party)
            await expect(page.locator(T("availability-grid"))).to_be_visible()
            api = avail(ui, "r_lat", THU_S, party)
            for s in api["slots"]:
                hm = s["starts_at_local"][-5:]
                for t in LAT["tables"]:
                    c = await cell(page, f"slot-{t['id']}-{hm}")
                    want = "true" if t["id"] in s["available_table_ids"] else "false"
                    await expect(c).to_have_attribute("data-available", want)
                for o in s["available_options"]:
                    if len(o["table_ids"]) == 2:
                        c = await cell(page, f"slot-{o['table_ids'][0]}+{o['table_ids'][1]}-{hm}")
                        await expect(c).to_have_attribute("data-available", "true")
            if party == 2:
                assert await page.locator(T("slot-w_2+w_1-19:00")).count() == 0
                assert await page.locator(T("slot-w_1+w_3-19:00")).count() == 0
        await search(page, date=WED_S, party=2)
        await expect(page.locator(T("no-slots"))).to_be_visible()
        await expect(page.locator('[data-testid^="slot-"]')).to_have_count(0)
    run(go)


def test_signed_out_click(ui):  # S2-59
    async def go(page):
        await page.goto(BASE + "/")
        await search(page)
        c = await cell(page, "slot-w_2-19:00")
        await c.click()
        await page.wait_for_timeout(500)
        assert page.url.rstrip("/").endswith("/login") or await page.locator(T("auth-error")).is_visible()
        assert my_res(ui, login(ui, "ada@example.com", "correct horse")) == []
    run(go)


def test_booking_flow_and_resubmit(ui):  # S2-60..S2-66
    posts = []

    async def go(page):
        page.on("request", lambda r: posts.append((r.headers.get("idempotency-key"), r.post_data)) if r.method == "POST" and r.url.endswith("/reservations") else None)
        statuses = []
        page.on("response", lambda r: statuses.append(r) if r.request.method == "POST" and r.url.endswith("/reservations") else None)
        await ui_login(page)
        await page.goto(BASE + "/")
        await search(page, party=2)
        unavailable_before = await page.locator(T("booking-form")).count()
        c = await cell(page, "slot-w_2-19:00")
        await c.click()
        await expect(page.locator(T("booking-form"))).to_be_visible()
        await expect(page.locator(T("booking-summary"))).to_contain_text("Kamin")
        await expect(page.locator(T("booking-summary"))).to_contain_text("19:00")
        await expect(page.locator(T("booking-party-size"))).to_have_value("2")
        await page.click(T("booking-submit"))
        ref_loc = page.locator(T("confirmation-reference"))
        await expect(ref_loc).to_have_text(REF)
        ref = (await ref_loc.text_content()).strip()
        assert (await ref_loc.text_content()) == ref
        det = page.locator(T("confirmation-details"))
        for s in ("Zur Laterne", "Kamin", "19:00"):
            await expect(det).to_contain_text(s)
        await expect(page.locator(T("booking-form"))).to_be_visible()
        await page.click(T("booking-submit"))
        await page.wait_for_timeout(800)
        await expect(page.locator(T("confirmation-reference"))).to_have_text(ref)
        await expect(page.locator(T("booking-error"))).to_have_count(0)
        assert [r["reference"] for r in my_res(ui, login(ui, "ada@example.com", "correct horse"))] == [ref]
        assert posts[0] == posts[1]
        await page.fill(T("booking-party-size"), "3")
        await page.click(T("booking-submit"))
        await page.wait_for_timeout(800)
        third = statuses[-1]
        body = await third.json()
        assert third.status in (201, 409), third.status
        assert body.get("error", {}).get("code") != "idempotency_key_reuse"
        if third.status == 409:
            await expect(page.locator(T("booking-error"))).to_be_visible()
    run(go)


def test_conflict_shows_error_and_refreshes(ui):  # S2-31..S2-33 (409 path)
    async def go(page):
        await ui_login(page)
        await page.goto(BASE + "/")
        await search(page, party=4)
        c = await cell(page, "slot-w_4-19:00")
        await c.click()
        await expect(page.locator(T("booking-form"))).to_be_visible()
        await page.fill(T("booking-party-size"), "5")
        bob = login(ui, "bob@example.com", "battery staple")
        r = ui.post("/reservations", json={"restaurant_id": "r_lat", "table_id": "w_4", "starts_at_local": f"{THU_S}T19:00",
                                           "party_size": 2}, headers=H(bob, str(uuid.uuid4())))
        assert r.status_code == 201
        await page.click(T("booking-submit"))
        await expect(page.locator(T("booking-error"))).to_be_visible()
        await expect(page.locator(T("confirmation"))).to_have_count(0)
        await expect(page.locator(T("booking-form"))).to_be_visible()
        await expect(page.locator(T("booking-party-size"))).to_have_value("5")
        await expect(page.locator(T("slot-w_4-19:00"))).to_have_attribute("data-available", "false")
    run(go)


def test_lost_response_then_retry(ui):  # S2-34..S2-37
    seen = []

    async def go(page):
        state = {"lose": True, "committed": None}

        async def handler(route):
            req = route.request
            if req.method == "POST" and state["lose"]:
                seen.append((req.headers.get("idempotency-key"), req.post_data))
                resp = await route.fetch()
                state["committed"] = await resp.json()
                state["lose"] = False
                await route.abort("connectionreset")
            else:
                if req.method == "POST":
                    seen.append((req.headers.get("idempotency-key"), req.post_data))
                await route.continue_()
        await ui_login(page)
        await page.goto(BASE + "/")
        await search(page, party=2)
        await (await cell(page, "slot-w_3-20:00")).click()
        await expect(page.locator(T("booking-form"))).to_be_visible()
        await page.route("**/reservations", handler)
        await page.click(T("booking-submit"))
        unc = page.locator(T("booking-uncertain"))
        await expect(unc).to_be_visible()
        assert (await unc.text_content()).strip()
        await expect(page.locator(T("booking-error"))).to_have_count(0)
        await expect(page.locator(T("confirmation"))).to_have_count(0)
        await page.click(T("booking-submit"))
        await expect(page.locator(T("confirmation-reference"))).to_have_text(state["committed"]["reference"])
        await expect(page.locator(T("booking-uncertain"))).to_have_count(0)
        await expect(page.locator(T("booking-error"))).to_have_count(0)
        assert seen[0][0] == seen[1][0] and json.loads(seen[0][1]) == json.loads(seen[1][1])
        assert len(my_res(ui, login(ui, "ada@example.com", "correct horse"))) == 1
    run(go)


def test_out_of_order_search(ui):  # S2-30
    async def go(page):
        async def slow(route):
            if "restaurant_id=r_lat" in route.request.url:
                await asyncio.sleep(2.0)
            await route.continue_()
        await ui_login(page)
        await page.goto(BASE + "/")
        await page.route("**/availability**", slow)
        await search(page, rest="r_lat", party=2)
        await page.wait_for_timeout(100)
        await search(page, rest="r_gar", party=2)
        await expect(page.locator(T("slot-g_a-19:00"))).to_have_count(1)
        await page.wait_for_timeout(3000)
        await expect(page.locator(T("slot-g_a-19:00"))).to_have_count(1)
        await expect(page.locator('[data-testid^="slot-w_"]')).to_have_count(0)
        await (await cell(page, "slot-g_a-19:00")).click()
        await expect(page.locator(T("booking-summary"))).to_contain_text("Linde")
    run(go)


def test_combination_booking_ui(ui):  # S2-70..S2-73
    async def go(page):
        await ui_login(page)
        await page.goto(BASE + "/")
        await search(page, party=5)
        c = await cell(page, "slot-w_1+w_2-19:00")
        await expect(c).to_have_attribute("data-available", "true")
        await c.click()
        summ = page.locator(T("booking-summary"))
        await expect(summ).to_contain_text("Fenster")
        await expect(summ).to_contain_text("Kamin")
        await page.click(T("booking-submit"))
        ref = page.locator(T("confirmation-reference"))
        await expect(ref).to_have_text(REF)
        r = (await ref.text_content()).strip()
        for s in ("Fenster", "Kamin"):
            await expect(page.locator(T("confirmation-tables"))).to_contain_text(s)
        await page.goto(BASE + "/lookup")
        await page.fill(T("lookup-reference-input"), r)
        await page.click(T("lookup-submit"))
        await expect(page.locator(T("reservation-detail"))).to_be_visible()
        for s in ("Fenster", "Kamin"):
            await expect(page.locator(T("reservation-tables"))).to_contain_text(s)
    run(go)


def test_lookup_and_cancel(ui):  # S2-67..S2-69
    ada = login(ui, "ada@example.com", "correct horse")
    r = ui.post("/reservations", json={"restaurant_id": "r_lat", "table_id": "w_1", "starts_at_local": f"{THU_S}T19:00",
                                       "party_size": 2}, headers=H(ada, str(uuid.uuid4()))).json()
    near = ui.post("/reservations", json={"restaurant_id": "r_now", "table_id": "c_1", "starts_at_local": now_slot(60),
                                          "party_size": 2}, headers=H(ada, str(uuid.uuid4()))).json()

    async def go(page):
        await ui_login(page)
        await page.goto(BASE + "/lookup")
        await page.fill(T("lookup-reference-input"), "NOPE99")
        await page.click(T("lookup-submit"))
        await expect(page.locator(T("reservation-error"))).to_be_visible()
        await page.fill(T("lookup-reference-input"), r["reference"])
        await page.click(T("lookup-submit"))
        await expect(page.locator(T("reservation-status"))).to_have_text("confirmed")
        await expect(page.locator(T("reservation-tables"))).to_contain_text("Fenster")
        await page.click(T("reservation-cancel-button"))
        await expect(page.locator(T("reservation-status"))).to_have_text("cancelled")
        await expect(page.locator(T("reservation-cancel-button"))).to_have_count(0)
        await page.fill(T("lookup-reference-input"), near["reference"])
        await page.click(T("lookup-submit"))
        await expect(page.locator(T("reservation-status"))).to_have_text("confirmed")
        await page.click(T("reservation-cancel-button"))
        await expect(page.locator(T("reservation-error"))).to_be_visible()
        await expect(page.locator(T("reservation-status"))).to_have_text("confirmed")
    run(go)
    assert [x["status"] for x in my_res(ui, ada) if x["reference"] == r["reference"]] == ["cancelled"]


def test_no_horizontal_scroll_375(ui):  # S2-45
    async def go(page):
        await ui_login(page)
        for r in ["/signup", "/login", "/lookup", "/"]:
            await page.goto(BASE + r)
            await page.wait_for_timeout(200)
            sw = await page.evaluate("document.documentElement.scrollWidth")
            assert sw <= 376, (r, sw)
        await search(page, party=5)
        await expect(page.locator(T("availability-grid"))).to_be_visible()
        await (await cell(page, "slot-w_1+w_2-19:00")).click()
        await expect(page.locator(T("booking-form"))).to_be_visible()
        sw = await page.evaluate("document.documentElement.scrollWidth")
        assert sw <= 376, sw
    run(go, width=375)


def test_upgrade_keeps_session_and_retry(ui):  # S2-38..S2-39 (export/import between browser requests)
    async def go(page):
        state = {"lose": True, "ref": None}

        async def handler(route):
            if route.request.method == "POST" and state["lose"]:
                resp = await route.fetch()
                state["ref"] = (await resp.json())["reference"]
                state["lose"] = False
                await route.abort("connectionreset")
            else:
                await route.continue_()
        await ui_login(page)
        await page.goto(BASE + "/")
        await search(page, party=2)
        await (await cell(page, "slot-w_1-21:00")).click()
        await page.route("**/reservations", handler)
        await page.click(T("booking-submit"))
        await expect(page.locator(T("booking-uncertain"))).to_be_visible()
        E = ui.get("/_test/export").json()
        reset(ui, {"users": [], "restaurants": [GAR], "reservations": []})
        assert ui.post("/_test/import", json=E).status_code == 204
        await page.click(T("booking-submit"))
        await expect(page.locator(T("confirmation-reference"))).to_have_text(state["ref"])
        await expect(page.locator(T("current-user"))).to_contain_text("Ada")
        await page.goto(BASE + "/lookup")
        await page.fill(T("lookup-reference-input"), state["ref"])
        await page.click(T("lookup-submit"))
        await expect(page.locator(T("reservation-status"))).to_have_text("confirmed")
    run(go)
