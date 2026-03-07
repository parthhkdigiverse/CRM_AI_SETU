from typing import List, Any, Optional
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, UTC

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.users.models import User, UserRole
from app.modules.timetable.schemas import TimelineEvent, TimetableResponse, TimetableEventCreate, TimetableEventRead, TimetableEventUpdate
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
    user_id = current_user.id if current_user else 0
    event = TimetableEvent(**event_in.model_dump(), user_id=user_id)
    db.add(event)
    db.commit()
    db.refresh(event)
    return event

@router.patch("/{event_id}", response_model=TimetableEventRead)
def update_timetable_event(
    event_id: int,
    event_in: TimetableEventUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    user_id = current_user.id if current_user else 0
    event = db.query(TimetableEvent).filter(
        TimetableEvent.id == event_id,
        TimetableEvent.user_id == user_id
    ).first()
    
    if not event:
        raise HTTPException(status_code=404, detail="Timetable event not found")
        
    update_data = event_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(event, field, value)
        
    db.commit()
    db.refresh(event)
    return event

@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_timetable_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> None:
    user_id = current_user.id if current_user else 0
    event = db.query(TimetableEvent).filter(
        TimetableEvent.id == event_id,
        TimetableEvent.user_id == user_id
    ).first()
    
    if not event:
        raise HTTPException(status_code=404, detail="Timetable event not found")
        
    db.delete(event)
    db.commit()
    from fastapi import Response
    return Response(status_code=status.HTTP_204_NO_CONTENT)

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

    # If end_date has no specific time (defaulting to 00:00:00), expand it to end of day
    if end_date.time() == datetime.min.time():
        end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)

    events = []

    # Helper format date
    def date_str(dt):
        return dt.strftime("%Y-%m-%d") if dt else ""

    # 1. Fetch Visits - show as 1 hour events
    user_id = current_user.id if current_user else 0
    username = (current_user.name or current_user.email or "Unknown User") if current_user else "Demo Admin"
    is_admin = current_user.role == UserRole.ADMIN if current_user else True

    visit_query = db.query(Visit).join(Shop)
    if not is_admin:
        visit_query = visit_query.filter(Visit.user_id == user_id)
    visits = visit_query.filter(
        Visit.visit_date >= start_date,
        Visit.visit_date <= end_date
    ).all()
    
    for v in visits:
        h = v.visit_date.hour if v.visit_date.hour >= 7 else 10 # Default to 10 AM if weird
        # Try to resolve actual user name if available
        real_user = username
        try:
            if v.user:
                real_user = v.user.name or v.user.email
        except:
            pass
        events.append(TimelineEvent(
            id=v.id,
            title=f"Visit: {v.shop.name}",
            date=date_str(v.visit_date),
            user=real_user or "Unknown User",
            sh=h, sm=0, eh=h+1, em=0,
            loc=v.shop.area.name if v.shop.area else "Shop",
            event_type="VISIT",
            status=v.status.value if hasattr(v.status, 'value') else str(v.status),
            reference_id=v.shop_id,
            description=v.remarks
        ))

    # 2. Fetch Meetings (Project Managers or Admins)
    meeting_query = db.query(MeetingSummary).join(Client)
    if current_user and current_user.role in [UserRole.PROJECT_MANAGER, UserRole.PROJECT_MANAGER_AND_SALES]:
        meeting_query = meeting_query.filter(Client.pm_id == current_user.id)
    elif current_user and current_user.role != UserRole.ADMIN:
        meeting_query = meeting_query.filter(Client.owner_id == current_user.id)
    meetings = meeting_query.filter(
        MeetingSummary.date >= start_date,
        MeetingSummary.date <= end_date
    ).all()
    for m in meetings:
        h = m.date.hour if m.date.hour >= 7 else 14
        
        real_user = username
        try:
            if m.client:
                real_user = m.client.owner.name if m.client.owner else username
        except:
            pass

        events.append(TimelineEvent(
            id=m.id,
            title=f"Meeting: {m.client.name}",
            date=date_str(m.date),
            user=real_user or "Unknown User",
            sh=h, sm=0, eh=h+1, em=30,
            loc="Office/Online",
            event_type="MEETING",
            status=m.status.value if hasattr(m.status, 'value') else str(m.status),
            reference_id=m.client_id,
            description=m.content
        ))

    # 3. Fetch Todos - shown as all day or specific time
    todo_query = db.query(Todo)
    if not is_admin:
        todo_query = todo_query.filter(Todo.user_id == user_id)
        
    todos = todo_query.filter(
        Todo.due_date >= start_date,
        Todo.due_date <= end_date
    ).all()
    for t in todos:
        if t.due_date:
            h = t.due_date.hour if t.due_date.hour >= 7 else 9
            
            real_user = t.assigned_to or username
            if not t.assigned_to and is_admin:
                try:
                    if t.user:
                        real_user = t.user.name or t.user.email
                except:
                    pass

            events.append(TimelineEvent(
                id=t.id,
                title=f"Todo: {t.title}",
                date=date_str(t.due_date),
                user=real_user or "Unknown User",
                sh=h, sm=0, eh=h+1, em=0,
                loc=t.related_entity or "",
                event_type="TODO",
                status=t.status.value if hasattr(t.status, 'value') else str(t.status),
                reference_id=t.id,
                description=t.description
            ))

    # 4. Fetch Custom Timetable Events
    tt_query = db.query(TimetableEvent)
    if not is_admin:
        tt_query = tt_query.filter(TimetableEvent.user_id == user_id)
        
    custom_events = tt_query.filter(
        TimetableEvent.date >= start_date.date(),
        TimetableEvent.date <= end_date.date()
    ).all()
    for c in custom_events:
        real_user = c.assignee_name or username
        if not c.assignee_name and is_admin:
            try:
                if c.user:
                    real_user = c.user.name or c.user.email
            except:
                pass
                
        events.append(TimelineEvent(
            id=c.id,
            title=c.title,
            date=date_str(c.date),
            user=real_user or "Unknown User",
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
