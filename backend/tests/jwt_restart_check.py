"""FIX-3: token issued before a backend restart must still work afterwards."""
import json
import subprocess
import sys
import time

import requests
from conftest import BASE_URL

creds = {"email": "Yumaclovstar@gmail.com", "password": "178910"}
r = requests.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=60)
assert r.status_code == 200, r.text[:300]
tok = r.json()["token"]
h = {"Authorization": f"Bearer {tok}"}
assert requests.get(f"{BASE_URL}/api/auth/me", headers=h, timeout=60).status_code == 200
print("token valid before restart")

subprocess.run(["sudo", "supervisorctl", "restart", "backend"], check=True)
for _ in range(30):
    time.sleep(2)
    try:
        if requests.get(f"{BASE_URL}/api/batches", headers=h, timeout=10).status_code in (200, 401, 403):
            break
    except Exception:
        pass
me = requests.get(f"{BASE_URL}/api/auth/me", headers=h, timeout=60)
print("after restart /api/auth/me ->", me.status_code)
if me.status_code != 200:
    print("FAIL: token invalidated by restart", me.text[:200])
    sys.exit(1)
print("PASS: JWT_SECRET persisted, token survives restart")
print(json.dumps({k: me.json().get(k) for k in ("email", "role", "status")}))
