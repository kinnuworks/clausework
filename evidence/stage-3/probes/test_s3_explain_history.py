"""Stage-3 explain=true (S3-01..S3-09), history (S3-10..S3-19), decision (S3-40..S3-42)."""
from datetime import timezone

import pytest

from conftest import H, THU_S, err, parse_ts, ref_slots
from s3lib import POL, TERMS0, day, hist, mk, pol, publish, rb, s3_env, terms_of


@pytest.fixture
def e(http):
    return s3_env(http)


def av(http, d, party, explain=None, rest="r_pol"):
    p = {"restaurant_id": rest, "date": d, "party_size": party}
    if explain is not None:
        p["explain"] = explain
    return http.get("/availability", params=p)


def test_explain_shape_and_reference(http, e):  # S3-01..S3-05
    ada = e["ada"]
    booked = []
    for t, loc in [("p_2", f"{THU_S}T19:00"), ("p_3", f"{THU_S}T21:00"), ("p_1", f"{THU_S}T18:00")]:
        r = mk(http, ada, rb(t, loc, 2))
        booked.append((t, parse_ts(r["starts_at"]).astimezone(timezone.utc)))
    for party in range(1, 8):
        r = av(http, THU_S, party, "true")
        assert r.status_code == 200, r.text
        free = {x[0]: set(x[2]) for x in ref_slots(POL, THU_S, 1, booked)}
        slots = r.json()["slots"]
        assert [s["starts_at_local"] for s in slots] == list(free)
        for s in slots:
            ex = s["explain"]
            assert [x["table_id"] for x in ex] == ["p_1", "p_2", "p_3"]
            for x, t in zip(ex, POL["tables"]):
                cap_ok = t["capacity"] >= party
                ov_ok = t["id"] in free[s["starts_at_local"]]
                assert x["rules"] == [{"rule": "capacity", "holds": cap_ok}, {"rule": "no_overlap", "holds": ov_ok}], x
                assert x["available"] is (cap_ok and ov_ok)
                assert x["policy_version"] == 0
            assert [x["table_id"] for x in ex if x["available"]] == s["available_table_ids"]
    plain = av(http, THU_S, 2).json()
    for s in plain["slots"]:
        assert "explain" not in s
        assert set(s) <= {"starts_at_local", "starts_at", "available_table_ids", "available_options"}


def test_explain_validation_and_closed(http, e):  # S3-06, S3-07
    for bad in ["false", "1", "", "TRUE", "yes", "True"]:
        err(av(http, THU_S, 2, bad), 422, "validation_failed")
    r = av(http, day(-1), 2, "true", rest="r_dst")  # Wednesday: r_dst closed
    assert r.status_code == 200 and r.json()["slots"] == []
    big = av(http, THU_S, 99, "true").json()["slots"]
    assert big and all(s["available_table_ids"] == [] and len(s["explain"]) == 3 for s in big)
    assert all(x["rules"][0] == {"rule": "capacity", "holds": False} for s in big for x in s["explain"])


def test_explain_uses_policy(http, e):  # S3-08
    r = publish(http, e["mgr"], pol(day(-7), caps={"p_1": 5, "p_2": 1, "p_3": 6}))
    assert r.status_code == 201, r.text
    v = r.json()["policy_version"]
    s = av(http, THU_S, 3, "true").json()["slots"][0]
    assert [x["policy_version"] for x in s["explain"]] == [v, v, v]
    assert [x["rules"][0]["holds"] for x in s["explain"]] == [True, False, True]
    assert s["available_table_ids"] == ["p_1", "p_3"]


