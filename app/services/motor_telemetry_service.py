# app/services/motor_telemetry_service.py
#
# Motor telemetry service layer.
# Handles creation, retrieval, and deletion of telemetry records.
#
# ── AppException Usage ────────────────────────────────────────────────────────
#  Always called as AppException(status_code=int, detail=str).
# ──────────────────────────────────────────────────────────────────────────────

from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.repositories.motor_telemetry_repo import MotorTelemetryRepository
from app.schemas.motor_telemetry_schema import MotorTelemetryCreate
from app.core.logger import logger
from app.core.exceptions import AppException, NotFoundException


class MotorTelemetryService:
    """
    Service layer for MotorTelemetry operations.

    Responsibilities
    ----------------
    - Create telemetry records from device payloads.
    - Retrieve all telemetry for a given device.
    - Delete individual telemetry records by ID.
    - Delegate all persistence to MotorTelemetryRepository.
    """

    def __init__(self):
        self.repo = MotorTelemetryRepository()

    # ─────────────────────────────────────────────────────────────────────────
    # CREATE
    # ─────────────────────────────────────────────────────────────────────────
    def create_telemetry(self, db: Session, data: MotorTelemetryCreate):
        """
        Persist a new telemetry record.

        Parameters
        ----------
        db   : Session               Active SQLAlchemy session.
        data : MotorTelemetryCreate  Validated telemetry payload.

        Returns
        -------
        MotorTelemetry
            The newly created and committed record.

        Raises
        ------
        AppException(400)   Database error during insert.
        """
        try:
            telemetry = self.repo.create(db, data)
            logger.info(
                "Telemetry created: id=%s, device_id=%s",
                telemetry.id, telemetry.device_id,
            )
            return telemetry

        except AppException:
            raise

        except SQLAlchemyError as exc:
            logger.error(
                "DB error creating telemetry for device_id=%s: %s",
                data.device_id, exc, exc_info=True,
            )
            raise AppException(
                status_code=400,
                detail=f"Database error: failed to create telemetry for device '{data.device_id}'",
            )

        except Exception as exc:
            logger.error(
                "Unexpected error creating telemetry: device_id=%s: %s",
                data.device_id, exc, exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=f"Unexpected error while creating telemetry: {exc}",
            )

    # ─────────────────────────────────────────────────────────────────────────
    # GET BY DEVICE
    # ─────────────────────────────────────────────────────────────────────────
    def get_device_telemetry(self, db: Session, device_id: str):
        """
        Return all telemetry records for a device, newest first.

        Parameters
        ----------
        db        : Session   Active SQLAlchemy session.
        device_id : str       Device primary key.

        Returns
        -------
        list[MotorTelemetry]

        Raises
        ------
        AppException(400)   Database error during query.
        """
        try:
            records = self.repo.get_by_device(db, device_id)
            logger.info(
                "Fetched %d telemetry records for device_id=%s",
                len(records), device_id,
            )
            return records

        except AppException:
            raise

        except SQLAlchemyError as exc:
            logger.error(
                "DB error fetching telemetry for device_id=%s: %s",
                device_id, exc, exc_info=True,
            )
            raise AppException(
                status_code=400,
                detail=f"Database error: failed to fetch telemetry for device '{device_id}'",
            )

        except Exception as exc:
            logger.error(
                "Unexpected error fetching telemetry: device_id=%s: %s",
                device_id, exc, exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=f"Unexpected error while fetching telemetry: {exc}",
            )

    # ─────────────────────────────────────────────────────────────────────────
    # DELETE
    # ─────────────────────────────────────────────────────────────────────────
    def delete_telemetry(self, db: Session, telemetry_id: UUID):
        """
        Permanently delete a telemetry record by ID.

        Parameters
        ----------
        db           : Session   Active SQLAlchemy session.
        telemetry_id : UUID      Primary key of the record to delete.

        Returns
        -------
        MotorTelemetry
            The deleted record.

        Raises
        ------
        NotFoundException(404)   Record not found.
        AppException(400)        Database error during delete.
        """
        try:
            deleted = self.repo.delete(db, telemetry_id)
            if not deleted:
                logger.warning(
                    "Telemetry not found for deletion: id=%s", telemetry_id
                )
                raise NotFoundException(
                    detail=f"Telemetry '{telemetry_id}' not found",
                )

            logger.info(
                "Telemetry deleted: id=%s, device_id=%s",
                deleted.id, deleted.device_id,
            )
            return deleted

        except (AppException, NotFoundException):
            raise

        except SQLAlchemyError as exc:
            logger.error(
                "DB error deleting telemetry id=%s: %s",
                telemetry_id, exc, exc_info=True,
            )
            raise AppException(
                status_code=400,
                detail=f"Database error: failed to delete telemetry '{telemetry_id}'",
            )

        except Exception as exc:
            logger.error(
                "Unexpected error deleting telemetry id=%s: %s",
                telemetry_id, exc, exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=f"Unexpected error while deleting telemetry: {exc}",
            )