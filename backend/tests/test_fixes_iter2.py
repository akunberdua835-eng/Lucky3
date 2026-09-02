"""Iteration-2 regression tests for FIX-1..FIX-6 (tx code counter, lockout reset, batch labels, CORS)."""
import re

import requests
from conftest import BASE_URL

DATE = "2026-10-20"


def _mk(client, batch, owner, arrival, exit_t, gross=1200):
    return client.post(f"{BASE_URL}/api/transactions", json={
        "batch_id": batch, "date": DATE, "arrival_time": arrival, "exit_time": exit_t,
        "owner_id": owner["id"], "owner_name": owner["name"], "vehicle_type": owner["vehicle_type"],
        "gross_kg": gross, "tare_kg": None, "price_per_kg": 3000, "note": "TEST_QA"}, timeout=60)


def _seq(code):
    m = re.match(r"^SJM-\d{6}-(\d{3,})$", code)
    assert m, f"unexpected code format: {code}"
    return int(m.group(1))


# FIX-1: atomic per-batch counter for transaction_code
class TestTxCodeCounter:
    def test_code_unique_after_delete_and_with_generator(self, admin_client, active_batch, owners_list):
        owner = next(o for o in owners_list if o["name"] == "Ita Sari")
        codes = []
        r1 = _mk(admin_client, active_batch, owner, "07:30:00", "07:55:00")
        r2 = _mk(admin_client, active_batch, owner, "10:30:00", "10:55:00")
        assert r1.status_code == 200 and r2.status_code == 200
        c1, c2 = r1.json()["transaction_code"], r2.json()["transaction_code"]
        assert _seq(c2) == _seq(c1) + 1
        codes += [c1, c2]

        # delete first tx, next insert must NOT reuse a code
        assert admin_client.delete(f"{BASE_URL}/api/transactions/{r1.json()['id']}", timeout=60).status_code == 200
        r3 = _mk(admin_client, active_batch, owner, "14:30:00", "14:55:00")
        assert r3.status_code == 200
        c3 = r3.json()["transaction_code"]
        assert c3 not in codes, f"duplicate code after delete: {c3}"
        assert _seq(c3) == _seq(c2) + 1
        codes.append(c3)

        # generator reserves a block from the same counter
        g = admin_client.post(f"{BASE_URL}/api/generator/run", json={
            "start_date": "2026-10-21", "end_date": "2026-10-21", "target_kg": 3000, "price_per_kg": 3000}, timeout=180)
        assert g.status_code == 200, g.text[:300]
        gen_rows = [t for t in admin_client.get(f"{BASE_URL}/api/transactions?batch_id={active_batch}", timeout=60).json()
                    if t["date"] == "2026-10-21"]
        assert gen_rows, "generator produced no rows"
        gen_seqs = sorted(_seq(t["transaction_code"]) for t in gen_rows)
        assert gen_seqs[0] > _seq(c3), f"generator reused codes: {gen_seqs} vs {c3}"
        assert gen_seqs == list(range(gen_seqs[0], gen_seqs[0] + len(gen_seqs))), gen_seqs

        # manual tx after generator continues the sequence
        r4 = _mk(admin_client, active_batch, owner, "15:30:00", "15:55:00")
        assert r4.status_code == 200
        assert _seq(r4.json()["transaction_code"]) == gen_seqs[-1] + 1

        # global uniqueness inside the batch
        all_codes = [t["transaction_code"] for t in
                     admin_client.get(f"{BASE_URL}/api/transactions?batch_id={active_batch}", timeout=60).json()]
        assert len(all_codes) == len(set(all_codes)), "duplicate transaction_code in batch"

        # cleanup
        admin_client.delete(f"{BASE_URL}/api/transactions/date/{DATE}?batch_id={active_batch}", timeout=60)
        admin_client.delete(f"{BASE_URL}/api/transactions/date/2026-10-21?batch_id={active_batch}", timeout=60)

    def test_edit_keeps_code(self, admin_client, active_batch, owners_list):
        owner = next(o for o in owners_list if o["name"] == "Epit")
        r = _mk(admin_client, active_batch, owner, "08:10:00", "08:40:00", gross=500)
        assert r.status_code == 200
        d = r.json()
        code = d["transaction_code"]
        d["gross_kg"] = 550
        d.pop("_id", None)
        r2 = admin_client.post(f"{BASE_URL}/api/transactions", json=d, timeout=60)
        assert r2.status_code == 200
        assert r2.json()["transaction_code"] == code
        assert r2.json()["netto_kg"] == 550
        admin_client.delete(f"{BASE_URL}/api/transactions/{d['id']}", timeout=60)


