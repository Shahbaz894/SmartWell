import secrets

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.core.exceptions import AppException
from app.core.logger import logger
from app.models.device import Device
from app.models.user import User
from app.repositories.device_repo import DeviceRepository
from app.schemas.device_schema import DeviceCreate, DeviceUpdate
from app.repositories.motor_telemetry_repo import MotorTelemetryRepository

def _db_error(exc: Exception) -> str:
    return str(exc.orig) if hasattr(exc, "orig") else str(exc)


class DeviceService:
    """
    Business logic for device management.

    Important design:
    - Device.id is UUID and is used by backend API routes.
    - Device.device_uid is used by ESP32 and MQTT topics.
    - Do not store TB-DEV-001 inside Device.id.
    - Store TB-DEV-001 inside Device.device_uid.

    MQTT note:
    Creating, updating, listing, or deleting a device does not publish MQTT.
    MQTT is used by MotorService, VFDControlService, and telemetry subscriber.
    """

    def __init__(self, db: Session):
        self.db = db
        self.repo = DeviceRepository(db)
        self.telemetry_repo = MotorTelemetryRepository()

    def create_device(self, user_id: str, device_data: DeviceCreate):
        """
        Create a new device for a user.

        Args:
            user_id: Existing user UUID.
            device_data: DeviceCreate schema.

        Returns:
            Created Device ORM object.

        Raises:
            AppException:
                404 if user does not exist.
                400 if device_uid already exists.
                500 for database or unexpected errors.
        """
        try:
            logger.info(
                "Creating device: uid=%s user_id=%s",
                device_data.device_uid,
                user_id,
            )

            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                raise AppException(
                    status_code=404,
                    detail=f"User '{user_id}' not found. Create user first.",
                )

            existing = self.repo.get_by_uid(device_data.device_uid)
            if existing:
                raise AppException(
                    status_code=400,
                    detail=f"Device UID '{device_data.device_uid}' already exists",
                )

            device = Device(
                user_id=user_id,
                device_name=device_data.device_name,
                device_uid=device_data.device_uid,
                sim_number=device_data.sim_number,
                location=device_data.location,
                reference_freq=getattr(device_data, "reference_freq", None),
                device_secret=secrets.token_urlsafe(32),
            )

            created = self.repo.create_device(device)

            logger.info(
                "Device created successfully: id=%s uid=%s user_id=%s",
                created.id,
                created.device_uid,
                created.user_id,
            )

            return created

        except AppException:
            raise

        except SQLAlchemyError as exc:
            logger.error(
                "Database error creating device: user_id=%s uid=%s error=%s",
                user_id,
                getattr(device_data, "device_uid", None),
                _db_error(exc),
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=f"Database error while creating device: {_db_error(exc)}",
            )

        except Exception as exc:
            logger.error(
                "Unexpected error creating device: user_id=%s uid=%s error_type=%s error=%s",
                user_id,
                getattr(device_data, "device_uid", None),
                type(exc).__name__,
                str(exc),
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=f"Unexpected error while creating device: {type(exc).__name__}: {str(exc)}",
            )

    def get_device(self, device_id: str, user_id: str):
        """
        Get one device by UUID and validate ownership.
        """
        try:
            device = self.repo.get_by_id(device_id)

            if not device:
                raise AppException(
                    status_code=404,
                    detail=f"Device '{device_id}' not found",
                )

            if str(device.user_id) != str(user_id):
                raise AppException(
                    status_code=403,
                    detail="Access denied. This device does not belong to you.",
                )

            logger.info(
                "Device fetched successfully: device_id=%s user_id=%s",
                device_id,
                user_id,
            )

            return device

        except AppException:
            raise

        except Exception as exc:
            logger.error(
                "Unexpected error fetching device: device_id=%s user_id=%s error_type=%s error=%s",
                device_id,
                user_id,
                type(exc).__name__,
                str(exc),
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=f"Unexpected error while fetching device: {type(exc).__name__}: {str(exc)}",
            )

    def get_user_devices(self, user_id: str):
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                raise AppException(
                    status_code=404,
                    detail=f"User '{user_id}' not found",
                )

            devices = self.repo.get_user_devices(user_id)
            telemetry_repo = MotorTelemetryRepository()

            result = []

            for device in devices:
                latest = telemetry_repo.get_latest(self.db, str(device.id))

                result.append({
                    "id": device.id,
                    "user_id": device.user_id,
                    "device_uid": device.device_uid,
                    "device_name": device.device_name,
                    "location": device.location,
                    "sim_number": device.sim_number,
                    "reference_freq": device.reference_freq,
                    "created_at": device.created_at,   # 🔥 REQUIRED
                    "is_online": latest is not None and latest.is_live == 1,
                })

            return result

        except AppException:
            raise

        except Exception as exc:
            logger.error(
                "Error fetching user devices: user_id=%s error_type=%s error=%s",
                user_id,
                type(exc).__name__,
                str(exc),
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=f"Could not fetch devices: {type(exc).__name__}: {str(exc)}",
            )

    def update_device(self, device_id: str, user_id: str, device_data: DeviceUpdate):
        """
        Update editable fields of a device.

        Editable:
        - device_name
        - sim_number
        - location
        - reference_freq

        Not editable here:
        - id
        - user_id
        - device_secret
        - device_uid

        If you want to change device_uid, create a separate protected method.
        """
        try:
            device = self.repo.get_by_id(device_id)

            if not device:
                raise AppException(
                    status_code=404,
                    detail=f"Device '{device_id}' not found",
                )

            if str(device.user_id) != str(user_id):
                raise AppException(
                    status_code=403,
                    detail="Access denied. This device does not belong to you.",
                )

            update_data = device_data.model_dump(exclude_unset=True)

            protected_fields = {"id", "user_id", "device_secret", "device_uid"}
            for field in protected_fields:
                update_data.pop(field, None)

            for field, value in update_data.items():
                setattr(device, field, value)

            updated = self.repo.update_device(device)

            logger.info(
                "Device updated successfully: device_id=%s user_id=%s",
                device_id,
                user_id,
            )

            return updated

        except AppException:
            raise

        except Exception as exc:
            logger.error(
                "Unexpected error updating device: device_id=%s user_id=%s error_type=%s error=%s",
                device_id,
                user_id,
                type(exc).__name__,
                str(exc),
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=f"Unexpected error while updating device: {type(exc).__name__}: {str(exc)}",
            )

    def delete_device(self, device_id: str, user_id: str):
        """
        Delete a device after checking ownership.

        Warning:
        Related rows may also be deleted because Device model relationships use
        cascade delete. This can remove motor logs, telemetry, schedules,
        VFD command logs, and Khata entries linked to this device.
        """
        try:
            device = self.repo.get_by_id(device_id)

            if not device:
                raise AppException(
                    status_code=404,
                    detail=f"Device '{device_id}' not found",
                )

            if str(device.user_id) != str(user_id):
                raise AppException(
                    status_code=403,
                    detail="Access denied. This device does not belong to you.",
                )

            device_uid = device.device_uid

            deleted = self.repo.delete_device(device)

            logger.info(
                "Device deleted successfully: device_id=%s device_uid=%s user_id=%s",
                device_id,
                device_uid,
                user_id,
            )

            return deleted

        except AppException:
            raise

        except Exception as exc:
            logger.error(
                "Unexpected error deleting device: device_id=%s user_id=%s error_type=%s error=%s",
                device_id,
                user_id,
                type(exc).__name__,
                str(exc),
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=f"Unexpected error while deleting device: {type(exc).__name__}: {str(exc)}",
            )