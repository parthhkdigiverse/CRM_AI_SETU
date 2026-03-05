from app.core.database import SessionLocal
from app.modules.meetings.models import MeetingSummary

db = SessionLocal()
meeting = db.query(MeetingSummary).filter(MeetingSummary.id == 5).first()
if meeting:
    print(f"Meeting ID: {meeting.id}")
    print(f"Title: {meeting.client.name}")
    print(f"Date: {meeting.date}")
    print(f"Status: {meeting.status}")
else:
    print("Meeting not found")
db.close()
