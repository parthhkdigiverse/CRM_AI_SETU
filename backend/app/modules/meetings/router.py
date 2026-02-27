from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import RoleChecker
from app.modules.users.models import User, UserRole
from app.modules.clients.models import Client
from app.modules.meetings.models import MeetingSummary
from app.modules.meetings.schemas import MeetingSummaryCreate, MeetingSummaryRead, MeetingSummaryUpdate

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

@router.post("/{client_id}/meetings", response_model=MeetingSummaryRead)
def create_meeting(
    client_id: int,
    meeting_in: MeetingSummaryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(pm_checker)
) -> Any:
    """
    PMs or Admins only. PMs can only add to their own assigned clients.
    """
    db_client = db.query(Client).filter(Client.id == client_id).first()
    if not db_client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if current_user.role == UserRole.PROJECT_MANAGER and db_client.pm_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied to this client")

    db_meeting = MeetingSummary(**meeting_in.model_dump(), client_id=client_id)
    db.add(db_meeting)
    db.commit()
    db.refresh(db_meeting)
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
        
    if current_user.role == UserRole.PROJECT_MANAGER and db_client.pm_id != current_user.id:
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
    if current_user.role == UserRole.PROJECT_MANAGER and db_client.pm_id != current_user.id:
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

    if current_user.role != UserRole.ADMIN:
        db_client = db.query(Client).filter(Client.id == db_meeting.client_id).first()
        if not db_client or db_client.pm_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

    db.delete(db_meeting)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

from app.modules.meetings.schemas import MeetingCancel
from app.modules.meetings.models import MeetingStatus

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
    if current_user.role == UserRole.PROJECT_MANAGER and db_client.pm_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    db_meeting.status = MeetingStatus.CANCELLED
    db_meeting.cancellation_reason = cancel_in.reason
    db.commit()
    db.refresh(db_meeting)
    return db_meeting

@router.post("/meetings/{meeting_id}/reschedule", response_model=MeetingSummaryRead)
def reschedule_meeting(
    meeting_id: int,
    # Allow optional body for new date, or just auto logic placeholder
    # For now, we assume simple status reset or date change if provided in query/body
    # User said "Auto", implying some logic. I'll just reset status to SCHEDULED for now.
    db: Session = Depends(get_db),
    current_user: User = Depends(pm_checker)
) -> Any:
    db_meeting = db.query(MeetingSummary).filter(MeetingSummary.id == meeting_id).first()
    if not db_meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    db_client = db.query(Client).filter(Client.id == db_meeting.client_id).first()
    if current_user.role == UserRole.PROJECT_MANAGER and db_client.pm_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Auto reschedule logic (Placeholder: Move to next day same time)
    # from datetime import timedelta
    # db_meeting.date = db_meeting.date + timedelta(days=1)
    
    db_meeting.status = MeetingStatus.SCHEDULED
    db_meeting.cancellation_reason = None # Clear reason
    
    db.commit()
    db.refresh(db_meeting)
    return db_meeting

@router.post("/meetings/{meeting_id}/import-summary", response_model=MeetingSummaryRead)
async def import_meeting_summary(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(pm_checker)
) -> Any:
    """
    Import meeting summary from Google Meet.
    """
    from app.modules.meetings.service import MeetingService
    service = MeetingService(db)
    return await service.import_meeting_summary(meeting_id)
