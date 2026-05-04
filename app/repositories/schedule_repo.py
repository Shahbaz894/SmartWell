from typing import Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException, NotFoundException
from app.core.logger import logger
from app.models.schedule import Schedule


class ScheduleRepository:
    """
    Repository layer for schedule database operations.

    This repository is initialized with a SQLAlchemy session.
    ScheduleService calls it as:

        self.repo = ScheduleRepository(db)
    """

    def __init__(self, db: Session):
        self.db = db

    def create(self, schedule: Schedule) -> Schedule:
        """
        Create a new schedule.
        """
        try:
            self.db.add(schedule)
            self.db.flush()
            self.db.refresh(schedule)

            logger.info(
                "Schedule persisted: id=%s device_id=%s schedule_type=%s",
                schedule.id,
                schedule.device_id,
                schedule.schedule_type,
            )

            return schedule

        except SQLAlchemyError as exc:
            logger.error(
                "DB error while creating schedule: device_id=%s error=%s",
                getattr(schedule, "device_id", None),
                str(exc),
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail="Database error while creating schedule",
            )

    def update(self, schedule: Schedule) -> Schedule:
        """
        Update an existing schedule.
        """
        try:
            self.db.flush()
            self.db.refresh(schedule)

            logger.info(
                "Schedule updated: id=%s device_id=%s schedule_type=%s",
                schedule.id,
                schedule.device_id,
                schedule.schedule_type,
            )

            return schedule

        except SQLAlchemyError as exc:
            logger.error(
                "DB error while updating schedule: id=%s error=%s",
                getattr(schedule, "id", None),
                str(exc),
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail="Database error while updating schedule",
            )

    def get_by_device_id(self, device_id: str) -> Optional[Schedule]:
        """
        Get schedule by internal device UUID.
        """
        try:
            return (
                self.db.query(Schedule)
                .filter(Schedule.device_id == str(device_id))
                .first()
            )

        except SQLAlchemyError as exc:
            logger.error(
                "DB error while fetching schedule: device_id=%s error=%s",
                device_id,
                str(exc),
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=f"Database error while fetching schedule for device '{device_id}'",
            )

    def delete_by_device_id(self, device_id: str) -> None:
        """
        Delete schedule by internal device UUID.
        """
        try:
            schedule = self.get_by_device_id(device_id)

            if not schedule:
                raise NotFoundException(detail="Schedule not found")

            self.db.delete(schedule)
            self.db.flush()

            logger.info(
                "Schedule deleted: id=%s device_id=%s",
                schedule.id,
                schedule.device_id,
            )

        except NotFoundException:
            raise

        except SQLAlchemyError as exc:
            logger.error(
                "DB error while deleting schedule: device_id=%s error=%s",
                device_id,
                str(exc),
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=f"Database error while deleting schedule for device '{device_id}'",
            )