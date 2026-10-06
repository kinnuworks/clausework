"""S1-36, S1-37, S1-84..93 — POST /reservation-moves."""
import uuid

from conftest import FRI_S, H, THU_S, avail, body, book, book_ok, burst, err, get_res, new_client, now_slot


def mv(http, token, moves, key=None, raw=None):
    return http.post("/reservation-moves", json=raw if raw is not None else {"moves": moves},
                     headers=H(token, key or str(uuid.uuid4())))


def setup(http, env):
    ada, bob = env["ada"], env["bob"]
    A = book_ok(http, ada, body("t_1", f"{THU_S}T19:00", 2))
    B = book_ok(http, ada, body("t_3", f"{THU_S}T19:00", 2))
    C = book_ok(http, bob, body("t_2", f"{THU_S}T19:00", 2))
    D = book_ok(http, ada, body("t_1", f"{THU_S}T20:30", 2))
    return A, B, C, D


def snap(http, env, refs):
    return [get_res(http, env["ada"], r) for r in refs], avail(http, "r_anker", THU_S, 2)


def test_swap_tables_and_times(http, env):  # S1-86, S1-89, S1-91
    ada = env["ada"]
    A, B, C, D = setup(http, env)
    r = mv(http, ada, [{"reference": B["reference"], "table_id": "t_1"}, {"reference": A["reference"], "table_id": "t_3"}])
    assert r.status_code == 201, r.text
    out = r.json()["reservations"]
    assert [x["reference"] for x in out] == [B["reference"], A["reference"]]
    assert out[0]["table_id"] == "t_1" and out[1]["table_id"] == "t_3"
    for new, old in ((out[0], B), (out[1], A)):
        assert new["reservation_id"] == old["reservation_id"] and new["created_at"] == old["created_at"]
        assert new["starts_at_local"] == old["starts_at_local"] and new["party_size"] == old["party_size"]
        assert get_res(http, ada, old["reference"]) == new
    # swap times on one table (t_1: B at 19:00, D at 20:30)
    r = mv(http, ada, [{"reference": B["reference"], "starts_at_local": f"{THU_S}T20:30"},
                       {"reference": D["reference"], "starts_at_local": f"{THU_S}T19:00", "foo": 1}])
    assert r.status_code == 201, r.text
    assert get_res(http, ada, B["reference"])["starts_at_local"] == f"{THU_S}T20:30"
    assert get_res(http, ada, D["reference"])["starts_at_local"] == f"{THU_S}T19:00"


def test_noop_move(http, env):  # S1-93
    A, *_ = setup(http, env)
    r = mv(http, env["ada"], [{"reference": A["reference"]}])
    assert r.status_code == 201, r.text
    assert r.json()["reservations"] == [get_res(http, env["ada"], A["reference"])]
    assert r.json()["reservations"][0] == A


def test_conflicts_all_or_nothing(http, env):  # S1-89, S1-90
    ada = env["ada"]
    A, B, C, D = setup(http, env)
    refs = [A["reference"], B["reference"], D["reference"]]
    before = snap(http, env, refs)
    cases = [
        [{"reference": B["reference"], "table_id": "t_2"}],  # onto unlisted (Bob's C)
        [{"reference": A["reference"], "starts_at_local": f"{FRI_S}T19:00"},
         {"reference": B["reference"], "table_id": "t_2"}],  # first ok, second conflicts
        [{"reference": A["reference"], "table_id": "t_2", "starts_at_local": f"{THU_S}T21:00"},
         {"reference": B["reference"], "table_id": "t_2", "starts_at_local": f"{THU_S}T21:00"}],  # among themselves
        [{"reference": A["reference"]}, {"reference": B["reference"], "table_id": "t_1", "starts_at_local": f"{THU_S}T19:30"}],
    ]
    for moves in cases:
        key = str(uuid.uuid4())
        err(mv(http, ada, moves, key), 409, "table_unavailable")
        assert snap(http, env, refs) == before, moves
    # failed key is reusable
    key = str(uuid.uuid4())
    err(mv(http, ada, cases[0], key), 409, "table_unavailable")
    ok = mv(http, ada, [{"reference": B["reference"], "starts_at_local": f"{THU_S}T21:00"}], key)
    assert ok.status_code == 201, ok.text


