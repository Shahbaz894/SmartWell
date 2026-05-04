# from uuid import UUID

# from sqlalchemy.orm import Session
# from sqlalchemy.exc import SQLAlchemyError, IntegrityError

# from app.core.exceptions import AppException, NotFoundException
# from app.core.logger import logger
# from app.models.device import Device
# from app.models.motor_parameter import MotorTelemetry
# from app.repositories.motor_telemetry_repo import MotorTelemetryRepository
# from app.schemas.motor_telemetry_schema import MotorTelemetryCreate


# class MotorTelemetryService:
#     """
#     Service layer for motor telemetry.

#     MQTT design:
#     - ESP32 publishes telemetry to:
#         tubewell/{device_uid}/telemetry

#     - FastAPI MQTT subscriber receives the payload.
#     - Backend finds device by device_uid.
#     - Backend stores telemetry in PostgreSQL.

#     This service supports both:
#     - HTTP telemetry, if your old route still exists.
#     - MQTT telemetry, through create_telemetry_from_mqtt().
#     """

#     def __init__(self):
#         self.repo = MotorTelemetryRepository()

#     def _get_device_by_uid_or_id(self, db: Session, device_id: str) -> Device | None:
#         """
#         Resolve a device from either:
#         - device_uid, for example ESP32_001_TW
#         - internal UUID devices.id

#         Returns None if no device is found.
#         """
#         device = db.query(Device).filter(Device.device_uid == device_id).first()

#         if device:
#             return device

#         try:
#             parsed_id = UUID(device_id)
#         except ValueError:
#             return None

#         return db.query(Device).filter(Device.id == parsed_id).first()

#     def create_telemetry_from_mqtt(
#         self,
#         db: Session,
#         device_uid: str,
#         payload: dict,
#     ) -> MotorTelemetry:
#         """
#         Store telemetry received from ESP32 through MQTT.

#         Args:
#             db: SQLAlchemy session.
#             device_uid: UID extracted from MQTT topic.
#             payload: JSON payload published by ESP32.

#         Returns:
#             Created telemetry row.

#         Raises:
#             AppException:
#                 404 if device_uid is not registered.
#                 400 if payload is invalid.
#                 500 if database insert fails.
#         """
#         try:
#             logger.info(
#                 "MQTT telemetry create requested: device_uid=%s payload=%s",
#                 device_uid,
#                 payload,
#             )

#             device = self._get_device_by_uid_or_id(db, device_uid)

#             if not device:
#                 logger.warning(
#                     "MQTT telemetry rejected. Device UID not found: device_uid=%s",
#                     device_uid,
#                 )
#                 raise AppException(
#                     status_code=404,
#                     detail=f"Device UID '{device_uid}' not found. Register device first.",
#                 )

#             telemetry = MotorTelemetry(
#                 device_id=str(device.id),
#                 timestamp=payload.get("timestamp"),
#                 freq=payload.get("freq"),
#                 current=payload.get("current"),
#                 voltage=payload.get("voltage"),
#                 dcbus=payload.get("dcbus"),
#                 power=payload.get("power"),
#                 energy_in=payload.get("energy_in"),
#                 fault=payload.get("fault"),
#                 fault_code=payload.get("fault_code"),
#                 status_code=payload.get("status_code"),
#                 reference_freq=payload.get("reference_freq"),
#                 motor_speed=payload.get("motor_speed"),
#                 power_percent=payload.get("power_percent"),
#                 torque_percent=payload.get("torque_percent"),
#                 is_live=payload.get("is_live", True),
#             )

#             created = self.repo.create(db, telemetry)
#             db.commit()
#             db.refresh(created)

#             logger.info(
#                 "MQTT telemetry stored: telemetry_id=%s device_id=%s device_uid=%s freq=%s voltage=%s current=%s live=%s",
#                 created.id,
#                 created.device_id,
#                 device.device_uid,
#                 created.freq,
#                 created.voltage,
#                 created.current,
#                 created.is_live,
#             )

#             return created

#         except AppException:
#             db.rollback()
#             raise

