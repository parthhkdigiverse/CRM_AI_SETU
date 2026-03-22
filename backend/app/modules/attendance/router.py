from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime, date, timedelta, time
from typing import List, Optional
import json

from app.core.dependencies import RoleChecker, get_current_user
from app.modules.attendance.models import Attendance
from app.modules.attendance import schemas
from app.modules.users.models import User, UserRole

router = APIRouter()

admin_checker = RoleChecker([UserRole.ADMIN])
staff_checker = RoleChecker([UserRole.ADMIN, UserRole.SALES, UserRole.TELESALES, UserRole.PROJECT_MANAGER, UserRole.PROJECT_MANAGER_AND_SALES])

DEFAULT_ABSENT_HOURS_THRESHOLD = 0.0
DEFAULT_HALF_DAY_HOURS_THRESHOLD = 4.0
DEFAULT_WEEKLY_OFF_SATURDAY = "FULL"
DEFAULT_WEEKLY_OFF_SUNDAY = "FULL"
DEFAULT_OFFICIAL_HOLIDAYS: List[str] = []

async def _get_setting(key: str, default: str) -> str:
    from app.modules.salary.models import AppSetting
    row = await AppSetting.find_one(AppSetting.key == key)
    return row.value if row and row.value is not None else default

async def _get_float_setting(key: str, default: float) -> float:
    raw = await _get_setting(key, str(default))
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default

async def _get_list_setting(key: str, default: List[str]) -> List[str]:
    raw = await _get_setting(key, json.dumps(default))
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

async def _load_attendance_settings() -> dict:
    return {
        "absent_hours_threshold": await _get_float_setting("attendance_absent_hours_threshold", DEFAULT_ABSENT_HOURS_THRESHOLD),
        "half_day_hours_threshold": await _get_float_setting("attendance_half_day_hours_threshold", DEFAULT_HALF_DAY_HOURS_THRESHOLD),
        "weekly_off_saturday": await _get_setting("attendance_weekly_off_saturday", DEFAULT_WEEKLY_OFF_SATURDAY),
        "weekly_off_sunday": await _get_setting("attendance_weekly_off_sunday", DEFAULT_WEEKLY_OFF_SUNDAY),
        "official_holidays": await _get_list_setting("attendance_official_holidays", DEFAULT_OFFICIAL_HOLIDAYS),
    }

def _is_official_leave(day: date, settings: dict) -> bool:
    weekday = day.weekday()
    if weekday == 5 and (settings.get("weekly_off_saturday") or "").upper() != "NONE":
        return True
    if weekday == 6 and (settings.get("weekly_off_sunday") or "").upper() != "NONE":
        return True
    holidays = set(settings.get("official_holidays") or [])
    return day.isoformat() in holidays

def _compute_daily_summary(records: List[Attendance], day: date) -> dict:
    total_hours = 0.0
    first_in = None
    last_out = None
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
                if day < datetime.now().date():
                    end_time = datetime.combine(day, time(23, 59, 59))
                else:
                    end_time = datetime.now()
            total_hours += max(0.0, (end_time - rec.punch_in).total_seconds() / 3600)
    return {"total_hours": round(total_hours, 2), "first_punch_in": first_in, "last_punch_out": last_out}

async def _ensure_auto_leaves(user: User, start_date: date, end_date: date, settings: dict) -> int:
    from app.modules.salary.models import LeaveRecord, LeaveStatus
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
        existing_leave = await LeaveRecord.find_one(LeaveRecord.user_id == user.id, LeaveRecord.start_date <= day, LeaveRecord.end_date >= day)
        if existing_leave:
            day += timedelta(days=1)
            continue
        records = await Attendance.find(Attendance.user_id == user.id, Attendance.date == day).to_list()
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
        from app.modules.salary.models import LeaveRecord, LeaveStatus
        db_leave = LeaveRecord(user_id=user.id, start_date=day, end_date=day, leave_type="UNPAID", day_type=day_type, reason=reason, status=LeaveStatus.PENDING)
        await db_leave.insert()
        created += 1
        day += timedelta(days=1)
    return created

@router.post("/punch", response_model=schemas.AttendanceResponse)
async def punch_in_out(current_user: User = Depends(get_current_user)):
    today = datetime.now().date()
    now = datetime.now()
    attendance = await Attendance.find_one(Attendance.user_id == current_user.id, Attendance.date == today, Attendance.punch_out == None, Attendance.is_deleted != True)
    if attendance:
        attendance.punch_out = now
        duration = (attendance.punch_out - attendance.punch_in).total_seconds() / 3600
        attendance.total_hours = round(duration, 2)
        await attendance.save()
        return attendance
    else:
        new_attendance = Attendance(user_id=current_user.id, date=today, punch_in=now)
        await new_attendance.insert()
        return new_attendance

