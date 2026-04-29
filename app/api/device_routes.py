from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.core.logger import logger
from app.db.session import get_db
from app.schemas.device_schema import DeviceCreate, DeviceResponse, DeviceUpdate
from app.services.device_service import DeviceService

router = APIRouter(prefix="/devices", tags=["Devices"])


def _raise_http_error(exc: AppException):
    """
    Convert AppException to FastAPI HTTPException.

    This keeps real service error messages visible in Swagger and frontend.
    """
    raise HTTPException(
        status_code=getattr(exc, "status_code", 500),
        detail=getattr(exc, "detail", str(exc)),
    )


@router.post(
    "/",
    response_model=DeviceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new device",
)
def create_device(
    device: DeviceCreate,
    user_id: str = Query(..., description="Owner user UUID"),
    db: Session = Depends(get_db),
):
    """
    Register a new device.

    MQTT note:
    This endpoint does not publish MQTT.
    It only creates the device in PostgreSQL.
    MQTT commands later use device_uid as topic identity.
    """
    service = DeviceService(db)

    try:
        created_device = service.create_device(
            user_id=user_id,
            device_data=device,
        )

        logger.info(
            "Device API create success: device_id=%s device_uid=%s user_id=%s",
            created_device.id,
            created_device.device_uid,
            user_id,
        )

        return created_device

    except AppException as exc:
        logger.error(
            "Device API create failed: user_id=%s device_uid=%s detail=%s",
            user_id,
            device.device_uid,
            getattr(exc, "detail", str(exc)),
            exc_info=True,
        )
        _raise_http_error(exc)

    except Exception as exc:
        logger.error(
            "Device API unexpected create error: user_id=%s error_type=%s error=%s",
            user_id,
            type(exc).__name__,
            str(exc),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected device create error: {type(exc).__name__}: {str(exc)}",
        )


@router.get(
    "/",
    response_model=List[DeviceResponse],
    summary="Get devices for a user",
)
def get_devices(
    user_id: str = Query(..., description="Owner user UUID"),
    db: Session = Depends(get_db),
):
    """
    Return all devices owned by a user.
    """
    service = DeviceService(db)

    try:
        devices = service.get_user_devices(user_id)

        logger.info(
            "Device API list success: user_id=%s count=%s",
            user_id,
            len(devices),
        )

        return devices

    except AppException as exc:
        logger.error(
            "Device API list failed: user_id=%s detail=%s",
            user_id,
            getattr(exc, "detail", str(exc)),
            exc_info=True,
        )
        _raise_http_error(exc)

    except Exception as exc:
        logger.error(
            "Device API unexpected list error: user_id=%s error_type=%s error=%s",
            user_id,
            type(exc).__name__,
            str(exc),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected device list error: {type(exc).__name__}: {str(exc)}",
        )


@router.put(
    "/{device_id}",
    response_model=DeviceResponse,
    summary="Update device",
)
def update_device(
    device_id: str,
    device: DeviceUpdate,
    user_id: str = Query(..., description="Owner user UUID"),
    db: Session = Depends(get_db),
):
    """
    Update editable device fields.

    MQTT note:
    Updating reference_freq here only changes database value.
    To send frequency to ESP32, use:
        POST /vfd/{device_id}/reference-frequency
    """
    service = DeviceService(db)

    try:
        updated_device = service.update_device(
            device_id=device_id,
            user_id=user_id,
            device_data=device,
        )

        logger.info(
            "Device API update success: device_id=%s user_id=%s",
            device_id,
            user_id,
        )

        return updated_device

    except AppException as exc:
        logger.error(
            "Device API update failed: device_id=%s user_id=%s detail=%s",
            device_id,
            user_id,
            getattr(exc, "detail", str(exc)),
            exc_info=True,
        )
        _raise_http_error(exc)

    except Exception as exc:
        logger.error(
            "Device API unexpected update error: device_id=%s user_id=%s error_type=%s error=%s",
            device_id,
            user_id,
            type(exc).__name__,
            str(exc),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected device update error: {type(exc).__name__}: {str(exc)}",
        )
        
        
@router.delete(
    "/{device_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete device",
)
def delete_device(
    device_id: str,
    user_id: str = Query(..., description="Owner user UUID"),
    db: Session = Depends(get_db),
):
    service = DeviceService(db)

    try:
        service.delete_device(device_id=device_id, user_id=user_id)

        logger.info(
            "Device API delete success: device_id=%s user_id=%s",
            device_id,
            user_id,
        )

        return {
            "message": "Device deleted successfully",
            "device_id": device_id,
        }

    except AppException as exc:
        logger.error(
            "Device API delete failed: device_id=%s user_id=%s detail=%s",
            device_id,
            user_id,
            getattr(exc, "detail", str(exc)),
            exc_info=True,
        )
        _raise_http_error(exc)

    except Exception as exc:
        logger.error(
            "Device API unexpected delete error: device_id=%s user_id=%s error_type=%s error=%s",
            device_id,
            user_id,
            type(exc).__name__,
            str(exc),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected device delete error: {type(exc).__name__}: {str(exc)}",
        )