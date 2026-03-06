from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException, status, Request
from fastapi.encoders import jsonable_encoder
from app.modules.meetings.models import MeetingSummary, MeetingStatus
from app.modules.meetings.schemas import MeetingSummaryCreate, MeetingSummaryUpdateBase
from app.modules.activity_logs.service import ActivityLogger
from app.modules.activity_logs.models import ActionType, EntityType
from app.modules.users.models import User
from app.utils.ai_summarizer import analyze_meeting_content, generate_ai_summary

class MeetingService:
    def __init__(self, db: Session):
        self.db = db
        self.activity_logger = ActivityLogger(db)

    def get_meeting(self, meeting_id: int):
        return self.db.query(MeetingSummary).filter(MeetingSummary.id == meeting_id).first()

    def get_meetings(self, skip: int = 0, limit: int = 100):
        return self.db.query(MeetingSummary).offset(skip).limit(limit).all()

    async def create_meeting(self, meeting: MeetingSummaryCreate, client_id: int, current_user: User, request: Request):
        from app.modules.meetings.models import MeetingType
        from app.utils.google_meet import generate_google_meet_link
        
        meeting_data = meeting.model_dump()
        meeting_data["client_id"] = client_id
        
        # Generate Meet link if type is Google Meet or Virtual
        if meeting_data.get("meeting_type") in [MeetingType.GOOGLE_MEET, MeetingType.VIRTUAL]:
            meeting_date = meeting_data.get("date") or datetime.now()
            result = generate_google_meet_link(
                title=meeting_data.get("title", "Meeting"),
                start_time=meeting_date,
                description=meeting_data.get("content", "")
            )
            # Unpack both values from the returned dict
            meeting_data["meet_link"] = result.get("meet_link")
            meeting_data["calendar_event_id"] = result.get("calendar_event_id")
            
        db_meeting = MeetingSummary(**meeting_data)

        self.db.add(db_meeting)
        self.db.commit()
        self.db.refresh(db_meeting)

        await self.activity_logger.log_activity(
            user_id=current_user.id,
            user_role=current_user.role,
            action=ActionType.CREATE,
            entity_type=EntityType.MEETING,
            entity_id=db_meeting.id,
            old_data=None,
            new_data=jsonable_encoder(meeting_data),
            request=request
        )

        return db_meeting

    async def update_meeting(self, meeting_id: int, meeting_update: MeetingSummaryUpdateBase, current_user: User, request: Request):
        db_meeting = self.get_meeting(meeting_id)
        if not db_meeting:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")

        old_data = {
            "title": db_meeting.title,
            "content": db_meeting.content,
            "status": db_meeting.status.value if hasattr(db_meeting.status, 'value') else str(db_meeting.status)
        }

        update_data = meeting_update.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            setattr(db_meeting, key, value)

        self.db.commit()
        self.db.refresh(db_meeting)

        new_data = {k: getattr(db_meeting, k) for k in old_data.keys()}
        new_data["status"] = new_data["status"].value if hasattr(new_data["status"], 'value') else str(new_data["status"])

        # Determine action type if status changed to CANCEL
        action = ActionType.UPDATE
        if "status" in update_data and update_data["status"] == MeetingStatus.CANCELLED:
             action = ActionType.CANCEL

        await self.activity_logger.log_activity(
            user_id=current_user.id,
            user_role=current_user.role,
            action=action,
            entity_type=EntityType.MEETING,
            entity_id=meeting_id,
            old_data=old_data,
            new_data=new_data,
            request=request
        )

        return db_meeting
    async def import_meeting_summary(self, meeting_id: int):
        """
        Fetches the real Google Meet transcript from Drive, runs it through
        Gemini AI, and stores the results in transcript + ai_summary columns.
        """
        db_meeting = self.get_meeting(meeting_id)
        if not db_meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")
        
        from app.utils.google_meet import fetch_transcript_from_drive

        # Step 1: Try to get real transcript from Google Drive
        transcript_text = None
        if db_meeting.calendar_event_id:
            transcript_text = fetch_transcript_from_drive(db_meeting.calendar_event_id)

        # Step 2: Fallback to manual notes if no transcript available yet
        if not transcript_text:
            transcript_text = db_meeting.content or "No transcript or notes available."
            print(f"[MeetingService] No Drive transcript found for meeting {meeting_id}, using manual notes.")
        else:
            # Persist the raw transcript
            db_meeting.transcript = transcript_text

        # Step 3: Generate AI summary with Gemini
        ai_result = await generate_ai_summary(meeting_id, transcript_text)

        # Step 4: Persist everything and mark as COMPLETED
        db_meeting.ai_summary = ai_result
        db_meeting.status = MeetingStatus.COMPLETED
        self.db.commit()
        self.db.refresh(db_meeting)
        return db_meeting

    async def initialize_google_meet(self, meeting_id: int):
        db_meeting = self.get_meeting(meeting_id)
        if not db_meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")
        
        from app.utils.google_meet import generate_google_meet_link
        from datetime import datetime
        
        meeting_date = db_meeting.date or datetime.now()
        result = generate_google_meet_link(
            title=db_meeting.title,
            start_time=meeting_date,
            description=db_meeting.content or ""
        )
        # Persist both link and calendar event ID
        db_meeting.meet_link = result.get("meet_link")
        db_meeting.calendar_event_id = result.get("calendar_event_id")
        self.db.commit()
        self.db.refresh(db_meeting)
        return db_meeting

    # async def get_real_ai_summary(self, meeting_id: int):
    #     db_meeting = self.get_meeting(meeting_id)
    #     if not db_meeting:
    #         raise HTTPException(status_code=404, detail="Meeting not found")

    #     # 1. Get the actual transcript or notes
    #     meeting_content = db_meeting.content or "No notes provided for this session."

    #     # 2. Call your AI Utility (Placeholder for real Gemini call)
    #     # In the next step, we can connect this to the real Gemini API
    #     highlights = [
    #         f"Discussed: {db_meeting.title}",
    #         "Reviewed client requirements for 'Antigravity' integration.",
    #         "Confirmed budget and project timeline."
    #     ]
    #     next_steps = "Follow up with a detailed proposal by EOD Friday."

    #     return {
    #         "highlights": highlights,
    #         "next_steps": next_steps
    #     }

    # Inside your MeetingService class
    async def get_ai_analysis(self, meeting_id: int):
        """
        Returns the stored ai_summary if available, otherwise generates one
        from the transcript or manual notes.
        """
        db_meeting = self.get_meeting(meeting_id)
        if not db_meeting:
            return {"error": "Meeting not found"}

        # Return cached result if already stored
        if db_meeting.ai_summary:
            return db_meeting.ai_summary

        # Build source text: prefer stored transcript, fall back to manual notes
        source_text = db_meeting.transcript or db_meeting.content or "No notes provided."

        try:
            analysis = await generate_ai_summary(meeting_id, source_text)
            # Cache the result to avoid repeated Gemini calls
            db_meeting.ai_summary = analysis
            self.db.commit()
            return analysis
        except Exception as e:
            print(f"[MeetingService] AI Error: {e}")
            return {
                "highlights": ["Error processing AI analysis"],
                "next_steps": "Please check your API key and connection."
            }

    async def reschedule_meeting(self, meeting_id: int, new_date: datetime, current_user: User, request: Request):
        db_meeting = self.get_meeting(meeting_id)
        if not db_meeting:
             raise HTTPException(status_code=404, detail="Meeting not found")

        old_data = {
            "date": db_meeting.date.isoformat() if db_meeting.date else None,
            "status": db_meeting.status.value if hasattr(db_meeting.status, 'value') else str(db_meeting.status)
        }

        # 1. Update Meeting in Local DB
        db_meeting.date = new_date
        db_meeting.status = MeetingStatus.SCHEDULED
        db_meeting.cancellation_reason = None
        self.db.commit()
        self.db.refresh(db_meeting)

        # 2. Sync with Google Calendar if event exists
        if db_meeting.calendar_event_id:
            from app.utils.google_meet import reschedule_google_calendar_event
            reschedule_google_calendar_event(db_meeting.calendar_event_id, new_date)

        # 3. Log activity
        await self.activity_logger.log_activity(
            user_id=current_user.id,
            user_role=current_user.role,
            action=ActionType.UPDATE,
            entity_type=EntityType.MEETING,
            entity_id=meeting_id,
            old_data=old_data,
            new_data={"date": new_date.isoformat(), "status": MeetingStatus.SCHEDULED.value},
            request=request
        )

        return db_meeting