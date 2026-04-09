# # app/models/schedule.py

# import uuid
# from sqlalchemy import Column, String, Boolean, TIMESTAMP, ForeignKey
# from sqlalchemy.dialects.postgresql import JSONB
# from sqlalchemy.sql import func
# from sqlalchemy.orm import relationship
# from app.db.base import Base

# class Schedule(Base):
#     __tablename__ = "schedules"

#     # UUID as string (safe)
#     id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))

#     # Link to device (SMSWELL1001)
#     device_id = Column(
#         String(50),
#         ForeignKey("devices.id", ondelete="CASCADE"),
#         nullable=False
#     )

#     # e.g. daily / weekly / custom
#     schedule_type = Column(String(20), nullable=False)

#     # JSON structure (timings etc.)
#     pattern = Column(JSONB, nullable=False)

#     is_active = Column(Boolean, default=True)
#     schedule_name = Column(String(100))

#     created_at = Column(
#         TIMESTAMP(timezone=True),
#         server_default=func.now()
#     )

#     updated_at = Column(
#         TIMESTAMP(timezone=True),
#         server_default=func.now(),
#         onupdate=func.now()
#     )

#     # 🔗 Relationship
#     device = relationship("Device", back_populates="schedules")
# app/models/schedule.py

import uuid
from sqlalchemy import Column, String, Boolean, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base

class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))

    device_id = Column(
        String(50),
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        unique=True  # 🔥 ONE schedule per device
    )

    schedule_type = Column(String(20), nullable=False)

    pattern = Column(JSONB, nullable=False)

    is_active = Column(Boolean, default=True)

    schedule_name = Column(String(100))

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    device = relationship("Device", back_populates="schedules")