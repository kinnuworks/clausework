"""S1-11, S1-59, S1-63 — cutoff against the real clock (restaurant r_now, cutoff 120, slot 15, duration 60)."""
from conftest import H, body, book, book_ok, err, get_res, now_slot, past_slot


def nb(table, local, party=2):
    return body(table, local, party, rest="r_now")


def test_past_booking_allowed_but_not_cancellable(http, env):  # S1-11, S1-59
    ada = env["ada"]
    r = book(http, ada, nb("c_1", past_slot()))
    assert r.status_code == 201, r.text
    ref = r.json()["reference"]
    err(http.post(f"/reservations/{ref}/cancel", headers=H(ada)), 409, "cutoff_passed")
    err(http.patch(f"/reservations/{ref}", json={"party_size": 3}, headers=H(ada)), 409, "cutoff_passed")
    assert get_res(http, ada, ref)["status"] == "confirmed"
    assert get_res(http, ada, ref)["party_size"] == 2


def test_within_cutoff(http, env):  # S1-59, S1-63
    ada = env["ada"]
    near = book_ok(http, ada, nb("c_1", now_slot(60)))
    err(http.post(f"/reservations/{near['reference']}/cancel", headers=H(ada)), 409, "cutoff_passed")
    err(http.patch(f"/reservations/{near['reference']}", json={"starts_at_local": now_slot(300)}, headers=H(ada)),
        409, "cutoff_passed")
    assert get_res(http, ada, near["reference"]) == near


def test_outside_cutoff_and_current_start_rule(http, env):  # S1-59, S1-63
    ada = env["ada"]
    far = book_ok(http, ada, nb("c_2", now_slot(300)))
    # cutoff is measured against the CURRENT start: moving a far booking to within the cutoff is allowed
    p = http.patch(f"/reservations/{far['reference']}", json={"starts_at_local": now_slot(60)}, headers=H(ada))
    assert p.status_code == 200, p.text
    far2 = book_ok(http, ada, nb("c_1", now_slot(300)))
    c = http.post(f"/reservations/{far2['reference']}/cancel", headers=H(ada))
    assert c.status_code == 200 and c.json()["status"] == "cancelled"
