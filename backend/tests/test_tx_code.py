"""Regression: transaction_code uniqueness after deletions (count-based numbering)."""
import pytest
from conftest import BASE_URL

DATE = "2026-10-15"


class TestTransactionCodeUniqueness:
    def _mk(self, admin_client, batch, owner, arrival, exit_t, gross):
        return admin_client.post(f"{BASE_URL}/api/transactions", json={
            "batch_id": batch, "date": DATE, "arrival_time": arrival, "exit_time": exit_t,
            "owner_id": owner["id"], "owner_name": owner["name"], "vehicle_type": owner["vehicle_type"],
            "gross_kg": gross, "tare_kg": None, "price_per_kg": 3000, "note": "TEST_QA"}, timeout=60)

    @pytest.fixture(scope="class", autouse=True)
    def cleanup(self, admin_client, active_batch):
        yield
        admin_client.delete(f"{BASE_URL}/api/transactions/date/{DATE}?batch_id={active_batch}", timeout=60)

    def test_code_not_reused_after_delete(self, admin_client, active_batch, owners_list):
        owner = next(o for o in owners_list if o["name"] == "Ita Sari")
        r1 = self._mk(admin_client, active_batch, owner, "07:30:00", "07:55:00", 1200)
        r2 = self._mk(admin_client, active_batch, owner, "10:30:00", "10:55:00", 1200)
        assert r1.status_code == 200 and r2.status_code == 200
        c1, c2 = r1.json()["transaction_code"], r2.json()["transaction_code"]
        assert c1 != c2
        # delete the first one, then create a new transaction
        assert admin_client.delete(f"{BASE_URL}/api/transactions/{r1.json()['id']}", timeout=60).status_code == 200
        r3 = self._mk(admin_client, active_batch, owner, "14:30:00", "14:55:00", 1200)
        assert r3.status_code == 200
        c3 = r3.json()["transaction_code"]
        assert c3 != c2, f"duplicate transaction_code generated after delete: {c2} == {c3}"
