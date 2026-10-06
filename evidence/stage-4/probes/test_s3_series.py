"""Stage-3 recurring reservations (S3-45..S3-58) and carried cross-cutting rules on the new write paths (S3-C*)."""
import uuid

import pytest

from conftest import H, THU_S, burst, err, get_res, my_res, new_client, now_slot, parse_ts, same_instant_offset
from s2lib import lb
from s3lib import TERMS0, day, hist, mk, pol, publish, rb, s3_env, terms_of


@pytest.fixture
def e(http):
    return s3_env(http)


def series(http, tok, body, key=None):
    return http.post("/series", json=body, headers=H(tok, key or str(uuid.uuid4())))


def test_adopt_basic(http, e):  # S3-45..S3-50
    mgr, ada = e["mgr"], e["ada"]
    pb = pol(day(14), dur=60)
    v = publish(http, mgr, pb).json()["policy_version"]
    A = mk(http, ada, rb("p_2", f"{THU_S}T19:00", 3))
    hA = hist(http, ada, A["reference"])
    key = str(uuid.uuid4())
    body = {"anchor_reference": A["reference"], "count": 3, "interval_weeks": 1, "note": "ignored"}
    r = series(http, ada, body, key)
    assert r.status_code == 201, r.text
    s = r.json()
    assert isinstance(s["series_id"], str) and s["revision"] == 1 and s["interval_weeks"] == 1
    occ = s["occurrences"]
    assert [o["index"] for o in occ] == [0, 1, 2]
    assert occ[0]["reference"] == A["reference"] and occ[0]["reservation"] == A and occ[0]["exception"] is False
    assert get_res(http, ada, A["reference"]) == A and hist(http, ada, A["reference"]) == hA
    assert len({o["reference"] for o in occ}) == 3
    for i, o in enumerate(occ):
        res = o["reservation"]
        assert res["reference"] == o["reference"]
        assert res["starts_at_local"] == f"{day(7 * i)}T19:00"
        assert res["table_id"] == "p_2" and res["party_size"] == 3 and res["status"] == "confirmed"
        assert o["exception"] is False
    assert occ[1]["reservation"]["accepted_terms"] == TERMS0
    assert occ[2]["reservation"]["accepted_terms"] == terms_of(pb, v)
    assert occ[1]["reservation"]["revision"] == 1
    assert [x["event"] for x in hist(http, ada, occ[1]["reference"])["entries"]] == ["created"]
    refs = {x["reference"] for x in my_res(http, ada)}
    assert {o["reference"] for o in occ} <= refs
    err(http.post("/reservations", json=rb("p_2", f"{day(7)}T19:30", 2), headers=H(e["bob"], str(uuid.uuid4()))),
        409, "table_unavailable")
    rp = series(http, ada, body, key)
    assert rp.status_code == 200 and rp.json() == s
    g = http.get(f"/series/{s['series_id']}", headers=H(ada))
    assert g.status_code == 200 and g.json() == s
    err(http.get(f"/series/{s['series_id']}", headers=H(e["bob"])), 404, "not_found")
    err(http.get(f"/series/{s['series_id']}"), 404, "not_found")
    err(series(http, ada, {**body, "count": 2}), 409, "already_in_series")
    err(series(http, ada, {"anchor_reference": occ[1]["reference"], "count": 2, "interval_weeks": 1}), 409, "already_in_series")


