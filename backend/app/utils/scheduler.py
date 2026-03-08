"""
scheduler.py — Background task runner using APScheduler.

Runs a job every 60 seconds that checks for meetings starting in ~15 minutes
and dispatches an in-app notification to the client's assigned PM.
"""
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.background import BackgroundScheduler

from app.core.database import SessionLocal
from app.modules.meetings.models import MeetingSummary, MeetingStatus
from app.modules.clients.models import Client
from app.modules.notifications.models import Notification

# Background thread scheduler (does not block asyncio event loop)
scheduler = BackgroundScheduler(timezone="UTC")


def check_upcoming_meetings():
    """
    Fired every 60 s.
    Finds SCHEDULED meetings whose date falls 14-16 minutes from now
    and creates a Notification for the assigned PM (or owner) if not already sent.
    """
    db = SessionLocal()
    try:
        # The database stores robust UTC timestamps.
        now = datetime.now(timezone.utc)
        # Find any meeting starting from 'right now' up to '16 minutes out'
        window_start = now
        window_end   = now + timedelta(minutes=16)

        upcoming = (
            db.query(MeetingSummary)
            .join(Client, MeetingSummary.client_id == Client.id)
            .filter(
                MeetingSummary.status == MeetingStatus.SCHEDULED,
                MeetingSummary.reminder_sent == False,          # noqa: E712
                MeetingSummary.date >= window_start,
                MeetingSummary.date <= window_end,
            )
            .all()
        )

        from app.modules.users.models import User, UserRole
        admins = db.query(User).filter(User.role == UserRole.ADMIN).all()

        for meeting in upcoming:
            client = meeting.client
            
            # Fetch the actual name of the PM for cleaner messaging
            manager_name = "Unknown"
            if client.pm_id:
                pm_user = db.query(User).filter(User.id == client.pm_id).first()
                if pm_user:
                    manager_name = pm_user.name

            # Determine who to notify: PM first, then owner, then skip
            recipient_id = client.pm_id or client.owner_id
            if not recipient_id:
                print(f"[Scheduler] Meeting {meeting.id} has no PM/owner — skipping notification.")
                continue

            # Embedded link payload structure
            message_text = f"Heads up! Your session '{meeting.title}' with {client.name} starts in 15 minutes."
            admin_msg_text = f"Session '{meeting.title}' with {client.name} (Manager: {manager_name}) starts in 15 minutes."

            if meeting.meet_link:
                message_text += f"\nLINK:{meeting.meet_link}"
                admin_msg_text += f"\nLINK:{meeting.meet_link}"

            # Core Recipient Notification (PM/Owner)
            notif = Notification(
                user_id=recipient_id,
                title="⏰ Upcoming Meeting",
                message=message_text,
                is_read=False,
            )
            db.add(notif)
            print(f"[Scheduler] Dispatched 15-min reminder for meeting {meeting.id} → {manager_name} (ID: {recipient_id})")

            # Also cc ALL Admins so they see it in the master feed
            for admin in admins:
                if admin.id == recipient_id:
                    continue  # The admin is already the recipient
                
                admin_notif = Notification(
                    user_id=admin.id,
                    title="⏰ Upcoming Meeting",
                    message=admin_msg_text,
                    is_read=False,
                )
                db.add(admin_notif)

            # Mark reminder as sent to avoid duplicates
            meeting.reminder_sent = True

        db.commit()

    except Exception as exc:
        print(f"[Scheduler] Error in check_upcoming_meetings: {exc}")
        db.rollback()
    finally:
        db.close()


def close_finished_meetings():
    """
    Fired every 5 minutes.
    Finds SCHEDULED meetings that started more than 1 hour ago
    and forcefully marks them as COMPLETED. It also finds their corresponding 
    Notifications in the DB and taints the payload with STATUS:COMPLETED to break the frontend join link.
    """
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        one_hour_ago = now - timedelta(hours=1)

        expired_meetings = (
            db.query(MeetingSummary)
            .filter(
                MeetingSummary.status == MeetingStatus.SCHEDULED,
                MeetingSummary.date <= one_hour_ago
            )
            .all()
        )

        for meeting in expired_meetings:
            meeting.status = MeetingStatus.COMPLETED
            print(f"[Scheduler] Auto-completed expired meeting {meeting.id} ({meeting.title}).")

            if meeting.meet_link:
                # Find notifications containing this link and append the kill switch
                notifs = (
                    db.query(Notification)
                    .filter(Notification.message.like(f"%LINK:{meeting.meet_link}%"))
                    .all()
                )
                for notif in notifs:
                    if "STATUS:COMPLETED" not in notif.message:
                        notif.message += "\nSTATUS:COMPLETED"

        if expired_meetings:
            db.commit()

    except Exception as exc:
        print(f"[Scheduler] Error in close_finished_meetings: {exc}")
        db.rollback()
    finally:
        db.close()


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

