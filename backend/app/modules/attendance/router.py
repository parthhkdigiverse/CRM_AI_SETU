from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta, time
from typing import List, Optional
import json

from app.core.database import get_db
from app.core.dependencies import RoleChecker
from app.modules.auth.router import get_current_user
from app.modules.attendance import models, schemas
from app.modules.users.models import User, UserRole
from app.modules.salary.models import LeaveRecord, LeaveStatus, AppSetting
from sqlalchemy import func

router = APIRouter()

admin_checker = RoleChecker([UserRole.ADMIN])
staff_checker = RoleChecker([
    UserRole.ADMIN,
    UserRole.SALES,
    UserRole.TELESALES,
    UserRole.PROJECT_MANAGER,
    UserRole.PROJECT_MANAGER_AND_SALES
])

DEFAULT_ABSENT_HOURS_THRESHOLD = 0.0
DEFAULT_HALF_DAY_HOURS_THRESHOLD = 4.0
DEFAULT_WEEKLY_OFF_SATURDAY = "FULL"
DEFAULT_WEEKLY_OFF_SUNDAY = "FULL"
DEFAULT_OFFICIAL_HOLIDAYS: List[str] = []


def _get_setting(db: Session, key: str, default: str) -> str:
    row = db.query(AppSetting).filter(AppSetting.key == key).first()
    return row.value if row and row.value is not None else default


def _get_float_setting(db: Session, key: str, default: float) -> float:
    raw = _get_setting(db, key, str(default))
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def _get_list_setting(db: Session, key: str, default: List[str]) -> List[str]:
    raw = _get_setting(db, key, json.dumps(default))
    if not raw:
        return list(default)
    raw = raw.strip()
    try:
        val = json.loads(raw)
        if isinstance(val, list):
            return [str(v).strip() for v in val if str(v).strip()]
    except json.JSONDecodeError:
        pass
    return [v.strip() for v in raw.split(',') if v.strip()]


def _load_attendance_settings(db: Session) -> dict:
    return {
        "absent_hours_threshold": _get_float_setting(db, "attendance_absent_hours_threshold", DEFAULT_ABSENT_HOURS_THRESHOLD),
        "half_day_hours_threshold": _get_float_setting(db, "attendance_half_day_hours_threshold", DEFAULT_HALF_DAY_HOURS_THRESHOLD),
        "weekly_off_saturday": _get_setting(db, "attendance_weekly_off_saturday", DEFAULT_WEEKLY_OFF_SATURDAY),
        "weekly_off_sunday": _get_setting(db, "attendance_weekly_off_sunday", DEFAULT_WEEKLY_OFF_SUNDAY),
        "official_holidays": _get_list_setting(db, "attendance_official_holidays", DEFAULT_OFFICIAL_HOLIDAYS),
    }


def _is_official_leave(day: date, settings: dict) -> bool:
    weekday = day.weekday()  # Monday=0 .. Sunday=6
    if weekday == 5 and (settings.get("weekly_off_saturday") or "").upper() != "NONE":
        return True
    if weekday == 6 and (settings.get("weekly_off_sunday") or "").upper() != "NONE":
        return True

    holidays = set(settings.get("official_holidays") or [])
    return day.isoformat() in holidays


def _compute_daily_summary(records: List[models.Attendance], day: date) -> dict:
    total_hours = 0.0
    first_in = None
    last_out = None
    missing_punch_out = False

    for rec in records:
        if rec.punch_in:
            if first_in is None or rec.punch_in < first_in:
                first_in = rec.punch_in
        if rec.punch_out:
            if last_out is None or rec.punch_out > last_out:
                last_out = rec.punch_out

    for rec in records:
        if rec.punch_in:
            if rec.punch_out:
                end_time = rec.punch_out
            else:
                missing_punch_out = True
                if day < datetime.now().date():
                    end_time = datetime.combine(day, time(23, 59, 59))
                else:
                    end_time = datetime.now()
            total_hours += max(0.0, (end_time - rec.punch_in).total_seconds() / 3600)

    return {
        "total_hours": round(total_hours, 2),
        "first_punch_in": first_in,
        "last_punch_out": last_out,
        "missing_punch_out": missing_punch_out,
    }


