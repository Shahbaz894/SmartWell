from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.core.exceptions import AppException, NotFoundException
from app.core.logger import logger
from app.models.motor_parameter import MotorTelemetry
from app.repositories.motor_telemetry_repo import MotorTelemetryRepository
from app.schemas.motor_telemetry_schema import MotorTelemetryCreate


class MotorTelemetryService:
    """
    Service layer for motor telemetry operations.

    Responsibilities:
    - Validate telemetry packets coming from ESP32 over HTTP
    - Persist live and offline telemetry packets
    - Fetch telemetry for dashboard and API usage
    - Fetch latest live telemetry without delay
    - Delete telemetry records when required
    """

    def __init__(self):
        self.repo = MotorTelemetryRepository()

    def create_telemetry(
        self,
        db: Session,
        device_id: str,
        data: MotorTelemetryCreate,
    ) -> MotorTelemetry:
        """
        Create and store telemetry for a specific device.

        Args:
            db: Active SQLAlchemy session
            device_id: Device ID from HTTP path parameter
            data: Validated telemetry payload

        Returns:
            MotorTelemetry: Created telemetry row

        Raises:
            AppException: On validation or database failure
        """
        try:
            telemetry = MotorTelemetry(
                device_id=device_id,
                timestamp=data.timestamp,
                freq=data.freq,
                current=data.current,
                voltage=data.voltage,
                dcbus=data.dcbus,
                power=data.power,
                energy_in=data.energy_in,
                fault=data.fault,
                fault_code=data.fault_code,
                status_code=data.status_code,
                reference_freq=data.reference_freq,
                motor_speed=data.motor_speed,
                power_percent=data.power_percent,
                torque_percent=data.torque_percent,
                is_live=data.is_live,
            )

            created = self.repo.create(db, telemetry)
            db.commit()

            logger.info(
                "Telemetry created successfully: device_id=%s, telemetry_id=%s, is_live=%s",
                device_id,
                created.id,
                created.is_live,
            )
            return created

        except AppException:
            db.rollback()
            raise

        except SQLAlchemyError as exc:
            db.rollback()
            logger.error(
                "DB error while creating telemetry: device_id=%s, error=%s",
                device_id,
                exc,
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=f"Database error while creating telemetry for device '{device_id}'",
            )

        except Exception as exc:
            db.rollback()
            logger.error(
                "Unexpected error while creating telemetry: device_id=%s, error=%s",
                device_id,
                exc,
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail="Unexpected error while creating telemetry",
            )

    def get_device_telemetry(self, db: Session, device_id: str):
        """
        Return all telemetry for a device, newest first.
        """
        try:
            records = self.repo.get_by_device(db, device_id)

            logger.info(
                "Telemetry fetched successfully: device_id=%s, count=%s",
                device_id,
                len(records),
            )
            return records

        except AppException:
            raise

        except Exception as exc:
            logger.error(
                "Unexpected error while fetching telemetry: device_id=%s, error=%s",
                device_id,
                exc,
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail="Unexpected error while fetching telemetry",
            )

    def get_latest_live(self, db: Session, device_id: str):
        """
        Return latest live telemetry packet for a device.
        """
        try:
            latest = self.repo.get_latest_live(db, device_id)

            if latest:
                logger.info(
                    "Latest live telemetry fetched: device_id=%s, telemetry_id=%s",
                    device_id,
                    latest.id,
                )
            else:
                logger.warning(
                    "No live telemetry found: device_id=%s",
                    device_id,
                )

            return latest

        except AppException:
            raise

        except Exception as exc:
            logger.error(
                "Unexpected error while fetching latest live telemetry: device_id=%s, error=%s",
                device_id,
                exc,
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail="Unexpected error while fetching latest live telemetry",
            )

    def delete_telemetry(self, db: Session, telemetry_id: UUID):
        """
        Delete a telemetry record by ID.
        """
        try:
            deleted = self.repo.delete(db, str(telemetry_id))
            db.commit()

            logger.info(
                "Telemetry deleted successfully: telemetry_id=%s, device_id=%s",
                deleted.id,
                deleted.device_id,
            )
            return deleted

        except (AppException, NotFoundException):
            db.rollback()
            raise

        except Exception as exc:
            db.rollback()
            logger.error(
                "Unexpected error while deleting telemetry: telemetry_id=%s, error=%s",
                telemetry_id,
                exc,
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail="Unexpected error while deleting telemetry",
            )