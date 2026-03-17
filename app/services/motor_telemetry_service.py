# app/services/motor_telemetry_service.py

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from uuid import UUID

from app.repositories.motor_telemetry_repo import MotorTelemetryRepository
from app.schemas.motor_telemetry_schema import MotorTelemetryCreate
from app.core.logger import logger
from app.core.exceptions import AppException, NotFoundException


class MotorTelemetryService:

    def __init__(self):
        self.repo = MotorTelemetryRepository()

    def create_telemetry(self, db: Session, data: MotorTelemetryCreate):
        try:
            telemetry = self.repo.create(db, data)
            logger.info(
                "Motor telemetry created: id=%s, device_id=%s",
                telemetry.id,
                telemetry.device_id
            )
            return telemetry
        except SQLAlchemyError as e:
            logger.error(
                "Failed to create telemetry for device_id=%s: %s",
                data.device_id,
                str(e)
            )
            raise AppException(f"Database error: failed to create telemetry for device {data.device_id}")

    def get_device_telemetry(self, db: Session, device_id: UUID):
        try:
            telemetry_list = self.repo.get_by_device(db, device_id)
            logger.info(
                "Fetched %d telemetry records for device_id=%s",
                len(telemetry_list),
                device_id
            )
            return telemetry_list
        except SQLAlchemyError as e:
            logger.error(
                "Failed to fetch telemetry for device_id=%s: %s",
                device_id,
                str(e)
            )
            raise AppException(f"Database error: failed to fetch telemetry for device {device_id}")

    def delete_telemetry(self, db: Session, telemetry_id: UUID):
        try:
            deleted = self.repo.delete(db, telemetry_id)
            if deleted:
                logger.info("Deleted telemetry: id=%s, device_id=%s", deleted.id, deleted.device_id)
                return deleted
            else:
                logger.warning("Telemetry not found to delete: id=%s", telemetry_id)
                raise NotFoundException(f"Telemetry {telemetry_id} not found")
        except SQLAlchemyError as e:
            logger.error("Failed to delete telemetry id=%s: %s", telemetry_id, str(e))
            raise AppException(f"Database error: failed to delete telemetry {telemetry_id}")