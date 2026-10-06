"""Stage-1 sealed probes. Run: TK_BASE_URL=http://127.0.0.1:PORT python -m pytest -q -p no:cacheprovider <dir>"""
import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import httpx
import pytest

BASE = os.environ.get("TK_BASE_URL", "http://127.0.0.1:8080").rstrip("/")
WD = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
ALL_DAYS = lambda o, c: [{"weekday": d, "opens": o, "closes": c} for d in WD]


def _future_thursday():
    d = date.today() + timedelta(days=60)
    while d.weekday() != 3:
        d += timedelta(days=1)
    return d


THU = _future_thursday()
FRI = THU + timedelta(days=1)
WED = THU - timedelta(days=1)
THU_S, FRI_S, WED_S = THU.isoformat(), FRI.isoformat(), WED.isoformat()


def _pick_now_tz():
    now = datetime.now(timezone.utc)
    for tz in ["UTC", "Asia/Tokyo", "America/New_York", "Asia/Kolkata", "Europe/Berlin",
               "America/Los_Angeles", "Pacific/Auckland", "Asia/Dubai", "America/Sao_Paulo",
               "Asia/Singapore", "Pacific/Honolulu"]:
        if 1 <= now.astimezone(ZoneInfo(tz)).hour <= 14:
            return tz
    return "UTC"


NOW_TZ = _pick_now_tz()

USERS = [
    {"id": "u_ada", "email": "ada@example.com", "password": "correct horse", "display_name": "Ada"},
    {"id": "u_bob", "email": "bob@example.com", "password": "battery staple", "display_name": "Bob"},
]
ANKER = {
    "id": "r_anker", "name": "Zum Anker", "timezone": "Europe/Berlin",
    "slot_minutes": 30, "reservation_duration_minutes": 90, "cancellation_cutoff_minutes": 120,
    "opening_hours": [{"weekday": "thu", "opens": "18:00", "closes": "23:00"},
                      {"weekday": "fri", "opens": "18:00", "closes": "23:30"}],
    "tables": [{"id": "t_1", "label": "1", "capacity": 2},
               {"id": "t_2", "label": "2", "capacity": 4},
               {"id": "t_3", "label": "3", "capacity": 2}],
}
GRID = {
    "id": "r_grid", "name": "Grid Haus", "timezone": "Europe/Berlin",
    "slot_minutes": 45, "reservation_duration_minutes": 60, "cancellation_cutoff_minutes": 60,
    "opening_hours": ALL_DAYS("17:15", "23:00"),
    "tables": [{"id": "g_1", "label": "G1", "capacity": 4}],
}
BERLIN_NIGHT = {
    "id": "r_bn", "name": "Berlin Nacht", "timezone": "Europe/Berlin",
    "slot_minutes": 30, "reservation_duration_minutes": 90, "cancellation_cutoff_minutes": 120,
    "opening_hours": [{"weekday": "sun", "opens": "00:00", "closes": "06:00"},
                      {"weekday": "thu", "opens": "18:00", "closes": "23:00"}],
    "tables": [{"id": "b_1", "label": "B1", "capacity": 2}, {"id": "b_2", "label": "B2", "capacity": 4}],
}
NY_NIGHT = {
    "id": "r_ny", "name": "NY Night", "timezone": "America/New_York",
    "slot_minutes": 30, "reservation_duration_minutes": 90, "cancellation_cutoff_minutes": 120,
    "opening_hours": [{"weekday": "sun", "opens": "00:00", "closes": "06:00"},
                      {"weekday": "thu", "opens": "18:00", "closes": "23:00"}],
    "tables": [{"id": "n_1", "label": "N1", "capacity": 2}, {"id": "n_2", "label": "N2", "capacity": 4}],
}
NOWR = {
    "id": "r_now", "name": "Now Cafe", "timezone": NOW_TZ,
    "slot_minutes": 15, "reservation_duration_minutes": 60, "cancellation_cutoff_minutes": 120,
    "opening_hours": ALL_DAYS("00:00", "23:30"),
    "tables": [{"id": "c_1", "label": "C1", "capacity": 4}, {"id": "c_2", "label": "C2", "capacity": 4}],
}
RESTAURANTS = [ANKER, GRID, BERLIN_NIGHT, NY_NIGHT, NOWR]


def base_fixture(reservations=None):
    return {"users": [dict(u) for u in USERS], "restaurants": [dict(r) for r in RESTAURANTS],
            "reservations": reservations or []}


def new_client():
    return httpx.Client(base_url=BASE, timeout=15.0,
                        limits=httpx.Limits(max_connections=100, max_keepalive_connections=100))


@pytest.fixture(scope="session")
def http():
    with new_client() as c:
        yield c


def reset(http, fixture=None):
    r = http.post("/_test/reset", json=fixture if fixture is not None else base_fixture())
    assert r.status_code == 204, r.text
    return r


