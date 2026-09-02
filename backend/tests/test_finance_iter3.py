# Iteration 3: Finance / Laba Rugi (POST /api/finance/day, GET /api/finance/summary)
# Destructive work is done inside a throwaway batch (2026-05); BATCH-2026-09 (live user data) is only read.
import os
import re
from pathlib import Path

import pytest
import requests
from dotenv import dotenv_values

fe = dotenv_values("/app/frontend/.env")
base = os.environ.get("REACT_APP_BACKEND_URL") or fe.get("REACT_APP_BACKEND_URL")
if not base:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base.rstrip("/")
LIVE_BATCH = "BATCH-2026-08"


def _creds():
    c = Path("/app/memory/test_credentials.md").read_text(encoding="utf-8")
    e = re.search(r'(?im)^\s*[-*]?\s*(?:\*\*)?email(?:\*\*)?\s*:\s*`?([^`\s]+)', c)
    p = re.search(r'(?im)^\s*[-*]?\s*(?:\*\*)?password(?:\*\*)?\s*:\s*`?([^`\s]+)', c)
    if not e or not p:
        pytest.skip("credentials missing")
    return e.group(1), p.group(1)


@pytest.fixture(scope="session")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    email, password = _creds()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password})
    if r.status_code != 200:
        pytest.fail(f"login failed {r.status_code}: {r.text[:300]}")
    tok = r.json().get("access_token") or r.json().get("token")
    assert tok, f"no token in login response: {r.json().keys()}"
    s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


@pytest.fixture(scope="session")
def qa_batch(client):
    """Throwaway batch with generated transactions; deleted afterwards, live batch reactivated."""
    r = client.post(f"{BASE_URL}/api/batches/new", json={"month": "2026-05"})
    assert r.status_code == 200, r.text
    bid = r.json()["id"]
    g = client.post(f"{BASE_URL}/api/generator/run", json={
        "start_date": "2026-05-04", "end_date": "2026-05-05", "target_kg": 30000, "price_per_kg": 2500})
    assert g.status_code == 200, g.text
    yield bid
    client.delete(f"{BASE_URL}/api/batches/{bid}")
    client.post(f"{BASE_URL}/api/batches/{LIVE_BATCH}/activate")


def summary(client, batch, **params):
    q = "&".join(f"{k}={v}" for k, v in params.items())
    r = client.get(f"{BASE_URL}/api/finance/summary?batch_id={batch}" + (f"&{q}" if q else ""))
    assert r.status_code == 200, r.text
    return r.json()