#         except IntegrityError as exc:
#             db.rollback()
#             logger.error(
#                 "MQTT telemetry integrity error: device_uid=%s db_error=%s payload=%s",
#                 device_uid,
#                 str(exc.orig) if hasattr(exc, "orig") else str(exc),
#                 payload,
#                 exc_info=True,
#             )
#             raise AppException(
#                 status_code=400,
#                 detail=f"MQTT telemetry insert failed. DB error: {str(exc.orig) if hasattr(exc, 'orig') else str(exc)}",
#             )

#         except SQLAlchemyError as exc:
#             db.rollback()
#             logger.error(
#                 "MQTT telemetry database error: device_uid=%s db_error=%s payload=%s",
#                 device_uid,
#                 str(exc.orig) if hasattr(exc, "orig") else str(exc),
#                 payload,
#                 exc_info=True,
#             )
#             raise AppException(
#                 status_code=500,
#                 detail=f"Database error while storing MQTT telemetry: {str(exc.orig) if hasattr(exc, 'orig') else str(exc)}",
#             )

#         except Exception as exc:
#             db.rollback()
#             logger.error(
#                 "Unexpected MQTT telemetry error: device_uid=%s error_type=%s error=%s payload=%s",
#                 device_uid,
#                 type(exc).__name__,
#                 str(exc),
#                 payload,
#                 exc_info=True,
#             )
#             raise AppException(
#                 status_code=500,
#                 detail=f"Unexpected MQTT telemetry error: {type(exc).__name__}: {str(exc)}",
#             )

#     def create_telemetry(
#         self,
#         db: Session,
#         device_id: str,
#         data: MotorTelemetryCreate,
#     ) -> MotorTelemetry:
#         """
#         Store telemetry received through HTTP.

#         Keep this only if your old HTTP telemetry route is still active.
#         If telemetry is now MQTT-only, this method can remain for testing.
#         """
#         try:
#             logger.info(
#                 "HTTP telemetry create requested: device_id=%s is_live=%s",
#                 device_id,
#                 getattr(data, "is_live", None),
#             )

#             device = self._get_device_by_uid_or_id(db, device_id)

#             if not device:
#                 raise AppException(
#                     status_code=404,
#                     detail=f"Device '{device_id}' not found. Register device first.",
#                 )

#             telemetry = MotorTelemetry(
#                 device_id=str(device.id),
#                 timestamp=data.timestamp,
#                 freq=data.freq,
#                 current=data.current,
#                 voltage=data.voltage,
#                 dcbus=data.dcbus,
#                 power=data.power,
#                 energy_in=data.energy_in,
#                 fault=data.fault,
#                 fault_code=data.fault_code,
#                 status_code=data.status_code,
#                 reference_freq=data.reference_freq,
#                 motor_speed=data.motor_speed,
#                 power_percent=data.power_percent,
#                 torque_percent=data.torque_percent,
#                 is_live=data.is_live,
#             )

#             created = self.repo.create(db, telemetry)
#             db.commit()
#             db.refresh(created)

#             logger.info(
#                 "HTTP telemetry stored: telemetry_id=%s device_id=%s device_uid=%s",
#                 created.id,
#                 created.device_id,
#                 device.device_uid,
#             )

#             return created

#         except AppException:
#             db.rollback()
#             raise

#         except SQLAlchemyError as exc:
#             db.rollback()
#             logger.error(
#                 "HTTP telemetry database error: device_id=%s db_error=%s",
#                 device_id,
#                 str(exc.orig) if hasattr(exc, "orig") else str(exc),
#                 exc_info=True,
#             )
#             raise AppException(
#                 status_code=500,
#                 detail=f"Database error while creating telemetry: {str(exc.orig) if hasattr(exc, 'orig') else str(exc)}",
#             )

#         except Exception as exc:
#             db.rollback()
#             logger.error(
#                 "Unexpected HTTP telemetry error: device_id=%s error_type=%s error=%s",
#                 device_id,
#                 type(exc).__name__,
#                 str(exc),
#                 exc_info=True,
#             )
#             raise AppException(
#                 status_code=500,
#                 detail=f"Unexpected error while creating telemetry: {type(exc).__name__}: {str(exc)}",
#             )

