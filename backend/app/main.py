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
from app.core.config import settings
from app.utils.scheduler import start_scheduler, stop_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup & shutdown hooks."""
    try:
        from app.core.database import connect_to_mongo, get_database
        from beanie import init_beanie 
        from app.modules.users.models import User
        from app.modules.activity_logs.models import ActivityLog
        from app.modules.clients.models import Client, ClientPMHistory
        from app.modules.shops.models import Shop
        from app.modules.visits.models import Visit
        from app.modules.projects.models import Project
        from app.modules.issues.models import Issue
        from app.modules.meetings.models import MeetingSummary
        from app.modules.todos.models import Todo
        from app.modules.notifications.models import Notification
        from app.modules.payments.models import Payment
        from app.modules.salary.models import LeaveRecord, SalarySlip, AppSetting
        from app.modules.reports.models import PerformanceNote
        from app.modules.attendance.models import Attendance
        from app.modules.settings.models import SystemSettings
        from app.modules.feedback.models import Feedback, UserFeedback
        from app.modules.areas.models import Area
        from app.modules.incentives.models import IncentiveSlab

        from app.modules.billing.models import Bill

        print("[Lifespan] Connecting to MongoDB...")
        await connect_to_mongo()
        
        db = get_database()
        if db is not None:
            print("[Lifespan] Initializing Beanie with all Document models...")
            await init_beanie(database=db, document_models=[
                User, ActivityLog, Client, ClientPMHistory, Shop, Visit,
                Project, Issue, MeetingSummary, Todo, Notification, Payment,
                LeaveRecord, SalarySlip, AppSetting, PerformanceNote, Attendance,
                SystemSettings, Feedback, UserFeedback, Area, IncentiveSlab, Bill
            ]) 
            print("[Lifespan] Beanie initialized successfully with all models.")
        # -------------------------------

        print("[Lifespan] Starting scheduler...")
        start_scheduler()
        
    except Exception as startup_error:
        print(f"[Lifespan] STARTUP ERROR: {startup_error}")
        traceback.print_exc()
        raise startup_error
    
    yield
    # ... shutdown logic will be here ...
    
    # ── Shutdown ─────────────────────────────────────────────────
    try:
        from app.core.database import close_mongo_connection
        print("[Lifespan] Stopping scheduler...")
        stop_scheduler()
        print("[Lifespan] Scheduler stopped successfully.")
        
        print("[Lifespan] Closing MongoDB connection...")
        await close_mongo_connection()
        print("[Lifespan] MongoDB connection closed.")
    except Exception as shutdown_error:
        print(f"[Lifespan] SHUTDOWN ERROR: {shutdown_error}")
        traceback.print_exc()

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

# --- Path Logic (Fixed) ---
app_path = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(app_path))
frontend_path = os.path.join(project_root, "frontend")

# 1. Frontend Static Files (JS/CSS/Images mate)
if os.path.exists(frontend_path):
    app.mount("/frontend", StaticFiles(directory=frontend_path), name="frontend")
    # Direct mounts for JS, CSS, Images (HTML templates use relative paths like ../js/auth.js)
    js_path = os.path.join(frontend_path, "js")
    css_path = os.path.join(frontend_path, "css")
    images_path = os.path.join(frontend_path, "images")
    if os.path.exists(js_path):
        app.mount("/js", StaticFiles(directory=js_path), name="js")
    if os.path.exists(css_path):
        app.mount("/css", StaticFiles(directory=css_path), name="css")
    if os.path.exists(images_path):
        app.mount("/images", StaticFiles(directory=images_path), name="images")
else:
    print(f"WARNING: Static frontend path not found at {frontend_path}")

# 2. Uploads / Static Assets
backend_path = os.path.join(project_root, "backend")
static_path = os.path.join(backend_path, "static")
os.makedirs(static_path, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_path), name="static")

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    favicon_path = os.path.join(frontend_path, "favicon.ico")
    if os.path.exists(favicon_path):
        return FileResponse(favicon_path)
    return Response(status_code=204)

# --- Updated Root Route (Login Page Sidhu Khulava Mate) ---
@app.get("/")
async def root():
    index_path = os.path.join(frontend_path, "template", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        return {
            "message": "Welcome to SRM AI SETU",
            "error": f"index.html not found at {index_path}",
            "status": "active"
        }

app.include_router(api_router, prefix="/api")

@app.get("/api/config")
async def get_config(request: Request):
    request_base = str(request.base_url).rstrip("/")
    return {
        "API_BASE_URL": f"{request_base}/api"
    }

# --- Catch-All Route for Frontend Pages ---
@app.get("/{page_name:path}")
async def serve_frontend_page(page_name: str):
    """
    Serve any frontend HTML page like /dashboard.html, /clients.html, etc.
    This must be the LAST route to avoid intercepting API calls.
    """
    # Skip static file extensions — let them 404 naturally
    static_extensions = ('.js', '.css', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.woff', '.woff2', '.ttf', '.map')
    if any(page_name.endswith(ext) for ext in static_extensions):
        return JSONResponse(status_code=404, content={"detail": f"Static file '{page_name}' not found"})

    # If the page name doesn't end with .html, add it
    if not page_name.endswith(".html"):
        page_name = page_name + ".html"
    
    page_path = os.path.join(frontend_path, "template", page_name)
    
    if os.path.exists(page_path):
        return FileResponse(page_path)
    
    # Fallback to index.html for SPA-style routing
    index_path = os.path.join(frontend_path, "template", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    
    return JSONResponse(status_code=404, content={"detail": f"Page '{page_name}' not found"})