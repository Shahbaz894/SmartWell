from sqlalchemy import Column, String, TIMESTAMP, Integer, ForeignKey, text
from sqlalchemy.orm import relationship
from app.db.base import Base
import uuid

class MotorLog(Base):
    __tablename__ = "motor_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    device_id = Column(String, ForeignKey("devices.id"), nullable=False)
    # device_id = Column(String,  nullable=False)

    start_time = Column(TIMESTAMP, nullable=False)
    end_time = Column(TIMESTAMP)
    duration_minutes = Column(Integer)

    # manual / schedule
    trigger_type = Column(String(20), nullable=False)

    # ON / OFF
    status = Column(String(10))

    created_at = Column(TIMESTAMP, server_default=text("now()"))

    # 🔗 Relationship
    device = relationship("Device", back_populates="motor_logs")