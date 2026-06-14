from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from app.schemas.motor_timer_schema import TriggerType

from app.core.exceptions import AppException, NotFoundException
from app.core.logger import logger
from app.models.device import Device
from app.models.motor_parameter import MotorTelemetry

# ---- Naye Imports Yahan Add Karein ----
from app.models.motor_timer import MotorTimer  # (Path apne project ke hisab se set karein)
from app.schemas.motor_timer_schema import TriggerType
# ---------------------------------------

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
        self.repo = MotorTelemetryRepository()

    def _get_device_by_uid_or_id(
        self,
        db: Session,
        device_id: str,
    ) -> Optional[Device]:
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
            logger.error("DB error while resolving device", exc_info=True)
            raise AppException(status_code=500, detail=f"Database error while resolving device '{device_id}'")

    def _to_int_or_default(self, value: Any, default: int) -> int:
        if value is None:
            return default
        if isinstance(value, bool):
            return 1 if value else 0
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _normalize_mqtt_payload(self, payload: dict) -> dict:
        normalized = dict(payload)

        now_ts = int(datetime.now(timezone.utc).timestamp())
        normalized["timestamp"] = self._to_int_or_default(normalized.get("timestamp"), now_ts)

        normalized["freq"] = float(normalized.get("freq", 0))
        normalized["current"] = float(normalized.get("current", 0))
        normalized["voltage"] = float(normalized.get("voltage", 0))
        normalized["dcbus"] = float(normalized.get("dcbus", 0))
        normalized["power"] = float(normalized.get("power", 0))
        normalized["reference_freq"] = float(normalized.get("reference_freq", 0))
        normalized["motor_speed"] = float(normalized.get("motor_speed", 0))
        normalized["power_percent"] = float(normalized.get("power_percent", 0))
        normalized["torque_percent"] = float(normalized.get("torque_percent", 0))
        normalized["fault"] = self._to_int_or_default(normalized.get("fault"), 0)
        normalized["fault_code"] = self._to_int_or_default(normalized.get("fault_code"), 0)
        normalized["status_code"] = self._to_int_or_default(normalized.get("status_code"), 0)
        normalized["is_live"] = self._to_int_or_default(normalized.get("is_live"), 0)

        return normalized
    
    

