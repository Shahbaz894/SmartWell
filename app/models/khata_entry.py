# app/models/khata_entry.py
from sqlalchemy import Column, String, TIMESTAMP, Numeric, Boolean, ForeignKey, Date
from sqlalchemy.dialects.postgresql import UUID
from app.db.session import Base
import uuid

class KhataEntry(Base):
    __tablename__ = "khata_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"))
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"))
    motor_log_id = Column(UUID(as_uuid=True), ForeignKey("motor_logs.id", ondelete="SET NULL"))
    date = Column(Date, nullable=False)
    run_hours = Column(Numeric(5,2), nullable=False)
    price_per_hour = Column(Numeric(10,2), nullable=False)
    total_bill = Column(Numeric(10,2), nullable=False)
    cash_received = Column(Numeric(10,2), default=0)
    balance = Column(Numeric(10,2))
    is_cleared = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, server_default="now()")