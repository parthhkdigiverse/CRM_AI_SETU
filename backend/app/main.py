# backend/app/main.py
import sys
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse, Response
import traceback

# Core Imports
from app.api.router import api_router
import config.config as config
from app.utils.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup & shutdown hooks."""
    # ── Startup ──────────────────────────────────────────────────
    from app.core.database import init_db
    init_db()
    start_scheduler()
    yield
    # ── Shutdown ─────────────────────────────────────────────────
    stop_scheduler()


app = FastAPI(title="SRM AI SETU API", lifespan=lifespan)

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
app_path = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(app_path))
frontend_path = os.path.join(project_root, "frontend")

if os.path.exists(frontend_path):
    app.mount("/frontend", StaticFiles(directory=frontend_path), name="frontend")
else:
    print(f"WARNING: Static frontend path not found at {frontend_path}")

# Uploads / Static Assets
backend_path = os.path.join(project_root, "backend")
static_path = os.path.join(backend_path, "static")
os.makedirs(static_path, exist_ok=True)  # ensure it exists on first boot
app.mount("/static", StaticFiles(directory=static_path), name="static")

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    favicon_path = os.path.join(frontend_path, "favicon.ico")
    if os.path.exists(favicon_path):
        return FileResponse(favicon_path)
    return Response(status_code=204)

@app.get("/")
async def root():
    return {
        "message": "Welcome to SRM AI SETU",
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
