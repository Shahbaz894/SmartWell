from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.core.logger import logger
from app.models.vfd_command_log import VFDCommandLog
from app.models.device import Device
from app.repositories.vfd_command_log_repo import VFDCommandLogRepository


class VFDControlService:

    def __init__(self, db: Session):
        self.db = db
        self.repo = VFDCommandLogRepository(db)

    # ─────────────────────────────────────────────
    # RESET VFD
    # ─────────────────────────────────────────────
    def reset_vfd(self, device_id: str, confirm: bool):

        if not confirm:
            raise AppException(400, "confirm=true required")

        device = self.db.query(Device).filter(Device.id == device_id).first()

        if not device:
            raise AppException(404, "Device not found")

        log = self.repo.create(
            VFDCommandLog(
                device_id=device_id,
                command="RESET_VFD",
                status="PENDING",
            )
        )

        # NO HTTP CALL → JUST MARK AS SENT
        self.repo.update_status(log.id, "SENT", "Queued for device")

        logger.info("RESET queued for device: %s", device_id)

        return {
            "message": "VFD reset queued successfully",
            "device_id": device_id,
            "command": "RESET_VFD"
        }

    # ─────────────────────────────────────────────
    # SET FREQUENCY
    # ─────────────────────────────────────────────
    def set_reference_frequency(
        self,
        device_id: str,
        reference_frequency: float
    ):

        if reference_frequency <= 0:
            raise AppException(400, "Invalid frequency")

        device = self.db.query(Device).filter(Device.id == device_id).first()

        if not device:
            raise AppException(404, "Device not found")

        log = self.repo.create(
            VFDCommandLog(
                device_id=device_id,
                command="SET_REFERENCE_FREQUENCY",
                reference_frequency=reference_frequency,
                status="PENDING",
            )
        )

        # NO HTTP CALL
        self.repo.update_status(log.id, "SENT", "Queued for device")

        logger.info(
            "Frequency queued: device=%s freq=%s",
            device_id,
            reference_frequency
        )

        return {
            "message": "Frequency command queued",
            "device_id": device_id,
            "command": "SET_REFERENCE_FREQUENCY"
        }