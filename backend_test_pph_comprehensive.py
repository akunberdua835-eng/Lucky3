#!/usr/bin/env python3
"""Comprehensive PPh 22 Feature Testing + Regression Tests for PT SJM Sawit"""
import requests
import sys
import json
from datetime import datetime

BASE_URL = "https://commit-history-web.preview.emergentagent.com"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

class TestRunner:
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.token = None
        self.batch_id = None
        self.test_date = "2026-09-15"
        self.failures = []

    def log(self, msg, color=Colors.RESET):
        print(f"{color}{msg}{Colors.RESET}")

    def test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{BASE_URL}{endpoint}"
        h = {'Content-Type': 'application/json'}
        if self.token:
            h['Authorization'] = f'Bearer {self.token}'
        if headers:
            h.update(headers)

        self.tests_run += 1
        self.log(f"\n[{self.tests_run}] Testing: {name}", Colors.BLUE)
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=h, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=h, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=h, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=h, timeout=30)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                self.log(f"✅ PASSED - Status: {response.status_code}", Colors.GREEN)
                try:
                    return True, response.json()
                except:
                    return True, {}
            else:
                self.tests_failed += 1
                self.log(f"❌ FAILED - Expected {expected_status}, got {response.status_code}", Colors.RED)
                self.log(f"Response: {response.text[:300]}", Colors.RED)
                self.failures.append(f"{name}: Expected {expected_status}, got {response.status_code}")
                return False, {}

        except Exception as e:
            self.tests_failed += 1
            self.log(f"❌ FAILED - Error: {str(e)}", Colors.RED)
            self.failures.append(f"{name}: {str(e)}")
            return False, {}

    def run_all_tests(self):
        self.log("\n" + "="*80, Colors.YELLOW)
        self.log("PT SJM SAWIT - COMPREHENSIVE PPH 22 + REGRESSION TESTING", Colors.YELLOW)
        self.log("="*80 + "\n", Colors.YELLOW)

        # 1. Health Check (New Feature)
        self.log("\n### 1. HEALTH ENDPOINT (NEW FEATURE) ###", Colors.YELLOW)
        success, data = self.test("Health check without auth", "GET", "/api/", 200)
        if success:
            assert data.get('status') == 'ok', "Health status should be ok"
            assert data.get('database') == 'connected', "Database should be connected"
            self.log(f"Health check response: {json.dumps(data, indent=2)}", Colors.GREEN)

        # 2. Authentication Tests
        self.log("\n### 2. AUTHENTICATION TESTS ###", Colors.YELLOW)
        
        # Test admin utama login
        success, data = self.test(
            "Login admin utama",
            "POST",
            "/api/auth/login",
            200,
            {"email": "yumaclovstar@gmail.com", "password": "178910"}
        )
        if success:
            self.token = data.get('token')
            self.log(f"Token obtained: {self.token[:20]}...", Colors.GREEN)
        else:
            self.log("CRITICAL: Cannot proceed without admin token", Colors.RED)
            return

        # Test admin cadangan login
        success, data = self.test(
            "Login admin cadangan",
            "POST",
            "/api/auth/login",
            200,
            {"email": "admin@ptsjm.co.id", "password": "AdminSJM2026!"}
        )
        if success:
            self.log("Admin cadangan login successful", Colors.GREEN)

        # Get current user
        success, data = self.test("Get current user (/api/auth/me)", "GET", "/api/auth/me", 200)
        if success:
            assert data.get('role') == 'admin', "User should be admin"
            self.log(f"Current user: {data.get('name')} ({data.get('email')})", Colors.GREEN)

        # 3. Get Active Batch
        self.log("\n### 3. BATCH MANAGEMENT ###", Colors.YELLOW)
        success, data = self.test("Get batches", "GET", "/api/batches", 200)
        if success:
            batches = [b for b in data if b.get('active')]
            if batches:
                self.batch_id = batches[0]['id']
                self.log(f"Active batch: {self.batch_id}", Colors.GREEN)

        # 4. Generate Test Data
        self.log("\n### 4. GENERATE TEST DATA ###", Colors.YELLOW)
        success, data = self.test(
            "Generate transactions",
            "POST",
            "/api/generator/run",
            200,
            {
                "start_date": self.test_date,
                "end_date": self.test_date,
                "target_kg": 5000,
                "price_per_kg": 2500
            }
        )
        if success:
            self.log(f"Generated {data.get('generated_count')} transactions", Colors.GREEN)

        # 5. Grading (Required for PPh testing)
        self.log("\n### 5. GRADING HARIAN ###", Colors.YELLOW)
        success, data = self.test(
            "Grade day for PPh testing",
            "POST",
            "/api/finance/day",
            200,
            {
                "batch_id": self.batch_id,
                "date": self.test_date,
                "total_tare_kg": 200,
                "sip_price_per_kg": 3500,
                "freight_per_kg": 200
            }
        )
        if success:
            self.log(f"Grading successful for {self.test_date}", Colors.GREEN)

        # 6. PPH 22 FEATURE TESTS
        self.log("\n### 6. PPH 22 FEATURE TESTS ###", Colors.YELLOW)

        # 6.1 Get default PPh rate
        success, data = self.test("GET /api/settings/pph - Get default rate", "GET", "/api/settings/pph", 200)
        if success:
            assert data.get('rate_pct') == 0.25, f"Default rate should be 0.25, got {data.get('rate_pct')}"
            assert data.get('system_default') == 0.25, "System default should be 0.25"
            self.log(f"Default PPh rate: {data.get('rate_pct')}%", Colors.GREEN)

        # 6.2 Change default PPh rate (admin only)
        success, data = self.test(
            "PUT /api/settings/pph - Change default rate to 0.5%",
            "PUT",
            "/api/settings/pph",
            200,
            {"rate_pct": 0.5}
        )
        if success:
            self.log("Default rate changed to 0.5%", Colors.GREEN)

        # Verify change in finance summary
        success, data = self.test(
            "Verify default rate change affects auto mode",
            "GET",
            f"/api/finance/summary?batch_id={self.batch_id}",
            200
        )
        if success:
            day = next((d for d in data['days'] if d['date'] == self.test_date), None)
            if day:
                assert day.get('pph_rate_pct') == 0.5, f"PPh rate should be 0.5, got {day.get('pph_rate_pct')}"
                self.log(f"PPh rate updated to {day.get('pph_rate_pct')}% in finance summary", Colors.GREEN)

        # Reset to default
        self.test("Reset default rate to 0.25%", "PUT", "/api/settings/pph", 200, {"rate_pct": 0.25})

        # 6.3 Set custom rate per day (auto mode)
        success, data = self.test(
            "POST /api/finance/pph - Set custom rate 1.5% (auto mode)",
            "POST",
            "/api/finance/pph",
            200,
            {
                "batch_id": self.batch_id,
                "date": self.test_date,
                "mode": "auto",
                "rate_pct": 1.5,
                "note": "Tarif khusus untuk tanggal ini"
            }
        )
        if success:
            assert data.get('pph_mode') == 'auto', "Mode should be auto"
            assert data.get('pph_rate_pct') == 1.5, "Rate should be 1.5"
            assert data.get('pph_custom') == True, "Should be marked as custom"
            self.log(f"Custom rate set: {data.get('pph_rate_pct')}%, PPh22: Rp {data.get('pph22'):,}", Colors.GREEN)

        # 6.4 Set manual amount (manual mode)
        success, data = self.test(
            "POST /api/finance/pph - Set manual amount (manual mode)",
            "POST",
            "/api/finance/pph",
            200,
            {
                "batch_id": self.batch_id,
                "date": self.test_date,
                "mode": "manual",
                "amount": 123456,
                "note": "Bukti potong dari PT SIP"
            }
        )
        if success:
            assert data.get('pph_mode') == 'manual', "Mode should be manual"
            assert data.get('pph22') == 123456, "PPh22 should be 123456"
            effective_pct = data.get('pph_rate_pct')
            self.log(f"Manual amount set: Rp {data.get('pph22'):,} (efektif {effective_pct}%)", Colors.GREEN)

        # 6.5 Validation Tests
        self.log("\n### 6.5 PPH VALIDATION TESTS ###", Colors.YELLOW)

        # Get harga_jual for validation tests
        success, summary_data = self.test(
            "Get finance summary for validation",
            "GET",
            f"/api/finance/summary?batch_id={self.batch_id}",
            200
        )
        harga_jual = 0
        if success:
            day = next((d for d in summary_data['days'] if d['date'] == self.test_date), None)
            if day:
                harga_jual = day.get('harga_jual', 0)

        # Test: amount > harga_jual
        self.test(
            "Validation: amount > harga_jual should fail",
            "POST",
            "/api/finance/pph",
            400,
            {
                "batch_id": self.batch_id,
                "date": self.test_date,
                "mode": "manual",
                "amount": harga_jual + 1000 if harga_jual else 999999999
            }
        )

        # Test: negative amount
        self.test(
            "Validation: negative amount should fail",
            "POST",
            "/api/finance/pph",
            400,
            {
                "batch_id": self.batch_id,
                "date": self.test_date,
                "mode": "manual",
                "amount": -1
            }
        )

        # Test: rate > 100
        self.test(
            "Validation: rate_pct > 100 should fail",
            "POST",
            "/api/finance/pph",
            400,
            {
                "batch_id": self.batch_id,
                "date": self.test_date,
                "mode": "auto",
                "rate_pct": 120
            }
        )

        # Test: invalid mode
        self.test(
            "Validation: invalid mode should fail",
            "POST",
            "/api/finance/pph",
            400,
            {
                "batch_id": self.batch_id,
                "date": self.test_date,
                "mode": "invalid_mode"
            }
        )

        # Test: ungraded date
        self.test(
            "Validation: ungraded date should fail",
            "POST",
            "/api/finance/pph",
            400,
            {
                "batch_id": self.batch_id,
                "date": "2030-01-01",
                "mode": "auto"
            }
        )

        # Test: invalid default rate (negative)
        self.test(
            "Validation: negative default rate should fail",
            "PUT",
            "/api/settings/pph",
            400,
            {"rate_pct": -1}
        )

        # Test: invalid default rate (> 100)
        self.test(
            "Validation: rate > 100 should fail",
            "PUT",
            "/api/settings/pph",
            400,
            {"rate_pct": 101}
        )

        # 6.6 Reset PPh to default
        success, data = self.test(
            "DELETE /api/finance/pph/{date} - Reset to default",
            "DELETE",
            f"/api/finance/pph/{self.test_date}?batch_id={self.batch_id}",
            200
        )
        if success:
            self.log("PPh reset to default successfully", Colors.GREEN)

        # Verify reset
        success, data = self.test(
            "Verify PPh reset to default",
            "GET",
            f"/api/finance/summary?batch_id={self.batch_id}",
            200
        )
        if success:
            day = next((d for d in data['days'] if d['date'] == self.test_date), None)
            if day:
                assert day.get('pph_custom') == False, "Should not be custom after reset"
                assert day.get('pph_mode') == 'auto', "Should be auto mode after reset"
                self.log("PPh successfully reset to default", Colors.GREEN)

        # Test: delete non-existent date
        self.test(
            "DELETE non-existent date should return 404",
            "DELETE",
            f"/api/finance/pph/2030-01-01?batch_id={self.batch_id}",
            404
        )

        # 6.7 Non-admin cannot change default rate
        self.log("\n### 6.7 AUTHORIZATION TESTS ###", Colors.YELLOW)
        self.test(
            "Anonymous user cannot change default rate",
            "PUT",
            "/api/settings/pph",
            401,
            {"rate_pct": 5},
            headers={"Authorization": ""}
        )

        # 7. REGRESSION TESTS
        self.log("\n### 7. REGRESSION TESTS ###", Colors.YELLOW)

        # 7.1 Transactions
        success, data = self.test("Get transactions", "GET", f"/api/transactions?batch_id={self.batch_id}", 200)
        if success:
            self.log(f"Transactions count: {len(data)}", Colors.GREEN)

        # 7.2 Owners
        success, data = self.test("Get owners", "GET", "/api/owners", 200)
        if success:
            self.log(f"Owners count: {len(data)}", Colors.GREEN)

        # 7.3 Prices
        success, data = self.test("Get prices", "GET", "/api/prices", 200)
        if success:
            self.log(f"Prices retrieved successfully", Colors.GREEN)

        # 7.4 Analytics
        success, data = self.test("Get analytics summary", "GET", f"/api/analytics/summary?batch_id={self.batch_id}", 200)
        if success:
            self.log(f"Total transactions: {data.get('total_transactions')}", Colors.GREEN)

        # 7.5 Excel Exports
        self.log("\n### 7.5 EXCEL EXPORT TESTS ###", Colors.YELLOW)
        
        # Test finance excel export (should have PPh columns)
        success, _ = self.test(
            "Export finance excel (with PPh columns)",
            "GET",
            f"/api/export/finance-excel?batch_id={self.batch_id}",
            200
        )

        success, _ = self.test("Export complete excel", "GET", f"/api/export/excel?batch_id={self.batch_id}", 200)
        success, _ = self.test("Export owners excel", "GET", f"/api/export/owners-excel?batch_id={self.batch_id}", 200)
        success, _ = self.test("Export daily excel", "GET", f"/api/export/daily-excel?batch_id={self.batch_id}", 200)
        success, _ = self.test("Export prices excel", "GET", "/api/export/prices-excel", 200)

        # Print Summary
        self.print_summary()

    def print_summary(self):
        self.log("\n" + "="*80, Colors.YELLOW)
        self.log("TEST SUMMARY", Colors.YELLOW)
        self.log("="*80, Colors.YELLOW)
        self.log(f"Total Tests: {self.tests_run}", Colors.BLUE)
        self.log(f"Passed: {self.tests_passed}", Colors.GREEN)
        self.log(f"Failed: {self.tests_failed}", Colors.RED)
        self.log(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%", Colors.BLUE)
        
        if self.failures:
            self.log("\n### FAILED TESTS ###", Colors.RED)
            for i, failure in enumerate(self.failures, 1):
                self.log(f"{i}. {failure}", Colors.RED)
        
        self.log("\n" + "="*80 + "\n", Colors.YELLOW)

if __name__ == "__main__":
    runner = TestRunner()
    runner.run_all_tests()
    sys.exit(0 if runner.tests_failed == 0 else 1)
