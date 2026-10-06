"""S2-34..S2-36: an export produced by the frozen stage-1 service imports into stage 2.
Needs TK_S1_URL = base URL of a running frozen stage-1 service (tag stage-1-frozen)."""
import uuid

import pytest

from conftest import FRI_S, H, THU_S, base_fixture, body, err, new_client
from s2lib import S1_URL

pytestmark = pytest.mark.skipif(not S1_URL, reason="TK_S1_URL (frozen stage-1 service) not set")


def same_with_table_ids(new, old):
    """Stage-2 view of a stage-1 record: every stage-1 field equal; only `table_ids` may be added (= [table_id])."""
    for k, v in old.items():
        assert new.get(k) == v, (k, new.get(k), v)
    extra = set(new) - set(old)
    assert extra <= {"table_ids"}, extra
    if "table_ids" in new:
        assert new["table_ids"] == [old["table_id"]]


def test_stage1_export_into_stage2(http):
    with httpx_client(S1_URL) as s1:
        assert s1.post("/_test/reset", json=base_fixture()).status_code == 204
        ada = s1.post("/auth/login", json={"email": "ada@example.com", "password": "correct horse"}).json()["token"]
        su = s1.post("/auth/signup", json={"email": "carol@example.com", "password": "carolpass1", "display_name": "Carol"})
        carol = su.json()["token"]
        k1, k2, k3 = (str(uuid.uuid4()) for _ in range(3))
        b1 = body("t_2", f"{THU_S}T19:00", 3)
        r1 = s1.post("/reservations", json=b1, headers=H(ada, k1)).json()   # treat as a lost response
        rB = s1.post("/reservations", json=body("t_1", f"{THU_S}T19:00", 2), headers=H(ada, str(uuid.uuid4()))).json()
        assert s1.post(f"/reservations/{rB['reference']}/cancel", headers=H(ada)).status_code == 200
        rC = s1.post("/reservations", json=body("t_3", f"{FRI_S}T20:00", 2), headers=H(carol, str(uuid.uuid4()))).json()
        moves = {"moves": [{"reference": rC["reference"], "table_id": "t_1"}]}
        m1 = s1.post("/reservation-moves", json=moves, headers=H(carol, k2))
        assert m1.status_code == 201
        assert s1.post("/reservations", json={**b1, "party_size": 0}, headers=H(ada, k3)).status_code == 422
        recs = {u: s1.get("/reservations", headers=H(t)).json()["reservations"] for u, t in (("ada", ada), ("carol", carol))}
        E = s1.get("/_test/export").json()
    imp = http.post("/_test/import", json=E)
    assert imp.status_code == 204, imp.text
    for u, t in (("ada", ada), ("carol", carol)):
        got = http.get("/reservations", headers=H(t))
        assert got.status_code == 200
        lst = got.json()["reservations"]
        assert len(lst) == len(recs[u])
        for n, o in zip(lst, recs[u]):
            same_with_table_ids(n, o)
    assert http.post("/auth/login", json={"email": "carol@example.com", "password": "carolpass1"}).status_code == 200
    rp = http.post("/reservations", json=b1, headers=H(ada, k1))
    assert rp.status_code == 200, rp.text
    same_with_table_ids(rp.json(), r1)
    mp = http.post("/reservation-moves", json=moves, headers=H(carol, k2))
    assert mp.status_code == 200, mp.text
    for n, o in zip(mp.json()["reservations"], m1.json()["reservations"]):
        same_with_table_ids(n, o)
    err(http.post("/reservations", json={**b1, "party_size": 2}, headers=H(ada, k1)), 409, "idempotency_key_reuse")
    fresh = http.post("/reservations", json=body("t_2", f"{FRI_S}T18:00", 2), headers=H(ada, k3))
    assert fresh.status_code == 201, fresh.text
    a = http.get("/availability", params={"restaurant_id": "r_anker", "date": THU_S, "party_size": 2}).json()
    s19 = [s for s in a["slots"] if s["starts_at_local"] == f"{THU_S}T19:00"][0]
    assert s19["available_table_ids"] == ["t_1", "t_3"]
    assert [o["table_ids"] for o in s19["available_options"]] == [["t_1"], ["t_3"]]


def httpx_client(url):
    import httpx
    return httpx.Client(base_url=url, timeout=15.0)
