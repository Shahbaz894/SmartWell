from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from app.models.user import User
from app.models.device import Device
from app.core.exceptions import AppException
from app.core.logger import logger

from app.repositories.motor_telemetry_repo import MotorTelemetryRepository
def _db_error(exc: Exception) -> str:
    return str(exc.orig) if hasattr(exc, "orig") else str(exc)


class DeviceRepository:
    """
    Database repository for Device table.

    This class only handles database operations.
    Ownership and business validation should stay in DeviceService.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, device_id: str):
        """
        Get one device by UUID primary key.
        """
        try:
            return self.db.query(Device).filter(Device.id == device_id).first()

        except SQLAlchemyError as exc:
            logger.error(
                "Device get_by_id database error: device_id=%s error=%s",
                device_id,
                _db_error(exc),
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=f"Database error while fetching device: {_db_error(exc)}",
            )

    def get_by_uid(self, device_uid: str):
        """
        Get one device by ESP32/MQTT device UID.
        """
        try:
            return self.db.query(Device).filter(Device.device_uid == device_uid).first()

        except SQLAlchemyError as exc:
            logger.error(
                "Device get_by_uid database error: device_uid=%s error=%s",
                device_uid,
                _db_error(exc),
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=f"Database error while fetching device by UID: {_db_error(exc)}",
            )

  

    def get_user_devices(self, user_id: str):
        try:
            return (
                self.db.query(Device)
                .filter(Device.user_id == user_id)
                .order_by(Device.created_at.desc())
                .all()
            )

        except SQLAlchemyError as exc:
            logger.error(
                "Device get_user_devices database error: user_id=%s error=%s",
                user_id,
                _db_error(exc),
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=f"Database error while fetching user devices: {_db_error(exc)}",
            )
    def create_device(self, device: Device):
        """
        Insert new device.
        """
        try:
            self.db.add(device)
            self.db.commit()
            self.db.refresh(device)
            return device

        except IntegrityError as exc:
            self.db.rollback()
            logger.error(
                "Device insert integrity error: device_uid=%s error=%s",
                getattr(device, "device_uid", None),
                _db_error(exc),
                exc_info=True,
            )
            raise AppException(
                status_code=400,
                detail=f"Device insert failed. Possible duplicate device_uid or invalid user_id. DB error: {_db_error(exc)}",
            )

        except SQLAlchemyError as exc:
            self.db.rollback()
            logger.error(
                "Device insert database error: device_uid=%s error=%s",
                getattr(device, "device_uid", None),
                _db_error(exc),
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=f"Database error while creating device: {_db_error(exc)}",
            )

    def update_device(self, device: Device):
        """
        Commit changes on an existing device.
        """
        try:
            self.db.commit()
            self.db.refresh(device)
            return device

        except IntegrityError as exc:
            self.db.rollback()
            logger.error(
                "Device update integrity error: device_id=%s error=%s",
                getattr(device, "id", None),
                _db_error(exc),
                exc_info=True,
            )
            raise AppException(
                status_code=400,
                detail=f"Device update failed. DB error: {_db_error(exc)}",
            )

        except SQLAlchemyError as exc:
            self.db.rollback()
            logger.error(
                "Device update database error: device_id=%s error=%s",
                getattr(device, "id", None),
                _db_error(exc),
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=f"Database error while updating device: {_db_error(exc)}",
            )

    def delete_device(self, device: Device):
        """
        Delete existing device.

        Because Device model has cascade relationships, related rows may also
        be deleted depending on relationship cascade and database constraints.
        """
        try:
            device_id = str(device.id)
            device_uid = device.device_uid

            self.db.delete(device)
            self.db.commit()

            logger.info(
                "Device deleted from database: device_id=%s device_uid=%s",
                device_id,
                device_uid,
            )

            return True

        except IntegrityError as exc:
            self.db.rollback()
            logger.error(
                "Device delete integrity error: device_id=%s error=%s",
                getattr(device, "id", None),
                _db_error(exc),
                exc_info=True,
            )
            raise AppException(
                status_code=400,
                detail=f"Device delete failed because related data still exists. DB error: {_db_error(exc)}",
            )

        except SQLAlchemyError as exc:
            self.db.rollback()
            logger.error(
                "Device delete database error: device_id=%s error=%s",
                getattr(device, "id", None),
                _db_error(exc),
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=f"Database error while deleting device: {_db_error(exc)}",
            )