def _ensure_auto_leaves(
    db: Session,
    user: User,
    start_date: date,
    end_date: date,
    settings: dict
) -> int:
    created = 0
    today = datetime.now().date()
    day = start_date

    while day <= end_date:
        if day >= today:
            day += timedelta(days=1)
            continue

        if _is_official_leave(day, settings):
            day += timedelta(days=1)
            continue

        existing_leave = db.query(LeaveRecord).filter(
            LeaveRecord.user_id == user.id,
            LeaveRecord.start_date <= day,
            LeaveRecord.end_date >= day
        ).first()
        if existing_leave:
            day += timedelta(days=1)
            continue

        records = db.query(models.Attendance).filter(
            models.Attendance.user_id == user.id,
            models.Attendance.date == day,
        ).all()

        summary = _compute_daily_summary(records, day)
        total_hours = summary["total_hours"]
        absent_threshold = float(settings.get("absent_hours_threshold") or 0.0)
        half_threshold = float(settings.get("half_day_hours_threshold") or 0.0)

        if total_hours <= absent_threshold:
            day_type = "FULL"
            reason = f"Auto leave: no punch recorded on {day.isoformat()}"
        elif total_hours < half_threshold:
            day_type = "HALF"
            reason = f"Auto leave: insufficient hours ({total_hours:.2f} < {half_threshold:.2f})"
        else:
            day += timedelta(days=1)
            continue

        db_leave = LeaveRecord(
            user_id=user.id,
            start_date=day,
            end_date=day,
            leave_type="UNPAID",
            day_type=day_type,
            reason=reason,
            status=LeaveStatus.PENDING,
        )
        db.add(db_leave)
        created += 1
        day += timedelta(days=1)

    if created:
        db.commit()
    return created

@router.post("/punch", response_model=schemas.AttendanceResponse)
def punch_in_out(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    today = datetime.now().date()
    now = datetime.now()
    
    # Check for an open attendance record today
    attendance = db.query(models.Attendance).filter(
        models.Attendance.user_id == current_user.id,
        models.Attendance.date == today,
        models.Attendance.punch_out == None,
        models.Attendance.is_deleted == False
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
        models.Attendance.date == today,
        models.Attendance.is_deleted == False
    ).order_by(models.Attendance.punch_in.desc()).first()
    
    is_punched_in = last_record is not None and last_record.punch_out is None
    last_punch = last_record.punch_in if last_record else None
    
    # 2. Today's total hours
    today_hours = db.query(func.sum(models.Attendance.total_hours)).filter(
        models.Attendance.user_id == current_user.id,
        models.Attendance.date == today,
        models.Attendance.is_deleted == False
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


@router.get("/settings", response_model=schemas.AttendanceSettings)
def get_attendance_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_checker)
):
    settings = _load_attendance_settings(db)
    return {
        "absent_hours_threshold": float(settings["absent_hours_threshold"]),
        "half_day_hours_threshold": float(settings["half_day_hours_threshold"]),
        "weekly_off_saturday": (settings["weekly_off_saturday"] or "FULL").upper(),
        "weekly_off_sunday": (settings["weekly_off_sunday"] or "FULL").upper(),
        "official_holidays": [date.fromisoformat(d) for d in settings.get("official_holidays") or []],
    }


