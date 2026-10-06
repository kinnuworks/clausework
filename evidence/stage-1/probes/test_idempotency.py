"""S1-18, S1-30..35, S1-38, S1-39."""
import json
import uuid

from conftest import FRI_S, H, THU_S, body, book, err, my_res


def test_missing_and_bad_key(http, env):  # S1-18, S1-30, S1-39
    ada = env["ada"]
    err(http.post("/reservations", json=body(), headers=H(ada)), 400, "missing_idempotency_key")
    err(http.post("/reservations", json=body(), headers=H(ada, "")), 400, "missing_idempotency_key")
    err(http.post("/reservations", json=body(), headers=H(ada, "k" * 256)), 422, "validation_failed")
    err(http.post("/reservations", json=body()), 401, "unauthenticated")
    assert my_res(http, ada) == []
    r = http.post("/reservations", json=body(), headers=H(ada, "k" * 255))
    assert r.status_code == 201, r.text


def test_replay_identical(http, env):  # S1-32, S1-33, S1-34
    ada = env["ada"]
    key = str(uuid.uuid4())
    b = body("t_2", f"{THU_S}T19:00", 3)
    r1 = book(http, ada, b, key)
    assert r1.status_code == 201
    r2 = book(http, ada, b, key)
    assert r2.status_code == 200 and r2.json() == r1.json()
    reordered = json.dumps({"party_size": 3, "starts_at_local": f"{THU_S}T19:00", "table_id": "t_2",
                            "restaurant_id": "r_anker"}, indent=3)
    r3 = http.post("/reservations", content=reordered.encode(),
                   headers={**H(ada, key), "Content-Type": "application/json"})
    assert r3.status_code == 200 and r3.json() == r1.json()
    err(book(http, ada, {**b, "party_size": 2}, key), 409, "idempotency_key_reuse")
    err(book(http, ada, {**b, "party_size": 0}, key), 409, "idempotency_key_reuse")
    err(book(http, ada, {**b, "restaurant_id": "r_nope"}, key), 409, "idempotency_key_reuse")
    err(book(http, ada, {**b, "starts_at_local": f"{THU_S}T19:15"}, key), 409, "idempotency_key_reuse")
    assert len(my_res(http, ada)) == 1


def test_key_scoped_per_user(http, env):  # S1-31
    key = "shared-key-1"
    a = book(http, env["ada"], body("t_1", f"{THU_S}T19:00"), key)
    b = book(http, env["bob"], body("t_2", f"{THU_S}T19:00"), key)
    assert a.status_code == 201 and b.status_code == 201
    assert a.json()["reference"] != b.json()["reference"]
    c = book(http, env["bob"], body("t_1", f"{THU_S}T19:00"), key)
    err(c, 409, "idempotency_key_reuse")


def test_key_after_failure_is_fresh(http, env):  # S1-35
    ada, bob = env["ada"], env["bob"]
    k1 = str(uuid.uuid4())
    err(book(http, ada, {**body(), "party_size": 0}, k1), 422, "validation_failed")
    r = book(http, ada, body("t_2", f"{THU_S}T19:00"), k1)
    assert r.status_code == 201, r.text
    k2 = str(uuid.uuid4())
    b = body("t_2", f"{THU_S}T20:00")
    err(book(http, bob, b, k2), 409, "table_unavailable")
    assert http.post(f"/reservations/{r.json()['reference']}/cancel", headers=H(ada)).status_code == 200
    r2 = book(http, bob, b, k2)
    assert r2.status_code == 201, r2.text
    assert book(http, bob, b, k2).status_code == 200


def test_replay_after_change_and_cancel(http, env):  # S1-38
    ada = env["ada"]
    key = str(uuid.uuid4())
    b = body("t_2", f"{FRI_S}T19:00", 2)
    r1 = book(http, ada, b, key)
    ref = r1.json()["reference"]
    p = http.patch(f"/reservations/{ref}", json={"party_size": 4}, headers=H(ada))
    assert p.status_code == 200, p.text
    r2 = book(http, ada, b, key)
    assert r2.status_code == 200 and r2.json() == r1.json()
    assert http.post(f"/reservations/{ref}/cancel", headers=H(ada)).status_code == 200
    r3 = book(http, ada, b, key)
    assert r3.status_code == 200 and r3.json() == r1.json() and r3.json()["status"] == "confirmed"
    lst = my_res(http, ada)
    assert len(lst) == 1 and lst[0]["status"] == "cancelled" and lst[0]["party_size"] == 4
