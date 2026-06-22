from sqlalchemy import Column, String, TIMESTAMP, Integer, ForeignKey, text
from sqlalchemy.orm import relationship,foreign
from sqlalchemy.orm import relationship, foreign
from app.db.base_class import Base

class MotorLog(Base):
    __tablename__ = "motor_logs"

    # Integer ID for performance and auto-incrementing
    id = Column(Integer, primary_key=True, index=True)

    # device_id as String to match your system's device naming convention
    device_id = Column(String, nullable=False, index=True)
    
    start_time = Column(TIMESTAMP, nullable=False, index=True)
    end_time = Column(TIMESTAMP, nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    
    # Using String for simplicity, ensure your Enum or Schema validates these values
    trigger_type = Column(String(20), nullable=False)
    customer_name = Column(String(100), nullable=False)
    
    # Default status set to "ON"
    status = Column(String(10), nullable=False, server_default="ON")
    
    # Automatically set creation time
    created_at = Column(TIMESTAMP, server_default=text("now()"))

    # Relationship to Device
    device = relationship(
    "Device", 
    back_populates="motor_logs",
    # Yeh instruction mapper ko batati hai ke bina physical FK ke join kaise karna hai
    primaryjoin="foreign(MotorLog.device_id) == Device.device_uid"
)