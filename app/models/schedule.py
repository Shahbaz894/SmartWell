# app/models/schedule.py

import uuid
from sqlalchemy import Column, String, Boolean, TIMESTAMP, ForeignKey, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.db.base import Base

class Schedule(Base):
    __tablename__ = "schedules"

    # Changed to String to avoid UUID casting issues in some environments
    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))

    # CRITICAL FIX: Changed from UUID to String(100) to match devices.id
    device_id = Column(
        String(100), 
        ForeignKey("devices.id", ondelete="CASCADE"), 
        nullable=False
    )

    schedule_type = Column(String(20), nullable=False)
    pattern = Column(JSONB, nullable=False)
    is_active = Column(Boolean, default=True)
    schedule_name = Column(String(100))

    created_at = Column(
        TIMESTAMP(timezone=True), 
        server_default=func.now()
    )

    updated_at = Column(
        TIMESTAMP(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now()
    )