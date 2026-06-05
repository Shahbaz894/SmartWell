# from fastapi import APIRouter, Depends, HTTPException, status
# from sqlalchemy.orm import Session
# from typing import List

# from app.core.exceptions import AppException
# from app.core.logger import logger
# from app.db.session import get_db
# from app.schemas.motor_schema import (
#     MotorStartRequest,
#     MotorStopRequest,
#     MotorLogResponse,
# )
# from app.services.motor_service import MotorService

# router = APIRouter(prefix="/motor", tags=["Motor"])


# def _raise_http_error(exc: AppException):
#     raise HTTPException(
#         status_code=getattr(exc, "status_code", 500),
#         detail=getattr(exc, "detail", str(exc)),
#     )


# @router.post(
#     "/{device_id}/start",
#     response_model=MotorLogResponse,
#     status_code=status.HTTP_200_OK,
#     summary="Start motor through MQTT",
# )
# def start_motor(
#     device_id: str,
#     payload: MotorStartRequest,
#     db: Session = Depends(get_db),
# ):
#     """
#     Start motor for one device.

#     MQTT flow:
#     API route calls MotorService.
#     MotorService saves motor log.
#     MotorService publishes MQTT command:
#         topic: tubewell/{device_uid}/motor
#         payload: {"command": "ON"}

#     ESP32 receives this command from Mosquitto.
#     """
#     service = MotorService(db)

#     try:
#         motor_log = service.start_motor(
#             device_id=device_id,
#             trigger_type=payload.trigger_type,
#             customer_name=payload.customer_name,
#         )

#         logger.info(
#             "Motor API start success: device_id=%s log_id=%s",
#             device_id,
#             motor_log.id,
#         )

#         return motor_log

#     except AppException as exc:
#         logger.error(
#             "Motor API start failed: device_id=%s detail=%s",
#             device_id,
#             getattr(exc, "detail", str(exc)),
#             exc_info=True,
#         )
#         _raise_http_error(exc)

#     except Exception as exc:
#         logger.error(
#             "Motor API unexpected start error: device_id=%s error_type=%s error=%s",
#             device_id,
#             type(exc).__name__,
#             str(exc),
#             exc_info=True,
#         )
#         raise HTTPException(
#             status_code=500,
#             detail=f"Unexpected motor start error: {type(exc).__name__}: {str(exc)}",
#         )


# @router.post(
#     "/{device_id}/stop",
#     response_model=MotorLogResponse,
#     status_code=status.HTTP_200_OK,
#     summary="Stop motor through MQTT",
# )
# def stop_motor(
#     device_id: str,
#     payload: MotorStopRequest,
#     db: Session = Depends(get_db),
# ):
#     """
#     Stop motor for one device.

#     MQTT flow:
#     API route calls MotorService.
#     MotorService updates motor log.
#     MotorService publishes MQTT command:
#         topic: tubewell/{device_uid}/motor
#         payload: {"command": "OFF"}
#     """
#     service = MotorService(db)

#     try:
#         motor_log = service.stop_motor(
#             device_id=device_id,
#             customer_name=payload.customer_name,
#         )

#         if not motor_log:
#             raise AppException(
#                 status_code=404,
#                 detail=f"No running motor found for device '{device_id}'",
#             )

#         logger.info(
#             "Motor API stop success: device_id=%s log_id=%s duration_minutes=%s",
#             device_id,
#             motor_log.id,
#             motor_log.duration_minutes,
#         )

#         return motor_log

#     except AppException as exc:
#         logger.error(
#             "Motor API stop failed: device_id=%s detail=%s",
#             device_id,
#             getattr(exc, "detail", str(exc)),
#             exc_info=True,
#         )
#         _raise_http_error(exc)

#     except Exception as exc:
#         logger.error(
#             "Motor API unexpected stop error: device_id=%s error_type=%s error=%s",
#             device_id,
#             type(exc).__name__,
#             str(exc),
#             exc_info=True,
#         )
#         raise HTTPException(
#             status_code=500,
#             detail=f"Unexpected motor stop error: {type(exc).__name__}: {str(exc)}",
#         )
        
        
        
# @router.get(
#     "/{device_id}/logs",
#     response_model=List[MotorLogResponse],
#     status_code=status.HTTP_200_OK,
#     summary="Get motor logs by device",
# )
# def get_motor_logs(
#     device_id: str,
#     db: Session = Depends(get_db),
# ):
#     service = MotorService(db)

