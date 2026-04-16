from datetime import datetime

import requests
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logger import logger
from app.models.motor_log import MotorLog
from app.repositories.motor_repo import MotorRepository


class MotorService:
    """
    Service layer for motor start and stop operations.

    Responsibilities:
    - Send HTTP command to the target device using device_id
    - Prevent duplicate start if motor is already running
    - Record motor start and stop times
    - Store operator_name for billing, khata, and usage tracking
    - Update motor status as ON or OFF
    """

    def __init__(self, db: Session):
        self.repo = MotorRepository(db)

    def _send_motor_command_http(
        self,
        device_id: str,
        command: str,
        trigger_type: str,
        operator_name: str,
    ) -> None:
        """
        Send motor control command over HTTP.

        Args:
            device_id: Device identifier
            command: ON or OFF
            trigger_type: manual or schedule
            operator_name: Name of operator or source

        Raises:
            AppException: If HTTP command delivery fails
        """
        base_url = (settings.DEVICE_HTTP_URL or "").rstrip("/")

        if not base_url:
            logger.error("DEVICE_HTTP_URL is not configured")
            raise AppException(
                status_code=500,
                detail="DEVICE_HTTP_URL is not configured",
            )

        url = f"{base_url}/motor"

        payload = {
            "device_id": device_id,
            "command": command,
            "trigger_type": trigger_type,
            "operator_name": operator_name,
        }

        try:
            response = requests.post(url, json=payload, timeout=5)
            response.raise_for_status()

            logger.info(
                "HTTP motor command sent successfully: device_id=%s, command=%s, status_code=%s",
                device_id,
                command,
                response.status_code,
            )

        except requests.RequestException as exc:
            logger.error(
                "HTTP motor command failed: device_id=%s, command=%s, error=%s",
                device_id,
                command,
                exc,
                exc_info=True,
            )
            raise AppException(
                status_code=502,
                detail=f"Failed to send motor command '{command}' to device '{device_id}'",
            )

    def start_motor(
        self,
        device_id: str,
        trigger_type: str = "manual",
        operator_name: str = "",
    ) -> MotorLog:
        """
        Start motor for a specific device and create a running log entry.

        Args:
            device_id: Device identifier from path parameter
            trigger_type: manual or schedule
            operator_name: Name entered from frontend for billing and khata

        Returns:
            MotorLog: Newly created or existing running motor log

        Raises:
            AppException: For validation, HTTP, database, or unexpected errors
        """
        try:
            if not operator_name or not operator_name.strip():
                raise AppException(
                    status_code=400,
                    detail="operator_name is required",
                )

            normalized_trigger = (trigger_type or "manual").strip().lower()
            if normalized_trigger not in {"manual", "schedule"}:
                raise AppException(
                    status_code=400,
                    detail="trigger_type must be 'manual' or 'schedule'",
                )

            running = self.repo.get_running_motor(device_id)
            if running:
                logger.warning(
                    "Start requested but motor already running: device_id=%s, log_id=%s",
                    device_id,
                    running.id,
                )
                return running

            self._send_motor_command_http(
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
            device_id: Device identifier from path parameter
            operator_name: Optional name from frontend

        Returns:
            MotorLog | None: Updated stopped log or None if no running log exists

        Raises:
            AppException: For HTTP, database, or unexpected errors
        """
        try:
            log = self.repo.get_running_motor(device_id)
            if not log:
                logger.warning(
                    "Stop requested but no running motor found: device_id=%s",
                    device_id,
                )
                return None

            final_operator_name = (
                operator_name.strip()
                if operator_name and operator_name.strip()
                else log.operator_name
            )

            self._send_motor_command_http(
                device_id=device_id,
                command="OFF",
                trigger_type=log.trigger_type,
                operator_name=final_operator_name,
            )

            end_time = datetime.utcnow()
            duration = end_time - log.start_time

            log.end_time = end_time
            log.duration_minutes = max(1, int(duration.total_seconds() / 60))
            log.status = "OFF"
            log.operator_name = final_operator_name

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

    def is_motor_running(self, device_id: str) -> bool:
        """
        Check whether a motor is currently running for the given device.

        Args:
            device_id: Device identifier

        Returns:
            bool: True if running log exists, otherwise False
        """
        try:
            running = self.repo.get_running_motor(device_id)
            is_running = running is not None

            logger.info(
                "Motor running check: device_id=%s, is_running=%s",
                device_id,
                is_running,
            )
            return is_running

        except AppException:
            raise

        except Exception as exc:
            logger.error(
                "Unexpected error while checking motor running state: device_id=%s, error=%s",
                device_id,
                exc,
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail="Unexpected error while checking motor status",
            )

    def get_running_log(self, device_id: str) -> MotorLog | None:
        """
        Return currently running motor log for a device.

        Args:
            device_id: Device identifier

        Returns:
            MotorLog | None: Running log if exists, otherwise None
        """
        try:
            running = self.repo.get_running_motor(device_id)

            if running:
                logger.info(
                    "Running motor log fetched: device_id=%s, log_id=%s",
                    device_id,
                    running.id,
                )
            else:
                logger.info(
                    "No running motor log found: device_id=%s",
                    device_id,
                )

            return running

        except AppException:
            raise

        except Exception as exc:
            logger.error(
                "Unexpected error while fetching running motor log: device_id=%s, error=%s",
                device_id,
                exc,
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail="Unexpected error while fetching running motor log",
            )