"""S1-05..07, S1-14..17, S1-42, S1-43."""
import copy
import uuid

from conftest import ANKER, H, THU_S, base_fixture, body, book, err, my_res, reset


def test_malformed_bodies(http, env):  # S1-14
    ada = env["ada"]
    for raw in [b"{", b"not json", b"[1]", b"\"str\""]:
        r = http.post("/reservations", content=raw,
                      headers={**H(ada, str(uuid.uuid4())), "Content-Type": "application/json"})
        err(r, 400, "malformed_request")
    err(book(http, ada, {**body(), "restaurant_id": 5}), 400, "malformed_request")
    err(book(http, ada, {**body(), "table_id": ["t_2"]}), 400, "malformed_request")
    err(http.post("/auth/signup", json={"email": 5, "password": "12345678", "display_name": "X"}), 400, "malformed_request")
    err(http.post("/auth/login", content=b"{", headers={"Content-Type": "application/json"}), 400, "malformed_request")
    assert my_res(http, ada) == []


def test_party_size_and_local_time_validation(http, env):  # S1-15
    ada = env["ada"]
    for p in ["4", True, 2.5, 0, -1, None]:
        err(book(http, ada, {**body(), "party_size": p}), 422, "validation_failed")
    for s in [f"{THU_S}T19:00:00", f"{THU_S}T19:00Z", f"{THU_S}T19:00+02:00", "2026-02-30T19:00",
              f"{THU_S}T25:00", f"{THU_S} 19:00", f"{THU_S}T7:00", "", "tomorrow"]:
        err(book(http, ada, {**body(), "starts_at_local": s}), 422, "validation_failed")
    err(book(http, ada, {**body(), "starts_at_local": 123}), 400, "malformed_request")
    assert my_res(http, ada) == []


def test_missing_fields(http, env):  # S1-16
    ada = env["ada"]
    for k in ["restaurant_id", "table_id", "starts_at_local", "party_size"]:
        b = body()
        del b[k]
        err(book(http, ada, b), 422, "validation_failed")
    for k in ["email", "password", "display_name"]:
        b = {"email": "q@example.com", "password": "12345678", "display_name": "Q"}
        del b[k]
        err(http.post("/auth/signup", json=b), 422, "validation_failed")


def test_unknown_fields_ignored(http, env):  # S1-05
    r = book(http, env["ada"], {**body(), "foo": 1, "notes": {"x": [1]}})
    assert r.status_code == 201, r.text
    s = http.post("/auth/signup", json={"email": "u@example.com", "password": "12345678", "display_name": "U", "role": "admin"})
    assert s.status_code == 201, s.text


def test_availability_params(http, env):  # S1-06, S1-17, S1-42, S1-43
    base = {"restaurant_id": "r_anker", "date": THU_S, "party_size": "2"}
    ok = http.get("/availability", params=base)
    assert ok.status_code == 200
    extra = http.get("/availability", params={**base, "x": "1", "foo": "bar"})
    assert extra.status_code == 200 and extra.json() == ok.json()
    for k in base:
        p = dict(base)
        del p[k]
        err(http.get("/availability", params=p), 422, "validation_failed")
    for bad in ["1e9", "4.0", "+4", "abc", "0", "-1", "", " 4"]:
        err(http.get("/availability", params={**base, "party_size": bad}), 422, "validation_failed")
    for bad in ["2026-02-30", "2026-13-01", "26-09-24", f"{THU_S}T00:00", "yesterday"]:
        err(http.get("/availability", params={**base, "date": bad}), 422, "validation_failed")
    err(http.get("/availability", params={**base, "restaurant_id": "r_nope"}), 404, "not_found")


def test_fixture_id_length(http):  # S1-07
    f = base_fixture()
    r64 = copy.deepcopy(ANKER)
    r64["id"] = "r" * 64
    f["restaurants"] = [r64]
    reset(http, f)
    assert http.get(f"/restaurants/{'r' * 64}").status_code == 200
    f2 = base_fixture()
    r65 = copy.deepcopy(ANKER)
    r65["id"] = "r" * 65
    f2["restaurants"] = [r65]
    err(http.post("/_test/reset", json=f2), 422, "validation_failed")