def test_series_exceptions_and_revision(http, e):  # S3-51..S3-54
    ada = e["ada"]
    A = mk(http, ada, rb("p_3", f"{THU_S}T19:00", 2))
    key = str(uuid.uuid4())
    s = series(http, ada, {"anchor_reference": A["reference"], "count": 4, "interval_weeks": 2}, key).json()
    sid, occ = s["series_id"], s["occurrences"]
    assert [o["reservation"]["starts_at_local"][:10] for o in occ] == [day(0), day(14), day(28), day(42)]
    get = lambda: http.get(f"/series/{sid}", headers=H(ada)).json()
    assert http.patch(f"/reservations/{occ[1]['reference']}", json={"party_size": 2}, headers=H(ada)).status_code == 200
    assert get()["revision"] == 1 and get()["occurrences"][1]["exception"] is False  # no-op
    err(http.patch(f"/reservations/{occ[1]['reference']}", json={"party_size": 0}, headers=H(ada)), 422, "validation_failed")
    assert get()["revision"] == 1
    assert http.patch(f"/reservations/{occ[1]['reference']}", json={"party_size": 4}, headers=H(ada)).status_code == 200
    g = get()
    assert g["revision"] == 2 and g["occurrences"][1]["exception"] is True
    assert g["occurrences"][1]["reservation"]["party_size"] == 4
    assert http.patch(f"/reservations/{occ[1]['reference']}", json={"party_size": 2}, headers=H(ada)).status_code == 200
    g = get()
    assert g["revision"] == 3 and g["occurrences"][1]["exception"] is True  # permanent
    assert http.post(f"/reservations/{occ[2]['reference']}/cancel", headers=H(ada)).status_code == 200
    g = get()
    assert g["revision"] == 4 and g["occurrences"][2]["exception"] is False
    assert g["occurrences"][2]["reservation"]["status"] == "cancelled"
    assert http.post(f"/reservations/{occ[2]['reference']}/cancel", headers=H(ada)).status_code == 200
    assert get()["revision"] == 4
    assert http.post(f"/reservations/{A['reference']}/cancel", headers=H(ada)).status_code == 200
    g = get()
    assert g["revision"] == 5
    assert [o["reservation"]["status"] for o in g["occurrences"]] == ["cancelled", "confirmed", "cancelled", "confirmed"]
    assert [o["index"] for o in g["occurrences"]] == [0, 1, 2, 3]
    assert [o["reference"] for o in g["occurrences"]] == [o["reference"] for o in occ]
    rp = series(http, ada, {"anchor_reference": A["reference"], "count": 4, "interval_weeks": 2}, key)
    assert rp.status_code == 200 and rp.json() == s
    assert get()["revision"] == 5
    # moves: two occurrences of one series in one batch -> series revision +1, both become exceptions
    m = http.post("/reservation-moves", json={"moves": [{"reference": occ[1]["reference"], "table_id": "p_2"},
                                                       {"reference": occ[3]["reference"], "table_id": "p_2"}]},
                  headers=H(ada, str(uuid.uuid4())))
    assert m.status_code == 201, m.text
    g = get()
    assert g["revision"] == 6 and g["occurrences"][3]["exception"] is True


def test_adopt_errors(http, e):  # S3-46, S3-47
    ada, bob = e["ada"], e["bob"]
    A = mk(http, ada, rb("p_2", f"{THU_S}T19:00"))
    Bb = mk(http, bob, rb("p_3", f"{THU_S}T19:00"))
    C = mk(http, ada, rb("p_1", f"{THU_S}T19:00"))
    assert http.post(f"/reservations/{C['reference']}/cancel", headers=H(ada)).status_code == 200
    near = mk(http, ada, {"restaurant_id": "r_now", "table_id": "c_1", "starts_at_local": now_slot(60), "party_size": 2})
    ok = {"anchor_reference": A["reference"], "count": 2, "interval_weeks": 1}
    err(http.post("/series", json=ok, headers={"Idempotency-Key": "x"}), 401, "unauthenticated")
    err(http.post("/series", json=ok, headers=H(ada)), 400, "missing_idempotency_key")
    err(http.post("/series", json=ok, headers=H(ada, "k" * 256)), 422, "validation_failed")
    err(series(http, ada, {**ok, "anchor_reference": "NOPE99"}), 404, "not_found")
    err(series(http, ada, {**ok, "anchor_reference": Bb["reference"]}), 404, "not_found")
    err(series(http, ada, {**ok, "anchor_reference": C["reference"]}), 409, "reservation_cancelled")
    err(series(http, ada, {**ok, "anchor_reference": near["reference"]}), 409, "cutoff_passed")
    for bad in [{"count": 1}, {"count": 13}, {"count": True}, {"count": 2.5}, {"interval_weeks": 0},
                {"interval_weeks": 5}, {"interval_weeks": True}, {"count": None}]:
        err(series(http, ada, {**ok, **bad}), 422, "validation_failed")
    b = dict(ok)
    del b["count"]
    err(series(http, ada, b), 422, "validation_failed")
    assert len(my_res(http, ada)) == 3
    s = series(http, ada, {**ok, "count": 12, "interval_weeks": 4})
    assert s.status_code == 201, s.text
    assert len(s.json()["occurrences"]) == 12


def test_adopt_atomic_and_first_failure(http, e):  # S3-55, S3-56
    ada, bob, mgr = e["ada"], e["bob"], e["mgr"]
    A = mk(http, ada, rb("p_2", f"{THU_S}T19:00"))
    blocker = mk(http, bob, rb("p_2", f"{day(14)}T19:30"))
    closed = pol(day(21), hours=[{"weekday": "mon", "opens": "18:00", "closes": "23:00"}])
    assert publish(http, mgr, closed).status_code == 201
    key = str(uuid.uuid4())
    body = {"anchor_reference": A["reference"], "count": 4, "interval_weeks": 1}
    err(series(http, ada, body, key), 409, "table_unavailable")  # occurrence 2 conflicts before occurrence 3 is closed
    assert len(my_res(http, ada)) == 1 and get_res(http, ada, A["reference"]) == A
    assert len(hist(http, ada, A["reference"])["entries"]) == 1
    assert http.post(f"/reservations/{blocker['reference']}/cancel", headers=H(bob)).status_code == 200
    err(series(http, ada, body, key), 422, "outside_opening_hours")
    r = series(http, ada, {**body, "count": 3}, key)
    assert r.status_code == 201, r.text
    assert len(my_res(http, ada)) == 3


