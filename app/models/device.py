"""
Device model (FIXED).

Key fixes:
1. Removed DUPLICATE `vfd_command_logs` relationship (was defined twice).
2. Removed the BROKEN `ForeignKeyConstraint(['device_uid'], ['motor_telemetry.device_id'])`
   — that constraint was reversed. devices.device_uid is the source of truth;
   motor_telemetry.device_id (and every other *_device_id column) references it
   logically, not physically, so admin can register a device before any telemetry
   row exists.
3. `device_uid` is the String identifier admin sets (e.g. "ESP32_001_TW").
   `id` (UUID) is the internal PK.
4. All child tables (MotorLog, MotorTelemetry, Schedule, VFDCommandLog, KhataEntry,
   MotorTimer) store device_uid as a plain String — NOT a UUID — because admin
   can type any custom string.
"""
import uuid
from sqlalchemy import (
    Column, Float, String, TIMESTAMP, text, ForeignKey
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base_class import Base


class Device(Base):
    __tablename__ = "devices"

    # Internal UUID primary key (never exposed to the device firmware)
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Owner of the device (User.id is UUID)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Human-readable, admin-assigned device id — STRING, not UUID.
    # Example: "ESP32_001_TW". This is what every child table references.
    device_uid = Column(String(100), unique=True, nullable=False, index=True)

    device_name = Column(String(100), nullable=False)
    sim_number = Column(String(20), nullable=True)
    location = Column(String(255), nullable=True)
    device_secret = Column(String(255), nullable=False)
    reference_freq = Column(Float, nullable=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=text("now()"))

    # ------------------------------------------------------------------
    # Relationships
    # All child tables use device_uid (String) to link back to Device.
    # We tell SQLAlchemy the join condition explicitly with `primaryjoin`
    # + `foreign()` because there is NO physical FK constraint on the child
    # side — this lets admin register a device before any telemetry/log row
    # exists, and lets a device be deleted without FK headaches.
    # ------------------------------------------------------------------
    owner = relationship("User", back_populates="devices")

    motor_logs = relationship(
        "MotorLog",
        back_populates="device",
        primaryjoin="Device.device_uid == foreign(MotorLog.device_id)",
        cascade="all, delete-orphan",
        lazy="select",
    )

    telemetry = relationship(
        "MotorTelemetry",
        back_populates="device",
        primaryjoin="Device.device_uid == foreign(MotorTelemetry.device_id)",
        cascade="all, delete-orphan",
    )

    schedules = relationship(
        "Schedule",
        back_populates="device",
        primaryjoin="Device.device_uid == foreign(Schedule.device_id)",
        cascade="all, delete-orphan",
    )

    vfd_command_logs = relationship(
        "VFDCommandLog",
        back_populates="device",
        primaryjoin="Device.device_uid == foreign(VFDCommandLog.device_id)",
        cascade="all, delete-orphan",
    )

    khata_entries = relationship(
        "KhataEntry",
        back_populates="device",
        primaryjoin="Device.device_uid == foreign(KhataEntry.device_id)",
        cascade="all, delete-orphan",
    )

    motor_timers = relationship(
        "MotorTimer",
        primaryjoin="Device.device_uid == foreign(MotorTimer.device_id)",
        cascade="all, delete-orphan",
    )

    # NOTE: no __table_args__ with ForeignKeyConstraint — the previous one
    # was reversed (devices.device_uid -> motor_telemetry.device_id) and
    # prevented inserting a device before telemetry existed.

    def __repr__(self):
        return f"<Device id={self.id} uid={self.device_uid} name={self.device_name}>"
