# from typing import Optional

# from sqlalchemy.orm import Session
# from sqlalchemy.exc import SQLAlchemyError

# from app.models.motor_parameter import MotorTelemetry
# from app.core.exceptions import AppException, NotFoundException
# from app.core.logger import logger


# class MotorTelemetryRepository:
#     """
#     Repository layer for motor telemetry database operations.
#     """

#     def create(self, db: Session, telemetry: MotorTelemetry) -> MotorTelemetry:
#         """
#         Persist a telemetry record.
#         """
#         try:
#             db.add(telemetry)
#             db.flush()
#             db.refresh(telemetry)

#             logger.info(
#                 "Telemetry persisted: id=%s, device_id=%s, is_live=%s",
#                 telemetry.id,
#                 telemetry.device_id,
#                 telemetry.is_live,
#             )
#             return telemetry

#         except SQLAlchemyError as exc:
#             logger.error(
#                 "DB error while persisting telemetry: device_id=%s, error=%s",
#                 telemetry.device_id,
#                 exc,
#                 exc_info=True,
#             )
#             raise AppException(
#                 status_code=500,
#                 detail=f"Database error while creating telemetry for device '{telemetry.device_id}'",
#             )

#     def get_by_device(self, db: Session, device_id: str):
#         """
#         Return all telemetry records for a device, newest first.
#         """
#         try:
#             return (
#                 db.query(MotorTelemetry)
#                 .filter(MotorTelemetry.device_id == device_id)
#                 .order_by(MotorTelemetry.timestamp.desc())
#                 .all()
#             )

#         except SQLAlchemyError as exc:
#             logger.error(
#                 "DB error while fetching telemetry: device_id=%s, error=%s",
#                 device_id,
#                 exc,
#                 exc_info=True,
#             )
#             raise AppException(
#                 status_code=500,
#                 detail=f"Database error while fetching telemetry for device '{device_id}'",
#             )

#     def get_latest_live(self, db: Session, device_id: str) -> Optional[MotorTelemetry]:
#         """
#         Return latest live telemetry record for a device.
#         """
#         try:
#             return (
#                 db.query(MotorTelemetry)
#                 .filter(
#                     MotorTelemetry.device_id == device_id,
#                     MotorTelemetry.is_live == 1,
#                 )
#                 .order_by(MotorTelemetry.timestamp.desc())
#                 .first()
#             )

#         except SQLAlchemyError as exc:
#             logger.error(
#                 "DB error while fetching latest live telemetry: device_id=%s, error=%s",
#                 device_id,
#                 exc,
#                 exc_info=True,
#             )
#             raise AppException(
#                 status_code=500,
#                 detail=f"Database error while fetching latest live telemetry for device '{device_id}'",
#             )

#     def delete(self, db: Session, telemetry_id: str) -> MotorTelemetry:
#         """
#         Delete telemetry by ID.
#         """
#         try:
#             telemetry = (
#                 db.query(MotorTelemetry)
#                 .filter(MotorTelemetry.id == telemetry_id)
#                 .first()
#             )

#             if not telemetry:
#                 raise NotFoundException(detail="Telemetry not found")

#             db.delete(telemetry)
#             db.flush()

#             logger.info(
#                 "Telemetry deleted from session: id=%s, device_id=%s",
#                 telemetry.id,
#                 telemetry.device_id,
#             )
#             return telemetry

#         except NotFoundException:
#             raise

#         except SQLAlchemyError as exc:
#             logger.error(
#                 "DB error while deleting telemetry: telemetry_id=%s, error=%s",
#                 telemetry_id,
#                 exc,
#                 exc_info=True,
#             )
#             raise AppException(
#                 status_code=500,
#                 detail=f"Database error while deleting telemetry '{telemetry_id}'",
#             )
from typing import Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException, NotFoundException
from app.core.logger import logger
from app.models.motor_parameter import MotorTelemetry


