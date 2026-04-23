# app/models/motor_telemetry.py
import uuid
from sqlalchemy import Column, String, Integer, Float, BigInteger, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base

class MotorTelemetry(Base):
    __tablename__ = "motor_telemetry"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    device_id = Column(
        UUID(as_uuid=True),          # ✅ matches Device.id
        ForeignKey("devices.id"),
        nullable=False
    )

    timestamp = Column(BigInteger, nullable=False)
    freq = Column(Float)
    current = Column(Float)
    voltage = Column(Float)
    dcbus = Column(Float)
    power = Column(Float)
    energy_in = Column(Float)
    fault = Column(Integer)
    fault_code = Column(Integer)
    status_code = Column(Integer)
    reference_freq = Column(Float)
    motor_speed = Column(Float)
    power_percent = Column(Float)
    torque_percent = Column(Float)
    is_live = Column(Integer)

    device = relationship("Device", back_populates="telemetry")