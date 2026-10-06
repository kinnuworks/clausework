"""S1-04, S1-10, S1-12, S1-44, S1-46..58, S1-60."""
import re
from datetime import timedelta

from conftest import (FRI_S, H, THU_S, WED_S, avail, body, book, book_ok, err, get_res, my_res, parse_ts,
                      resolve, same_instant_offset, slot_tables)

REF = re.compile(r"^[A-Z0-9]{6,12}$")


def test_create_shape(http, env):  # S1-04, S1-47, S1-48
    r = book(http, env["ada"], body("t_2", f"{THU_S}T19:00", 4))
    assert r.status_code == 201, r.text
    j = r.json()
    assert REF.match(j["reference"])
    assert isinstance(j["reservation_id"], str) and 0 < len(j["reservation_id"]) <= 64
    assert j["restaurant_id"] == "r_anker" and j["table_id"] == "t_2" and j["party_size"] == 4
    assert j["status"] == "confirmed" and j["starts_at_local"] == f"{THU_S}T19:00"
    s, e = parse_ts(j["starts_at"]), parse_ts(j["ends_at"])
    same_instant_offset(j["starts_at"], resolve(f"{THU_S}T19:00", "Europe/Berlin"))
    assert e - s == timedelta(minutes=90)
    parse_ts(j["created_at"])
    assert get_res(http, env["ada"], j["reference"]) == j


def test_references_unique(http, env):  # S1-48
    refs = set()
    for day in (THU_S, FRI_S):
        for t in ("t_1", "t_2", "t_3"):
            for hh in ("18:00", "19:30", "21:00"):
                refs.add(book_ok(http, env["ada"], body(t, f"{day}T{hh}", 2))["reference"])
    assert len(refs) == 18 and all(REF.match(x) for x in refs)


def test_half_open_overlap(http, env):  # S1-49, S1-54
    ada, bob = env["ada"], env["bob"]
    book_ok(http, ada, body("t_2", f"{THU_S}T19:00"))
    assert book(http, bob, body("t_2", f"{THU_S}T20:30")).status_code == 201
    err(book(http, bob, body("t_2", f"{THU_S}T19:30")), 409, "table_unavailable")
    err(book(http, bob, body("t_2", f"{THU_S}T18:00")), 409, "table_unavailable")
    err(book(http, bob, body("t_2", f"{THU_S}T19:00")), 409, "table_unavailable")
    assert book(http, bob, body("t_1", f"{THU_S}T19:00")).status_code == 201
    assert book(http, bob, body("t_2", f"{FRI_S}T19:00")).status_code == 201
    assert len(my_res(http, bob)) == 3
    assert len(my_res(http, ada)) == 1


def test_grid_hours_capacity_notfound(http, env):  # S1-10, S1-12, S1-50..54
    ada = env["ada"]
    err(book(http, ada, body("t_2", f"{THU_S}T19:15")), 422, "not_on_slot_grid")
    err(book(http, ada, body("t_2", f"{THU_S}T19:10")), 422, "not_on_slot_grid")
    err(book(http, ada, body("t_2", f"{THU_S}T17:30")), 422, "outside_opening_hours")
    err(book(http, ada, body("t_2", f"{THU_S}T22:00")), 422, "outside_opening_hours")
    err(book(http, ada, body("t_2", f"{THU_S}T23:00")), 422, "outside_opening_hours")
    err(book(http, ada, body("t_2", f"{WED_S}T19:00")), 422, "outside_opening_hours")
    err(book(http, ada, body("t_1", f"{THU_S}T19:00", 3)), 422, "party_exceeds_capacity")
    err(book(http, ada, body("t_9", f"{THU_S}T19:00")), 404, "not_found")
    err(book(http, ada, body("t_2", f"{THU_S}T19:00", rest="r_nope")), 404, "not_found")
    err(book(http, ada, body("g_1", f"{THU_S}T19:00")), 404, "not_found")
    assert my_res(http, ada) == []
    assert slot_tables(http, "r_anker", THU_S, 2, f"{THU_S}T19:00") == ["t_1", "t_2", "t_3"]
    assert book(http, ada, body("t_2", f"{THU_S}T21:30")).status_code == 201
    assert book(http, ada, body("t_2", f"{FRI_S}T22:00")).status_code == 201
    assert book(http, ada, body("t_1", f"{FRI_S}T18:00", 2)).status_code == 201
    # opening-anchored grid: opens 17:15, slot 45
    err(book(http, ada, body("g_1", f"{THU_S}T18:30", rest="r_grid")), 422, "not_on_slot_grid")
    err(book(http, ada, body("g_1", f"{THU_S}T19:00", rest="r_grid")), 422, "not_on_slot_grid")
    assert book(http, ada, body("g_1", f"{THU_S}T18:45", rest="r_grid")).status_code == 201
    assert book(http, ada, body("g_1", f"{THU_S}T17:15", rest="r_grid")).status_code == 201


