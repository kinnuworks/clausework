"""Stage-3 policies (S3-20..S3-32), accepted terms / revision / expected_revision (S3-33..S3-39), moves (S3-70..S3-74)."""
import uuid

import pytest

from conftest import ALL_DAYS, H, THU_S, burst, err, get_res, new_client, now_slot, parse_ts
from s3lib import POL, TERMS0, day, hist, mk, pol, publish, rb, s3_env, terms_of


@pytest.fixture
def e(http):
    return s3_env(http)


def test_publish_permissions_and_versions(http, e):  # S3-20..S3-23
    mgr, ada = e["mgr"], e["ada"]
    err(publish(http, ada, pol(day(-7))), 403, "forbidden")
    err(http.post("/restaurants/r_pol/policies", json=pol(day(-7)), headers={"Idempotency-Key": "k"}), 401, "unauthenticated")
    err(publish(http, mgr, pol(day(-7)), rest="r_nope"), 404, "not_found")
    err(publish(http, mgr, pol(day(-7)), rest="r_lat"), 403, "forbidden")  # manager_user_ids defaults to []
    err(http.post("/restaurants/r_pol/policies", json=pol(day(-7)), headers=H(mgr)), 400, "missing_idempotency_key")
    key = str(uuid.uuid4())
    p1 = pol(day(-7), dur=60)
    r1 = publish(http, mgr, {**p1, "note": "ignored"}, key=key)
    assert r1.status_code == 201, r1.text
    j = r1.json()
    assert j["policy_version"] == 1 and all(j[k] == v for k, v in p1.items())
    rr = publish(http, mgr, {**p1, "note": "ignored"}, key=key)
    assert rr.status_code == 200 and rr.json() == j
    err(publish(http, mgr, pol(day(-6)), key=key), 409, "idempotency_key_reuse")
    r2 = publish(http, mgr, pol(day(14), slot=60))
    assert r2.status_code == 201 and r2.json()["policy_version"] == 2
    lst = http.get("/restaurants/r_pol/policies")
    assert lst.status_code == 200
    assert [x["policy_version"] for x in lst.json()["policies"]] == [1, 2]
    assert lst.json()["policies"][0]["effective_from"] == day(-7)
    det = http.get("/restaurants/r_pol").json()
    assert det["reservation_duration_minutes"] == 90 and det["slot_minutes"] == 30


def test_policy_validation_no_version(http, e):  # S3-24, S3-25
    mgr = e["mgr"]
    good = pol(day(-7))
    bads = []
    for k in good:
        bads.append({kk: v for kk, v in good.items() if kk != k})
    bads += [
        {**good, "effective_from": "2026-02-30"}, {**good, "effective_from": "2026-9-1"},
        {**good, "slot_minutes": 0}, {**good, "slot_minutes": 1441}, {**good, "slot_minutes": True},
        {**good, "slot_minutes": 2.5}, {**good, "reservation_duration_minutes": 0},
        {**good, "reservation_duration_minutes": 1441}, {**good, "cancellation_cutoff_minutes": -1},
        {**good, "cancellation_cutoff_minutes": 10081}, {**good, "cancellation_cutoff_minutes": False},
        {**good, "capacities": {"p_1": 2, "p_2": 4}}, {**good, "capacities": {"p_1": 2, "p_2": 4, "p_3": 6, "p_9": 2}},
        {**good, "capacities": {"p_1": 0, "p_2": 4, "p_3": 6}}, {**good, "capacities": {"p_1": 101, "p_2": 4, "p_3": 6}},
        {**good, "capacities": {"p_1": True, "p_2": 4, "p_3": 6}},
        {**good, "opening_hours": [{"weekday": "mon", "opens": "18:00", "closes": "23:00"},
                                   {"weekday": "mon", "opens": "12:00", "closes": "14:00"}]},
        {**good, "opening_hours": [{"weekday": "mon", "opens": "20:00", "closes": "18:00"}]},
        {**good, "opening_hours": [{"weekday": "xyz", "opens": "18:00", "closes": "23:00"}]},
    ]
    for b in bads:
        err(publish(http, mgr, b), 422, "validation_failed")
    assert http.get("/restaurants/r_pol/policies").json() == {"policies": []}
    assert publish(http, mgr, good).json()["policy_version"] == 1
    assert publish(http, mgr, {**good, "cancellation_cutoff_minutes": 0, "slot_minutes": 1440,
                               "reservation_duration_minutes": 1440}).json()["policy_version"] == 2
    assert publish(http, mgr, {**good, "cancellation_cutoff_minutes": 10080}).json()["policy_version"] == 3


