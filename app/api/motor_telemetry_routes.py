from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
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

router = APIRouter(prefix="/telemetry", tags=["Motor Telemetry"])


def get_service():
    return MotorTelemetryService()


def _raise_http_error(exc: AppException):
    raise HTTPException(
        status_code=getattr(exc, "status_code", 500),
        detail=getattr(exc, "detail", str(exc)),
    )


@router.post(
    "/{device_id}",
    response_model=MotorTelemetryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="HTTP test ingestion for telemetry",
)
def create_telemetry(
    device_id: str,
    payload: MotorTelemetryCreate,
    db: Session = Depends(get_db),
    service: MotorTelemetryService = Depends(get_service),
):
    """
    Store telemetry through HTTP.

    MQTT note:
    ESP32 should normally publish telemetry to:
        tubewell/{device_uid}/telemetry

    This endpoint is kept for Swagger, curl, and debugging only.
    """
    try:
        created = service.create_telemetry(db, device_id, payload)

        logger.info(
            "HTTP telemetry API create success: device_id=%s telemetry_id=%s",
            device_id,
            created.id,
        )

        return created

    except AppException as exc:
        logger.error(
            "HTTP telemetry API create failed: device_id=%s detail=%s",
            device_id,
            getattr(exc, "detail", str(exc)),
            exc_info=True,
        )
        _raise_http_error(exc)

    except Exception as exc:
        logger.error(
            "HTTP telemetry API unexpected create error: device_id=%s error_type=%s error=%s",
            device_id,
            type(exc).__name__,
            str(exc),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected telemetry create error: {type(exc).__name__}: {str(exc)}",
        )


@router.get(
    "/{device_id}/latest",
    response_model=Optional[MotorTelemetryResponse],
    summary="Get latest live telemetry",
)
def get_latest_live_telemetry(
    device_id: str,
    db: Session = Depends(get_db),
    service: MotorTelemetryService = Depends(get_service),
    user: User = Depends(get_current_user),
):
    """
    Return latest live telemetry saved in PostgreSQL.

    It does not read directly from MQTT.
    MQTT subscriber stores telemetry first, then this route reads DB.
    """
    try:
        latest = service.get_latest_live(db, device_id)

        logger.info(
            "Telemetry API latest success: user_id=%s device_id=%s found=%s",
            user.id,
            device_id,
            latest is not None,
        )

        return latest

    except AppException as exc:
        logger.error(
            "Telemetry API latest failed: user_id=%s device_id=%s detail=%s",
            user.id,
            device_id,
            getattr(exc, "detail", str(exc)),
            exc_info=True,
        )
        _raise_http_error(exc)

    except Exception as exc:
        logger.error(
            "Telemetry API unexpected latest error: user_id=%s device_id=%s error_type=%s error=%s",
            user.id,
            device_id,
            type(exc).__name__,
            str(exc),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected latest telemetry error: {type(exc).__name__}: {str(exc)}",
        )


@router.get(
    "/{device_id}",
    response_model=List[MotorTelemetryResponse],
    summary="Get all telemetry records",
)
def get_device_telemetry(
    device_id: str,
    db: Session = Depends(get_db),
    service: MotorTelemetryService = Depends(get_service),
    user: User = Depends(get_current_user),
):
    """
    Return stored telemetry records for dashboard.
    """
    try:
        records = service.get_device_telemetry(db, device_id)

        logger.info(
            "Telemetry API list success: user_id=%s device_id=%s count=%s",
            user.id,
            device_id,
            len(records),
        )

        return records

    except AppException as exc:
        logger.error(
            "Telemetry API list failed: user_id=%s device_id=%s detail=%s",
            user.id,
            device_id,
            getattr(exc, "detail", str(exc)),
            exc_info=True,
        )
        _raise_http_error(exc)

    except Exception as exc:
        logger.error(
            "Telemetry API unexpected list error: user_id=%s device_id=%s error_type=%s error=%s",
            user.id,
            device_id,
            type(exc).__name__,
            str(exc),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected telemetry list error: {type(exc).__name__}: {str(exc)}",
        )


@router.delete(
    "/record/{telemetry_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete telemetry record",
)
def delete_telemetry(
    telemetry_id: UUID,
    db: Session = Depends(get_db),
    service: MotorTelemetryService = Depends(get_service),
    user: User = Depends(get_current_user),
):
    """
    Delete one telemetry record.

    Route uses /record/{telemetry_id} to avoid conflict with /{device_id}.
    """
    try:
        deleted = service.delete_telemetry(db, telemetry_id)

        if not deleted:
            raise NotFoundException(detail="Telemetry not found")

        logger.info(
            "Telemetry API delete success: user_id=%s telemetry_id=%s",
            user.id,
            telemetry_id,
        )

        return {
            "detail": "Telemetry deleted successfully",
            "telemetry_id": str(telemetry_id),
        }

    except (AppException, NotFoundException) as exc:
        logger.error(
            "Telemetry API delete failed: user_id=%s telemetry_id=%s detail=%s",
            user.id,
            telemetry_id,
            getattr(exc, "detail", str(exc)),
            exc_info=True,
        )
        raise HTTPException(
            status_code=getattr(exc, "status_code", 404),
            detail=getattr(exc, "detail", str(exc)),
        )

    except Exception as exc:
        logger.error(
            "Telemetry API unexpected delete error: user_id=%s telemetry_id=%s error_type=%s error=%s",
            user.id,
            telemetry_id,
            type(exc).__name__,
            str(exc),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected telemetry delete error: {type(exc).__name__}: {str(exc)}",
        )