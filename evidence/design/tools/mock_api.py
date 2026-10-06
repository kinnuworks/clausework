"""Design-check mock of the Tablekeeper stage-2 API, serving the static UI.

Only for capturing screens; the real service is the builder's. Stdlib only.
Usage: python3 mock_api.py <ui-dir> <port>
"""
import json
import secrets
import sys
import threading
from datetime import date as Date
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

UI = Path(sys.argv[1]).resolve()
PORT = int(sys.argv[2])
LOCK = threading.Lock()

RESTAURANTS = {
    "r_anker": {
        "id": "r_anker", "name": "Zum Anker", "timezone": "Europe/Berlin",
        "slot_minutes": 30, "reservation_duration_minutes": 90, "cancellation_cutoff_minutes": 120,
        "opening_hours": [{"weekday": d, "opens": "18:00", "closes": "22:30"} for d in ("tue", "wed", "thu", "fri", "sat", "sun")],
        "tables": [
            {"id": "t_1", "label": "1", "capacity": 2},
            {"id": "t_2", "label": "2", "capacity": 4},
            {"id": "t_3", "label": "3", "capacity": 4},
            {"id": "t_4", "label": "Window booth", "capacity": 6},
            {"id": "t_5", "label": "5", "capacity": 2},
        ],
        "combinable": [["t_1", "t_2"], ["t_2", "t_3"]],
    },
    "r_lumen": {
        "id": "r_lumen", "name": "Lumen Dining Room", "timezone": "America/New_York",
        "slot_minutes": 30, "reservation_duration_minutes": 90, "cancellation_cutoff_minutes": 120,
        "opening_hours": [{"weekday": "fri", "opens": "17:30", "closes": "21:00"}],
        "tables": [{"id": "l_1", "label": "1", "capacity": 4}, {"id": "l_2", "label": "2", "capacity": 8}],
        "combinable": [],
    },
}
TAKEN = {("r_anker", "19:00", "t_2"), ("r_anker", "19:00", "t_4"), ("r_anker", "19:30", "t_2"),
         ("r_anker", "20:00", "t_1"), ("r_anker", "20:30", "t_3")}
USERS = {"ada@example.com": {"user_id": "u_ada", "display_name": "Ada Lovelace", "pw": "correct horse"}}
TOKENS = {}
IDEM = {}
RESERVATIONS = {}


def slots_for(rid, day):
    r = RESTAURANTS[rid]
    wd = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"][Date.fromisoformat(day).weekday()]
    hours = [o for o in r["opening_hours"] if o["weekday"] == wd]
    out = []
    for o in hours:
        h, m = map(int, o["opens"].split(":"))
        ch, cm = map(int, o["closes"].split(":"))
        t, close = h * 60 + m, ch * 60 + cm
        while t + r["reservation_duration_minutes"] <= close:
            out.append(f"{t // 60:02d}:{t % 60:02d}")
            t += r["slot_minutes"]
    return out


