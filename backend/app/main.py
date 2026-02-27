import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from app.api.router import api_router
import sys
import os

# Allow absolute imports from the project root
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from config import config

from app.modules.salary import models as salary_models # Force load models
from app.modules.feedback import models as feedback_models # Force load models
from app.modules.incentives import models as incentives_models # Force load models

app = FastAPI(title="CRM AI SETU API")

from app.core.database import SessionLocal
from sqlalchemy import text




from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all for local dev (5500, 8080, etc)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi import Request
import traceback

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

@app.middleware("http")
async def no_cache_html_middleware(request: Request, call_next):
    """Force browsers to always fetch fresh HTML — prevents 304 stale-cache issues."""
    response = await call_next(request)
    if request.url.path.endswith(".html"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        # Remove ETag so browser can't use conditional requests to get a 304
        if "etag" in response.headers:
            del response.headers["etag"]
        if "last-modified" in response.headers:
            del response.headers["last-modified"]
    return response

# Mount the static frontend directory so uvicorn serves both API and UI
# We need to guarantee root_dir points to the very top project folder
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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
    import os
    
    app_dir = os.path.dirname(os.path.abspath(__file__))
    uvicorn.run(
        "app.main:app", 
        host="127.0.0.1", 
        port=8000, 
        reload=True,
        reload_dirs=[app_dir]
    )
