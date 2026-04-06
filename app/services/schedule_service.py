import uuid
from datetime import datetime, time
from sqlalchemy.exc import SQLAlchemyError

from app.repositories.schedule_repo import ScheduleRepository
from app.services.motor_service import MotorService
from app.models.schedule import Schedule
from app.schemas.schedule_schema import ScheduleCreate
from app.core.logger import logger
from app.core.exceptions import AppException

class ScheduleService:

    def __init__(self, db):
        self.db = db
        self.repo = ScheduleRepository(db)
        self.motor_service = MotorService(db)

    def check_and_run(self):
        """
        Background task logic to check active schedules and toggle motors.
        """
        try:
            schedules = self.repo.get_active_schedules()
            # Note: Ensure your server/DB uses consistent timezones (UTC recommended)
            now = datetime.utcnow().time()

            logger.info("CRON: Checking %d active schedules at UTC %s", len(schedules), now.strftime("%H:%M:%S"))

            for schedule in schedules:
                pattern = schedule.pattern
                slots = pattern.get("daily_slots", [])
                
                # Logic: Should the motor be on right now based on THIS schedule?
                should_be_running = False
                for slot in slots:
                    try:
                        start = time.fromisoformat(slot["start"])
                        end = time.fromisoformat(slot["end"])

                        if start <= now <= end:
                            should_be_running = True
                            break 
                    except (ValueError, KeyError) as slot_error:
                        logger.error("FORMAT_ERROR: Invalid slot format for device %s: %s", schedule.device_id, slot_error)

                # Fetch current motor state to decide action
                is_running = self.motor_service.is_motor_running(schedule.device_id)

                if should_be_running:
                    if not is_running:
                        logger.info("SCHEDULE_ACTION: Starting motor for device %s (Time Slot Active)", schedule.device_id)
                        self.motor_service.start_motor(schedule.device_id, "schedule")
                    else:
                        # Motor is already running (either by this schedule or manually)
                        # We do nothing to avoid duplicate logs or interrupting a manual run
                        pass
                else:
                    # If time is outside slots, but a motor log is still open...
                    if is_running:
                        # Optional: Only stop if it was started by a 'schedule'
                        # This prevents stopping a motor a user manually turned on
                        running_log = self.motor_service.get_running_log(schedule.device_id)
                        if running_log and running_log.trigger_type == "schedule":
                            logger.info("SCHEDULE_ACTION: Stopping motor for device %s (Slot Ended)", schedule.device_id)
                            self.motor_service.stop_motor(schedule.device_id)

        except SQLAlchemyError as e:
            logger.error("DB_ERROR in check_and_run: %s", str(e))
        except Exception as e:
            logger.error("UNEXPECTED_ERROR in schedule check: %s", str(e))

    def create_schedule(self, device_id: str, schedule_in: ScheduleCreate):
        """
        Converts Pydantic Schema to SQLAlchemy Model and saves via Repo.
        """
        try:
            logger.info("SERVICE: Creating new schedule for device %s", device_id)
            
            db_schedule = Schedule(
                id=str(uuid.uuid4()),
                device_id=device_id,
                schedule_type=schedule_in.schedule_type,
                pattern=schedule_in.pattern,
                schedule_name=schedule_in.schedule_name,
                is_active=True
            )
            
            created_schedule = self.repo.create_schedule(db_schedule)
            return created_schedule

        except AppException as ae:
            # Re-raise known application errors (like DB failures from repo)
            raise ae
        except Exception as e:
            logger.error("SERVICE_ERROR: Failed to create schedule for %s: %s", device_id, str(e))
            raise AppException(f"Unexpected error while creating schedule for {device_id}")