# app/repositories/schedule_repo.py

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.models.schedule import Schedule
from app.core.logger import logger
from app.core.exceptions import AppException, NotFoundException


class ScheduleRepository:

    def __init__(self, db: Session):
        self.db = db

    def create_schedule(self, schedule: Schedule):
        try:
            self.db.add(schedule)
            self.db.commit()
            self.db.refresh(schedule)
            logger.info(
                "Schedule created: id=%s, device_id=%s, active=%s",
                schedule.id,
                schedule.device_id,
                schedule.is_active
            )
            return schedule
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(
                "Failed to create schedule for device %s: %s",
                schedule.device_id,
                str(e)
            )
            raise AppException(f"Database error: failed to create schedule for device {schedule.device_id}")

    def get_device_schedules(self, device_id: str):
        try:
            schedules = self.db.query(Schedule).filter(Schedule.device_id == device_id).all()
            logger.info(
                "Fetched %d schedules for device_id=%s",
                len(schedules),
                device_id
            )
            return schedules
        except SQLAlchemyError as e:
            logger.error("Failed to fetch schedules for device %s: %s", device_id, str(e))
            raise AppException(f"Database error: failed to fetch schedules for device {device_id}")

    def get_active_schedules(self):
        try:
            active_schedules = self.db.query(Schedule).filter(Schedule.is_active == True).all()
            logger.info("Fetched %d active schedules", len(active_schedules))
            return active_schedules
        except SQLAlchemyError as e:
            logger.error("Failed to fetch active schedules: %s", str(e))
            raise AppException("Database error: failed to fetch active schedules")

    def clear_schedule(self, device_id: str):
        """
        Deactivate all schedules for a device
        """
        try:
            schedules = self.db.query(Schedule).filter(Schedule.device_id == device_id).all()
            if not schedules:
                logger.warning("No schedules found to clear for device_id=%s", device_id)
                raise NotFoundException(f"No schedules found for device {device_id}")

            for sched in schedules:
                sched.is_active = False

            self.db.commit()
            logger.info("Cleared %d schedules for device_id=%s", len(schedules), device_id)
            return len(schedules)
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error("Failed to clear schedules for device %s: %s", device_id, str(e))
            raise AppException(f"Database error: failed to clear schedules for device {device_id}")