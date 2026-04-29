from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.core.logger import logger
from app.db.session import get_db
from app.schemas.schedule_schema import ScheduleCreate, ScheduleResponse
from app.services.schedule_service import ScheduleService

router = APIRouter(prefix="/schedule", tags=["Schedule"])


def _raise_http_error(exc: AppException):
    raise HTTPException(
        status_code=getattr(exc, "status_code", 500),
        detail=getattr(exc, "detail", str(exc)),
    )


@router.post(
    "/",
    response_model=ScheduleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or update motor schedule",
)
def create_schedule(
    data: ScheduleCreate,
    db: Session = Depends(get_db),
):
    """
    Create or update a schedule for a device.

    MQTT note:
    This endpoint does not publish MQTT immediately.
    The background scheduler calls ScheduleService.check_and_run().
    Then MotorService sends MQTT ON or OFF to ESP32.
    """
    service = ScheduleService(db)

    try:
        schedule = service.create_schedule(data.device_id, data)

        logger.info(
            "Schedule API save success: device_id=%s schedule_id=%s",
            data.device_id,
            schedule.id,
        )

        return schedule

    except AppException as exc:
        logger.error(
            "Schedule API save failed: device_id=%s detail=%s",
            data.device_id,
            getattr(exc, "detail", str(exc)),
            exc_info=True,
        )
        _raise_http_error(exc)

    except Exception as exc:
        logger.error(
            "Schedule API unexpected save error: device_id=%s error_type=%s error=%s",
            data.device_id,
            type(exc).__name__,
            str(exc),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected schedule save error: {type(exc).__name__}: {str(exc)}",
        )


@router.get(
    "/{device_id}",
    response_model=ScheduleResponse,
    summary="Get schedule by device",
)
def get_schedule(
    device_id: str,
    db: Session = Depends(get_db),
):
    """
    Return schedule for one device.
    """
    service = ScheduleService(db)

    try:
        schedule = service.get_schedule(device_id)

        logger.info(
            "Schedule API get success: device_id=%s schedule_id=%s",
            device_id,
            schedule.id,
        )

        return schedule

    except AppException as exc:
        logger.error(
            "Schedule API get failed: device_id=%s detail=%s",
            device_id,
            getattr(exc, "detail", str(exc)),
            exc_info=True,
        )
        _raise_http_error(exc)

    except Exception as exc:
        logger.error(
            "Schedule API unexpected get error: device_id=%s error_type=%s error=%s",
            device_id,
            type(exc).__name__,
            str(exc),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected schedule get error: {type(exc).__name__}: {str(exc)}",
        )


@router.delete(
    "/{device_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete schedule by device",
)
def delete_schedule(
    device_id: str,
    db: Session = Depends(get_db),
):
    """
    Delete schedule for one device.
    """
    service = ScheduleService(db)

    try:
        service.delete_schedule(device_id)

        logger.info("Schedule API delete success: device_id=%s", device_id)

        return {
            "detail": "Schedule deleted successfully",
            "device_id": device_id,
        }

    except AppException as exc:
        logger.error(
            "Schedule API delete failed: device_id=%s detail=%s",
            device_id,
            getattr(exc, "detail", str(exc)),
            exc_info=True,
        )
        _raise_http_error(exc)

    except Exception as exc:
        logger.error(
            "Schedule API unexpected delete error: device_id=%s error_type=%s error=%s",
            device_id,
            type(exc).__name__,
            str(exc),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected schedule delete error: {type(exc).__name__}: {str(exc)}",
        )