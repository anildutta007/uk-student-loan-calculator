"""
test_api_endpoints.py - Integration tests for the FastAPI backend
"""

import unittest
from starlette.testclient import TestClient
from server import app

class TestServerAPI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_get_plans(self):
        resp = self.client.get("/api/plans")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("undergrad_plans", data)
        self.assertIn("plan_5", data["undergrad_plans"])
        self.assertIn("plan_2", data["undergrad_plans"])

    def test_quick_payslip(self):
        payload = {
            "salary": 35000.0,
            "plan_type": "plan_5",
            "has_postgrad": False
        }
        resp = self.client.post("/api/quick-payslip", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["annual_gross"], 35000.0)
        # Plan 5 threshold is £25,000. (35000 - 25000) * 0.09 = £900/year
        self.assertAlmostEqual(data["annual_student_loan"], 900.0, places=1)
        self.assertAlmostEqual(data["monthly_student_loan"], 75.0, places=1)

    def test_calculate_student(self):
        payload = {
            "mode": "studying",
            "plan_type": "plan_5",
            "starting_salary": 32000.0,
            "salary_growth_rate": 0.035,
            "rpi": 0.032,
            "course_length_years": 3,
            "tuition_per_year": 9250.0,
            "maintenance_per_year": 10227.0,
            "existing_balance": 0.0,
            "has_postgrad": False,
            "postgrad_balance": 0.0
        }
        resp = self.client.post("/api/calculate-student", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("simulation", data)
        self.assertIn("initial_payslip", data)
        self.assertEqual(len(data["simulation"]["schedule"]), 40)  # Plan 5 has 40 years

    def test_evaluate_parent_graduate_tax_trap(self):
        payload = {
            "mode": "studying",
            "plan_type": "plan_2",
            "starting_salary": 29000.0,
            "salary_growth_rate": 0.02,
            "rpi": 0.032,
            "course_length_years": 3,
            "tuition_per_year": 9250.0,
            "maintenance_per_year": 10227.0,
            "existing_balance": 0.0,
            "contribution_type": "annual_fee",
            "parent_annual_amount": 9250.0,
            "parent_lump_sum_amount": 25000.0,
            "market_rates": [0.03, 0.04, 0.05],
            "custom_market_rate": 0.06,
            "has_postgrad": False,
            "postgrad_balance": 0.0
        }
        resp = self.client.post("/api/evaluate-parent", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["total_parent_contribution"], 27750.0)
        self.assertIn("market_investment_growth", data)
        self.assertIn("3%", data["market_investment_growth"])
        self.assertIn("4%", data["market_investment_growth"])
        self.assertIn("5%", data["market_investment_growth"])
        self.assertIn("6%", data["market_investment_growth"])
        self.assertEqual(data["verdict"]["type"], "tax_trap")

    def test_static_files(self):
        resp_index = self.client.get("/")
        self.assertEqual(resp_index.status_code, 200)
        resp_css = self.client.get("/styles.css")
        self.assertEqual(resp_css.status_code, 200)
        resp_js = self.client.get("/app.js")
        self.assertEqual(resp_js.status_code, 200)

if __name__ == "__main__":
    unittest.main()