# (Baaki imports waise hi rahenge)

    def _determine_trigger_type(self, db: Session, device_id: UUID, current_trigger: Optional[TriggerType] = None) -> TriggerType:
        """
        Check karta hai ke motor kis cheez se on/off hui (APP, TIMER, SCHEDULE, ya PHYSICAL)
        """
        
        # 1. Agar HTTP/Payload ne khud bataya hai ke trigger type kya hai (e.g., App ne bheja),
        # to physical ko chhor kar baaki sab ko as-is accept kar lein.
        if current_trigger in [TriggerType.APP, TriggerType.SCHEDULE, TriggerType.TIMER]:
            return current_trigger

        # 2. Agar MQTT (Hardware) se call aayi hai (matlab current_trigger = None ya PHYSICAL hai):
        
        # -> Pehle Timer check karein
        active_timer = db.query(MotorTimer).filter(
            MotorTimer.device_id == device_id, 
            MotorTimer.is_running == True
        ).first()

        if active_timer:
            return TriggerType.TIMER

        # -> Phir Schedule check karein (Agar aapke paas Schedule ka table hai)
        # Note: Niche wali line ko apne Schedule table ke hisab se adjust kar lein.
        # active_schedule = db.query(MotorSchedule).filter(
        #     MotorSchedule.device_id == device_id,
        #     MotorSchedule.is_active == True,
        #     # Yahan wo condition lagani hogi jo bataye ke schedule IS WAQT run ho raha hai ya nahi
        # ).first()
        # 
        # if active_schedule:
        #     return TriggerType.SCHEDULE

        # 3. Agar na App se request aayi, na Timer hai, na Schedule hai, 
        # to 100% kisi ne physical button press kiya hai.
        return TriggerType.PHYSICAL

    def _build_telemetry_model(self, device: Device, data: MotorTelemetryCreate) -> MotorTelemetry:
        return MotorTelemetry(
            device_id=str(device.id),
            
            # Yahan Model mein trigger_type map kar diya gaya hai
            trigger_type=data.trigger_type, 
            
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

    def _save_telemetry(self, db: Session, device: Device, data: MotorTelemetryCreate) -> MotorTelemetry:
        telemetry = self._build_telemetry_model(device, data)
        created = self.repo.create(db, telemetry)
        db.commit()
        db.refresh(created)
        return created

    def create_telemetry_from_mqtt(self, db: Session, device_uid: str, payload: dict) -> MotorTelemetry:
        try:
            device = self._get_device_by_uid_or_id(db, device_uid)

            if not device:
                raise AppException(status_code=404, detail=f"Device UID '{device_uid}' not found.")

            normalized_payload = self._normalize_mqtt_payload(payload)

            # ---- YAHAN TRIGGER TYPE DECIDE HO RAHA HAI ----
            trigger = self._determine_trigger_type(db, device.id)
            normalized_payload["trigger_type"] = trigger
            # -----------------------------------------------

            try:
                data = MotorTelemetryCreate(**normalized_payload)
            except ValidationError as exc:
                raise AppException(status_code=400, detail={"message": "Invalid payload", "errors": exc.errors()})

            created = self._save_telemetry(db, device, data)
            return created

        except AppException:
            db.rollback()
            raise
        except Exception as exc:
            db.rollback()
            raise AppException(status_code=500, detail={"message": str(exc)})

    def create_telemetry(self, db: Session, device_id: str, data: MotorTelemetryCreate) -> MotorTelemetry:
        try:
            device = self._get_device_by_uid_or_id(db, device_id)

            if not device:
                raise AppException(status_code=404, detail=f"Device '{device_id}' not found.")

            normalized_payload = self._normalize_mqtt_payload(data.model_dump())

            # ---- HTTP MEIN BHI TRIGGER TYPE DECIDE KAREIN ----
            # Agar user ne body mein TriggerType bheja hai (e.g., App se click kiya), to usko pass karein
            trigger = self._determine_trigger_type(db, device.id, current_trigger=data.trigger_type)
            normalized_payload["trigger_type"] = trigger
            # --------------------------------------------------

            try:
                normalized_data = MotorTelemetryCreate(**normalized_payload)
            except ValidationError as exc:
                raise AppException(status_code=400, detail={"message": "Invalid payload", "errors": exc.errors()})

            created = self._save_telemetry(db, device, normalized_data)
            return created

        except AppException:
            db.rollback()
            raise
        except Exception as exc:
            db.rollback()
            raise AppException(status_code=500, detail={"message": str(exc)})
    def get_device_telemetry(self, db: Session, device_id: str):
        """
        Return all telemetry records for one device, newest first.
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
                "Telemetry fetch error: device_id=%s error=%s",
                device_id,
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

    def get_latest_live(self, db: Session, device_id: str):
        """
        Return latest telemetry packet for dashboard.
        Includes both is_live=1 and is_live=0 so Flutter always sees current state.
        """
        try:
            device = self._get_device_by_uid_or_id(db, device_id)

            if not device:
                logger.warning(
                    "Telemetry latest requested for unknown device: device_id=%s",
                    device_id,
                )
                return None

            latest = self.repo.get_latest(db, str(device.id))

            if not latest:
                logger.warning(
                    "No telemetry found: device_id=%s device_uid=%s",
                    device.id,
                    device.device_uid,
                )
                return None

            logger.info(
                "Latest telemetry fetched: telemetry_id=%s device_uid=%s status_code=%s fault=%s is_live=%s",
                latest.id,
                device.device_uid,
                latest.status_code,
                latest.fault,
                latest.is_live,
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
                "Latest telemetry fetch error: device_id=%s error=%s",
                device_id,
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

    def delete_telemetry(self, db: Session, telemetry_id: UUID):
        """
        Delete one telemetry record by UUID.
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
                "Telemetry delete error: telemetry_id=%s error=%s",
                telemetry_id,
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