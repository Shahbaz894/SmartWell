from app.db.base_class import Base

# Import ALL models here
from app.models.user import User  # noqa
from app.models.device import Device  # noqa
from app.models.motor_log import MotorLog  # noqa
from app.models.customer import Customer  # noqa
from app.models.schedule import Schedule  # noqa
from app.models.khata_entry import KhataEntry  # noqa
from app.models.motor_parameter import MotorTelemetry  # noqa
from app.models.vfd_command_log import VFDCommandLog  # noqa
from app.models.motor_timer import MotorTimer