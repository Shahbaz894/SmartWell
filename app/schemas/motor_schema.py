from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from uuid import UUID
from app.schemas.enums import TriggerType



class MotorStartRequest(BaseModel):
    # Enforce one of the four types
    trigger_type: TriggerType = TriggerType.app
    customer_name: Optional[str] = None

class MotorStopRequest(BaseModel):
    customer_name: Optional[str] = None

class MotorLogResponse(BaseModel):
    id: UUID
    device_id: UUID
    start_time: datetime
    end_time: Optional[datetime]
    duration_minutes: Optional[int]
    trigger_type: TriggerType  # Changed from str to enum
    customer_name: Optional[str] = None
    status: Optional[str] = None

    class Config:
        from_attributes = True