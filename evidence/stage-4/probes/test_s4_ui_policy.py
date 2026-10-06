"""S4-C7 (stage-3 verdict O2): the availability grid must follow the SELECTED POLICY's capacities, not the fixture's.
Every single and pair cell is compared with GET /availability for several party sizes after a capacity-raising policy."""
from conftest import BASE, THU_S, avail, login
from s3lib import pol, publish
from s4lib import R4, s4_env
from test_s2_ui import T, cell, run, search, ui_login


def test_grid_follows_policy_capacities(http):
    env = s4_env(http)
    caps = {"q_1": 6, "q_2": 6, "q_3": 4, "q_4": 4, "q_5": 6, "q_6": 2}
    r = publish(http, env["mgr"], pol("2020-01-01", hours=R4["opening_hours"], caps=caps), rest="r_four")
    assert r.status_code == 201, r.text
    parties = (6, 10, 12)
    api = {p: avail(http, "r_four", THU_S, p) for p in parties}
    pairs10 = [o["table_ids"] for o in api[10]["slots"][0]["available_options"] if len(o["table_ids"]) == 2]
    assert ["q_1", "q_2"] in pairs10  # 6+6 under the policy (fixture would give 2+2)

    async def go(page):
        await ui_login(page)
        await page.goto(BASE + "/")
        for party in parties:
            await search(page, rest="r_four", date=THU_S, party=party)
            await page.wait_for_selector(T("availability-grid"))
            for s in api[party]["slots"]:
                hm = s["starts_at_local"][-5:]
                for t in R4["tables"]:
                    c = await cell(page, f"slot-{t['id']}-{hm}")
                    want = "true" if t["id"] in s["available_table_ids"] else "false"
                    assert await c.get_attribute("data-available") == want, (party, hm, t["id"])
                offered = {tuple(o["table_ids"]) for o in s["available_options"] if len(o["table_ids"]) == 2}
                for p in R4["combinable"]:
                    loc = page.locator(T(f"slot-{p[0]}+{p[1]}-{hm}"))
                    n = await loc.count()
                    if tuple(p) in offered:
                        assert n == 1, (party, hm, p, "pair offered by API but missing from grid")
                        assert await loc.get_attribute("data-available") == "true", (party, hm, p)
                    elif n:
                        assert await loc.get_attribute("data-available") == "false", (party, hm, p)
    run(go)
    assert login(http, "ada@example.com", "correct horse")
