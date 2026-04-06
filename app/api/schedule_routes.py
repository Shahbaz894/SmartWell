# app/api/schedule_routes.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.schedule_schema import ScheduleCreate
from app.services.schedule_service import ScheduleService
from app.core.logger import logger
from app.core.exceptions import AppException

router = APIRouter(prefix="/schedule", tags=["Schedule"])


@router.post("/")
def create_schedule(data: ScheduleCreate, db: Session = Depends(get_db)):
    service = ScheduleService(db)
    try:
        schedule = service.create_schedule(data.device_id, data)
        logger.info(
            "Schedule created: device_id=%s, schedule_id=%s",
            data.device_id,
            schedule.id
        )
        return schedule

    except AppException as e:
        logger.error(
            "Failed to create schedule for device_id=%s: %s",
            data.device_id,
            str(e)
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            "Unexpected error creating schedule for device_id=%s: %s",
            data.device_id,
            str(e)
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{device_id}")
def get_schedules(device_id: str, db: Session = Depends(get_db)):
    service = ScheduleService(db)
    try:
        schedules = service.repo.get_device_schedules(device_id)
        logger.info(
            "Fetched %d schedules for device_id=%s",
            len(schedules),
            device_id
        )
        return schedules

    except AppException as e:
        logger.error(
            "Failed to fetch schedules for device_id=%s: %s",
            device_id,
            str(e)
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            "Unexpected error fetching schedules for device_id=%s: %s",
            device_id,
            str(e)
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/clear/{device_id}")
def clear_schedule(device_id: str, db: Session = Depends(get_db)):
    service = ScheduleService(db)
    try:
        deleted_count = service.repo.clear_schedule(device_id)
        logger.info(
            "Cleared %d schedules for device_id=%s",
            deleted_count,
            device_id
        )
        return {"detail": f"Cleared {deleted_count} schedules for device_id {device_id}"}

    except AppException as e:
        logger.error(
            "Failed to clear schedules for device_id=%s: %s",
            device_id,
            str(e)
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            "Unexpected error clearing schedules for device_id=%s: %s",
            device_id,
            str(e)
        )
        raise HTTPException(status_code=500, detail="Internal server error")