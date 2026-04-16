import uuid
from datetime import datetime, time
from typing import Any

from sqlalchemy.exc import SQLAlchemyError

from app.core.exceptions import AppException, NotFoundException
from app.core.logger import logger
from app.models.schedule import Schedule
from app.repositories.schedule_repo import ScheduleRepository
from app.schemas.schedule_schema import ScheduleCreate
from app.services.motor_service import MotorService
from app.services.schedule_mqtt_service import ScheduleMQTTService


class ScheduleService:
    """
    Service layer for schedule operations.

    Responsibilities:
    - Create or update one schedule per device
    - Get schedule by device
    - Delete schedule by device
    - Run background schedule checks
    - Publish schedule changes to ESP32 over MQTT
    """

    def __init__(self, db):
        self.db = db
        self.repo = ScheduleRepository(db)
        self.motor_service = MotorService(db)
        self.schedule_mqtt_service = ScheduleMQTTService()

    def create_schedule(self, device_id: str, schedule_in: ScheduleCreate):
        """
        Create or update a device schedule, then publish it to ESP32.

        Args:
            device_id: Device identifier
            schedule_in: Validated schedule input

        Returns:
            Schedule: Created or updated schedule row
        """
        try:
            schedule = Schedule(
                id=str(uuid.uuid4()),
                device_id=device_id,
                schedule_type=schedule_in.schedule_type,
                pattern=schedule_in.pattern,
                schedule_name=schedule_in.schedule_name,
                is_active=True,
            )

            saved = self.repo.create_or_update(schedule)

            self.schedule_mqtt_service.publish_schedule_set(
                device_id=saved.device_id,
                schedule_type=saved.schedule_type,
                pattern=saved.pattern,
                schedule_name=saved.schedule_name,
                is_active=saved.is_active,
            )

            logger.info(
                "Schedule created or updated successfully: device_id=%s, schedule_id=%s",
                saved.device_id,
                saved.id,
            )
            return saved

        except AppException:
            raise

        except SQLAlchemyError as exc:
            logger.error(
                "DB error while creating schedule: device_id=%s, error=%s",
                device_id,
                exc,
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=f"Database error while creating schedule for device '{device_id}'",
            )

        except Exception as exc:
            logger.error(
                "Unexpected error while creating schedule: device_id=%s, error=%s",
                device_id,
                exc,
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail="Failed to create schedule",
            )

    def get_schedule(self, device_id: str):
        """
        Fetch schedule for a device.
        """
        try:
            schedule = self.repo.get_by_device(device_id)

            if not schedule:
                logger.warning("No schedule found: device_id=%s", device_id)
                raise NotFoundException(detail=f"No schedule found for device '{device_id}'")

            logger.info("Schedule fetched successfully: device_id=%s", device_id)
            return schedule

        except (AppException, NotFoundException):
            raise

        except Exception as exc:
            logger.error(
                "Unexpected error while fetching schedule: device_id=%s, error=%s",
                device_id,
                exc,
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail="Failed to fetch schedule",
            )

    def delete_schedule(self, device_id: str):
        """
        Delete a schedule for a device, then publish clear message to ESP32.
        """
        try:
            self.repo.delete(device_id)

            self.schedule_mqtt_service.publish_schedule_clear(device_id)

            logger.info("Schedule deleted successfully: device_id=%s", device_id)

        except (AppException, NotFoundException):
            raise

        except Exception as exc:
            logger.error(
                "Unexpected error while deleting schedule: device_id=%s, error=%s",
                device_id,
                exc,
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail="Failed to delete schedule",
            )

    def check_and_run(self):
        """
        Background scheduler logic.

        Rules:
        - Fetch all active schedules
        - Check whether current UTC time matches today's slots
        - Start motor if schedule says it should run and motor is not running
        - Stop motor if schedule says it should stop and running log was started by schedule
        """
        try:
            schedules = self.repo.get_active_schedules()

            now_dt = datetime.utcnow()
            now_time = now_dt.time()
            today_day = now_dt.day

            logger.info(
                "Schedule check started: active_schedule_count=%s, utc_time=%s",
                len(schedules),
                now_dt.isoformat(),
            )

            for schedule in schedules:
                try:
                    slots = self._extract_today_slots(schedule.pattern, today_day)
                    should_run = self._should_run_now(slots, now_time)

                    is_running = self.motor_service.is_motor_running(schedule.device_id)

                    if should_run and not is_running:
                        logger.info(
                            "Schedule triggered motor start: device_id=%s",
                            schedule.device_id,
                        )
                        self.motor_service.start_motor(
                            device_id=schedule.device_id,
                            trigger_type="schedule",
                            customer_name="Schedule",
                        )

                    elif not should_run and is_running:
                        running_log = self.motor_service.get_running_log(schedule.device_id)

                        if running_log and running_log.trigger_type == "schedule":
                            logger.info(
                                "Schedule triggered motor stop: device_id=%s",
                                schedule.device_id,
                            )
                            self.motor_service.stop_motor(
                                device_id=schedule.device_id,
                                customer_name="Schedule",
                            )

                except AppException as exc:
                    logger.error(
                        "Schedule execution error for device_id=%s: %s",
                        schedule.device_id,
                        getattr(exc, "detail", str(exc)),
                        exc_info=True,
                    )
                except Exception as exc:
                    logger.error(
                        "Unexpected schedule execution error for device_id=%s: %s",
                        schedule.device_id,
                        exc,
                        exc_info=True,
                    )

        except SQLAlchemyError as exc:
            logger.error(
                "Database error during schedule check: %s",
                exc,
                exc_info=True,
            )

        except Exception as exc:
            logger.error(
                "Unexpected schedule cron error: %s",
                exc,
                exc_info=True,
            )

    def _extract_today_slots(self, pattern: dict[str, Any], today_day: int) -> list[dict]:
        """
        Extract today's schedule slots from stored pattern.

        Supported pattern types:
        - monthly
        - monthly_custom
        """
        schedule_type = pattern.get("type")
        slots: list[dict] = []

        if schedule_type == "monthly":
            if today_day in pattern.get("days", []):
                slots = pattern.get("slots", [])

        elif schedule_type == "monthly_custom":
            slots = pattern.get("days", {}).get(str(today_day), [])

        return slots

    def _should_run_now(self, slots: list[dict], now_time: time) -> bool:
        """
        Return True if current time falls inside any provided slot.
        """
        for slot in slots:
            try:
                start = time.fromisoformat(slot["start"])
                end = time.fromisoformat(slot["end"])

                if start <= now_time <= end:
                    return True

            except (KeyError, ValueError, TypeError) as exc:
                logger.error(
                    "Invalid schedule slot format: slot=%s, error=%s",
                    slot,
                    exc,
                    exc_info=True,
                )

        return False