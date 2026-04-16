from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.core.logger import logger
from app.models.vfd_command_log import VFDCommandLog
from app.repositories.vfd_command_log_repo import VFDCommandLogRepository
from app.services.mqtt_command_service import MQTTCommandService


class VFDControlService:
    """
    Service layer for VFD control actions.

    Responsibilities:
    - Validate reset request
    - Validate reference frequency request
    - Publish VFD commands to ESP32 over MQTT
    - Store VFD command history in database
    """

    def __init__(self, db: Session):
        self.repo = VFDCommandLogRepository(db)
        self.mqtt_command_service = MQTTCommandService()

    def reset_vfd(
        self,
        device_id: str,
        confirm: bool,
        triggered_by: str | None = None,
    ) -> dict:
        """
        Reset VFD for a specific device.
        """
        log_entry = None

        try:
            if not confirm:
                raise AppException(
                    status_code=400,
                    detail="Reset confirmation is required",
                )

            log_entry = self.repo.create(
                VFDCommandLog(
                    device_id=device_id,
                    command="RESET_VFD",
                    triggered_by=triggered_by,
                    trigger_source="manual",
                    status="PENDING",
                )
            )

            self.mqtt_command_service.publish_vfd_reset_command(device_id)

            self.repo.update_status(
                command_log_id=log_entry.id,
                status="SENT",
                message="VFD reset command sent successfully",
            )

            logger.info("VFD reset requested successfully: device_id=%s", device_id)

            return {
                "message": "VFD reset command sent successfully",
                "device_id": device_id,
                "command": "RESET_VFD",
            }

        except AppException as exc:
            if log_entry:
                try:
                    self.repo.update_status(
                        command_log_id=log_entry.id,
                        status="FAILED",
                        message=getattr(exc, "detail", str(exc)),
                    )
                except Exception:
                    logger.error(
                        "Failed to update VFD reset log to FAILED: log_id=%s",
                        log_entry.id,
                        exc_info=True,
                    )
            raise

        except Exception as exc:
            logger.error(
                "Unexpected error while resetting VFD: device_id=%s, error=%s",
                device_id,
                exc,
                exc_info=True,
            )
            if log_entry:
                try:
                    self.repo.update_status(
                        command_log_id=log_entry.id,
                        status="FAILED",
                        message=str(exc),
                    )
                except Exception:
                    logger.error(
                        "Failed to update VFD reset log to FAILED: log_id=%s",
                        log_entry.id,
                        exc_info=True,
                    )

            raise AppException(
                status_code=500,
                detail="Failed to reset VFD",
            )

    def set_reference_frequency(
        self,
        device_id: str,
        reference_frequency: float,
        triggered_by: str | None = None,
    ) -> dict:
        """
        Set VFD reference frequency for a specific device.
        """
        log_entry = None

        try:
            if reference_frequency <= 0:
                raise AppException(
                    status_code=400,
                    detail="reference_frequency must be greater than 0",
                )

            log_entry = self.repo.create(
                VFDCommandLog(
                    device_id=device_id,
                    command="SET_REFERENCE_FREQUENCY",
                    reference_frequency=reference_frequency,
                    triggered_by=triggered_by,
                    trigger_source="manual",
                    status="PENDING",
                )
            )

            self.mqtt_command_service.publish_reference_frequency_command(
                device_id=device_id,
                reference_frequency=reference_frequency,
            )

            self.repo.update_status(
                command_log_id=log_entry.id,
                status="SENT",
                message="Reference frequency command sent successfully",
            )

            logger.info(
                "VFD reference frequency requested successfully: device_id=%s, reference_frequency=%s",
                device_id,
                reference_frequency,
            )

            return {
                "message": "Reference frequency command sent successfully",
                "device_id": device_id,
                "command": "SET_REFERENCE_FREQUENCY",
            }

        except AppException as exc:
            if log_entry:
                try:
                    self.repo.update_status(
                        command_log_id=log_entry.id,
                        status="FAILED",
                        message=getattr(exc, "detail", str(exc)),
                    )
                except Exception:
                    logger.error(
                        "Failed to update reference frequency log to FAILED: log_id=%s",
                        log_entry.id,
                        exc_info=True,
                    )
            raise

        except Exception as exc:
            logger.error(
                "Unexpected error while setting reference frequency: device_id=%s, error=%s",
                device_id,
                exc,
                exc_info=True,
            )
            if log_entry:
                try:
                    self.repo.update_status(
                        command_log_id=log_entry.id,
                        status="FAILED",
                        message=str(exc),
                    )
                except Exception:
                    logger.error(
                        "Failed to update reference frequency log to FAILED: log_id=%s",
                        log_entry.id,
                        exc_info=True,
                    )

            raise AppException(
                status_code=500,
                detail="Failed to set reference frequency",
            )