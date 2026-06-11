from datetime import datetime

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from uuid import UUID  
from app.core.exceptions import AppException
from app.core.logger import logger
from app.models.device import Device
from app.models.motor_log import MotorLog
from app.repositories.motor_repo import MotorRepository
from app.services.mqtt_service import MQTTService
from app.core.state import pending_commands

class MotorService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = MotorRepository(db)
        self.mqtt = MQTTService()

    # def _get_device(self, device_id: str) -> Device:
    #     device = self.db.query(Device).filter(Device.device_uid== device_id).first()

    #     if not device:
    #         raise AppException(
    #             status_code=404,
    #             detail=f"Device '{device_id}' not found",
    #         )

    #     return device
    
    def _get_device(self, device_id: str) -> Device:
    # 1. Try ESP32 device UID first
        device = (
            self.db.query(Device)
            .filter(Device.device_uid == device_id)
            .first()
        )

        if device:
            return device

        # 2. Try UUID only if value is a valid UUID
        try:
            parsed_uuid = UUID(device_id)
        except ValueError:
            parsed_uuid = None

        if parsed_uuid:
            device = (
                self.db.query(Device)
                .filter(Device.id == parsed_uuid)
                .first()
            )

        if not device:
            raise AppException(
                status_code=404,
                detail=f"Device '{device_id}' not found",
            )

        return device

    def start_motor(
        self,
        device_id: str,
        trigger_type: str = "physical", # Updated default
        customer_name: str = "",
    ) -> MotorLog:
        try:
            device = self._get_device(device_id)
            db_device_id = str(device.id)

            # 1. Normalize and Validate Trigger Type
            # Using your Enum categories: app, schedule, timer, physical
            normalized_trigger = (trigger_type or "physical").strip().lower()
            allowed_triggers = {"app", "schedule", "timer", "physical"}
            
            if normalized_trigger not in allowed_triggers:
                raise AppException(
                    status_code=400,
                    detail=f"trigger_type must be one of {allowed_triggers}",
                )

            # 2. Require customer name only for 'app' or 'manual' type triggers
            if normalized_trigger in {"app", "manual"} and not customer_name.strip():
                raise AppException(
                    status_code=400,
                    detail="customer_name is required for App/Manual starts",
                )

            # 3. Prevent duplicate log entries
            running = self.repo.get_running_motor(db_device_id)
            if running:
                logger.warning(
                    "Motor already running: device_id=%s log_id=%s",
                    device_id,
                    running.id,
                )
                return running

            # 4. MQTT Command: Send to hardware
            self.mqtt.publish_command(
                device_uid=device.device_uid,
                payload={
                    "command": "ON",
                    "device_id": db_device_id,
                    "device_uid": device.device_uid,
                    "trigger_type": normalized_trigger,
                },
            )

            # 5. Database: Create persistent record
            # We use normalized_trigger to ensure the UI knows exactly how it started
            log = MotorLog(
                device_id=db_device_id,
                start_time=datetime.utcnow(),
                trigger_type=normalized_trigger,
                customer_name=customer_name.strip() or f"{normalized_trigger.capitalize()} Start",
                status="ON",
            )

            created = self.repo.create_log(log)
            self.db.commit() # Ensure the transaction is finalized

            logger.info(
                "Motor started: device_id=%s uid=%s trigger=%s log_id=%s",
                device_id,
                device.device_uid,
                normalized_trigger,
                created.id,
            )

            return created

        except AppException:
            self.db.rollback()
            raise

        except SQLAlchemyError as exc:
            self.db.rollback()
            logger.error("DB error while starting motor: %s", exc, exc_info=True)
            raise AppException(
                status_code=500,
                detail=f"Database error: {str(exc.orig) if hasattr(exc, 'orig') else str(exc)}",
            )

        except Exception as exc:
            self.db.rollback()
            logger.error("Unexpected error while starting motor: %s", exc, exc_info=True)
            raise AppException(
                status_code=500,
                detail=f"Unexpected error: {type(exc).__name__}: {str(exc)}",
            )

    def stop_motor(
        self,
        device_id: str,
        customer_name: str | None = None,
    ) -> MotorLog | None:
        try:
            # # device = self._get_device(device_id)
            # db_device_id = str(device.id)
            # device = self._get_device (db_device_id)
            device = self._get_device(device_id)
            db_device_id = str(device.id)

            log = self.repo.get_running_motor(db_device_id)
            if not log:
                logger.warning("Stop requested but motor is not running: %s", db_device_id)

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
        device = self._get_device(device_id)
        return self.repo.get_running_motor(str(device.id)) is not None

    def get_running_log(self, device_id: str):
        device = self._get_device(device_id)
        return self.repo.get_running_motor(str(device.id))
    
    
    def get_motor_logs(self, device_id: str):
        """
        Return all motor ON/OFF logs for one device, newest first.
        """
        try:
            device = self._get_device(device_id)
            db_device_id = str(device.id)

            return (
                self.db.query(MotorLog)
                .filter(MotorLog.device_id == db_device_id)
                .order_by(MotorLog.start_time.desc())
                .all()
            )

        except AppException:
            raise

        except SQLAlchemyError as exc:
            logger.error(
                "DB error while fetching motor logs: device_id=%s error=%s",
                device_id,
                exc,
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=f"Database error while fetching motor logs: {str(exc.orig) if hasattr(exc, 'orig') else str(exc)}",
            )

        except Exception as exc:
            logger.error(
                "Unexpected error while fetching motor logs: device_id=%s error=%s",
                device_id,
                exc,
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=f"Unexpected error while fetching motor logs: {type(exc).__name__}: {str(exc)}",
            )

    def delete_motor_log(self, log_id: str) -> None:
        """
        Delete one motor log by log UUID.
        """
        try:
            try:
                parsed_log_id = UUID(log_id)
            except ValueError:
                raise AppException(
                    status_code=400,
                    detail="Invalid motor log id",
                )

            log = (
                self.db.query(MotorLog)
                .filter(MotorLog.id == parsed_log_id)
                .first()
            )

            if not log:
                raise AppException(
                    status_code=404,
                    detail="Motor log not found",
                )

            self.db.delete(log)
            self.db.commit()

            logger.info("Motor log deleted: log_id=%s", log_id)

        except AppException:
            raise

        except SQLAlchemyError as exc:
            self.db.rollback()

            logger.error(
                "DB error while deleting motor log: log_id=%s error=%s",
                log_id,
                exc,
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=f"Database error while deleting motor log: {str(exc.orig) if hasattr(exc, 'orig') else str(exc)}",
            )

        except Exception as exc:
            self.db.rollback()

            logger.error(
                "Unexpected error while deleting motor log: log_id=%s error=%s",
                log_id,
                exc,
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=f"Unexpected error while deleting motor log: {type(exc).__name__}: {str(exc)}",
            )

    def clear_motor_logs(self, device_id: str) -> int:
        """
        Delete all motor logs for one device.
        """
        try:
            device = self._get_device(device_id)
            db_device_id = str(device.id)

            logs = (
                self.db.query(MotorLog)
                .filter(MotorLog.device_id == db_device_id)
                .all()
            )

            deleted_count = len(logs)

            for log in logs:
                self.db.delete(log)

            self.db.commit()

            logger.info(
                "Motor logs cleared: device_id=%s count=%s",
                device_id,
                deleted_count,
            )

            return deleted_count

        except AppException:
            raise

        except SQLAlchemyError as exc:
            self.db.rollback()

            logger.error(
                "DB error while clearing motor logs: device_id=%s error=%s",
                device_id,
                exc,
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=f"Database error while clearing motor logs: {str(exc.orig) if hasattr(exc, 'orig') else str(exc)}",
            )

        except Exception as exc:
            self.db.rollback()

            logger.error(
                "Unexpected error while clearing motor logs: device_id=%s error=%s",
                device_id,
                exc,
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=f"Unexpected error while clearing motor logs: {type(exc).__name__}: {str(exc)}",
            )
            
   

    def sync_motor_state(self, device_id: str, status_code: int):
        device = self._get_device(device_id)
        running_log = self.repo.get_running_motor(str(device.id))
        
        # Check if a command is currently expected from our system
        active_trigger = pending_commands.pop(str(device.id), "physical") 

        # Case 1: Hardware ON (1), DB OFF -> Start Logic
        if status_code == 1 and not running_log:
            self.start_motor(
                device_id=device_id, 
                trigger_type=active_trigger, 
                customer_name=f"{active_trigger.capitalize()} Start"
            )

        # Case 2: Hardware OFF (0), DB ON -> Stop Logic
        elif status_code == 0 and running_log:
            self.stop_motor(device_id=device_id)