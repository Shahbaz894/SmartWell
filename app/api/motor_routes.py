from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.motor_service import MotorService
from app.core.logger import logger
from app.core.exceptions import AppException

router = APIRouter(prefix="/motor", tags=["Motor"])


@router.post("/{device_id}/start")
def start_motor(device_id: str, db: Session = Depends(get_db)):
    service = MotorService(db)
    try:
        motor_log = service.start_motor(device_id, "manual")
        logger.info("Motor started: device_id=%s, log_id=%s", device_id, motor_log.id)
        return motor_log

    except AppException:
        raise  # ✅ let FastAPI handle it with the correct status_code

    except Exception as e:
        logger.error("Unexpected error starting motor: device_id=%s: %s", device_id, e, exc_info=True)
        raise AppException(status_code=500, detail="Internal server error")


@router.post("/{device_id}/stop")
def stop_motor(device_id: str, db: Session = Depends(get_db)):
    service = MotorService(db)
    try:
        motor_log = service.stop_motor(device_id)
        if not motor_log:
            logger.warning("No running motor found to stop: device_id=%s", device_id)
            raise AppException(status_code=404, detail="No running motor found")

        logger.info(
            "Motor stopped: device_id=%s, log_id=%s, duration=%s minutes",
            device_id, motor_log.id, motor_log.duration_minutes
        )
        return motor_log

    except AppException:
        raise  # ✅ let FastAPI handle it with the correct status_code

    except Exception as e:
        logger.error("Unexpected error stopping motor: device_id=%s: %s", device_id, e, exc_info=True)
        raise AppException(status_code=500, detail="Internal server error")