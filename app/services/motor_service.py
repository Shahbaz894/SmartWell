# app/services/motor_service.py
#
# Motor control service layer.
# Handles start / stop lifecycle of motor logs.
#
# ── AppException Usage ────────────────────────────────────────────────────────
#  Always called as AppException(status_code=int, detail=str).
# ──────────────────────────────────────────────────────────────────────────────

from datetime import datetime

from sqlalchemy.exc import SQLAlchemyError

from app.repositories.motor_repo import MotorRepository
from app.models.motor_log import MotorLog
from app.core.logger import logger
from app.core.exceptions import AppException


class MotorService:
    """
    Service layer for motor start/stop operations.

    Responsibilities
    ----------------
    - Prevent duplicate start when motor is already running.
    - Record start_time on start, end_time + duration_minutes on stop.
    - Delegate all persistence to MotorRepository.
    """

    def __init__(self, db):
        self.repo = MotorRepository(db)

    # ─────────────────────────────────────────────────────────────────────────
    # START
    # ─────────────────────────────────────────────────────────────────────────
    def start_motor(self, device_id: str, trigger: str):
        """
        Start the motor for a device, or return the existing log if already running.

        Parameters
        ----------
        device_id : str   ID of the device whose motor to start.
        trigger   : str   How the motor was triggered (e.g. "manual", "schedule").

        Returns
        -------
        MotorLog
            Either the newly created log, or the existing running log if the
            motor was already active (idempotent — no duplicate logs created).

        Raises
        ------
        AppException(400)   Database error during insert.
        """
        try:
            running = self.repo.get_running_motor(device_id)
            if running:
                logger.info(
                    "Motor already running: device_id=%s, log_id=%s, trigger=%s",
                    device_id, running.id, trigger,
                )
                return running

            log = MotorLog(
                device_id    = device_id,
                start_time   = datetime.utcnow(),
                trigger_type = trigger,
            )
            created = self.repo.create_log(log)
            logger.info(
                "Motor started: device_id=%s, log_id=%s, trigger=%s",
                device_id, created.id, trigger,
            )
            return created

        except AppException:
            raise

        except SQLAlchemyError as exc:
            logger.error(
                "DB error starting motor: device_id=%s, trigger=%s: %s",
                device_id, trigger, exc, exc_info=True,
            )
            raise AppException(
                status_code=400,
                detail=f"Database error: failed to start motor for device '{device_id}'",
            )

        except Exception as exc:
            logger.error(
                "Unexpected error starting motor: device_id=%s: %s",
                device_id, exc, exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=f"Unexpected error while starting motor: {exc}",
            )

    # ─────────────────────────────────────────────────────────────────────────
    # STOP
    # ─────────────────────────────────────────────────────────────────────────
    def stop_motor(self, device_id: str):
        """
        Stop the running motor for a device and record duration.

        Parameters
        ----------
        device_id : str   ID of the device whose motor to stop.

        Returns
        -------
        MotorLog
            The updated log with end_time and duration_minutes set.
        None
            If no motor was running for this device (no-op).

        Raises
        ------
        AppException(400)   Database error during update.
        """
        try:
            log = self.repo.get_running_motor(device_id)
            if not log:
                logger.warning(
                    "Stop called but no running motor: device_id=%s", device_id
                )
                return None

            log.end_time         = datetime.utcnow()
            duration             = log.end_time - log.start_time
            log.duration_minutes = int(duration.total_seconds() / 60)

            updated = self.repo.update_log(log)
            logger.info(
                "Motor stopped: device_id=%s, log_id=%s, duration=%d min",
                device_id, updated.id, updated.duration_minutes,
            )
            return updated

        except AppException:
            raise

        except SQLAlchemyError as exc:
            logger.error(
                "DB error stopping motor: device_id=%s: %s",
                device_id, exc, exc_info=True,
            )
            raise AppException(
                status_code=400,
                detail=f"Database error: failed to stop motor for device '{device_id}'",
            )

        except Exception as exc:
            logger.error(
                "Unexpected error stopping motor: device_id=%s: %s",
                device_id, exc, exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=f"Unexpected error while stopping motor: {exc}",
            )