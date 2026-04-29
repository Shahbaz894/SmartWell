from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.core.logger import logger
from app.models.device import Device
from app.models.vfd_command_log import VFDCommandLog
from app.repositories.vfd_command_log_repo import VFDCommandLogRepository
from app.services.mqtt_service import MQTTService


class VFDControlService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = VFDCommandLogRepository(db)
        self.mqtt = MQTTService()

    def _get_device(self, device_id: str) -> Device:
        device = self.db.query(Device).filter(Device.id == device_id).first()

        if not device:
            raise AppException(
                status_code=404,
                detail=f"Device '{device_id}' not found",
            )

        return device

    def reset_vfd(self, device_id: str, confirm: bool):
        if not confirm:
            raise AppException(
                status_code=400,
                detail="confirm=true is required to reset VFD",
            )

        try:
            device = self._get_device(device_id)

            log = self.repo.create(
                VFDCommandLog(
                    device_id=device_id,
                    command="RESET_VFD",
                    status="PENDING",
                )
            )

            self.mqtt.publish_command(
                device_uid=device.device_uid,
                payload={
                    "command": "RESET_VFD",
                    "device_id": str(device.id),
                    "device_uid": device.device_uid,
                },
            )

            self.repo.update_status(log.id, "SENT", "Published to MQTT broker")

            logger.info(
                "VFD reset command published: device_id=%s uid=%s",
                device_id,
                device.device_uid,
            )

            return {
                "message": "VFD reset command sent to ESP32 through MQTT",
                "device_id": str(device.id),
                "device_uid": device.device_uid,
                "command": "RESET_VFD",
            }

        except AppException:
            raise

        except SQLAlchemyError as exc:
            logger.error("DB error while resetting VFD: %s", exc, exc_info=True)
            raise AppException(
                status_code=500,
                detail=f"Database error while resetting VFD: {str(exc.orig) if hasattr(exc, 'orig') else str(exc)}",
            )

        except Exception as exc:
            logger.error("Unexpected VFD reset error: %s", exc, exc_info=True)
            raise AppException(
                status_code=500,
                detail=f"Unexpected VFD reset error: {type(exc).__name__}: {str(exc)}",
            )

    def set_reference_frequency(
        self,
        device_id: str,
        reference_frequency: float,
    ):
        if reference_frequency <= 0:
            raise AppException(
                status_code=400,
                detail="reference_frequency must be greater than 0",
            )

        if reference_frequency > 60:
            raise AppException(
                status_code=400,
                detail="reference_frequency cannot be greater than 60 Hz",
            )

        try:
            device = self._get_device(device_id)

            log = self.repo.create(
                VFDCommandLog(
                    device_id=device_id,
                    command="SET_REFERENCE_FREQUENCY",
                    reference_frequency=reference_frequency,
                    status="PENDING",
                )
            )

            self.mqtt.publish_command(
                device_uid=device.device_uid,
                payload={
                    "command": "SET_REFERENCE_FREQUENCY",
                    "device_id": str(device.id),
                    "device_uid": device.device_uid,
                    "reference_frequency": reference_frequency,
                },
            )

            device.reference_freq = reference_frequency
            self.db.commit()

            self.repo.update_status(log.id, "SENT", "Published to MQTT broker")

            logger.info(
                "VFD frequency command published: device_id=%s uid=%s freq=%s",
                device_id,
                device.device_uid,
                reference_frequency,
            )

            return {
                "message": "VFD frequency command sent to ESP32 through MQTT",
                "device_id": str(device.id),
                "device_uid": device.device_uid,
                "command": "SET_REFERENCE_FREQUENCY",
                "reference_frequency": reference_frequency,
            }

        except AppException:
            raise

        except SQLAlchemyError as exc:
            self.db.rollback()
            logger.error("DB error while setting VFD frequency: %s", exc, exc_info=True)
            raise AppException(
                status_code=500,
                detail=f"Database error while setting VFD frequency: {str(exc.orig) if hasattr(exc, 'orig') else str(exc)}",
            )

        except Exception as exc:
            self.db.rollback()
            logger.error("Unexpected VFD frequency error: %s", exc, exc_info=True)
            raise AppException(
                status_code=500,
                detail=f"Unexpected VFD frequency error: {type(exc).__name__}: {str(exc)}",
            )