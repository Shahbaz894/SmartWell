# app/models/vfd_command_log.py
import uuid
from sqlalchemy import Column, String, TIMESTAMP, Float, text,ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base

class VFDCommandLog(Base):
    __tablename__ = "vfd_command_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    device_id = Column(
        UUID(as_uuid=True),          # ✅ matches Device.id
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    command = Column(String(50), nullable=False)
    reference_frequency = Column(Float, nullable=True)
    triggered_by = Column(String(100), nullable=True)
    trigger_source = Column(String(50), nullable=False, default="manual")
    status = Column(String(30), nullable=False, default="PENDING")
    message = Column(String(255), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("now()"))

    device = relationship("Device", back_populates="vfd_command_logs")