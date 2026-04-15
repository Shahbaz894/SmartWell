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
from app.core.exceptions import AppException, NotFoundException
from app.core.security import get_current_user
from app.models.user import User


router = APIRouter(
    prefix="/telemetry",
    tags=["Motor Telemetry"]
)


# =========================================================
# 🔧 Dependency
# =========================================================
def get_service():
    """Create MotorTelemetryService instance per request."""
    return MotorTelemetryService()


# =========================================================
# 🚀 CREATE TELEMETRY (ESP32)
# =========================================================
@router.post("/{device_id}", response_model=MotorTelemetryResponse)
def create_telemetry(
    device_id: str,
    data: MotorTelemetryCreate,
    db: Session = Depends(get_db),
    service: MotorTelemetryService = Depends(get_service),
    user: User = Depends(get_current_user)
):
    """
    Create telemetry data from ESP32 device.

    This endpoint is used by IoT devices (ESP32) to send
    real-time motor parameters such as voltage, current,
    power, and status.

    Args:
        device_id (str): Device unique identifier (from URL)
        data (MotorTelemetryCreate): Telemetry payload
        db (Session): Database session
        user (User): Authenticated user

    Returns:
        MotorTelemetryResponse: Created telemetry record
    """

    logger.info(
        "Create telemetry request | user_id=%s | device_id=%s",
        user.id,
        device_id
    )

    try:
        telemetry = service.create_telemetry(db, device_id, data)

        db.commit()
        db.refresh(telemetry)

        logger.info(
            "Telemetry created successfully | device_id=%s | telemetry_id=%s",
            device_id,
            telemetry.id
        )

        return telemetry

    except AppException:
        db.rollback()
        raise

    except Exception as e:
        db.rollback()
        logger.error(
            "Unexpected error creating telemetry | device_id=%s | error=%s",
            device_id,
            str(e),
            exc_info=True
        )
        raise AppException(500, "Failed to create telemetry")


# =========================================================
# 📊 GET TELEMETRY BY DEVICE
# =========================================================
@router.get(
    "/{device_id}",
    response_model=List[MotorTelemetryResponse]
)
def get_device_telemetry(
    device_id: str,
    db: Session = Depends(get_db),
    service: MotorTelemetryService = Depends(get_service),
    user: User = Depends(get_current_user)
):
    """
    Fetch all telemetry records for a specific device.

    Args:
        device_id (str): Device identifier
        db (Session): Database session
        user (User): Authenticated user

    Returns:
        List[MotorTelemetryResponse]: List of telemetry records
    """

    logger.info(
        "Fetch telemetry request | user_id=%s | device_id=%s",
        user.id,
        device_id
    )

    try:
        telemetry_list = service.get_device_telemetry(db, device_id)

        logger.info(
            "Telemetry fetched | device_id=%s | count=%d",
            device_id,
            len(telemetry_list)
        )

        return telemetry_list

    except AppException:
        raise

    except Exception as e:
        logger.error(
            "Unexpected error fetching telemetry | device_id=%s | error=%s",
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
    service: MotorTelemetryService = Depends(get_service),
    user: User = Depends(get_current_user)
):
    """
    Delete a telemetry record by ID.

    Only authenticated users can delete their telemetry data.

    Args:
        telemetry_id (UUID): Telemetry record ID
        db (Session): Database session
        user (User): Authenticated user

    Returns:
        dict: Success message
    """

    logger.info(
        "Delete telemetry request | user_id=%s | telemetry_id=%s",
        user.id,
        telemetry_id
    )

    try:
        deleted = service.delete_telemetry(db, telemetry_id)

        if not deleted:
            raise NotFoundException("Telemetry not found")

        db.commit()

        logger.info(
            "Telemetry deleted successfully | telemetry_id=%s",
            telemetry_id
        )

        return {"detail": "Telemetry deleted successfully"}

    except AppException:
        db.rollback()
        raise

    except Exception as e:
        db.rollback()
        logger.error(
            "Unexpected error deleting telemetry | telemetry_id=%s | error=%s",
            telemetry_id,
            str(e),
            exc_info=True
        )
        raise AppException(500, "Failed to delete telemetry")