class MotorTelemetryRepository:
    """
    Repository layer for motor telemetry database operations.

    This class only handles direct database queries.
    Business validation should stay in the service layer.
    """

    def create(self, db: Session, telemetry: MotorTelemetry) -> MotorTelemetry:
        """
        Persist one telemetry record.

        Args:
            db: Active SQLAlchemy database session.
            telemetry: MotorTelemetry instance to save.

        Returns:
            Saved MotorTelemetry row.

        Raises:
            AppException: If database insert fails.
        """
        try:
            db.add(telemetry)
            db.flush()
            db.refresh(telemetry)

            logger.info(
                "Telemetry persisted: id=%s device_id=%s timestamp=%s "
                "status_code=%s fault=%s fault_code=%s is_live=%s",
                telemetry.id,
                telemetry.device_id,
                telemetry.timestamp,
                telemetry.status_code,
                telemetry.fault,
                telemetry.fault_code,
                telemetry.is_live,
            )

            return telemetry

        except SQLAlchemyError as exc:
            logger.error(
                "DB error while persisting telemetry: device_id=%s error=%s",
                telemetry.device_id,
                str(exc.orig) if hasattr(exc, "orig") else str(exc),
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail={
                    "code": "TELEMETRY_CREATE_DATABASE_ERROR",
                    "message": "Database error while creating telemetry",
                    "device_id": str(telemetry.device_id),
                    "database_error": str(exc.orig)
                    if hasattr(exc, "orig")
                    else str(exc),
                },
            )

    def get_by_device(self, db: Session, device_id: str):
        """
        Return all telemetry records for a device, newest first.

        Args:
            db: Active SQLAlchemy database session.
            device_id: Internal device UUID as string.

        Returns:
            List of MotorTelemetry records ordered by newest timestamp first.

        Raises:
            AppException: If database query fails.
        """
        try:
            records = (
                db.query(MotorTelemetry)
                .filter(MotorTelemetry.device_id == device_id)
                .order_by(MotorTelemetry.timestamp.desc())
                .all()
            )

            logger.info(
                "Telemetry records fetched: device_id=%s count=%s",
                device_id,
                len(records),
            )

            return records

        except SQLAlchemyError as exc:
            logger.error(
                "DB error while fetching telemetry: device_id=%s error=%s",
                device_id,
                str(exc.orig) if hasattr(exc, "orig") else str(exc),
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail={
                    "code": "TELEMETRY_LIST_DATABASE_ERROR",
                    "message": "Database error while fetching telemetry",
                    "device_id": device_id,
                    "database_error": str(exc.orig)
                    if hasattr(exc, "orig")
                    else str(exc),
                },
            )

    def get_latest_live(
        self,
        db: Session,
        device_id: str,
    ) -> Optional[MotorTelemetry]:
        """
        Return the newest telemetry record for a device.

        Important:
        This method intentionally does NOT filter by is_live.

        Reason:
        - is_live = 1 means the latest device state is motor ON.
        - is_live = 0 means the latest device state is motor OFF or offline packet.

        The Flutter Home screen needs both states.
        If this method filters only is_live == 1, the app will keep showing
        an old ON packet and will not update when a new OFF packet arrives.

        The method name is kept as get_latest_live for compatibility with
        existing service code.
        """
        try:
            telemetry = (
                db.query(MotorTelemetry)
                .filter(MotorTelemetry.device_id == device_id)
                .order_by(MotorTelemetry.timestamp.desc())
                .first()
            )

            if telemetry:
                logger.info(
                    "Latest telemetry fetched: id=%s device_id=%s timestamp=%s "
                    "status_code=%s fault=%s fault_code=%s is_live=%s",
                    telemetry.id,
                    telemetry.device_id,
                    telemetry.timestamp,
                    telemetry.status_code,
                    telemetry.fault,
                    telemetry.fault_code,
                    telemetry.is_live,
                )
            else:
                logger.warning(
                    "No telemetry found for device_id=%s",
                    device_id,
                )

            return telemetry

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
                    "device_id": device_id,
                    "database_error": str(exc.orig)
                    if hasattr(exc, "orig")
                    else str(exc),
                },
            )

    def get_latest_live_only(
        self,
        db: Session,
        device_id: str,
    ) -> Optional[MotorTelemetry]:
        """
        Return the newest telemetry record where is_live = 1.

        Use this only if you specifically need the last live/running packet.
        Do not use this for the Home screen, because Home screen must also
        see is_live = 0 packets to show motor OFF.
        """
        try:
            telemetry = (
                db.query(MotorTelemetry)
                .filter(
                    MotorTelemetry.device_id == device_id,
                    MotorTelemetry.is_live == 1,
                )
                .order_by(
                    MotorTelemetry.created_at.desc(),
                    MotorTelemetry.timestamp.desc(),
                    MotorTelemetry.id.desc(),
                )
                .first()
            )

            if telemetry:
                logger.info(
                    "Latest live-only telemetry fetched: id=%s device_id=%s "
                    "created_at=%s timestamp=%s is_live=%s",
                    telemetry.id,
                    telemetry.device_id,
                    telemetry.created_at,
                    telemetry.timestamp,
                    telemetry.is_live,
                )
            else:
                logger.warning(
                    "No live-only telemetry found for device_id=%s",
                    device_id,
                )

            return telemetry

        except SQLAlchemyError as exc:
            logger.error(
                "DB error while fetching live-only telemetry: device_id=%s error=%s",
                device_id,
                str(exc.orig) if hasattr(exc, "orig") else str(exc),
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail={
                    "code": "LATEST_LIVE_TELEMETRY_DATABASE_ERROR",
                    "message": "Database error while fetching latest live telemetry",
                    "device_id": device_id,
                    "database_error": str(exc.orig)
                    if hasattr(exc, "orig")
                    else str(exc),
                },
            )
            
    def get_latest(
        self,
        db: Session,
        device_id: str,
    ) -> Optional[MotorTelemetry]:
        """
        Return newest telemetry record for Home/Telemetry screen.

        This includes both:
        - is_live = 1 motor ON packets
        - is_live = 0 motor OFF packets
        """
        try:
            telemetry = (
                db.query(MotorTelemetry)
                .filter(MotorTelemetry.device_id == device_id)
                .order_by(
                    MotorTelemetry.created_at.desc(),
                    MotorTelemetry.is_live.desc(),
                    MotorTelemetry.timestamp.desc(),
                    MotorTelemetry.id.desc(),
                )
                .first()
            )
            
            

            return telemetry

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
                    "device_id": device_id,
                    "database_error": str(exc.orig)
                    if hasattr(exc, "orig")
                    else str(exc),
                },
            )

    def delete(self, db: Session, telemetry_id: str) -> MotorTelemetry:
        """
        Delete telemetry by telemetry ID.

        Args:
            db: Active SQLAlchemy database session.
            telemetry_id: Telemetry UUID as string.

        Returns:
            Deleted MotorTelemetry row.

        Raises:
            NotFoundException: If telemetry row does not exist.
            AppException: If database delete fails.
        """
        try:
            telemetry = (
                db.query(MotorTelemetry)
                .filter(MotorTelemetry.id == telemetry_id)
                .first()
            )

            if not telemetry:
                logger.warning(
                    "Telemetry delete failed. Record not found: telemetry_id=%s",
                    telemetry_id,
                )
                raise NotFoundException(detail="Telemetry not found")

            db.delete(telemetry)
            db.flush()

            logger.info(
                "Telemetry deleted from session: id=%s device_id=%s timestamp=%s",
                telemetry.id,
                telemetry.device_id,
                telemetry.timestamp,
            )

            return telemetry

        except NotFoundException:
            raise

        except SQLAlchemyError as exc:
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
                    "telemetry_id": telemetry_id,
                    "database_error": str(exc.orig)
                    if hasattr(exc, "orig")
                    else str(exc),
                },
            )