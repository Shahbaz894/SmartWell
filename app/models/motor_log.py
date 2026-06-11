# app/models/motor_log.py
import uuid
from sqlalchemy import Column, String, TIMESTAMP, Integer, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class MotorLog(Base):
    __tablename__ = "motor_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Add index=True for faster lookups when querying history
    device_id = Column(
        UUID(as_uuid=True),
        ForeignKey("devices.id", ondelete="CASCADE"), # Added CASCADE for cleanup
        nullable=False,
        index=True 
    )

    start_time = Column(TIMESTAMP, nullable=False, index=True) # Index start_time
    end_time = Column(TIMESTAMP, nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    
    # Keeping it as String is fine, but ensure your FastAPI logic validates these
    trigger_type = Column(String(20), nullable=False)
    customer_name = Column(String(100), nullable=False)
    status = Column(String(10), nullable=False, server_default="ON")
    created_at = Column(TIMESTAMP, server_default=text("now()"))

    device = relationship("Device", back_populates="motor_logs")
