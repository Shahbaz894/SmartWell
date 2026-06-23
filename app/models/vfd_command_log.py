"""
VFDCommandLog model (no behaviour change — kept clean).

`device_id` stays as String — stores Device.device_uid.
"""
import uuid
from sqlalchemy import Column, String, TIMESTAMP, Float, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base_class import Base


class VFDCommandLog(Base):
    __tablename__ = "vfd_command_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # STRING — stores Device.device_uid. NOT a UUID.
    device_id = Column(String(100), nullable=False, index=True)

    command = Column(String(50), nullable=False)
    reference_frequency = Column(Float, nullable=True)
    triggered_by = Column(String(100), nullable=True)
    trigger_source = Column(String(50), nullable=False, default="manual")
    status = Column(String(30), nullable=False, default="PENDING")
    message = Column(String(255), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("now()"))

    device = relationship(
        "Device",
        back_populates="vfd_command_logs",
        primaryjoin="foreign(VFDCommandLog.device_id) == Device.device_uid",
    )
