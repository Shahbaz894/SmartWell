"""
Models package init (FIXED — added Customer import so its mapper registers).
"""
from app.models.device import Device
from app.models.motor_parameter import MotorTelemetry
from app.models.motor_log import MotorLog
from app.models.schedule import Schedule
from app.models.vfd_command_log import VFDCommandLog
from app.models.khata_entry import KhataEntry
from app.models.motor_timer import MotorTimer
from app.models.user import User
from app.models.customer import Customer

__all__ = [
    "Device",
    "MotorTelemetry",
    "MotorLog",
    "Schedule",
    "VFDCommandLog",
    "KhataEntry",
    "MotorTimer",
    "User",
    "Customer",
]
