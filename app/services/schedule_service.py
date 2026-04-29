import uuid
from datetime import datetime, time
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException, NotFoundException
from app.core.logger import logger
from app.models.device import Device
from app.models.schedule import Schedule
from app.repositories.schedule_repo import ScheduleRepository
from app.schemas.schedule_schema import ScheduleCreate
from app.services.motor_service import MotorService


class ScheduleService:
    """
    Service layer for device schedules.

    MQTT design:
    - ScheduleService does not publish MQTT directly.
    - ScheduleService calls MotorService.
    - MotorService publishes MQTT commands to ESP32.
    - ESP32 receives ON or OFF on:
        tubewell/{device_uid}/motor
    """

    def __init__(self, db: Session):
        self.db = db
        self.repo = ScheduleRepository(db)
        self.motor_service = MotorService(db)

    def _get_device(self, device_id: str) -> Device:
        """
        Validate that a device exists before schedule operation.
        """
        device = self.db.query(Device).filter(Device.id == device_id).first()

        if not device:
            logger.warning("Schedule device not found: device_id=%s", device_id)
            raise AppException(
                status_code=404,
                detail=f"Device '{device_id}' not found",
            )

        return device

    def create_schedule(self, device_id: str, schedule_in: ScheduleCreate) -> Schedule:
        """
        Create or update one schedule for a device.
        """
        try:
            device = self._get_device(device_id)

            logger.info(
                "Creating schedule: device_id=%s device_uid=%s schedule_type=%s",
                device_id,
                device.device_uid,
                schedule_in.schedule_type,
            )

            schedule = Schedule(
                id=str(uuid.uuid4()),
                device_id=device_id,
                schedule_type=schedule_in.schedule_type,
                pattern=schedule_in.pattern,
                schedule_name=schedule_in.schedule_name,
                is_active=True,
            )

            saved = self.repo.create_or_update(schedule)

            logger.info(
                "Schedule saved: schedule_id=%s device_id=%s device_uid=%s",
                saved.id,
                device_id,
                device.device_uid,
            )

            return saved

        except AppException:
            raise

        except SQLAlchemyError as exc:
            logger.error(
                "Schedule DB error: device_id=%s db_error=%s",
                device_id,
                str(exc.orig) if hasattr(exc, "orig") else str(exc),
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=f"Database error while creating schedule: {str(exc.orig) if hasattr(exc, 'orig') else str(exc)}",
            )

        except Exception as exc:
            logger.error(
                "Schedule unexpected error: device_id=%s error_type=%s error=%s",
                device_id,
                type(exc).__name__,
                str(exc),
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=f"Unexpected error while creating schedule: {type(exc).__name__}: {str(exc)}",
            )

    def get_schedule(self, device_id: str) -> Schedule:
        """
        Fetch schedule for one device.
        """
        try:
            self._get_device(device_id)

            schedule = self.repo.get_by_device(device_id)

            if not schedule:
                raise AppException(
                    status_code=404,
                    detail=f"No schedule found for device '{device_id}'",
                )

            return schedule

        except AppException:
            raise

        except Exception as exc:
            logger.error(
                "Schedule fetch error: device_id=%s error_type=%s error=%s",
                device_id,
                type(exc).__name__,
                str(exc),
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=f"Failed to fetch schedule: {type(exc).__name__}: {str(exc)}",
            )

    def delete_schedule(self, device_id: str) -> None:
        """
        Delete schedule for one device.
        """
        try:
            self._get_device(device_id)
            self.repo.delete(device_id)

            logger.info("Schedule deleted: device_id=%s", device_id)

        except (AppException, NotFoundException):
            raise

        except Exception as exc:
            logger.error(
                "Schedule delete error: device_id=%s error_type=%s error=%s",
                device_id,
                type(exc).__name__,
                str(exc),
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=f"Failed to delete schedule: {type(exc).__name__}: {str(exc)}",
            )

    def check_and_run(self) -> None:
        """
        Background schedule checker.

        This method:
        - Reads active schedules.
        - Checks current UTC time.
        - Calls MotorService.start_motor().
        - Calls MotorService.stop_motor().
        - MotorService sends MQTT command to ESP32.
        """
        try:
            schedules = self.repo.get_active_schedules()

            now_dt = datetime.utcnow()
            now_time = now_dt.time()
            today_day = now_dt.day

            logger.info(
                "Schedule check started: count=%s utc_time=%s",
                len(schedules),
                now_dt.isoformat(),
            )

            for schedule in schedules:
                try:
                    device = self._get_device(schedule.device_id)

                    slots = self._extract_today_slots(schedule.pattern, today_day)
                    should_run = self._should_run_now(slots, now_time)
                    is_running = self.motor_service.is_motor_running(schedule.device_id)

                    logger.info(
                        "Schedule checked: device_id=%s device_uid=%s should_run=%s is_running=%s",
                        schedule.device_id,
                        device.device_uid,
                        should_run,
                        is_running,
                    )

                    if should_run and not is_running:
                        self.motor_service.start_motor(
                            device_id=schedule.device_id,
                            trigger_type="schedule",
                            customer_name="Schedule",
                        )

                    elif not should_run and is_running:
                        running_log = self.motor_service.get_running_log(schedule.device_id)

                        if running_log and running_log.trigger_type == "schedule":
                            self.motor_service.stop_motor(
                                device_id=schedule.device_id,
                                customer_name="Schedule",
                            )

                except AppException as exc:
                    logger.error(
                        "Schedule execution AppException: device_id=%s detail=%s",
                        schedule.device_id,
                        getattr(exc, "detail", str(exc)),
                        exc_info=True,
                    )

                except Exception as exc:
                    logger.error(
                        "Schedule execution error: device_id=%s error_type=%s error=%s",
                        schedule.device_id,
                        type(exc).__name__,
                        str(exc),
                        exc_info=True,
                    )

        except Exception as exc:
            logger.error(
                "Schedule cron error: error_type=%s error=%s",
                type(exc).__name__,
                str(exc),
                exc_info=True,
            )

    def _extract_today_slots(self, pattern: dict[str, Any], today_day: int) -> list[dict]:
        """
        Extract today's slots from schedule pattern.
        """
        if not isinstance(pattern, dict):
            logger.error(
                "Invalid schedule pattern: expected=dict actual=%s value=%s",
                type(pattern).__name__,
                pattern,
            )
            return []

        schedule_type = pattern.get("type")
        slots: list[dict] = []

        if schedule_type == "monthly":
            if today_day in pattern.get("days", []):
                slots = pattern.get("slots", [])

        elif schedule_type == "monthly_custom":
            slots = pattern.get("days", {}).get(str(today_day), [])

        else:
            logger.warning(
                "Unknown schedule type: type=%s pattern=%s",
                schedule_type,
                pattern,
            )

        if not isinstance(slots, list):
            logger.error(
                "Invalid slots format: expected=list actual=%s value=%s",
                type(slots).__name__,
                slots,
            )
            return []

        return slots

    def _should_run_now(self, slots: list[dict], now_time: time) -> bool:
        """
        Check if current UTC time is inside a schedule slot.
        """
        for slot in slots:
            try:
                start = time.fromisoformat(slot["start"])
                end = time.fromisoformat(slot["end"])

                if start <= now_time <= end:
                    return True

            except (KeyError, ValueError, TypeError) as exc:
                logger.error(
                    "Invalid slot: slot=%s error_type=%s error=%s",
                    slot,
                    type(exc).__name__,
                    str(exc),
                    exc_info=True,
                )

        return False