# backend/app/modules/feedback/service.py
from sqlalchemy.orm import Session
from app.modules.feedback.models import Feedback, UserFeedback
from app.modules.feedback.schemas import FeedbackCreate, UserFeedbackCreate
from typing import List

class FeedbackService:
    def __init__(self, db: Session):
        self.db = db

    def create_client_feedback(self, feedback_in: FeedbackCreate):
        data = feedback_in.model_dump()
        # Handle field name mapping if needed (client_name from client, s_rating from rating)
        db_feedback = Feedback(**data)
        self.db.add(db_feedback)
        self.db.commit()
        self.db.refresh(db_feedback)
        return db_feedback

    def _attach_roles(self, feedbacks: List[Feedback]):
        from app.modules.users.models import User
        if not feedbacks:
            return feedbacks
            
        ref_codes = list({fb.referral_code for fb in feedbacks if fb.referral_code})
        role_map = {}
        if ref_codes:
            users = self.db.query(User).filter(User.referral_code.in_(ref_codes)).all()
            for u in users:
                if u.referral_code:
                    role_str = u.role.value if hasattr(u.role, 'value') else str(u.role)
                    role_map[u.referral_code] = role_str.replace("_", " ").title()
                    
        for fb in feedbacks:
            fb.agent_role = role_map.get(fb.referral_code, "Sales Executive")
            
        return feedbacks

    def get_client_feedbacks(self, client_id: str):
        feedbacks = self.db.query(Feedback).filter(Feedback.client_id == client_id).all()
        return self._attach_roles(feedbacks)

    def get_all_client_feedbacks(self):
        feedbacks = self.db.query(Feedback).order_by(Feedback.id.desc()).all()
        return self._attach_roles(feedbacks)

    def create_user_feedback(self, user_id: str, feedback_in: UserFeedbackCreate):
        db_feedback = UserFeedback(
            **feedback_in.model_dump(),
            user_id=user_id
        )
        self.db.add(db_feedback)
        self.db.commit()
        self.db.refresh(db_feedback)
        return db_feedback

    def get_user_feedbacks(self):
        return self.db.query(UserFeedback).all()

    def delete_feedback(self, feedback_id: int):
        db_feedback = self.db.query(Feedback).filter(Feedback.id == feedback_id).first()
        if not db_feedback:
            raise ValueError(f"Feedback with id {feedback_id} not found")
        self.db.delete(db_feedback)
        self.db.commit()
        return True
