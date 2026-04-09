# from sqlalchemy.orm import Session
# from sqlalchemy.exc import SQLAlchemyError
# from app.models.schedule import Schedule
# from app.core.logger import logger
# from app.core.exceptions import AppException, NotFoundException

# class ScheduleRepository:
#     def __init__(self, db: Session):
#         self.db = db

#     def create_schedule(self, schedule: Schedule):
#         try:
#             self.db.add(schedule)
#             self.db.commit()
#             self.db.refresh(schedule)
#             logger.info("SUCCESS: Schedule %s created for device %s", schedule.id, schedule.device_id)
#             return schedule
#         except SQLAlchemyError as e:
#             self.db.rollback()
#             logger.error("DB_ERROR (Create Schedule) for %s: %s", schedule.device_id, str(e))
#             raise AppException(f"Database error: failed to create schedule for device {schedule.device_id}")

#     def get_device_schedules(self, device_id: str):
#         try:
#             schedules = self.db.query(Schedule).filter(Schedule.device_id == device_id).all()
#             logger.info("Fetched %d schedules for device_id=%s", len(schedules), device_id)
#             return schedules
#         except SQLAlchemyError as e:
#             logger.error("Failed to fetch schedules for device %s: %s", device_id, str(e))
#             raise AppException(f"Database error: failed to fetch schedules for device {device_id}")

#     def get_active_schedules(self):
#         try:
#             active_schedules = self.db.query(Schedule).filter(Schedule.is_active == True).all()
#             logger.info("Fetched %d active schedules", len(active_schedules))
#             return active_schedules
#         except SQLAlchemyError as e:
#             logger.error("Failed to fetch active schedules: %s", str(e))
#             raise AppException("Database error: failed to fetch active schedules")

#     def clear_schedule(self, device_id: str):
#         """
#         Deactivate all schedules for a device using an efficient update.
#         """
#         try:
#             # We first check if they exist to satisfy your NotFoundException requirement
#             query = self.db.query(Schedule).filter(Schedule.device_id == device_id)
#             schedules_count = query.count()

#             if schedules_count == 0:
#                 logger.warning("No schedules found to clear for device_id=%s", device_id)
#                 raise NotFoundException(f"No schedules found for device {device_id}")

#             # Efficiently update all records to inactive
#             updated_count = query.update({"is_active": False}, synchronize_session=False)
            
#             self.db.commit()
#             logger.info("Cleared %d schedules for device_id=%s", updated_count, device_id)
#             return updated_count
#         except (SQLAlchemyError, NotFoundException) as e:
#             self.db.rollback()
#             if isinstance(e, NotFoundException):
#                 raise e
#             logger.error("Failed to clear schedules for device %s: %s", device_id, str(e))
#             raise AppException(f"Database error: failed to clear schedules for device {device_id}")
# app/repositories/schedule_repo.py

# app/repositories/schedule_repo.py

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.models.schedule import Schedule
from app.core.logger import logger
from app.core.exceptions import AppException, NotFoundException

class ScheduleRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_device(self, device_id: str):
        try:
            schedule = self.db.query(Schedule).filter(Schedule.device_id == device_id).first()
            if schedule:
                logger.info("Fetched schedule for device_id=%s", device_id)
            else:
                logger.info("No schedule found for device_id=%s", device_id)
            return schedule
        except SQLAlchemyError as e:
            logger.error("DB_ERROR (get_by_device) for device %s: %s", device_id, str(e))
            raise AppException(f"Database error: failed to fetch schedule for device {device_id}")

    def create_or_update(self, schedule: Schedule):
        try:
            existing = self.get_by_device(schedule.device_id)

            if existing:
                existing.pattern = schedule.pattern
                existing.schedule_type = schedule.schedule_type
                existing.schedule_name = schedule.schedule_name
                existing.is_active = True
                self.db.commit()
                self.db.refresh(existing)
                logger.info("Updated schedule %s for device_id=%s", existing.id, schedule.device_id)
                return existing

            self.db.add(schedule)
            self.db.commit()
            self.db.refresh(schedule)
            logger.info("Created schedule %s for device_id=%s", schedule.id, schedule.device_id)
            return schedule

        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error("DB_ERROR (create_or_update) for device %s: %s", schedule.device_id, str(e))
            raise AppException(f"Database error: failed to create or update schedule for device {schedule.device_id}")

    def get_active_schedules(self):
        try:
            active_schedules = self.db.query(Schedule).filter(Schedule.is_active == True).all()
            logger.info("Fetched %d active schedules", len(active_schedules))
            return active_schedules
        except SQLAlchemyError as e:
            logger.error("DB_ERROR (get_active_schedules): %s", str(e))
            raise AppException("Database error: failed to fetch active schedules")

    def delete(self, device_id: str):
        try:
            obj = self.get_by_device(device_id)
            if not obj:
                logger.warning("No schedule found to delete for device_id=%s", device_id)
                raise NotFoundException(f"No schedule found for device {device_id}")

            self.db.delete(obj)
            self.db.commit()
            logger.info("Deleted schedule %s for device_id=%s", obj.id, device_id)
            return True
        except (SQLAlchemyError, NotFoundException) as e:
            self.db.rollback()
            if isinstance(e, NotFoundException):
                raise e
            logger.error("DB_ERROR (delete) for device %s: %s", device_id, str(e))
            raise AppException(f"Database error: failed to delete schedule for device {device_id}")