"""
Schedule model (no behaviour change — kept clean).

`device_id` stays as String — stores Device.device_uid.
"""
import uuid

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base_class import Base
from sqlalchemy import Column, String, Boolean, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB  # <--- Sahi import path

# Ab baki ka code niche likhein...


class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # STRING — stores Device.device_uid. NOT a UUID.
    device_id = Column(String(100), nullable=False, index=True)

    schedule_type = Column(String(20), nullable=False)
    pattern = Column(JSONB, nullable=False)
    is_active = Column(Boolean, default=True, index=True)
    schedule_name = Column(String(100))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    device = relationship(
        "Device",
        back_populates="schedules",
        primaryjoin="foreign(Schedule.device_id) == Device.device_uid",
    )
