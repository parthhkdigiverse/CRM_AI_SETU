from typing import List, Any, Optional
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, UTC

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.users.models import User, UserRole
from app.modules.timetable.schemas import TimelineEvent, TimetableResponse, TimetableEventCreate, TimetableEventRead
from app.modules.timetable.models import TimetableEvent
from app.modules.visits.models import Visit
from app.modules.meetings.models import MeetingSummary
from app.modules.todos.models import Todo
from app.modules.shops.models import Shop
from app.modules.clients.models import Client

router = APIRouter()

@router.post("/", response_model=TimetableEventRead, status_code=status.HTTP_201_CREATED)
def create_timetable_event(
    event_in: TimetableEventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    event = TimetableEvent(**event_in.model_dump(), user_id=current_user.id)
    db.add(event)
    db.commit()
    db.refresh(event)
    return event

@router.get("/", response_model=TimetableResponse)
def get_timetable(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Unified timetable view aggregating Visits, Meetings, Todos, and custom TimetableEvents.
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

    # Helper format date
    def date_str(dt):
        return dt.strftime("%Y-%m-%d") if dt else ""

    # 1. Fetch Visits - show as 1 hour events
    visits = db.query(Visit).join(Shop).filter(
        Visit.user_id == current_user.id,
        Visit.visit_date >= start_date,
        Visit.visit_date <= end_date
    ).all()
    for v in visits:
        h = v.visit_date.hour if v.visit_date.hour >= 7 else 10 # Default to 10 AM if weird
        events.append(TimelineEvent(
            id=v.id,
            title=f"Visit: {v.shop.name}",
            date=date_str(v.visit_date),
            user=current_user.name or "User",
            sh=h, sm=0, eh=h+1, em=0,
            loc=v.shop.area.name if v.shop.area else "Shop",
            event_type="VISIT",
            status=v.status.value if hasattr(v.status, 'value') else str(v.status),
            reference_id=v.shop_id,
            description=v.remarks
        ))

    # 2. Fetch Meetings (Project Managers or Admins)
    meeting_query = db.query(MeetingSummary).join(Client)
    if current_user.role in [UserRole.PROJECT_MANAGER, UserRole.PROJECT_MANAGER_AND_SALES]:
        meeting_query = meeting_query.filter(Client.pm_id == current_user.id)
    elif current_user.role != UserRole.ADMIN:
        meeting_query = meeting_query.filter(Client.owner_id == current_user.id)
    meetings = meeting_query.filter(
        MeetingSummary.date >= start_date,
        MeetingSummary.date <= end_date
    ).all()
    for m in meetings:
        h = m.date.hour if m.date.hour >= 7 else 14
        events.append(TimelineEvent(
            id=m.id,
            title=f"Meeting: {m.client.name}",
            date=date_str(m.date),
            user=current_user.name or "User",
            sh=h, sm=0, eh=h+1, em=30,
            loc="Office/Online",
            event_type="MEETING",
            status=m.status.value if hasattr(m.status, 'value') else str(m.status),
            reference_id=m.client_id,
            description=m.content
        ))

    # 3. Fetch Todos - shown as all day or specific time
    todos = db.query(Todo).filter(
        Todo.user_id == current_user.id,
        Todo.due_date >= start_date,
        Todo.due_date <= end_date
    ).all()
    for t in todos:
        if t.due_date:
            h = t.due_date.hour if t.due_date.hour >= 7 else 9
            events.append(TimelineEvent(
                id=t.id,
                title=f"Todo: {t.title}",
                date=date_str(t.due_date),
                user=t.assigned_to or current_user.name or "User",
                sh=h, sm=0, eh=h+1, em=0,
                loc=t.related_entity or "",
                event_type="TODO",
                status=t.status.value if hasattr(t.status, 'value') else str(t.status),
                reference_id=t.id,
                description=t.description
            ))

    # 4. Fetch Custom Timetable Events
    custom_events = db.query(TimetableEvent).filter(
        TimetableEvent.user_id == current_user.id,
        TimetableEvent.date >= start_date.date(),
        TimetableEvent.date <= end_date.date()
    ).all()
    for c in custom_events:
        events.append(TimelineEvent(
            id=c.id,
            title=c.title,
            date=date_str(c.date),
            user=c.assignee_name or current_user.name or "User",
            sh=c.start_time.hour,
            sm=c.start_time.minute,
            eh=c.end_time.hour,
            em=c.end_time.minute,
            loc=c.location or "",
            event_type="TIMETABLE",
            status="PENDING",
            reference_id=c.id,
            description=None
        ))

    return {"events": events}
