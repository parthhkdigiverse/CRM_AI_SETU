import google.generativeai as genai
import json
from app.core.config import settings
from app.utils.google_meet import fetch_meeting_transcript

# Configuration
genai.configure(api_key=settings.google_api_key)

async def generate_ai_summary(meeting_id: int, manual_notes: str = None):
    """
    Generates a structured meeting summary using Google Gemini.
    Falls back to meeting transcript if manual notes are not provided.
    """
    # 1. Determine the source text for analysis
    source_text = manual_notes
    if not source_text or source_text.strip() == "":
        source_text = fetch_meeting_transcript(meeting_id)
    
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    Analyze the following meeting text (manual notes or transcript) and provide a concise JSON response.
    
    Meeting Data:
    {source_text}
    
    Return exactly this JSON format:
    {{
        "highlights": ["bullet 1", "bullet 2", "bullet 3"],
        "next_steps": "A concise summary of action items"
    }}
    """
    
    try:
        response = model.generate_content(prompt)
        # Clean the response to ensure it's valid JSON (remove markdown code blocks)
        raw_text = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(raw_text)
    except Exception as e:
        print(f"AI/Gemini Error: {e}")
        return {
            "highlights": ["AI analysis temporarily unavailable"],
            "next_steps": "Review raw meeting notes or transcript manually."
        }

# For backward compatibility or alternative use
async def analyze_meeting_content(transcript_or_notes: str):
    return await generate_ai_summary(0, transcript_or_notes)