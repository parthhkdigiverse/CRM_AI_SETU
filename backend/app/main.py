from fastapi import FastAPI
from app.api.router import api_router

app = FastAPI(title="CRM AI SETU API")

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
