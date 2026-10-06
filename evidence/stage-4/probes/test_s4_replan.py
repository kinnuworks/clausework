"""Stage-4 seating changes after a table closure (S4-01..S4-40)."""
import random
import uuid
from datetime import timezone

import pytest

from conftest import H, THU_S, burst, err, get_res, my_res, new_client, now_slot, parse_ts
from s3lib import hist, pol, publish
from s4lib import R4, apply_plan, booking_model, inst, preview, ref_plan, s4_env


@pytest.fixture
def e(http):
    return s4_env(http)


def mk(http, tok, tables, hm, party, day=THU_S, rest="r_four"):
    return http.post("/reservations", json={"restaurant_id": rest, "table_ids": list(tables),
                                            "starts_at_local": f"{day}T{hm}", "party_size": party},
                     headers=H(tok, str(uuid.uuid4())))


def ok(http, tok, tables, hm, party, **kw):
    r = mk(http, tok, tables, hm, party, **kw)
    assert r.status_code == 201, r.text
    return r.json()


def closure_utc(table, frm, to):
    return (table, parse_ts(frm).astimezone(timezone.utc), parse_ts(to).astimezone(timezone.utc))


def check_against_ref(http, tok, plan, bookings, closure, prior=()):
    ref = ref_plan(R4, bookings, closure, prior)
    if ref is None:
        err(plan, 409, "no_feasible_plan")
        return None
    assert plan.status_code == 201, (plan.text, ref)
    j = plan.json()
    assert [a["reference"] for a in j["assignments"]] == ref["considered"]
    for a in j["assignments"]:
        assert set(a["table_ids"]) == set(ref["assign"][a["reference"]]), (a, ref)
        assert a["changed"] is ref["changed"][a["reference"]], (a, ref)
    assert j["moved_count"] == ref["moved"] and j["unused_seats"] == ref["unused"], (j, ref)
    return j


def test_replan_matches_bruteforce(http):  # S4-10..S4-14 (best possible answer)
    rng = random.Random(4242)
    opts = [[t["id"]] for t in R4["tables"]] + R4["combinable"]
    hms = ["18:00", "18:30", "19:00", "19:30", "20:00", "20:30", "21:00"]
    done = 0
    for scenario in range(40):
        env = s4_env(http)
        users = [env["ada"], env["bob"]]
        created = []
        for _ in range(14):
            if len(created) >= 7:
                break
            r = mk(http, rng.choice(users), rng.choice(opts), rng.choice(hms), rng.randint(1, 6))
            if r.status_code == 201:
                created.append(r.json())
        table = rng.choice(R4["tables"])["id"]
        a = rng.randint(0, 6)
        b = rng.randint(a + 1, 10)
        frm, to = inst(f"{THU_S}T{17 + a // 2}:{'30' if a % 2 else '00'}"), inst(f"{THU_S}T{17 + b // 2}:{'30' if b % 2 else '00'}")
        cl = closure_utc(table, frm, to)
        models = [booking_model(x) for x in created]
        considered = [m for m in models if m["start"] < cl[2] and cl[1] < m["end"]]
        if len(considered) > 6:
            continue
        p = preview(http, env["mgr"], table, frm, to)
        j = check_against_ref(http, env["mgr"], p, models, cl)
        if j is not None:
            assert j["restaurant_revision"] == len(created)
            assert j["closure"]["table_id"] == table
            assert parse_ts(j["closure"]["from"]) == parse_ts(frm) and parse_ts(j["closure"]["to"]) == parse_ts(to)
        done += 1
    assert done >= 20


