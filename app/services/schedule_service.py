import uuid
from datetime import datetime, time
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

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
    - ScheduleService checks saved schedules.
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
        Resolve a device from either:
        - device_uid, for example ESP32_001_TW
        - internal UUID devices.id
        """
        device = (
            self.db.query(Device)
            .filter(Device.device_uid == device_id)
            .first()
        )

        if device:
            return device

        try:
            parsed_id = UUID(str(device_id))
        except ValueError:
            parsed_id = None

        if parsed_id is not None:
            device = (
                self.db.query(Device)
                .filter(Device.id == parsed_id)
                .first()
            )

        if not device:
            logger.warning(
                "Schedule device not found: device_id=%s",
                device_id,
            )
            raise AppException(
                status_code=404,
                detail=f"Device '{device_id}' not found",
            )

        return device

    def create_schedule(
        self,
        device_id: str,
        schedule_in: ScheduleCreate,
    ) -> Schedule:
        """
        Create or update one schedule for a device.

        This method uses the repository methods you currently have:
        - get_by_device_id()
        - create()
        - update()
        """
        try:
            device = self._get_device(device_id)

            logger.info(
                "Schedule save requested: input_device_id=%s device_id=%s device_uid=%s schedule_type=%s",
                device_id,
                device.id,
                device.device_uid,
                schedule_in.schedule_type,
            )

            existing = self.repo.get_by_device_id(str(device.id))

            if existing:
                existing.schedule_type = schedule_in.schedule_type
                existing.pattern = schedule_in.pattern
                existing.schedule_name = schedule_in.schedule_name
                existing.is_active = True

                saved = self.repo.update(existing)

                logger.info(
                    "Schedule updated: schedule_id=%s device_id=%s device_uid=%s",
                    saved.id,
                    device.id,
                    device.device_uid,
                )

            else:
                schedule = Schedule(
                    id=str(uuid.uuid4()),
                    device_id=str(device.id),
                    schedule_type=schedule_in.schedule_type,
                    pattern=schedule_in.pattern,
                    schedule_name=schedule_in.schedule_name,
                    is_active=True,
                )

                saved = self.repo.create(schedule)

                logger.info(
                    "Schedule created: schedule_id=%s device_id=%s device_uid=%s",
                    saved.id,
                    device.id,
                    device.device_uid,
                )

            self.db.commit()
            self.db.refresh(saved)

            return saved

        except AppException:
            self.db.rollback()
            raise

        except SQLAlchemyError as exc:
            self.db.rollback()
            logger.error(
                "Schedule DB error: device_id=%s db_error=%s",
                device_id,
                str(exc.orig) if hasattr(exc, "orig") else str(exc),
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=(
                    "Database error while creating schedule: "
                    f"{str(exc.orig) if hasattr(exc, 'orig') else str(exc)}"
                ),
            )

        except Exception as exc:
            self.db.rollback()
            logger.error(
                "Schedule unexpected error: device_id=%s error_type=%s error=%s",
                device_id,
                type(exc).__name__,
                str(exc),
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=(
                    "Unexpected error while creating schedule: "
                    f"{type(exc).__name__}: {str(exc)}"
                ),
            )

    def get_schedule(self, device_id: str) -> Schedule:
        """
        Fetch schedule for one device.

        Accepts both:
        - device_uid
        - internal UUID
        """
        try:
            device = self._get_device(device_id)

            schedule = self.repo.get_by_device_id(str(device.id))

            if not schedule:
                raise AppException(
                    status_code=404,
                    detail=f"No schedule found for device '{device_id}'",
                )

            logger.info(
                "Schedule fetched: schedule_id=%s device_id=%s device_uid=%s",
                schedule.id,
                device.id,
                device.device_uid,
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
            device = self._get_device(device_id)

            self.repo.delete_by_device_id(str(device.id))
            self.db.commit()

            logger.info(
                "Schedule deleted: device_id=%s device_uid=%s",
                device.id,
                device.device_uid,
            )

        except (AppException, NotFoundException):
            self.db.rollback()
            raise

        except Exception as exc:
            self.db.rollback()
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

        Supports:
        - daily schedule
        - weekly schedule
        - monthly schedule
        - monthly_custom schedule

        For your weekly JSON, it reads:

        pattern["days"][i]["day"]
        pattern["days"][i]["slots"][j]["start_time"]
        pattern["days"][i]["slots"][j]["end_time"]
        """
        try:
            schedules = (
                self.db.query(Schedule)
                .filter(Schedule.is_active.is_(True))
                .all()
            )

            logger.info(
                "Schedule check started: count=%s",
                len(schedules),
            )

            for schedule in schedules:
                try:
                    pattern = schedule.pattern or {}

                    now_dt = self._get_now_for_pattern(pattern)
                    now_time = now_dt.time().replace(second=0, microsecond=0)

                    slots = self._extract_today_slots(
                        schedule=schedule,
                        now_dt=now_dt,
                    )

                    should_run = self._should_run_now(
                        slots=slots,
                        now_time=now_time,
                    )

                    device = self._get_device(str(schedule.device_id))

                    is_running = self.motor_service.is_motor_running(
                        str(schedule.device_id)
                    )

                    logger.info(
                        "Schedule checked: schedule_id=%s device_id=%s device_uid=%s now=%s should_run=%s is_running=%s",
                        schedule.id,
                        schedule.device_id,
                        device.device_uid,
                        now_dt.isoformat(),
                        should_run,
                        is_running,
                    )

                    if should_run and not is_running:
                        self.motor_service.start_motor(
                            device_id=str(schedule.device_id),
                            trigger_type="schedule",
                            customer_name="Schedule",
                        )

                        logger.info(
                            "Schedule started motor: schedule_id=%s device_id=%s",
                            schedule.id,
                            schedule.device_id,
                        )

                    elif not should_run and is_running:
                        running_log = self.motor_service.get_running_log(
                            str(schedule.device_id)
                        )

                        if running_log and running_log.trigger_type == "schedule":
                            self.motor_service.stop_motor(
                                device_id=str(schedule.device_id),
                                customer_name="Schedule",
                            )

                            logger.info(
                                "Schedule stopped motor: schedule_id=%s device_id=%s",
                                schedule.id,
                                schedule.device_id,
                            )

                except AppException as exc:
                    logger.error(
                        "Schedule execution AppException: schedule_id=%s device_id=%s detail=%s",
                        getattr(schedule, "id", None),
                        getattr(schedule, "device_id", None),
                        getattr(exc, "detail", str(exc)),
                        exc_info=True,
                    )

                except Exception as exc:
                    logger.error(
                        "Schedule execution error: schedule_id=%s device_id=%s error_type=%s error=%s",
                        getattr(schedule, "id", None),
                        getattr(schedule, "device_id", None),
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

    def _get_now_for_pattern(self, pattern: dict[str, Any]) -> datetime:
        """
        Get current time using schedule timezone.

        Default timezone is Asia/Karachi.
        """
        timezone_name = "Asia/Karachi"

        if isinstance(pattern, dict):
            timezone_name = pattern.get("timezone") or timezone_name

        try:
            return datetime.now(ZoneInfo(timezone_name))
        except Exception:
            logger.warning(
                "Invalid schedule timezone: timezone=%s. Falling back to Asia/Karachi",
                timezone_name,
                exc_info=True,
            )
            return datetime.now(ZoneInfo("Asia/Karachi"))

    def _extract_today_slots(
        self,
        schedule: Schedule,
        now_dt: datetime,
    ) -> list[dict[str, Any]]:
        """
        Extract today's slots from schedule pattern.

        Supports your weekly body:

        {
            "timezone": "Asia/Karachi",
            "enabled": true,
            "days": [
                {
                    "day": "monday",
                    "enabled": true,
                    "slots": [
                        {
                            "start_time": "09:00",
                            "end_time": "12:00"
                        }
                    ]
                }
            ]
        }
        """
        pattern = schedule.pattern or {}

        if not isinstance(pattern, dict):
            logger.error(
                "Invalid schedule pattern: expected=dict actual=%s value=%s",
                type(pattern).__name__,
                pattern,
            )
            return []

        if pattern.get("enabled") is False:
            return []

        schedule_type = schedule.schedule_type or pattern.get("type")
        today_name = now_dt.strftime("%A").lower()
        today_day_number = now_dt.day

        if schedule_type == "daily":
            start_time = pattern.get("start_time")
            end_time = pattern.get("end_time")

            if not start_time or not end_time:
                return []

            return [
                {
                    "start_time": start_time,
                    "end_time": end_time,
                }
            ]

        if schedule_type == "weekly":
            days = pattern.get("days", [])

            if not isinstance(days, list):
                logger.error(
                    "Invalid weekly schedule days: expected=list actual=%s value=%s",
                    type(days).__name__,
                    days,
                )
                return []

            for day_config in days:
                if not isinstance(day_config, dict):
                    continue

                day_name = str(day_config.get("day", "")).lower()

                if day_name != today_name:
                    continue

                if day_config.get("enabled") is False:
                    return []

                slots = day_config.get("slots", [])

                if not isinstance(slots, list):
                    logger.error(
                        "Invalid weekly slots: expected=list actual=%s value=%s",
                        type(slots).__name__,
                        slots,
                    )
                    return []

                return slots

            return []

        if schedule_type == "monthly":
            days = pattern.get("days", [])
            slots = pattern.get("slots", [])

            if today_day_number in days:
                return slots if isinstance(slots, list) else []

            return []

        if schedule_type == "monthly_custom":
            days = pattern.get("days", {})

            if not isinstance(days, dict):
                return []

            slots = days.get(str(today_day_number), [])

            return slots if isinstance(slots, list) else []

        logger.warning(
            "Unknown schedule type: schedule_id=%s schedule_type=%s pattern=%s",
            schedule.id,
            schedule_type,
            pattern,
        )

        return []

    def _should_run_now(
        self,
        slots: list[dict[str, Any]],
        now_time: time,
    ) -> bool:
        """
        Check if current time is inside any schedule slot.

        Supported slot formats:

        {
            "start_time": "09:00",
            "end_time": "12:00"
        }

        Also supports older keys:

        {
            "start": "09:00",
            "end": "12:00"
        }
        """
        for slot in slots:
            try:
                start_value = slot.get("start_time") or slot.get("start")
                end_value = slot.get("end_time") or slot.get("end")

                if not start_value or not end_value:
                    continue

                start = time.fromisoformat(str(start_value))
                end = time.fromisoformat(str(end_value))

                if start <= now_time < end:
                    return True

            except (ValueError, TypeError, AttributeError) as exc:
                logger.error(
                    "Invalid schedule slot: slot=%s error_type=%s error=%s",
                    slot,
                    type(exc).__name__,
                    str(exc),
                    exc_info=True,
                )

        return False