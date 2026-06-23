"""
KhataEntry model (FIXED).

Key fixes:
1. `device` relationship now declared BEFORE __repr__ (was after, fragile).
2. Added `owner` relationship to User (was commented out).
3. Added `motor_log` relationship to MotorLog (was commented out).
4. `device_id` stays as String(100) — it stores Device.device_uid (e.g. "ESP32_001_TW"),
   NOT a UUID. This matches admin workflow.
5. Added `is_open` flag — TRUE when motor is running for this customer, FALSE when
   motor stopped and khata was finalized. This is the flag the lifecycle service
   checks to decide whether to resume an existing khata or open a new one.
6. Added `started_at` / `ended_at` timestamps (in addition to `date` and `created_at`)
   so we can compute exact run-hours from the actual motor session, not just from
   the date.
"""
import uuid
from sqlalchemy import (
    Column, Integer, String, TIMESTAMP, Numeric,
    Boolean, ForeignKey, Date, text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base_class import Base


class KhataEntry(Base):
    __tablename__ = "khata_entries"

    # ─────────────────────────────────────────────────────────────────────────
    # Primary Key
    # ─────────────────────────────────────────────────────────────────────────
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Owner of this khata (User.id is UUID)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # STRING — stores Device.device_uid (e.g. "ESP32_001_TW"). NOT a UUID.
    # No physical FK so admin can rename / re-register devices safely.
    device_id = Column(String(100), nullable=False, index=True)

    # Links to the MotorLog that opened this khata (optional, for traceability)
    motor_log_id = Column(
        Integer,
        ForeignKey("motor_logs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Consumer Info
    # ─────────────────────────────────────────────────────────────────────────
    customer_name = Column(String(100), nullable=False, index=True)

    # ─────────────────────────────────────────────────────────────────────────
    # Session window (when motor actually ran for this customer)
    # ─────────────────────────────────────────────────────────────────────────
    date = Column(Date, nullable=False)
    started_at = Column(TIMESTAMP, nullable=True)        # motor ON timestamp
    ended_at   = Column(TIMESTAMP, nullable=True, index=True)  # motor OFF timestamp

    # TRUE while motor is running for this customer; FALSE after motor off + bill finalized.
    is_open = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
        index=True,
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Billing Fields
    # ─────────────────────────────────────────────────────────────────────────
    run_hours      = Column(Numeric(10, 2), nullable=False, default=0, server_default=text("0"))
    price_per_hour = Column(Numeric(10, 2), nullable=False, default=0, server_default=text("0"))
    total_bill     = Column(Numeric(10, 2), nullable=False, default=0, server_default=text("0"))

    cash_received = Column(
        Numeric(10, 2),
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    balance = Column(
        Numeric(10, 2),
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    advance_amount = Column(
        Numeric(10, 2),
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    is_cleared = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
        index=True,
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Timestamps
    # ─────────────────────────────────────────────────────────────────────────
    created_at = Column(
        TIMESTAMP,
        nullable=False,
        server_default=text("now()"),
    )
    updated_at = Column(
        TIMESTAMP,
        nullable=True,
        onupdate=text("now()"),
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Relationships
    # ─────────────────────────────────────────────────────────────────────────
    owner = relationship(
        "User",
        back_populates="khata_entries",
    )

    device = relationship(
        "Device",
        back_populates="khata_entries",
        primaryjoin="foreign(KhataEntry.device_id) == Device.device_uid",
    )

    motor_log = relationship(
        "MotorLog",
        back_populates="khata_entries",
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Debug helper
    # ─────────────────────────────────────────────────────────────────────────
    def __repr__(self):
        return (
            f"<KhataEntry id={self.id} "
            f"user_id={self.user_id} "
            f"device_id={self.device_id} "
            f"customer={self.customer_name} "
            f"open={self.is_open} "
            f"total={self.total_bill} "
            f"balance={self.balance} "
            f"cleared={self.is_cleared}>"
        )
