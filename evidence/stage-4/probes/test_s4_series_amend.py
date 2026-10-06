"""Stage-4 recurring amendments (S4-50..S4-66), seating repairs of series (S4-67), extra order variants (S4-V*)."""
import uuid

import pytest

from conftest import H, THU_S, burst, err, get_res, new_client
from s3lib import day, hist, pol, publish
from s4lib import R4, apply_plan, inst, preview, s4_env


@pytest.fixture
def e(http):
    return s4_env(http)


def res(http, tok, tables, local, party=2, rest="r_four"):
    r = http.post("/reservations", json={"restaurant_id": rest, "table_ids": list(tables), "starts_at_local": local,
                                         "party_size": party}, headers=H(tok, str(uuid.uuid4())))
    assert r.status_code == 201, r.text
    return r.json()


def adopt(http, tok, anchor, count, interval=1):
    r = http.post("/series", json={"anchor_reference": anchor, "count": count, "interval_weeks": interval},
                  headers=H(tok, str(uuid.uuid4())))
    assert r.status_code == 201, r.text
    return r.json()


def amend(http, tok, sid, body, key=None):
    return http.post(f"/series/{sid}/amend", json=body, headers=H(tok, key or str(uuid.uuid4())))


def sget(http, tok, sid):
    r = http.get(f"/series/{sid}", headers=H(tok))
    assert r.status_code == 200
    return r.json()


def rrev(http, mgr):
    return preview(http, mgr, "q_6", inst(f"{THU_S}T12:00"), inst(f"{THU_S}T12:30")).json()["restaurant_revision"]


def test_amend_basic_and_replay(http, e):  # S4-50..S4-56, S4-60
    ada, mgr = e["ada"], e["mgr"]
    A = res(http, ada, ["q_3"], f"{THU_S}T19:00")
    s = adopt(http, ada, A["reference"], 4)
    sid, occ = s["series_id"], s["occurrences"]
    hist0 = [hist(http, ada, o["reference"]) for o in occ]
    r0 = rrev(http, mgr)
    key = str(uuid.uuid4())
    body = {"expected_revision": 1, "from_index": 1, "local_time": "20:00", "note": "ignored"}
    r = amend(http, ada, sid, body, key)
    assert r.status_code == 201, r.text
    j = r.json()
    assert j["series_id"] == sid and j["revision"] == 2
    o = j["occurrences"]
    assert [x["reference"] for x in o] == [x["reference"] for x in occ]
    assert o[0]["reservation"]["starts_at_local"] == f"{day(0)}T19:00" and o[0]["reservation"]["revision"] == 1
    for i in (1, 2, 3):
        rr = o[i]["reservation"]
        assert rr["starts_at_local"] == f"{day(7 * i)}T20:00" and rr["revision"] == 2 and rr["table_ids"] == ["q_3"]
        assert o[i]["exception"] is False
        h = hist(http, ada, o[i]["reference"])["entries"]
        assert len(h) == len(hist0[i]["entries"]) + 1 and h[-1]["event"] == "changed"
        assert h[-1]["changes"] == [{"field": "starts_at_local", "from": f"{day(7 * i)}T19:00", "to": f"{day(7 * i)}T20:00"}]
    assert hist(http, ada, occ[0]["reference"]) == hist0[0]
    assert rrev(http, mgr) == r0 + 1
    # all-no-op: succeeds, nothing changes
    n = amend(http, ada, sid, {"expected_revision": 2, "from_index": 1, "local_time": "20:00"})
    assert n.status_code == 201 and n.json()["revision"] == 2
    assert rrev(http, mgr) == r0 + 1
    # replay even after later edits/cancellations
    assert http.post(f"/reservations/{occ[3]['reference']}/cancel", headers=H(ada)).status_code == 200
    rp = amend(http, ada, sid, body, key)
    assert rp.status_code == 200 and rp.json() == j
    err(amend(http, ada, sid, {**body, "local_time": "21:00"}, key), 409, "idempotency_key_reuse")


