import os
import json
from google import genai
from dotenv import load_dotenv

# 1. Force load the .env file from the current environment
load_dotenv()

# 2. Get the key directly from the environment variables
api_key = os.getenv("GOOGLE_API_KEY")

# 3. Initialize the client with the direct key
client = genai.Client(api_key=api_key)

async def generate_ai_summary(meeting_id: int, manual_notes: str = None):
    """
    Generates a structured meeting summary using Google Gemini.

    Priority:
    1. Use manual_notes if provided
    2. Fetch real transcript from Google Drive (via calendar_event_id)
    3. Fall back to generic message
    """
    from app.utils.google_meet import fetch_transcript_from_drive

    # Use passed text as primary source
    source_text = manual_notes
    if not source_text or source_text.strip() == "":
        # Try fetching transcript from Drive using meeting_id as a hint
        # (In the full flow, service.py passes the transcript text directly)
        source_text = fetch_transcript_from_drive(str(meeting_id))

    if not source_text:
        source_text = "No meeting transcript or notes were provided."

    prompt = f"""
    Analyze the following meeting text and provide a concise JSON response.
    
    Meeting Data:
    {source_text}
    
    Return exactly this JSON format:
    {{
        "highlights": ["bullet 1", "bullet 2", "bullet 3"],
        "next_steps": "A concise summary of action items"
    }}
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt
        )
        
        # Clean the response for JSON parsing
        raw_text = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(raw_text)
        
    except Exception as e:
        print(f"[ai_summarizer] Gemini Error: {e}")
        return {
            "highlights": ["AI analysis temporarily unavailable"],
            "next_steps": "Review raw meeting notes or transcript manually."
        }

async def analyze_meeting_content(transcript_or_notes: str):
    return await generate_ai_summary(0, transcript_or_notes)
