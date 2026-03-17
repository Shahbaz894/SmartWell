from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.schemas.device_schema import DeviceCreate, DeviceResponse
from app.services.device_service import DeviceService
from app.core.logger import logger
from app.core.exceptions import AppException

router = APIRouter(prefix="/devices", tags=["Devices"])

@router.post("/", response_model=DeviceResponse)
def create_device(
    device: DeviceCreate,
    user_id: str = Query(..., description="User ID for which device is being created"),
    db: Session = Depends(get_db)
):
    service = DeviceService(db)
    try:
        # Pass the 'device' Pydantic model as 'device_data'
        created_device = service.create_device(
            user_id=user_id, 
            device_data=device  # This matches the 'device_data' argument in your Service
        )
        return created_device
    except AppException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Unexpected error: %s", str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/", response_model=List[DeviceResponse])
def get_devices(
    user_id: str = Query(..., description="User ID to fetch devices"),
    db: Session = Depends(get_db)
):
    service = DeviceService(db)
    try:
        devices = service.get_user_devices(user_id)
        logger.info("Fetched %d devices for user_id=%s", len(devices), user_id)
        return devices

    except AppException as e:
        logger.error(
            "Failed to fetch devices for user_id=%s: %s",
            user_id,
            str(e)
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            "Unexpected error fetching devices for user_id=%s: %s",
            user_id,
            str(e)
        )
        raise HTTPException(status_code=500, detail="Internal server error")