def login(http, email, password):
    r = http.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture
def env(http):
    reset(http)
    ada = login(http, "ada@example.com", "correct horse")
    bob = login(http, "bob@example.com", "battery staple")
    return {"ada": ada, "bob": bob}


def H(token=None, key=None):
    h = {}
    if token is not None:
        h["Authorization"] = f"Bearer {token}"
    if key is not None:
        h["Idempotency-Key"] = key
    return h


def body(table="t_2", local=None, party=2, rest="r_anker"):
    return {"restaurant_id": rest, "table_id": table,
            "starts_at_local": local or f"{THU_S}T19:00", "party_size": party}


def book(http, token, b, key=None):
    return http.post("/reservations", json=b, headers=H(token, key or str(uuid.uuid4())))


def book_ok(http, token, b):
    r = book(http, token, b)
    assert r.status_code == 201, r.text
    return r.json()


def err(r, status, code):
    assert r.status_code == status, f"expected {status} {code}, got {r.status_code} {r.text}"
    j = r.json()
    assert isinstance(j, dict) and isinstance(j.get("error"), dict), r.text
    assert j["error"].get("code") == code, f"expected code {code}, got {r.text}"
    assert isinstance(j["error"].get("message"), str)


def my_res(http, token):
    r = http.get("/reservations", headers=H(token))
    assert r.status_code == 200, r.text
    return r.json()["reservations"]


def get_res(http, token, ref):
    r = http.get(f"/reservations/{ref}", headers=H(token))
    assert r.status_code == 200, r.text
    return r.json()


def avail(http, rest, d, party):
    r = http.get("/availability", params={"restaurant_id": rest, "date": d, "party_size": party})
    assert r.status_code == 200, r.text
    return r.json()


def slot_tables(http, rest, d, party, local):
    for s in avail(http, rest, d, party)["slots"]:
        if s["starts_at_local"] == local:
            return s["available_table_ids"]
    return None


def parse_ts(s):
    assert isinstance(s, str) and len(s) >= 20, s
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    assert dt.tzinfo is not None, s
    return dt


def resolve(local, tz):
    """local 'YYYY-MM-DDTHH:MM' -> aware datetime in zone (first occurrence) or None if nonexistent."""
    naive = datetime.strptime(local, "%Y-%m-%dT%H:%M")
    z = ZoneInfo(tz)
    utc = naive.replace(tzinfo=z, fold=0).astimezone(timezone.utc)
    back = utc.astimezone(z)
    if back.replace(tzinfo=None) != naive:
        return None
    return back


def same_instant_offset(api_ts, ref_dt):
    a = parse_ts(api_ts)
    assert a.astimezone(timezone.utc) == ref_dt.astimezone(timezone.utc), (api_ts, ref_dt)
    assert a.utcoffset() == ref_dt.utcoffset(), (api_ts, ref_dt)


def ref_slots(rest, d, party, booked):
    """booked: list of (table_id, start_utc). Returns [(local, aware_start, [table ids])]."""
    tz = rest["timezone"]
    dd = date.fromisoformat(d)
    dur = timedelta(minutes=rest["reservation_duration_minutes"])
    step = timedelta(minutes=rest["slot_minutes"])
    out = []
    for h in rest["opening_hours"]:
        if h["weekday"] != WD[dd.weekday()]:
            continue
        o = datetime.combine(dd, time.fromisoformat(h["opens"]))
        c = datetime.combine(dd, time.fromisoformat(h["closes"]))
        close_utc = resolve(c.strftime("%Y-%m-%dT%H:%M"), tz).astimezone(timezone.utc)
        t = o
        while t < c:
            loc = t.strftime("%Y-%m-%dT%H:%M")
            a = resolve(loc, tz)
            if a is not None:
                s = a.astimezone(timezone.utc)
                if s + dur <= close_utc:
                    tables = [tb["id"] for tb in rest["tables"] if tb["capacity"] >= party and not any(
                        bt == tb["id"] and bs < s + dur and s < bs + dur for bt, bs in booked)]
                    out.append((loc, a, tables))
            t += step
    return out


def burst(fns, workers=50):
    """Release all callables at the same instant; return results in order."""
    barrier = threading.Barrier(len(fns))

    def run(fn):
        barrier.wait()
        return fn()

    with ThreadPoolExecutor(max_workers=max(workers, len(fns))) as ex:
        return list(ex.map(run, fns))


def now_local():
    return datetime.now(timezone.utc).astimezone(ZoneInfo(NOW_TZ))


def floor15(dt):
    return dt.replace(minute=dt.minute - dt.minute % 15, second=0, microsecond=0)


def now_slot(delta_minutes):
    return floor15(now_local() + timedelta(minutes=delta_minutes)).strftime("%Y-%m-%dT%H:%M")


def past_slot():
    return (now_local() - timedelta(days=1)).strftime("%Y-%m-%dT12:00")
