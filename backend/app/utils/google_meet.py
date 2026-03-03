import google.auth
from googleapiclient.discovery import build
from google.oauth2 import service_account

def generate_google_meet_link():
    try:
        # 1. Path to your downloaded Google Service Account JSON
        # Ensure this file is in your backend folder!
        SERVICE_ACCOUNT_FILE = 'credentials.json' 
        
        scopes = ['https://www.googleapis.com/auth/calendar']
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=scopes)
        
        service = build('calendar', 'v3', credentials=creds)

        # 2. Create a dummy event just to get a Meet Link
        event = {
            'summary': 'CRM Strategy Session',
            'conferenceData': {
                'createRequest': {
                    'requestId': 'sample123',
                    'conferenceSolutionKey': {'type': 'hangoutsMeet'}
                }
            },
            'start': {'dateTime': '2026-03-03T20:00:00Z'},
            'end': {'dateTime': '2026-03-03T21:00:00Z'},
        }

        event = service.events().insert(
            calendarId='primary', 
            body=event, 
            conferenceDataVersion=1
        ).execute()

        return event.get('hangoutLink')
    
    except Exception as e:
        print(f"DEBUG ERROR: {e}")
        # FALLBACK: While you are still setting up credentials, 
        # return a temporary link so you don't get the error.
        return "https://meet.google.com/new"

def fetch_meeting_transcript(meeting_id: int):
    """
    Mock function to simulate fetching a Google Meet transcript.
    In a real scenario, this would use the Google Drive/Meet API.
    """
    # Simulate different transcripts for different meetings
    transcripts = {
        1: "The team discussed the new CRM features. Client wants a deep integration with Gemini for automated reporting.",
        2: "Strategy session for Q3. Focus on user retention and field operation efficiency.",
    }
    return transcripts.get(meeting_id, "Standard meeting transcript: Project roadmap was reviewed and milestones were confirmed.")