from sqlalchemy.orm import Session
from app.modules.feedback.models import Feedback, UserFeedback
from app.modules.feedback.schemas import FeedbackCreate, UserFeedbackCreate
from typing import List

class FeedbackService:
    def __init__(self, db: Session):
        self.db = db

    def create_client_feedback(self, feedback_in: FeedbackCreate):
        db_feedback = Feedback(**feedback_in.model_dump())
        self.db.add(db_feedback)
        self.db.commit()
        self.db.refresh(db_feedback)
        return db_feedback

    def get_client_feedbacks(self, client_id: int):
        return self.db.query(Feedback).filter(Feedback.client_id == client_id).all()

    def get_all_client_feedbacks(self):
        return self.db.query(Feedback).all()

    def create_user_feedback(self, user_id: int, feedback_in: UserFeedbackCreate):
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
