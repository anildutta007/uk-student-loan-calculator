"""
server.py - FastAPI backend & Web Server for UK Student Loan & Parent Investment Calculator
"""

import os
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
import uvicorn

from engine import (
    PLAN_CONFIGS,
    POSTGRAD_CONFIG,
    calculate_take_home_pay,
    calculate_in_study_loan_balance,
    simulate_loan_lifetime,
    evaluate_parental_contribution,
    calculate_interest_rate_post_study,
)

app = FastAPI(
    title="UK University Student Loan & Parent Contribution Calculator",
    description="England & Wales Student Loan Simulator with Parental Contribution & Market Investment Opportunity Cost Analyzer",
    version="1.0.0",
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Request Models ---
class QuickPayslipRequest(BaseModel):
    salary: float = Field(..., ge=0, description="Annual gross salary in GBP")
    plan_type: str = Field("plan_5", description="Student loan plan: plan_5, plan_2, plan_1")
    has_postgrad: bool = Field(False, description="Whether graduate also has a postgraduate loan")

class StudentCalcRequest(BaseModel):
    mode: str = Field("studying", description="'studying' or 'graduated'")
    plan_type: str = Field("plan_5", description="'plan_5', 'plan_2', 'plan_1'")
    starting_salary: float = Field(32000.0, ge=0)
    salary_growth_rate: float = Field(0.03, ge=0, le=0.30)
    rpi: float = Field(0.032, ge=0, le=0.15)
    # If studying
    course_length_years: int = Field(3, ge=1, le=6)
    tuition_per_year: float = Field(9250.0, ge=0)
    maintenance_per_year: float = Field(10227.0, ge=0)
    # If graduated
    existing_balance: float = Field(50000.0, ge=0)
    # Postgrad
    has_postgrad: bool = Field(False)
    postgrad_balance: float = Field(0.0, ge=0)

class ParentEvalRequest(BaseModel):
    mode: str = Field("studying", description="'studying' or 'graduated'")
    plan_type: str = Field("plan_5", description="'plan_5', 'plan_2', 'plan_1'")
    starting_salary: float = Field(32000.0, ge=0)
    salary_growth_rate: float = Field(0.03, ge=0, le=0.30)
    rpi: float = Field(0.032, ge=0, le=0.15)
    course_length_years: int = Field(3, ge=1, le=6)
    tuition_per_year: float = Field(9250.0, ge=0)
    maintenance_per_year: float = Field(10227.0, ge=0)
    existing_balance: float = Field(50000.0, ge=0)
    contribution_type: str = Field("annual_fee", description="'annual_fee' or 'lump_sum'")
    parent_annual_amount: float = Field(9250.0, ge=0)
    parent_lump_sum_amount: float = Field(25000.0, ge=0)
    market_rates: List[float] = Field([0.03, 0.04, 0.05])
    custom_market_rate: Optional[float] = Field(None, ge=0.0, le=0.20)
    has_postgrad: bool = Field(False)
    postgrad_balance: float = Field(0.0, ge=0)


# --- API Endpoints ---
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
    res = evaluate_parental_contribution(
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
    return res

# Static file serving
@app.get("/")
async def serve_index():
    index_path = os.path.join(BASE_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "UK Student Loan Calculator API running"}

@app.get("/styles.css")
async def serve_css():
    css_path = os.path.join(BASE_DIR, "styles.css")
    if os.path.exists(css_path):
        return FileResponse(css_path, media_type="text/css")
    return JSONResponse(status_code=404, content={"error": "styles.css not found"})

@app.get("/app.js")
async def serve_js():
    js_path = os.path.join(BASE_DIR, "app.js")
    if os.path.exists(js_path):
        return FileResponse(js_path, media_type="application/javascript")
    return JSONResponse(status_code=404, content={"error": "app.js not found"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8060))
    print(f"Starting UK Student Loan & Parental Contribution Calculator on http://localhost:{port}")
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=True)