def test_shape_errors(http, env):  # S1-84, S1-85
    ada, bob = env["ada"], env["bob"]
    A, B, C, D = setup(http, env)
    G = book_ok(http, ada, body("g_1", f"{THU_S}T18:45", 2, rest="r_grid"))
    for raw in [{"moves": []}, {}, {"moves": "x"}, {"moves": [{"table_id": "t_1"}]},
                {"moves": [{"reference": 5}]}, {"moves": [{"reference": A["reference"]}, {"reference": A["reference"]}]},
                {"moves": [{"reference": A["reference"]}] + [{"reference": f"ZZ{i:04d}"} for i in range(8)]}]:
        err(mv(http, ada, None, raw=raw), 422, "validation_failed")
    err(mv(http, ada, [{"reference": "NOPE99"}]), 404, "not_found")
    err(mv(http, ada, [{"reference": C["reference"]}]), 404, "not_found")
    err(mv(http, ada, [{"reference": A["reference"]}, {"reference": G["reference"]}]), 422, "validation_failed")
    err(http.post("/reservation-moves", json={"moves": [{"reference": A["reference"]}]},
                  headers={"Idempotency-Key": "x"}), 401, "unauthenticated")
    err(http.post("/reservation-moves", json={"moves": [{"reference": A["reference"]}]}, headers=H(ada)),
        400, "missing_idempotency_key")
    err(http.post("/reservation-moves", json={"moves": [{"reference": A["reference"]}]}, headers=H(ada, "k" * 256)),
        422, "validation_failed")
    # 8 distinct own references accepted
    eight = [A, B, D] + [book_ok(http, ada, body(t, f"{FRI_S}T{hm}", 2)) for t, hm in
                         [("t_1", "18:00"), ("t_1", "19:30"), ("t_3", "18:00"), ("t_3", "19:30"), ("t_2", "18:00")]]
    r = mv(http, ada, [{"reference": x["reference"]} for x in eight])
    assert r.status_code == 201, r.text
    assert len(r.json()["reservations"]) == 8


def test_cancelled_cutoff_and_precedence(http, env):  # S1-87, S1-88
    ada = env["ada"]
    A, B, C, D = setup(http, env)
    assert http.post(f"/reservations/{D['reference']}/cancel", headers=H(ada)).status_code == 200
    err(mv(http, ada, [{"reference": D["reference"]}]), 409, "reservation_cancelled")
    err(mv(http, ada, [{"reference": A["reference"], "party_size": 9}, {"reference": D["reference"]}]),
        422, "party_exceeds_capacity")
    err(mv(http, ada, [{"reference": D["reference"]}, {"reference": A["reference"], "party_size": 9}]),
        409, "reservation_cancelled")
    err(mv(http, ada, [{"reference": A["reference"], "table_id": "t_2"}, {"reference": B["reference"], "party_size": 9}]),
        422, "party_exceeds_capacity")
    err(mv(http, ada, [{"reference": A["reference"], "starts_at_local": f"{THU_S}T19:15"}]), 422, "not_on_slot_grid")
    err(mv(http, ada, [{"reference": A["reference"], "party_size": 0}]), 422, "validation_failed")
    near = book_ok(http, ada, body("c_1", now_slot(60), 2, rest="r_now"))
    near2 = book_ok(http, ada, body("c_2", now_slot(300), 2, rest="r_now"))
    err(mv(http, ada, [{"reference": near["reference"], "party_size": 0}]), 409, "cutoff_passed")
    err(mv(http, ada, [{"reference": near2["reference"], "table_id": "c_1"}, {"reference": near["reference"]}]),
        409, "cutoff_passed")
    assert get_res(http, ada, near2["reference"]) == near2


def test_moves_idempotency(http, env):  # S1-36, S1-37, S1-92
    ada = env["ada"]
    A, B, C, D = setup(http, env)
    key = str(uuid.uuid4())
    moves = [{"reference": A["reference"], "table_id": "t_3", "starts_at_local": f"{THU_S}T21:00"}]
    r1 = mv(http, ada, moves, key)
    assert r1.status_code == 201, r1.text
    r2 = mv(http, ada, moves, key)
    assert r2.status_code == 200 and r2.json() == r1.json()
    err(mv(http, ada, [{"reference": A["reference"], "party_size": 1}], key), 409, "idempotency_key_reuse")
    err(mv(http, ada, [{"reference": "NOPE99"}], key), 409, "idempotency_key_reuse")
    assert http.patch(f"/reservations/{A['reference']}", json={"party_size": 1}, headers=H(ada)).status_code == 200
    assert http.post(f"/reservations/{A['reference']}/cancel", headers=H(ada)).status_code == 200
    r3 = mv(http, ada, moves, key)
    assert r3.status_code == 200 and r3.json() == r1.json()
    assert get_res(http, ada, A["reference"])["status"] == "cancelled"
    # same key on a different path is a different request
    k2 = str(uuid.uuid4())
    assert book(http, ada, body("t_2", f"{FRI_S}T21:00"), k2).status_code == 201
    r4 = mv(http, ada, [{"reference": B["reference"]}], k2)
    assert r4.status_code == 201, r4.text
    # concurrent identical batch
    k3 = str(uuid.uuid4())
    bm = [{"reference": B["reference"], "starts_at_local": f"{THU_S}T21:30"}]

    def f():
        with new_client() as c:
            return c.post("/reservation-moves", json={"moves": bm}, headers=H(ada, k3))
    rs = burst([f for _ in range(20)])
    codes = [r.status_code for r in rs]
    assert codes.count(201) == 1 and codes.count(200) == 19, codes
    assert all(r.json() == rs[0].json() for r in rs)
