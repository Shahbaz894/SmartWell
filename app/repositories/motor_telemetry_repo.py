from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from uuid import UUID

from app import db
from app.models.motor_parameter import MotorTelemetry
from app.schemas.motor_telemetry_schema import MotorTelemetryCreate
from app.core.logger import logger
from app.core.exceptions import AppException, NotFoundException


class MotorTelemetryRepository:

    def create(self, db: Session, data: MotorTelemetryCreate):
        try:
            telemetry = MotorTelemetry(
                device_id=data.device_id,
                freq=data.output_frequency,
                reference_freq=data.reference_frequency,
                dcbus=data.dc_bus_voltage,
                voltage=data.output_voltage,
                current=data.output_current,
                motor_speed=data.motor_speed,
                power=data.real_power,
                power_percent=data.power_load,
                torque_percent=data.torque_load,
                timestamp=int(datetime.now().timestamp() * 1000),
                
                is_live=1
            )
            db.add(telemetry)
            db.commit()
            db.refresh(telemetry)
            logger.info(
                "Motor telemetry created: id=%s, device_id=%s",
                telemetry.id,
                telemetry.device_id
            )
            return telemetry
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(
                "Failed to create motor telemetry for device %s: %s",
                data.device_id,
                str(e)
            )
            raise AppException(f"Database error: {str(e)}")

    def get_by_device(self, db: Session, device_id: str):
        try:
            telemetry_list = (
                db.query(MotorTelemetry)
                .filter(MotorTelemetry.device_id == device_id)
                .order_by(MotorTelemetry.id.desc())  # Change this
                .all()
            )
            logger.info(
                "Fetched %d telemetry records for device_id=%s",
                len(telemetry_list),
                device_id
            )
            return telemetry_list
        except SQLAlchemyError as e:
            logger.error("Failed to fetch telemetry for device %s: %s", device_id, str(e))
            raise AppException(f"Database error: failed to fetch telemetry for device {device_id}")

    def delete(self, db: Session, telemetry_id: UUID):
        try:
            telemetry = db.query(MotorTelemetry).filter(MotorTelemetry.id == telemetry_id).first()
            if telemetry:
                db.delete(telemetry)
                db.commit()
                logger.info(
                    "Deleted telemetry record: id=%s, device_id=%s",
                    telemetry.id,
                    telemetry.device_id
                )
            else:
                logger.warning("Telemetry record not found: id=%s", telemetry_id)
                raise NotFoundException(f"Telemetry record {telemetry_id} not found")
            return telemetry
        except SQLAlchemyError as e:
            db.rollback()
            logger.error("Failed to delete telemetry id=%s: %s", telemetry_id, str(e))
            raise AppException(f"Database error: failed to delete telemetry {telemetry_id}")