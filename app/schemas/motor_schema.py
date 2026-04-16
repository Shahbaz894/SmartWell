# app/schemas/motor_schema.py

from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class MotorStartRequest(BaseModel):
    trigger_type: str  # manual or schedule
    customer_name: Optional[str] = None


class MotorStopRequest(BaseModel):
    customer_name: Optional[str] = None


class MotorLogResponse(BaseModel):
    id: str
    device_id: str
    start_time: datetime
    end_time: Optional[datetime]
    duration_minutes: Optional[int]
    trigger_type: str
    customer_name: Optional[str] = None
    status: Optional[str] = None

    class Config:
        from_attributes = True