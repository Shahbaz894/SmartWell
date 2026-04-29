from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from app.core.exceptions import AppException, NotFoundException
from app.core.logger import logger
from app.models.device import Device
from app.models.motor_parameter import MotorTelemetry
from app.repositories.motor_telemetry_repo import MotorTelemetryRepository
from app.schemas.motor_telemetry_schema import MotorTelemetryCreate


class MotorTelemetryService:
    """
    Service layer for motor telemetry.

    MQTT design:
    - ESP32 publishes telemetry to:
        tubewell/{device_uid}/telemetry

    - FastAPI MQTT subscriber receives the payload.
    - Backend finds device by device_uid.
    - Backend stores telemetry in PostgreSQL.

    This service supports both:
    - HTTP telemetry, if your route still exists.
    - MQTT telemetry, through create_telemetry_from_mqtt().
    """

    def __init__(self):
        self.repo = MotorTelemetryRepository()

    def create_telemetry_from_mqtt(
        self,
        db: Session,
        device_uid: str,
        payload: dict,
    ) -> MotorTelemetry:
        """
        Store telemetry received from ESP32 through MQTT.

        Args:
            db: SQLAlchemy session.
            device_uid: UID extracted from MQTT topic.
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

            device = db.query(Device).filter(Device.device_uid == device_uid).first()

            if not device:
                logger.warning(
                    "MQTT telemetry rejected. Device UID not found: device_uid=%s",
                    device_uid,
                )
                raise AppException(
                    status_code=404,
                    detail=f"Device UID '{device_uid}' not found. Register device first.",
                )

            telemetry = MotorTelemetry(
                device_id=str(device.id),
                timestamp=payload.get("timestamp"),
                freq=payload.get("freq"),
                current=payload.get("current"),
                voltage=payload.get("voltage"),
                dcbus=payload.get("dcbus"),
                power=payload.get("power"),
                energy_in=payload.get("energy_in"),
                fault=payload.get("fault"),
                fault_code=payload.get("fault_code"),
                status_code=payload.get("status_code"),
                reference_freq=payload.get("reference_freq"),
                motor_speed=payload.get("motor_speed"),
                power_percent=payload.get("power_percent"),
                torque_percent=payload.get("torque_percent"),
                is_live=payload.get("is_live", True),
            )

            created = self.repo.create(db, telemetry)
            db.commit()
            db.refresh(created)

            logger.info(
                "MQTT telemetry stored: telemetry_id=%s device_id=%s device_uid=%s freq=%s voltage=%s current=%s live=%s",
                created.id,
                created.device_id,
                device.device_uid,
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
                detail=f"MQTT telemetry insert failed. DB error: {str(exc.orig) if hasattr(exc, 'orig') else str(exc)}",
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
                detail=f"Database error while storing MQTT telemetry: {str(exc.orig) if hasattr(exc, 'orig') else str(exc)}",
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
                detail=f"Unexpected MQTT telemetry error: {type(exc).__name__}: {str(exc)}",
            )

    def create_telemetry(
        self,
        db: Session,
        device_id: str,
        data: MotorTelemetryCreate,
    ) -> MotorTelemetry:
        """
        Store telemetry received through HTTP.

        Keep this only if your old HTTP telemetry route is still active.
        If telemetry is now MQTT-only, this method can remain for testing.
        """
        try:
            logger.info(
                "HTTP telemetry create requested: device_id=%s is_live=%s",
                device_id,
                getattr(data, "is_live", None),
            )

            device = db.query(Device).filter(Device.id == device_id).first()

            if not device:
                raise AppException(
                    status_code=404,
                    detail=f"Device '{device_id}' not found. Register device first.",
                )

            telemetry = MotorTelemetry(
                device_id=device_id,
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

            created = self.repo.create(db, telemetry)
            db.commit()
            db.refresh(created)

            logger.info(
                "HTTP telemetry stored: telemetry_id=%s device_id=%s uid=%s",
                created.id,
                device_id,
                device.device_uid,
            )

            return created

        except AppException:
            db.rollback()
            raise

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
                detail=f"Database error while creating telemetry: {str(exc.orig) if hasattr(exc, 'orig') else str(exc)}",
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
                detail=f"Unexpected error while creating telemetry: {type(exc).__name__}: {str(exc)}",
            )

    def get_device_telemetry(self, db: Session, device_id: str):
        """
        Return all telemetry records for one device.
        """
        try:
            records = self.repo.get_by_device(db, device_id)

            logger.info(
                "Telemetry fetched: device_id=%s count=%s",
                device_id,
                len(records),
            )

            return records

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
                detail=f"Failed to fetch telemetry: {type(exc).__name__}: {str(exc)}",
            )

    def get_latest_live(self, db: Session, device_id: str):
        """
        Return latest live telemetry packet.
        """
        try:
            latest = self.repo.get_latest_live(db, device_id)

            if not latest:
                logger.warning("No live telemetry found: device_id=%s", device_id)

            return latest

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
                detail=f"Failed to fetch latest telemetry: {type(exc).__name__}: {str(exc)}",
            )

    def delete_telemetry(self, db: Session, telemetry_id: UUID):
        """
        Delete telemetry record by ID.
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
                detail=f"Failed to delete telemetry: {type(exc).__name__}: {str(exc)}",
            )