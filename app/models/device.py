# from sqlalchemy import Column, String, ForeignKey, TIMESTAMP, text
# from sqlalchemy.dialects.postgresql import UUID
# from sqlalchemy.orm import relationship
# from app.db.base import Base

# class Device(Base):
#     __tablename__ = "devices"

#     # Example: SMSWELL1001
#     id = Column(String(50), primary_key=True)

#     user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))

#     device_name = Column(String(100), nullable=False)
#     device_uid = Column(String(100), unique=True, nullable=False)
#     sim_number = Column(String(20))
#     location = Column(String(255))
#     device_secret = Column(String(255), nullable=False)

#     created_at = Column(TIMESTAMP, server_default=text("now()"))

#     # 🔗 Relationships
#     motor_logs = relationship("MotorLog", back_populates="device", cascade="all, delete")
#     telemetry = relationship("MotorTelemetry", back_populates="device", cascade="all, delete")

from sqlalchemy import Column, String, ForeignKey, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base

class Device(Base):
 __tablename__ = "devices"
 id = Column(String(50), primary_key=True)
 user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
 device_name = Column(String(100), nullable=False)
 device_uid = Column(String(100), unique=True, nullable=False)
 sim_number = Column(String(20))
 location = Column(String(255))
 device_secret = Column(String(255), nullable=False)
 created_at = Column(TIMESTAMP, server_default=text("now()"))
 
 # 🔗 Relationships
 motor_logs = relationship("MotorLog", back_populates="device", cascade="all, delete")
 telemetry = relationship("MotorTelemetry", back_populates="device", cascade="all, delete")
 schedules = relationship("Schedule", back_populates="device", cascade="all, delete")