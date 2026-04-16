from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.models.motor_parameter import MotorTelemetry
from app.core.exceptions import AppException, NotFoundException
from app.core.logger import logger


class MotorTelemetryRepository:
    """
    Repository layer for motor telemetry database operations.
    """

    def create(self, db: Session, telemetry: MotorTelemetry) -> MotorTelemetry:
        """
        Persist a telemetry record.
        """
        try:
            db.add(telemetry)
            db.flush()
            db.refresh(telemetry)

            logger.info(
                "Telemetry persisted: id=%s, device_id=%s, is_live=%s",
                telemetry.id,
                telemetry.device_id,
                telemetry.is_live,
            )
            return telemetry

        except SQLAlchemyError as exc:
            logger.error(
                "DB error while persisting telemetry: device_id=%s, error=%s",
                telemetry.device_id,
                exc,
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=f"Database error while creating telemetry for device '{telemetry.device_id}'",
            )

    def get_by_device(self, db: Session, device_id: str):
        """
        Return all telemetry records for a device, newest first.
        """
        try:
            return (
                db.query(MotorTelemetry)
                .filter(MotorTelemetry.device_id == device_id)
                .order_by(MotorTelemetry.timestamp.desc())
                .all()
            )

        except SQLAlchemyError as exc:
            logger.error(
                "DB error while fetching telemetry: device_id=%s, error=%s",
                device_id,
                exc,
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=f"Database error while fetching telemetry for device '{device_id}'",
            )

    def get_latest_live(self, db: Session, device_id: str) -> Optional[MotorTelemetry]:
        """
        Return latest live telemetry record for a device.
        """
        try:
            return (
                db.query(MotorTelemetry)
                .filter(
                    MotorTelemetry.device_id == device_id,
                    MotorTelemetry.is_live == 1,
                )
                .order_by(MotorTelemetry.timestamp.desc())
                .first()
            )

        except SQLAlchemyError as exc:
            logger.error(
                "DB error while fetching latest live telemetry: device_id=%s, error=%s",
                device_id,
                exc,
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=f"Database error while fetching latest live telemetry for device '{device_id}'",
            )

    def delete(self, db: Session, telemetry_id: str) -> MotorTelemetry:
        """
        Delete telemetry by ID.
        """
        try:
            telemetry = (
                db.query(MotorTelemetry)
                .filter(MotorTelemetry.id == telemetry_id)
                .first()
            )

            if not telemetry:
                raise NotFoundException(detail="Telemetry not found")

            db.delete(telemetry)
            db.flush()

            logger.info(
                "Telemetry deleted from session: id=%s, device_id=%s",
                telemetry.id,
                telemetry.device_id,
            )
            return telemetry

        except NotFoundException:
            raise

        except SQLAlchemyError as exc:
            logger.error(
                "DB error while deleting telemetry: telemetry_id=%s, error=%s",
                telemetry_id,
                exc,
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=f"Database error while deleting telemetry '{telemetry_id}'",
            )