#     try:
#         return service.get_motor_logs(device_id)

#     except AppException as exc:
#         logger.error(
#             "Motor logs get failed: device_id=%s detail=%s",
#             device_id,
#             getattr(exc, "detail", str(exc)),
#             exc_info=True,
#         )
#         _raise_http_error(exc)

#     except Exception as exc:
#         logger.error(
#             "Motor logs unexpected get error: device_id=%s error_type=%s error=%s",
#             device_id,
#             type(exc).__name__,
#             str(exc),
#             exc_info=True,
#         )
#         raise HTTPException(
#             status_code=500,
#             detail=f"Unexpected motor logs get error: {type(exc).__name__}: {str(exc)}",
#         )


# @router.delete(
#     "/logs/{log_id}",
#     status_code=status.HTTP_200_OK,
#     summary="Delete one motor log",
# )
# def delete_motor_log(
#     log_id: str,
#     db: Session = Depends(get_db),
# ):
#     service = MotorService(db)

#     try:
#         service.delete_motor_log(log_id)

#         return {
#             "detail": "Motor log deleted successfully",
#             "log_id": log_id,
#         }

#     except AppException as exc:
#         logger.error(
#             "Motor log delete failed: log_id=%s detail=%s",
#             log_id,
#             getattr(exc, "detail", str(exc)),
#             exc_info=True,
#         )
#         _raise_http_error(exc)

#     except Exception as exc:
#         logger.error(
#             "Motor log unexpected delete error: log_id=%s error_type=%s error=%s",
#             log_id,
#             type(exc).__name__,
#             str(exc),
#             exc_info=True,
#         )
#         raise HTTPException(
#             status_code=500,
#             detail=f"Unexpected motor log delete error: {type(exc).__name__}: {str(exc)}",
#         )


# @router.delete(
#     "/{device_id}/logs",
#     status_code=status.HTTP_200_OK,
#     summary="Clear all motor logs by device",
# )
# def clear_motor_logs(
#     device_id: str,
#     db: Session = Depends(get_db),
# ):
#     service = MotorService(db)

#     try:
#         deleted_count = service.clear_motor_logs(device_id)

#         return {
#             "detail": "Motor logs cleared successfully",
#             "device_id": device_id,
#             "deleted_count": deleted_count,
#         }

#     except AppException as exc:
#         logger.error(
#             "Motor logs clear failed: device_id=%s detail=%s",
#             device_id,
#             getattr(exc, "detail", str(exc)),
#             exc_info=True,
#         )
#         _raise_http_error(exc)

#     except Exception as exc:
#         logger.error(
#             "Motor logs unexpected clear error: device_id=%s error_type=%s error=%s",
#             device_id,
#             type(exc).__name__,
#             str(exc),
#             exc_info=True,
#         )
#         raise HTTPException(
#             status_code=500,
#             detail=f"Unexpected motor logs clear error: {type(exc).__name__}: {str(exc)}",
#         )
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.core.logger import logger
from app.db.session import get_db
from app.schemas.motor_schema import (
    MotorStartRequest,
    MotorStopRequest,
    MotorLogResponse,
)
from app.services.motor_service import MotorService
# 🚀 NEW PERSISTENT MQTT SERVICE IMPORT
from app.services.mqtt_service import MQTTService 

router = APIRouter(prefix="/motor", tags=["Motor"])


def _raise_http_error(exc: AppException):
    raise HTTPException(
        status_code=getattr(exc, "status_code", 500),
        detail=getattr(exc, "detail", str(exc)),
    )


