# backend/app/modules/attendance/router.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
from typing import List
from app.core.database import get_db
from app.modules.auth.router import get_current_user
from app.modules.attendance import models, schemas
from sqlalchemy import func

router = APIRouter()

@router.post("/punch", response_model=schemas.AttendanceResponse)
def punch_in_out(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    today = datetime.now().date()
    now = datetime.now()
    
    # Check for an open attendance record today
    attendance = db.query(models.Attendance).filter(
        models.Attendance.user_id == current_user.id,
        models.Attendance.date == today,
        models.Attendance.punch_out == None
    ).first()
    
    if attendance:
        # Punch Out
        attendance.punch_out = now
        duration = (attendance.punch_out - attendance.punch_in).total_seconds() / 3600
        attendance.total_hours = round(duration, 2)
        db.commit()
        db.refresh(attendance)
        return attendance
    else:
        # Punch In
        new_attendance = models.Attendance(
            user_id = current_user.id,
            date = today,
            punch_in = now
        )
        db.add(new_attendance)
        db.commit()
        db.refresh(new_attendance)
        return new_attendance

@router.get("/status", response_model=schemas.PunchStatus)
def get_punch_status(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    today = datetime.now().date()
    
    # 1. Today's Status
    last_record = db.query(models.Attendance).filter(
        models.Attendance.user_id == current_user.id,
        models.Attendance.date == today
    ).order_by(models.Attendance.punch_in.desc()).first()
    
    is_punched_in = last_record is not None and last_record.punch_out is None
    last_punch = last_record.punch_in if last_record else None
    
    # 2. Today's total hours
    today_hours = db.query(func.sum(models.Attendance.total_hours)).filter(
        models.Attendance.user_id == current_user.id,
        models.Attendance.date == today
    ).scalar() or 0.0
    
    # 3. Weekly total hours (Last 7 days)
    week_ago = today - timedelta(days=7)
    week_hours = db.query(func.sum(models.Attendance.total_hours)).filter(
        models.Attendance.user_id == current_user.id,
        models.Attendance.date >= week_ago
    ).scalar() or 0.0
    
    # 4. Monthly total hours (Current month)
    month_start = today.replace(day=1)
    month_hours = db.query(func.sum(models.Attendance.total_hours)).filter(
        models.Attendance.user_id == current_user.id,
        models.Attendance.date >= month_start
    ).scalar() or 0.0
    
    return {
        "is_punched_in": is_punched_in,
        "last_punch": last_punch,
        "today_hours": round(today_hours, 2),
        "week_hours": round(week_hours, 2),
        "month_hours": round(month_hours, 2)
    }
