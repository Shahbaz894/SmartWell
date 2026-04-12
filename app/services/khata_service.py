# app/services/khata_service.py

from app.models.device import Device
from app.models.motor_log import MotorLog
from app.repositories.khata_repo import KhataRepository
from app.models.khata_entry import KhataEntry
from app.core.logger import logger
from app.core.exceptions import AppException, NotFoundException
from uuid import uuid4
from datetime import datetime


class KhataService:
    def __init__(self, db):
        self.db = db
        self.repo = KhataRepository(db)

    # ─────────────────────────────────────────────
    # CREATE
    # ─────────────────────────────────────────────
    def create_entry(self, user_id: str, data: dict):
        try:
            # Validate device belongs to user
            device = self.db.query(Device).filter_by(
                id=data["device_id"], user_id=user_id
            ).first()

            if not device:
                raise AppException("Invalid device_id or device doesn't belong to you")

            # Customer name required
            if not data.get("customer_name"):
                raise AppException("customer_name is required")

            # Assign customer_id from logged-in user
            data["customer_id"] = str(user_id)

            # Auto date
            if not data.get("date"):
                data["date"] = datetime.now().date()

            # Auto run_hours from motor log
            if not data.get("run_hours") and data.get("motor_log_id"):
                log = self.db.query(MotorLog).filter_by(
                    id=data["motor_log_id"]
                ).first()

                if not log:
                    raise AppException("Invalid motor_log_id: log not found")

                if log.start_time and log.end_time:
                    duration = (log.end_time - log.start_time).total_seconds()
                    data["run_hours"] = round(duration / 3600, 2)
                else:
                    raise AppException("Motor log is incomplete: motor not stopped yet")

            if not data.get("run_hours"):
                raise AppException("run_hours is required (or provide a valid motor_log_id)")

            # Billing calculations
            hours = float(data["run_hours"])
            price = float(data["price_per_hour"])

            if data.get("total_bill") is None:
                data["total_bill"] = round(hours * price, 2)

            cash = float(data.get("cash_received") or 0)

            if cash < 0:
                raise AppException("Cash received cannot be negative")

            if cash > data["total_bill"]:
                raise AppException("Cash received cannot exceed total bill")

            data["cash_received"] = round(cash, 2)
            data["balance"]       = round(data["total_bill"] - cash, 2)
            data["is_cleared"]    = data["balance"] <= 0

            # Build and save entry
            entry = KhataEntry(
                id=str(uuid4()),
                created_at=datetime.now(),
                **data
            )

            return self.repo.create_entry(entry)

        except AppException:
            raise  # re-raise known errors as-is
        except Exception as e:
            logger.error("Create khata entry failed: %s", str(e), exc_info=True)
            raise AppException(f"Unexpected error while creating entry: {str(e)}")

    # ─────────────────────────────────────────────
    # UPDATE PAYMENT  (partial or full payment)
    # ─────────────────────────────────────────────
    def update_payment(self, entry_id: str, cash_received: float):
        """
        Add a payment to an existing entry.
        Entry stays visible after clearing — is_cleared is just a flag.
        """
        try:
            entry = self.repo.get_entry(entry_id)

            if not entry:
                raise NotFoundException(f"Entry not found: {entry_id}")

            if entry.is_cleared:
                raise AppException("Entry is already fully cleared")

            if cash_received <= 0:
                raise AppException("Payment amount must be greater than zero")

            new_cash = round(float(entry.cash_received or 0) + cash_received, 2)

            if new_cash > float(entry.total_bill):
                raise AppException(
                    f"Total cash ({new_cash}) would exceed total bill ({entry.total_bill})"
                )

            entry.cash_received = new_cash
            entry.balance       = round(float(entry.total_bill) - new_cash, 2)
            entry.is_cleared    = entry.balance <= 0   # mark cleared but KEEP entry

            return self.repo.save(entry)

        except (AppException, NotFoundException):
            raise
        except Exception as e:
            logger.error("Update payment failed: %s", str(e), exc_info=True)
            raise AppException(f"Unexpected error while updating payment: {str(e)}")

    # ─────────────────────────────────────────────
    # GET ALL  (for one user)
    # ─────────────────────────────────────────────
    def get_all_entries(self, user_id: str):
        """
        Returns ALL entries — cleared entries remain visible with is_cleared=True.
        """
        try:
            return self.repo.get_all_entries(user_id)
        except Exception as e:
            logger.error("Get all entries failed: %s", str(e), exc_info=True)
            raise AppException(f"Unexpected error while fetching entries: {str(e)}")

    # ─────────────────────────────────────────────
    # GET ONE
    # ─────────────────────────────────────────────
    def get_entry(self, entry_id: str):
        try:
            entry = self.repo.get_entry(entry_id)
            if not entry:
                raise NotFoundException(f"Entry not found: {entry_id}")
            return entry
        except (AppException, NotFoundException):
            raise
        except Exception as e:
            logger.error("Get entry failed: %s", str(e), exc_info=True)
            raise AppException(f"Unexpected error while fetching entry: {str(e)}")

    # ─────────────────────────────────────────────
    # DELETE  (only allowed when fully cleared)
    # ─────────────────────────────────────────────
    def delete_entry(self, entry_id: str):
        """
        Deletion is only allowed after the entry is fully cleared.
        Cleared entries are NOT auto-deleted — explicit DELETE required.
        """
        try:
            entry = self.repo.get_entry(entry_id)

            if not entry:
                raise NotFoundException(f"Entry not found: {entry_id}")

            if not entry.is_cleared:
                raise AppException(
                    f"Cannot delete: balance of {entry.balance} is still pending"
                )

            return self.repo.delete_entry(entry)

        except (AppException, NotFoundException):
            raise
        except Exception as e:
            logger.error("Delete khata entry failed: %s", str(e), exc_info=True)
            raise AppException(f"Unexpected error while deleting entry: {str(e)}")