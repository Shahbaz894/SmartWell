from fastapi import APIRouter, Depends, HTTPException, status
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


def _raise_http_error(exc: AppException):
    raise HTTPException(
        status_code=getattr(exc, "status_code", 500),
        detail=getattr(exc, "detail", str(exc)),
    )


@router.post(
    "/{device_id}/reset",
    response_model=VFDCommandResponse,
    status_code=status.HTTP_200_OK,
    summary="Reset VFD through MQTT",
)
def reset_vfd(
    device_id: str,
    payload: VFDResetRequest,
    db: Session = Depends(get_db),
):
    """
    Send VFD reset command to ESP32 through MQTT.

    MQTT flow:
    API route calls VFDControlService.
    VFDControlService creates command log.
    VFDControlService publishes:
        topic: tubewell/{device_uid}/motor
        payload: {"command": "RESET_VFD"}
    """
    service = VFDControlService(db)

    try:
        result = service.reset_vfd(
            device_id=device_id,
            confirm=payload.confirm,
        )

        logger.info(
            "VFD reset API success: device_id=%s result=%s",
            device_id,
            result,
        )

        return result

    except AppException as exc:
        logger.error(
            "VFD reset API failed: device_id=%s detail=%s",
            device_id,
            getattr(exc, "detail", str(exc)),
            exc_info=True,
        )
        _raise_http_error(exc)

    except Exception as exc:
        logger.error(
            "VFD reset API unexpected error: device_id=%s error_type=%s error=%s",
            device_id,
            type(exc).__name__,
            str(exc),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected VFD reset error: {type(exc).__name__}: {str(exc)}",
        )


@router.post(
    "/{device_id}/reference-frequency",
    response_model=VFDCommandResponse,
    status_code=status.HTTP_200_OK,
    summary="Set VFD reference frequency through MQTT",
)
def set_reference_frequency(
    device_id: str,
    payload: VFDReferenceFrequencyRequest,
    db: Session = Depends(get_db),
):
    """
    Send VFD reference frequency command to ESP32 through MQTT.

    MQTT flow:
    API route calls VFDControlService.
    VFDControlService creates command log.
    VFDControlService publishes:
        topic: tubewell/{device_uid}/motor
        payload:
            {
              "command": "SET_REFERENCE_FREQUENCY",
              "reference_frequency": 45.0
            }
    """
    service = VFDControlService(db)

    try:
        result = service.set_reference_frequency(
            device_id=device_id,
            reference_frequency=payload.reference_frequency,
        )

        logger.info(
            "VFD frequency API success: device_id=%s frequency=%s result=%s",
            device_id,
            payload.reference_frequency,
            result,
        )

        return result

    except AppException as exc:
        logger.error(
            "VFD frequency API failed: device_id=%s frequency=%s detail=%s",
            device_id,
            payload.reference_frequency,
            getattr(exc, "detail", str(exc)),
            exc_info=True,
        )
        _raise_http_error(exc)

    except Exception as exc:
        logger.error(
            "VFD frequency API unexpected error: device_id=%s frequency=%s error_type=%s error=%s",
            device_id,
            payload.reference_frequency,
            type(exc).__name__,
            str(exc),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected VFD frequency error: {type(exc).__name__}: {str(exc)}",
        )