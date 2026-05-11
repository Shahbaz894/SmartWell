from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class DeviceCreate(BaseModel):
    device_name: str = Field(..., min_length=1, max_length=100)
    device_uid: str = Field(..., min_length=1, max_length=100)
    sim_number: Optional[str] = None
    location: Optional[str] = None
    reference_freq: Optional[float] = None


class DeviceUpdate(BaseModel):
    device_name: Optional[str] = None
    sim_number: Optional[str] = None
    location: Optional[str] = None
    reference_freq: Optional[float] = None


class DeviceResponse(BaseModel):
    id: UUID
    user_id: UUID
    device_name: str
    device_uid: str
    sim_number: Optional[str]
    location: Optional[str]
    reference_freq: Optional[float]
    created_at: Optional[datetime]
    is_online: bool = False

    class Config:
        from_attributes = True