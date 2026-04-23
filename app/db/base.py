# app/db/base.py

# from sqlalchemy.orm import DeclarativeBase


# class Base(DeclarativeBase):
#     pass
# app/db/base.py
from app.db.base_class import Base  # noqa

# ALL models must be imported here so metadata knows about them
from app.models.user import User  # noqa
from app.models.device import Device  # noqa
from app.models.motor_log import MotorLog  # noqa
from app.models.motor_parameter import MotorTelemetry  # noqa
from app.models.schedule import Schedule  # noqa
from app.models.khata_entry import KhataEntry  # noqa
from app.models.vfd_command_log import VFDCommandLog  # noqa