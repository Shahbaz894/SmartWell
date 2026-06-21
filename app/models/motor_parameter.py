import uuid
from sqlalchemy import Column, Integer, Float, BigInteger, ForeignKey, DateTime,String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base_class import Base

# models/motor_telemetry.py me
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column
from app.schemas.enums import TriggerType

class MotorTelemetry(Base):
    __tablename__ = "motor_telemetry"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # device_id = Column(
    #     UUID(as_uuid=True),
    #     ForeignKey("devices.id"),
    #     nullable=False,
    #     index=True,
    
    # )
    device_id = Column(String, nullable=False, index=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    timestamp = Column(BigInteger, nullable=False, index=True)
    trigger_type: Mapped[TriggerType] = mapped_column(SQLEnum(TriggerType), default=TriggerType.physical)

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