@router.post(
    "/{device_id}/start",
    response_model=MotorLogResponse,
    status_code=status.HTTP_200_OK,
    summary="Start motor through Optimized MQTT Shared Pool",
)
def start_motor(
    device_id: str,
    payload: MotorStartRequest,
    db: Session = Depends(get_db),
):
    """
    Start motor for one device.
    1. Saves log to PostgreSQL via MotorService.
    2. Fires instantaneous MQTT command via Shared Persistent Client.
    """
    service = MotorService(db)

    try:
        # 1. Database mein log entry write karein
        motor_log = service.start_motor(
            device_id=device_id,
            trigger_type=payload.trigger_type,
            customer_name=payload.customer_name,
        )

        # 2. ⚡ FAST EXPRESS DELIVERY VIA NEW MQTT POOL
        # Is se purana dynamic broker network leak ka masla khatam!
        MQTTService.publish_motor_command(device_uid=device_id, action="ON")

        logger.info(
            "Motor API start success & MQTT fired: device_id=%s log_id=%s",
            device_id,
            motor_log.id,
        )

        return motor_log

    except AppException as exc:
        logger.error(
            "Motor API start failed: device_id=%s detail=%s",
            device_id,
            getattr(exc, "detail", str(exc)),
            exc_info=True,
        )
        _raise_http_error(exc)
    except Exception as exc:
        logger.error(
            "Motor API unexpected start error: device_id=%s error=%s",
            device_id,
            str(exc),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected motor start error: {type(exc).__name__}: {str(exc)}",
        )


@router.post(
    "/{device_id}/stop",
    response_model=MotorLogResponse,
    status_code=status.HTTP_200_OK,
    summary="Stop motor through Optimized MQTT Shared Pool",
)
def stop_motor(
    device_id: str,
    payload: MotorStopRequest,
    db: Session = Depends(get_db),
):
    """
    Stop motor for one device.
    1. Updates log in PostgreSQL via MotorService.
    2. Fires instantaneous MQTT OFF command via Shared Persistent Client.
    """
    service = MotorService(db)

    try:
        # 1. Database status update karein
        motor_log = service.stop_motor(
            device_id=device_id,
            customer_name=payload.customer_name,
        )

        # 🚀 FIX: "No running motor found" crash protection loop bypass.
        # Agar physical button ya out-of-sync state ki wajah se DB log nahi mila, 
        # tab bhi hardware ko safe shutoff command lazmi fire karo!
        if not motor_log:
            logger.warning(f"No running log found in DB for {device_id}, forcing MQTT OFF bypass.")
            MQTTService.publish_motor_command(device_uid=device_id, action="OFF")
            raise AppException(
                status_code=404,
                detail=f"No active database session tracking found for device '{device_id}'. Hardware force-stop signal sent successfully.",
            )

        # 2. ⚡ FAST EXPRESS DELIVERY VIA NEW MQTT POOL
        MQTTService.publish_motor_command(device_uid=device_id, action="OFF")

        logger.info(
            "Motor API stop success & MQTT fired: device_id=%s log_id=%s duration_minutes=%s",
            device_id,
            motor_log.id,
            motor_log.duration_minutes,
        )

        return motor_log

    except AppException as exc:
        logger.error(
            "Motor API stop failed: device_id=%s detail=%s",
            device_id,
            getattr(exc, "detail", str(exc)),
            exc_info=True,
        )
        _raise_http_error(exc)
    except Exception as exc:
        logger.error(
            "Motor API unexpected stop error: device_id=%s error=%s",
            device_id,
            str(exc),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected motor stop error: {type(exc).__name__}: {str(exc)}",
        )


# --- 📜 GET LOGS, DELETE, CLEAR ENDPOINTS AS-IS (NO CHANGES NEEDED) ---

@router.get(
    "/{device_id}/logs",
    response_model=List[MotorLogResponse],
    status_code=status.HTTP_200_OK,
    summary="Get motor logs by device",
)
def get_motor_logs(device_id: str, db: Session = Depends(get_db)):
    service = MotorService(db)
    try:
        return service.get_motor_logs(device_id)
    except AppException as exc:
        _raise_http_error(exc)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete(
    "/logs/{log_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete one motor log",
)
def delete_motor_log(log_id: str, db: Session = Depends(get_db)):
    service = MotorService(db)
    try:
        service.delete_motor_log(log_id)
        return {"detail": "Motor log deleted successfully", "log_id": log_id}
    except AppException as exc:
        _raise_http_error(exc)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete(
    "/{device_id}/logs",
    status_code=status.HTTP_200_OK,
    summary="Clear all motor logs by device",
)
def clear_motor_logs(device_id: str, db: Session = Depends(get_db)):
    service = MotorService(db)
    try:
        deleted_count = service.clear_motor_logs(device_id)
        return {
            "detail": "Motor logs cleared successfully",
            "device_id": device_id,
            "deleted_count": deleted_count,
        }
    except AppException as exc:
        _raise_http_error(exc)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))