# FIX-2: lockout counter resets after a successful login
class TestLockoutReset:
    def test_attempts_reset_after_success(self, api_client, test_credentials):
        for _ in range(3):
            r = api_client.post(f"{BASE_URL}/api/auth/login",
                                json={"email": test_credentials["email"], "password": "wrong-pw"}, timeout=60)
            assert r.status_code == 401
        ok = api_client.post(f"{BASE_URL}/api/auth/login", json=test_credentials, timeout=60)
        assert ok.status_code == 200, ok.text[:200]
        # after reset we must be able to fail 5 more times before a lock
        codes = []
        for _ in range(4):
            codes.append(api_client.post(f"{BASE_URL}/api/auth/login",
                                         json={"email": test_credentials["email"], "password": "wrong-pw"},
                                         timeout=60).status_code)
        assert codes == [401] * 4, f"counter not reset after successful login: {codes}"
        # clear the counter again so the admin account stays usable
        assert api_client.post(f"{BASE_URL}/api/auth/login", json=test_credentials, timeout=60).status_code == 200


# FIX-6: unique batch labels within the same month
class TestBatchLabels:
    def test_new_batch_label_unique(self, admin_client):
        before = admin_client.get(f"{BASE_URL}/api/batches", timeout=60).json()
        original_active = next(b for b in before if b["active"])
        created = []
        try:
            for _ in range(2):
                r = admin_client.post(f"{BASE_URL}/api/batches/new", timeout=60)
                assert r.status_code == 200
                created.append(r.json())
            after = admin_client.get(f"{BASE_URL}/api/batches", timeout=60).json()
            labels = [b["label"] for b in after]
            assert len(labels) == len(set(labels)), f"duplicate batch labels: {labels}"
            assert any("Periode" in l for l in labels), labels
            assert all("_id" not in b for b in after)
        finally:
            # restore original active batch state (extra batches removed by qa_cleanup)
            import pymongo, os
            cl = pymongo.MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
            dbn = cl[os.environ.get("DB_NAME", "test_database")]
            for b in created:
                dbn.batches.delete_one({"id": b["id"]})
                dbn.counters.delete_one({"_id": f"tx-{b['id']}"})
            dbn.batches.update_one({"id": original_active["id"]},
                                   {"$set": {"active": True}, "$unset": {"archived_at": ""}})
            cl.close()


# FIX-4: explicit CORS origins still allow the frontend.
# NOTE: the k8s ingress rewrites CORS headers to '*' on the public URL, so the app-level
# configuration is asserted against the internal app port; the public URL only gets a
# "request succeeds with Origin header" smoke check.
APP_ORIGIN = "http://localhost:8001"


class TestCors:
    def test_app_preflight_echoes_explicit_origin(self):
        origin = BASE_URL
        r = requests.options(f"{APP_ORIGIN}/api/auth/login", headers={
            "Origin": origin, "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type"}, timeout=30)
        assert r.status_code in (200, 204), r.status_code
        assert r.headers.get("access-control-allow-origin") == origin, dict(r.headers)
        assert r.headers.get("access-control-allow-credentials") == "true", dict(r.headers)

    def test_app_rejects_unknown_origin(self):
        r = requests.options(f"{APP_ORIGIN}/api/auth/login", headers={
            "Origin": "https://evil.example.com", "Access-Control-Request-Method": "POST"}, timeout=30)
        assert r.headers.get("access-control-allow-origin") != "https://evil.example.com", dict(r.headers)

    def test_public_request_with_origin_succeeds(self, test_credentials):
        r = requests.post(f"{BASE_URL}/api/auth/login", json=test_credentials,
                          headers={"Origin": BASE_URL}, timeout=60)
        assert r.status_code == 200
        assert r.headers.get("access-control-allow-origin") in (BASE_URL, "*")
