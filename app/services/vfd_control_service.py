import requests
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logger import logger
from app.models.vfd_command_log import VFDCommandLog
from app.repositories.vfd_command_log_repo import VFDCommandLogRepository


class VFDControlService:
    """
    Service layer for VFD control actions.

    Responsibilities:
    - Validate reset request
    - Validate reference frequency request
    - Send VFD commands to device over HTTP
    - Store VFD command history in database
    """

    def __init__(self, db: Session):
        self.repo = VFDCommandLogRepository(db)

    def _send_vfd_command_http(
        self,
        device_id: str,
        command: str,
        reference_frequency: float | None = None,
    ) -> None:
        """
        Send VFD command to device over HTTP.

        Args:
            device_id: Device identifier
            command: Command name such as RESET_VFD or SET_REFERENCE_FREQUENCY
            reference_frequency: Optional reference frequency value

        Raises:
            AppException: If HTTP command delivery fails or base URL is missing
        """
        base_url = (settings.DEVICE_HTTP_URL or "").rstrip("/")

        if not base_url:
            logger.error("DEVICE_HTTP_URL is not configured")
            raise AppException(
                status_code=500,
                detail="DEVICE_HTTP_URL is not configured",
            )

        url = f"{base_url}/vfd"

        payload = {
            "device_id": device_id,
            "command": command,
        }

        if reference_frequency is not None:
            payload["reference_frequency"] = reference_frequency

        try:
            response = requests.post(url, json=payload, timeout=5)
            response.raise_for_status()

            logger.info(
                "HTTP VFD command sent successfully: device_id=%s, command=%s, status_code=%s",
                device_id,
                command,
                response.status_code,
            )

        except requests.RequestException as exc:
            logger.error(
                "HTTP VFD command failed: device_id=%s, command=%s, error=%s",
                device_id,
                command,
                exc,
                exc_info=True,
            )
            raise AppException(
                status_code=502,
                detail=f"Failed to send VFD command '{command}' to device '{device_id}'",
            )

    def reset_vfd(
        self,
        device_id: str,
        confirm: bool,
        triggered_by: str | None = None,
    ) -> dict:
        """
        Reset VFD for a specific device.

        Args:
            device_id: Device identifier from path parameter
            confirm: Must be True to allow reset
            triggered_by: Optional actor name or source

        Returns:
            dict: Success response payload

        Raises:
            AppException: For validation, HTTP, database, or unexpected errors
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

            self._send_vfd_command_http(
                device_id=device_id,
                command="RESET_VFD",
            )

            self.repo.update_status(
                command_log_id=log_entry.id,
                status="SENT",
                message="VFD reset command sent successfully",
            )

            logger.info(
                "VFD reset requested successfully: device_id=%s",
                device_id,
            )

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

        Args:
            device_id: Device identifier from path parameter
            reference_frequency: Frequency value to send to device
            triggered_by: Optional actor name or source

        Returns:
            dict: Success response payload

        Raises:
            AppException: For validation, HTTP, database, or unexpected errors
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

            self._send_vfd_command_http(
                device_id=device_id,
                command="SET_REFERENCE_FREQUENCY",
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