def test_amend_skips_exceptions_and_cancelled(http, e):  # S4-57
    ada = e["ada"]
    A = res(http, ada, ["q_4"], f"{THU_S}T19:00")
    s = adopt(http, ada, A["reference"], 4)
    sid, occ = s["series_id"], s["occurrences"]
    assert http.patch(f"/reservations/{occ[1]['reference']}", json={"party_size": 3}, headers=H(ada)).status_code == 200
    assert http.post(f"/reservations/{occ[2]['reference']}/cancel", headers=H(ada)).status_code == 200
    cur = sget(http, ada, sid)
    assert cur["revision"] == 3
    r = amend(http, ada, sid, {"expected_revision": 3, "from_index": 0, "local_time": "18:30"})
    assert r.status_code == 201, r.text
    o = r.json()["occurrences"]
    assert [x["reservation"]["starts_at_local"][-5:] for x in o] == ["18:30", "19:00", "19:00", "18:30"]
    assert [x["exception"] for x in o] == [False, True, False, False]
    assert o[2]["reservation"]["status"] == "cancelled" and r.json()["revision"] == 4


def test_amend_validation_and_stale(http, e):  # S4-51, S4-52
    ada, bob = e["ada"], e["bob"]
    A = res(http, ada, ["q_5"], f"{THU_S}T19:00")
    sid = adopt(http, ada, A["reference"], 3)["series_id"]
    good = {"expected_revision": 1, "from_index": 0, "local_time": "20:00"}
    bads = [{"expected_revision": 0}, {"expected_revision": -1}, {"expected_revision": True}, {"expected_revision": "1"},
            {"from_index": -1}, {"from_index": 3}, {"from_index": True}, {"from_index": 1.5},
            {"local_time": "8:00"}, {"local_time": "24:00"}, {"local_time": "20:00:00"}, {"local_time": "20:60"},
            {"local_time": ""}, {"local_time": 2000}]
    for b in bads:
        err(amend(http, ada, sid, {**good, **b}), 422, "validation_failed")
    for k in good:
        err(amend(http, ada, sid, {kk: v for kk, v in good.items() if kk != k}), 422, "validation_failed")
    err(amend(http, ada, sid, {**good, "expected_revision": 2}), 409, "stale_revision")
    err(amend(http, ada, sid, {**good, "expected_revision": 2, "local_time": "23:30"}), 409, "stale_revision")
    err(amend(http, bob, sid, good), 404, "not_found")
    err(amend(http, ada, "no-such-series", good), 404, "not_found")
    err(http.post(f"/series/{sid}/amend", json=good, headers={"Idempotency-Key": "x"}), 401, "unauthenticated")
    err(http.post(f"/series/{sid}/amend", json=good, headers=H(ada)), 400, "missing_idempotency_key")
    assert sget(http, ada, sid)["revision"] == 1
    assert amend(http, ada, sid, {**good, "local_time": "00:00"}).status_code in (422,)  # outside opening hours


def test_amend_atomic_and_precedence(http, e):  # S4-58, S4-59
    ada, bob, mgr = e["ada"], e["bob"], e["mgr"]
    A = res(http, ada, ["q_3"], f"{THU_S}T19:00")
    s = adopt(http, ada, A["reference"], 4)
    sid, occ = s["series_id"], s["occurrences"]
    blocker = res(http, bob, ["q_3"], f"{day(7)}T20:30")
    snaps = [get_res(http, ada, o["reference"]) for o in occ]
    hs = [hist(http, ada, o["reference"]) for o in occ]
    r0 = rrev(http, mgr)
    key = str(uuid.uuid4())
    body = {"expected_revision": 1, "from_index": 0, "local_time": "20:00"}
    err(amend(http, ada, sid, body, key), 409, "table_unavailable")
    assert [get_res(http, ada, o["reference"]) for o in occ] == snaps
    assert [hist(http, ada, o["reference"]) for o in occ] == hs
    assert sget(http, ada, sid)["revision"] == 1 and rrev(http, mgr) == r0
    # a non-occupancy error at a later index beats an occupancy conflict at an earlier one
    assert publish(http, mgr, pol(day(21), hours=[{"weekday": "thu", "opens": "18:00", "closes": "21:00"}],
                                  caps={t["id"]: t["capacity"] for t in R4["tables"]}), rest="r_four").status_code == 201
    err(amend(http, ada, sid, {**body, "local_time": "20:00", "expected_revision": 1}), 422, "outside_opening_hours")
    # once the blocker is gone and the time fits, the failed key is reusable
    assert http.post(f"/reservations/{blocker['reference']}/cancel", headers=H(bob)).status_code == 200
    ok = amend(http, ada, sid, {**body, "local_time": "19:30"}, key)
    assert ok.status_code == 201, ok.text
    assert [x["reservation"]["accepted_terms"]["policy_version"] for x in ok.json()["occurrences"]] == [0, 0, 0, 1]


