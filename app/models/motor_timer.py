"""
MotorTimer model (no behaviour change — kept clean).

`device_id` stays as String — stores Device.device_uid.
"""
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Integer
from app.db.base_class import Base


class MotorTimer(Base):
    __tablename__ = "motor_timers"

    id = Column(Integer, primary_key=True, index=True)

    # STRING — stores Device.device_uid. NOT a UUID.
    device_id = Column(String(100), nullable=False, index=True)

    customer_name = Column(String(100), nullable=True)
    start_time = Column(DateTime, nullable=False)
    stop_time = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    is_running = Column(Boolean, default=True)
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # NOTE: no back_populates here (one-way link). If you want two-way, add
    # `motor_timers = relationship(...)` on Device — already done in fixed Device.
