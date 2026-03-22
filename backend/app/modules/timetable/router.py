from typing import List, Any, Optional
from fastapi import APIRouter, Depends, Query, status, HTTPException, Response
from datetime import datetime, timedelta, timezone
import datetime as dt
from beanie import PydanticObjectId

# SQLAlchemy kadhi ne Beanie na logic mujab dependencies rakshe
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
async def create_timetable_event(
    event_in: TimetableEventCreate,
    current_user: User = Depends(get_current_user)
) -> Any:
    # SQL .id (int) na badle string check
    user_id = str(current_user.id) if current_user else "0"
    event = TimetableEvent(**event_in.model_dump(), user_id=user_id)
    await event.insert() # SQL .add() -> Beanie .insert()
    return event

@router.patch("/{event_id}", response_model=TimetableEventRead)
async def update_timetable_event(
    event_id: str,
    event_in: TimetableEventUpdate,
    current_user: User = Depends(get_current_user)
) -> Any:
    user_id = str(current_user.id) if current_user else "0"
    
    # query = db.query... logic change to Beanie .get()
    event = await TimetableEvent.get(event_id)
    
    if not event or event.is_deleted:
        raise HTTPException(status_code=404, detail="Timetable event not found")
        
    if current_user and current_user.role != UserRole.ADMIN:
        if event.user_id != user_id:
             raise HTTPException(status_code=403, detail="Not authorized")
    
    update_data = event_in.model_dump(exclude_unset=True)
    await event.update({"$set": update_data}) # SQL .commit() -> Beanie .update()
    return event

@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_timetable_event(
    event_id: str,
    current_user: User = Depends(get_current_user)
) -> None:
    event = await TimetableEvent.get(event_id)
    
    if not event or event.is_deleted:
        raise HTTPException(status_code=404, detail="Timetable event not found")

    # Policy logic silently skipped for soft-delete simplicity in Mongo
    await event.update({"$set": {"is_deleted": True}})
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.get("/", response_model=TimetableResponse)
async def get_timetable(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: User = Depends(get_current_user)
) -> Any:
    if not start_date:
        start_date = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=30)
    if not end_date:
        end_date = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=30)

    events = []

    def date_str(dt_obj):
        return dt_obj.strftime("%Y-%m-%d") if dt_obj else ""

    user_id = str(current_user.id) if current_user else "0"
    username = (current_user.name or current_user.email or "Unknown User") if current_user else "Demo Admin"
    is_admin = current_user.role == UserRole.ADMIN if current_user else True

    # 1. Fetch Visits (SQL Join -> MongoDB Fetch Links)
    visit_filters = {"visit_date": {"$gte": start_date, "$lte": end_date}}
    if not is_admin:
        visit_filters["user_id"] = user_id
    
    visits = await Visit.find(visit_filters, fetch_links=True).to_list()
    
    for v in visits:
        h = v.visit_date.hour if v.visit_date.hour >= 7 else 10
        events.append(TimelineEvent(
            _id=v.id,
            title=f"Visit: {v.shop.name if v.shop else 'Shop'}",
            date=date_str(v.visit_date),
            user=username,
            sh=h, sm=0, eh=h+1, em=0,
            loc=v.shop.area.name if (v.shop and v.shop.area) else "Shop",
            event_type="VISIT",
            status=str(v.status),
            reference_id=str(v.shop_id) if v.shop_id else None,
            description=v.remarks
        ))

    # 2. Fetch Meetings
    m_filters = {"date": {"$gte": start_date, "$lte": end_date}, "is_deleted": False}
    meetings = await MeetingSummary.find(m_filters, fetch_links=True).to_list()
    for m in meetings:
        h = m.date.hour if m.date.hour >= 7 else 14
        events.append(TimelineEvent(
            _id=m.id,
            title=f"Meeting: {m.client.name if m.client else 'Client'}",
            date=date_str(m.date),
            user=username,
            sh=h, sm=0, eh=h+1, em=30,
            loc="Office/Online",
            event_type="MEETING",
            status=str(m.status),
            reference_id=str(m.client_id) if m.client_id else None,
            description=m.content
        ))

    # 3. Fetch Todos
    t_filters = {"due_date": {"$gte": start_date, "$lte": end_date}, "is_deleted": False}
    if not is_admin:
        t_filters["user_id"] = user_id
    
    todos = await Todo.find(t_filters).to_list()
    for t in todos:
        h = t.due_date.hour if t.due_date.hour >= 7 else 9
        sh = t.start_time.hour if t.start_time else h
        events.append(TimelineEvent(
            _id=t.id,
            title=f"Todo: {t.title}",
            date=date_str(t.due_date),
            user=t.assigned_to or username,
            sh=sh, sm=0, eh=sh+1, em=0,
            loc=t.related_entity or "",
            event_type="TODO",
            status=str(t.status),
            reference_id=str(t.id),
            description=t.description
        ))

    # 4. Fetch Custom Timetable Events
    tt_filters = {"date": {"$gte": start_date.date(), "$lte": end_date.date()}, "is_deleted": False}
    if not is_admin:
        tt_filters["user_id"] = user_id
        
    custom_events = await TimetableEvent.find(tt_filters).to_list()
    for c in custom_events:
        events.append(TimelineEvent(
            _id=c.id,
            title=c.title,
            date=date_str(c.date),
            user=c.assignee_name or username,
            sh=c.start_time.hour, sm=c.start_time.minute,
            eh=c.end_time.hour, em=c.end_time.minute,
            loc=c.location or "",
            event_type="TIMETABLE",
            status="PENDING",
            reference_id=str(c.id),
            description=None
        ))

    return {"events": events}