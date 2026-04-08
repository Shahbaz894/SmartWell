from sqlalchemy import Column, String, TIMESTAMP, Numeric, Boolean, ForeignKey, Date
from app.db.base import Base
import uuid

class KhataEntry(Base):
    __tablename__ = "khata_entries"

    # Primary key can remain UUID or string
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # FK to customer (assuming customer.id is still UUID)
    # MUST match the type in customer.py exactly
    customer_id = Column(String, ForeignKey("customers.id", ondelete="CASCADE"))

    # FK to device (ESP32 string ID)
    device_id = Column(String, ForeignKey("devices.id", ondelete="CASCADE"))

    # FK to motor_logs (adjusted to string, matches your updated MotorLog.id)
    motor_log_id = Column(String, ForeignKey("motor_logs.id", ondelete="SET NULL"))

    date = Column(Date, nullable=False)
    run_hours = Column(Numeric(5,2), nullable=False)
    price_per_hour = Column(Numeric(10,2), nullable=False)
    total_bill = Column(Numeric(10,2), nullable=False)
    cash_received = Column(Numeric(10,2), default=0)
    balance = Column(Numeric(10,2))
    is_cleared = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, server_default="now()")