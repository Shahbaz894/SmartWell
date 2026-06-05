# app/models/customer.py
import uuid
from sqlalchemy import Column, String, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.db.base_class import Base

class Customer(Base):
    __tablename__ = "customers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)  # ✅ UUID PK

    user_id = Column(
        UUID(as_uuid=True),          # ✅ matches User.id
        ForeignKey("users.id", ondelete="CASCADE")
    )

    name = Column(String(100), nullable=False)
    phone = Column(String(20))
    address = Column(String(255))
    created_at = Column(TIMESTAMP, server_default="now()")