"""
MotorLog model (FIXED).

Key fix:
Added `khata_entries = relationship("KhataEntry", back_populates="motor_log")`
so KhataEntry.motor_log (which we now declare) can resolve. Without this,
the mapper error chain would just shift from KhataEntry to MotorLog.

`device_id` stays as String — stores Device.device_uid (e.g. "ESP32_001_TW").
"""
from sqlalchemy import Column, String, TIMESTAMP, Integer, text
from sqlalchemy.orm import relationship
from app.db.base_class import Base


class MotorLog(Base):
    __tablename__ = "motor_logs"

    # Integer ID for performance and auto-incrementing
    id = Column(Integer, primary_key=True, index=True)

    # STRING — stores Device.device_uid. NOT a UUID.
    device_id = Column(String(100), nullable=False, index=True)

    start_time = Column(TIMESTAMP, nullable=False, index=True)
    end_time = Column(TIMESTAMP, nullable=True)
    duration_minutes = Column(Integer, nullable=True)

    # Values: "physical" | "schedule" | "manual" | etc.
    trigger_type = Column(String(20), nullable=False)

    # The customer who was running the motor in this session.
    customer_name = Column(String(100), nullable=False, index=True)

    # "ON" while motor is running; "OFF" once it stopped.
    status = Column(String(10), nullable=False, server_default="ON", index=True)

    created_at = Column(TIMESTAMP, server_default=text("now()"))

    # Relationship to Device (logical join via device_uid)
    device = relationship(
        "Device",
        back_populates="motor_logs",
        primaryjoin="foreign(MotorLog.device_id) == Device.device_uid",
    )

    # Relationship to KhataEntry (one MotorLog can open many khata sessions
    # if the same motor session spans multiple customers — unusual, but safe).
    khata_entries = relationship(
        "KhataEntry",
        back_populates="motor_log",
    )
