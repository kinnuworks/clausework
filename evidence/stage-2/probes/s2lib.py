"""Stage-2 helpers: fixture with combinable pairs and a reference model for available_options."""
import copy
import os

from conftest import NOWR, THU_S, USERS, ref_slots

S1_URL = os.environ.get("TK_S1_URL", "").rstrip("/")

LAT = {
    "id": "r_lat", "name": "Zur Laterne", "timezone": "Europe/Berlin",
    "slot_minutes": 30, "reservation_duration_minutes": 90, "cancellation_cutoff_minutes": 120,
    "opening_hours": [{"weekday": "thu", "opens": "18:00", "closes": "23:00"},
                      {"weekday": "fri", "opens": "18:00", "closes": "23:30"}],
    "tables": [{"id": "w_1", "label": "Fenster", "capacity": 2},
               {"id": "w_2", "label": "Kamin", "capacity": 4},
               {"id": "w_3", "label": "Ecke", "capacity": 2},
               {"id": "w_4", "label": "Terrasse", "capacity": 6}],
    "combinable": [["w_1", "w_2"], ["w_3", "w_2"], ["w_4", "w_1"]],
}
GAR = {
    "id": "r_gar", "name": "Gartenhaus", "timezone": "Europe/Berlin",
    "slot_minutes": 30, "reservation_duration_minutes": 90, "cancellation_cutoff_minutes": 120,
    "opening_hours": [{"weekday": "thu", "opens": "18:00", "closes": "23:00"}],
    "tables": [{"id": "g_a", "label": "Linde", "capacity": 4}],
    "combinable": [],
}
LABEL = {t["id"]: t["label"] for t in LAT["tables"] + GAR["tables"]}


def s2_fixture(reservations=None):
    return {"users": copy.deepcopy(USERS), "restaurants": copy.deepcopy([LAT, GAR, {**NOWR, "combinable": []}]),
            "reservations": reservations or []}


def lb(tables, local=None, party=2, rest="r_lat"):
    b = {"restaurant_id": rest, "starts_at_local": local or f"{THU_S}T19:00", "party_size": party}
    if isinstance(tables, str):
        b["table_id"] = tables
    else:
        b["table_ids"] = list(tables)
    return b


def ref_options(rest, d, party, booked):
    """booked: list of (set_of_table_ids, start_utc). Returns {local: (singles_ids, options)}."""
    flat = [(t, s) for ts, s in booked for t in ts]
    out = {}
    cap = {t["id"]: t["capacity"] for t in rest["tables"]}
    free_by_slot = {x[0]: set(x[2]) for x in ref_slots(rest, d, 1, flat)}
    for loc, a, singles in ref_slots(rest, d, party, flat):
        free1 = free_by_slot[loc]
        opts = [{"table_ids": [t], "capacity": cap[t]} for t in singles]
        for p in rest.get("combinable", []):
            if all(t in free1 for t in p) and cap[p[0]] + cap[p[1]] >= party:
                opts.append({"table_ids": list(p), "capacity": cap[p[0]] + cap[p[1]]})
        out[loc] = (singles, opts)
    return out
