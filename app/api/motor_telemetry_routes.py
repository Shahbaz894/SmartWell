# app/api/motor_telemetry_routes.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from app.db.session import get_db
from app.services.motor_telemetry_service import MotorTelemetryService
from app.schemas.motor_telemetry_schema import MotorTelemetryCreate, MotorTelemetryResponse
from app.core.logger import logger
from app.core.exceptions import AppException

router = APIRouter(prefix="/telemetry", tags=["Motor Telemetry"])

service = MotorTelemetryService()


@router.post("/", response_model=MotorTelemetryResponse)
def create_telemetry(data: MotorTelemetryCreate, db: Session = Depends(get_db)):
    try:
        telemetry = service.create_telemetry(db, data)
        logger.info(
            "Motor telemetry created: device_id=%s, id=%s",
            data.device_id,
            telemetry.id
        )
        return telemetry

    except AppException as e:
        logger.error(
            "Failed to create motor telemetry for device_id=%s: %s",
            data.device_id,
            str(e)
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            "Unexpected error creating telemetry for device_id=%s: %s",
            data.device_id,
            str(e)
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{device_id}")
def get_device_telemetry(device_id: str, db: Session = Depends(get_db)):
    try:
        telemetry_list = service.get_device_telemetry(db, device_id)
        logger.info(
            "Fetched %d telemetry records for device_id=%s",
            len(telemetry_list),
            device_id
        )
        return telemetry_list

    except AppException as e:
        logger.error(
            "Failed to fetch telemetry for device_id=%s: %s",
            device_id,
            str(e)
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            "Unexpected error fetching telemetry for device_id=%s: %s",
            device_id,
            str(e)
        ) 
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/{telemetry_id}")
def delete_telemetry(telemetry_id: UUID, db: Session = Depends(get_db)):
    try:
        deleted = service.delete_telemetry(db, telemetry_id)
        if deleted:
            logger.info("Motor telemetry deleted: id=%s", telemetry_id)
            return {"detail": "Telemetry deleted successfully"}
        else:
            logger.warning("Telemetry not found for deletion: id=%s", telemetry_id)
            raise HTTPException(status_code=404, detail="Telemetry not found")

    except AppException as e:
        logger.error("Failed to delete telemetry id=%s: %s", telemetry_id, str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Unexpected error deleting telemetry id=%s: %s", telemetry_id, str(e))
        raise HTTPException(status_code=500, detail="Internal server error")