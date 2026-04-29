from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.core.logger import logger
from app.db.session import get_db
from app.schemas.motor_schema import (
    MotorStartRequest,
    MotorStopRequest,
    MotorLogResponse,
)
from app.services.motor_service import MotorService

router = APIRouter(prefix="/motor", tags=["Motor"])


def _raise_http_error(exc: AppException):
    raise HTTPException(
        status_code=getattr(exc, "status_code", 500),
        detail=getattr(exc, "detail", str(exc)),
    )


@router.post(
    "/{device_id}/start",
    response_model=MotorLogResponse,
    status_code=status.HTTP_200_OK,
    summary="Start motor through MQTT",
)
def start_motor(
    device_id: str,
    payload: MotorStartRequest,
    db: Session = Depends(get_db),
):
    """
    Start motor for one device.

    MQTT flow:
    API route calls MotorService.
    MotorService saves motor log.
    MotorService publishes MQTT command:
        topic: tubewell/{device_uid}/motor
        payload: {"command": "ON"}

    ESP32 receives this command from Mosquitto.
    """
    service = MotorService(db)

    try:
        motor_log = service.start_motor(
            device_id=device_id,
            trigger_type=payload.trigger_type,
            customer_name=payload.customer_name,
        )

        logger.info(
            "Motor API start success: device_id=%s log_id=%s",
            device_id,
            motor_log.id,
        )

        return motor_log

    except AppException as exc:
        logger.error(
            "Motor API start failed: device_id=%s detail=%s",
            device_id,
            getattr(exc, "detail", str(exc)),
            exc_info=True,
        )
        _raise_http_error(exc)

    except Exception as exc:
        logger.error(
            "Motor API unexpected start error: device_id=%s error_type=%s error=%s",
            device_id,
            type(exc).__name__,
            str(exc),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected motor start error: {type(exc).__name__}: {str(exc)}",
        )


@router.post(
    "/{device_id}/stop",
    response_model=MotorLogResponse,
    status_code=status.HTTP_200_OK,
    summary="Stop motor through MQTT",
)
def stop_motor(
    device_id: str,
    payload: MotorStopRequest,
    db: Session = Depends(get_db),
):
    """
    Stop motor for one device.

    MQTT flow:
    API route calls MotorService.
    MotorService updates motor log.
    MotorService publishes MQTT command:
        topic: tubewell/{device_uid}/motor
        payload: {"command": "OFF"}
    """
    service = MotorService(db)

    try:
        motor_log = service.stop_motor(
            device_id=device_id,
            customer_name=payload.customer_name,
        )

        if not motor_log:
            raise AppException(
                status_code=404,
                detail=f"No running motor found for device '{device_id}'",
            )

        logger.info(
            "Motor API stop success: device_id=%s log_id=%s duration_minutes=%s",
            device_id,
            motor_log.id,
            motor_log.duration_minutes,
        )

        return motor_log

    except AppException as exc:
        logger.error(
            "Motor API stop failed: device_id=%s detail=%s",
            device_id,
            getattr(exc, "detail", str(exc)),
            exc_info=True,
        )
        _raise_http_error(exc)

    except Exception as exc:
        logger.error(
            "Motor API unexpected stop error: device_id=%s error_type=%s error=%s",
            device_id,
            type(exc).__name__,
            str(exc),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected motor stop error: {type(exc).__name__}: {str(exc)}",
        )