#     def get_device_telemetry(self, db: Session, device_id: str):
#         """
#         Return all telemetry records for one device.

#         Accepts both:
#         - device_uid, for example ESP32_001_TW
#         - internal UUID devices.id

#         If the device exists but has no telemetry, returns an empty list.
#         """
#         try:
#             device = self._get_device_by_uid_or_id(db, device_id)

#             if not device:
#                 logger.warning(
#                     "Telemetry list requested for unknown device: device_id=%s",
#                     device_id,
#                 )
#                 return []

#             records = self.repo.get_by_device(db, str(device.id))

#             logger.info(
#                 "Telemetry fetched: device_id=%s device_uid=%s count=%s",
#                 device.id,
#                 device.device_uid,
#                 len(records),
#             )

#             return records

#         except Exception as exc:
#             logger.error(
#                 "Telemetry fetch error: device_id=%s error_type=%s error=%s",
#                 device_id,
#                 type(exc).__name__,
#                 str(exc),
#                 exc_info=True,
#             )
#             raise AppException(
#                 status_code=500,
#                 detail=f"Failed to fetch telemetry: {type(exc).__name__}: {str(exc)}",
#             )

#     def get_latest_live(self, db: Session, device_id: str):
#         """
#         Return latest live telemetry packet.

#         Accepts both:
#         - device_uid, for example ESP32_001_TW
#         - internal UUID devices.id

#         If the device exists but has no telemetry, returns None.
#         """
#         try:
#             device = self._get_device_by_uid_or_id(db, device_id)

#             if not device:
#                 logger.warning(
#                     "Telemetry latest requested for unknown device: device_id=%s",
#                     device_id,
#                 )
#                 return None

#             latest = self.repo.get_latest_live(db, str(device.id))

#             if not latest:
#                 logger.warning(
#                     "No live telemetry found: device_id=%s device_uid=%s",
#                     device.id,
#                     device.device_uid,
#                 )
#                 return None

#             logger.info(
#                 "Latest telemetry fetched: telemetry_id=%s device_id=%s device_uid=%s",
#                 latest.id,
#                 device.id,
#                 device.device_uid,
#             )

#             return latest

#         except Exception as exc:
#             logger.error(
#                 "Latest telemetry fetch error: device_id=%s error_type=%s error=%s",
#                 device_id,
#                 type(exc).__name__,
#                 str(exc),
#                 exc_info=True,
#             )
#             raise AppException(
#                 status_code=500,
#                 detail=f"Failed to fetch latest telemetry: {type(exc).__name__}: {str(exc)}",
#             )

#     def delete_telemetry(self, db: Session, telemetry_id: UUID):
#         """
#         Delete telemetry record by ID.
#         """
#         try:
#             deleted = self.repo.delete(db, str(telemetry_id))
#             db.commit()

#             logger.info(
#                 "Telemetry deleted: telemetry_id=%s device_id=%s",
#                 deleted.id,
#                 deleted.device_id,
#             )

#             return deleted

#         except (AppException, NotFoundException):
#             db.rollback()
#             raise

#         except Exception as exc:
#             db.rollback()
#             logger.error(
#                 "Telemetry delete error: telemetry_id=%s error_type=%s error=%s",
#                 telemetry_id,
#                 type(exc).__name__,
#                 str(exc),
#                 exc_info=True,
#             )
#             raise AppException(
#                 status_code=500,
#                 detail=f"Failed to delete telemetry: {type(exc).__name__}: {str(exc)}",
#             )

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException, NotFoundException
from app.core.logger import logger
from app.models.device import Device
from app.models.motor_parameter import MotorTelemetry
from app.repositories.motor_telemetry_repo import MotorTelemetryRepository
from app.schemas.motor_telemetry_schema import MotorTelemetryCreate


