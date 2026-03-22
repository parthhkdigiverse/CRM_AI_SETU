from pydantic import BaseModel, ConfigDict, Field
from typing import Dict, Any
from beanie import PydanticObjectId

class SystemSettingsRead(BaseModel):
    id: PydanticObjectId = Field(alias="_id") # MongoDB ni ID mate
    feature_flags: Dict[str, Any]

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True
    )

class SystemSettingsUpdate(BaseModel):
    feature_flags: Dict[str, Any]