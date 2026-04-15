# app/api/motor_telemetry_routes.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List

from app.db.session import get_db
from app.services.motor_telemetry_service import MotorTelemetryService
from app.schemas.motor_telemetry_schema import (
    MotorTelemetryCreate,
    MotorTelemetryResponse
)
from app.core.logger import logger
from app.core.exceptions import (
    AppException,
    ValidationException,
    NotFoundException
)


router = APIRouter(
    prefix="/telemetry",
    tags=["Motor Telemetry"]
)


# =========================================================
# 🔧 Dependency Injection
# =========================================================
def get_service():
    """Provide MotorTelemetryService instance."""
    return MotorTelemetryService()


# =========================================================
# 🚀 CREATE TELEMETRY (ESP32)
# =========================================================
@router.post("/devices/{device_id}", response_model=MotorTelemetryResponse)
def create_telemetry(
    device_id: str,
    data: MotorTelemetryCreate,
    db: Session = Depends(get_db),
    service: MotorTelemetryService = Depends(get_service)
):
    """
    Create telemetry record for a specific device.

    This endpoint is primarily used by ESP32 devices to send
    real-time motor data such as voltage, current, power, etc.

    Args:
        device_id (str): Unique identifier of the device
        data (MotorTelemetryCreate): Telemetry payload
        db (Session): Database session

    Returns:
        MotorTelemetryResponse: Created telemetry record
    """

    logger.info("Create telemetry request received: device_id=%s", device_id)

    # ✅ Validate device_id consistency
    if data.device_id and data.device_id != device_id:
        logger.warning(
            "Device ID mismatch: path=%s body=%s",
            device_id,
            data.device_id
        )
        raise ValidationException("Device ID mismatch")

    try:
        telemetry = service.create_telemetry(db, device_id, data)

        logger.info(
            "Telemetry created successfully: device_id=%s telemetry_id=%s",
            device_id,
            telemetry.id
        )

        return telemetry

    except AppException:
        # Already handled business error
        raise

    except Exception as e:
        logger.error(
            "Unexpected error while creating telemetry: device_id=%s error=%s",
            device_id,
            str(e),
            exc_info=True
        )
        db.rollback()
        raise AppException(500, "Failed to create telemetry")


# =========================================================
# 📊 GET TELEMETRY BY DEVICE
# =========================================================
@router.get(
    "/devices/{device_id}",
    response_model=List[MotorTelemetryResponse]
)
def get_device_telemetry(
    device_id: str,
    db: Session = Depends(get_db),
    service: MotorTelemetryService = Depends(get_service)
):
    """
    Fetch all telemetry records for a given device.

    Args:
        device_id (str): Device identifier
        db (Session): Database session

    Returns:
        List[MotorTelemetryResponse]: List of telemetry records
    """

    logger.info("Fetching telemetry: device_id=%s", device_id)

    try:
        telemetry_list = service.get_device_telemetry(db, device_id)

        logger.info(
            "Telemetry fetched successfully: device_id=%s count=%d",
            device_id,
            len(telemetry_list)
        )

        return telemetry_list

    except AppException:
        raise

    except Exception as e:
        logger.error(
            "Unexpected error fetching telemetry: device_id=%s error=%s",
            device_id,
            str(e),
            exc_info=True
        )
        raise AppException(500, "Failed to fetch telemetry")


# =========================================================
# 🗑 DELETE TELEMETRY
# =========================================================
@router.delete("/{telemetry_id}")
def delete_telemetry(
    telemetry_id: UUID,
    db: Session = Depends(get_db),
    service: MotorTelemetryService = Depends(get_service)
):
    """
    Delete a telemetry record by its ID.

    Args:
        telemetry_id (UUID): Telemetry record ID
        db (Session): Database session

    Returns:
        dict: Success message
    """

    logger.info("Delete telemetry request: id=%s", telemetry_id)

    try:
        deleted = service.delete_telemetry(db, telemetry_id)

        if not deleted:
            logger.warning("Telemetry not found: id=%s", telemetry_id)
            raise NotFoundException("Telemetry not found")

        logger.info("Telemetry deleted successfully: id=%s", telemetry_id)

        return {"detail": "Telemetry deleted successfully"}

    except AppException:
        raise

    except Exception as e:
        logger.error(
            "Unexpected error deleting telemetry: id=%s error=%s",
            telemetry_id,
            str(e),
            exc_info=True
        )
        db.rollback()
        raise AppException(500, "Failed to delete telemetry")