def test_policy_selection(http, e):  # S3-26..S3-29, S3-33
    mgr, ada = e["mgr"], e["ada"]
    early = mk(http, ada, rb("p_2", f"{THU_S}T19:00", 2))  # before any publication: policy 0
    pa = pol(day(-7), dur=120)
    pb = pol(day(7), slot=60, dur=60)
    pc = pol(day(-7), dur=60, caps={"p_1": 3, "p_2": 4, "p_3": 6})
    assert publish(http, mgr, pa).json()["policy_version"] == 1
    assert publish(http, mgr, pb).json()["policy_version"] == 2
    assert publish(http, mgr, pc).json()["policy_version"] == 3  # same date as pa: greater version wins
    assert get_res(http, ada, early["reference"]) == early
    assert len(hist(http, ada, early["reference"])["entries"]) == 1
    r = mk(http, ada, rb("p_1", f"{THU_S}T21:00", 3))  # p_1 capacity 3 under v3
    assert r["accepted_terms"] == terms_of(pc, 3)
    assert (parse_ts(r["ends_at"]) - parse_ts(r["starts_at"])).total_seconds() == 3600
    old = mk(http, ada, rb("p_3", f"{day(-14)}T19:00", 2))
    assert old["accepted_terms"] == TERMS0
    nxt = mk(http, ada, rb("p_3", f"{day(7)}T19:00", 2))
    assert nxt["accepted_terms"] == terms_of(pb, 2)
    err(http.post("/reservations", json=rb("p_3", f"{day(7)}T19:30", 2), headers=H(ada, str(uuid.uuid4()))),
        422, "not_on_slot_grid")
    err(http.post("/reservations", json=rb("p_1", f"{day(-14)}T21:00", 3), headers=H(ada, str(uuid.uuid4()))),
        422, "party_exceeds_capacity")
    s = http.get("/availability", params={"restaurant_id": "r_pol", "date": day(7), "party_size": 2}).json()["slots"]
    assert [x["starts_at_local"][-5:] for x in s] == ["18:00", "19:00", "20:00", "21:00", "22:00"]


def test_amendment_reselects_policy(http, e):  # S3-34, S3-35
    mgr, ada = e["mgr"], e["ada"]
    r = mk(http, ada, rb("p_1", f"{day(-14)}T19:00", 2))
    pc = pol(day(-7), dur=60, caps={"p_1": 1, "p_2": 4, "p_3": 6})
    v = publish(http, mgr, pc).json()["policy_version"]
    before = get_res(http, ada, r["reference"])
    err(http.patch(f"/reservations/{r['reference']}", json={"starts_at_local": f"{THU_S}T19:00"}, headers=H(ada)),
        422, "party_exceeds_capacity")  # all resulting fields validated against the new date's policy
    assert get_res(http, ada, r["reference"]) == before
    p = http.patch(f"/reservations/{r['reference']}", json={"starts_at_local": f"{THU_S}T19:00", "party_size": 1},
                   headers=H(ada))
    assert p.status_code == 200, p.text
    j = p.json()
    assert j["revision"] == 2 and j["accepted_terms"] == terms_of(pc, v)
    assert (parse_ts(j["ends_at"]) - parse_ts(j["starts_at"])).total_seconds() == 3600
    h = hist(http, ada, r["reference"])["entries"]
    assert h[0]["accepted_terms"] == TERMS0 and h[1]["accepted_terms"] == terms_of(pc, v)


def test_accepted_cutoff_rules(http, e):  # S3-36, S3-37
    mgr, ada = e["mgr"], e["ada"]
    strict = mk(http, ada, {"restaurant_id": "r_now", "table_id": "c_1", "starts_at_local": now_slot(60), "party_size": 2})
    base_hours = ALL_DAYS("00:00", "23:30")
    relaxed = {"effective_from": "2020-01-01", "slot_minutes": 15, "reservation_duration_minutes": 60,
               "cancellation_cutoff_minutes": 0, "opening_hours": base_hours, "capacities": {"c_1": 4, "c_2": 4}}
    assert publish(http, mgr, relaxed, rest="r_now").status_code == 201
    # accepted (old) cutoff still governs the strict booking
    err(http.post(f"/reservations/{strict['reference']}/cancel", headers=H(ada)), 409, "cutoff_passed")
    err(http.patch(f"/reservations/{strict['reference']}", json={"party_size": 3}, headers=H(ada)), 409, "cutoff_passed")
    err(http.patch(f"/reservations/{strict['reference']}", json={"party_size": 2}, headers=H(ada)), 409, "cutoff_passed")  # no-op still needs editable
    err(http.patch(f"/reservations/{strict['reference']}", json={"expected_revision": 7}, headers=H(ada)), 409, "stale_revision")
    loose = mk(http, ada, {"restaurant_id": "r_now", "table_id": "c_2", "starts_at_local": now_slot(60), "party_size": 2})
    assert loose["accepted_terms"]["cancellation_cutoff_minutes"] == 0
    c = http.post(f"/reservations/{loose['reference']}/cancel", headers=H(ada))
    assert c.status_code == 200 and c.json()["status"] == "cancelled" and c.json()["revision"] == 2
    err(http.patch(f"/reservations/{loose['reference']}", json={"party_size": 2}, headers=H(ada)), 409, "reservation_cancelled")


