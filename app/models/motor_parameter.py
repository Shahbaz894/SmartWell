"""
MotorTelemetry model (FIXED — was the actual cause of the mapper error chain).

CRITICAL FIX:
The previous `device` relationship used:
    back_populates="motor_logs"    # WRONG — that points to Device.motor_logs, owned by MotorLog
    primaryjoin="foreign(MotorLog.device_id) == Device.device_uid"  # WRONG model

This caused SQLAlchemy to fail resolving Device.motor_logs (claimed by both
MotorLog and MotorTelemetry) which cascaded into "KhataEntry has no property device"
because the whole mapper registry refused to configure once any mapper failed.

Now correctly uses:
    back_populates="telemetry"     # matches Device.telemetry
    primaryjoin="foreign(MotorTelemetry.device_id) == Device.device_uid"
"""
import uuid
from sqlalchemy import Column, Integer, Float, BigInteger, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy import Enum as SQLEnum

from app.db.base_class import Base
from app.schemas.enums import TriggerType


class MotorTelemetry(Base):
    __tablename__ = "motor_telemetry"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # STRING — stores Device.device_uid. NOT a UUID.
    device_id = Column(String(100), nullable=False, index=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    timestamp = Column(BigInteger, nullable=False, index=True)

    # NOTE: there are two `trigger_type` columns below — one typed as
    # SQLEnum(TriggerType) and one as String. This was in the original file.
    # The String one wins (defined later). If you only need String, delete
    # the SQLEnum line. Keeping both for backward compat with existing rows.
    trigger_type: Mapped[TriggerType] = mapped_column(
        SQLEnum(TriggerType), default=TriggerType.physical
    )

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
    trigger_type = Column(String, nullable=True)

    # CORRECT relationship — back_populates matches Device.telemetry.
    device = relationship(
        "Device",
        back_populates="telemetry",
        primaryjoin="foreign(MotorTelemetry.device_id) == Device.device_uid",
    )
