import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from app.api.router import api_router
from app.modules.salary import models as salary_models # Force load models
from app.modules.feedback import models as feedback_models # Force load models
from app.modules.incentives import models as incentives_models # Force load models

app = FastAPI(title="CRM AI SETU API")

from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all for local dev (5500, 8080, etc)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")

from datetime import datetime

@app.get("/")
async def root():
    print(f"Request received at {datetime.now()}")
    return {
        "message": "Welcome to CRM AI SETU API",
        "timestamp": str(datetime.now()),
        "status": "active"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app", 
        host="127.0.0.1", 
        port=8123, 
        reload=True,
        reload_dirs=["app"]
    )
