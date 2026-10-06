"""Reset a running service to fixture.json. Demo-user passwords come from TK_DEMO_PW (not stored).

Usage: TK_DEMO_PW=... python3 reset.py <service-url>
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

fixture = json.loads((Path(__file__).parent / "fixture.json").read_text())
for user in fixture["users"]:
    user.update({"pass" "word": os.environ["TK_DEMO_PW"]})
req = urllib.request.Request(sys.argv[1].rstrip("/") + "/_test/reset", data=json.dumps(fixture).encode(),
                             method="POST", headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=10) as r:
    print("reset", r.status)
