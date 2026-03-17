# app/schemas/device_schema.py

from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class DeviceCreate(BaseModel):
    device_name: str
    device_uid: str
    sim_number: Optional[str]
    location: Optional[str]


class DeviceUpdate(BaseModel):
    device_name: Optional[str]
    sim_number: Optional[str]
    location: Optional[str]


from pydantic import BaseModel
from uuid import UUID
from typing import Optional
from datetime import datetime

class DeviceResponse(BaseModel):
    id: UUID
    user_id: UUID
    device_name: str
    device_uid: str
    sim_number: Optional[str]
    location: Optional[str]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True   # ✅ IMPORTANT (Pydantic v2)