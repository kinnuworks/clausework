"""S1-61, S1-62, S1-64..67, S1-69."""
from conftest import FRI_S, H, THU_S, avail, body, book_ok, err, get_res, slot_tables


def test_patch_each_field(http, env):  # S1-61, S1-65, S1-67
    ada = env["ada"]
    r = book_ok(http, ada, body("t_2", f"{THU_S}T19:00", 2))
    ref, rid, created = r["reference"], r["reservation_id"], r["created_at"]
    p = http.patch(f"/reservations/{ref}", json={"party_size": 3}, headers=H(ada))
    assert p.status_code == 200, p.text
    assert p.json()["party_size"] == 3 and p.json()["table_id"] == "t_2" and p.json()["starts_at_local"] == f"{THU_S}T19:00"
    p = http.patch(f"/reservations/{ref}", json={"starts_at_local": f"{THU_S}T19:30"}, headers=H(ada))
    assert p.status_code == 200, p.text
    assert p.json()["starts_at_local"] == f"{THU_S}T19:30" and p.json()["party_size"] == 3
    assert slot_tables(http, "r_anker", THU_S, 2, f"{THU_S}T18:00") == ["t_1", "t_2", "t_3"]
    assert "t_2" not in slot_tables(http, "r_anker", THU_S, 2, f"{THU_S}T20:30")
    p = http.patch(f"/reservations/{ref}", json={"table_id": "t_1", "party_size": 2}, headers=H(ada))
    assert p.status_code == 200, p.text
    j = p.json()
    assert j["table_id"] == "t_1" and j["party_size"] == 2
    assert j["reference"] == ref and j["reservation_id"] == rid and j["created_at"] == created
    assert j["status"] == "confirmed"
    assert slot_tables(http, "r_anker", THU_S, 2, f"{THU_S}T19:30") == ["t_2", "t_3"]
    assert get_res(http, ada, ref) == j


def test_patch_failures_leave_booking(http, env):  # S1-62, S1-66
    ada, bob = env["ada"], env["bob"]
    r = book_ok(http, ada, body("t_2", f"{THU_S}T19:00", 2))
    book_ok(http, bob, body("t_1", f"{THU_S}T19:00", 2))
    ref = r["reference"]
    before = get_res(http, ada, ref)
    av_before = avail(http, "r_anker", THU_S, 2)
    cases = [
        ({"party_size": "3"}, 422, "validation_failed"),
        ({"party_size": 0}, 422, "validation_failed"),
        ({"party_size": True}, 422, "validation_failed"),
        ({"party_size": 5}, 422, "party_exceeds_capacity"),
        ({"starts_at_local": f"{THU_S}T19:15"}, 422, "not_on_slot_grid"),
        ({"starts_at_local": f"{THU_S}T22:00"}, 422, "outside_opening_hours"),
        ({"starts_at_local": f"{THU_S}T19:00Z"}, 422, "validation_failed"),
        ({"table_id": "t_3", "party_size": 3}, 422, "party_exceeds_capacity"),
        ({"table_id": "g_1"}, 404, "not_found"),
        ({"table_id": "t_9"}, 404, "not_found"),
        ({"table_id": "t_1"}, 409, "table_unavailable"),
        ({"table_id": "t_1", "starts_at_local": f"{THU_S}T20:00"}, 409, "table_unavailable"),
    ]
    for patch, st, code in cases:
        err(http.patch(f"/reservations/{ref}", json=patch, headers=H(ada)), st, code)
        assert get_res(http, ada, ref) == before, patch
    assert avail(http, "r_anker", THU_S, 2) == av_before
    err(http.patch(f"/reservations/{ref}", json={"party_size": 1}, headers=H(bob)), 404, "not_found")
    err(http.patch("/reservations/NOPE99", json={"party_size": 1}, headers=H(ada)), 404, "not_found")
    assert get_res(http, ada, ref) == before


def test_patch_cancelled(http, env):  # S1-64
    ada = env["ada"]
    r = book_ok(http, ada, body("t_2", f"{FRI_S}T19:00"))
    assert http.post(f"/reservations/{r['reference']}/cancel", headers=H(ada)).status_code == 200
    err(http.patch(f"/reservations/{r['reference']}", json={"party_size": 3}, headers=H(ada)), 409, "reservation_cancelled")
    assert get_res(http, ada, r["reference"])["status"] == "cancelled"
