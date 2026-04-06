from sqlalchemy import Column, String, Float, ForeignKey
from app.db.base import Base
import uuid

class MotorTelemetry(Base):
    __tablename__ = "motor_telemetry"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    # ✅ Use String to match Device.id
    device_id = Column(String, ForeignKey("devices.id"), nullable=False)

    # Optional: store ESP32 ID separately
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