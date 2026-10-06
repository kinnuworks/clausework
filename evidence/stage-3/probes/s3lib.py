"""Stage-3 helpers: fixture with managers, policies, DST restaurant."""
import copy
import os
import uuid
from datetime import date, timedelta

from conftest import ALL_DAYS, NOWR, THU, USERS, H, login, reset
from s2lib import GAR, LAT

S1_URL = os.environ.get("TK_S1_URL", "").rstrip("/")
S2_URL = os.environ.get("TK_S2_URL", "").rstrip("/")

MGR = {"id": "u_mgr", "email": "mgr@example.com", "password": "manager pass", "display_name": "Mia"}
POL = {
    "id": "r_pol", "name": "Policy Haus", "timezone": "Europe/Berlin",
    "slot_minutes": 30, "reservation_duration_minutes": 90, "cancellation_cutoff_minutes": 120,
    "opening_hours": ALL_DAYS("18:00", "23:00"),
    "tables": [{"id": "p_1", "label": "Eins", "capacity": 2}, {"id": "p_2", "label": "Zwei", "capacity": 4},
               {"id": "p_3", "label": "Drei", "capacity": 6}],
    "combinable": [["p_2", "p_1"]],
    "manager_user_ids": ["u_mgr"],
}
DSTR = {
    "id": "r_dst", "name": "Nachtcafe", "timezone": "Europe/Berlin",
    "slot_minutes": 30, "reservation_duration_minutes": 90, "cancellation_cutoff_minutes": 120,
    "opening_hours": [{"weekday": "sun", "opens": "00:00", "closes": "06:00"}],
    "tables": [{"id": "d_1", "label": "Nacht", "capacity": 4}], "combinable": [], "manager_user_ids": [],
}
NOW3 = {**NOWR, "combinable": [], "manager_user_ids": ["u_mgr"]}
TERMS0 = {"policy_version": 0, "slot_minutes": 30, "reservation_duration_minutes": 90,
          "cancellation_cutoff_minutes": 120, "opening_hours": ALL_DAYS("18:00", "23:00"),
          "capacities": {"p_1": 2, "p_2": 4, "p_3": 6}}
CHANGE_ORDER = ["table_id", "table_ids", "starts_at_local", "party_size"]


def day(n):
    return (THU + timedelta(days=n)).isoformat()


def s3_fixture(reservations=None):
    return {"users": copy.deepcopy(USERS) + [dict(MGR)],
            "restaurants": copy.deepcopy([POL, DSTR, NOW3, LAT, GAR]),
            "reservations": reservations or []}


def s3_env(http, reservations=None):
    reset(http, s3_fixture(reservations))
    return {"ada": login(http, "ada@example.com", "correct horse"),
            "bob": login(http, "bob@example.com", "battery staple"),
            "mgr": login(http, "mgr@example.com", "manager pass")}


def pol(eff, slot=30, dur=90, cut=120, hours=None, caps=None):
    return {"effective_from": eff, "slot_minutes": slot, "reservation_duration_minutes": dur,
            "cancellation_cutoff_minutes": cut, "opening_hours": hours if hours is not None else ALL_DAYS("18:00", "23:00"),
            "capacities": caps if caps is not None else {"p_1": 2, "p_2": 4, "p_3": 6}}


def publish(http, tok, body, rest="r_pol", key=None):
    return http.post(f"/restaurants/{rest}/policies", json=body, headers=H(tok, key or str(uuid.uuid4())))


def rb(tables, local, party=2, rest="r_pol"):
    b = {"restaurant_id": rest, "starts_at_local": local, "party_size": party}
    if isinstance(tables, str):
        b["table_id"] = tables
    else:
        b["table_ids"] = list(tables)
    return b


def mk(http, tok, b, key=None):
    r = http.post("/reservations", json=b, headers=H(tok, key or str(uuid.uuid4())))
    assert r.status_code == 201, r.text
    return r.json()


def hist(http, tok, ref):
    r = http.get(f"/reservations/{ref}/history", headers=H(tok))
    assert r.status_code == 200, r.text
    return r.json()


def terms_of(p, version):
    t = {k: v for k, v in p.items() if k != "effective_from"}
    t["policy_version"] = version
    return t