class MotorTelemetryService:
    """
    Service layer for motor telemetry operations.

    MQTT design:
    - ESP32 publishes telemetry to:
        tubewell/{device_uid}/telemetry

    - Backend MQTT subscriber receives the payload.
    - Backend resolves the device by device_uid.
    - Backend validates and normalizes payload values.
    - Backend stores telemetry in PostgreSQL.

    This service supports:
    - HTTP telemetry creation for Swagger, curl, Postman, and debugging.
    - MQTT telemetry creation for ESP32 live data.
    - Latest telemetry lookup for dashboard.
    - Telemetry list lookup for history.
    - Telemetry deletion by record ID.
    """

    def __init__(self):
        """
        Initialize telemetry service with repository dependency.
        """
        self.repo = MotorTelemetryRepository()

    def _get_device_by_uid_or_id(
        self,
        db: Session,
        device_id: str,
    ) -> Optional[Device]:
        """
        Resolve a device from either device_uid or internal UUID.

        Args:
            db: SQLAlchemy database session.
            device_id: Public device_uid such as ESP32_001_TW, or internal UUID.

        Returns:
            Device if found, otherwise None.
        """
        try:
            device = (
                db.query(Device)
                .filter(Device.device_uid == device_id)
                .first()
            )

            if device:
                return device

            try:
                parsed_id = UUID(device_id)
            except ValueError:
                return None

            return (
                db.query(Device)
                .filter(Device.id == parsed_id)
                .first()
            )

        except SQLAlchemyError as exc:
            logger.error(
                "DB error while resolving device: device_id=%s error=%s",
                device_id,
                str(exc.orig) if hasattr(exc, "orig") else str(exc),
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=f"Database error while resolving device '{device_id}'",
            )

    def _to_int_or_default(
        self,
        value: Any,
        default: int,
    ) -> int:
        """
        Convert a value to integer safely.

        This helper accepts int, float, bool, and numeric strings.
        Invalid values return the provided default.
        """
        if value is None:
            return default

        if isinstance(value, bool):
            return 1 if value else 0

        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _normalize_mqtt_payload(
        self,
        payload: dict,
    ) -> dict:
        """
        Normalize raw MQTT payload from ESP32 before Pydantic validation.

        This method protects database inserts when ESP32 sends:
        - booleans instead of 0 or 1
        - numeric strings instead of integers
        - null or missing values
        - timestamp 0

        Returns:
            Normalized dictionary ready for MotorTelemetryCreate validation.
        """
        normalized = dict(payload)

        if not normalized.get("timestamp"):
            normalized["timestamp"] = int(datetime.now(timezone.utc).timestamp())

        normalized["timestamp"] = self._to_int_or_default(
            normalized.get("timestamp"),
            int(datetime.now(timezone.utc).timestamp()),
        )

        if normalized["timestamp"] <= 0:
            logger.warning(
                "MQTT telemetry timestamp was invalid. Replacing with current server timestamp. payload=%s",
                payload,
            )
            normalized["timestamp"] = int(datetime.now(timezone.utc).timestamp())

        normalized["fault"] = self._to_int_or_default(
            normalized.get("fault"),
            0,
        )

        normalized["fault_code"] = self._to_int_or_default(
            normalized.get("fault_code"),
            0,
        )

        normalized["status_code"] = self._to_int_or_default(
            normalized.get("status_code"),
            3,
        )

        normalized["is_live"] = self._to_int_or_default(
            normalized.get("is_live"),
            1,
        )

        if normalized["fault_code"] > 0:
            normalized["fault"] = 1

        if normalized["status_code"] == 4:
            normalized["fault"] = 1

        return normalized

    def _build_telemetry_model(
        self,
        device: Device,
        data: MotorTelemetryCreate,
    ) -> MotorTelemetry:
        """
        Convert validated telemetry schema into SQLAlchemy model.

        Args:
            device: Resolved device model.
            data: Validated telemetry data.

        Returns:
            MotorTelemetry SQLAlchemy model instance.
        """
        return MotorTelemetry(
            device_id=str(device.id),
            timestamp=data.timestamp,
            freq=data.freq,
            current=data.current,
            voltage=data.voltage,
            dcbus=data.dcbus,
            power=data.power,
            energy_in=data.energy_in,
            fault=data.fault,
            fault_code=data.fault_code,
            status_code=data.status_code,
            reference_freq=data.reference_freq,
            motor_speed=data.motor_speed,
            power_percent=data.power_percent,
            torque_percent=data.torque_percent,
            is_live=data.is_live,
        )

    def create_telemetry_from_mqtt(
        self,
        db: Session,
        device_uid: str,
        payload: dict,
    ) -> MotorTelemetry:
        """
        Store telemetry received from ESP32 through MQTT.

        Args:
            db: SQLAlchemy database session.
            device_uid: Device UID extracted from MQTT topic.
            payload: JSON payload published by ESP32.

        Returns:
            Created telemetry row.

        Raises:
            AppException:
                404 if device_uid is not registered.
                400 if payload is invalid.
                500 if database insert fails.
        """
        try:
            logger.info(
                "MQTT telemetry create requested: device_uid=%s payload=%s",
                device_uid,
                payload,
            )

            device = self._get_device_by_uid_or_id(db, device_uid)

            if not device:
                logger.warning(
                    "MQTT telemetry rejected. Device UID not found: device_uid=%s",
                    device_uid,
                )
                raise AppException(
                    status_code=404,
                    detail=f"Device UID '{device_uid}' not found. Register device first.",
                )

            normalized_payload = self._normalize_mqtt_payload(payload)

            try:
                data = MotorTelemetryCreate(**normalized_payload)
            except ValidationError as exc:
                logger.error(
                    "Invalid MQTT telemetry payload: device_uid=%s payload=%s normalized_payload=%s error=%s",
                    device_uid,
                    payload,
                    normalized_payload,
                    exc.errors(),
                    exc_info=True,
                )
                raise AppException(
                    status_code=400,
                    detail={
                        "code": "INVALID_MQTT_TELEMETRY",
                        "message": "Invalid MQTT telemetry payload",
                        "errors": exc.errors(),
                    },
                )

            telemetry = self._build_telemetry_model(device, data)

            created = self.repo.create(db, telemetry)
            db.commit()
            db.refresh(created)

            logger.info(
                "MQTT telemetry stored: telemetry_id=%s device_id=%s device_uid=%s status_code=%s fault=%s fault_code=%s freq=%s voltage=%s current=%s is_live=%s",
                created.id,
                created.device_id,
                device.device_uid,
                created.status_code,
                created.fault,
                created.fault_code,
                created.freq,
                created.voltage,
                created.current,
                created.is_live,
            )

            return created

        except AppException:
            db.rollback()
            raise

        except IntegrityError as exc:
            db.rollback()
            logger.error(
                "MQTT telemetry integrity error: device_uid=%s db_error=%s payload=%s",
                device_uid,
                str(exc.orig) if hasattr(exc, "orig") else str(exc),
                payload,
                exc_info=True,
            )
            raise AppException(
                status_code=400,
                detail={
                    "code": "MQTT_TELEMETRY_INTEGRITY_ERROR",
                    "message": "MQTT telemetry insert failed",
                    "database_error": str(exc.orig) if hasattr(exc, "orig") else str(exc),
                },
            )

        except SQLAlchemyError as exc:
            db.rollback()
            logger.error(
                "MQTT telemetry database error: device_uid=%s db_error=%s payload=%s",
                device_uid,
                str(exc.orig) if hasattr(exc, "orig") else str(exc),
                payload,
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail={
                    "code": "MQTT_TELEMETRY_DATABASE_ERROR",
                    "message": "Database error while storing MQTT telemetry",
                    "database_error": str(exc.orig) if hasattr(exc, "orig") else str(exc),
                },
            )

        except Exception as exc:
            db.rollback()
            logger.error(
                "Unexpected MQTT telemetry error: device_uid=%s error_type=%s error=%s payload=%s",
                device_uid,
                type(exc).__name__,
                str(exc),
                payload,
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail={
                    "code": "MQTT_TELEMETRY_UNEXPECTED_ERROR",
                    "message": f"Unexpected MQTT telemetry error: {type(exc).__name__}: {str(exc)}",
                },
            )

    def create_telemetry(
        self,
        db: Session,
        device_id: str,
        data: MotorTelemetryCreate,
    ) -> MotorTelemetry:
        """
        Store telemetry received through HTTP.

        This method is used by Swagger, curl, Postman, or manual testing.
        ESP32 production telemetry should normally use MQTT.

        Args:
            db: SQLAlchemy database session.
            device_id: Device UID or internal device UUID.
            data: Validated telemetry payload.

        Returns:
            Created telemetry row.

        Raises:
            AppException:
                404 if device is not found.
                500 if database insert fails.
        """
        try:
            logger.info(
                "HTTP telemetry create requested: device_id=%s status_code=%s fault=%s fault_code=%s is_live=%s",
                device_id,
                data.status_code,
                data.fault,
                data.fault_code,
                data.is_live,
            )

            device = self._get_device_by_uid_or_id(db, device_id)

            if not device:
                logger.warning(
                    "HTTP telemetry rejected. Device not found: device_id=%s",
                    device_id,
                )
                raise AppException(
                    status_code=404,
                    detail=f"Device '{device_id}' not found. Register device first.",
                )

            telemetry = self._build_telemetry_model(device, data)

            created = self.repo.create(db, telemetry)
            db.commit()
            db.refresh(created)

            logger.info(
                "HTTP telemetry stored: telemetry_id=%s device_id=%s device_uid=%s status_code=%s fault=%s fault_code=%s is_live=%s",
                created.id,
                created.device_id,
                device.device_uid,
                created.status_code,
                created.fault,
                created.fault_code,
                created.is_live,
            )

            return created

        except AppException:
            db.rollback()
            raise

        except IntegrityError as exc:
            db.rollback()
            logger.error(
                "HTTP telemetry integrity error: device_id=%s db_error=%s",
                device_id,
                str(exc.orig) if hasattr(exc, "orig") else str(exc),
                exc_info=True,
            )
            raise AppException(
                status_code=400,
                detail={
                    "code": "HTTP_TELEMETRY_INTEGRITY_ERROR",
                    "message": "HTTP telemetry insert failed",
                    "database_error": str(exc.orig) if hasattr(exc, "orig") else str(exc),
                },
            )

        except SQLAlchemyError as exc:
            db.rollback()
            logger.error(
                "HTTP telemetry database error: device_id=%s db_error=%s",
                device_id,
                str(exc.orig) if hasattr(exc, "orig") else str(exc),
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail={
                    "code": "HTTP_TELEMETRY_DATABASE_ERROR",
                    "message": "Database error while creating telemetry",
                    "database_error": str(exc.orig) if hasattr(exc, "orig") else str(exc),
                },
            )

        except Exception as exc:
            db.rollback()
            logger.error(
                "Unexpected HTTP telemetry error: device_id=%s error_type=%s error=%s",
                device_id,
                type(exc).__name__,
                str(exc),
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail={
                    "code": "HTTP_TELEMETRY_UNEXPECTED_ERROR",
                    "message": f"Unexpected error while creating telemetry: {type(exc).__name__}: {str(exc)}",
                },
            )

    def get_device_telemetry(
        self,
        db: Session,
        device_id: str,
    ):
        """
        Return all telemetry records for one device.

        Accepts:
        - device_uid, for example ESP32_001_TW
        - internal UUID devices.id

        If the device exists but has no telemetry, this returns an empty list.
        """
        try:
            device = self._get_device_by_uid_or_id(db, device_id)

            if not device:
                logger.warning(
                    "Telemetry list requested for unknown device: device_id=%s",
                    device_id,
                )
                return []

            records = self.repo.get_by_device(db, str(device.id))

            logger.info(
                "Telemetry fetched: device_id=%s device_uid=%s count=%s",
                device.id,
                device.device_uid,
                len(records),
            )

            return records

        except AppException:
            raise

        except SQLAlchemyError as exc:
            logger.error(
                "DB error while fetching telemetry list: device_id=%s error=%s",
                device_id,
                str(exc.orig) if hasattr(exc, "orig") else str(exc),
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail={
                    "code": "TELEMETRY_LIST_DATABASE_ERROR",
                    "message": "Database error while fetching telemetry list",
                    "database_error": str(exc.orig) if hasattr(exc, "orig") else str(exc),
                },
            )

        except Exception as exc:
            logger.error(
                "Telemetry fetch error: device_id=%s error_type=%s error=%s",
                device_id,
                type(exc).__name__,
                str(exc),
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail={
                    "code": "TELEMETRY_LIST_UNEXPECTED_ERROR",
                    "message": f"Failed to fetch telemetry: {type(exc).__name__}: {str(exc)}",
                },
            )

    def get_latest_live(
        self,
        db: Session,
        device_id: str,
    ):
        """
        Return latest live telemetry packet.

        Accepts:
        - device_uid, for example ESP32_001_TW
        - internal UUID devices.id

        If the device exists but has no live telemetry, this returns None.
        """
        try:
            device = self._get_device_by_uid_or_id(db, device_id)

            if not device:
                logger.warning(
                    "Telemetry latest requested for unknown device: device_id=%s",
                    device_id,
                )
                return None

            latest = self.repo.get_latest_live(db, str(device.id))

            if not latest:
                logger.warning(
                    "No live telemetry found: device_id=%s device_uid=%s",
                    device.id,
                    device.device_uid,
                )
                return None

            logger.info(
                "Latest telemetry fetched: telemetry_id=%s device_id=%s device_uid=%s status_code=%s fault=%s fault_code=%s timestamp=%s",
                latest.id,
                device.id,
                device.device_uid,
                latest.status_code,
                latest.fault,
                latest.fault_code,
                latest.timestamp,
            )

            return latest

        except AppException:
            raise

        except SQLAlchemyError as exc:
            logger.error(
                "DB error while fetching latest telemetry: device_id=%s error=%s",
                device_id,
                str(exc.orig) if hasattr(exc, "orig") else str(exc),
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail={
                    "code": "LATEST_TELEMETRY_DATABASE_ERROR",
                    "message": "Database error while fetching latest telemetry",
                    "database_error": str(exc.orig) if hasattr(exc, "orig") else str(exc),
                },
            )

        except Exception as exc:
            logger.error(
                "Latest telemetry fetch error: device_id=%s error_type=%s error=%s",
                device_id,
                type(exc).__name__,
                str(exc),
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail={
                    "code": "LATEST_TELEMETRY_UNEXPECTED_ERROR",
                    "message": f"Failed to fetch latest telemetry: {type(exc).__name__}: {str(exc)}",
                },
            )

    def delete_telemetry(
        self,
        db: Session,
        telemetry_id: UUID,
    ):
        """
        Delete one telemetry record by telemetry UUID.

        Args:
            db: SQLAlchemy database session.
            telemetry_id: Telemetry record UUID.

        Returns:
            Deleted telemetry row.

        Raises:
            NotFoundException:
                If telemetry row does not exist.
            AppException:
                If database deletion fails.
        """
        try:
            deleted = self.repo.delete(db, str(telemetry_id))
            db.commit()

            logger.info(
                "Telemetry deleted: telemetry_id=%s device_id=%s",
                deleted.id,
                deleted.device_id,
            )

            return deleted

        except (AppException, NotFoundException):
            db.rollback()
            raise

        except SQLAlchemyError as exc:
            db.rollback()
            logger.error(
                "DB error while deleting telemetry: telemetry_id=%s error=%s",
                telemetry_id,
                str(exc.orig) if hasattr(exc, "orig") else str(exc),
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail={
                    "code": "TELEMETRY_DELETE_DATABASE_ERROR",
                    "message": "Database error while deleting telemetry",
                    "database_error": str(exc.orig) if hasattr(exc, "orig") else str(exc),
                },
            )

        except Exception as exc:
            db.rollback()
            logger.error(
                "Telemetry delete error: telemetry_id=%s error_type=%s error=%s",
                telemetry_id,
                type(exc).__name__,
                str(exc),
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail={
                    "code": "TELEMETRY_DELETE_UNEXPECTED_ERROR",
                    "message": f"Failed to delete telemetry: {type(exc).__name__}: {str(exc)}",
                },
            )