class TestFinanceDay:
    def test_summary_before_grading(self, client, qa_batch):
        s = summary(client, qa_batch)
        assert len(s["days"]) == 2, s["days"]
        for d in s["days"]:
            assert d["configured"] is False
            assert d["freight_per_kg"] == 200
            assert d["total_angkut"] == d["netto_kg"] * 200
            assert d["total_modal"] == d["total_beli"] + d["total_angkut"]
            assert "untung_rugi" not in d
        assert s["totals"]["configured_days"] == 0
        assert s["totals"]["netto_kg"] == sum(d["netto_kg"] for d in s["days"])

    def test_tare_distribution_exact_and_bounded(self, client, qa_batch):
        s = summary(client, qa_batch)
        day = s["days"][0]["date"]
        tare = 1234
        r = client.post(f"{BASE_URL}/api/finance/day", json={
            "batch_id": qa_batch, "date": day, "total_tare_kg": tare,
            "sip_price_per_kg": 3500, "freight_per_kg": 250})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["total_tare_kg"] == tare
        assert body["distributed"] == s["days"][0]["tx_count"]

        s2 = summary(client, qa_batch)
        txs = [t for t in s2["transactions"] if t["date"] == day]
        assert len(txs) == body["distributed"]
        assert sum(t["tare_kg"] for t in txs) == tare, [t["tare_kg"] for t in txs]
        for t in txs:
            assert 0 <= t["tare_kg"] < t["netto_kg"]
            assert t["netto_jual"] == t["netto_kg"] - t["tare_kg"]
            assert t["harga_jual"] == t["netto_jual"] * 3500
            assert t["grading_pct"] == round(t["tare_kg"] / t["netto_kg"] * 100, 2)
        # other day untouched
        assert all(t.get("tare_kg") is None for t in s2["transactions"] if t["date"] != day)

    def test_day_row_formulas(self, client, qa_batch):
        s = summary(client, qa_batch)
        d = next(x for x in s["days"] if x["configured"])
        assert d["freight_per_kg"] == 250
        assert d["total_angkut"] == d["netto_kg"] * 250
        assert d["total_modal"] == d["total_beli"] + d["total_angkut"]
        assert d["grading_pct"] == round(d["total_tare_kg"] / d["netto_kg"] * 100, 2)
        assert d["netto_jual"] == d["netto_kg"] - d["total_tare_kg"]
        assert d["harga_jual"] == d["netto_jual"] * d["sip_price_per_kg"]
        assert d["pph22"] == round(d["harga_jual"] * 0.0025)
        assert d["untung_rugi"] == d["harga_jual"] - d["pph22"] - d["total_modal"]

    def test_resubmit_is_idempotent_overwrite(self, client, qa_batch):
        s = summary(client, qa_batch)
        day = next(x["date"] for x in s["days"] if x["configured"])
        r = client.post(f"{BASE_URL}/api/finance/day", json={
            "batch_id": qa_batch, "date": day, "total_tare_kg": 500,
            "sip_price_per_kg": 3600, "freight_per_kg": 200})
        assert r.status_code == 200, r.text
        s2 = summary(client, qa_batch)
        d = next(x for x in s2["days"] if x["date"] == day)
        assert d["total_tare_kg"] == 500
        assert d["sip_price_per_kg"] == 3600
        assert d["freight_per_kg"] == 200
        txs = [t for t in s2["transactions"] if t["date"] == day]
        assert sum(t["tare_kg"] for t in txs) == 500
        # only one finance_days doc per date -> configured_days must stay 1 for this batch
        assert sum(1 for x in s2["days"] if x["configured"]) == 1

    def test_totals_aggregate(self, client, qa_batch):
        s = summary(client, qa_batch)
        conf = [d for d in s["days"] if d["configured"]]
        t = s["totals"]
        assert t["total_days"] == len(s["days"])
        assert t["configured_days"] == len(conf)
        assert t["total_beli"] == sum(d["total_beli"] for d in s["days"])
        assert t["total_angkut"] == sum(d["total_angkut"] for d in s["days"])
        assert t["total_modal"] == sum(d["total_modal"] for d in s["days"])
        assert t["harga_jual"] == sum(d["harga_jual"] for d in conf)
        assert t["pph22"] == sum(d["pph22"] for d in conf)
        assert t["untung_rugi"] == sum(d["untung_rugi"] for d in conf)

    def test_date_filter(self, client, qa_batch):
        s = summary(client, qa_batch)
        first = s["days"][0]["date"]
        f = summary(client, qa_batch, start=first, end=first)
        assert [d["date"] for d in f["days"]] == [first]
        assert f["totals"]["netto_kg"] == s["days"][0]["netto_kg"]
        assert all(t["date"] == first for t in f["transactions"])

    def test_validation_no_transactions(self, client, qa_batch):
        r = client.post(f"{BASE_URL}/api/finance/day", json={
            "batch_id": qa_batch, "date": "2026-05-20", "total_tare_kg": 10,
            "sip_price_per_kg": 3500, "freight_per_kg": 200})
        assert r.status_code == 400, r.text
        assert "transaksi" in r.json()["detail"].lower()

    def test_validation_tare_ge_netto(self, client, qa_batch):
        s = summary(client, qa_batch)
        day, netto = s["days"][0]["date"], s["days"][0]["netto_kg"]
        r = client.post(f"{BASE_URL}/api/finance/day", json={
            "batch_id": qa_batch, "date": day, "total_tare_kg": netto,
            "sip_price_per_kg": 3500, "freight_per_kg": 200})
        assert r.status_code == 400, r.text

    def test_validation_bad_prices(self, client, qa_batch):
        s = summary(client, qa_batch)
        day = s["days"][0]["date"]
        for payload in ({"sip_price_per_kg": 0, "freight_per_kg": 200},
                        {"sip_price_per_kg": 3500, "freight_per_kg": -5}):
            r = client.post(f"{BASE_URL}/api/finance/day", json={
                "batch_id": qa_batch, "date": day, "total_tare_kg": 100, **payload})
            assert r.status_code == 400, (payload, r.status_code, r.text[:200])

    def test_zero_tare_allowed(self, client, qa_batch):
        s = summary(client, qa_batch)
        day = s["days"][1]["date"]
        r = client.post(f"{BASE_URL}/api/finance/day", json={
            "batch_id": qa_batch, "date": day, "total_tare_kg": 0,
            "sip_price_per_kg": 3500, "freight_per_kg": 200})
        assert r.status_code == 200, r.text
        s2 = summary(client, qa_batch)
        d = next(x for x in s2["days"] if x["date"] == day)
        assert d["total_tare_kg"] == 0 and d["grading_pct"] == 0.0
        assert d["netto_jual"] == d["netto_kg"]

    def test_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/finance/summary")
        assert r.status_code in (401, 403), r.status_code
        r2 = requests.post(f"{BASE_URL}/api/finance/day", json={
            "date": "2026-05-04", "total_tare_kg": 1, "sip_price_per_kg": 1, "freight_per_kg": 200})
        assert r2.status_code in (401, 403), r2.status_code


class TestLiveBatchReadOnly:
    """Non-destructive checks against the live user batch (must not be modified)."""

    def test_live_summary_consistent(self, client):
        s = summary(client, LIVE_BATCH)
        assert s["days"], "live batch has no days"
        for d in s["days"]:
            assert d["total_angkut"] == d["netto_kg"] * d["freight_per_kg"]
            assert d["total_modal"] == d["total_beli"] + d["total_angkut"]
            if d["configured"]:
                assert d["harga_jual"] == d["netto_jual"] * d["sip_price_per_kg"]
                assert d["pph22"] == round(d["harga_jual"] * 0.0025)
                assert d["untung_rugi"] == d["harga_jual"] - d["pph22"] - d["total_modal"]
                txs = [t for t in s["transactions"] if t["date"] == d["date"]]
                assert sum(t["tare_kg"] for t in txs) == d["total_tare_kg"]
        assert "_id" not in str(s)

    def test_analytics_summary_matches_finance(self, client):
        a = client.get(f"{BASE_URL}/api/analytics/summary?batch_id={LIVE_BATCH}")
        assert a.status_code == 200, a.text
        s = summary(client, LIVE_BATCH)
        assert a.json()["total_netto_kg"] == s["totals"]["netto_kg"]
        assert a.json()["total_spending"] == s["totals"]["total_beli"]

    def test_export_excel_downloads(self, client):
        r = client.get(f"{BASE_URL}/api/export/excel?batch_id={LIVE_BATCH}")
        assert r.status_code == 200, r.text[:200]
        assert "spreadsheet" in r.headers.get("content-type", "")
        assert len(r.content) > 3000


