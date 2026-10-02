"""
api/index.py - Vercel Serverless Entrypoint for UK Student Loan Calculator.
Top-level ASGI application 'app' for Vercel Python runtime.
"""

import os
import sys
from typing import Optional, List, Dict, Any
from pathlib import Path

# Add current and parent directories to sys.path
CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parent
for p in [str(CURRENT_DIR), str(ROOT_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

try:
    from engine import (
        PLAN_CONFIGS,
        POSTGRAD_CONFIG,
        calculate_take_home_pay,
        calculate_in_study_loan_balance,
        simulate_loan_lifetime,
        evaluate_parental_contribution,
    )
except ImportError:
    from .engine import (
        PLAN_CONFIGS,
        POSTGRAD_CONFIG,
        calculate_take_home_pay,
        calculate_in_study_loan_balance,
        simulate_loan_lifetime,
        evaluate_parental_contribution,
    )

# Top-level ASGI app definition required by Vercel
app = FastAPI(
    title="UK University Student Loan & Parent Contribution Calculator API",
    description="England & Wales Student Loan Simulator and Parental Investment Opportunity Cost API",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

# Enable CORS for external callers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Request Models ---
class QuickPayslipRequest(BaseModel):
    salary: float = Field(..., ge=0)
    plan_type: str = Field("plan_5")
    has_postgrad: bool = Field(False)


class StudentCalcRequest(BaseModel):
    mode: str = Field("studying")
    plan_type: str = Field("plan_5")
    starting_salary: float = Field(32000.0, ge=0)
    salary_growth_rate: float = Field(0.03, ge=0, le=0.30)
    rpi: float = Field(0.032, ge=0, le=0.15)
    course_length_years: int = Field(3, ge=1, le=6)
    tuition_per_year: float = Field(9250.0, ge=0)
    maintenance_per_year: float = Field(10227.0, ge=0)
    existing_balance: float = Field(50000.0, ge=0)
    has_postgrad: bool = Field(False)
    postgrad_balance: float = Field(0.0, ge=0)


class ParentEvalRequest(BaseModel):
    mode: str = Field("studying")
    plan_type: str = Field("plan_5")
    starting_salary: float = Field(32000.0, ge=0)
    salary_growth_rate: float = Field(0.03, ge=0, le=0.30)
    rpi: float = Field(0.032, ge=0, le=0.15)
    course_length_years: int = Field(3, ge=1, le=6)
    tuition_per_year: float = Field(9250.0, ge=0)
    maintenance_per_year: float = Field(10227.0, ge=0)
    existing_balance: float = Field(50000.0, ge=0)
    contribution_type: str = Field("annual_fee")
    parent_annual_amount: float = Field(9250.0, ge=0)
    parent_lump_sum_amount: float = Field(25000.0, ge=0)
    market_rates: List[float] = Field([0.03, 0.04, 0.05])
    custom_market_rate: Optional[float] = Field(None, ge=0.0, le=0.20)
    has_postgrad: bool = Field(False)
    postgrad_balance: float = Field(0.0, ge=0)


# --- Endpoints ---
@app.get("/api")
@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "UK Student Loan & Parental Contribution Calculator API",
        "regions": "England & Wales",
    }


@app.get("/api/plans")
async def get_plans():
    return {
        "undergrad_plans": PLAN_CONFIGS,
        "postgrad_plan": POSTGRAD_CONFIG,
    }


@app.post("/api/quick-payslip")
async def quick_payslip(req: QuickPayslipRequest):
    plan = PLAN_CONFIGS.get(req.plan_type, PLAN_CONFIGS["plan_5"])
    threshold = plan["repayment_threshold"]
    ug_sl = max(0.0, (req.salary - threshold) * plan["repayment_rate"])

    pg_sl = 0.0
    if req.has_postgrad:
        pg_threshold = POSTGRAD_CONFIG["repayment_threshold"]
        pg_sl = max(0.0, (req.salary - pg_threshold) * POSTGRAD_CONFIG["repayment_rate"])

    total_sl = ug_sl + pg_sl
    breakdown = calculate_take_home_pay(req.salary, student_loan_annual=total_sl)
    breakdown["breakdown_ug_sl"] = round(ug_sl, 2)
    breakdown["breakdown_pg_sl"] = round(pg_sl, 2)
    return breakdown


@app.post("/api/calculate-student")
async def calculate_student(req: StudentCalcRequest):
    if req.mode == "studying":
        study_acc = calculate_in_study_loan_balance(
            course_length_years=req.course_length_years,
            tuition_per_year=req.tuition_per_year,
            maintenance_per_year=req.maintenance_per_year,
            parent_annual_contribution=0.0,
            rpi=req.rpi,
            plan_type=req.plan_type,
        )
        starting_balance = study_acc["graduation_balance"]
        in_study_info = study_acc
    else:
        starting_balance = req.existing_balance
        in_study_info = None

    simulation = simulate_loan_lifetime(
        starting_balance=starting_balance,
        starting_salary=req.starting_salary,
        salary_growth_rate=req.salary_growth_rate,
        plan_type=req.plan_type,
        rpi=req.rpi,
        has_postgrad=req.has_postgrad,
        postgrad_balance=req.postgrad_balance,
    )

    first_year_repay = simulation["schedule"][0]["total_annual_repay"] if simulation["schedule"] else 0.0
    payslip = calculate_take_home_pay(req.starting_salary, first_year_repay)

    return {
        "mode": req.mode,
        "plan_type": req.plan_type,
        "in_study_info": in_study_info,
        "starting_balance": starting_balance,
        "simulation": simulation,
        "initial_payslip": payslip,
    }


@app.post("/api/evaluate-parent")
async def evaluate_parent(req: ParentEvalRequest):
    return evaluate_parental_contribution(
        mode=req.mode,
        plan_type=req.plan_type,
        starting_salary=req.starting_salary,
        salary_growth_rate=req.salary_growth_rate,
        rpi=req.rpi,
        course_length_years=req.course_length_years,
        tuition_per_year=req.tuition_per_year,
        maintenance_per_year=req.maintenance_per_year,
        existing_balance=req.existing_balance,
        contribution_type=req.contribution_type,
        parent_annual_amount=req.parent_annual_amount,
        parent_lump_sum_amount=req.parent_lump_sum_amount,
        market_rates=req.market_rates,
        custom_market_rate=req.custom_market_rate,
        has_postgrad=req.has_postgrad,
        postgrad_balance=req.postgrad_balance,
    )
