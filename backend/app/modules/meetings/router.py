from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import RoleChecker
from app.modules.users.models import User, UserRole
from app.modules.clients.models import Client
from app.modules.meetings.models import MeetingSummary
from app.modules.meetings.service import MeetingService
from app.modules.meetings.schemas import MeetingSummaryCreate, MeetingSummaryRead, MeetingSummaryUpdate, MeetingCancel, MeetingReschedule
from app.modules.meetings.models import MeetingStatus

router = APIRouter()

# Role definitions
admin_checker = RoleChecker([UserRole.ADMIN])
staff_checker = RoleChecker([
    UserRole.ADMIN, 
    UserRole.SALES, 
    UserRole.TELESALES, 
    UserRole.PROJECT_MANAGER, 
    UserRole.PROJECT_MANAGER_AND_SALES
])
pm_checker = RoleChecker([
    UserRole.ADMIN, 
    UserRole.PROJECT_MANAGER, 
    UserRole.PROJECT_MANAGER_AND_SALES
])

global_router = APIRouter()

@global_router.get("/", response_model=List[MeetingSummaryRead])
def read_all_meetings(
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    """
    Get all meetings. PMs only see meetings for their assigned clients.
    """
    query = db.query(MeetingSummary).join(Client)
    
    if current_user.role == UserRole.PROJECT_MANAGER:
        query = query.filter(Client.pm_id == current_user.id)
    
    return query.all()

@router.post("/{client_id}/meetings", response_model=MeetingSummaryRead)
async def create_meeting(
    client_id: int,
    meeting_in: MeetingSummaryCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(pm_checker)
) -> Any:
    """
    PMs or Admins only. PMs can only add to their own assigned clients.
    """
    db_client = db.query(Client).filter(Client.id == client_id).first()
    if not db_client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if current_user and current_user.role == UserRole.PROJECT_MANAGER and db_client.pm_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied to this client")

    # Use the service to handle business logic (like Meet link generation)
    service = MeetingService(db)
    # Inject client_id into payload for service
    meeting_data = meeting_in.model_dump()
    meeting_data["client_id"] = client_id
    
    from app.modules.meetings.schemas import MeetingSummaryBase
    # We might need a slightly different schema or just pass dict
    # Let's just update the service to handle it or pass manually
    # However, create_meeting in service expects MeetingSummaryCreate
    # Let's just manually set client_id on the model after creation or fix service
    # I will fix service create_meeting to accept client_id
    db_meeting = await service.create_meeting(meeting_in, client_id, current_user, request)
    return db_meeting

@router.get("/{client_id}/meetings", response_model=List[MeetingSummaryRead])
def read_client_meetings(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_checker)
) -> Any:
    db_client = db.query(Client).filter(Client.id == client_id).first()
    if not db_client:
        raise HTTPException(status_code=404, detail="Client not found")
        
    if current_user and current_user.role == UserRole.PROJECT_MANAGER and db_client.pm_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return db.query(MeetingSummary).filter(MeetingSummary.client_id == client_id).all()

@router.patch("/meetings/{meeting_id}", response_model=MeetingSummaryRead)
def update_meeting(
    meeting_id: int,
    meeting_in: MeetingSummaryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(pm_checker)
) -> Any:
    db_meeting = db.query(MeetingSummary).filter(MeetingSummary.id == meeting_id).first()
    if not db_meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    db_client = db.query(Client).filter(Client.id == db_meeting.client_id).first()
    if current_user and current_user.role == UserRole.PROJECT_MANAGER and db_client.pm_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    update_data = meeting_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_meeting, field, value)
    
    db.add(db_meeting)
    db.commit()
    db.refresh(db_meeting)
    return db_meeting

@router.delete("/meetings/{meeting_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_meeting(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(pm_checker)
):
    db_meeting = db.query(MeetingSummary).filter(MeetingSummary.id == meeting_id).first()
    if not db_meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if current_user and current_user.role != UserRole.ADMIN:
        db_client = db.query(Client).filter(Client.id == db_meeting.client_id).first()
        if not db_client or db_client.pm_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

    db.delete(db_meeting)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.post("/meetings/{meeting_id}/cancel", response_model=MeetingSummaryRead)
def cancel_meeting(
    meeting_id: int,
    cancel_in: MeetingCancel,
    db: Session = Depends(get_db),
    current_user: User = Depends(pm_checker)
) -> Any:
    db_meeting = db.query(MeetingSummary).filter(MeetingSummary.id == meeting_id).first()
    if not db_meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    db_client = db.query(Client).filter(Client.id == db_meeting.client_id).first()
    if current_user and current_user.role == UserRole.PROJECT_MANAGER and db_client.pm_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Business Logic: Cannot cancel a finished meeting
    if db_meeting.status in [MeetingStatus.COMPLETED, MeetingStatus.DONE]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Cannot cancel a completed meeting."
        )

    db_meeting.status = MeetingStatus.CANCELLED
    db_meeting.cancellation_reason = cancel_in.reason
    db.commit()
    db.refresh(db_meeting)
    return db_meeting

# --- GLOBAL WRAPPERS FOR MEETING ACTIONS ---

@global_router.post("/{meeting_id}/reschedule", response_model=MeetingSummaryRead)
async def reschedule_meeting_global(
    meeting_id: int,
    reschedule_in: MeetingReschedule,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(pm_checker)
) -> Any:
    service = MeetingService(db)
    return await service.reschedule_meeting(
        meeting_id=meeting_id,
        new_date=reschedule_in.new_date,
        current_user=current_user,
        request=request
    )

@global_router.post("/{meeting_id}/import-summary", response_model=MeetingSummaryRead)
async def import_meeting_summary_global(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(pm_checker)
) -> Any:
    service = MeetingService(db)
    return await service.import_meeting_summary(meeting_id)

@global_router.post("/{meeting_id}/initialize-meet", response_model=MeetingSummaryRead)
async def init_meeting_link_global(
    meeting_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(pm_checker)
) -> Any:
    service = MeetingService(db)
    return await service.initialize_google_meet(meeting_id)

@global_router.post("/{meeting_id}/generate-ai-summary")
async def trigger_ai_summary_global(meeting_id: int, db: Session = Depends(get_db)):
    service = MeetingService(db)
    return await service.get_ai_analysis(meeting_id)
    
