"""S1-19, S1-29, S1-37, S1-68, S1-95, S1-96 — bursts released at one instant."""
import uuid
from datetime import datetime, timedelta

from conftest import FRI_S, H, THU_S, avail, body, book_ok, burst, err, get_res, my_res, new_client


def _post(token, b, key):
    def f():
        with new_client() as c:
            return c.post("/reservations", json=b, headers=H(token, key))
    return f


def test_same_slot_burst_50(http, env):  # S1-96, S1-19
    toks = [env["ada"], env["bob"]]
    b = body("t_2", f"{THU_S}T19:00")
    rs = burst([_post(toks[i % 2], b, str(uuid.uuid4())) for i in range(50)])
    codes = [r.status_code for r in rs]
    assert all(c < 500 for c in codes), codes
    assert codes.count(201) == 1, codes
    for r in rs:
        if r.status_code != 201:
            err(r, 409, "table_unavailable")
    total = len(my_res(http, env["ada"])) + len(my_res(http, env["bob"]))
    assert total == 1
    s = {x["starts_at_local"]: x["available_table_ids"] for x in avail(http, "r_anker", THU_S, 2)["slots"]}
    assert "t_2" not in s[f"{THU_S}T19:00"]


def test_overlapping_starts_burst(http, env):  # S1-96: some serial order explains every answer
    toks = [env["ada"], env["bob"]]
    starts = ["18:00", "18:30", "19:00", "19:30", "20:00", "20:30", "21:00", "21:30"]
    reqs = [(st, toks[i % 2]) for i, st in enumerate(starts * 6)]
    rs = burst([_post(t, body("t_1", f"{THU_S}T{st}"), str(uuid.uuid4())) for st, t in reqs])
    assert all(r.status_code in (201, 409) for r in rs), [r.status_code for r in rs]

    def iv(st):
        s = datetime.fromisoformat(f"{THU_S}T{st}")
        return s, s + timedelta(minutes=90)

    ok = [iv(st) for (st, _), r in zip(reqs, rs) if r.status_code == 201]
    for i, a in enumerate(ok):
        for b in ok[i + 1:]:
            assert not (a[0] < b[1] and b[0] < a[1]), ok
    for (st, _), r in zip(reqs, rs):
        if r.status_code == 409:
            err(r, 409, "table_unavailable")
            a = iv(st)
            assert any(a[0] < b[1] and b[0] < a[1] for b in ok), st
    confirmed = [x for x in my_res(http, env["ada"]) + my_res(http, env["bob"]) if x["status"] == "confirmed"]
    assert len(confirmed) == len(ok)


def test_idempotent_burst(http, env):  # S1-37
    key = str(uuid.uuid4())
    b = body("t_2", f"{FRI_S}T19:00", 3)
    rs = burst([_post(env["ada"], b, key) for _ in range(30)])
    codes = [r.status_code for r in rs]
    assert codes.count(201) == 1 and codes.count(200) == 29, codes
    first = [r for r in rs if r.status_code == 201][0].json()
    assert all(r.json() == first for r in rs)
    assert len(my_res(http, env["ada"])) == 1


def test_signup_burst(http, env):  # S1-29
    def f():
        with new_client() as c:
            return c.post("/auth/signup", json={"email": "race@example.com", "password": "12345678", "display_name": "R"})
    rs = burst([f for _ in range(20)])
    codes = [r.status_code for r in rs]
    assert codes.count(201) == 1, codes
    for r in rs:
        if r.status_code != 201:
            err(r, 409, "email_taken")


def test_patch_burst(http, env):  # S1-68
    ada = env["ada"]
    placed = [("t_1", "18:00"), ("t_1", "19:30"), ("t_1", "21:00"), ("t_3", "18:00"), ("t_3", "19:30"),
              ("t_3", "21:00"), ("t_2", "18:00"), ("t_2", "19:30")]
    refs = [book_ok(http, ada, body(t, f"{FRI_S}T{hm}", 2))["reference"] for t, hm in placed]
    before = {r: get_res(http, ada, r) for r in refs}

    def f(ref):
        def g():
            with new_client() as c:
                return c.patch(f"/reservations/{ref}", json={"table_id": "t_2", "starts_at_local": f"{FRI_S}T22:00"},
                               headers=H(ada))
        return g
    targets = [r for r, (t, _) in zip(refs, placed) if t != "t_2"]
    rs = burst([f(r) for r in targets])
    codes = [r.status_code for r in rs]
    assert codes.count(200) == 1, codes
    for ref, r in zip(targets, rs):
        if r.status_code != 200:
            err(r, 409, "table_unavailable")
            assert get_res(http, ada, ref) == before[ref]


def test_moves_burst(http, env):  # S1-95
    users = []
    for i in range(8):
        s = http.post("/auth/signup", json={"email": f"m{i}@example.com", "password": "12345678", "display_name": f"M{i}"})
        assert s.status_code == 201
        users.append(s.json()["token"])
    # each user books on a distinct free slot first
    slots = [("t_1", "18:00"), ("t_1", "19:30"), ("t_1", "21:00"), ("t_3", "18:00"), ("t_3", "19:30"),
             ("t_3", "21:00"), ("t_2", "18:00"), ("t_2", "19:30")]
    refs = [book_ok(http, t, body(tb, f"{FRI_S}T{hm}", 2))["reference"] for t, (tb, hm) in zip(users, slots)]

    def f(tok, ref):
        def g():
            with new_client() as c:
                return c.post("/reservation-moves", json={"moves": [{"reference": ref, "table_id": "t_2",
                                                                      "starts_at_local": f"{FRI_S}T21:30"}]},
                              headers=H(tok, str(uuid.uuid4())))
        return g
    idx = [i for i, (tb, _) in enumerate(slots) if tb != "t_2"]
    rs = burst([f(users[i], refs[i]) for i in idx])
    codes = [r.status_code for r in rs]
    assert codes.count(201) == 1, codes
    for r in rs:
        if r.status_code != 201:
            err(r, 409, "table_unavailable")
