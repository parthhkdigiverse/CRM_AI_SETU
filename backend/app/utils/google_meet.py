import google.auth, json, os
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account
from datetime import datetime, timedelta
from typing import Optional

# ── Credential Helper ─────────────────────────────────────────
def get_google_creds(scopes: list):
    """
    Returns service account credentials with the given scopes.
    Loads from GOOGLE_CREDENTIALS_JSON env variable (JSON string),
    or falls back to credentials.json for local dev.
    """
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if creds_json:
        info = json.loads(creds_json)
        return service_account.Credentials.from_service_account_info(info, scopes=scopes)
    return service_account.Credentials.from_service_account_file(
        'credentials.json', scopes=scopes
    )

# ── Google Meet Link Generator ────────────────────────────────
def generate_google_meet_link(
    title: str,
    start_time: datetime,
    description: str = "",
    duration_minutes: int = 60
) -> dict:
    """
    Creates a Google Calendar event with a Meet conference.

    Returns:
        dict: {"meet_link": str, "calendar_event_id": str}
              Returns fallback values on failure.
    """
    try:
        scopes = [
            'https://www.googleapis.com/auth/calendar',
            'https://www.googleapis.com/auth/drive.readonly',
        ]
        creds = get_google_creds(scopes)
        service = build('calendar', 'v3', credentials=creds)

        end_time = start_time + timedelta(minutes=duration_minutes)
        start_iso = start_time.strftime('%Y-%m-%dT%H:%M:%S')
        end_iso   = end_time.strftime('%Y-%m-%dT%H:%M:%S')
        timezone  = 'Asia/Kolkata'

        event = {
            'summary': title,
            'description': description,
            'conferenceData': {
                'createRequest': {
                    'requestId': f"meet_{int(datetime.now().timestamp())}",
                    'conferenceSolutionKey': {'type': 'hangoutsMeet'}
                }
            },
            'start': {'dateTime': start_iso, 'timeZone': timezone},
            'end':   {'dateTime': end_iso,   'timeZone': timezone},
        }

        created_event = service.events().insert(
            calendarId='primary',
            body=event,
            conferenceDataVersion=1
        ).execute()

        return {
            "meet_link":        created_event.get('hangoutLink', 'https://meet.google.com/new'),
            "calendar_event_id": created_event.get('id'),
        }

    except Exception as e:
        print(f"[google_meet] generate_google_meet_link error: {e}")
        return {
            "meet_link":        "https://meet.google.com/new",
            "calendar_event_id": None,
        }

# ── Transcript Fetcher ─────────────────────────────────────────
def fetch_transcript_from_drive(calendar_event_id: str) -> Optional[str]:
    """
    Fetches the Google Meet transcript from Google Drive.

    Google Meet automatically saves transcripts as Google Docs
    in the meeting organiser's Drive when transcription is enabled.

    Strategy:
      1. Look up the Calendar event to read its attachments / description.
      2. Search Drive for a Transcript doc whose name matches the event.
      3. Export that doc as plain text and return it.

    Returns:
        str: Raw transcript text, or None if not found / not ready.
    """
    if not calendar_event_id:
        return None

    scopes = [
        'https://www.googleapis.com/auth/calendar.readonly',
        'https://www.googleapis.com/auth/drive.readonly',
    ]

    try:
        creds = get_google_creds(scopes)

        # ── Step 1: Get event title from Calendar ────────────
        cal_service = build('calendar', 'v3', credentials=creds)
        event = cal_service.events().get(
            calendarId='primary',
            eventId=calendar_event_id
        ).execute()

        event_title = event.get('summary', '')
        print(f"[google_meet] Fetching transcript for event: '{event_title}' (id={calendar_event_id})")

        # ── Step 2: Check event attachments for a transcript doc ──
        attachments = event.get('attachments', [])
        transcript_file_id = None

        for attachment in attachments:
            # Google Meet transcripts have mimeType 'application/vnd.google-apps.document'
            if (
                attachment.get('mimeType') == 'application/vnd.google-apps.document'
                and 'transcript' in attachment.get('title', '').lower()
            ):
                transcript_file_id = attachment.get('fileId')
                print(f"[google_meet] Found transcript attachment: {attachment.get('title')}")
                break

        # ── Step 3: If not in attachments, search Drive by name ──
        if not transcript_file_id:
            drive_service = build('drive', 'v3', credentials=creds)
            # Google Meet saves transcripts with the event title in the name
            query = (
                f"name contains '{event_title}' and "
                "mimeType = 'application/vnd.google-apps.document' and "
                "name contains 'Transcript'"
            )
            results = drive_service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name, createdTime)',
                orderBy='createdTime desc',
                pageSize=1
            ).execute()

            files = results.get('files', [])
            if files:
                transcript_file_id = files[0]['id']
                print(f"[google_meet] Found transcript in Drive: {files[0]['name']}")

        if not transcript_file_id:
            print(f"[google_meet] No transcript found yet for event '{event_title}'.")
            return None

        # ── Step 4: Export the Google Doc as plain text ──────
        drive_service = build('drive', 'v3', credentials=creds)
        exported = drive_service.files().export(
            fileId=transcript_file_id,
            mimeType='text/plain'
        ).execute()

        # export() returns bytes
        transcript_text = exported.decode('utf-8') if isinstance(exported, bytes) else str(exported)
        print(f"[google_meet] Transcript fetched ({len(transcript_text)} chars).")
        return transcript_text

    except HttpError as e:
        print(f"[google_meet] Google API error while fetching transcript: {e}")
        return None
    except Exception as e:
        print(f"[google_meet] Unexpected error in fetch_transcript_from_drive: {e}")
        return None

# ── Legacy Mock (kept for backward compat, no longer used in service.py) ──
def fetch_meeting_transcript(meeting_id: int) -> str:
    """
    DEPRECATED — was a mock. Left here so old imports don't break.
    Use fetch_transcript_from_drive(calendar_event_id) instead.
    """
    return f"[Legacy mock] No real transcript available for meeting_id={meeting_id}."

# ── Google Calendar Reschedule ────────────────────────────────
def reschedule_google_calendar_event(
    calendar_event_id: str,
    new_start_time: datetime,
    duration_minutes: int = 60
) -> bool:
    """
    Updates the start/end time of an existing Google Calendar event.
    """
    if not calendar_event_id:
        return False

    try:
        scopes = ['https://www.googleapis.com/auth/calendar']
        creds = get_google_creds(scopes)
        service = build('calendar', 'v3', credentials=creds)

        # 1. Fetch existing event
        event = service.events().get(calendarId='primary', eventId=calendar_event_id).execute()

        # 2. Update times
        end_time = new_start_time + timedelta(minutes=duration_minutes)
        start_iso = new_start_time.strftime('%Y-%m-%dT%H:%M:%S')
        end_iso   = end_time.strftime('%Y-%m-%dT%H:%M:%S')
        timezone  = 'Asia/Kolkata'

        event['start'] = {'dateTime': start_iso, 'timeZone': timezone}
        event['end']   = {'dateTime': end_iso,   'timeZone': timezone}

        # 3. Patch the event
        service.events().patch(
            calendarId='primary',
            eventId=calendar_event_id,
            body=event
        ).execute()

        return True

    except Exception as e:
        print(f"[google_meet] reschedule_google_calendar_event error: {e}")
        return False