def test_expected_revision(http, e):  # S3-38, S3-39
    ada = e["ada"]
    r = mk(http, ada, rb("p_3", f"{THU_S}T19:00", 2))
    ref = r["reference"]
    for bad in [0, -1, "1", True, 1.5]:
        err(http.patch(f"/reservations/{ref}", json={"party_size": 3, "expected_revision": bad}, headers=H(ada)),
            422, "validation_failed")
    err(http.patch(f"/reservations/{ref}", json={"party_size": 3, "expected_revision": 2}, headers=H(ada)), 409, "stale_revision")
    err(http.patch(f"/reservations/{ref}", json={"party_size": 0, "expected_revision": 2}, headers=H(ada)), 409, "stale_revision")
    p = http.patch(f"/reservations/{ref}", json={"party_size": 3, "expected_revision": 1, "x": 1}, headers=H(ada))
    assert p.status_code == 200 and p.json()["revision"] == 2
    assert get_res(http, ada, ref)["revision"] == 2

    def f(n):
        def g():
            with new_client() as c:
                return c.patch(f"/reservations/{ref}", json={"party_size": n, "expected_revision": 2}, headers=H(ada))
        return g
    rs = burst([f(n) for n in (1, 2, 4, 5, 6, 1, 2, 4, 5, 6)])
    codes = [x.status_code for x in rs]
    assert all(c in (200, 409) for c in codes), codes
    real = [x for x in rs if x.status_code == 200 and x.json()["revision"] == 3]
    assert len(real) <= 1, codes
    for x in rs:
        if x.status_code == 409:
            err(x, 409, "stale_revision")
    final = get_res(http, ada, ref)
    assert final["revision"] == 2 + len(real)
    assert len(hist(http, ada, ref)["entries"]) == 2 + len(real)


def test_moves_under_policies(http, e):  # S3-70..S3-74
    mgr, ada = e["mgr"], e["ada"]
    A = mk(http, ada, rb("p_1", f"{THU_S}T19:00", 2))
    B = mk(http, ada, rb("p_2", f"{THU_S}T19:00", 2))
    C = mk(http, ada, rb("p_3", f"{THU_S}T21:00", 2))
    pc = pol(day(-7), dur=60)
    v = publish(http, mgr, pc).json()["policy_version"]
    key = str(uuid.uuid4())
    body = {"moves": [{"reference": A["reference"], "table_id": "p_2"}, {"reference": B["reference"], "table_id": "p_1"},
                      {"reference": C["reference"]}]}
    m = http.post("/reservation-moves", json=body, headers=H(ada, key))
    assert m.status_code == 201, m.text
    out = m.json()["reservations"]
    assert [x["revision"] for x in out] == [2, 2, 1]
    assert out[0]["accepted_terms"] == terms_of(pc, v) and out[2]["accepted_terms"] == TERMS0
    assert len(hist(http, ada, C["reference"])["entries"]) == 1
    assert hist(http, ada, A["reference"])["entries"][-1]["changes"] == [{"field": "table_id", "from": "p_1", "to": "p_2"}]
    snap = [get_res(http, ada, x["reference"]) for x in (A, B, C)]
    hs = [hist(http, ada, x["reference"]) for x in (A, B, C)]
    err(http.post("/reservation-moves", json={"moves": [{"reference": A["reference"], "table_id": "p_3"},
                                                        {"reference": B["reference"], "table_id": "p_3"}]},
                  headers=H(ada, str(uuid.uuid4()))), 409, "table_unavailable")
    err(http.post("/reservation-moves", json={"moves": [{"reference": A["reference"], "table_id": "p_3", "expected_revision": 1}]},
                  headers=H(ada, str(uuid.uuid4()))), 409, "stale_revision")
    err(http.post("/reservation-moves", json={"moves": [{"reference": A["reference"], "table_id": "p_3", "expected_revision": 0}]},
                  headers=H(ada, str(uuid.uuid4()))), 422, "validation_failed")
    r2 = http.post("/reservation-moves", json=body, headers=H(ada, key))
    assert r2.status_code == 200 and r2.json() == m.json()
    assert [get_res(http, ada, x["reference"]) for x in (A, B, C)] == snap
    assert [hist(http, ada, x["reference"]) for x in (A, B, C)] == hs
