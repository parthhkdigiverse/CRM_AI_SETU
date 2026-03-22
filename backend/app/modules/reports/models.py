from beanie import Document
from typing import Optional
from datetime import datetime, timezone

class PerformanceNote(Document):
    employee_id: str
    created_by_id: str
    note: str
    created_at: datetime = datetime.now(timezone.utc)

    class Settings:
        name = "performance_notes"
