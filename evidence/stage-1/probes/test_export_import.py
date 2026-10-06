"""S1-75..83, S1-94 — export/import round trip."""
import copy
import uuid

from conftest import ANKER, FRI_S, H, THU_S, avail, body, book, book_ok, err, get_res, login, my_res, reset


def export(http):
    r = http.get("/_test/export")
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["track"] == "tablekeeper" and j["format_version"] == 1 and isinstance(j["state"], dict)
    return j


def imp(http, obj):
    return http.post("/_test/import", json=obj)


def populate(http, env):
    ada, bob = env["ada"], env["bob"]
    s = http.post("/auth/signup", json={"email": "carol@example.com", "password": "carolpass1", "display_name": "Carol"})
    assert s.status_code == 201
    carol = s.json()["token"]
    k1, k2, k3, k4 = (str(uuid.uuid4()) for _ in range(4))
    b1 = body("t_2", f"{THU_S}T19:00", 3)
    r1 = book(http, ada, b1, k1)
    assert r1.status_code == 201
    rB = book_ok(http, ada, body("t_1", f"{THU_S}T19:00", 2))
    assert http.post(f"/reservations/{rB['reference']}/cancel", headers=H(ada)).status_code == 200
    rC = book_ok(http, carol, body("t_3", f"{FRI_S}T20:00", 2))
    moves = {"moves": [{"reference": rC["reference"], "table_id": "t_1"}]}
    m1 = http.post("/reservation-moves", json=moves, headers=H(carol, k2))
    assert m1.status_code == 201, m1.text
    err(book(http, bob, {**b1, "party_size": 0}, k3), 422, "validation_failed")
    return dict(ada=ada, bob=bob, carol=carol, k1=k1, k2=k2, k3=k3, k4=k4, b1=b1, r1=r1.json(), rB=rB,
                rC=m1.json()["reservations"][0], moves=moves, m1=m1.json())


def test_export_shape_public(http, env):  # S1-75
    export(http)


def test_round_trip(http, env):  # S1-76..79, S1-94
    p = populate(http, env)
    lists = {u: my_res(http, p[u]) for u in ("ada", "bob", "carol")}
    av = {d: avail(http, "r_anker", d, 2) for d in (THU_S, FRI_S)}
    E = export(http)
    reset(http, {"users": [], "restaurants": [{**copy.deepcopy(ANKER), "id": "r_other"}], "reservations": []})
    r = imp(http, copy.deepcopy(E))
    assert r.status_code == 204, r.text
    for rep in range(2):  # repeat import: no duplication
        for u in ("ada", "bob", "carol"):
            assert my_res(http, p[u]) == lists[u], u
        for d in (THU_S, FRI_S):
            assert avail(http, "r_anker", d, 2) == av[d]
        assert sorted(x["id"] for x in http.get("/restaurants").json()["restaurants"]) == \
            sorted(["r_anker", "r_grid", "r_bn", "r_ny", "r_now"])
        err(http.get("/restaurants/r_other"), 404, "not_found")
        if rep == 0:
            assert imp(http, copy.deepcopy(E)).status_code == 204
    assert get_res(http, p["ada"], p["r1"]["reference"]) == p["r1"]
    assert get_res(http, p["ada"], p["rB"]["reference"])["status"] == "cancelled"
    assert get_res(http, p["carol"], p["rC"]["reference"]) == p["rC"]
    assert login(http, "carol@example.com", "carolpass1")
    assert login(http, "ada@example.com", "correct horse")
    rp = book(http, p["ada"], p["b1"], p["k1"])
    assert rp.status_code == 200 and rp.json() == p["r1"]
    mp = http.post("/reservation-moves", json=p["moves"], headers=H(p["carol"], p["k2"]))
    assert mp.status_code == 200 and mp.json() == p["m1"]
    err(book(http, p["ada"], {**p["b1"], "party_size": 2}, p["k1"]), 409, "idempotency_key_reuse")
    fresh = book(http, p["bob"], body("t_2", f"{FRI_S}T18:00", 2), p["k3"])
    assert fresh.status_code == 201, fresh.text
    assert fresh.json()["reference"] not in {p["r1"]["reference"], p["rB"]["reference"], p["rC"]["reference"]}
    err(http.post("/auth/signup", json={"email": "carol@example.com", "password": "12345678", "display_name": "C"}),
        409, "email_taken")


def test_import_replaces_and_snapshot(http, env):  # S1-80, S1-82, S1-83
    p = populate(http, env)
    E = export(http)
    s = http.post("/auth/signup", json={"email": "late@example.com", "password": "latepass1", "display_name": "L"})
    late = s.json()["token"]
    late_res = book_ok(http, p["ada"], body("t_3", f"{THU_S}T19:00", 2))
    assert imp(http, E).status_code == 204
    err(http.get("/reservations", headers=H(late)), 401, "unauthenticated")
    err(http.post("/auth/login", json={"email": "late@example.com", "password": "latepass1"}), 401, "unauthenticated")
    err(http.get(f"/reservations/{late_res['reference']}", headers=H(p["ada"])), 404, "not_found")
    E2 = export(http)
    assert imp(http, E2).status_code == 204
    assert get_res(http, p["ada"], p["r1"]["reference"]) == p["r1"]
    reset(http)
    err(http.get("/reservations", headers=H(p["carol"])), 401, "unauthenticated")


def test_invalid_import_changes_nothing(http, env):  # S1-81
    p = populate(http, env)
    E = export(http)
    before = my_res(http, p["ada"])
    err(http.post("/_test/import", content=b"{", headers={"Content-Type": "application/json"}), 400, "malformed_request")
    bads = [{k: v for k, v in E.items() if k != "state"}, {k: v for k, v in E.items() if k != "track"},
            {k: v for k, v in E.items() if k != "format_version"}, {**E, "track": "other"}, {**E, "format_version": 2},
            {**E, "state": "garbage"}, {**E, "state": 42}, {}]
    for bad in bads:
        err(imp(http, bad), 422, "validation_failed")
        assert my_res(http, p["ada"]) == before
        assert http.get("/reservations", headers=H(p["carol"])).status_code == 200
