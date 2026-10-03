"""
engine.py - Core calculation engine for UK Student Loans (England & Wales)
Includes:
- Plan 1, Plan 2, Plan 5, and Postgraduate loans
- In-study interest accrual & graduate balances
- Salary growth projections & PAYE payslip deductions (Tax, NI, Student Loan)
- 30-year (Plan 2) and 40-year (Plan 5) lifetime simulations
- Parental contribution impact (interest saved, years reduced)
- Market investment opportunity cost comparisons (3%, 4%, 5% compound growth)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

# --- Statutory UK Student Loan Parameters ---
PLAN_CONFIGS = {
    "plan_5": {
        "name": "Plan 5 (England: courses started on or after 1 August 2023)",
        "country": "England",
        "description": "Started undergraduate course, PGCE, or Advanced Learner Loan on or after 1 August 2023 (Student Finance England)",
        "repayment_threshold": 25000.0,
        "monthly_threshold": 2083.33,
        "weekly_threshold": 480.77,
        "repayment_rate": 0.09,
        "write_off_years": 40,
        "study_interest_formula": "rpi",  # flat RPI, 0% real rate
        "post_study_interest_formula": "rpi",  # flat RPI
        "default_rpi": 0.041,  # 4.1% current statutory rate published on GOV.UK
    },
    "plan_2": {
        "name": "Plan 2 (England: 1 Sept 2012 – 31 July 2023 | Wales: 1 Sept 2012 onwards)",
        "country": "England & Wales",
        "description": "Started university between 1 September 2012 and 31 July 2023 (England) or 1 September 2012 onwards (Wales)",
        "repayment_threshold": 29385.0,
        "monthly_threshold": 2448.75,
        "weekly_threshold": 565.10,
        "upper_threshold": 52884.0,
        "repayment_rate": 0.09,
        "write_off_years": 30,
        "study_interest_formula": "rpi_plus_3_capped",  # RPI + 3% capped at 6.0%
        "post_study_interest_formula": "plan_2_sliding",
        "default_rpi": 0.041,
        "cap_rate": 0.060,  # 6.0% prevailing market rate cap
    },
    "plan_1": {
        "name": "Plan 1 (England & Wales: pre-1 Sept 2012 | Northern Ireland)",
        "country": "England, Wales & Northern Ireland",
        "description": "Started university before 1 September 2012 (England/Wales) or any time (Northern Ireland)",
        "repayment_threshold": 26900.0,
        "monthly_threshold": 2241.67,
        "weekly_threshold": 517.31,
        "repayment_rate": 0.09,
        "write_off_years": 25,
        "study_interest_formula": "plan_1_rate",
        "post_study_interest_formula": "plan_1_rate",
        "default_rpi": 0.041,
    },
}

POSTGRAD_CONFIG = {
    "name": "Postgraduate Loan (Master's / Doctoral)",
    "repayment_threshold": 21000.0,
    "monthly_threshold": 1750.00,
    "weekly_threshold": 403.85,
    "repayment_rate": 0.06,
    "write_off_years": 30,
    "interest_formula": "rpi_plus_3_capped",
    "default_rate": 0.060,  # 6.0% currently published on GOV.UK
}

# --- Tax & NI 2024-2026 Brackets (England & Wales) ---
def calculate_take_home_pay(annual_salary: float, student_loan_annual: float = 0.0) -> Dict[str, float]:
    """Calculates UK Income Tax, National Insurance, Student Loan, and Net Take-Home Pay."""
    # Personal allowance with tapering above £100k
    personal_allowance = 12570.0
    if annual_salary > 100000.0:
        reduction = (annual_salary - 100000.0) / 2.0
        personal_allowance = max(0.0, personal_allowance - reduction)

    # Income Tax
    taxable_income = max(0.0, annual_salary - personal_allowance)
    income_tax = 0.0

    basic_band = 50270.0 - 12570.0  # £37,700
    higher_band = 125140.0 - 50270.0  # £74,870

    if taxable_income > 0:
        basic_taxable = min(taxable_income, basic_band)
        income_tax += basic_taxable * 0.20

        if taxable_income > basic_band:
            higher_taxable = min(taxable_income - basic_band, higher_band)
            income_tax += higher_taxable * 0.40

            if taxable_income > (basic_band + higher_band):
                additional_taxable = taxable_income - (basic_band + higher_band)
                income_tax += additional_taxable * 0.45

    # National Insurance (Class 1 Employee)
    ni = 0.0
    ni_primary_threshold = 12570.0
    ni_uel = 50270.0

    if annual_salary > ni_primary_threshold:
        main_ni_income = min(annual_salary, ni_uel) - ni_primary_threshold
        ni += main_ni_income * 0.08  # Current 8% employee NI rate

        if annual_salary > ni_uel:
            upper_ni_income = annual_salary - ni_uel
            ni += upper_ni_income * 0.02

    net_annual = max(0.0, annual_salary - income_tax - ni - student_loan_annual)

    # Marginal rate at this salary
    marginal_tax = 0.20 if annual_salary <= 50270 else (0.40 if annual_salary <= 125140 else 0.45)
    if 100000 < annual_salary <= 125140:
        marginal_tax = 0.60  # Personal allowance taper
    marginal_ni = 0.08 if annual_salary <= 50270 else 0.02
    marginal_sl = 0.09  # standard undergrad
    marginal_total = marginal_tax + marginal_ni + marginal_sl

    return {
        "annual_gross": round(annual_salary, 2),
        "monthly_gross": round(annual_salary / 12.0, 2),
        "annual_tax": round(income_tax, 2),
        "monthly_tax": round(income_tax / 12.0, 2),
        "annual_ni": round(ni, 2),
        "monthly_ni": round(ni / 12.0, 2),
        "annual_student_loan": round(student_loan_annual, 2),
        "monthly_student_loan": round(student_loan_annual / 12.0, 2),
        "annual_net": round(net_annual, 2),
        "monthly_net": round(net_annual / 12.0, 2),
        "effective_tax_rate_percent": round(((income_tax + ni + student_loan_annual) / max(1.0, annual_salary)) * 100, 1),
        "marginal_rate_percent": round(marginal_total * 100, 1),
    }


def calculate_in_study_loan_balance(
    course_length_years: int,
    tuition_per_year: float,
    maintenance_per_year: float,
    parent_annual_contribution: float = 0.0,
    rpi: float = 0.041,
    plan_type: str = "plan_5",
) -> Dict[str, Any]:
    """
    Simulates loan balance accumulation during university years.
    Returns balance at graduation and yearly accumulation history.
    """
    # Net annual borrowing after parent contribution
    annual_borrowing_base = tuition_per_year + maintenance_per_year
    annual_borrowing_net = max(0.0, annual_borrowing_base - parent_annual_contribution)

    balance = 0.0
    history = []

    # In-study interest rate
    if plan_type == "plan_5":
        study_rate = rpi  # Plan 5 is strictly RPI (currently 4.1%)
    elif plan_type == "plan_2":
        study_rate = min(rpi + 0.03, 0.060)  # Plan 2 is RPI + 3%, capped at 6.0% (currently 6.0%)
    elif plan_type == "plan_1":
        study_rate = min(rpi, 0.041)  # Plan 1 currently 4.1%
    else:
        study_rate = rpi

    total_parent_paid = parent_annual_contribution * course_length_years
    total_borrowed = 0.0

    for year in range(1, course_length_years + 1):
        # Student receives loan installments throughout the year
        # Standard SLC calculation compounds interest monthly; on average 6 months on current year's borrowing
        interest_on_existing = balance * study_rate
        interest_on_new = annual_borrowing_net * (study_rate / 2.0)
        year_interest = interest_on_existing + interest_on_new

        balance += annual_borrowing_net + year_interest
        total_borrowed += annual_borrowing_net

        history.append({
            "study_year": year,
            "borrowed_this_year": round(annual_borrowing_net, 2),
            "interest_this_year": round(year_interest, 2),
            "end_balance": round(balance, 2),
        })

    return {
        "graduation_balance": round(balance, 2),
        "total_borrowed": round(total_borrowed, 2),
        "total_in_study_interest": round(balance - total_borrowed, 2),
        "total_parent_contribution": round(total_parent_paid, 2),
        "in_study_history": history,
    }


def calculate_interest_rate_post_study(plan_type: str, salary: float, rpi: float = 0.041) -> float:
    """Calculates statutory interest rate based on plan rules and graduate salary."""
    if plan_type == "plan_5":
        # Plan 5: Just RPI (no real interest, currently 4.1%)
        return rpi
    elif plan_type == "plan_2":
        lower_threshold = 29385.0
        upper_threshold = 52884.0
        cap_rate = 0.060
        max_addition = max(0.0, min(0.03, cap_rate - rpi))
        if salary <= lower_threshold:
            return rpi
        elif salary >= upper_threshold:
            return rpi + max_addition
        else:
            proportion = (salary - lower_threshold) / (upper_threshold - lower_threshold)
            return rpi + (max_addition * proportion)
    elif plan_type == "plan_1":
        # Plan 1: lower of RPI or Bank Rate + 1% (currently 4.1%)
        return min(rpi, 0.041)
    else:
        return rpi


def simulate_loan_lifetime(
    starting_balance: float,
    starting_salary: float,
    salary_growth_rate: float,
    plan_type: str = "plan_5",
    rpi: float = 0.041,
    has_postgrad: bool = False,
    postgrad_balance: float = 0.0,
    salary_milestones: Optional[Dict[int, float]] = None,
) -> Dict[str, Any]:
    """
    Simulates annual repayments, interest accruals, and balance over the 30- or 40-year write-off window.
    """
    plan = PLAN_CONFIGS.get(plan_type, PLAN_CONFIGS["plan_5"])
    threshold = plan["repayment_threshold"]
    repayment_rate = plan["repayment_rate"]
    write_off_years = plan["write_off_years"]

    current_balance = float(starting_balance)
    current_pg_balance = float(postgrad_balance) if has_postgrad else 0.0

    schedule = []
    total_repaid_ug = 0.0
    total_repaid_pg = 0.0
    total_interest_ug = 0.0
    is_paid_off = False
    payoff_year = None

    for year in range(1, write_off_years + 1):
        # Determine salary for year
        if salary_milestones and year in salary_milestones:
            current_salary = salary_milestones[year]
        else:
            current_salary = starting_salary * ((1.0 + salary_growth_rate) ** (year - 1))

        # Undergrad repayment
        eligible_ug_income = max(0.0, current_salary - threshold)
        expected_ug_repay = eligible_ug_income * repayment_rate

        # Postgrad repayment
        expected_pg_repay = 0.0
        if has_postgrad and current_pg_balance > 0:
            eligible_pg_income = max(0.0, current_salary - POSTGRAD_CONFIG["repayment_threshold"])
            expected_pg_repay = eligible_pg_income * POSTGRAD_CONFIG["repayment_rate"]

        # If undergrad loan is already cleared
        actual_ug_repay = 0.0
        interest_ug = 0.0
        active_interest_rate = calculate_interest_rate_post_study(plan_type, current_salary, rpi)

        if current_balance > 0:
            # Interest applied with mid-year repayment approximation
            max_payable = current_balance * (1.0 + active_interest_rate)
            if expected_ug_repay >= max_payable:
                actual_ug_repay = max_payable
                interest_ug = max_payable - current_balance
                current_balance = 0.0
                if not is_paid_off:
                    is_paid_off = True
                    payoff_year = year
            else:
                actual_ug_repay = expected_ug_repay
                # Monthly repayment interest approximation: (Balance - Repay/2) * rate
                interest_ug = max(0.0, (current_balance - (actual_ug_repay / 2.0)) * active_interest_rate)
                current_balance = current_balance + interest_ug - actual_ug_repay
                if current_balance <= 0.01:
                    current_balance = 0.0
                    if not is_paid_off:
                        is_paid_off = True
                        payoff_year = year

        total_repaid_ug += actual_ug_repay
        total_interest_ug += interest_ug

        # Postgrad handling
        actual_pg_repay = 0.0
        if has_postgrad and current_pg_balance > 0:
            pg_rate = min(rpi + 0.03, 0.060)  # Capped at 6.0% as published on GOV.UK
            max_pg_payable = current_pg_balance * (1.0 + pg_rate)
            if expected_pg_repay >= max_pg_payable:
                actual_pg_repay = max_pg_payable
                current_pg_balance = 0.0
            else:
                actual_pg_repay = expected_pg_repay
                pg_interest = max(0.0, (current_pg_balance - (actual_pg_repay / 2.0)) * pg_rate)
                current_pg_balance = current_pg_balance + pg_interest - actual_pg_repay
            total_repaid_pg += actual_pg_repay

        total_annual_repay = actual_ug_repay + actual_pg_repay
        monthly_repay = total_annual_repay / 12.0

        schedule.append({
            "year": year,
            "salary": round(current_salary, 2),
            "monthly_repay": round(monthly_repay, 2),
            "annual_repay_ug": round(actual_ug_repay, 2),
            "annual_repay_pg": round(actual_pg_repay, 2),
            "total_annual_repay": round(total_annual_repay, 2),
            "cumulative_repaid": round(total_repaid_ug + total_repaid_pg, 2),
            "interest_rate_percent": round(active_interest_rate * 100, 2),
            "interest_accrued_ug": round(interest_ug, 2),
            "balance_end_ug": round(current_balance, 2),
            "balance_end_pg": round(current_pg_balance, 2),
            "is_paid_off": is_paid_off,
        })

    written_off_ug = round(current_balance, 2)
    written_off_pg = round(current_pg_balance, 2)

    return {
        "plan_type": plan_type,
        "plan_name": plan["name"],
        "starting_balance": round(starting_balance, 2),
        "total_repaid": round(total_repaid_ug + total_repaid_pg, 2),
        "total_repaid_ug": round(total_repaid_ug, 2),
        "total_repaid_pg": round(total_repaid_pg, 2),
        "total_interest_ug": round(total_interest_ug, 2),
        "written_off_amount": written_off_ug,
        "is_paid_off": is_paid_off,
        "payoff_year": payoff_year,
        "write_off_years": write_off_years,
        "schedule": schedule,
    }


def calculate_market_investment_growth(
    annual_contributions: List[float],
    lump_sum_initial: float = 0.0,
    rates: List[float] = [0.03, 0.04, 0.05],
    total_years: int = 40,
) -> Dict[str, Any]:
    """
    Calculates the compound growth of an alternative market investment (e.g. Stocks & Shares ISA / Global Index Fund)
    at specified annual growth rates (e.g. 3%, 4%, 5%).
    """
    results_by_rate = {}

    for rate in rates:
        rate_key = f"{int(round(rate * 100))}%"
        pot = lump_sum_initial
        yearly_pot = []

        for yr in range(1, total_years + 1):
            contrib = annual_contributions[yr - 1] if yr <= len(annual_contributions) else 0.0
            # Beginning of year contribution compounded for full year
            pot = (pot + contrib) * (1.0 + rate)
            yearly_pot.append(round(pot, 2))

        # Extract milestone values
        results_by_rate[rate_key] = {
            "rate_percent": round(rate * 100, 1),
            "year_5": yearly_pot[4] if len(yearly_pot) >= 5 else yearly_pot[-1],
            "year_10": yearly_pot[9] if len(yearly_pot) >= 10 else yearly_pot[-1],
            "year_20": yearly_pot[19] if len(yearly_pot) >= 20 else yearly_pot[-1],
            "year_30": yearly_pot[29] if len(yearly_pot) >= 30 else yearly_pot[-1],
            "year_40": yearly_pot[39] if len(yearly_pot) >= 40 else yearly_pot[-1],
            "yearly_trajectory": yearly_pot,
            "final_pot": yearly_pot[-1],
        }

    return results_by_rate


def evaluate_parental_contribution(
    # Loan settings
    mode: str,  # "studying" or "graduated"
    plan_type: str,
    starting_salary: float,
    salary_growth_rate: float,
    rpi: float = 0.041,
    # For studying
    course_length_years: int = 3,
    tuition_per_year: float = 9250.0,
    maintenance_per_year: float = 10227.0,
    # For graduated
    existing_balance: float = 50000.0,
    # Parental contribution
    contribution_type: str = "annual_fee",  # "annual_fee" or "lump_sum"
    parent_annual_amount: float = 9250.0,
    parent_lump_sum_amount: float = 25000.0,
    # Comparison market rates
    market_rates: List[float] = [0.03, 0.04, 0.05],
    custom_market_rate: Optional[float] = None,
    has_postgrad: bool = False,
    postgrad_balance: float = 0.0,
) -> Dict[str, Any]:
    """
    Comprehensive evaluation of parental fee contribution:
    1. Scenario A: Baseline (no parental contribution)
    2. Scenario B: With parental contribution (reduced borrowing or upfront paydown)
    3. Market investment simulation of the identical parental capital at 3%, 4%, 5% (and custom rate)
    4. Strategic Financial Advisory summary with verdict and payback metrics.
    """
    all_market_rates = list(market_rates)
    if custom_market_rate is not None and custom_market_rate not in all_market_rates:
        all_market_rates.append(custom_market_rate)
        all_market_rates.sort()

    # --- Scenario A: Without parental contribution ---
    if mode == "studying":
        base_study = calculate_in_study_loan_balance(
            course_length_years=course_length_years,
            tuition_per_year=tuition_per_year,
            maintenance_per_year=maintenance_per_year,
            parent_annual_contribution=0.0,
            rpi=rpi,
            plan_type=plan_type,
        )
        base_start_balance = base_study["graduation_balance"]
    else:
        base_start_balance = existing_balance

    sim_base = simulate_loan_lifetime(
        starting_balance=base_start_balance,
        starting_salary=starting_salary,
        salary_growth_rate=salary_growth_rate,
        plan_type=plan_type,
        rpi=rpi,
        has_postgrad=has_postgrad,
        postgrad_balance=postgrad_balance,
    )

    # --- Scenario B: With parental contribution ---
    parent_contrib_flow = []
    total_parent_spent = 0.0

    if mode == "studying":
        if contribution_type == "annual_fee":
            annual_parent_contrib = parent_annual_amount
            lump_parent = 0.0
            parent_contrib_flow = [annual_parent_contrib] * course_length_years
            total_parent_spent = annual_parent_contrib * course_length_years
        else:  # lump_sum paid upfront in year 1
            annual_parent_contrib = 0.0
            lump_parent = parent_lump_sum_amount
            # Allocate lump sum towards study borrowing
            parent_contrib_flow = [lump_parent]
            total_parent_spent = lump_parent

        contrib_study = calculate_in_study_loan_balance(
            course_length_years=course_length_years,
            tuition_per_year=tuition_per_year,
            maintenance_per_year=maintenance_per_year,
            parent_annual_contribution=annual_parent_contrib if contribution_type == "annual_fee" else (lump_parent / course_length_years),
            rpi=rpi,
            plan_type=plan_type,
        )
        contrib_start_balance = contrib_study["graduation_balance"]
    else:
        # Graduated: lump sum paydown
        total_parent_spent = parent_lump_sum_amount
        parent_contrib_flow = [total_parent_spent]
        contrib_start_balance = max(0.0, existing_balance - parent_lump_sum_amount)

    sim_contrib = simulate_loan_lifetime(
        starting_balance=contrib_start_balance,
        starting_salary=starting_salary,
        salary_growth_rate=salary_growth_rate,
        plan_type=plan_type,
        rpi=rpi,
        has_postgrad=has_postgrad,
        postgrad_balance=postgrad_balance,
    )

    # --- Savings & Deltas ---
    student_repayments_saved = round(sim_base["total_repaid"] - sim_contrib["total_repaid"], 2)
    interest_saved = round(sim_base["total_interest_ug"] - sim_contrib["total_interest_ug"], 2)
    
    # Payoff period reduction
    base_payoff_yr = sim_base["payoff_year"] or sim_base["write_off_years"]
    contrib_payoff_yr = sim_contrib["payoff_year"] or sim_contrib["write_off_years"]
    years_cleared_earlier = max(0, base_payoff_yr - contrib_payoff_yr) if sim_contrib["is_paid_off"] else 0

    # Net Family Financial Gain = (Student Repayments Saved) - (Parent Money Spent)
    # A negative number means the parent paid money that would have been cancelled by HMRC!
    net_family_financial_gain = round(student_repayments_saved - total_parent_spent, 2)

    # --- Market Investment of Parental Capital ---
    horizon_years = sim_base["write_off_years"]  # 30 for Plan 2, 40 for Plan 5
    if mode == "studying" and contribution_type == "annual_fee":
        annual_investments = parent_contrib_flow + [0.0] * (horizon_years - len(parent_contrib_flow))
        market_growth = calculate_market_investment_growth(
            annual_contributions=annual_investments,
            lump_sum_initial=0.0,
            rates=all_market_rates,
            total_years=horizon_years,
        )
    else:
        market_growth = calculate_market_investment_growth(
            annual_contributions=[0.0] * horizon_years,
            lump_sum_initial=total_parent_spent,
            rates=all_market_rates,
            total_years=horizon_years,
        )

    # --- Strategic Financial Advice & Verdict ---
    # High Earner vs Graduate Tax Trap
    if not sim_base["is_paid_off"] and not sim_contrib["is_paid_off"]:
        verdict_type = "tax_trap"
        verdict_title = "⚠️ High Risk of Wasted Parental Capital (Graduate Tax Trap)"
        verdict_summary = (
            f"Under this career salary path, the student never repays the loan in full before write-off at Year {horizon_years}. "
            f"Because repayments depend strictly on salary (not debt size), paying £{total_parent_spent:,.0f} upfront reduces student repayments by only "
            f"£{student_repayments_saved:,.0f}. The parental contribution largely saves HMRC money, resulting in a net family loss of "
            f"-£{abs(net_family_financial_gain):,.0f} compared to keeping the money."
        )
        verdict_recommendation = (
            f"Recommendation: Strongly advise AGAINST paying tuition upfront. Instead, invest the £{total_parent_spent:,.0f} "
            f"in a Stocks & Shares ISA, Cash ISA, or Lifetime ISA (which adds a 25% free government bonus for a first home deposit). "
            f"At a modest 5% annual return, this capital will grow into £{market_growth.get('5%', {}).get('year_20', 0):,.0f} by Year 20, "
            f"providing a life-changing house deposit or safety net for your child."
        )
    elif not sim_base["is_paid_off"] and sim_contrib["is_paid_off"]:
        verdict_type = "partial_benefit"
        verdict_title = "⚖️ Mixed Financial Benefit: Loan Cleared, But Check Investment Return"
        verdict_summary = (
            f"With your £{total_parent_spent:,.0f} contribution, the loan is cleared in Year {contrib_payoff_yr} (otherwise written off at Year {horizon_years}). "
            f"The student saves £{student_repayments_saved:,.0f} in lifetime loan deductions, yielding a net family return of £{net_family_financial_gain:,.0f}."
        )
        pot_30 = market_growth.get('5%', {}).get('year_30', 0)
        verdict_recommendation = (
            f"Recommendation: Compare the £{student_repayments_saved:,.0f} student repayment savings against the £{pot_30:,.0f} "
            f"investment pot generated at 5% market growth. If your child will need liquid cash for a house deposit in their 20s/30s, "
            f"investing the money offers far greater flexibility than locking it into HMRC debt."
        )
    else:  # High earner: loan paid off in both scenarios
        verdict_type = "high_earner_effective"
        verdict_title = "✅ Effective Debt Paydown for High Earner"
        verdict_summary = (
            f"The student's earnings are high enough to clear the debt in both scenarios. "
            f"Your £{total_parent_spent:,.0f} contribution saves £{interest_saved:,.0f} in interest, clears the loan {years_cleared_earlier} years earlier, "
            f"and saves the student £{student_repayments_saved:,.0f} in total payslip deductions (Net family gain: +£{net_family_financial_gain:,.0f})."
        )
        verdict_recommendation = (
            f"Recommendation: Under this high-earning scenario where the student clears the balance before write-off, "
            f"reducing the loan balance avoids compounding interest (currently {sim_base['schedule'][0]['interest_rate_percent']}%). "
            f"This provides a return equivalent to the loan interest rate, but this outcome is conditional on sustained high graduate earnings; "
            f"voluntary repayments cannot be refunded if earnings drop."
        )

    # First year payslip comparison for current salary
    initial_payslip_base = calculate_take_home_pay(
        starting_salary,
        sim_base["schedule"][0]["total_annual_repay"] if sim_base["schedule"] else 0.0
    )

    return {
        "mode": mode,
        "plan_type": plan_type,
        "total_parent_contribution": round(total_parent_spent, 2),
        "starting_salary": round(starting_salary, 2),
        "salary_growth_rate_percent": round(salary_growth_rate * 100, 2),
        "base_scenario": {
            "initial_balance": sim_base["starting_balance"],
            "total_repaid": sim_base["total_repaid"],
            "total_interest": sim_base["total_interest_ug"],
            "is_paid_off": sim_base["is_paid_off"],
            "payoff_year": sim_base["payoff_year"],
            "written_off_amount": sim_base["written_off_amount"],
            "schedule": sim_base["schedule"],
        },
        "contribution_scenario": {
            "initial_balance": sim_contrib["starting_balance"],
            "total_repaid": sim_contrib["total_repaid"],
            "total_interest": sim_contrib["total_interest_ug"],
            "is_paid_off": sim_contrib["is_paid_off"],
            "payoff_year": sim_contrib["payoff_year"],
            "written_off_amount": sim_contrib["written_off_amount"],
            "schedule": sim_contrib["schedule"],
        },
        "comparison_metrics": {
            "student_repayments_saved": student_repayments_saved,
            "interest_saved": interest_saved,
            "years_cleared_earlier": years_cleared_earlier,
            "net_family_financial_gain": net_family_financial_gain,
        },
        "market_investment_growth": market_growth,
        "verdict": {
            "type": verdict_type,
            "title": verdict_title,
            "summary": verdict_summary,
            "recommendation": verdict_recommendation,
        },
        "initial_payslip": initial_payslip_base,
    }
