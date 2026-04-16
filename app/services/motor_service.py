from datetime import datetime

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.core.logger import logger
from app.models.motor_log import MotorLog
from app.repositories.motor_repo import MotorRepository
from app.services.mqtt_service import MQTTService


class MotorService:
    """
    Service layer for motor start/stop operations.

    Responsibilities:
    - Send MQTT command to the correct device using path parameter device_id.
    - Prevent duplicate start for already running motor.
    - Record motor start and stop times.
    - Store operator_name for khata, billing, and usage calculations.
    - Update status as ON/OFF.
    """

    def __init__(self, db: Session):
        self.repo = MotorRepository(db)
        self.mqtt_service = MQTTService()

    def start_motor(
        self,
        device_id: str,
        trigger_type: str = "manual",
        operator_name: str = "",
    ) -> MotorLog:
        """
        Start motor for a specific device and create a running log entry.

        Args:
            device_id: Device identifier from path parameter.
            trigger_type: manual or schedule.
            operator_name: Name entered from frontend for billing/khata use.

        Returns:
            MotorLog: Newly created or existing running motor log.

        Raises:
            AppException: For validation, MQTT, DB, or unexpected errors.
        """
        try:
            if not operator_name or not operator_name.strip():
                raise AppException(status_code=400, detail="operator_name is required")

            normalized_trigger = (trigger_type or "manual").strip().lower()
            if normalized_trigger not in {"manual", "schedule"}:
                raise AppException(status_code=400, detail="trigger_type must be 'manual' or 'schedule'")

            running = self.repo.get_running_motor(device_id)
            if running:
                logger.warning(
                    "Start requested but motor already running: device_id=%s, log_id=%s",
                    device_id,
                    running.id,
                )
                return running

            # Publish MQTT ON command for this specific device
            self.mqtt_service.publish_motor_command(
                device_id=device_id,
                command="ON",
                trigger_type=normalized_trigger,
                operator_name=operator_name.strip(),
            )

            log = MotorLog(
                device_id=device_id,
                start_time=datetime.utcnow(),
                trigger_type=normalized_trigger,
                operator_name=operator_name.strip(),
                status="ON",
            )

            created = self.repo.create_log(log)

            logger.info(
                "Motor started successfully: device_id=%s, log_id=%s, operator_name=%s",
                device_id,
                created.id,
                created.operator_name,
            )
            return created

        except AppException:
            raise

        except SQLAlchemyError as exc:
            logger.error(
                "DB error while starting motor: device_id=%s, error=%s",
                device_id,
                exc,
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=f"Database error while starting motor for device '{device_id}'",
            )

        except Exception as exc:
            logger.error(
                "Unexpected error while starting motor: device_id=%s, error=%s",
                device_id,
                exc,
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail="Unexpected error while starting motor",
            )

    def stop_motor(
        self,
        device_id: str,
        operator_name: str | None = None,
    ) -> MotorLog | None:
        """
        Stop motor for a specific device and close running log entry.

        Args:
            device_id: Device identifier from path parameter.
            operator_name: Optional name from frontend. If provided, can update latest log name.

        Returns:
            MotorLog | None: Updated stopped log or None if no running log exists.

        Raises:
            AppException: For MQTT, DB, or unexpected errors.
        """
        try:
            log = self.repo.get_running_motor(device_id)
            if not log:
                logger.warning("Stop requested but no running motor found: device_id=%s", device_id)
                return None

            # Publish MQTT OFF command for this specific device
            self.mqtt_service.publish_motor_command(
                device_id=device_id,
                command="OFF",
                trigger_type=log.trigger_type,
                operator_name=operator_name.strip() if operator_name else log.operator_name,
            )

            end_time = datetime.utcnow()
            duration = end_time - log.start_time

            log.end_time = end_time
            log.duration_minutes = max(1, int(duration.total_seconds() / 60))
            log.status = "OFF"

            if operator_name and operator_name.strip():
                log.operator_name = operator_name.strip()

            updated = self.repo.update_log(log)

            logger.info(
                "Motor stopped successfully: device_id=%s, log_id=%s, duration_minutes=%s",
                device_id,
                updated.id,
                updated.duration_minutes,
            )
            return updated

        except AppException:
            raise

        except SQLAlchemyError as exc:
            logger.error(
                "DB error while stopping motor: device_id=%s, error=%s",
                device_id,
                exc,
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=f"Database error while stopping motor for device '{device_id}'",
            )

        except Exception as exc:
            logger.error(
                "Unexpected error while stopping motor: device_id=%s, error=%s",
                device_id,
                exc,
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail="Unexpected error while stopping motor",
            )