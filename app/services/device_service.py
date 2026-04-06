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
            logger.info("Creating device with custom ID: %s", device_data.device_uid)
            
            # Check if device already exists
            existing = self.repo.get_by_uid(device_data.device_uid)
            if existing:
                raise AppException("Device with this UID already exists")

            generated_secret = secrets.token_urlsafe(32)

            new_device = Device(
                # Use the custom ID (e.g., SMSWELL1001) as the Primary Key
                id=device_data.device_uid, 
                user_id=user_id,
                device_name=device_data.device_name,
                device_uid=device_data.device_uid,
                sim_number=device_data.sim_number,
                location=device_data.location,
                device_secret=generated_secret
            )

            created_device = self.repo.create_device(new_device)
            return created_device

        except Exception as e:
            logger.error("Error in DeviceService: %s", str(e), exc_info=True)
            raise AppException(str(e))

    def get_user_devices(self, user_id: str):
        try:
            return self.repo.get_user_devices(user_id)
        except Exception as e:
            logger.error("Error fetching devices: %s", str(e))
            raise AppException("Could not fetch devices")