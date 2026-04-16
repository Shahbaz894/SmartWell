from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.exceptions import AppException, NotFoundException
from app.core.logger import logger
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.motor_telemetry_schema import (
    MotorTelemetryCreate,
    MotorTelemetryResponse,
)
from app.services.motor_telemetry_service import MotorTelemetryService

router = APIRouter(
    prefix="/telemetry",
    tags=["Motor Telemetry"],
)


def get_service() -> MotorTelemetryService:
    """
    Provide telemetry service instance per request.
    """
    return MotorTelemetryService()


@router.post("/{device_id}", response_model=MotorTelemetryResponse)
def create_telemetry(
    device_id: str,
    payload: MotorTelemetryCreate,
    db: Session = Depends(get_db),
    service: MotorTelemetryService = Depends(get_service),
):
    """
    Create telemetry record for a specific device over HTTP.

    This endpoint is used by ESP32 to send both live and offline telemetry.

    Args:
        device_id: Device identifier from URL path
        payload: Telemetry payload sent by ESP32
        db: Active database session
        service: Motor telemetry service instance

    Returns:
        MotorTelemetryResponse: Created telemetry record

    Raises:
        AppException: For validation, database, or unexpected errors
    """
    logger.info(
        "Telemetry create requested: device_id=%s, is_live=%s, timestamp=%s",
        device_id,
        payload.is_live,
        payload.timestamp,
    )

    try:
        telemetry = service.create_telemetry(
            db=db,
            device_id=device_id,
            data=payload,
        )

        logger.info(
            "Telemetry create success: device_id=%s, telemetry_id=%s",
            device_id,
            telemetry.id,
        )
        return telemetry

    except AppException:
        raise

    except Exception as exc:
        logger.error(
            "Unexpected error creating telemetry: device_id=%s, error=%s",
            device_id,
            exc,
            exc_info=True,
        )
        raise AppException(
            status_code=500,
            detail="Failed to create telemetry",
        )


@router.get("/{device_id}", response_model=List[MotorTelemetryResponse])
def get_device_telemetry(
    device_id: str,
    db: Session = Depends(get_db),
    service: MotorTelemetryService = Depends(get_service),
    user: User = Depends(get_current_user),
):
    """
    Return all telemetry records for a device.

    Args:
        device_id: Device identifier
        db: Active database session
        service: Motor telemetry service instance
        user: Authenticated user

    Returns:
        List[MotorTelemetryResponse]: Telemetry list, newest first
    """
    logger.info(
        "Telemetry list requested: user_id=%s, device_id=%s",
        user.id,
        device_id,
    )

    try:
        telemetry_records = service.get_device_telemetry(db, device_id)

        logger.info(
            "Telemetry list fetched successfully: device_id=%s, count=%s",
            device_id,
            len(telemetry_records),
        )
        return telemetry_records

    except AppException:
        raise

    except Exception as exc:
        logger.error(
            "Unexpected error fetching telemetry list: device_id=%s, error=%s",
            device_id,
            exc,
            exc_info=True,
        )
        raise AppException(
            status_code=500,
            detail="Failed to fetch telemetry records",
        )


@router.get("/{device_id}/latest", response_model=Optional[MotorTelemetryResponse])
def get_latest_live_telemetry(
    device_id: str,
    db: Session = Depends(get_db),
    service: MotorTelemetryService = Depends(get_service),
    user: User = Depends(get_current_user),
):
    """
    Return latest live telemetry for a device.

    Args:
        device_id: Device identifier
        db: Active database session
        service: Motor telemetry service instance
        user: Authenticated user

    Returns:
        Optional[MotorTelemetryResponse]: Latest live record or None
    """
    logger.info(
        "Latest live telemetry requested: user_id=%s, device_id=%s",
        user.id,
        device_id,
    )

    try:
        latest_record = service.get_latest_live(db, device_id)

        if latest_record:
            logger.info(
                "Latest live telemetry fetched successfully: device_id=%s, telemetry_id=%s",
                device_id,
                latest_record.id,
            )
        else:
            logger.warning(
                "No latest live telemetry found: device_id=%s",
                device_id,
            )

        return latest_record

    except AppException:
        raise

    except Exception as exc:
        logger.error(
            "Unexpected error fetching latest live telemetry: device_id=%s, error=%s",
            device_id,
            exc,
            exc_info=True,
        )
        raise AppException(
            status_code=500,
            detail="Failed to fetch latest live telemetry",
        )


@router.delete("/{telemetry_id}")
def delete_telemetry(
    telemetry_id: UUID,
    db: Session = Depends(get_db),
    service: MotorTelemetryService = Depends(get_service),
    user: User = Depends(get_current_user),
):
    """
    Delete telemetry record by ID.

    Args:
        telemetry_id: Telemetry record identifier
        db: Active database session
        service: Motor telemetry service instance
        user: Authenticated user

    Returns:
        dict: Success message
    """
    logger.info(
        "Telemetry delete requested: user_id=%s, telemetry_id=%s",
        user.id,
        telemetry_id,
    )

    try:
        deleted = service.delete_telemetry(db, telemetry_id)

        if not deleted:
            raise NotFoundException(detail="Telemetry not found")

        logger.info(
            "Telemetry delete success: telemetry_id=%s",
            telemetry_id,
        )
        return {"detail": "Telemetry deleted successfully"}

    except (AppException, NotFoundException):
        raise

    except Exception as exc:
        logger.error(
            "Unexpected error deleting telemetry: telemetry_id=%s, error=%s",
            telemetry_id,
            exc,
            exc_info=True,
        )
        raise AppException(
            status_code=500,
            detail="Failed to delete telemetry",
        )