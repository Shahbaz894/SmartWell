# app/schemas/schedule_schema.py

from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime


class ScheduleCreate(BaseModel):
    device_id: str
    schedule_type: str
    pattern: Dict[str, Any]
    schedule_name: Optional[str]


class ScheduleUpdate(BaseModel):
    pattern: Optional[Dict[str, Any]]
    is_active: Optional[bool]
    schedule_name: Optional[str]


class ScheduleResponse(BaseModel):
    id: str
    device_id: str
    schedule_type: str
    pattern: Dict[str, Any]
    is_active: bool
    schedule_name: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True