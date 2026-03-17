# app/services/schedule_service.py

from datetime import datetime, time
from sqlalchemy.exc import SQLAlchemyError
from app.repositories.schedule_repo import ScheduleRepository
from app.services.motor_service import MotorService
from app.core.logger import logger
from app.core.exceptions import AppException


class ScheduleService:

    def __init__(self, db):
        self.repo = ScheduleRepository(db)
        self.motor_service = MotorService(db)

    def check_and_run(self):
        try:
            schedules = self.repo.get_active_schedules()
            now = datetime.utcnow().time()

            logger.info("Checking %d active schedules at UTC time %s", len(schedules), now)

            for schedule in schedules:
                pattern = schedule.pattern
                slots = pattern.get("daily_slots", [])

                for slot in slots:
                    try:
                        start = time.fromisoformat(slot["start"])
                        end = time.fromisoformat(slot["end"])

                        if start <= now <= end:
                            self.motor_service.start_motor(
                                schedule.device_id,
                                "schedule"
                            )
                            logger.info(
                                "Motor triggered by schedule: device_id=%s, slot=%s-%s",
                                schedule.device_id,
                                slot["start"],
                                slot["end"]
                            )
                    except Exception as slot_error:
                        logger.error(
                            "Failed to process schedule slot for device_id=%s: %s",
                            schedule.device_id,
                            str(slot_error)
                        )
        except SQLAlchemyError as e:
            logger.error("Failed to fetch active schedules: %s", str(e))
            raise AppException("Database error: failed to fetch active schedules")
        except Exception as e:
            logger.error("Unexpected error in schedule check: %s", str(e))
            raise AppException("Unexpected error while running schedules")