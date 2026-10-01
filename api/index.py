"""
Vercel Serverless Entrypoint for UK Student Loan Calculator.
Exposes the FastAPI application to Vercel's Python runtime.
"""

import sys
import os
from pathlib import Path

# Add project root and api directory to sys.path
API_DIR = Path(__file__).resolve().parent
ROOT_DIR = API_DIR.parent

for p in [str(API_DIR), str(ROOT_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

# Import app from server.py
try:
    import server
    app = server.app
except Exception as e:
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    app = FastAPI(title="UK Student Loan Calculator Fallback")
    
    @app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE"])
    def fallback_handler(full_path: str):
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"Serverless initialization error: {e}"}
        )
