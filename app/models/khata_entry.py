# app/models/khata_entry.py

from sqlalchemy import Column, String, TIMESTAMP, Numeric, Boolean, ForeignKey, Date, text
from sqlalchemy.orm import relationship
from app.db.base import Base
import uuid


class KhataEntry(Base):
    __tablename__ = "khata_entries"

    # ─────────────────────────────────────────────
    # Primary Key
    # ─────────────────────────────────────────────
    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    # ─────────────────────────────────────────────
    # Foreign Keys
    # ─────────────────────────────────────────────
    customer_id = Column(
        String,
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=True   # nullable because customer may not be registered
    )

    device_id = Column(
        String,
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False
    )

    motor_log_id = Column(
        String,
        ForeignKey("motor_logs.id", ondelete="SET NULL"),
        nullable=True   # nullable because run_hours can be entered manually
    )

    # ─────────────────────────────────────────────
    # Customer Info
    # ─────────────────────────────────────────────
    customer_name = Column(String, nullable=False)

    # ─────────────────────────────────────────────
    # Billing Fields
    # ─────────────────────────────────────────────
    date           = Column(Date,          nullable=False)
    run_hours      = Column(Numeric(5, 2), nullable=False)
    price_per_hour = Column(Numeric(10, 2), nullable=False)
    total_bill     = Column(Numeric(10, 2), nullable=False)

    cash_received  = Column(
        Numeric(10, 2),
        nullable=False,
        default=0,
        server_default=text("0")   # ✅ DB-level default so column is never NULL
    )

    balance = Column(
        Numeric(10, 2),
        nullable=False,
        default=0,
        server_default=text("0")   # ✅ DB-level default
    )

    is_cleared = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false")  # ✅ DB-level default
    )

    # ─────────────────────────────────────────────
    # Timestamps
    # ─────────────────────────────────────────────
    created_at = Column(
        TIMESTAMP,
        nullable=False,
        server_default=text("now()")  # ✅ DB-level default
    )

    # ─────────────────────────────────────────────
    # Relationships (optional — for joins later)
    # ─────────────────────────────────────────────
    # customer  = relationship("Customer",  back_populates="khata_entries")
    # device    = relationship("Device",    back_populates="khata_entries")
    # motor_log = relationship("MotorLog",  back_populates="khata_entries")

    # ─────────────────────────────────────────────
    # Debug helper
    # ─────────────────────────────────────────────
    def __repr__(self):
        return (
            f"<KhataEntry id={self.id} "
            f"customer={self.customer_name} "
            f"total={self.total_bill} "
            f"balance={self.balance} "
            f"cleared={self.is_cleared}>"
        )