def busy(rid, day, hhmm, tid):
    if (rid, hhmm, tid) in TAKEN:
        return True
    return any(x["status"] == "confirmed" and x["restaurant_id"] == rid and tid in x["table_ids"]
               and x["starts_at_local"] == f"{day}T{hhmm}" for x in RESERVATIONS.values())


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send_json(self, status, obj):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def err(self, status, code):
        self.send_json(status, {"error": {"code": code, "message": code.replace("_", " ")}})

    def user(self):
        auth = self.headers.get("Authorization", "")
        return TOKENS.get(auth[7:]) if auth.startswith("Bearer ") else None

    def static(self, path):
        if path in ("/", "/signup", "/login", "/lookup"):
            f = UI / "index.html"
        else:
            f = (UI / path[len("/static/"):]).resolve()
            if not str(f).startswith(str(UI)) or not f.is_file():
                return self.err(404, "not_found")
        types = {".html": "text/html; charset=utf-8", ".css": "text/css", ".js": "text/javascript",
                 ".woff2": "font/woff2", ".svg": "image/svg+xml", ".txt": "text/plain"}
        body = f.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", types.get(f.suffix, "application/octet-stream"))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        p = u.path
        if p in ("/", "/signup", "/login", "/lookup") or p.startswith("/static/"):
            return self.static(p)
        if p == "/restaurants":
            return self.send_json(200, {"restaurants": [{k: r[k] for k in ("id", "name", "timezone")} for r in RESTAURANTS.values()]})
        if p.startswith("/restaurants/"):
            r = RESTAURANTS.get(p.split("/")[2])
            return self.send_json(200, r) if r else self.err(404, "not_found")
        if p == "/availability":
            q = {k: v[0] for k, v in parse_qs(u.query).items()}
            rid, day, party = q.get("restaurant_id"), q.get("date"), int(q.get("party_size", "0"))
            if rid not in RESTAURANTS:
                return self.err(404, "not_found")
            r = RESTAURANTS[rid]
            caps = {t["id"]: t["capacity"] for t in r["tables"]}
            slots = []
            for hhmm in slots_for(rid, day):
                free = [t["id"] for t in r["tables"] if t["capacity"] >= party and not busy(rid, day, hhmm, t["id"])]
                opts = [{"table_ids": [t], "capacity": caps[t]} for t in free]
                for a, b in r["combinable"]:
                    if caps[a] + caps[b] >= party and not busy(rid, day, hhmm, a) and not busy(rid, day, hhmm, b):
                        opts.append({"table_ids": [a, b], "capacity": caps[a] + caps[b]})
                slots.append({"starts_at_local": f"{day}T{hhmm}", "starts_at": f"{day}T{hhmm}:00+02:00",
                              "available_table_ids": free, "available_options": opts})
            return self.send_json(200, {"restaurant_id": rid, "date": day, "timezone": r["timezone"], "slots": slots})
        if p.startswith("/reservations/"):
            me = self.user()
            if not me:
                return self.err(401, "unauthenticated")
            x = RESERVATIONS.get(p.split("/")[2])
            return self.send_json(200, x) if x and x["user_id"] == me["user_id"] else self.err(404, "not_found")
        return self.err(404, "not_found")

    def do_POST(self):
        p = urlparse(self.path).path
        raw = self.rfile.read(int(self.headers.get("Content-Length", "0") or 0))
        try:
            body = json.loads(raw or b"{}")
        except ValueError:
            return self.err(400, "malformed_request")
        with LOCK:
            if p == "/auth/signup":
                if body["email"] in USERS:
                    return self.err(409, "email_taken")
                USERS[body["email"]] = {"user_id": "u_" + secrets.token_hex(3), "display_name": body["display_name"], "pw": body["password"]}
            if p in ("/auth/signup", "/auth/login"):
                u = USERS.get(body.get("email"))
                if not u or u["pw"] != body.get("password"):
                    return self.err(401, "unauthenticated")
                tok = secrets.token_hex(16)
                TOKENS[tok] = u
                return self.send_json(201 if p.endswith("signup") else 200, {"user_id": u["user_id"], "display_name": u["display_name"], "token": tok})
            me = self.user()
            if not me:
                return self.err(401, "unauthenticated")
            if p == "/reservations":
                key = (me["user_id"], self.headers.get("Idempotency-Key"))
                if key in IDEM:
                    prev_body, resp = IDEM[key]
                    return self.send_json(200, resp) if prev_body == body else self.err(409, "idempotency_key_reuse")
                ids = body.get("table_ids") or [body.get("table_id")]
                day, hhmm = body["starts_at_local"].split("T")
                if any(busy(body["restaurant_id"], day, hhmm, t) for t in ids):
                    return self.err(409, "table_unavailable")
                ref = "".join(secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(6))
                res = {"reservation_id": "res_" + ref.lower(), "reference": ref, "restaurant_id": body["restaurant_id"],
                       "table_ids": ids, "party_size": body["party_size"], "status": "confirmed",
                       "starts_at_local": body["starts_at_local"], "starts_at": body["starts_at_local"] + ":00+02:00",
                       "user_id": me["user_id"]}
                if len(ids) == 1:
                    res["table_id"] = ids[0]
                RESERVATIONS[ref] = res
                IDEM[key] = (body, dict(res))
                return self.send_json(201, res)
            if p.startswith("/reservations/") and p.endswith("/cancel"):
                x = RESERVATIONS.get(p.split("/")[2])
                if not x or x["user_id"] != me["user_id"]:
                    return self.err(404, "not_found")
                if x["starts_at_local"].startswith("2020"):
                    return self.err(409, "cutoff_passed")
                x["status"] = "cancelled"
                return self.send_json(200, x)
        return self.err(404, "not_found")


ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
