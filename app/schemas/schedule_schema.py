from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel


class ScheduleCreate(BaseModel):
    device_id: str
    schedule_type: str
    pattern: Dict[str, Any]
    schedule_name: Optional[str] = None


class ScheduleUpdate(BaseModel):
    pattern: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    schedule_name: Optional[str] = None


class ScheduleResponse(BaseModel):
    id: UUID
    device_id: str
    schedule_type: str
    pattern: Dict[str, Any]
    is_active: bool
    schedule_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True