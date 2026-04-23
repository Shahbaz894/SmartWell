# app/models/device.py
import uuid
from sqlalchemy import Column, Float, String, ForeignKey, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base


class Device(Base):
    __tablename__ = "devices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,       # FIX: was missing nullable=False
        index=True            # FIX: add index for faster user→devices lookups
    )

    device_name   = Column(String(100), nullable=False)
    device_uid    = Column(String(100), unique=True, nullable=False, index=True)  # e.g. "TB-DEV-001"

    sim_number    = Column(String(20),  nullable=True)
    location      = Column(String(255), nullable=True)
    device_secret = Column(String(255), nullable=False)
    reference_freq = Column(Float,      nullable=True)

    created_at = Column(TIMESTAMP, nullable=False, server_default=text("now()"))

    # ── Relationships ──────────────────────────────────────────────────────────
    owner = relationship("User", back_populates="devices")   # FIX: add this

    motor_logs = relationship(
        "MotorLog", back_populates="device", cascade="all, delete"
    )
    telemetry = relationship(
        "MotorTelemetry", back_populates="device", cascade="all, delete"
    )
    schedules = relationship(
        "Schedule", back_populates="device", cascade="all, delete"
    )
    vfd_command_logs = relationship(
        "VFDCommandLog", back_populates="device", cascade="all, delete-orphan"
    )
    khata_entries = relationship(                            # FIX: add this
        "KhataEntry", back_populates="device", cascade="all, delete"
    )

    def __repr__(self):
        return (
            f"<Device id={self.id} "
            f"uid={self.device_uid} "
            f"name={self.device_name}>"
        )