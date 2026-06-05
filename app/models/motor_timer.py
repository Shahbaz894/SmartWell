from datetime import datetime

from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import String

from app.db.base_class import Base


class MotorTimer(Base):
    __tablename__ = "motor_timers"

    id = Column(Integer, primary_key=True, index=True)

    device_id = Column(String, nullable=False, index=True)

    customer_name = Column(String, nullable=True)

    start_time = Column(DateTime, nullable=False)

    stop_time = Column(DateTime, nullable=False)

    duration_minutes = Column(Integer, nullable=False)

    is_running = Column(Boolean, default=True)

    is_completed = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)