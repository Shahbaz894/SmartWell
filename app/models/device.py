# app/models/device.py

from sqlalchemy import Column, String, ForeignKey, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base   # ✅ FIXED
import uuid
from sqlalchemy.sql import func


class Device(Base):
    __tablename__ = "devices"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    device_name = Column(String(100), nullable=False)
    device_uid = Column(String(100), unique=True, nullable=False)
    sim_number = Column(String(20))
    location = Column(String(255))
    device_secret = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP, server_default=text("now()"))  # ✅ better