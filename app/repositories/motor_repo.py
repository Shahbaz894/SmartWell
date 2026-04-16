from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.models.motor_log import MotorLog
from app.core.logger import logger
from app.core.exceptions import AppException


class MotorRepository:
    """
    Repository layer for motor log database operations.
    """

    def __init__(self, db: Session):
        self.db = db

    def create_log(self, log: MotorLog) -> MotorLog:
        """
        Persist a new motor log.
        """
        try:
            self.db.add(log)
            self.db.commit()
            self.db.refresh(log)

            logger.info(
                "Motor log created: id=%s, device_id=%s, trigger_type=%s, status=%s",
                log.id,
                log.device_id,
                log.trigger_type,
                log.status,
            )
            return log

        except SQLAlchemyError as exc:
            self.db.rollback()
            logger.error(
                "DB error creating motor log: device_id=%s, error=%s",
                log.device_id,
                exc,
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=f"Database error while creating motor log for device '{log.device_id}'",
            )

    def get_running_motor(self, device_id: str) -> MotorLog | None:
        """
        Fetch currently running motor log for a device.
        """
        try:
            return (
                self.db.query(MotorLog)
                .filter(
                    MotorLog.device_id == device_id,
                    MotorLog.end_time.is_(None),
                    MotorLog.status == "ON",
                )
                .first()
            )

        except SQLAlchemyError as exc:
            logger.error(
                "DB error fetching running motor: device_id=%s, error=%s",
                device_id,
                exc,
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=f"Database error while fetching running motor for device '{device_id}'",
            )

    def update_log(self, log: MotorLog) -> MotorLog:
        """
        Commit changes to an existing motor log.
        """
        try:
            self.db.commit()
            self.db.refresh(log)

            logger.info(
                "Motor log updated: id=%s, device_id=%s, status=%s",
                log.id,
                log.device_id,
                log.status,
            )
            return log

        except SQLAlchemyError as exc:
            self.db.rollback()
            logger.error(
                "DB error updating motor log: id=%s, device_id=%s, error=%s",
                log.id,
                log.device_id,
                exc,
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=f"Database error while updating motor log '{log.id}'",
            )