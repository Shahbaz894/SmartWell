# app/models/schedule.py

import uuid
from sqlalchemy import Column, String, Boolean, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.db.base import Base


class Schedule(Base):
    __tablename__ = "schedules"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Device relation
    device_id = Column(
        UUID(as_uuid=True),
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False
    )

    # Schedule type
    # monthly_pattern OR daily_slot
    schedule_type = Column(String(20), nullable=False)

    # JSON schedule pattern
    # Example stored structure:
    # {
    #   "month_pattern":[
    #       {"days":7,"state":"ON"},
    #       {"days":3,"state":"OFF"},
    #       {"days":5,"state":"ON"}
    #   ],
    #   "daily_slots":[
    #       {"start":"08:00","end":"12:00"},
    #       {"start":"14:00","end":"16:00"}
    #   ]
    # }
    pattern = Column(JSONB, nullable=False)

    # Enable / disable schedule
    is_active = Column(Boolean, default=True)

    # Schedule name (optional)
    schedule_name = Column(String(100))

    # Metadata
    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now()
    )

    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )