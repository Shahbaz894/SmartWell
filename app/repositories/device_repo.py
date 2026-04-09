

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.models import device
from app.models import device
from app.models.device import Device
from app.core.logger import logger
from app.core.exceptions import AppException, NotFoundException


class DeviceRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_device(self, device: Device):
        try:
            self.db.add(device)
            self.db.commit()
            self.db.refresh(device)
            # FIX: Changed .name to .device_name
            logger.info("Device created: id=%s, name=%s", device.id, device.device_name)
            return device
        except SQLAlchemyError as e:
            self.db.rollback()
            # FIX: Changed .name to .device_name
            logger.error("Failed to create device: %s", str(e))
            raise AppException(f"Database error: failed to create device")

    def get_user_devices(self, user_id: str):
        try:
            return self.db.query(Device).filter(Device.user_id == user_id).all()
        except SQLAlchemyError as e:
            logger.error("Failed to fetch devices for user_id=%s: %s", user_id, str(e))
            raise AppException("Database error while fetching devices")

    def get_device(self, device_id: str):
        device = self.db.query(Device).filter(Device.id == device_id).first()
        if not device:
            raise NotFoundException(f"Device {device_id} not found")
        
        
        return device
    
    def update_device(self, device: Device):
        self.db.add(device)
        self.db.commit()
        self.db.refresh(device)
        return device

    def delete_device(self, device_id: str):
        try:
            device = self.get_device(device_id)
            self.db.delete(device)
            self.db.commit()
            logger.info("Device deleted: id=%s", device_id)
            return True
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error("Failed to delete device id=%s: %s", device_id, str(e))
            raise AppException("Database error during deletion")
        
        
    def get_by_uid(self, device_uid: str):
        return self.db.query(Device).filter(Device.device_uid == device_uid).first()