# app/models/motor_log.py
from sqlalchemy import Column, String, TIMESTAMP, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base
import uuid

class MotorLog(Base):
    __tablename__ = "motor_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    start_time = Column(TIMESTAMP, nullable=False)
    end_time = Column(TIMESTAMP)
    duration_minutes = Column(Integer)
    trigger_type = Column(String(20))  # manual or schedule
    created_at = Column(TIMESTAMP, server_default="now()")