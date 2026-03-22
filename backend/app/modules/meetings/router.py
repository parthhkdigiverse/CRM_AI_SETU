from datetime import date as dt_date, datetime, time, timedelta, timezone
from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from app.core.dependencies import RoleChecker
from app.modules.users.models import User, UserRole
from app.modules.clients.models import Client
from app.modules.meetings.models import MeetingSummary
from app.modules.meetings.service import MeetingService
from app.modules.meetings.schemas import MeetingSummaryCreate, MeetingSummaryRead, MeetingSummaryUpdate, MeetingCancel, MeetingReschedule
from app.core.enums import GlobalTaskStatus

router = APIRouter()
global_router = APIRouter()

admin_checker = RoleChecker([UserRole.ADMIN])
staff_checker = RoleChecker([UserRole.ADMIN, UserRole.SALES, UserRole.TELESALES, UserRole.PROJECT_MANAGER, UserRole.PROJECT_MANAGER_AND_SALES])
pm_checker = RoleChecker([UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.PROJECT_MANAGER_AND_SALES])

PM_SCOPED_ROLES = {UserRole.PROJECT_MANAGER, UserRole.PROJECT_MANAGER_AND_SALES}

@global_router.get("/", response_model=List[MeetingSummaryRead])
async def read_all_meetings(client_id: Optional[str] = None, meeting_type: Optional[str] = None, status: Optional[str] = None, start_date: Optional[dt_date] = None, end_date: Optional[dt_date] = None, current_user: User = Depends(staff_checker)) -> Any:
    query_filter = [MeetingSummary.is_deleted != True]
    if client_id:
        query_filter.append(MeetingSummary.client_id == client_id)
    if meeting_type and meeting_type not in {"ALL", "all"}:
        query_filter.append(MeetingSummary.meeting_type == meeting_type)
    if status and status not in {"ALL", "all"}:
        query_filter.append(MeetingSummary.status == status)
    meetings = await MeetingSummary.find(*query_filter).sort(-MeetingSummary.date).to_list()
    if start_date:
        meetings = [m for m in meetings if m.date and m.date.date() >= start_date]
    if end_date:
        meetings = [m for m in meetings if m.date and m.date.date() <= end_date]
    if current_user.role in PM_SCOPED_ROLES:
        filtered = []
        for m in meetings:
            client = await Client.find_one(Client.id == m.client_id)
            if client and client.pm_id == current_user.id:
                filtered.append(m)
        return filtered
    return meetings

@router.post("/{client_id}/meetings", response_model=MeetingSummaryRead)
async def create_meeting(client_id: str, meeting_in: MeetingSummaryCreate, request: Request, current_user: User = Depends(pm_checker)) -> Any:
    db_client = await Client.find_one(Client.id == client_id)
    if not db_client:
        raise HTTPException(status_code=404, detail="Client not found")
    if current_user and current_user.role in PM_SCOPED_ROLES and db_client.pm_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied to this client")
    service = MeetingService()
    return await service.create_meeting(meeting_in, client_id, current_user, request)

@router.get("/{client_id}/meetings", response_model=List[MeetingSummaryRead])
async def read_client_meetings(client_id: str, current_user: User = Depends(staff_checker)) -> Any:
    db_client = await Client.find_one(Client.id == client_id)
    if not db_client:
        raise HTTPException(status_code=404, detail="Client not found")
    if current_user and current_user.role in PM_SCOPED_ROLES and db_client.pm_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return await MeetingSummary.find(MeetingSummary.client_id == client_id, MeetingSummary.is_deleted != True).to_list()

@router.patch("/meetings/{meeting_id}", response_model=MeetingSummaryRead)
async def update_meeting(meeting_id: str, meeting_in: MeetingSummaryUpdate, current_user: User = Depends(pm_checker)) -> Any:
    db_meeting = await MeetingSummary.find_one(MeetingSummary.id == meeting_id)
    if not db_meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    db_client = await Client.find_one(Client.id == db_meeting.client_id)
    if current_user and current_user.role in PM_SCOPED_ROLES and db_client and db_client.pm_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    update_data = meeting_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_meeting, field, value)
    if update_data.get("status") in [GlobalTaskStatus.COMPLETED, GlobalTaskStatus.DONE, GlobalTaskStatus.CANCELLED]:
        if db_meeting.meet_link:
            from app.modules.notifications.models import Notification
            notifs = await Notification.find(Notification.message.regex(f"LINK:{db_meeting.meet_link}")).to_list()
            for notif in notifs:
                if "STATUS:COMPLETED" not in notif.message:
                    notif.message += "\nSTATUS:COMPLETED"
                    await notif.save()
    await db_meeting.save()
    return db_meeting

@router.delete("/meetings/{meeting_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meeting(meeting_id: str, current_user: User = Depends(pm_checker)):
    db_meeting = await MeetingSummary.find_one(MeetingSummary.id == meeting_id)
    if not db_meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    if current_user and current_user.role != UserRole.ADMIN:
        db_client = await Client.find_one(Client.id == db_meeting.client_id)
        if db_client and db_client.pm_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
    await db_meeting.delete()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@global_router.post("/batch-delete")
async def batch_delete_meetings(ids: List[int], current_user: User = Depends(admin_checker)):
    meetings = await MeetingSummary.find(MeetingSummary.id.in_(ids)).to_list()
    for meeting in meetings:
        await meeting.delete()
    return {"message": f"Successfully deleted {len(meetings)} meetings"}

@router.post("/meetings/{meeting_id}/cancel", response_model=MeetingSummaryRead)
async def cancel_meeting(meeting_id: str, cancel_in: MeetingCancel, current_user: User = Depends(pm_checker)) -> Any:
    db_meeting = await MeetingSummary.find_one(MeetingSummary.id == meeting_id)
    if not db_meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    db_client = await Client.find_one(Client.id == db_meeting.client_id)
    if current_user and current_user.role in PM_SCOPED_ROLES and db_client and db_client.pm_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    if db_meeting.status in [GlobalTaskStatus.COMPLETED, GlobalTaskStatus.DONE]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot cancel a completed meeting.")
    db_meeting.status = GlobalTaskStatus.CANCELLED
    db_meeting.cancellation_reason = cancel_in.reason
    await db_meeting.save()
    return db_meeting

@global_router.post("/{meeting_id}/reschedule", response_model=MeetingSummaryRead)
async def reschedule_meeting_global(meeting_id: str, reschedule_in: MeetingReschedule, request: Request, current_user: User = Depends(pm_checker)) -> Any:
    service = MeetingService()
    return await service.reschedule_meeting(meeting_id=meeting_id, new_date=reschedule_in.new_date, current_user=current_user, request=request)

@global_router.post("/{meeting_id}/import-summary", response_model=MeetingSummaryRead)
async def import_meeting_summary_global(meeting_id: str, current_user: User = Depends(pm_checker)) -> Any:
    service = MeetingService()
    return await service.import_meeting_summary(meeting_id)

@global_router.post("/{meeting_id}/initialize-meet", response_model=MeetingSummaryRead)
async def init_meeting_link_global(meeting_id: str, current_user: User = Depends(pm_checker)) -> Any:
    service = MeetingService()
    return await service.initialize_google_meet(meeting_id)

@global_router.post("/{meeting_id}/generate-ai-summary")
async def trigger_ai_summary_global(meeting_id: str):
    service = MeetingService()
    return await service.get_ai_analysis(meeting_id)