def test_history_rules(http, e):  # S3-10..S3-15
    ada = e["ada"]
    key = "hist-key-1"
    b = rb("p_2", f"{THU_S}T19:00", 3)
    r = http.post("/reservations", json=b, headers=H(ada, key))
    assert r.status_code == 201
    res = r.json()
    ref = res["reference"]
    assert res["revision"] == 1 and res["accepted_terms"] == TERMS0
    h = hist(http, ada, ref)
    assert h["reference"] == ref and len(h["entries"]) == 1
    c = h["entries"][0]
    assert c["seq"] == 1 and c["event"] == "created" and c["revision"] == 1 and c["accepted_terms"] == TERMS0
    assert c["changes"] == [{"field": "table_id", "from": None, "to": "p_2"},
                            {"field": "starts_at_local", "from": None, "to": f"{THU_S}T19:00"},
                            {"field": "party_size", "from": None, "to": 3}]
    parse_ts(c["at"])
    assert http.post("/reservations", json=b, headers=H(ada, key)).status_code == 200  # replay records nothing
    p = http.patch(f"/reservations/{ref}", json={"table_id": "p_3"}, headers=H(ada))
    assert p.status_code == 200 and p.json()["revision"] == 2
    p = http.patch(f"/reservations/{ref}", json={"party_size": 4, "starts_at_local": f"{THU_S}T20:00", "table_id": "p_3"},
                   headers=H(ada))
    assert p.status_code == 200 and p.json()["revision"] == 3
    n = http.patch(f"/reservations/{ref}", json={"party_size": 4, "table_id": "p_3", "starts_at_local": f"{THU_S}T20:00"},
                   headers=H(ada))
    assert n.status_code == 200 and n.json()["revision"] == 3  # no-op
    err(http.patch(f"/reservations/{ref}", json={"party_size": 0}, headers=H(ada)), 422, "validation_failed")
    c1 = http.post(f"/reservations/{ref}/cancel", headers=H(ada))
    assert c1.status_code == 200 and c1.json()["revision"] == 4
    c2 = http.post(f"/reservations/{ref}/cancel", headers=H(ada))
    assert c2.status_code == 200 and c2.json()["revision"] == 4
    h = hist(http, ada, ref)["entries"]
    assert [x["seq"] for x in h] == [1, 2, 3, 4]
    assert [x["event"] for x in h] == ["created", "changed", "changed", "cancelled"]
    assert [x["revision"] for x in h] == [1, 2, 3, 4]
    assert h[1]["changes"] == [{"field": "table_id", "from": "p_2", "to": "p_3"}]
    assert h[2]["changes"] == [{"field": "starts_at_local", "from": f"{THU_S}T19:00", "to": f"{THU_S}T20:00"},
                               {"field": "party_size", "from": 3, "to": 4}]
    assert h[3]["changes"] == []
    ats = [parse_ts(x["at"]) for x in h]
    assert ats == sorted(ats)
    # replay still returns the original response, revision 1
    rp = http.post("/reservations", json=b, headers=H(ada, key))
    assert rp.status_code == 200 and rp.json() == res


def test_history_and_decision_visibility(http, e):  # S3-16, S3-40..S3-42
    ada, bob, mgr = e["ada"], e["bob"], e["mgr"]
    r = mk(http, ada, rb("p_1", f"{THU_S}T19:00"))
    ref = r["reference"]
    for path in (f"/reservations/{ref}/history", f"/reservations/{ref}/decision"):
        err(http.get(path, headers=H(bob)), 404, "not_found")
        err(http.get(path, headers=H(mgr)), 404, "not_found")
        err(http.get(path), 404, "not_found")
        err(http.get(path, headers={"Authorization": "Bearer bogus"}), 404, "not_found")
    err(http.get("/reservations/NOPE99/history", headers=H(ada)), 404, "not_found")
    d = http.get(f"/reservations/{ref}/decision", headers=H(ada))
    assert d.status_code == 200 and d.json() == {"reference": ref, "revision": 1, "accepted_terms": TERMS0}
    assert http.post(f"/reservations/{ref}/cancel", headers=H(ada)).status_code == 200
    d = http.get(f"/reservations/{ref}/decision", headers=H(ada)).json()
    assert d["revision"] == 2 and d["accepted_terms"] == TERMS0
    assert [x["event"] for x in hist(http, ada, ref)["entries"]] == ["created", "cancelled"]


def test_combined_history(http, e):  # S3-60..S3-63
    ada = e["ada"]
    r = mk(http, ada, rb(["p_1", "p_2"], f"{THU_S}T19:00", 5))  # declared order is ["p_2","p_1"]
    ref = r["reference"]
    assert r["accepted_terms"]["capacities"] == {"p_1": 2, "p_2": 4, "p_3": 6}
    h = hist(http, ada, ref)["entries"]
    assert h[0]["changes"] == [{"field": "table_ids", "from": None, "to": ["p_2", "p_1"]},
                               {"field": "starts_at_local", "from": None, "to": f"{THU_S}T19:00"},
                               {"field": "party_size", "from": None, "to": 5}]
    p = http.patch(f"/reservations/{ref}", json={"table_ids": ["p_2", "p_1"]}, headers=H(ada))
    assert p.status_code == 200 and p.json()["revision"] == 1  # reversed input pair: same set, no amendment
    p = http.patch(f"/reservations/{ref}", json={"table_ids": ["p_3"]}, headers=H(ada))
    assert p.status_code == 200 and p.json()["revision"] == 2
    p = http.patch(f"/reservations/{ref}", json={"table_id": "p_2", "party_size": 4}, headers=H(ada))
    assert p.status_code == 200
    h = hist(http, ada, ref)["entries"]
    assert len(h) == 3
    assert h[1]["changes"] == [{"field": "table_ids", "from": ["p_2", "p_1"], "to": ["p_3"]}]
    assert h[2]["changes"] == [{"field": "table_id", "from": "p_3", "to": "p_2"}, {"field": "party_size", "from": 5, "to": 4}]
    # combination capacity uses the selected policy's capacities
    v = publish(http, e["mgr"], pol(day(-7), caps={"p_1": 1, "p_2": 1, "p_3": 6})).json()["policy_version"]
    err(http.post("/reservations", json=rb(["p_2", "p_1"], f"{THU_S}T21:00", 3), headers=H(ada, "combo-cap")),
        422, "party_exceeds_capacity")
    ok = mk(http, ada, rb(["p_2", "p_1"], f"{THU_S}T21:00", 2))
    assert ok["accepted_terms"]["policy_version"] == v
