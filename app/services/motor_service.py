from datetime import datetime

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.core.logger import logger
from app.models.device import Device
from app.models.motor_log import MotorLog
from app.repositories.motor_repo import MotorRepository
from app.services.mqtt_service import MQTTService


class MotorService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = MotorRepository(db)
        self.mqtt = MQTTService()

    def _get_device(self, device_id: str) -> Device:
        device = self.db.query(Device).filter(Device.id == device_id).first()

        if not device:
            raise AppException(
                status_code=404,
                detail=f"Device '{device_id}' not found",
            )

        return device

    def start_motor(
        self,
        device_id: str,
        trigger_type: str = "manual",
        customer_name: str = "",
    ) -> MotorLog:
        try:
            device = self._get_device(device_id)

            normalized_trigger = (trigger_type or "manual").strip().lower()
            if normalized_trigger not in {"manual", "schedule"}:
                raise AppException(
                    status_code=400,
                    detail="trigger_type must be 'manual' or 'schedule'",
                )

            if normalized_trigger == "manual" and not customer_name.strip():
                raise AppException(
                    status_code=400,
                    detail="customer_name is required for manual start",
                )

            running = self.repo.get_running_motor(device_id)
            if running:
                logger.warning(
                    "Motor already running: device_id=%s log_id=%s",
                    device_id,
                    running.id,
                )
                return running

            self.mqtt.publish_command(
                device_uid=device.device_uid,
                payload={
                    "command": "ON",
                    "device_id": str(device.id),
                    "device_uid": device.device_uid,
                    "trigger_type": normalized_trigger,
                },
            )

            log = MotorLog(
                device_id=device_id,
                start_time=datetime.utcnow(),
                trigger_type=normalized_trigger,
                customer_name=customer_name.strip() or "Schedule",
                status="ON",
            )

            created = self.repo.create_log(log)

            logger.info(
                "Motor started and MQTT ON sent: device_id=%s uid=%s log_id=%s",
                device_id,
                device.device_uid,
                created.id,
            )

            return created

        except AppException:
            raise

        except SQLAlchemyError as exc:
            logger.error("DB error while starting motor: %s", exc, exc_info=True)
            raise AppException(
                status_code=500,
                detail=f"Database error while starting motor: {str(exc.orig) if hasattr(exc, 'orig') else str(exc)}",
            )

        except Exception as exc:
            logger.error("Unexpected error while starting motor: %s", exc, exc_info=True)
            raise AppException(
                status_code=500,
                detail=f"Unexpected error while starting motor: {type(exc).__name__}: {str(exc)}",
            )

    def stop_motor(
        self,
        device_id: str,
        customer_name: str | None = None,
    ) -> MotorLog | None:
        try:
            device = self._get_device(device_id)

            log = self.repo.get_running_motor(device_id)
            if not log:
                logger.warning("Stop requested but motor is not running: %s", device_id)

                self.mqtt.publish_command(
                    device_uid=device.device_uid,
                    payload={
                        "command": "OFF",
                        "device_id": str(device.id),
                        "device_uid": device.device_uid,
                    },
                )

                return None

            self.mqtt.publish_command(
                device_uid=device.device_uid,
                payload={
                    "command": "OFF",
                    "device_id": str(device.id),
                    "device_uid": device.device_uid,
                },
            )

            end_time = datetime.utcnow()
            duration = end_time - log.start_time

            log.end_time = end_time
            log.duration_minutes = max(1, int(duration.total_seconds() / 60))
            log.status = "OFF"

            if customer_name and customer_name.strip():
                log.customer_name = customer_name.strip()

            updated = self.repo.update_log(log)

            logger.info(
                "Motor stopped and MQTT OFF sent: device_id=%s uid=%s log_id=%s",
                device_id,
                device.device_uid,
                updated.id,
            )

            return updated

        except AppException:
            raise

        except SQLAlchemyError as exc:
            logger.error("DB error while stopping motor: %s", exc, exc_info=True)
            raise AppException(
                status_code=500,
                detail=f"Database error while stopping motor: {str(exc.orig) if hasattr(exc, 'orig') else str(exc)}",
            )

        except Exception as exc:
            logger.error("Unexpected error while stopping motor: %s", exc, exc_info=True)
            raise AppException(
                status_code=500,
                detail=f"Unexpected error while stopping motor: {type(exc).__name__}: {str(exc)}",
            )

    def is_motor_running(self, device_id: str) -> bool:
        return self.repo.get_running_motor(device_id) is not None

    def get_running_log(self, device_id: str):
        return self.repo.get_running_motor(device_id)