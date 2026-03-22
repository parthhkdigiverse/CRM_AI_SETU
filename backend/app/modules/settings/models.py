from typing import Dict, Any
from beanie import Document
from pydantic import Field

class SystemSettings(Document):
    # MongoDB ma JSON mate sidhu dict vapri shakay
    feature_flags: Dict[str, Any] = Field(default_factory=dict)

    class Settings:
        name = "system_settings"  # MongoDB collection nu naam

    class Config:
        json_schema_extra = {
            "example": {
                "feature_flags": {
                    "enable_new_ui": True,
                    "maintenance_mode": False
                }
            }
        }