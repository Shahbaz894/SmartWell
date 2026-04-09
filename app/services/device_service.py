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
        
    
    def _update_device(self, device_id: str, user_id: str, device_data):
        try:
            logger.info("Updating device: %s", device_id)

            # Get device and verify ownership
            db_device = self.repo.get_by_id(device_id)
            if not db_device or str(db_device.user_id) != user_id:
                raise AppException("Device not found or unauthorized")

            # Update reference_freq if provided
            if getattr(device_data, "reference_freq", None) is not None:
                db_device.reference_freq = device_data.reference_freq

            # Update the device in DB
            updated_device = self.repo.update_device(db_device)

            logger.info("Device updated successfully: %s", device_id)
            return updated_device

        except Exception as e:
            logger.error("Error updating device: %s", str(e), exc_info=True)
            raise AppException(str(e))
            
    
    

    def get_user_devices(self, user_id: str):
        try:
            return self.repo.get_user_devices(user_id)
        except Exception as e:
            logger.error("Error fetching devices: %s", str(e))
            raise AppException("Could not fetch devices")