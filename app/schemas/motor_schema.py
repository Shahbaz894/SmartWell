from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from uuid import UUID

class TriggerType(str, Enum):
    APP = "app"
    SCHEDULE = "schedule"
    TIMER = "timer"
    PHYSICAL = "physical"

class MotorStartRequest(BaseModel):
    # Enforce one of the four types
    trigger_type: TriggerType = TriggerType.APP
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