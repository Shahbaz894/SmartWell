# app/schemas/device_schema.py

from pydantic import BaseModel
from datetime import datetime
from typing import Optional

from uuid import UUID


class DeviceCreate(BaseModel):
    device_name: str
    device_uid: str
    sim_number: Optional[str]
    location: Optional[str]


class DeviceUpdate(BaseModel):
    device_name: Optional[str]
    sim_number: Optional[str]
    location: Optional[str]


class DeviceResponse(BaseModel):
    id: str  # Changed from UUID to str
    user_id: UUID  # Changed from UUID to str
    device_name: str
    device_uid: str
    sim_number: Optional[str]
    location: Optional[str]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True

    