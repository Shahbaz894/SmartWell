from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.exceptions import AppException, NotFoundException
from app.core.logger import logger
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.motor_telemetry_schema import MotorTelemetryCreate, MotorTelemetryResponse
from app.services.motor_telemetry_service import MotorTelemetryService

router = APIRouter(
    prefix="/telemetry",
    tags=["Motor Telemetry"],
)


def get_service():
    """
    Provide a fresh telemetry service instance per request.
    """
    return MotorTelemetryService()


# ─── ESP32 Public Ingestion (no JWT required) ────────────────────────────────

@router.post(
    "/{device_id}",
    response_model=MotorTelemetryResponse,
    status_code=201,
    summary="Ingest telemetry from ESP32 device",
)
def create_telemetry(
    device_id: str,
    payload: MotorTelemetryCreate,
    db: Session = Depends(get_db),
    service: MotorTelemetryService = Depends(get_service),
):
    """
    Ingest a telemetry packet from an ESP32 device (no auth required).

    The ESP32 sends either a live packet (is_live=1) or an offline
    EEPROM-buffered packet (is_live=0) to this endpoint over HTTP.

    Args:
        device_id: Unique device identifier passed as a path parameter.
        payload:   Validated telemetry payload from the request body.
        db:        Active SQLAlchemy session (injected).
        service:   Telemetry service instance (injected).

    Returns:
        MotorTelemetryResponse: The persisted telemetry record (HTTP 201).

    Raises:
        AppException (422): If payload validation fails (handled by Pydantic).
        AppException (500): On any database or unexpected server error.
    """
    logger.info(
        "Telemetry ingestion requested: device_id=%s, is_live=%s",
        device_id,
        payload.is_live,
    )

    try:
        created = service.create_telemetry(db, device_id, payload)

        logger.info(
            "Telemetry ingested successfully: device_id=%s, telemetry_id=%s",
            device_id,
            created.id,
        )
        return created

    except AppException:
        raise

    except Exception as exc:
        logger.error(
            "Unexpected error ingesting telemetry: device_id=%s, error=%s",
            device_id,
            exc,
            exc_info=True,
        )
        raise AppException(
            status_code=500,
            detail="Failed to ingest telemetry",
        )


# ─── Authenticated Dashboard Endpoints ───────────────────────────────────────

@router.get(
    "/{device_id}/latest",
    response_model=Optional[MotorTelemetryResponse],
    summary="Get latest live telemetry for a device",
)
def get_latest_live_telemetry(
    device_id: str,
    db: Session = Depends(get_db),
    service: MotorTelemetryService = Depends(get_service),
    user: User = Depends(get_current_user),
):
    """
    Return the most recent live telemetry packet for a device.

    NOTE: This route must stay above /{device_id} GET to prevent
    FastAPI from matching the literal string 'latest' as a device_id.

    Args:
        device_id: Unique device identifier passed as a path parameter.
        db:        Active SQLAlchemy session (injected).
        service:   Telemetry service instance (injected).
        user:      Authenticated user from JWT (injected).

    Returns:
        MotorTelemetryResponse or None if no live record exists.
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


@router.get(
    "/{device_id}",
    response_model=List[MotorTelemetryResponse],
    summary="Get all telemetry records for a device",
)
def get_device_telemetry(
    device_id: str,
    db: Session = Depends(get_db),
    service: MotorTelemetryService = Depends(get_service),
    user: User = Depends(get_current_user),
):
    """
    Return all telemetry records for a device, newest first.

    Args:
        device_id: Unique device identifier passed as a path parameter.
        db:        Active SQLAlchemy session (injected).
        service:   Telemetry service instance (injected).
        user:      Authenticated user from JWT (injected).

    Returns:
        List[MotorTelemetryResponse]: All telemetry records for the device.
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


@router.delete(
    "/{telemetry_id}",
    summary="Delete a telemetry record by ID",
)
def delete_telemetry(
    telemetry_id: UUID,
    db: Session = Depends(get_db),
    service: MotorTelemetryService = Depends(get_service),
    user: User = Depends(get_current_user),
):
    """
    Delete a telemetry record by its UUID.

    Args:
        telemetry_id: UUID of the telemetry record to delete.
        db:           Active SQLAlchemy session (injected).
        service:      Telemetry service instance (injected).
        user:         Authenticated user from JWT (injected).

    Returns:
        dict: Confirmation message on successful deletion.

    Raises:
        NotFoundException (404): If the telemetry record does not exist.
        AppException (500):      On any unexpected server error.
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