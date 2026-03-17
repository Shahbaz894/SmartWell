# app/db/base_class.py

from app.db.base import Base

# Import all models here so Alembic detects them
from app.db.base import Base
from app.models.user import User
from app.models.device import Device          # Must come before MotorTelemetry
from app.models.motor_log import MotorLog
from app.models.schedule import Schedule
from app.models.customer import Customer
from app.models.khata_entry import KhataEntry
from app.models.motor_parameter import MotorTelemetry