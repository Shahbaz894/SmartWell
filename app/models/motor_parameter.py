from sqlalchemy import Column, String, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base
import uuid

class MotorTelemetry(Base):
    __tablename__ = "motor_telemetry"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 🔥 Link with DB Device (UUID)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id"), nullable=False)

    # Optional: store ESP32 ID also
    device_uid = Column(String, nullable=False)

    output_frequency = Column(Float)
    reference_frequency = Column(Float)
    dc_bus_voltage = Column(Float)
    output_voltage = Column(Float)
    output_current = Column(Float)
    motor_speed = Column(Float)
    power = Column(Float)
    load_torque = Column(Float)
    real_power = Column(Float)