def test_adopt_dst(http, e):  # S3-57
    ada = e["ada"]
    fall = mk(http, ada, rb("d_1", "2026-10-18T02:30", 2, rest="r_dst"))
    s = series(http, ada, {"anchor_reference": fall["reference"], "count": 2, "interval_weeks": 1})
    assert s.status_code == 201, s.text
    o1 = s.json()["occurrences"][1]["reservation"]
    assert o1["starts_at_local"] == "2026-10-25T02:30" and o1["starts_at"].endswith("+02:00")
    same_instant_offset(o1["ends_at"], parse_ts("2026-10-25T03:00:00+01:00"))
    spring = mk(http, ada, rb("d_1", "2027-03-21T02:30", 2, rest="r_dst"))
    err(series(http, ada, {"anchor_reference": spring["reference"], "count": 3, "interval_weeks": 1}), 422, "invalid_local_time")
    assert len([x for x in my_res(http, ada) if x["restaurant_id"] == "r_dst"]) == 3


def test_combined_anchor_series(http, e):  # S3-58
    ada = e["ada"]
    A = mk(http, ada, rb(["p_2", "p_1"], f"{THU_S}T19:00", 5))
    s = series(http, ada, {"anchor_reference": A["reference"], "count": 2, "interval_weeks": 1})
    assert s.status_code == 201, s.text
    o1 = s.json()["occurrences"][1]["reservation"]
    assert sorted(o1["table_ids"]) == ["p_1", "p_2"] and "table_id" not in o1 and o1["party_size"] == 5


def test_series_burst_and_policy_burst(http, e):  # S3-C3 simultaneous use on new paths
    ada, mgr = e["ada"], e["mgr"]
    A = mk(http, ada, rb("p_3", f"{THU_S}T19:00"))
    key = str(uuid.uuid4())
    body = {"anchor_reference": A["reference"], "count": 3, "interval_weeks": 1}

    def f():
        with new_client() as c:
            return c.post("/series", json=body, headers=H(ada, key))
    rs = burst([f for _ in range(20)])
    codes = [x.status_code for x in rs]
    assert codes.count(201) == 1 and codes.count(200) == 19, codes
    assert all(x.json() == rs[0].json() for x in rs)
    assert len(my_res(http, ada)) == 3
    B = mk(http, ada, rb("p_1", f"{THU_S}T19:00"))
    rs = burst([lambda: series(new_client(), ada, {"anchor_reference": B["reference"], "count": 2, "interval_weeks": 1})
                for _ in range(10)])
    codes = [x.status_code for x in rs]
    assert codes.count(201) == 1, codes
    for x in rs:
        if x.status_code != 201:
            err(x, 409, "already_in_series")

    def g(i):
        def h():
            with new_client() as c:
                return publish(c, mgr, pol(day(-30 + i)))
        return h
    rs = burst([g(i) for i in range(20)])
    assert all(x.status_code == 201 for x in rs), [x.status_code for x in rs]
    assert sorted(x.json()["policy_version"] for x in rs) == list(range(1, 21))


def nested(depth):
    v = 0
    for _ in range(depth):
        v = [v]
    return v


def test_new_paths_f1_and_errors(http, e):  # S3-C1, S3-C2 (F1 on new entry points)
    ada, mgr = e["ada"], e["mgr"]
    A = mk(http, ada, rb("p_3", f"{THU_S}T19:00"))
    r = series(http, ada, {"anchor_reference": A["reference"], "count": 2, "interval_weeks": 1, "u": nested(3000)})
    assert r.status_code < 500
    r = publish(http, mgr, {**pol(day(-7)), "u": nested(3000)})
    assert r.status_code < 500
    for path, hdr in [("/series", H(ada, "d1")), ("/restaurants/r_pol/policies", H(mgr, "d2"))]:
        x = http.post(path, content=b"{", headers={**hdr, "Content-Type": "application/json"})
        err(x, 400, "malformed_request")
        x = http.post(path, content=b"[1]", headers={**hdr, "Content-Type": "application/json"})
        err(x, 400, "malformed_request")
    err(series(http, ada, {"anchor_reference": 5, "count": 2, "interval_weeks": 1}), 400, "malformed_request")
    assert http.get("/health").status_code == 200
