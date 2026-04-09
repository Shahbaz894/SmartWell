# app/schemas/device_schema.py

from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from uuid import UUID


# -----------------------
# Create Device
# -----------------------
class DeviceCreate(BaseModel):
    id: str  # 👈 IMPORTANT (SMSWELL1001 comes from frontend)
    device_name: str
    device_uid: str
    device_secret: str  # 👈 required (matches model)
    sim_number: Optional[str] = None
    location: Optional[str] = None


# -----------------------
# Update Device
# -----------------------
class DeviceUpdate(BaseModel):
 device_name: Optional[str] = None
 sim_number: Optional[str] = None
 location: Optional[str] = None
 reference_freq: Optional[float] = None


# -----------------------
# Response Schema
# -----------------------
class DeviceResponse(BaseModel):
    id: str  # SMSWELL1001
    user_id: UUID  # correct (matches DB)
    device_name: str
    device_uid: str
    device_secret: str  # 👈 include if needed (optional: hide for security)
    sim_number: Optional[str]
    location: Optional[str]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True