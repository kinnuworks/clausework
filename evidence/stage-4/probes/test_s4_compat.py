"""S4-80..S4-83: a stage-3-frozen export (TK_S3_URL) imports into stage 4. Imported series, with moved and cancelled
occurrences, can be amended; imported bookings can be replanned; receipts, histories and retries stay valid.
Stage-1/2 exports are covered by the carried test_s3_compat (TK_S1_URL, TK_S2_URL)."""
import uuid

import httpx
import pytest

from conftest import H, THU_S
from s3lib import day, s3_fixture
from s4lib import S3_URL, inst

pytestmark = pytest.mark.skipif(not S3_URL, reason="TK_S3_URL (stage-3-frozen) not set")


def test_stage3_export_into_stage4(http):
    with httpx.Client(base_url=S3_URL, timeout=15.0) as c:
        assert c.post("/_test/reset", json=s3_fixture()).status_code == 204
        ada = c.post("/auth/login", json={"email": "ada@example.com", "password": "correct horse"}).json()["token"]
        mgr = c.post("/auth/login", json={"email": "mgr@example.com", "password": "manager pass"}).json()["token"]
        kb, ks = str(uuid.uuid4()), str(uuid.uuid4())
        b = {"restaurant_id": "r_pol", "table_id": "p_2", "starts_at_local": f"{THU_S}T19:00", "party_size": 2}
        A = c.post("/reservations", json=b, headers=H(ada, kb))
        assert A.status_code == 201
        A = A.json()
        sb = {"anchor_reference": A["reference"], "count": 4, "interval_weeks": 1}
        S = c.post("/series", json=sb, headers=H(ada, ks))
        assert S.status_code == 201, S.text
        S = S.json()
        occ = S["occurrences"]
        assert c.patch(f"/reservations/{occ[1]['reference']}", json={"table_id": "p_3"}, headers=H(ada)).status_code == 200
        assert c.post(f"/reservations/{occ[2]['reference']}/cancel", headers=H(ada)).status_code == 200
        series_now = c.get(f"/series/{S['series_id']}", headers=H(ada)).json()
        hists = {o["reference"]: c.get(f"/reservations/{o['reference']}/history", headers=H(ada)).json() for o in occ}
        E = c.get("/_test/export").json()
    assert http.post("/_test/import", json=E).status_code == 204
    assert http.get(f"/series/{S['series_id']}", headers=H(ada)).json() == series_now
    for ref, h in hists.items():
        assert http.get(f"/reservations/{ref}/history", headers=H(ada)).json() == h
    rb_ = http.post("/reservations", json=b, headers=H(ada, kb))
    assert rb_.status_code == 200 and rb_.json() == A
    rs = http.post("/series", json=sb, headers=H(ada, ks))
    assert rs.status_code == 200 and rs.json() == S
    rev = series_now["revision"]
    am = http.post(f"/series/{S['series_id']}/amend", json={"expected_revision": rev, "from_index": 0, "local_time": "20:00"},
                   headers=H(ada, str(uuid.uuid4())))
    assert am.status_code == 201, am.text
    o = am.json()["occurrences"]
    assert [x["reservation"]["starts_at_local"][-5:] for x in o] == ["20:00", "19:00", "19:00", "20:00"]
    assert am.json()["revision"] == rev + 1
    p = http.post("/restaurants/r_pol/replans", json={"table_id": "p_2", "from": inst(f"{THU_S}T18:00"),
                                                       "to": inst(f"{THU_S}T23:00")}, headers=H(mgr, str(uuid.uuid4())))
    assert p.status_code == 201, p.text
    assert p.json()["assignments"][0]["reference"] == A["reference"]
    ap = http.post(f"/restaurants/r_pol/replans/{p.json()['plan_id']}/apply", json={}, headers=H(mgr, str(uuid.uuid4())))
    assert ap.status_code == 201, ap.text
    assert http.get(f"/reservations/{A['reference']}", headers=H(ada)).json()["table_ids"] != ["p_2"]
