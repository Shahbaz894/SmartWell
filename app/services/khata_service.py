from uuid import uuid4
from datetime import datetime

from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from app.models.device import Device
from app.models.motor_log import MotorLog
from app.repositories.khata_repo import KhataRepository
from app.models.khata_entry import KhataEntry
from app.core.logger import logger
from app.core.exceptions import AppException, NotFoundException


def _db_error(exc: Exception) -> str:
    """
    Return the real database error message.

    SQLAlchemy wraps PostgreSQL errors.
    exc.orig usually contains the actual PostgreSQL error.
    """
    return str(exc.orig) if hasattr(exc, "orig") else str(exc)


def _to_float(value) -> float:
    """
    Convert Decimal, int, float, string number, or None to float.

    PostgreSQL Numeric columns often return Decimal.
    This avoids Decimal and float arithmetic errors.
    """
    if value is None:
        return 0.0

    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        logger.error(
            "Numeric conversion failed: value=%s error_type=%s error=%s",
            value,
            type(exc).__name__,
            str(exc),
            exc_info=True,
        )
        raise AppException(
            status_code=400,
            detail=f"Invalid numeric value '{value}'",
        )


class KhataService:
    """
    Service layer for Khata ledger entries.

    MQTT note:
    - This service does not publish or subscribe MQTT.
    - ESP32 sends telemetry by MQTT.
    - Motor start and stop commands use MQTT through MotorService.
    - Khata uses saved PostgreSQL data such as Device and MotorLog.

    Responsibilities:
    - Validate device ownership.
    - Calculate bill from run hours and price per hour.
    - Create ledger entries.
    - Update ledger entries.
    - Record partial or full payments.
    - Delete only fully cleared entries.
    """

    def __init__(self, db):
        self.db = db
        self.repo = KhataRepository(db)

    @staticmethod
    def _compute_payment_status(balance: float, cash: float) -> str:
        """
        Compute payment status from balance and cash received.

        Returns:
            paid, partial, or unpaid
        """
        if balance <= 0:
            return "paid"
        if cash > 0:
            return "partial"
        return "unpaid"

    @staticmethod
    def _attach_computed_fields(entry: KhataEntry) -> KhataEntry:
        """
        Attach response-only fields to an ORM object.

        These fields are not stored as database columns:
        - remaining_balance
        - payment_status
        """
        balance = _to_float(entry.balance)
        cash = _to_float(entry.cash_received)

        entry.remaining_balance = balance
        entry.payment_status = KhataService._compute_payment_status(balance, cash)

        return entry

    def _get_owned_device(self, user_id: str, device_id: str) -> Device:
        """
        Get a device owned by the user.

        Accepts both:
        - device_uid, for example ESP32_001_TW
        - internal UUID devices.id

        Returns:
            Device ORM object.

        Raises:
            AppException if device does not exist or does not belong to user.
        """
        device = (
            self.db.query(Device)
            .filter(Device.device_uid == device_id, Device.user_id == user_id)
            .first()
        )

        if not device:
            device = (
                self.db.query(Device)
                .filter(Device.id == device_id, Device.user_id == user_id)
                .first()
            )

        if not device:
            logger.warning(
                "Khata device lookup denied. Device not found or not owned: user_id=%s device_id=%s",
                user_id,
                device_id,
            )
            raise AppException(
                status_code=404,
                detail="Device not found or does not belong to you",
            )

        return device

    def create_entry(self, user_id: str, data: dict) -> KhataEntry:
        """
        Create a Khata ledger entry.

        Expected data:
        - device_id
        - customer_name
        - run_hours or motor_log_id
        - price_per_hour
        - cash_received

        If motor_log_id is provided, run_hours is calculated from motor log.
        """
        try:
            logger.info(
                "Khata create requested: user_id=%s customer=%s device_id=%s motor_log_id=%s",
                user_id,
                data.get("customer_name"),
                data.get("device_id"),
                data.get("motor_log_id"),
            )

            device_id = data.get("device_id")
            if not device_id:
                raise AppException(
                    status_code=400,
                    detail="device_id is required",
                )

            device = self._get_owned_device(user_id=user_id, device_id=device_id)

            db_device_id = str(device.id)
            data["device_id"] = db_device_id

            if not data.get("date"):
                data["date"] = datetime.now().date()

            if data.get("motor_log_id"):
                log = (
                    self.db.query(MotorLog)
                    .filter(
                        MotorLog.id == data["motor_log_id"],
                        MotorLog.device_id == db_device_id,
                    )
                    .first()
                )

                if not log:
                    raise AppException(
                        status_code=404,
                        detail="Motor log not found for this device",
                    )

                if not log.start_time or not log.end_time:
                    raise AppException(
                        status_code=400,
                        detail="Motor log is incomplete. Motor may still be running.",
                    )

                run_seconds = (log.end_time - log.start_time).total_seconds()
                data["run_hours"] = round(run_seconds / 3600, 2)

                logger.info(
                    "Khata run_hours calculated from motor log: motor_log_id=%s run_hours=%s",
                    data["motor_log_id"],
                    data["run_hours"],
                )

            if not data.get("run_hours"):
                raise AppException(
                    status_code=400,
                    detail="run_hours is required. Supply it directly or provide motor_log_id.",
                )

            if data.get("price_per_hour") is None:
                raise AppException(
                    status_code=400,
                    detail="price_per_hour is required",
                )

            run_hours = round(_to_float(data["run_hours"]), 2)
            price_per_hour = round(_to_float(data["price_per_hour"]), 2)
            cash_received = round(_to_float(data.get("cash_received")), 2)

            if run_hours <= 0:
                raise AppException(
                    status_code=400,
                    detail="run_hours must be greater than 0",
                )

            if price_per_hour < 0:
                raise AppException(
                    status_code=400,
                    detail="price_per_hour cannot be negative",
                )

            if cash_received < 0:
                raise AppException(
                    status_code=400,
                    detail="cash_received cannot be negative",
                )

            total_bill = round(run_hours * price_per_hour, 2)
            balance = round(total_bill - cash_received, 2)

            data.update(
                run_hours=run_hours,
                price_per_hour=price_per_hour,
                total_bill=total_bill,
                cash_received=cash_received,
                balance=balance,
                is_cleared=balance <= 0,
            )

            for field in ("remaining_balance", "payment_status", "user_id"):
                data.pop(field, None)

            entry = KhataEntry(
                id=str(uuid4()),
                user_id=user_id,
                **data,
            )

            created = self.repo.create_entry(entry)

            logger.info(
                "Khata entry created: id=%s user_id=%s device_id=%s device_uid=%s total_bill=%s cash=%s balance=%s",
                created.id,
                user_id,
                db_device_id,
                device.device_uid,
                created.total_bill,
                created.cash_received,
                created.balance,
            )

            return self._attach_computed_fields(created)

        except AppException:
            raise

        except IntegrityError as exc:
            logger.error(
                "Khata create integrity error: user_id=%s data=%s db_error=%s",
                user_id,
                data,
                _db_error(exc),
                exc_info=True,
            )
            raise AppException(
                status_code=400,
                detail=f"Khata create failed. Check device_id, motor_log_id, and required fields. DB error: {_db_error(exc)}",
            )

        except SQLAlchemyError as exc:
            logger.error(
                "Khata create database error: user_id=%s data=%s db_error=%s",
                user_id,
                data,
                _db_error(exc),
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=f"Database error while creating Khata entry: {_db_error(exc)}",
            )

        except Exception as exc:
            logger.error(
                "Khata create unexpected error: user_id=%s error_type=%s error=%s data=%s",
                user_id,
                type(exc).__name__,
                str(exc),
                data,
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=f"Unexpected error while creating Khata entry: {type(exc).__name__}: {str(exc)}",
            )

    def get_all_entries(self, user_id: str) -> list[KhataEntry]:
        """
        Return all Khata entries owned by one user.
        """
        try:
            entries = self.repo.get_all_entries(user_id)

            for entry in entries:
                self._attach_computed_fields(entry)

            logger.info(
                "Khata entries fetched: user_id=%s count=%s",
                user_id,
                len(entries),
            )

            return entries

        except AppException:
            raise

        except SQLAlchemyError as exc:
            logger.error(
                "Khata fetch all database error: user_id=%s db_error=%s",
                user_id,
                _db_error(exc),
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=f"Database error while fetching Khata entries: {_db_error(exc)}",
            )

        except Exception as exc:
            logger.error(
                "Khata fetch all unexpected error: user_id=%s error_type=%s error=%s",
                user_id,
                type(exc).__name__,
                str(exc),
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=f"Unexpected error while fetching Khata entries: {type(exc).__name__}: {str(exc)}",
            )

    def get_entry(self, entry_id: str, user_id: str) -> KhataEntry:
        """
        Return one Khata entry and enforce user ownership.
        """
        try:
            entry = self.repo.get_entry(entry_id=entry_id, user_id=user_id)

            logger.info(
                "Khata entry fetched: entry_id=%s user_id=%s",
                entry_id,
                user_id,
            )

            return self._attach_computed_fields(entry)

        except NotFoundException:
            logger.warning(
                "Khata entry not found: entry_id=%s user_id=%s",
                entry_id,
                user_id,
            )
            raise AppException(
                status_code=404,
                detail="Khata entry not found",
            )

        except AppException:
            raise

        except SQLAlchemyError as exc:
            logger.error(
                "Khata get database error: entry_id=%s user_id=%s db_error=%s",
                entry_id,
                user_id,
                _db_error(exc),
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=f"Database error while fetching Khata entry: {_db_error(exc)}",
            )

        except Exception as exc:
            logger.error(
                "Khata get unexpected error: entry_id=%s user_id=%s error_type=%s error=%s",
                entry_id,
                user_id,
                type(exc).__name__,
                str(exc),
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=f"Unexpected error while fetching Khata entry: {type(exc).__name__}: {str(exc)}",
            )

    def update_entry(self, entry_id: str, user_id: str, data: dict) -> KhataEntry:
        """
        Update editable Khata fields.

        After update, balance and is_cleared are recalculated.
        """
        try:
            logger.info(
                "Khata update requested: entry_id=%s user_id=%s data=%s",
                entry_id,
                user_id,
                data,
            )

            entry = self.repo.get_entry(entry_id=entry_id, user_id=user_id)

            clean_data = {
                key: value for key, value in data.items()
                if value is not None
            }

            if "device_id" in clean_data:
                device = self._get_owned_device(
                    user_id=user_id,
                    device_id=clean_data["device_id"],
                )
                clean_data["device_id"] = str(device.id)

            if "run_hours" in clean_data:
                clean_data["run_hours"] = round(_to_float(clean_data["run_hours"]), 2)
                if clean_data["run_hours"] <= 0:
                    raise AppException(
                        status_code=400,
                        detail="run_hours must be greater than 0",
                    )

            if "price_per_hour" in clean_data:
                clean_data["price_per_hour"] = round(_to_float(clean_data["price_per_hour"]), 2)
                if clean_data["price_per_hour"] < 0:
                    raise AppException(
                        status_code=400,
                        detail="price_per_hour cannot be negative",
                    )

            if "cash_received" in clean_data:
                clean_data["cash_received"] = round(_to_float(clean_data["cash_received"]), 2)
                if clean_data["cash_received"] < 0:
                    raise AppException(
                        status_code=400,
                        detail="cash_received cannot be negative",
                    )

            updated = self.repo.update_entry(entry, clean_data)

            run_hours = _to_float(updated.run_hours)
            price_per_hour = _to_float(updated.price_per_hour)
            cash_received = _to_float(updated.cash_received)

            total_bill = round(run_hours * price_per_hour, 2)
            balance = round(total_bill - cash_received, 2)

            updated = self.repo.update_entry(
                updated,
                {
                    "total_bill": total_bill,
                    "balance": balance,
                    "is_cleared": balance <= 0,
                },
            )

            logger.info(
                "Khata entry updated: entry_id=%s total_bill=%s balance=%s cleared=%s",
                updated.id,
                updated.total_bill,
                updated.balance,
                updated.is_cleared,
            )

            return self._attach_computed_fields(updated)

        except NotFoundException:
            raise AppException(
                status_code=404,
                detail="Khata entry not found",
            )

        except AppException:
            raise

        except SQLAlchemyError as exc:
            logger.error(
                "Khata update database error: entry_id=%s user_id=%s db_error=%s",
                entry_id,
                user_id,
                _db_error(exc),
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=f"Database error while updating Khata entry: {_db_error(exc)}",
            )

        except Exception as exc:
            logger.error(
                "Khata update unexpected error: entry_id=%s user_id=%s error_type=%s error=%s",
                entry_id,
                user_id,
                type(exc).__name__,
                str(exc),
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=f"Unexpected error while updating Khata entry: {type(exc).__name__}: {str(exc)}",
            )

    def update_payment(
        self,
        entry_id: str,
        user_id: str,
        cash_received: float,
    ) -> KhataEntry:
        """
        Add a payment to an existing Khata entry.

        cash_received is added to the old value.
        It does not replace the old value.
        """
        try:
            if cash_received <= 0:
                raise AppException(
                    status_code=400,
                    detail="cash_received must be greater than 0",
                )

            entry = self.repo.get_entry(entry_id=entry_id, user_id=user_id)

            if entry.is_cleared:
                raise AppException(
                    status_code=400,
                    detail="Entry is already fully cleared",
                )

            new_cash = round(_to_float(entry.cash_received) + _to_float(cash_received), 2)
            total_bill = _to_float(entry.total_bill)
            new_balance = round(total_bill - new_cash, 2)

            updated = self.repo.update_entry(
                entry,
                {
                    "cash_received": new_cash,
                    "balance": new_balance,
                    "is_cleared": new_balance <= 0,
                },
            )

            logger.info(
                "Khata payment recorded: entry_id=%s added=%s total_cash=%s balance=%s cleared=%s",
                updated.id,
                cash_received,
                updated.cash_received,
                updated.balance,
                updated.is_cleared,
            )

            return self._attach_computed_fields(updated)

        except NotFoundException:
            raise AppException(
                status_code=404,
                detail="Khata entry not found",
            )

        except AppException:
            raise

        except SQLAlchemyError as exc:
            logger.error(
                "Khata payment database error: entry_id=%s user_id=%s db_error=%s",
                entry_id,
                user_id,
                _db_error(exc),
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=f"Database error while recording payment: {_db_error(exc)}",
            )

        except Exception as exc:
            logger.error(
                "Khata payment unexpected error: entry_id=%s user_id=%s error_type=%s error=%s",
                entry_id,
                user_id,
                type(exc).__name__,
                str(exc),
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=f"Unexpected error while recording payment: {type(exc).__name__}: {str(exc)}",
            )

    def delete_entry(self, entry_id: str, user_id: str) -> bool:
        """
        Delete a Khata entry.

        Rule:
        Only fully paid entries can be deleted.
        """
        try:
            entry = self.repo.get_entry(entry_id=entry_id, user_id=user_id)

            if not entry.is_cleared:
                raise AppException(
                    status_code=400,
                    detail="Cannot delete entry with outstanding balance. Record full payment first.",
                )

            result = self.repo.delete_entry(entry)

            logger.info(
                "Khata entry deleted: entry_id=%s user_id=%s",
                entry_id,
                user_id,
            )

            return result

        except NotFoundException:
            raise AppException(
                status_code=404,
                detail="Khata entry not found",
            )

        except AppException:
            raise

        except SQLAlchemyError as exc:
            logger.error(
                "Khata delete database error: entry_id=%s user_id=%s db_error=%s",
                entry_id,
                user_id,
                _db_error(exc),
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=f"Database error while deleting Khata entry: {_db_error(exc)}",
            )

        except Exception as exc:
            logger.error(
                "Khata delete unexpected error: entry_id=%s user_id=%s error_type=%s error=%s",
                entry_id,
                user_id,
                type(exc).__name__,
                str(exc),
                exc_info=True,
            )
            raise AppException(
                status_code=500,
                detail=f"Unexpected error while deleting Khata entry: {type(exc).__name__}: {str(exc)}",
            )