from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.core.exceptions import AppException, NotFoundException
from app.core.logger import logger
from app.models.vfd_command_log import VFDCommandLog


class VFDCommandLogRepository:
    """
    Repository layer for VFD command log operations.
    """

    def __init__(self, db: Session):
        self.db = db

    def create(self, command_log: VFDCommandLog) -> VFDCommandLog:
        """
        Create and persist a new VFD command log.
        """
        try:
            self.db.add(command_log)
            self.db.commit()
            self.db.refresh(command_log)

            logger.info(
                "VFD command log created: id=%s, device_id=%s, command=%s, status=%s",
                command_log.id,
                command_log.device_id,
                command_log.command,
                command_log.status,
            )
            return command_log

        except SQLAlchemyError as exc:
            self.db.rollback()
            logger.error(
                "DB error creating VFD command log: device_id=%s, command=%s, error=%s",
                command_log.device_id,
                command_log.command,
                exc,
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=f"Database error while creating VFD command log for device '{command_log.device_id}'",
            )

    def get_by_id(self, command_log_id: str) -> VFDCommandLog:
        """
        Fetch VFD command log by ID.
        """
        try:
            command_log = (
                self.db.query(VFDCommandLog)
                .filter(VFDCommandLog.id == command_log_id)
                .first()
            )

            if not command_log:
                logger.warning("VFD command log not found: id=%s", command_log_id)
                raise NotFoundException(detail="VFD command log not found")

            return command_log

        except NotFoundException:
            raise

        except SQLAlchemyError as exc:
            logger.error(
                "DB error fetching VFD command log: id=%s, error=%s",
                command_log_id,
                exc,
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=f"Database error while fetching VFD command log '{command_log_id}'",
            )

    def get_by_device(self, device_id: str, limit: int = 50) -> list[VFDCommandLog]:
        """
        Fetch recent VFD command logs for a device.
        """
        try:
            return (
                self.db.query(VFDCommandLog)
                .filter(VFDCommandLog.device_id == device_id)
                .order_by(VFDCommandLog.created_at.desc())
                .limit(limit)
                .all()
            )

        except SQLAlchemyError as exc:
            logger.error(
                "DB error fetching VFD command logs: device_id=%s, error=%s",
                device_id,
                exc,
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=f"Database error while fetching VFD command logs for device '{device_id}'",
            )

    def update_status(
        self,
        command_log_id: str,
        status: str,
        message: str | None = None,
    ) -> VFDCommandLog:
        """
        Update VFD command log status.
        """
        try:
            command_log = (
                self.db.query(VFDCommandLog)
                .filter(VFDCommandLog.id == command_log_id)
                .first()
            )

            if not command_log:
                logger.warning(
                    "VFD command log not found for update: id=%s",
                    command_log_id,
                )
                raise NotFoundException(detail="VFD command log not found")

            command_log.status = status
            command_log.message = message

            self.db.commit()
            self.db.refresh(command_log)

            logger.info(
                "VFD command log status updated: id=%s, status=%s",
                command_log.id,
                command_log.status,
            )
            return command_log

        except NotFoundException:
            raise

        except SQLAlchemyError as exc:
            self.db.rollback()
            logger.error(
                "DB error updating VFD command log: id=%s, error=%s",
                command_log_id,
                exc,
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=f"Database error while updating VFD command log '{command_log_id}'",
            )