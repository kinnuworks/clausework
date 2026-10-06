"""S1-44, S1-45, S1-70..74 — DST in Berlin and New York, plus a reference availability model."""
from datetime import timezone

import pytest

from conftest import (BERLIN_NIGHT, NY_NIGHT, ANKER, THU_S, FRI_S, WED_S, avail, body, book, book_ok, err,
                      parse_ts, ref_slots, resolve, same_instant_offset)

DAYS = {
    "r_bn": ("2026-03-29", "2026-10-25"),
    "r_ny": ("2026-03-08", "2026-11-01"),
}


def compare(http, rest, d, party, booked):
    api = avail(http, rest["id"], d, party)
    assert api["timezone"] == rest["timezone"] and api["date"] == d
    ref = ref_slots(rest, d, party, booked)
    got = [s["starts_at_local"] for s in api["slots"]]
    assert got == [x[0] for x in ref], (d, party, got)
    for s, (loc, a, tables) in zip(api["slots"], ref):
        same_instant_offset(s["starts_at"], a)
        assert s["available_table_ids"] == tables, (d, party, loc)


@pytest.mark.parametrize("rid,day,skipped,before,after", [
    ("r_bn", "2026-03-29", ["02:00", "02:30"], "+01:00", "+02:00"),
    ("r_ny", "2026-03-08", ["02:00", "02:30"], "-05:00", "-04:00"),
])
def test_spring_forward(http, env, rid, day, skipped, before, after):  # S1-70, S1-72
    slots = avail(http, rid, day, 2)["slots"]
    locs = [s["starts_at_local"] for s in slots]
    for hm in skipped:
        assert f"{day}T{hm}" not in locs
        err(book(http, env["ada"], body(f"{rid[2]}_1", f"{day}T{hm}", rest=rid)), 422, "invalid_local_time")
    by = {s["starts_at_local"]: s for s in slots}
    assert by[f"{day}T01:30"]["starts_at"].endswith(before) or parse_ts(by[f"{day}T01:30"]["starts_at"]).utcoffset() == parse_ts(f"{day}T00:00:00{before}").utcoffset()
    assert parse_ts(by[f"{day}T03:00"]["starts_at"]).utcoffset() == parse_ts(f"{day}T00:00:00{after}").utcoffset()
    r = book_ok(http, env["ada"], body(f"{rid[2]}_1", f"{day}T01:30", rest=rid))
    same_instant_offset(r["starts_at"], parse_ts(f"{day}T01:30:00{before}"))
    same_instant_offset(r["ends_at"], parse_ts(f"{day}T04:00:00{after}"))


@pytest.mark.parametrize("rid,day,hm,first,second,end_local", [
    ("r_bn", "2026-10-25", "02:30", "+02:00", "+01:00", "03:00"),
    ("r_ny", "2026-11-01", "01:30", "-04:00", "-05:00", "02:00"),
])
def test_fall_back(http, env, rid, day, hm, first, second, end_local):  # S1-71, S1-72
    slots = avail(http, rid, day, 2)["slots"]
    locs = [s["starts_at_local"] for s in slots]
    assert len(locs) == len(set(locs))
    assert locs.count(f"{day}T{hm}") == 1
    r = book_ok(http, env["ada"], body(f"{rid[2]}_1", f"{day}T{hm}", rest=rid))
    same_instant_offset(r["starts_at"], parse_ts(f"{day}T{hm}:00{first}"))
    same_instant_offset(r["ends_at"], parse_ts(f"{day}T{end_local}:00{second}"))
    # second occurrence is not bookable: same local string resolves to the first occurrence -> occupied
    err(book(http, env["bob"], body(f"{rid[2]}_1", f"{day}T{hm}", rest=rid)), 409, "table_unavailable")


def test_ny_fall_back_absolute_duration_occupancy(http, env):  # S1-72
    book_ok(http, env["ada"], body("n_1", "2026-11-01T01:30", rest="r_ny"))
    sl = {s["starts_at_local"]: s["available_table_ids"] for s in avail(http, "r_ny", "2026-11-01", 2)["slots"]}
    assert "n_1" in sl["2026-11-01T02:00"]       # 01:30 EDT + 90 min = 02:00 EST; half-open
    assert "n_1" not in sl["2026-11-01T01:00"]
    assert book(http, env["bob"], body("n_1", "2026-11-01T02:00", rest="r_ny")).status_code == 201


def test_reference_availability(http, env):  # S1-45, S1-73, S1-74 (best-answer reference over small inputs)
    ada = env["ada"]
    rests = {"r_bn": BERLIN_NIGHT, "r_ny": NY_NIGHT, "r_anker": ANKER}
    plan = [
        ("r_bn", "b_1", "2026-03-29T01:30"), ("r_bn", "b_2", "2026-03-29T03:30"),
        ("r_bn", "b_1", "2026-10-25T02:00"), ("r_bn", "b_2", "2026-10-25T01:00"), ("r_bn", "b_2", "2026-10-25T03:30"),
        ("r_ny", "n_1", "2026-03-08T00:30"), ("r_ny", "n_2", "2026-03-08T03:00"),
        ("r_ny", "n_1", "2026-11-01T01:00"), ("r_ny", "n_2", "2026-11-01T02:30"), ("r_ny", "n_2", "2026-11-01T04:00"),
        ("r_anker", "t_2", f"{THU_S}T19:00"), ("r_anker", "t_1", f"{THU_S}T20:30"), ("r_anker", "t_3", f"{FRI_S}T22:00"),
    ]
    booked = {k: [] for k in rests}
    for rid, t, loc in plan:
        r = book_ok(http, ada, body(t, loc, 2, rest=rid))
        booked[rid].append((t, parse_ts(r["starts_at"]).astimezone(timezone.utc)))
        same_instant_offset(r["starts_at"], resolve(loc, rests[rid]["timezone"]))
    days = {"r_bn": list(DAYS["r_bn"]) + ["2026-03-28", "2026-10-24", THU_S],
            "r_ny": list(DAYS["r_ny"]) + ["2026-03-07", "2026-10-31", THU_S],
            "r_anker": [THU_S, FRI_S, WED_S]}
    for rid, ds in days.items():
        for d in ds:
            for party in range(1, 6):
                compare(http, rests[rid], d, party, booked[rid])
