import os
import re
from pathlib import Path

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
_base = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not _base:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = _base.rstrip("/")


@pytest.fixture(scope="session")
def test_credentials():
    p = Path("/app/memory/test_credentials.md")
    if not p.exists():
        pytest.skip("missing test_credentials.md")
    c = p.read_text(encoding="utf-8")
    e = re.search(r'(?im)^\s*(?:[-*]\s*)?(?:\*\*)?email(?:\*\*)?\s*:\s*`?([^`\s]+)', c)
    pw = re.search(r'(?im)^\s*(?:[-*]\s*)?(?:\*\*)?password(?:\*\*)?\s*:\s*`?([^`\s]+)', c)
    if not e or not pw:
        pytest.skip("credentials not parseable")
    return {"email": e.group(1), "password": pw.group(1)}


@pytest.fixture(scope="class")
def api_client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="class")
def admin_client(test_credentials):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/login", json=test_credentials, timeout=60)
    if r.status_code != 200:
        pytest.fail(f"admin login failed {r.status_code}: {r.text[:300]}")
    tok = r.json().get("token")
    if not tok:
        pytest.fail("no token in login response")
    s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


@pytest.fixture(scope="class")
def active_batch(admin_client):
    r = admin_client.get(f"{BASE_URL}/api/batches", timeout=60)
    assert r.status_code == 200
    act = [b for b in r.json() if b.get("active")]
    assert act, "no active batch"
    return act[0]["id"]


@pytest.fixture(scope="class")
def owners_list(admin_client):
    r = admin_client.get(f"{BASE_URL}/api/owners", timeout=60)
    assert r.status_code == 200
    return r.json()
