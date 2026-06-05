from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class MotorTimerCreate(BaseModel):
    device_id: str
    customer_name: Optional[str] = None
    start_time: datetime
    stop_time: datetime
    # 🔥 FIXED: Added duration_minutes so Pydantic parses it from Flutter 
    # and satisfies SQLAlchemy's nullable=False constraint.
    duration_minutes: int


class MotorTimerResponse(BaseModel):
    id: int
    device_id: str
    customer_name: Optional[str]
    start_time: datetime
    stop_time: datetime
    duration_minutes: int
    is_running: bool
    is_completed: bool

    class Config:
        from_attributes = True