import secrets
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.models.device import Device
from app.repositories.device_repo import DeviceRepository
from app.schemas.device_schema import DeviceCreate
from app.core.logger import logger
from app.core.exceptions import AppException


class DeviceService:
    def __init__(self, db: Session):
        self.repo = DeviceRepository(db)

    def create_device(self, user_id: str, device_data: DeviceCreate):
        try:
            logger.info(
                "Creating device UID=%s for user=%s",
                device_data.device_uid,
                user_id
            )
            existing = self.repo.get_by_uid(device_data.device_uid)
            if existing:
             raise AppException("Device with this UID already exists")

            # ✅ generate secure secret
            generated_secret = secrets.token_urlsafe(32)

            new_device = Device(
                user_id=user_id,  # ✅ keep UUID
                device_name=device_data.device_name,
                device_uid=device_data.device_uid,
                sim_number=device_data.sim_number,
                location=device_data.location,
                device_secret=generated_secret
            )

            created_device = self.repo.create_device(new_device)

            logger.info("Device created successfully: %s", created_device.id)
            return created_device

        except SQLAlchemyError as e:
            # logger.error("DB error: %s", str(e))
            # raise AppException("Database error while creating device")
            # except Exception as e:
            logger.error("Unexpected error in DeviceService.create_device: %s", str(e), exc_info=True)
            raise AppException(str(e))   # 👈 SHOW REAL ERROR

        except Exception as e:
            logger.error("Unexpected error: %s", str(e), exc_info=True)
            raise AppException("Unexpected error while creating device")

    def get_user_devices(self, user_id: str):
        try:
            return self.repo.get_user_devices(user_id)
        except Exception as e:
            logger.error("Error fetching devices: %s", str(e))
            raise AppException("Could not fetch devices")