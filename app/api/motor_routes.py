from fastapi import APIRouter, Depends
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


@router.post("/{device_id}/start", response_model=MotorLogResponse)
def start_motor(
    device_id: str,
    payload: MotorStartRequest,
    db: Session = Depends(get_db),
):
    """
    Start motor for a specific device.

    Path param:
        device_id -> only this device receives MQTT ON command.

    Body:
        trigger_type, operator_name
    """
    service = MotorService(db)

    try:
        motor_log = service.start_motor(
            device_id=device_id,
            trigger_type=payload.trigger_type,
            customer_name=payload.customer_name,
        )

        logger.info(
            "Motor start API success: device_id=%s, log_id=%s",
            device_id,
            motor_log.id,
        )
        return motor_log

    except AppException:
        raise

    except Exception as exc:
        logger.error(
            "Unexpected API error starting motor: device_id=%s, error=%s",
            device_id,
            exc,
            exc_info=True,
        )
        raise AppException(status_code=500, detail="Internal server error")


@router.post("/{device_id}/stop", response_model=MotorLogResponse)
def stop_motor(
    device_id: str,
    payload: MotorStopRequest,
    db: Session = Depends(get_db),
):
    """
    Stop motor for a specific device.

    Path param:
        device_id -> only this device receives MQTT OFF command.
    """
    service = MotorService(db)

    try:
        motor_log = service.stop_motor(
            device_id=device_id,
            customer_name=payload.customer_name,
        )

        if not motor_log:
            logger.warning("No running motor found to stop: device_id=%s", device_id)
            raise AppException(status_code=404, detail="No running motor found")

        logger.info(
            "Motor stop API success: device_id=%s, log_id=%s, duration=%s minutes",
            device_id,
            motor_log.id,
            motor_log.duration_minutes,
        )
        return motor_log

    except AppException:
        raise

    except Exception as exc:
        logger.error(
            "Unexpected API error stopping motor: device_id=%s, error=%s",
            device_id,
            exc,
            exc_info=True,
        )
        raise AppException(status_code=500, detail="Internal server error")