def test_accepted_terms_capacity_and_cutoff_ignored(http, e):  # S4-12, S4-13
    mgr, ada = e["mgr"], e["ada"]
    B = ok(http, ada, ["q_3"], "19:00", 4)
    assert publish(http, mgr, pol("2020-01-01", hours=R4["opening_hours"],
                                  caps={"q_1": 2, "q_2": 2, "q_3": 4, "q_4": 2, "q_5": 6, "q_6": 2}),
                   rest="r_four").status_code == 201
    p = preview(http, mgr, "q_3", inst(f"{THU_S}T18:00"), inst(f"{THU_S}T23:00"))
    assert p.status_code == 201, p.text
    assert p.json()["assignments"] == [{"reference": B["reference"], "table_ids": ["q_4"], "changed": True}]
    assert p.json()["unused_seats"] == 0 and p.json()["moved_count"] == 1
    near = ok(http, ada, ["c_1"], now_slot(60)[-5:], 2, day=now_slot(60)[:10], rest="r_now")
    pn = preview(http, mgr, "c_1", near["starts_at"], near["ends_at"], rest="r_now")
    assert pn.status_code == 201, pn.text
    assert pn.json()["assignments"][0]["table_ids"] == ["c_2"]
    an = apply_plan(http, mgr, pn.json()["plan_id"], rest="r_now")
    assert an.status_code == 201, an.text
    assert get_res(http, ada, near["reference"])["table_ids"] == ["c_2"]


def test_preview_apply_lifecycle(http, e):  # S4-20..S4-32
    mgr, ada, bob = e["mgr"], e["ada"], e["bob"]
    A = ok(http, ada, ["q_3"], "19:00", 3)
    B = ok(http, bob, ["q_5"], "19:00", 5)
    C = ok(http, ada, ["q_1"], "21:00", 2)
    snapA, hA = get_res(http, ada, A["reference"]), hist(http, ada, A["reference"])
    av_before = http.get("/availability", params={"restaurant_id": "r_four", "date": THU_S, "party_size": 1}).json()
    frm, to = inst(f"{THU_S}T18:00"), inst(f"{THU_S}T20:00")
    # validation and permissions
    err(preview(http, ada, "q_3", frm, to), 403, "forbidden")
    err(http.post("/restaurants/r_four/replans", json={"table_id": "q_3", "from": frm, "to": to},
                  headers={"Idempotency-Key": "x"}), 401, "unauthenticated")
    err(http.post("/restaurants/r_four/replans", json={"table_id": "q_3", "from": frm, "to": to}, headers=H(mgr)),
        400, "missing_idempotency_key")
    err(preview(http, mgr, "q_9", frm, to), 404, "not_found")
    err(preview(http, mgr, "q_3", frm, to, rest="r_nope"), 404, "not_found")
    err(preview(http, mgr, "q_3", to, frm), 422, "validation_failed")
    err(preview(http, mgr, "q_3", frm, frm), 422, "validation_failed")
    err(preview(http, mgr, "q_3", f"{THU_S}T18:00:00", to), 422, "validation_failed")
    err(preview(http, mgr, "q_3", "not-a-time", to), 422, "validation_failed")
    p = preview(http, mgr, "q_3", frm, to)
    assert p.status_code == 201, p.text
    pj = p.json()
    assert pj["restaurant_revision"] == 3
    assert [a["reference"] for a in pj["assignments"]] == sorted([A["reference"], B["reference"]])
    moved = [a for a in pj["assignments"] if a["changed"]]
    assert [a["reference"] for a in moved] == [A["reference"]] and moved[0]["table_ids"] == ["q_4"]
    # preview changes nothing
    assert get_res(http, ada, A["reference"]) == snapA and hist(http, ada, A["reference"]) == hA
    assert http.get("/availability", params={"restaurant_id": "r_four", "date": THU_S, "party_size": 1}).json() == av_before
    assert preview(http, mgr, "q_3", frm, to).json()["restaurant_revision"] == 3
    err(apply_plan(http, mgr, "nope-plan"), 404, "not_found")
    err(apply_plan(http, mgr, pj["plan_id"], rest="r_far"), 404, "not_found")
    err(apply_plan(http, ada, pj["plan_id"]), 403, "forbidden")
    key = str(uuid.uuid4())
    ap = apply_plan(http, mgr, pj["plan_id"], key=key)
    assert ap.status_code == 201, ap.text
    aj = ap.json()
    assert aj["plan_id"] == pj["plan_id"] and aj["restaurant_revision"] == 4
    assert [r["reference"] for r in aj["reservations"]] == [a["reference"] for a in pj["assignments"]]
    a2 = get_res(http, ada, A["reference"])
    assert a2["table_ids"] == ["q_4"] and a2["revision"] == snapA["revision"] + 1
    for k in ("starts_at", "ends_at", "starts_at_local", "party_size", "accepted_terms", "reference", "reservation_id", "created_at"):
        assert a2[k] == snapA[k], k
    h = hist(http, ada, A["reference"])["entries"]
    assert len(h) == len(hA["entries"]) + 1
    last = h[-1]
    assert last["event"] == "reassigned" and last["plan_id"] == pj["plan_id"]
    assert last["changes"] == [{"field": "table_ids", "from": ["q_3"], "to": ["q_4"]}]
    b2 = get_res(http, bob, B["reference"])
    assert b2["revision"] == B["revision"] and len(hist(http, bob, B["reference"])["entries"]) == 1
    # replay and second key
    rp = apply_plan(http, mgr, pj["plan_id"], key=key)
    assert rp.status_code == 200 and rp.json() == aj
    err(apply_plan(http, mgr, pj["plan_id"]), 409, "plan_already_applied")
    # closure now in force
    sl = {s["starts_at_local"]: s for s in http.get("/availability", params={
        "restaurant_id": "r_four", "date": THU_S, "party_size": 1, "explain": "true"}).json()["slots"]}
    s = sl[f"{THU_S}T18:00"]
    assert "q_3" not in s["available_table_ids"]
    assert all("q_3" not in o["table_ids"] for o in s["available_options"])
    q3 = [x for x in s["explain"] if x["table_id"] == "q_3"][0]
    assert q3["available"] is False and q3["rules"][1] == {"rule": "no_overlap", "holds": False}
    assert "q_3" in sl[f"{THU_S}T20:00"]["available_table_ids"]  # half-open: [18:00, 20:00)
    err(mk(http, bob, ["q_3"], "18:30", 2), 409, "table_unavailable")
    err(mk(http, bob, ["q_4", "q_3"], "18:00", 2), 409, "table_unavailable")
    err(http.patch(f"/reservations/{C['reference']}", json={"table_id": "q_3", "starts_at_local": f"{THU_S}T18:30"},
                   headers=H(ada)), 409, "table_unavailable")
    assert mk(http, bob, ["q_3"], "20:00", 2).status_code == 201
    # replay still original after later changes
    assert http.post(f"/reservations/{A['reference']}/cancel", headers=H(ada)).status_code == 200
    rp = apply_plan(http, mgr, pj["plan_id"], key=key)
    assert rp.status_code == 200 and rp.json() == aj


