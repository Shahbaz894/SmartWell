# app/services/motor_service.py

from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
from app.repositories.motor_repo import MotorRepository
from app.models.motor_log import MotorLog
from app.core.logger import logger
from app.core.exceptions import AppException


class MotorService:

    def __init__(self, db):
        self.repo = MotorRepository(db)

    def start_motor(self, device_id, trigger):
        try:
            running = self.repo.get_running_motor(device_id)
            if running:
                logger.info(
                    "Motor already running for device_id=%s, trigger=%s",
                    device_id,
                    trigger
                )
                return running

            log = MotorLog(
                device_id=device_id,
                start_time=datetime.utcnow(),
                trigger_type=trigger
            )

            created_log = self.repo.create_log(log)
            logger.info(
                "Motor started: device_id=%s, log_id=%s, trigger=%s",
                device_id,
                created_log.id,
                trigger
            )
            return created_log

        except SQLAlchemyError as e:
            logger.error(
                "Failed to start motor for device_id=%s, trigger=%s: %s",
                device_id,
                trigger,
                str(e)
            )
            raise AppException(f"Database error: failed to start motor for device {device_id}")

    def stop_motor(self, device_id):
        try:
            log = self.repo.get_running_motor(device_id)
            if not log:
                logger.warning("No running motor found for device_id=%s", device_id)
                return None

            log.end_time = datetime.utcnow()
            duration = log.end_time - log.start_time
            log.duration_minutes = int(duration.total_seconds() / 60)

            updated_log = self.repo.update_log(log)
            logger.info(
                "Motor stopped: device_id=%s, log_id=%s, duration=%d minutes",
                device_id,
                updated_log.id,
                updated_log.duration_minutes
            )
            return updated_log

        except SQLAlchemyError as e:
            logger.error(
                "Failed to stop motor for device_id=%s: %s",
                device_id,
                str(e)
            )
            raise AppException(f"Database error: failed to stop motor for device {device_id}")