@router.get("/status", response_model=schemas.PunchStatus)
async def get_punch_status(current_user: User = Depends(get_current_user)):
    today = datetime.now().date()
    records = await Attendance.find(Attendance.user_id == current_user.id, Attendance.date == today, Attendance.is_deleted != True).to_list()
    last_record = sorted(records, key=lambda r: r.punch_in or datetime.min, reverse=True)[0] if records else None
    is_punched_in = last_record is not None and last_record.punch_out is None
    last_punch = last_record.punch_in if last_record else None
    today_hours = sum(r.total_hours for r in records)
    week_ago = today - timedelta(days=7)
    week_records = await Attendance.find(Attendance.user_id == current_user.id, Attendance.date >= week_ago).to_list()
    week_hours = sum(r.total_hours for r in week_records)
    month_start = today.replace(day=1)
    month_records = await Attendance.find(Attendance.user_id == current_user.id, Attendance.date >= month_start).to_list()
    month_hours = sum(r.total_hours for r in month_records)
    return {"is_punched_in": is_punched_in, "last_punch": last_punch, "today_hours": round(today_hours, 2), "week_hours": round(week_hours, 2), "month_hours": round(month_hours, 2)}

@router.get("/settings", response_model=schemas.AttendanceSettings)
async def get_attendance_settings(current_user: User = Depends(admin_checker)):
    settings = await _load_attendance_settings()
    return {"absent_hours_threshold": float(settings["absent_hours_threshold"]), "half_day_hours_threshold": float(settings["half_day_hours_threshold"]), "weekly_off_saturday": (settings["weekly_off_saturday"] or "FULL").upper(), "weekly_off_sunday": (settings["weekly_off_sunday"] or "FULL").upper(), "official_holidays": [date.fromisoformat(d) for d in settings.get("official_holidays") or []]}

@router.put("/settings", response_model=schemas.AttendanceSettings)
async def update_attendance_settings(payload: dict, current_user: User = Depends(admin_checker)):
    from app.modules.salary.models import AppSetting
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
    updates = {"attendance_absent_hours_threshold": str(absent_hours), "attendance_half_day_hours_threshold": str(half_hours), "attendance_weekly_off_saturday": saturday, "attendance_weekly_off_sunday": sunday, "attendance_official_holidays": json.dumps([d.isoformat() for d in holiday_list])}
    for key, value in updates.items():
        row = await AppSetting.find_one(AppSetting.key == key)
        if row:
            row.value = value
            await row.save()
        else:
            await AppSetting(key=key, value=value).insert()
    return {"absent_hours_threshold": absent_hours, "half_day_hours_threshold": half_hours, "weekly_off_saturday": saturday, "weekly_off_sunday": sunday, "official_holidays": holiday_list}

@router.get("/summary", response_model=schemas.AttendanceSummaryResponse)
async def get_attendance_summary(user_id: Optional[str] = Query(None), start_date: Optional[date] = Query(None), end_date: Optional[date] = Query(None), reconcile: bool = Query(False), current_user: User = Depends(staff_checker)):
    today = datetime.now().date()
    if end_date is None:
        end_date = today
    if start_date is None:
        start_date = end_date - timedelta(days=6)
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date must be before end_date")
    target_user = None
    if user_id:
        target_user = await User.find_one(User.id == user_id)
        if not target_user:
            raise HTTPException(status_code=404, detail="User not found")
    if current_user.role != UserRole.ADMIN:
        if user_id and current_user.id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        target_user = current_user
    settings = await _load_attendance_settings()
    if reconcile:
        if current_user.role == UserRole.ADMIN:
            if target_user:
                await _ensure_auto_leaves(target_user, start_date, end_date, settings)
            else:
                users = await User.find(User.is_deleted != True).to_list()
                for u in users:
                    if u.role != UserRole.ADMIN:
                        await _ensure_auto_leaves(u, start_date, end_date, settings)
        else:
            await _ensure_auto_leaves(current_user, start_date, end_date, settings)
    records = []
    total_hours = 0.0
    if target_user:
        users = [target_user]
    else:
        users = await User.find(User.is_deleted != True).to_list()
    day = start_date
    while day <= end_date:
        for u in users:
            if u.role == UserRole.ADMIN:
                continue
            day_records = await Attendance.find(Attendance.user_id == u.id, Attendance.date == day, Attendance.is_deleted != True).to_list()
            summary = _compute_daily_summary(day_records, day)
            day_status = "PRESENT"
            if _is_official_leave(day, settings):
                day_status = "OFF"
            else:
                if summary["total_hours"] <= float(settings.get("absent_hours_threshold") or 0.0):
                    day_status = "ABSENT"
                elif summary["total_hours"] < float(settings.get("half_day_hours_threshold") or 0.0):
                    day_status = "HALF"
            from app.modules.salary.models import LeaveRecord
            leave = await LeaveRecord.find_one(LeaveRecord.user_id == u.id, LeaveRecord.start_date <= day, LeaveRecord.end_date >= day)
            record = {"date": day, "user_id": u.id, "user_name": u.name or u.email, "first_punch_in": summary["first_punch_in"], "last_punch_out": summary["last_punch_out"], "total_hours": summary["total_hours"], "day_status": day_status, "leave_status": leave.status if leave else None}
            records.append(record)
            total_hours += summary["total_hours"]
        day += timedelta(days=1)
    return {"start_date": start_date, "end_date": end_date, "total_hours": round(total_hours, 2), "records": records}
