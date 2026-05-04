# app/schemas/motor_schema.py

from pydantic import BaseModel
from datetime import datetime
from typing import Optional

from uuid import UUID  


class MotorStartRequest(BaseModel):
    trigger_type: str  # manual or schedule
    customer_name: Optional[str] = None


class MotorStopRequest(BaseModel):
    customer_name: Optional[str] = None


class MotorLogResponse(BaseModel):
    id: UUID
    device_id: UUID
    start_time: datetime
    end_time: Optional[datetime]
    duration_minutes: Optional[int]
    trigger_type: str
    customer_name: Optional[str] = None
    status: Optional[str] = None

    class Config:
        from_attributes = True