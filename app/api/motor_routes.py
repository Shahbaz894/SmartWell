# app/api/motor_routes.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.motor_service import MotorService
from app.core.logger import logger
from app.core.exceptions import AppException

router = APIRouter(prefix="/motor", tags=["Motor"])


@router.post("/start")
def start_motor(device_id: str, db: Session = Depends(get_db)):
    service = MotorService(db)
    try:
        motor_log = service.start_motor(device_id, "manual")
        logger.info("Motor started: device_id=%s, log_id=%s", device_id, motor_log.id)
        return motor_log

    except AppException as e:
        logger.error("Failed to start motor for device_id=%s: %s", device_id, str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Unexpected error starting motor for device_id=%s: %s", device_id, str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/stop")
def stop_motor(device_id: str, db: Session = Depends(get_db)):
    service = MotorService(db)
    try:
        motor_log = service.stop_motor(device_id)
        if motor_log:
            logger.info(
                "Motor stopped: device_id=%s, log_id=%s, duration=%s minutes",
                device_id,
                motor_log.id,
                motor_log.duration_minutes
            )
            return motor_log
        else:
            logger.warning("No running motor found to stop: device_id=%s", device_id)
            raise HTTPException(status_code=404, detail="No running motor found")

    except AppException as e:
        logger.error("Failed to stop motor for device_id=%s: %s", device_id, str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Unexpected error stopping motor for device_id=%s: %s", device_id, str(e))
        raise HTTPException(status_code=500, detail="Internal server error")