def test_amend_dst(http, e):  # S4-61
    ada = e["ada"]
    A = res(http, ada, ["d_1"], "2027-03-21T00:30", rest="r_dst")
    sid = adopt(http, ada, A["reference"], 2)["series_id"]
    err(amend(http, ada, sid, {"expected_revision": 1, "from_index": 0, "local_time": "02:30"}), 422, "invalid_local_time")
    assert sget(http, ada, sid)["revision"] == 1


def test_amend_concurrent_same_revision(http, e):  # S4-62
    ada = e["ada"]
    A = res(http, ada, ["q_5"], f"{THU_S}T18:00")
    sid = adopt(http, ada, A["reference"], 3)["series_id"]
    times = ["18:30", "19:00", "19:30", "20:00", "20:30", "21:00"]

    def f(t):
        def g():
            with new_client() as c:
                return amend(c, ada, sid, {"expected_revision": 1, "from_index": 0, "local_time": t})
        return g
    rs = burst([f(t) for t in times * 2])
    real = [x for x in rs if x.status_code == 201]
    assert len(real) <= 1, [x.status_code for x in rs]
    for x in rs:
        if x.status_code != 201:
            err(x, 409, "stale_revision")
    assert sget(http, ada, sid)["revision"] == 1 + len(real)


def test_repair_moves_series_occurrence(http, e):  # S4-67
    ada, mgr = e["ada"], e["mgr"]
    A = res(http, ada, ["q_3"], f"{THU_S}T19:00", 3)
    s = adopt(http, ada, A["reference"], 3)
    sid, occ = s["series_id"], s["occurrences"]
    assert http.patch(f"/reservations/{occ[2]['reference']}", json={"party_size": 4}, headers=H(ada)).status_code == 200
    before = sget(http, ada, sid)
    p = preview(http, mgr, "q_3", inst(f"{day(7)}T18:00"), inst(f"{day(14)}T23:00"))
    assert p.status_code == 201, p.text
    ap = apply_plan(http, mgr, p.json()["plan_id"])
    assert ap.status_code == 201, ap.text
    after = sget(http, ada, sid)
    assert after["revision"] == before["revision"] + 1
    assert [o["exception"] for o in after["occurrences"]] == [o["exception"] for o in before["occurrences"]]
    for b, a in zip(before["occurrences"][1:], after["occurrences"][1:]):
        assert a["reference"] == b["reference"]
        assert a["reservation"]["starts_at_local"] == b["reservation"]["starts_at_local"]
        assert a["reservation"]["accepted_terms"] == b["reservation"]["accepted_terms"]
        assert a["reservation"]["table_ids"] != ["q_3"]


def test_moves_precedence_variant(http, e):  # S4-V1: second precedence variant (stage-2 audit weak spot)
    ada = e["ada"]
    A = res(http, ada, ["q_1"], f"{THU_S}T19:00")
    F = res(http, ada, ["f_1"], f"{THU_S}T19:00", rest="r_far")
    assert http.post(f"/reservations/{A['reference']}/cancel", headers=H(ada)).status_code == 200
    err(http.post("/reservation-moves", json={"moves": [{"reference": A["reference"]}, {"reference": F["reference"]}]},
                  headers=H(ada, str(uuid.uuid4()))), 409, "reservation_cancelled")
    B = res(http, ada, ["q_2"], f"{THU_S}T19:00")
    err(http.post("/reservation-moves", json={"moves": [{"reference": B["reference"]}, {"reference": F["reference"]}]},
                  headers=H(ada, str(uuid.uuid4()))), 422, "validation_failed")
