"""Stage-4 helpers: fixture, brute-force reference planner for replans."""
import copy
import os
import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from conftest import ALL_DAYS, NOWR, THU_S, USERS, H, login, parse_ts, reset
from s3lib import DSTR, MGR

S3_URL = os.environ.get("TK_S3_URL", "").rstrip("/")
BERLIN = ZoneInfo("Europe/Berlin")

R4 = {
    "id": "r_four", "name": "Vier Linden", "timezone": "Europe/Berlin",
    "slot_minutes": 30, "reservation_duration_minutes": 90, "cancellation_cutoff_minutes": 120,
    "opening_hours": ALL_DAYS("12:00", "23:30"),
    "tables": [{"id": "q_1", "label": "Linde", "capacity": 2}, {"id": "q_2", "label": "Birke", "capacity": 2},
               {"id": "q_3", "label": "Eiche", "capacity": 4}, {"id": "q_4", "label": "Ahorn", "capacity": 4},
               {"id": "q_5", "label": "Ulme", "capacity": 6}, {"id": "q_6", "label": "Buche", "capacity": 2}],
    "combinable": [["q_1", "q_2"], ["q_3", "q_4"], ["q_6", "q_2"], ["q_5", "q_1"]],
    "manager_user_ids": ["u_mgr"],
}
FAR = {
    "id": "r_far", "name": "Fernhaus", "timezone": "Europe/Berlin",
    "slot_minutes": 30, "reservation_duration_minutes": 90, "cancellation_cutoff_minutes": 120,
    "opening_hours": ALL_DAYS("12:00", "23:30"),
    "tables": [{"id": "f_1", "label": "Fern1", "capacity": 4}, {"id": "f_2", "label": "Fern2", "capacity": 4}],
    "combinable": [], "manager_user_ids": ["u_mgr"],
}
NOW4 = {**NOWR, "combinable": [["c_1", "c_2"]], "manager_user_ids": ["u_mgr"]}
DST4 = {**DSTR, "manager_user_ids": ["u_mgr"]}


def s4_fixture(reservations=None):
    return {"users": copy.deepcopy(USERS) + [dict(MGR)], "restaurants": copy.deepcopy([R4, FAR, NOW4, DST4]),
            "reservations": reservations or []}


def s4_env(http, reservations=None):
    reset(http, s4_fixture(reservations))
    return {"ada": login(http, "ada@example.com", "correct horse"),
            "bob": login(http, "bob@example.com", "battery staple"),
            "mgr": login(http, "mgr@example.com", "manager pass")}


def inst(local):
    """'YYYY-MM-DDTHH:MM' Berlin -> RFC 3339 with offset."""
    return datetime.strptime(local, "%Y-%m-%dT%H:%M").replace(tzinfo=BERLIN).isoformat()


def preview(http, tok, table, frm, to, rest="r_four", key=None):
    return http.post(f"/restaurants/{rest}/replans", json={"table_id": table, "from": frm, "to": to},
                     headers=H(tok, key or str(uuid.uuid4())))


def apply_plan(http, tok, plan_id, rest="r_four", key=None):
    return http.post(f"/restaurants/{rest}/replans/{plan_id}/apply", json={}, headers=H(tok, key or str(uuid.uuid4())))


def options(rest):
    opts = [[t["id"]] for t in rest["tables"]] + [list(p) for p in rest["combinable"]]
    return opts


def ref_plan(rest, bookings, closure, prior_closures=()):
    """bookings: list of dicts {reference, start, end (utc datetimes), party, tables(set), caps(dict), status}.
    closure: (table_id, from_utc, to_utc). Returns None if infeasible else
    {'assign': {ref: option_list}, 'moved': n, 'unused': n}. Brute force over all option vectors."""
    ct, cf, cto = closure
    conf = [b for b in bookings if b["status"] == "confirmed"]
    considered = sorted([b for b in conf if b["start"] < cto and cf < b["end"]], key=lambda b: b["reference"])
    fixed = [b for b in conf if b not in considered]
    closures = list(prior_closures) + [closure]
    opts = options(rest)

    def ok_alone(b, o):
        if sum(b["caps"][t] for t in o) < b["party"]:
            return False
        for (t, f, to) in closures:
            if t in o and b["start"] < to and f < b["end"]:
                return False
        for x in fixed:
            if set(o) & x["tables"] and b["start"] < x["end"] and x["start"] < b["end"]:
                return False
        return True
    cand = [[(r, o) for r, o in enumerate(opts) if ok_alone(b, o)] for b in considered]
    best = [None]

    def rec(i, chosen, moved, unused):
        if i == len(considered):
            key = (moved, unused, [r for r, _ in chosen])
            if best[0] is None or key < best[0][0]:
                best[0] = (key, list(chosen))
            return
        b = considered[i]
        for r, o in cand[i]:
            clash = False
            for j, (rj, oj) in enumerate(chosen):
                bj = considered[j]
                if set(o) & set(oj) and b["start"] < bj["end"] and bj["start"] < b["end"]:
                    clash = True
                    break
            if clash:
                continue
            m = 0 if set(o) == b["tables"] else 1
            u = sum(b["caps"][t] for t in o) - b["party"]
            chosen.append((r, o))
            rec(i + 1, chosen, moved + m, unused + u)
            chosen.pop()
    rec(0, [], 0, 0)
    if best[0] is None:
        return None
    (moved, unused, _), chosen = best[0]
    return {"considered": [b["reference"] for b in considered],
            "assign": {b["reference"]: o for b, (_, o) in zip(considered, chosen)},
            "changed": {b["reference"]: set(o) != b["tables"] for b, (_, o) in zip(considered, chosen)},
            "moved": moved, "unused": unused}


def booking_model(res):
    return {"reference": res["reference"], "start": parse_ts(res["starts_at"]).astimezone(timezone.utc),
            "end": parse_ts(res["ends_at"]).astimezone(timezone.utc), "party": res["party_size"],
            "tables": set(res["table_ids"]), "caps": res["accepted_terms"]["capacities"], "status": res["status"]}
