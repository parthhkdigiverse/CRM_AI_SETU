from sqlalchemy.orm import Session
from fastapi import HTTPException, status, Request
from fastapi.encoders import jsonable_encoder
from app.modules.meetings.models import MeetingSummary, MeetingStatus
from app.modules.meetings.schemas import MeetingSummaryCreate, MeetingSummaryUpdateBase
from app.modules.activity_logs.service import ActivityLogger
from app.modules.activity_logs.models import ActionType, EntityType
from app.modules.users.models import User
# Add this import at the top
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
            meeting_data["meet_link"] = generate_google_meet_link()
            
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
        db_meeting = self.get_meeting(meeting_id)
        if not db_meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")
        
        # In a real app, this would call Google Meet API or analyze a transcript.
        # Here we simulate the extraction.
        summary_text = (
            f"Imported Google Meet Summary for Meeting {meeting_id}:\n"
            f"- Discussed project timeline.\n"
            f"- Agreed on next steps."
        )
        
        db_meeting.content = summary_text
        db_meeting.status = MeetingStatus.COMPLETED
        self.db.commit()
        self.db.refresh(db_meeting)
        return db_meeting

    async def initialize_google_meet(self, meeting_id: int):
        db_meeting = self.get_meeting(meeting_id)
        if not db_meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")
        
        from app.utils.google_meet import generate_google_meet_link
        db_meeting.meet_link = generate_google_meet_link()
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
        db_meeting = self.get_meeting(meeting_id)
        if not db_meeting:
            return {"error": "Meeting not found"}

        # Use the actual text you typed in the 'content' field
        source_text = db_meeting.content or "No notes provided."

        try:
            # This calls the real Gemini API with transcript fallback
            analysis = await generate_ai_summary(meeting_id, db_meeting.content)
            return analysis
        except Exception as e:
            print(f"AI Error: {e}")
            return {
                "highlights": ["Error processing AI analysis"],
                "next_steps": "Please check your API key and connection."
            }