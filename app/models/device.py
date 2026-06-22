import uuid
from sqlalchemy import Column, Float, String, ForeignKey, TIMESTAMP, text, ForeignKeyConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class Device(Base):
    __tablename__ = "devices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    
    device_uid = Column(String(100), unique=True, nullable=False, index=True)
    device_name = Column(String(100), nullable=False)
    sim_number = Column(String(20), nullable=True)
    location = Column(String(255), nullable=True)
    device_secret = Column(String(255), nullable=False)
    reference_freq = Column(Float, nullable=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=text("now()"))

    # Relationships (Logical links only, not physical DB constraints)
    owner = relationship("User", back_populates="devices")
    motor_logs = relationship(
        "MotorLog", 
        back_populates="device", 
        primaryjoin="Device.device_uid == foreign(MotorLog.device_id)", 
        cascade="all, delete",
        lazy="select"
    )

    telemetry = relationship(
        "MotorTelemetry", 
        back_populates="device", 
        primaryjoin="Device.device_uid == foreign(MotorTelemetry.device_id)",
        cascade="all, delete"
    )
    # motor_logs = relationship("MotorLog", back_populates="device", primaryjoin="Device.device_uid == foreign(MotorLog.device_id)")
    # telemetry = relationship("MotorTelemetry", back_populates="device", primaryjoin="Device.device_uid == foreign(MotorTelemetry.device_id)")
    schedules = relationship("Schedule", back_populates="device", primaryjoin="Device.device_uid == foreign(Schedule.device_id)")
    vfd_command_logs = relationship("VFDCommandLog", back_populates="device", primaryjoin="Device.device_uid == foreign(VFDCommandLog.device_id)")
    khata_entries = relationship("KhataEntry", back_populates="device", primaryjoin="Device.device_uid == foreign(KhataEntry.device_id)")
        # Device model ke andar:
    vfd_command_logs = relationship(
        "VFDCommandLog", 
        back_populates="device", 
        primaryjoin="Device.device_uid == foreign(VFDCommandLog.device_id)",
        cascade="all, delete-orphan"
    )

    # Yahan hum SQLAlchemy ko batate hain ke ye columns logically linked hain
    # Isse mapper error khatam ho jayega
    __table_args__ = (
        ForeignKeyConstraint(['device_uid'], ['motor_telemetry.device_id'], use_alter=True),
    )

    def __repr__(self):
        return f"<Device id={self.id} uid={self.device_uid} name={self.device_name}>"