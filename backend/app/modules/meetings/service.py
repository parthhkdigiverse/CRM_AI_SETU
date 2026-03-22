from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status, Request
from fastapi.encoders import jsonable_encoder
from app.modules.meetings.models import MeetingSummary
from app.core.enums import GlobalTaskStatus
from app.modules.meetings.schemas import MeetingSummaryCreate, MeetingSummaryUpdateBase
from app.modules.activity_logs.service import ActivityLogger
from app.modules.activity_logs.models import ActionType, EntityType
from app.modules.users.models import User
from app.utils.ai_summarizer import analyze_meeting_content, generate_ai_summary

class MeetingService:
    def __init__(self):
        self.activity_logger = ActivityLogger()

    async def get_meeting(self, meeting_id: str):
        return await MeetingSummary.find_one(MeetingSummary.id == meeting_id, MeetingSummary.is_deleted != True)

    async def get_meetings(self, skip: int = 0, limit: int = 100):
        return await MeetingSummary.find(MeetingSummary.is_deleted != True).skip(skip).limit(limit).to_list()

    async def create_meeting(self, meeting: MeetingSummaryCreate, client_id: str, current_user: User, request: Request):
        from app.modules.meetings.models import MeetingType
        from app.utils.google_meet import generate_google_meet_link
        meeting_data = meeting.model_dump()
        meeting_data["client_id"] = client_id
        if meeting_data.get("meeting_type") in [MeetingType.GOOGLE_MEET, MeetingType.VIRTUAL]:
            meeting_date = meeting_data.get("date") or datetime.now(timezone.utc)
            result = generate_google_meet_link(title=meeting_data.get("title", "Meeting"), start_time=meeting_date, description=meeting_data.get("content", ""))
            meeting_data["meet_link"] = result.get("meet_link")
            meeting_data["calendar_event_id"] = result.get("calendar_event_id")
        db_meeting = MeetingSummary(**meeting_data)
        await db_meeting.insert()
        from app.modules.todos.models import Todo, TodoPriority
        db_todo = Todo(user_id=current_user.id, title=f"Meeting: {db_meeting.title}", description=db_meeting.content, due_date=db_meeting.date, priority=TodoPriority.MEDIUM, assigned_to=current_user.name or current_user.email, related_entity=f"MEETING:{db_meeting.id}", client_id=client_id)
        await db_todo.insert()
        db_meeting.todo_id = db_todo.id
        await db_meeting.save()
        await self.activity_logger.log_activity(user_id=current_user.id, user_role=current_user.role, action=ActionType.CREATE, entity_type=EntityType.MEETING, entity_id=db_meeting.id, old_data=None, new_data=jsonable_encoder(meeting_data), request=request)
        return db_meeting

    async def update_meeting(self, meeting_id: str, meeting_update: MeetingSummaryUpdateBase, current_user: User, request: Request):
        db_meeting = await self.get_meeting(meeting_id)
        if not db_meeting:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")
        old_data = {"title": db_meeting.title, "content": db_meeting.content, "status": db_meeting.status.value if hasattr(db_meeting.status, 'value') else str(db_meeting.status)}
        update_data = meeting_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_meeting, key, value)
        await db_meeting.save()
        if db_meeting.todo_id:
            from app.modules.todos.models import Todo, TodoStatus
            db_todo = await Todo.find_one(Todo.id == db_meeting.todo_id)
            if db_todo:
                if "title" in update_data:
                    db_todo.title = f"Meeting: {db_meeting.title}"
                if "content" in update_data:
                    db_todo.description = db_meeting.content
                if "status" in update_data:
                    if update_data["status"] in [GlobalTaskStatus.COMPLETED, GlobalTaskStatus.DONE]:
                        db_todo.status = TodoStatus.COMPLETED
                await db_todo.save()
        new_data = {k: getattr(db_meeting, k) for k in old_data.keys()}
        new_data["status"] = new_data["status"].value if hasattr(new_data["status"], 'value') else str(new_data["status"])
        action = ActionType.CANCEL if "status" in update_data and update_data["status"] == GlobalTaskStatus.CANCELLED else ActionType.UPDATE
        await self.activity_logger.log_activity(user_id=current_user.id, user_role=current_user.role, action=action, entity_type=EntityType.MEETING, entity_id=meeting_id, old_data=old_data, new_data=new_data, request=request)
        return db_meeting

    async def import_meeting_summary(self, meeting_id: str):
        db_meeting = await self.get_meeting(meeting_id)
        if not db_meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")
        from app.utils.google_meet import fetch_transcript_from_drive
        transcript_text = None
        if db_meeting.calendar_event_id:
            transcript_text = fetch_transcript_from_drive(db_meeting.calendar_event_id)
        if not transcript_text:
            transcript_text = db_meeting.content or "No transcript or notes available."
        else:
            db_meeting.transcript = transcript_text
        ai_result = await generate_ai_summary(meeting_id, transcript_text)
        db_meeting.ai_summary = ai_result
        db_meeting.status = GlobalTaskStatus.COMPLETED
        await db_meeting.save()
        return db_meeting

    async def initialize_google_meet(self, meeting_id: str):
        db_meeting = await self.get_meeting(meeting_id)
        if not db_meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")
        from app.utils.google_meet import generate_google_meet_link
        meeting_date = db_meeting.date or datetime.now(timezone.utc)
        result = generate_google_meet_link(title=db_meeting.title, start_time=meeting_date, description=db_meeting.content or "")
        db_meeting.meet_link = result.get("meet_link")
        db_meeting.calendar_event_id = result.get("calendar_event_id")
        await db_meeting.save()
        return db_meeting

    async def get_ai_analysis(self, meeting_id: str):
        db_meeting = await self.get_meeting(meeting_id)
        if not db_meeting:
            return {"error": "Meeting not found"}
        if db_meeting.ai_summary:
            return db_meeting.ai_summary
        source_text = db_meeting.transcript or db_meeting.content or "No notes provided."
        try:
            analysis = await generate_ai_summary(meeting_id, source_text)
            db_meeting.ai_summary = analysis
            await db_meeting.save()
            return analysis
        except Exception as e:
            print(f"[MeetingService] AI Error: {e}")
            return {"highlights": ["Error processing AI analysis"], "next_steps": "Please check your API key and connection."}

    async def reschedule_meeting(self, meeting_id: str, new_date: datetime, current_user: User, request: Request):
        db_meeting = await self.get_meeting(meeting_id)
        if not db_meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")
        old_data = {"date": db_meeting.date.isoformat() if db_meeting.date else None, "status": db_meeting.status.value if hasattr(db_meeting.status, 'value') else str(db_meeting.status)}
        db_meeting.date = new_date
        db_meeting.status = GlobalTaskStatus.SCHEDULED
        db_meeting.cancellation_reason = None
        await db_meeting.save()
        if db_meeting.todo_id:
            from app.modules.todos.models import Todo
            db_todo = await Todo.find_one(Todo.id == db_meeting.todo_id)
            if db_todo:
                db_todo.due_date = new_date
                await db_todo.save()
        if db_meeting.calendar_event_id:
            from app.utils.google_meet import reschedule_google_calendar_event
            reschedule_google_calendar_event(db_meeting.calendar_event_id, new_date)
        await self.activity_logger.log_activity(user_id=current_user.id, user_role=current_user.role, action=ActionType.UPDATE, entity_type=EntityType.MEETING, entity_id=meeting_id, old_data=old_data, new_data={"date": new_date.isoformat(), "status": GlobalTaskStatus.SCHEDULED.value}, request=request)
        return db_meeting
