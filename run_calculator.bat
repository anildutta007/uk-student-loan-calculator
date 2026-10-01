@echo off
title UK UniLoan Calculator & Parental Contribution Lab
cd /d "%~dp0"
echo ========================================================
echo   UK Student Loan & Parental Contribution Calculator
echo   England & Wales (Plan 2, Plan 5, Plan 1, Postgrad)
echo ========================================================
echo Starting server on http://localhost:8060 ...
echo Press Ctrl+C to stop.
echo.
python server.py
pause
