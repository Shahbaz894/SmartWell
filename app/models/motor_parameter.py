from sqlalchemy import Column, String, Integer, Float, BigInteger, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base
import uuid


class MotorTelemetry(Base):
    __tablename__ = "motor_telemetry"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    device_id = Column(String, ForeignKey("devices.id"), nullable=False)

    # From ESP32
    timestamp = Column(BigInteger, nullable=False)

    freq = Column(Float)
    current = Column(Float)
    voltage = Column(Float)
    dcbus = Column(Float)
    power = Column(Float)
    energy_in = Column(Float)

    # Status
    fault = Column(Integer)
    fault_code = Column(Integer)      # ✅ ADDED
    status_code = Column(Integer)

    # Performance
    reference_freq = Column(Float)
    motor_speed = Column(Float)
    power_percent = Column(Float)
    torque_percent = Column(Float)

    # Live / offline
    is_live = Column(Integer)

    # Relationship
    device = relationship("Device", back_populates="telemetry")