def test_stale_plan_and_other_restaurant(http, e):  # S4-27, S4-33
    mgr, ada = e["mgr"], e["ada"]
    A = ok(http, ada, ["q_3"], "19:00", 3)
    p = preview(http, mgr, "q_3", inst(f"{THU_S}T18:00"), inst(f"{THU_S}T21:00")).json()
    # writes elsewhere do not invalidate
    ok(http, ada, ["f_1"], "19:00", 2, rest="r_far")
    pf = preview(http, mgr, "f_1", inst(f"{THU_S}T18:00"), inst(f"{THU_S}T21:00"), rest="r_far").json()
    assert apply_plan(http, mgr, pf["plan_id"], rest="r_far").status_code == 201
    # a no-op, a failure and a replay do not invalidate either
    assert http.patch(f"/reservations/{A['reference']}", json={"party_size": 3}, headers=H(ada)).status_code == 200
    err(mk(http, ada, ["q_3"], "19:30", 2), 409, "table_unavailable")
    ap = apply_plan(http, mgr, p["plan_id"])
    assert ap.status_code == 201, ap.text
    # a real write in between makes a plan stale, and nothing changes
    p2 = preview(http, mgr, "q_5", inst(f"{THU_S}T12:00"), inst(f"{THU_S}T13:00")).json()
    ok(http, ada, ["q_6"], "21:00", 2)
    snap = get_res(http, ada, A["reference"])
    err(apply_plan(http, mgr, p2["plan_id"]), 409, "stale_plan")
    assert get_res(http, ada, A["reference"]) == snap
    assert mk(http, ada, ["q_5"], "12:00", 2).status_code == 201  # q_5 closure from the stale plan was not recorded


