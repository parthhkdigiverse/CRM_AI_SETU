import sys
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import traceback

# Core Imports
from app.api.router import api_router
from config import config

app = FastAPI(title="CRM AI SETU API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Exception Handler
@app.middleware("http")
async def catch_exceptions_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal Server Error", "error": str(e)}
        )

# Static Files
# project_root is 2 levels up from backend/app/main.py
app_path = os.path.dirname(os.path.abspath(__file__)) # backend/app
project_root = os.path.dirname(os.path.dirname(app_path)) # e:/CRM AI SETU
frontend_path = os.path.join(project_root, "frontend")

if os.path.exists(frontend_path):
    app.mount("/frontend", StaticFiles(directory=frontend_path), name="frontend")
else:
    print(f"WARNING: Static frontend path not found at {frontend_path}")

@app.get("/")
async def root():
    return {
        "message": "Welcome to CRM AI SETU",
        "backend_api_docs": "/docs",
        "frontend_app": "/frontend/template/index.html",
        "status": "active"
    }

app.include_router(api_router, prefix="/api")

@app.get("/api/config")
async def get_config():
    return {
        "API_BASE_URL": config.API_BASE_URL
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
