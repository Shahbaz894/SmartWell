
# app/models/motor_log.py
from sqlalchemy import Column, String, TIMESTAMP, Integer
from app.db.base import Base
from datetime import datetime
import uuid

class MotorLog(Base):
    __tablename__ = "motor_logs"

    # Use a string ID for simplicity
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Device ID stored as string to match actual ESP32 device ID
    device_id = Column(String, nullable=False)

    start_time = Column(TIMESTAMP, nullable=False)
    end_time = Column(TIMESTAMP)
    duration_minutes = Column(Integer)
    trigger_type = Column(String(20))  # manual or schedule
    created_at = Column(TIMESTAMP, server_default="now()")