def test_availability_basic(http, env):  # S1-10, S1-44, S1-45, S1-46
    a = avail(http, "r_anker", THU_S, 2)
    assert a["restaurant_id"] == "r_anker" and a["date"] == THU_S and a["timezone"] == "Europe/Berlin"
    locs = [s["starts_at_local"] for s in a["slots"]]
    assert locs == [f"{THU_S}T{h}" for h in ["18:00", "18:30", "19:00", "19:30", "20:00", "20:30", "21:00", "21:30"]]
    assert all(s["available_table_ids"] == ["t_1", "t_2", "t_3"] for s in a["slots"])
    assert all(x["available_table_ids"] == ["t_2"] for x in avail(http, "r_anker", THU_S, 3)["slots"])
    big = avail(http, "r_anker", THU_S, 99)["slots"]
    assert len(big) == 8 and all(x["available_table_ids"] == [] for x in big)
    assert avail(http, "r_anker", WED_S, 2)["slots"] == []
    g = [s["starts_at_local"][-5:] for s in avail(http, "r_grid", THU_S, 2)["slots"]]
    assert g == ["17:15", "18:00", "18:45", "19:30", "20:15", "21:00", "21:45"]
    # echo every slot into POST
    for s in a["slots"][::3]:
        r = book(http, env["ada"], body("t_3", s["starts_at_local"]))
        assert r.status_code == 201, r.text
        assert parse_ts(r.json()["starts_at"]) == parse_ts(s["starts_at"])
    after = avail(http, "r_anker", THU_S, 2)["slots"]
    blocked = {x["starts_at_local"] for x in after if "t_3" not in x["available_table_ids"]}
    assert blocked == set(locs)  # t_3 booked 18:00, 19:30, 21:00 -> every slot overlaps one
    assert all(x["available_table_ids"][:2] == ["t_1", "t_2"] for x in after)


def test_list_order_and_visibility(http, env):  # S1-55, S1-56
    ada, bob = env["ada"], env["bob"]
    assert my_res(http, ada) == []
    r1 = book_ok(http, ada, body("t_1", f"{THU_S}T19:00"))
    r2 = book_ok(http, ada, body("t_1", f"{FRI_S}T18:00"))
    r3 = book_ok(http, ada, body("t_1", f"{THU_S}T21:00"))
    book_ok(http, bob, body("t_2", f"{THU_S}T19:00"))
    assert http.post(f"/reservations/{r1['reference']}/cancel", headers=H(ada)).status_code == 200
    lst = my_res(http, ada)
    assert [x["reference"] for x in lst] == [r2["reference"], r3["reference"], r1["reference"]]
    assert [x["status"] for x in lst] == ["confirmed", "confirmed", "cancelled"]
    assert set(lst[0].keys()) >= {"reservation_id", "reference", "restaurant_id", "table_id", "party_size", "status",
                                  "starts_at_local", "starts_at", "ends_at", "created_at"}
    err(http.get(f"/reservations/{r2['reference']}", headers=H(bob)), 404, "not_found")
    err(http.get("/reservations/ZZZZZZZZ", headers=H(ada)), 404, "not_found")


def test_cancel(http, env):  # S1-57, S1-58, S1-60
    ada, bob = env["ada"], env["bob"]
    r = book_ok(http, ada, body("t_2", f"{THU_S}T19:00"))
    ref = r["reference"]
    assert slot_tables(http, "r_anker", THU_S, 2, f"{THU_S}T19:00") == ["t_1", "t_3"]
    err(http.post(f"/reservations/{ref}/cancel", headers=H(bob)), 404, "not_found")
    assert get_res(http, ada, ref)["status"] == "confirmed"
    err(http.post("/reservations/NOPE99/cancel", headers=H(ada)), 404, "not_found")
    c = http.post(f"/reservations/{ref}/cancel", headers=H(ada))
    assert c.status_code == 200, c.text
    assert c.json()["reference"] == ref and c.json()["status"] == "cancelled"
    assert slot_tables(http, "r_anker", THU_S, 2, f"{THU_S}T19:00") == ["t_1", "t_2", "t_3"]
    c2 = http.post(f"/reservations/{ref}/cancel", headers=H(ada))
    assert c2.status_code == 200 and c2.json()["status"] == "cancelled"
    assert book(http, bob, body("t_2", f"{THU_S}T19:30")).status_code == 201
