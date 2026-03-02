from typing import List, Any, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, UTC

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.users.models import User, UserRole
from app.modules.timetable.schemas import TimelineEvent, TimetableResponse
from app.modules.visits.models import Visit
from app.modules.meetings.models import MeetingSummary
from app.modules.todos.models import Todo
from app.modules.shops.models import Shop
from app.modules.clients.models import Client

router = APIRouter()

@router.get("/", response_model=TimetableResponse)
def get_timetable(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Unified timetable view aggregating Visits, Meetings, and Todos for the logged-in user.
    """
    if not start_date:
        start_date = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=30)
    if not end_date:
        end_date = datetime.now(UTC).replace(tzinfo=None) + timedelta(days=30)

    # Ensure naive for DB comparison if columns are naive
    if start_date.tzinfo:
        start_date = start_date.replace(tzinfo=None)
    if end_date.tzinfo:
        end_date = end_date.replace(tzinfo=None)

    events = []

    # 1. Fetch Visits
    visits = db.query(Visit).join(Shop).filter(
        Visit.user_id == current_user.id,
        Visit.visit_date >= start_date,
        Visit.visit_date <= end_date
    ).all()
    for v in visits:
        events.append(TimelineEvent(
            id=v.id,
            title=f"Visit: {v.shop.name}",
            date=v.visit_date,
            event_type="VISIT",
            status=v.status.value if hasattr(v.status, 'value') else str(v.status),
            reference_id=v.shop_id,
            description=v.remarks
        ))

    # 2. Fetch Meetings (Project Managers or Admins)
    # PMs see meetings for their clients.
    meeting_query = db.query(MeetingSummary).join(Client)
    if current_user.role in [UserRole.PROJECT_MANAGER, UserRole.PROJECT_MANAGER_AND_SALES]:
        meeting_query = meeting_query.filter(Client.pm_id == current_user.id)
    elif current_user.role != UserRole.ADMIN:
        # Others might not have 'meetings' in this context unless sales referred? 
        # For now, staff/admins see relevant ones.
        meeting_query = meeting_query.filter(Client.owner_id == current_user.id)

    meetings = meeting_query.filter(
        MeetingSummary.date >= start_date,
        MeetingSummary.date <= end_date
    ).all()
    for m in meetings:
        events.append(TimelineEvent(
            id=m.id,
            title=f"Meeting: {m.client.name}",
            date=m.date,
            event_type="MEETING",
            status=m.status.value if hasattr(m.status, 'value') else str(m.status),
            reference_id=m.client_id,
            description=m.content
        ))

    # 3. Fetch Todos
    todos = db.query(Todo).filter(
        Todo.user_id == current_user.id,
        Todo.due_date >= start_date,
        Todo.due_date <= end_date
    ).all()
    for t in todos:
        events.append(TimelineEvent(
            id=t.id,
            title=f"Todo: {t.title}",
            date=t.due_date,
            event_type="TODO",
            status=t.status.value if hasattr(t.status, 'value') else str(t.status),
            reference_id=t.id,
            description=t.description
        ))

    # Sort by date
    events.sort(key=lambda x: x.date)

    return {"events": events}
