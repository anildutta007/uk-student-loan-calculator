"""
test_loan_calculator.py - Test suite for England & Wales Student Loan Engine
"""

import unittest
from engine import (
    calculate_take_home_pay,
    calculate_in_study_loan_balance,
    calculate_interest_rate_post_study,
    simulate_loan_lifetime,
    calculate_market_investment_growth,
    evaluate_parental_contribution,
    PLAN_CONFIGS,
)

class TestUKStudentLoanEngine(unittest.TestCase):

    def test_plan_configs(self):
        self.assertEqual(PLAN_CONFIGS["plan_2"]["repayment_threshold"], 29385.0)
        self.assertEqual(PLAN_CONFIGS["plan_2"]["write_off_years"], 30)
        self.assertEqual(PLAN_CONFIGS["plan_5"]["repayment_threshold"], 25000.0)
        self.assertEqual(PLAN_CONFIGS["plan_5"]["write_off_years"], 40)
        self.assertEqual(PLAN_CONFIGS["plan_1"]["repayment_threshold"], 26900.0)

    def test_take_home_pay_calculation(self):
        # Salary £35,000 with Plan 2 (£29,385 threshold)
        annual_sl = (35000 - 29385) * 0.09
        res = calculate_take_home_pay(35000, student_loan_annual=annual_sl)
        
        self.assertEqual(res["annual_gross"], 35000.0)
        self.assertAlmostEqual(res["monthly_gross"], 35000.0 / 12, places=2)
        self.assertGreater(res["annual_tax"], 0)
        self.assertGreater(res["annual_ni"], 0)
        self.assertAlmostEqual(res["annual_student_loan"], annual_sl, places=2)
        # Net pay must be Gross - Tax - NI - Student Loan
        expected_net = 35000.0 - res["annual_tax"] - res["annual_ni"] - res["annual_student_loan"]
        self.assertAlmostEqual(res["annual_net"], expected_net, places=2)

    def test_in_study_loan_accumulation(self):
        # 3 year course, £9250 tuition, £10227 maintenance = £19477/yr
        res_no_parent = calculate_in_study_loan_balance(
            course_length_years=3,
            tuition_per_year=9250.0,
            maintenance_per_year=10227.0,
            parent_annual_contribution=0.0,
            rpi=0.03,
            plan_type="plan_5"
        )
        self.assertEqual(res_no_parent["total_borrowed"], 19477.0 * 3)
        self.assertGreater(res_no_parent["graduation_balance"], res_no_parent["total_borrowed"])

        # With parent paying full tuition £9250/yr
        res_with_parent = calculate_in_study_loan_balance(
            course_length_years=3,
            tuition_per_year=9250.0,
            maintenance_per_year=10227.0,
            parent_annual_contribution=9250.0,
            rpi=0.03,
            plan_type="plan_5"
        )
        self.assertEqual(res_with_parent["total_borrowed"], 10227.0 * 3)
        self.assertLess(res_with_parent["graduation_balance"], res_no_parent["graduation_balance"])

    def test_interest_rate_post_study_sliding_scale(self):
        # Plan 5 is always RPI
        self.assertAlmostEqual(calculate_interest_rate_post_study("plan_5", 30000, 0.03), 0.03)
        self.assertAlmostEqual(calculate_interest_rate_post_study("plan_5", 80000, 0.03), 0.03)

        # Plan 2 below lower threshold (£29,385) -> RPI
        self.assertAlmostEqual(calculate_interest_rate_post_study("plan_2", 25000, 0.03), 0.03)
        # Plan 2 above upper threshold (£52,884) -> RPI + 3% (capped at 6%)
        self.assertAlmostEqual(calculate_interest_rate_post_study("plan_2", 60000, 0.03), 0.06)
        # Plan 2 midpoint -> RPI + 1.5%
        mid_salary = (29385.0 + 52884.0) / 2.0
        self.assertAlmostEqual(calculate_interest_rate_post_study("plan_2", mid_salary, 0.03), 0.045)

    def test_market_compound_investment_growth(self):
        # Initial lump sum £10,000 at 3%, 4%, 5%
        growth = calculate_market_investment_growth(
            annual_contributions=[0.0] * 30,
            lump_sum_initial=10000.0,
            rates=[0.03, 0.04, 0.05],
            total_years=30
        )
        self.assertIn("3%", growth)
        self.assertIn("4%", growth)
        self.assertIn("5%", growth)
        # 10,000 * (1.05^10) ~ 16,288.95
        self.assertAlmostEqual(growth["5%"]["year_10"], 16288.95, delta=1.0)
        # 5% pot must be greater than 4% pot which is greater than 3% pot
        self.assertGreater(growth["5%"]["final_pot"], growth["4%"]["final_pot"])
        self.assertGreater(growth["4%"]["final_pot"], growth["3%"]["final_pot"])

    def test_parent_evaluation_graduate_tax_trap(self):
        # Low to median earner: starts at £28,000 with 2% growth on Plan 2
        # Starts with £55,000 debt. Will NEVER pay off £55,000 debt before year 30!
        res = evaluate_parental_contribution(
            mode="graduated",
            plan_type="plan_2",
            starting_salary=28000.0,
            salary_growth_rate=0.02,
            existing_balance=55000.0,
            contribution_type="lump_sum",
            parent_lump_sum_amount=20000.0,
        )
        self.assertEqual(res["verdict"]["type"], "tax_trap")
        self.assertIn("⚠️ High Risk", res["verdict"]["title"])
        # Net family gain is negative because parent gave £20k to reduce debt that gets written off anyway!
        self.assertLess(res["comparison_metrics"]["net_family_financial_gain"], 0)

    def test_parent_evaluation_high_earner(self):
        # High earner: starts at £65,000 with 5% growth
        # Will pay off loan before write off!
        res = evaluate_parental_contribution(
            mode="graduated",
            plan_type="plan_2",
            starting_salary=65000.0,
            salary_growth_rate=0.05,
            existing_balance=40000.0,
            contribution_type="lump_sum",
            parent_lump_sum_amount=20000.0,
        )
        self.assertEqual(res["verdict"]["type"], "high_earner_effective")
        self.assertTrue(res["base_scenario"]["is_paid_off"])
        self.assertTrue(res["contribution_scenario"]["is_paid_off"])
        self.assertGreater(res["comparison_metrics"]["interest_saved"], 0)
        self.assertGreaterEqual(res["comparison_metrics"]["years_cleared_earlier"], 1)

if __name__ == "__main__":
    unittest.main()
