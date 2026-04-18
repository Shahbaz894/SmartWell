from sqlalchemy import Column, String, TIMESTAMP, Integer, ForeignKey, text
from sqlalchemy.orm import relationship
from app.db.base import Base
import uuid


class MotorLog(Base):
    __tablename__ = "motor_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    device_id = Column(String, ForeignKey("devices.id"), nullable=False)

    start_time = Column(TIMESTAMP, nullable=False)
    end_time = Column(TIMESTAMP, nullable=True)
    duration_minutes = Column(Integer, nullable=True)

    # manual / schedule
    trigger_type = Column(String(20), nullable=False)

    # Name entered from frontend for billing / khata usage
    customer_name = Column(String(100), nullable=False)

    # ON / OFF
    status = Column(String(10), nullable=False, server_default="ON")

    created_at = Column(TIMESTAMP, server_default=text("now()"))

    device = relationship("Device", back_populates="motor_logs")