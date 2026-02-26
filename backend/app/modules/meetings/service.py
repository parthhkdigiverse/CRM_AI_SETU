from sqlalchemy.orm import Session
from fastapi import HTTPException, status, Request
from app.modules.meetings.models import MeetingSummary, MeetingStatus
from app.modules.meetings.schemas import MeetingSummaryCreate, MeetingSummaryUpdateBase
from app.modules.activity_logs.service import ActivityLogger
from app.modules.activity_logs.models import ActionType, EntityType
from app.modules.users.models import User

class MeetingService:
    def __init__(self, db: Session):
        self.db = db
        self.activity_logger = ActivityLogger(db)

    def get_meeting(self, meeting_id: int):
        return self.db.query(MeetingSummary).filter(MeetingSummary.id == meeting_id).first()

    def get_meetings(self, skip: int = 0, limit: int = 100):
        return self.db.query(MeetingSummary).offset(skip).limit(limit).all()

    async def create_meeting(self, meeting: MeetingSummaryCreate, current_user: User, request: Request):
        db_meeting = MeetingSummary(**meeting.model_dump())

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
            new_data=meeting.model_dump(),

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
