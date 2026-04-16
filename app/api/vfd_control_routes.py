from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.core.logger import logger
from app.db.session import get_db
from app.schemas.vfd_control_schema import (
    VFDResetRequest,
    VFDReferenceFrequencyRequest,
    VFDCommandResponse,
)
from app.services.vfd_control_service import VFDControlService

router = APIRouter(prefix="/vfd", tags=["VFD Control"])


@router.post("/{device_id}/reset", response_model=VFDCommandResponse)
def reset_vfd(
    device_id: str,
    payload: VFDResetRequest,
    db: Session = Depends(get_db),
):
    """
    Reset VFD to default settings for a specific device.
    """
    service = VFDControlService(db)

    try:
        response = service.reset_vfd(
            device_id=device_id,
            confirm=payload.confirm,
        )

        logger.info("VFD reset API success: device_id=%s", device_id)
        return response

    except AppException:
        raise

    except Exception as exc:
        logger.error(
            "Unexpected error in reset_vfd API: device_id=%s, error=%s",
            device_id,
            exc,
            exc_info=True,
        )
        raise AppException(
            status_code=500,
            detail="Internal server error",
        )


@router.post("/{device_id}/reference-frequency", response_model=VFDCommandResponse)
def set_reference_frequency(
    device_id: str,
    payload: VFDReferenceFrequencyRequest,
    db: Session = Depends(get_db),
):
    """
    Set VFD reference frequency for a specific device.
    """
    service = VFDControlService(db)

    try:
        response = service.set_reference_frequency(
            device_id=device_id,
            reference_frequency=payload.reference_frequency,
        )

        logger.info(
            "VFD reference frequency API success: device_id=%s, reference_frequency=%s",
            device_id,
            payload.reference_frequency,
        )
        return response

    except AppException:
        raise

    except Exception as exc:
        logger.error(
            "Unexpected error in set_reference_frequency API: device_id=%s, error=%s",
            device_id,
            exc,
            exc_info=True,
        )
        raise AppException(
            status_code=500,
            detail="Internal server error",
        )