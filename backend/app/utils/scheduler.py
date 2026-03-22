# backend/app/utils/scheduler.py
"""
scheduler.py — Background task runner using APScheduler.

Runs a job every 60 seconds that checks for meetings starting in ~15 minutes
and dispatches an in-app notification to the client's assigned PM.
"""
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.background import BackgroundScheduler

from app.modules.meetings.models import MeetingSummary, MeetingType
from app.core.enums import GlobalTaskStatus
from app.modules.clients.models import Client
from app.modules.notifications.models import Notification
# SQL na imports jya sudhi MongoDB ma convert na thay tya sudhi comment rakhya che
# from app.core.database import SessionLocal 

# Background thread scheduler (does not block asyncio event loop)
scheduler = BackgroundScheduler(timezone="UTC")


def check_upcoming_meetings():
    """
    Fired every 60 s.
    Finds SCHEDULED meetings whose date falls 14-16 minutes from now
    and creates a Notification for the assigned PM (or owner) if not already sent.
    """
    # db = SessionLocal()  <-- SQL hovathi comment karyu che
    try:
        # The database stores robust UTC timestamps.
        now = datetime.now(timezone.utc)
        window_start = now
        window_end   = now + timedelta(minutes=16)

        """
        # SQL Queries ne comment kari che kem ke te Beanie/MongoDB ma nahi chale
        upcoming = (
            db.query(MeetingSummary)
            .join(Client, MeetingSummary.client_id == Client.id)
            .filter(
                MeetingSummary.status == GlobalTaskStatus.OPEN,
                MeetingSummary.reminder_sent == False,
                MeetingSummary.date >= window_start,
                MeetingSummary.date <= window_end,
            )
            .all()
        )
        """
        pass # Temporary jya sudhi navu logic na lakhiye
        
    except Exception as exc:
        print(f"[Scheduler] Error in check_upcoming_meetings: {exc}")
        # db.rollback()
    finally:
        # db.close()
        pass


def close_finished_meetings():
    """
    Fired every 5 minutes.
    """
    # db = SessionLocal() <-- SQL hovathi comment karyu che
    try:
        now = datetime.now(timezone.utc)
        one_hour_ago = now - timedelta(hours=1)

        """
        expired_meetings = (
            db.query(MeetingSummary)
            .filter(
                MeetingSummary.status == GlobalTaskStatus.OPEN,
                MeetingSummary.date <= one_hour_ago
            )
            .all()
        )
        """
        pass

    except Exception as exc:
        print(f"[Scheduler] Error in close_finished_meetings: {exc}")
        # db.rollback()
    finally:
        # db.close()
        pass


def start_scheduler():
    """Call this from main.py startup to begin background tasks."""
    scheduler.add_job(
        check_upcoming_meetings,
        trigger="interval",
        seconds=60,
        id="meeting_reminders",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.add_job(
        close_finished_meetings,
        trigger="interval",
        minutes=5,
        id="meeting_auto_closer",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.start()
    print("[Scheduler] APScheduler started — checking meetings every 60 s, closing old ones every 5 mins.")


def stop_scheduler():
    """Call this from main.py shutdown."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        print("[Scheduler] APScheduler stopped.")