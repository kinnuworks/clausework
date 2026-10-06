"""Stage-2 API clauses S2-10..S2-45 (combined tables), carried cross-cutting rules, F1, ruling S1-97."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from conftest import FRI_S, H, THU_S, avail, burst, err, get_res, login, my_res, new_client, now_slot, parse_ts, reset
from s2lib import LAT, lb, ref_options, s2_fixture


@pytest.fixture
def s2(http):
    reset(http, s2_fixture())
    return {"ada": login(http, "ada@example.com", "correct horse"),
            "bob": login(http, "bob@example.com", "battery staple")}


def post(http, tok, b, key=None):
    return http.post("/reservations", json=b, headers=H(tok, key or str(uuid.uuid4())))


def ok(http, tok, b):
    r = post(http, tok, b)
    assert r.status_code == 201, r.text
    return r.json()


def opts_at(http, d, party, loc, rest="r_lat"):
    for s in avail(http, rest, d, party)["slots"]:
        if s["starts_at_local"] == loc:
            return s
    return None


def test_available_options_basic(http, s2):  # S2-12, S2-13, S2-14
    s = opts_at(http, THU_S, 5, f"{THU_S}T19:00")
    assert s["available_table_ids"] == ["w_4"]
    assert s["available_options"] == [
        {"table_ids": ["w_4"], "capacity": 6},
        {"table_ids": ["w_1", "w_2"], "capacity": 6},
        {"table_ids": ["w_3", "w_2"], "capacity": 6},
        {"table_ids": ["w_4", "w_1"], "capacity": 8}]
    s7 = opts_at(http, THU_S, 7, f"{THU_S}T19:00")
    assert s7["available_table_ids"] == [] and s7["available_options"] == [{"table_ids": ["w_4", "w_1"], "capacity": 8}]
    s9 = opts_at(http, THU_S, 9, f"{THU_S}T19:00")
    assert s9["available_options"] == [] and s9["available_table_ids"] == []
    s2_ = opts_at(http, THU_S, 2, f"{THU_S}T19:00")
    assert [o["table_ids"] for o in s2_["available_options"]] == [["w_1"], ["w_2"], ["w_3"], ["w_4"], ["w_1", "w_2"],
                                                                  ["w_3", "w_2"], ["w_4", "w_1"]]
    ok(http, s2["ada"], lb("w_2", party=2))
    s = opts_at(http, THU_S, 5, f"{THU_S}T19:00")
    assert s["available_options"] == [{"table_ids": ["w_4"], "capacity": 6}, {"table_ids": ["w_4", "w_1"], "capacity": 8}]


def test_options_reference_model(http, s2):  # S2-13 best-answer reference
    ada = s2["ada"]
    plan = [(["w_1", "w_2"], f"{THU_S}T18:00", 5), ("w_4", f"{THU_S}T19:30", 6), (["w_3"], f"{THU_S}T20:30", 2),
            (["w_2", "w_3"], f"{FRI_S}T21:30", 6), ("w_1", f"{FRI_S}T22:00", 2), (["w_4", "w_1"], f"{FRI_S}T18:30", 7)]
    booked = []
    for tables, loc, p in plan:
        r = ok(http, ada, lb(tables, loc, p))
        booked.append((set(r["table_ids"]), parse_ts(r["starts_at"]).astimezone(timezone.utc)))
    for d in (THU_S, FRI_S):
        for party in range(1, 10):
            ref = ref_options(LAT, d, party, booked)
            api = avail(http, "r_lat", d, party)["slots"]
            assert [x["starts_at_local"] for x in api] == list(ref)
            for x in api:
                singles, opts = ref[x["starts_at_local"]]
                assert x["available_table_ids"] == singles, (d, party, x["starts_at_local"])
                assert x["available_options"] == opts, (d, party, x["starts_at_local"])


def test_combo_booking_and_shape(http, s2):  # S2-15..S2-18, S2-23
    ada, bob = s2["ada"], s2["bob"]
    r = ok(http, ada, lb(["w_1", "w_2"], party=6))
    assert sorted(r["table_ids"]) == ["w_1", "w_2"] and "table_id" not in r
    assert get_res(http, ada, r["reference"]) == r
    err(post(http, bob, lb("w_1", f"{THU_S}T19:30")), 409, "table_unavailable")
    err(post(http, bob, lb(["w_2"], f"{THU_S}T20:00")), 409, "table_unavailable")
    err(post(http, bob, lb(["w_3", "w_2"], party=6)), 409, "table_unavailable")
    assert post(http, bob, lb("w_1", f"{THU_S}T20:30")).status_code == 201
    one = ok(http, bob, lb(["w_3"], f"{THU_S}T19:00"))
    assert one["table_ids"] == ["w_3"] and one["table_id"] == "w_3"
    legacy = ok(http, bob, lb("w_4", f"{THU_S}T19:00"))
    assert legacy["table_ids"] == ["w_4"] and legacy["table_id"] == "w_4"
    rev = ok(http, ada, lb(["w_2", "w_1"], f"{FRI_S}T19:00", 6))  # unordered pair
    assert sorted(rev["table_ids"]) == ["w_1", "w_2"]
    lst = my_res(http, ada)
    assert all("table_ids" in x for x in lst)
    assert all(("table_id" in x) == (len(x["table_ids"]) == 1) for x in lst)


def test_combo_errors(http, s2):  # S2-19..S2-22, S2-40
    ada = s2["ada"]
    err(post(http, ada, lb(["w_1", "w_3"])), 422, "combination_not_allowed")
    err(post(http, ada, lb(["w_2", "w_4"])), 422, "combination_not_allowed")
    err(post(http, ada, lb(["w_1", "w_2", "w_3"])), 422, "combination_not_allowed")
    err(post(http, ada, lb(["w_1", "w_1"])), 422, "validation_failed")
    err(post(http, ada, lb(["w_1", "w_2"], party=7)), 422, "party_exceeds_capacity")
    err(post(http, ada, {**lb(["w_1", "w_2"]), "table_id": "w_1"}), 422, "validation_failed")
    err(post(http, ada, {**lb("w_1"), "table_ids": ["w_1"]}), 422, "validation_failed")
    b = lb("w_1")
    del b["table_id"]
    err(post(http, ada, b), 422, "validation_failed")
    err(post(http, ada, lb([])), 422, "validation_failed")
    err(post(http, ada, {"restaurant_id": "r_lat", "table_ids": "w_1", "starts_at_local": f"{THU_S}T19:00",
                         "party_size": 2}), 400, "malformed_request")
    err(post(http, ada, lb(["w_1", "w_2"], f"{THU_S}T19:15", 4)), 422, "not_on_slot_grid")
    err(post(http, ada, lb(["w_1", "w_2"], party="4")), 422, "validation_failed")
    assert my_res(http, ada) == []
    s = opts_at(http, THU_S, 2, f"{THU_S}T19:00")
    assert len(s["available_options"]) == 7


def test_cancel_frees_all(http, s2):  # S2-24
    ada = s2["ada"]
    r = ok(http, ada, lb(["w_4", "w_1"], party=8))
    assert opts_at(http, THU_S, 1, f"{THU_S}T19:00")["available_table_ids"] == ["w_2", "w_3"]
    c = http.post(f"/reservations/{r['reference']}/cancel", headers=H(ada))
    assert c.status_code == 200 and c.json()["status"] == "cancelled"
    assert opts_at(http, THU_S, 1, f"{THU_S}T19:00")["available_table_ids"] == ["w_1", "w_2", "w_3", "w_4"]


def test_patch_table_ids(http, s2):  # S2-25..S2-27
    ada, bob = s2["ada"], s2["bob"]
    r = ok(http, ada, lb("w_2", party=4))
    ref = r["reference"]
    p = http.patch(f"/reservations/{ref}", json={"table_ids": ["w_1", "w_2"], "party_size": 6}, headers=H(ada))
    assert p.status_code == 200, p.text
    assert sorted(p.json()["table_ids"]) == ["w_1", "w_2"] and "table_id" not in p.json()
    assert p.json()["reference"] == ref and p.json()["reservation_id"] == r["reservation_id"]
    # shift onto a pair sharing w_2 with itself: must release old and take new together
    p = http.patch(f"/reservations/{ref}", json={"table_ids": ["w_3", "w_2"], "party_size": 5}, headers=H(ada))
    assert p.status_code == 200, p.text
    assert opts_at(http, THU_S, 1, f"{THU_S}T19:00")["available_table_ids"] == ["w_1", "w_4"]
    before = get_res(http, ada, ref)
    ok(http, bob, lb("w_4", f"{THU_S}T19:00"))
    for patch, st, code in [({"table_ids": ["w_1", "w_3"]}, 422, "combination_not_allowed"),
                            ({"table_ids": ["w_1", "w_2", "w_3"]}, 422, "combination_not_allowed"),
                            ({"table_ids": ["w_2", "w_2"]}, 422, "validation_failed"),
                            ({"table_ids": ["w_4", "w_1"]}, 409, "table_unavailable"),
                            ({"table_ids": ["w_1", "w_2"], "party_size": 7}, 422, "party_exceeds_capacity"),
                            ({"table_ids": ["w_1"], "table_id": "w_1"}, 422, "validation_failed")]:
        err(http.patch(f"/reservations/{ref}", json=patch, headers=H(ada)), st, code)
        assert get_res(http, ada, ref) == before, patch
    p = http.patch(f"/reservations/{ref}", json={"table_id": "w_1", "party_size": 2}, headers=H(ada))
    assert p.status_code == 200, p.text
    assert p.json()["table_ids"] == ["w_1"] and p.json()["table_id"] == "w_1"
    err(http.patch(f"/reservations/{ref}", json={"table_ids": ["w_1", "w_2"]}, headers=H(bob)), 404, "not_found")


def test_moves_with_table_ids(http, s2):  # S2-28, S2-29
    ada = s2["ada"]
    A = ok(http, ada, lb(["w_1", "w_2"], party=6))
    B = ok(http, ada, lb("w_4", party=4))
    key = str(uuid.uuid4())
    m = http.post("/reservation-moves", json={"moves": [
        {"reference": A["reference"], "table_ids": ["w_4", "w_1"]},
        {"reference": B["reference"], "table_ids": ["w_2"]}]}, headers=H(ada, key))
    assert m.status_code == 201, m.text
    out = m.json()["reservations"]
    assert sorted(out[0]["table_ids"]) == ["w_1", "w_4"] and out[1]["table_ids"] == ["w_2"] and out[1]["table_id"] == "w_2"
    before = [get_res(http, ada, x["reference"]) for x in (A, B)]
    for moves, st, code in [
        ([{"reference": A["reference"], "table_ids": ["w_1", "w_3"]}], 422, "combination_not_allowed"),
        ([{"reference": B["reference"], "table_ids": ["w_4"]}, {"reference": A["reference"]}], 409, "table_unavailable"),
        ([{"reference": A["reference"], "table_ids": ["w_3", "w_2"]}, {"reference": B["reference"]}], 409, "table_unavailable"),
    ]:
        err(http.post("/reservation-moves", json={"moves": moves}, headers=H(ada, str(uuid.uuid4()))), st, code)
        assert [get_res(http, ada, x["reference"]) for x in (A, B)] == before
    r2 = http.post("/reservation-moves", json={"moves": [
        {"reference": A["reference"], "table_ids": ["w_4", "w_1"]},
        {"reference": B["reference"], "table_ids": ["w_2"]}]}, headers=H(ada, key))
    assert r2.status_code == 200 and r2.json() == m.json()


def test_seeded_table_ids_and_status(http):  # S2-08, S2-09
    seeds = [
        {"id": "res_a", "reference": "SEEDA1", "user_id": "u_ada", "restaurant_id": "r_lat", "table_ids": ["w_1", "w_2"],
         "starts_at_local": f"{THU_S}T19:00", "party_size": 5},
        {"id": "res_b", "reference": "SEEDB1", "user_id": "u_ada", "restaurant_id": "r_lat", "table_id": "w_4",
         "starts_at_local": f"{THU_S}T19:00", "party_size": 4, "status": "cancelled"},
        {"id": "res_c", "reference": "SEEDC1", "user_id": "u_bob", "restaurant_id": "r_lat", "table_id": "w_3",
         "starts_at_local": f"{THU_S}T21:00", "party_size": 2},
    ]
    reset(http, s2_fixture(seeds))
    ada = login(http, "ada@example.com", "correct horse")
    a = get_res(http, ada, "SEEDA1")
    assert sorted(a["table_ids"]) == ["w_1", "w_2"] and a["status"] == "confirmed" and "table_id" not in a
    b = get_res(http, ada, "SEEDB1")
    assert b["status"] == "cancelled" and b["table_ids"] == ["w_4"]
    s = opts_at(http, THU_S, 1, f"{THU_S}T19:00")
    assert s["available_table_ids"] == ["w_3", "w_4"]
    s21 = opts_at(http, THU_S, 1, f"{THU_S}T21:00")
    assert s21["available_table_ids"] == ["w_1", "w_2", "w_4"]


def test_idempotency_with_table_ids(http, s2):  # S2-30 (carried §7)
    ada = s2["ada"]
    key = str(uuid.uuid4())
    b = lb(["w_1", "w_2"], party=6)
    r1 = post(http, ada, b, key)
    assert r1.status_code == 201
    r2 = post(http, ada, dict(reversed(list(b.items()))), key)
    assert r2.status_code == 200 and r2.json() == r1.json()
    err(post(http, ada, lb(["w_2", "w_1"], party=6), key), 409, "idempotency_key_reuse")  # array order is part of the JSON value
    err(post(http, ada, lb(["w_1", "w_3"], party=6), key), 409, "idempotency_key_reuse")
    err(http.post("/reservations", json=b, headers=H(ada)), 400, "missing_idempotency_key")
    assert len(my_res(http, ada)) == 1


def test_combo_concurrency(http, s2):  # S2-41 serializability with combinations
    toks = [s2["ada"], s2["bob"]]
    reqs = [["w_1", "w_2"]] * 15 + [["w_1"]] * 10 + [["w_2"]] * 10 + [["w_3", "w_2"]] * 10 + [["w_4", "w_1"]] * 5
    starts = ["19:00", "19:30", "20:00"]

    def mk(i, tables):
        st = starts[i % 3]
        party = 2

        def f():
            with new_client() as c:
                return c.post("/reservations", json=lb(tables, f"{THU_S}T{st}", party),
                              headers=H(toks[i % 2], str(uuid.uuid4())))
        return f, set(tables), st
    made = [mk(i, t) for i, t in enumerate(reqs)]
    rs = burst([m[0] for m in made])
    assert all(r.status_code in (201, 409) for r in rs), [r.status_code for r in rs]

    def iv(st):
        s = datetime.fromisoformat(f"{THU_S}T{st}")
        return s, s + timedelta(minutes=90)

    def clash(a, b):
        return bool(a[0] & b[0]) and iv(a[1])[0] < iv(b[1])[1] and iv(b[1])[0] < iv(a[1])[1]
    won = [(m[1], m[2]) for m, r in zip(made, rs) if r.status_code == 201]
    for i, a in enumerate(won):
        for b in won[i + 1:]:
            assert not clash(a, b), won
    for m, r in zip(made, rs):
        if r.status_code == 409:
            err(r, 409, "table_unavailable")
            assert any(clash((m[1], m[2]), w) for w in won)
    total = [x for t in toks for x in my_res(http, t) if x["status"] == "confirmed"]
    assert len(total) == len(won)


def nested(depth):
    v = 0
    for _ in range(depth):
        v = [v]
    return v


def test_f1_deeply_nested_ignored_field(http, s2):  # S2-42 (F1): never 5xx; unknown fields ignored
    ada = s2["ada"]
    r = post(http, ada, {**lb("w_1"), "extra": nested(512)})
    assert r.status_code == 201, r.text
    ref = r.json()["reference"]
    m = http.post("/reservation-moves", json={"moves": [{"reference": ref, "x": nested(512)}], "extra": nested(512)},
                  headers=H(ada, str(uuid.uuid4())))
    assert m.status_code == 201, m.text
    p = http.patch(f"/reservations/{ref}", json={"party_size": 2, "extra": nested(512)}, headers=H(ada))
    assert p.status_code == 200, p.text
    s = http.post("/auth/signup", json={"email": "deep@example.com", "password": "12345678", "display_name": "D",
                                        "extra": nested(512)})
    assert s.status_code == 201, s.text
    deep = "{\"extra\":" + "[" * 100000 + "]" * 100000 + "}"
    targets = [("POST", "/reservations", H(ada, str(uuid.uuid4()))), ("POST", "/reservation-moves", H(ada, str(uuid.uuid4()))),
               ("PATCH", f"/reservations/{ref}", H(ada)), ("POST", "/auth/signup", {}), ("POST", "/auth/login", {}),
               ("POST", "/_test/import", {})]
    for method, path, hdr in targets:
        x = http.request(method, path, content=deep.encode(), headers={**hdr, "Content-Type": "application/json"})
        assert x.status_code < 500, (path, x.status_code)
        if x.status_code >= 400:
            assert isinstance(x.json().get("error", {}).get("code"), str), (path, x.text)
    assert http.get("/health").status_code == 200
    assert get_res(http, ada, ref)["status"] == "confirmed"


def test_ruling_s1_97_moves_precedence(http, s2):  # S1-97 carried into stage 2
    ada = s2["ada"]
    A = ok(http, ada, lb("w_1"))
    assert http.post(f"/reservations/{A['reference']}/cancel", headers=H(ada)).status_code == 200
    err(http.post("/reservation-moves", json={"moves": [{"reference": A["reference"]}, {"reference": "NOPE99"}]},
                  headers=H(ada, str(uuid.uuid4()))), 409, "reservation_cancelled")
    err(http.post("/reservation-moves", json={"moves": [{"reference": "NOPE99"}, {"reference": A["reference"]}]},
                  headers=H(ada, str(uuid.uuid4()))), 404, "not_found")
    near = ok(http, ada, {"restaurant_id": "r_now", "table_id": "c_1", "starts_at_local": now_slot(60), "party_size": 2})
    err(http.post("/reservation-moves", json={"moves": [{"reference": near["reference"], "table_ids": ["c_1", "c_2"]}]},
                  headers=H(ada, str(uuid.uuid4()))), 409, "cutoff_passed")


def test_f1_regression_depth_3000(http, s2):  # S2-C6 / F1 regression: depth 3000 on both idempotent paths
    ada = s2["ada"]
    ref = ok(http, ada, lb("w_2", f"{FRI_S}T19:00"))["reference"]
    for path, payload in [("/reservations", {**lb("w_1", f"{FRI_S}T19:00"), "unknown": nested(3000)}),
                          ("/reservation-moves", {"moves": [{"reference": ref}], "unknown": nested(3000)})]:
        x = http.post(path, json=payload, headers=H(ada, str(uuid.uuid4())))
        assert x.status_code < 500, (path, x.status_code)
        if x.status_code >= 400:
            assert isinstance(x.json().get("error", {}).get("code"), str), (path, x.text)
    assert http.get("/health").status_code == 200
