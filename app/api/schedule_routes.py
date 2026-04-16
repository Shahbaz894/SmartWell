from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.core.logger import logger
from app.db.session import get_db
from app.schemas.schedule_schema import ScheduleCreate, ScheduleResponse
from app.services.schedule_service import ScheduleService

router = APIRouter(prefix="/schedule", tags=["Schedule"])


@router.post("/", response_model=ScheduleResponse)
def create_schedule(data: ScheduleCreate, db: Session = Depends(get_db)):
    """
    Create or update schedule for a device.

    Args:
        data: Schedule payload from client
        db: Active database session

    Returns:
        ScheduleResponse: Created or updated schedule
    """
    service = ScheduleService(db)

    try:
        schedule = service.create_schedule(data.device_id, data)

        logger.info(
            "Schedule API create or update success: device_id=%s, schedule_id=%s",
            data.device_id,
            schedule.id,
        )
        return schedule

    except AppException:
        raise

    except Exception as exc:
        logger.error(
            "Unexpected error in create_schedule API: device_id=%s, error=%s",
            data.device_id,
            exc,
            exc_info=True,
        )
        raise AppException(
            status_code=500,
            detail="Internal server error",
        )


@router.get("/{device_id}", response_model=ScheduleResponse)
def get_schedule(device_id: str, db: Session = Depends(get_db)):
    """
    Get schedule for a device.

    Args:
        device_id: Device identifier
        db: Active database session

    Returns:
        ScheduleResponse: Schedule for the device
    """
    service = ScheduleService(db)

    try:
        schedule = service.get_schedule(device_id)

        logger.info(
            "Schedule API get success: device_id=%s, schedule_id=%s",
            device_id,
            schedule.id,
        )
        return schedule

    except AppException:
        raise

    except Exception as exc:
        logger.error(
            "Unexpected error in get_schedule API: device_id=%s, error=%s",
            device_id,
            exc,
            exc_info=True,
        )
        raise AppException(
            status_code=500,
            detail="Internal server error",
        )


@router.delete("/{device_id}")
def delete_schedule(device_id: str, db: Session = Depends(get_db)):
    """
    Delete schedule for a device.

    Args:
        device_id: Device identifier
        db: Active database session

    Returns:
        dict: Success message
    """
    service = ScheduleService(db)

    try:
        service.delete_schedule(device_id)

        logger.info("Schedule API delete success: device_id=%s", device_id)
        return {"message": "Deleted"}

    except AppException:
        raise

    except Exception as exc:
        logger.error(
            "Unexpected error in delete_schedule API: device_id=%s, error=%s",
            device_id,
            exc,
            exc_info=True,
        )
        raise AppException(
            status_code=500,
            detail="Internal server error",
        )