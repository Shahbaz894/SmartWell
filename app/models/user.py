# app/models/user.py
from sqlalchemy import Column, String, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base
import uuid
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    google_id = Column(String(255), nullable=True)
    role = Column(String(20), default="user")  # 👈 ADD THIS
  

    created_at = Column(TIMESTAMP, server_default=func.now())
    
    # inside User class
    devices = relationship("Device", back_populates="owner", cascade="all, delete")