from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.exceptions import AppException
from app.core.logger import logger
from app.schemas.vfd_control_schema import (
    VFDResetRequest,
    VFDReferenceFrequencyRequest,
    VFDCommandResponse,
)
from app.services.vfd_control_service import VFDControlService

router = APIRouter(prefix="/vfd", tags=["VFD Control"])


# ─────────────────────────────────────────────
# RESET VFD
# ─────────────────────────────────────────────
@router.post("/{device_id}/reset", response_model=VFDCommandResponse)
def reset_vfd(
    device_id: str,
    payload: VFDResetRequest,
    db: Session = Depends(get_db),
):
    service = VFDControlService(db)

    try:
        return service.reset_vfd(
            device_id=device_id,
            confirm=payload.confirm,
        )

    except AppException:
        raise

    except Exception as exc:
        logger.error("reset_vfd error: %s", exc, exc_info=True)
        raise AppException(500, "Internal server error")


# ─────────────────────────────────────────────
# SET FREQUENCY
# ─────────────────────────────────────────────
@router.post("/{device_id}/reference-frequency", response_model=VFDCommandResponse)
def set_reference_frequency(
    device_id: str,
    payload: VFDReferenceFrequencyRequest,
    db: Session = Depends(get_db),
):
    service = VFDControlService(db)

    try:
        return service.set_reference_frequency(
            device_id=device_id,
            reference_frequency=payload.reference_frequency,
        )

    except AppException:
        raise

    except Exception as exc:
        logger.error("freq error: %s", exc, exc_info=True)
        raise AppException(500, "Internal server error")