@router.put("/settings", response_model=schemas.AttendanceSettings)
def update_attendance_settings(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_checker)
):
    absent_hours = payload.get("absent_hours_threshold", DEFAULT_ABSENT_HOURS_THRESHOLD)
    half_hours = payload.get("half_day_hours_threshold", DEFAULT_HALF_DAY_HOURS_THRESHOLD)
    saturday = (payload.get("weekly_off_saturday") or DEFAULT_WEEKLY_OFF_SATURDAY).upper()
    sunday = (payload.get("weekly_off_sunday") or DEFAULT_WEEKLY_OFF_SUNDAY).upper()
    holidays = payload.get("official_holidays") or []

    if saturday not in {"NONE", "HALF", "FULL"}:
        raise HTTPException(status_code=400, detail="weekly_off_saturday must be NONE, HALF, or FULL")
    if sunday not in {"NONE", "HALF", "FULL"}:
        raise HTTPException(status_code=400, detail="weekly_off_sunday must be NONE, HALF, or FULL")

    try:
        absent_hours = float(absent_hours)
        half_hours = float(half_hours)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid hour thresholds")

    holiday_list = []
    for h in holidays:
        try:
            holiday_list.append(date.fromisoformat(str(h)))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid holiday date: {h}")

    updates = {
        "attendance_absent_hours_threshold": str(absent_hours),
        "attendance_half_day_hours_threshold": str(half_hours),
        "attendance_weekly_off_saturday": saturday,
        "attendance_weekly_off_sunday": sunday,
        "attendance_official_holidays": json.dumps([d.isoformat() for d in holiday_list]),
    }

    for key, value in updates.items():
        row = db.query(AppSetting).filter(AppSetting.key == key).first()
        if row:
            row.value = value
        else:
            db.add(AppSetting(key=key, value=value))
    db.commit()

    return {
        "absent_hours_threshold": absent_hours,
        "half_day_hours_threshold": half_hours,
        "weekly_off_saturday": saturday,
        "weekly_off_sunday": sunday,
        "official_holidays": holiday_list,
    }


@router.get("/summary", response_model=schemas.AttendanceSummaryResponse)
def get_attendance_summary(
    user_id: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    reconcile: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
):
    today = datetime.now().date()
    if end_date is None:
        end_date = today
    if start_date is None:
        start_date = end_date - timedelta(days=6)

    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date must be before end_date")

    target_user = None
    if user_id:
        target_user = db.query(User).filter(User.id == user_id).first()
        if not target_user:
            raise HTTPException(status_code=404, detail="User not found")

    if current_user.role != UserRole.ADMIN:
        if user_id and current_user.id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        target_user = current_user

    settings = _load_attendance_settings(db)

    if reconcile:
        if current_user.role == UserRole.ADMIN:
            if target_user:
                _ensure_auto_leaves(db, target_user, start_date, end_date, settings)
            else:
                users = db.query(User).filter(User.is_deleted == False).all()
                for u in users:
                    if u.role != UserRole.ADMIN:
                        _ensure_auto_leaves(db, u, start_date, end_date, settings)
        else:
            _ensure_auto_leaves(db, current_user, start_date, end_date, settings)

    records = []
    total_hours = 0.0

    if target_user:
        users = [target_user]
    else:
        users = db.query(User).filter(User.is_deleted == False).all()

    day = start_date
    while day <= end_date:
        for u in users:
            if u.role == UserRole.ADMIN:
                continue

            day_records = db.query(models.Attendance).filter(
                models.Attendance.user_id == u.id,
                models.Attendance.date == day,
                models.Attendance.is_deleted == False
            ).all()
            summary = _compute_daily_summary(day_records, day)

            day_status = "PRESENT"
            if _is_official_leave(day, settings):
                day_status = "OFF"
            else:
                if summary["total_hours"] <= float(settings.get("absent_hours_threshold") or 0.0):
                    day_status = "ABSENT"
                elif summary["total_hours"] < float(settings.get("half_day_hours_threshold") or 0.0):
                    day_status = "HALF"

            leave = db.query(LeaveRecord).filter(
                LeaveRecord.user_id == u.id,
                LeaveRecord.start_date <= day,
                LeaveRecord.end_date >= day
            ).first()

            record = {
                "date": day,
                "user_id": u.id,
                "user_name": u.name or u.email,
                "first_punch_in": summary["first_punch_in"],
                "last_punch_out": summary["last_punch_out"],
                "total_hours": summary["total_hours"],
                "day_status": day_status,
                "leave_status": leave.status if leave else None,
            }
            records.append(record)
            total_hours += summary["total_hours"]
        day += timedelta(days=1)

    return {
        "start_date": start_date,
        "end_date": end_date,
        "total_hours": round(total_hours, 2),
        "records": records,
    }
