# app/models/khata_entry.py
#
# SQLAlchemy ORM model for the khata_entries table.
#
# ── Schema change log ─────────────────────────────────────────────────────────
#  • customer_id (FK → customers.id) has been DROPPED.
#  • user_id     (FK → users.id)     has been ADDED.
#
#  Migration SQL:
#      ALTER TABLE khata_entries DROP COLUMN customer_id;
#      ALTER TABLE khata_entries ADD COLUMN user_id VARCHAR
#          REFERENCES users(id) ON DELETE CASCADE;
# ──────────────────────────────────────────────────────────────────────────────

from sqlalchemy import (
    Column, Integer, String, TIMESTAMP, Numeric,
    Boolean, ForeignKey, Date, text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base_class import Base
import uuid


class KhataEntry(Base):
    __tablename__ = "khata_entries"

    # ─────────────────────────────────────────────────────────────────────────
    # Primary Key
    # ─────────────────────────────────────────────────────────────────────────
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # FIX: Must be UUID to match User.id
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    # FIX: Must be UUID to match Device.id
    device_id = Column(String, nullable=False, index=True)

    # FIX: Assuming MotorLog.id is also a UUID
    motor_log_id = Column(
        Integer,
        ForeignKey("motor_logs.id", ondelete="SET NULL"),
        nullable=True
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Consumer Info
    # ─────────────────────────────────────────────────────────────────────────
    customer_name = Column(String, nullable=False)

    # ─────────────────────────────────────────────────────────────────────────
    # Billing Fields update and parameter
    # ─────────────────────────────────────────────────────────────────────────
    date           = Column(Date,           nullable=False)
    run_hours      = Column(Numeric(5,  2), nullable=False)
    price_per_hour = Column(Numeric(10, 2), nullable=False)
    total_bill     = Column(Numeric(10, 2), nullable=False)

    cash_received = Column(
        Numeric(10, 2),
        nullable=False,
        default=0,
        server_default=text("0")        # DB-level default — never NULL
    )

    balance = Column(
        Numeric(10, 2),
        nullable=False,
        default=0,
        server_default=text("0")        # DB-level default
    )
    advance_amount = Column( 
    Numeric(10, 2), 
    nullable=False,
    default=0,
    server_default=text("0") )

    is_cleared = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false")    # DB-level default
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Timestamps
    # ─────────────────────────────────────────────────────────────────────────
    created_at = Column(
        TIMESTAMP,
        nullable=False,
        server_default=text("now()")    # DB-level default
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Relationships (uncomment when back_populates added to related models)
    # ─────────────────────────────────────────────────────────────────────────
    # owner     = relationship("User",     back_populates="khata_entries")
    # device    = relationship("Device",   back_populates="khata_entries")
    # motor_log = relationship("MotorLog", back_populates="khata_entries")

    # ─────────────────────────────────────────────────────────────────────────
    # Debug helper
    # ─────────────────────────────────────────────────────────────────────────
    def __repr__(self):
        return (
            f"<KhataEntry id={self.id} "
            f"user_id={self.user_id} "
            f"customer={self.customer_name} "
            f"total={self.total_bill} "
            f"balance={self.balance} "
            f"cleared={self.is_cleared}>"
        )
    device = relationship("Device", back_populates="khata_entries")