import uuid

from sqlalchemy import Column, String, TIMESTAMP, ForeignKey, Float, text
from sqlalchemy.orm import relationship

from app.db.base import Base


class VFDCommandLog(Base):
    """
    Stores VFD command history sent from backend to device.

    Supported commands:
    - RESET_VFD
    - SET_REFERENCE_FREQUENCY

    Useful for:
    - audit history
    - troubleshooting
    - mobile app history
    """

    __tablename__ = "vfd_command_logs"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))

    device_id = Column(
        String(50),
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