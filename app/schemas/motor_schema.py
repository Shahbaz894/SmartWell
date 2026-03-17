# app/schemas/motor_schema.py

from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class MotorStartRequest(BaseModel):
    device_id: str
    trigger_type: str  # manual or schedule


class MotorStopRequest(BaseModel):
    device_id: str


class MotorLogResponse(BaseModel):
    id: str
    device_id: str
    start_time: datetime
    end_time: Optional[datetime]
    duration_minutes: Optional[int]
    trigger_type: str

    class Config:
        from_attributes = True