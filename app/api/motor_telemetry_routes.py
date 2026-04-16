from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.exceptions import AppException, NotFoundException
from app.core.logger import logger
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.motor_telemetry_schema import MotorTelemetryResponse
from app.services.motor_telemetry_service import MotorTelemetryService

router = APIRouter(
    prefix="/telemetry",
    tags=["Motor Telemetry"],
)


def get_service():
    """
    Provide telemetry service instance per request.
    """
    return MotorTelemetryService()


@router.get("/{device_id}", response_model=List[MotorTelemetryResponse])
def get_device_telemetry(
    device_id: str,
    db: Session = Depends(get_db),
    service: MotorTelemetryService = Depends(get_service),
    user: User = Depends(get_current_user),
):
    """
    Return all telemetry records for a device.
    """
    logger.info(
        "Telemetry list requested: user_id=%s, device_id=%s",
        user.id,
        device_id,
    )

    try:
        return service.get_device_telemetry(db, device_id)

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
    """
    logger.info(
        "Latest live telemetry requested: user_id=%s, device_id=%s",
        user.id,
        device_id,
    )

    try:
        return service.get_latest_live(db, device_id)

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