def test_restaurant_revision_counting(http, e):  # S4-21
    mgr, ada = e["mgr"], e["ada"]
    rev = lambda: preview(http, mgr, "q_6", inst(f"{THU_S}T12:00"), inst(f"{THU_S}T12:30")).json()["restaurant_revision"]
    assert rev() == 0
    key = str(uuid.uuid4())
    b = {"restaurant_id": "r_four", "table_id": "q_3", "starts_at_local": f"{THU_S}T19:00", "party_size": 2}
    A = http.post("/reservations", json=b, headers=H(ada, key)).json()
    assert rev() == 1
    assert http.post("/reservations", json=b, headers=H(ada, key)).status_code == 200
    err(mk(http, ada, ["q_3"], "19:30", 2), 409, "table_unavailable")
    assert http.patch(f"/reservations/{A['reference']}", json={"party_size": 2}, headers=H(ada)).status_code == 200
    ok(http, ada, ["f_1"], "19:00", 2, rest="r_far")
    assert rev() == 1
    assert http.patch(f"/reservations/{A['reference']}", json={"party_size": 3}, headers=H(ada)).status_code == 200
    assert rev() == 2
    m = http.post("/reservation-moves", json={"moves": [{"reference": A["reference"], "table_id": "q_4"}]},
                  headers=H(ada, str(uuid.uuid4())))
    assert m.status_code == 201
    assert rev() == 3
    s = http.post("/series", json={"anchor_reference": A["reference"], "count": 3, "interval_weeks": 1},
                  headers=H(ada, str(uuid.uuid4())))
    assert s.status_code == 201, s.text
    assert rev() == 4
    assert publish(http, mgr, pol("2020-01-01", hours=R4["opening_hours"],
                                  caps={t["id"]: t["capacity"] for t in R4["tables"]}), rest="r_four").status_code == 201
    assert rev() == 5
    assert http.post(f"/reservations/{A['reference']}/cancel", headers=H(ada)).status_code == 200
    assert http.post(f"/reservations/{A['reference']}/cancel", headers=H(ada)).status_code == 200
    assert rev() == 6


def test_no_feasible_plan(http, e):  # S4-15
    mgr, ada = e["mgr"], e["ada"]
    ok(http, ada, ["q_5"], "19:00", 6)
    ok(http, ada, ["q_3", "q_4"], "19:00", 6)
    p = preview(http, mgr, "q_5", inst(f"{THU_S}T18:00"), inst(f"{THU_S}T21:00"))
    err(p, 409, "no_feasible_plan")
    assert preview(http, mgr, "q_6", inst(f"{THU_S}T12:00"), inst(f"{THU_S}T12:30")).json()["restaurant_revision"] == 2


def test_concurrent_applies(http, e):  # S4-34
    mgr, ada = e["mgr"], e["ada"]
    A = ok(http, ada, ["q_3"], "19:00", 3)
    B = ok(http, ada, ["q_1"], "19:00", 2)
    p1 = preview(http, mgr, "q_3", inst(f"{THU_S}T18:00"), inst(f"{THU_S}T21:00")).json()
    p2 = preview(http, mgr, "q_1", inst(f"{THU_S}T18:00"), inst(f"{THU_S}T21:00")).json()

    def f(pid):
        def g():
            with new_client() as c:
                return apply_plan(c, mgr, pid)
        return g
    rs = burst([f(p1["plan_id"]) for _ in range(5)] + [f(p2["plan_id"]) for _ in range(5)])
    codes = [x.status_code for x in rs]
    assert codes.count(201) == 1, codes
    for x in rs:
        if x.status_code != 201:
            assert x.status_code == 409 and x.json()["error"]["code"] in ("stale_plan", "plan_already_applied"), x.text
    win = [x for x in rs if x.status_code == 201][0].json()
    plan = p1 if win["plan_id"] == p1["plan_id"] else p2
    for a in plan["assignments"]:
        assert set(get_res(http, ada, a["reference"])["table_ids"]) == set(a["table_ids"])
