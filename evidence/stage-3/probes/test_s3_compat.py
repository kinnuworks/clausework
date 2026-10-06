"""S3-80..S3-83: exports from frozen stage-1 (TK_S1_URL, tag stage-1-frozen) and frozen stage-2 (TK_S2_URL, tag
stage-2-frozen) import into stage 3; tokens, replays and references survive; imported bookings can anchor a series."""
import uuid

import httpx
import pytest

from conftest import FRI_S, H, THU_S, base_fixture, body, err
from s2lib import lb, s2_fixture
from s3lib import S1_URL, S2_URL

ALLOWED_EXTRA = {"table_ids", "revision", "accepted_terms"}


def same_plus(new, old):
    """Every earlier-stage field equal; only stage-2/3 fields may be added (RULING S3-81)."""
    for k, v in old.items():
        assert new.get(k) == v, (k, new.get(k), v)
    assert set(new) - set(old) <= ALLOWED_EXTRA, set(new) - set(old)
    if "revision" in new and "revision" not in old:
        assert new["revision"] == 1


def build_source(url, fixture, b1, b2):
    with httpx.Client(base_url=url, timeout=15.0) as c:
        assert c.post("/_test/reset", json=fixture).status_code == 204
        ada = c.post("/auth/login", json={"email": "ada@example.com", "password": "correct horse"}).json()["token"]
        k1, k2, k3 = (str(uuid.uuid4()) for _ in range(3))
        r1 = c.post("/reservations", json=b1, headers=H(ada, k1))
        assert r1.status_code == 201
        r2 = c.post("/reservations", json=b2, headers=H(ada, k2)).json()
        m = c.post("/reservation-moves", json={"moves": [{"reference": r2["reference"]}]}, headers=H(ada, str(uuid.uuid4())))
        assert m.status_code == 201
        assert c.post("/reservations", json={**b1, "party_size": 0}, headers=H(ada, k3)).status_code == 422
        E = c.get("/_test/export").json()
    return E, ada, (k1, r1.json()), r2, k3


def check_target(http, E, ada, k1r1, r2, k3, b1, fresh_body):
    assert http.post("/_test/import", json=E).status_code == 204
    k1, r1 = k1r1
    g = http.get(f"/reservations/{r1['reference']}", headers=H(ada))
    assert g.status_code == 200, g.text
    same_plus(g.json(), r1)
    assert g.json().get("revision", 1) == 1
    rp = http.post("/reservations", json=b1, headers=H(ada, k1))
    assert rp.status_code == 200
    same_plus(rp.json(), r1)
    err(http.post("/reservations", json={**b1, "party_size": 1}, headers=H(ada, k1)), 409, "idempotency_key_reuse")
    assert http.post("/reservations", json=fresh_body, headers=H(ada, k3)).status_code == 201
    assert http.post("/auth/login", json={"email": "ada@example.com", "password": "correct horse"}).status_code == 200
    s = http.post("/series", json={"anchor_reference": r2["reference"], "count": 2, "interval_weeks": 1},
                  headers=H(ada, str(uuid.uuid4())))
    assert s.status_code == 201, s.text
    occ = s.json()["occurrences"]
    assert occ[0]["reference"] == r2["reference"]
    same_plus(occ[0]["reservation"], r2)
    h = http.get(f"/reservations/{r2['reference']}/history", headers=H(ada))
    assert h.status_code == 200
    d = http.get(f"/reservations/{r2['reference']}/decision", headers=H(ada))
    assert d.status_code == 200 and d.json()["accepted_terms"]["policy_version"] == 0


@pytest.mark.skipif(not S1_URL, reason="TK_S1_URL (stage-1-frozen) not set")
def test_stage1_export_into_stage3(http):
    b1 = body("t_2", f"{THU_S}T19:00", 3)
    b2 = body("t_1", f"{FRI_S}T19:00", 2)
    E, ada, k1r1, r2, k3 = build_source(S1_URL, base_fixture(), b1, b2)
    check_target(http, E, ada, k1r1, r2, k3, b1, body("t_3", f"{FRI_S}T21:00", 2))


@pytest.mark.skipif(not S2_URL, reason="TK_S2_URL (stage-2-frozen) not set")
def test_stage2_export_into_stage3(http):
    b1 = lb(["w_1", "w_2"], f"{THU_S}T19:00", 5)
    b2 = lb("w_4", f"{FRI_S}T19:00", 2)
    E, ada, k1r1, r2, k3 = build_source(S2_URL, s2_fixture(), b1, b2)
    check_target(http, E, ada, k1r1, r2, k3, b1, lb("w_3", f"{FRI_S}T21:00", 2))
