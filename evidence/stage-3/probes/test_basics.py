"""S1-01..03, S1-08, S1-09, S1-20..28, S1-40, S1-41."""
import uuid

from conftest import (ANKER, H, RESTAURANTS, THU_S, USERS, base_fixture, body, book_ok, err, login,
                      my_res, reset, slot_tables)


def test_health(http):  # S1-01
    r = http.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_reset_replaces_everything(http):  # S1-02, S1-03
    reset(http)
    ada = login(http, "ada@example.com", "correct horse")
    book_ok(http, ada, body())
    other = {"users": [{"id": "u_zed", "email": "zed@example.com", "password": "zzzzzzzz", "display_name": "Zed"}],
             "restaurants": [ANKER], "reservations": []}
    reset(http, other)
    r = http.post("/auth/login", json={"email": "ada@example.com", "password": "correct horse"})
    err(r, 401, "unauthenticated")
    err(http.get("/reservations", headers=H(ada)), 401, "unauthenticated")
    zed = login(http, "zed@example.com", "zzzzzzzz")
    assert my_res(http, zed) == []
    assert [x["id"] for x in http.get("/restaurants").json()["restaurants"]] == ["r_anker"]
    assert slot_tables(http, "r_anker", THU_S, 2, f"{THU_S}T19:00") == ["t_1", "t_2", "t_3"]
    reset(http)
    reset(http)
    assert login(http, "ada@example.com", "correct horse")


def test_seeded_users_and_reservations(http):  # S1-08, S1-09
    seeded = {"id": "res_seed_1", "reference": "SEED01", "user_id": "u_ada", "restaurant_id": "r_anker",
              "table_id": "t_2", "starts_at_local": f"{THU_S}T19:00", "party_size": 3}
    reset(http, base_fixture([seeded]))
    ada = login(http, "ada@example.com", "correct horse")
    bob = login(http, "bob@example.com", "battery staple")
    r = http.get("/reservations/SEED01", headers=H(ada))
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["reference"] == "SEED01" and j["status"] == "confirmed" and j["reservation_id"] == "res_seed_1"
    assert j["table_id"] == "t_2" and j["party_size"] == 3
    assert [x["reference"] for x in my_res(http, ada)] == ["SEED01"]
    err(http.get("/reservations/SEED01", headers=H(bob)), 404, "not_found")
    assert slot_tables(http, "r_anker", THU_S, 2, f"{THU_S}T19:00") == ["t_1", "t_3"]
    assert slot_tables(http, "r_anker", THU_S, 2, f"{THU_S}T20:30") == ["t_1", "t_2", "t_3"]


def test_restaurants_list_and_detail(http):  # S1-40, S1-41
    reset(http)
    r = http.get("/restaurants")
    assert r.status_code == 200
    assert r.json()["restaurants"] == [{"id": x["id"], "name": x["name"], "timezone": x["timezone"]} for x in RESTAURANTS] \
        or sorted(r.json()["restaurants"], key=lambda x: x["id"]) == sorted(
            [{"id": x["id"], "name": x["name"], "timezone": x["timezone"]} for x in RESTAURANTS], key=lambda x: x["id"])
    d = http.get("/restaurants/r_anker")
    assert d.status_code == 200
    dj = d.json()
    for k in ["id", "name", "timezone", "slot_minutes", "reservation_duration_minutes",
              "cancellation_cutoff_minutes", "opening_hours", "tables"]:
        assert dj[k] == ANKER[k], k
    err(http.get("/restaurants/r_nope"), 404, "not_found")


def test_signup_login(http):  # S1-21, S1-22, S1-28
    reset(http)
    r = http.post("/auth/signup", json={"email": "cy@example.com", "password": "12345678", "display_name": "Cy"})
    assert r.status_code == 201, r.text
    s = r.json()
    assert s["display_name"] == "Cy" and isinstance(s["user_id"], str) and isinstance(s["token"], str) and s["token"]
    assert len(s["user_id"]) <= 64
    assert http.get("/reservations", headers=H(s["token"])).json() == {"reservations": []}
    l1 = http.post("/auth/login", json={"email": "cy@example.com", "password": "12345678"})
    assert l1.status_code == 200
    assert l1.json()["user_id"] == s["user_id"] and l1.json()["display_name"] == "Cy"
    t2 = login(http, "cy@example.com", "12345678")
    for t in [s["token"], l1.json()["token"], t2]:
        assert http.get("/reservations", headers=H(t)).status_code == 200


def test_signup_errors(http):  # S1-23..26
    reset(http)
    err(http.post("/auth/signup", json={"email": "ada@example.com", "password": "12345678", "display_name": "X"}),
        409, "email_taken")
    assert http.post("/auth/signup", json={"email": "d@example.com", "password": "12345678", "display_name": "D"}).status_code == 201
    err(http.post("/auth/signup", json={"email": "d@example.com", "password": "12345678", "display_name": "D"}),
        409, "email_taken")
    err(http.post("/auth/signup", json={"email": "e@example.com", "password": "1234567", "display_name": "E"}),
        422, "validation_failed")
    for bad in ["nope", "@x.com", "a@", ""]:
        err(http.post("/auth/signup", json={"email": bad, "password": "12345678", "display_name": "E"}),
            422, "validation_failed")
    err(http.post("/auth/login", json={"email": "ada@example.com", "password": "wrong password"}), 401, "unauthenticated")
    err(http.post("/auth/login", json={"email": "ghost@example.com", "password": "whatever1"}), 401, "unauthenticated")


def test_auth_required_and_public(http):  # S1-20, S1-27
    reset(http)
    assert http.get("/restaurants").status_code == 200
    assert http.get("/restaurants/r_anker").status_code == 200
    assert http.get("/availability", params={"restaurant_id": "r_anker", "date": THU_S, "party_size": 2}).status_code == 200
    for hdr in [{}, {"Authorization": "Token abc"}, {"Authorization": "Bearer"}, {"Authorization": "Bearer bogus-token"}]:
        err(http.get("/reservations", headers=hdr), 401, "unauthenticated")
        err(http.get("/reservations/ABCDEF", headers=hdr), 401, "unauthenticated")
        err(http.post("/reservations", json=body(), headers={**hdr, "Idempotency-Key": str(uuid.uuid4())}),
            401, "unauthenticated")
        err(http.post("/reservations/ABCDEF/cancel", headers=hdr), 401, "unauthenticated")
        err(http.patch("/reservations/ABCDEF", json={"party_size": 2}, headers=hdr), 401, "unauthenticated")
        err(http.post("/reservation-moves", json={"moves": [{"reference": "ABCDEF"}]},
                      headers={**hdr, "Idempotency-Key": str(uuid.uuid4())}), 401, "unauthenticated")
