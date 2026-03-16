# backend/app/api/routes/health.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def health_check():
    return {"status": "ok"}
