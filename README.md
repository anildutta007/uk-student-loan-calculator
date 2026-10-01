# UK UniLoan Calculator & Parental Contribution Lab
> **England & Wales Student Loan Simulator & Parental Investment Opportunity Cost Analyzer**

An interactive, accurate financial decision tool designed for students (currently studying or graduated) and parents in England & Wales. It simulates lifetime loan repayments and models the financial wisdom of paying tuition fees upfront versus investing that capital into the market at 3%, 4%, and 5% compound growth.

---

## 🌟 Key Features

### 1. Student Repayment Simulator (England & Wales)
* **Undergraduate Plans Supported:**
  * **Plan 5 (England 2023+):** £25,000 threshold, 9% repayment, 40-year write-off, flat RPI inflation interest.
  * **Plan 2 (England 2012–2023 / Wales 2012+):** £27,295 threshold, 9% repayment, 30-year write-off, sliding interest scale (RPI to RPI+3%).
  * **Plan 1 (Pre-2012):** £24,990 threshold, 9% repayment, 25-year write-off.
  * **Postgraduate Loan:** +6% repayment above £21,000 (concurrent repayment).
* **Current vs Expected Salary Modeler:**
  * Starting salary inputs and annual career growth progression (1% to 8%).
  * Instant career presets: NHS Nurse (£28k), Teacher (£30k), Median Graduate (£32k), Tech/Engineering (£42k), City Law/Finance (£60k).
* **PAYE Payslip Breakdown:**
  * Monthly and annual deductions for **Gross Pay, Income Tax (20%/40%), National Insurance (8%/2%), Student Loan (9%), and Net Take-Home Pay**.
  * Shows your true marginal tax rate (e.g. 37% or 51%).
* **30- & 40-Year Lifetime Visualizer:**
  * Dynamic charts tracking balance trajectory, annual deductions, and cumulative amount repaid versus government write-off forgiveness.

---

### 2. Parental Contribution & Market Comparison Lab
* **Evaluate Fee Paydown Impact:**
  * Compare paying full annual tuition (£9,250/yr), custom annual amounts, or upfront lump sums.
  * Calculates exact **interest saved**, **years cleared earlier**, and **net family financial return**.
* **3%, 4%, 5% Stock Market / ISA Comparison:**
  * Calculates compound pot growth of the identical parental capital invested in a Stocks & Shares ISA, Cash ISA, or Global Index Fund.
  * Compares loan savings vs investment pot values across key milestones (Course End, 5 yrs, 10 yrs, 20 yrs, 30 yrs, 40 yrs).
* **Strategic Financial Advisory Engine:**
  * **The "Graduate Tax Trap" Warning:** Identifies when paying fees upfront is effectively gifting money to HMRC with £0 benefit to the student (because the balance would have been cancelled anyway).
  * **High-Earner Green Light:** Quantifies when paying down the debt delivers guaranteed tax-free savings.
  * **Lifetime ISA (LISA) / First Home Deposit Alternative:** Illustrates how investing the capital generates a liquid house deposit for your child.

---

### 3. Data Tables & Export
* Comprehensive year-by-year schedule from graduation to write-off.
* One-click **CSV Export** and print-friendly summary report.

---

## 🚀 Quick Start

### 1-Click Launch (Windows)
Double-click `run_loan_calculator.bat` in the workspace root or `run_calculator.bat` inside `uk-student-loan-calculator`:

```powershell
.\run_loan_calculator.bat
```

Open your browser at:
```
http://localhost:8060
```

### Manual Start (Python FastAPI)
```bash
cd uk-student-loan-calculator
python server.py
```

### Running the Test Suite
```bash
python test_loan_calculator.py
python test_api_endpoints.py
```

---

## 🏛️ Statutory UK Student Finance Rules Reference

| Metric | Plan 5 (England 2023+) | Plan 2 (England 2012-23 / Wales 2012+) | Plan 1 (Pre-2012) |
|---|---|---|---|
| **Repayment Threshold** | £25,000 / yr (£2,083/mo) | £27,295 / yr (£2,274/mo) | £24,990 / yr (£2,082/mo) |
| **Repayment Rate** | 9% above threshold | 9% above threshold | 9% above threshold |
| **Interest Rate** | Flat RPI (0% real) | RPI to RPI + 3% (sliding scale) | min(RPI, BoE Base + 1%) |
| **Write-Off Period** | 40 years post-study | 30 years post-study | 25 years (or age 65) |
| **Postgraduate Loan** | 6% above £21,000 (concurrent) | 6% above £21,000 (concurrent) | 6% above £21,000 (concurrent) |

---

## 📁 Project Structure

```
uk-student-loan-calculator/
├── server.py               # FastAPI server and static file provider (port 8060)
├── engine.py               # Mathematical simulation engine (SLC formulas, tax, compound interest)
├── index.html              # Responsive UI with Tailwind CSS & Chart.js
├── app.js                  # Client-side reactivity, interactive charts & CSV export
├── styles.css              # Custom styling, gradients, and print stylesheets
├── test_loan_calculator.py # Unit tests for financial formulas & plan policies
├── test_api_endpoints.py   # Integration tests for FastAPI endpoints
├── run_calculator.bat      # 1-click batch launcher
├── USER_GUIDE.md           # In-depth guide for parents and students
└── README.md               # Project documentation
```
