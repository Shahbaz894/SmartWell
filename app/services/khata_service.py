# app/services/khata_service.py
#
# Business-logic layer for Khata (ledger) entries.
#
# Responsibilities
# ────────────────
# • Orchestrates device/motor-log validation, billing calculations,
#   payment logic, and computed response fields.
# • Converts all Decimal values returned by PostgreSQL/SQLAlchemy Numeric
#   columns to float before arithmetic — this prevents silent type errors.
# • Never exposes raw DB exceptions to the caller; re-raises as AppException.
# • NotFoundException from the repo is always converted to AppException(404).

from decimal import Decimal
from uuid import uuid4
from datetime import datetime

from app.models.device import Device
from app.models.motor_log import MotorLog
from app.repositories.khata_repo import KhataRepository
from app.models.khata_entry import KhataEntry
from app.core.logger import logger
from app.core.exceptions import AppException, NotFoundException


def _to_float(value) -> float:
    """
    Safely convert Decimal, int, float, or None → float.

    SQLAlchemy Numeric columns return decimal.Decimal objects.
    Mixing Decimal with float causes TypeError in arithmetic.
    This helper centralises the conversion.

    Args:
        value: Any numeric-ish value or None.

    Returns:
        float: Converted value, or 0.0 if value is None/falsy.
    """
    if value is None:
        return 0.0
    return float(value)


class KhataService:
    """
    Service layer for all Khata (ledger) business operations.

    Args:
        db: SQLAlchemy Session injected by FastAPI dependency system.
    """

    def __init__(self, db):
        self.db = db
        self.repo = KhataRepository(db)

    # ─────────────────────────────────────────────────────────────────────────
    # PRIVATE HELPERS
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _compute_payment_status(balance: float, cash: float) -> str:
        """
        Derive human-readable payment status from balance and cash received.

        Rules:
            balance <= 0          → "paid"
            balance > 0, cash > 0 → "partial"
            balance > 0, cash = 0 → "unpaid"

        Args:
            balance (float): Remaining amount owed.
            cash    (float): Total cash received so far.

        Returns:
            str: One of "paid" | "partial" | "unpaid".
        """
        if balance <= 0:
            return "paid"
        if cash > 0:
            return "partial"
        return "unpaid"

    @staticmethod
    def _attach_computed_fields(entry: KhataEntry) -> KhataEntry:
        """
        Attach non-persisted computed fields to an ORM entry before returning.

        These fields exist on KhataResponse but are NOT stored in the DB:
            • remaining_balance  — mirrors the DB balance column
            • payment_status     — derived from balance + cash_received

        Attaching them as instance attributes works because Pydantic's
        from_attributes=True reads from __dict__, not from DB columns only.

        Args:
            entry (KhataEntry): ORM object fresh from a DB query.

        Returns:
            KhataEntry: Same object, mutated in place (fluent helper).
        """
        balance = _to_float(entry.balance)
        cash    = _to_float(entry.cash_received)

        entry.remaining_balance = balance
        entry.payment_status    = KhataService._compute_payment_status(
            balance, cash
        )
        return entry

    # ─────────────────────────────────────────────────────────────────────────
    # CREATE ENTRY
    # ─────────────────────────────────────────────────────────────────────────

    def create_entry(self, user_id: str, data: dict) -> KhataEntry:
        """
        Validate inputs, compute billing fields, and persist a new KhataEntry.

        Validation steps (in order):
            1. Device must exist and belong to the authenticated user.
            2. If motor_log_id supplied → derive run_hours from log timestamps.
            3. run_hours must be present (either manual or from motor log).
            4. Compute total_bill = run_hours × price_per_hour.
            5. Validate cash_received ≥ 0.
            6. Compute balance and is_cleared.

        Args:
            user_id (str): UUID of the authenticated user (from JWT).
            data    (dict): Deserialised request body from KhataCreate schema.

        Returns:
            KhataEntry: Persisted entry with computed fields attached.

        Raises:
            AppException: 400 on validation failure, 500 on DB error.
        """
        logger.info(
            "create_entry called | user_id=%s customer=%s",
            user_id,
            data.get("customer_name"),
        )

        # ── 1. Device ownership check ─────────────────────────────────────────
        device = (
            self.db.query(Device)
            .filter(
                Device.id      == data["device_id"],
                Device.user_id == user_id,
            )
            .first()
        )
        if not device:
            raise AppException(400, "Device not found or does not belong to you")

        # ── 2. Default date ───────────────────────────────────────────────────
        if not data.get("date"):
            data["date"] = datetime.now().date()

        # ── 3. Motor log → run_hours ──────────────────────────────────────────
        if data.get("motor_log_id"):
            log = (
                self.db.query(MotorLog)
                .filter(MotorLog.id == data["motor_log_id"])
                .first()
            )
            if not log:
                raise AppException(400, "Motor log not found")

            if not log.start_time or not log.end_time:
                raise AppException(
                    400,
                    "Motor log is incomplete — motor may still be running",
                )

            run_seconds      = (log.end_time - log.start_time).total_seconds()
            data["run_hours"] = round(run_seconds / 3600, 2)

            logger.debug(
                "run_hours derived from motor_log | log_id=%s run_hours=%s",
                data["motor_log_id"],
                data["run_hours"],
            )

        # ── 4. run_hours guard ────────────────────────────────────────────────
        if not data.get("run_hours"):
            raise AppException(
                400,
                "run_hours is required — supply it directly or via motor_log_id",
            )

        # ── 5. Billing calculation ────────────────────────────────────────────
        run_hours      = round(_to_float(data["run_hours"]),      2)
        price_per_hour = round(_to_float(data["price_per_hour"]), 2)
        total_bill     = round(run_hours * price_per_hour,         2)

        # ── 6. Payment logic ──────────────────────────────────────────────────
        cash = round(_to_float(data.get("cash_received")), 2)
        if cash < 0:
            raise AppException(400, "cash_received cannot be negative")

        balance    = round(total_bill - cash, 2)
        is_cleared = balance <= 0

        # ── 7. Merge computed values back into data dict ──────────────────────
        data.update(
            run_hours      = run_hours,
            price_per_hour = price_per_hour,
            total_bill     = total_bill,
            cash_received  = cash,
            balance        = balance,
            is_cleared     = is_cleared,
        )

        # ── 8. Strip fields that must not reach the ORM constructor ───────────
        for field in ("remaining_balance", "payment_status", "user_id"):
            data.pop(field, None)

        # ── 9. Build and persist ORM object ───────────────────────────────────
        entry = KhataEntry(
            id      = str(uuid4()),
            user_id = user_id,
            **data,
        )

        created = self.repo.create_entry(entry)

        logger.info(
            "KhataEntry created successfully | id=%s total_bill=%s balance=%s",
            created.id,
            created.total_bill,
            created.balance,
        )

        return self._attach_computed_fields(created)

    # ─────────────────────────────────────────────────────────────────────────
    # GET ALL ENTRIES
    # ─────────────────────────────────────────────────────────────────────────

    def get_all_entries(self, user_id: str) -> list[KhataEntry]:
        """
        Fetch every KhataEntry owned by the authenticated user.

        Args:
            user_id (str): UUID of the authenticated user.

        Returns:
            list[KhataEntry]: Entries ordered newest first (may be empty).

        Raises:
            AppException: 500 on unexpected failure.
        """
        try:
            entries = self.repo.get_all_entries(user_id)

            for entry in entries:
                self._attach_computed_fields(entry)

            logger.info(
                "get_all_entries | user_id=%s count=%d",
                user_id,
                len(entries),
            )
            return entries

        except AppException:
            raise   # already formatted — let it propagate

        except Exception as exc:
            logger.error(
                "get_all_entries unexpected error | user_id=%s error=%s",
                user_id,
                repr(exc),
                exc_info=True,
            )
            raise AppException(500, "Failed to fetch entries")

    # ─────────────────────────────────────────────────────────────────────────
    # GET ONE ENTRY
    # ─────────────────────────────────────────────────────────────────────────

    def get_entry(self, entry_id: str, user_id: str) -> KhataEntry:
        """
        Fetch a single KhataEntry, enforcing user ownership.

        Args:
            entry_id (str): UUID of the entry to fetch.
            user_id  (str): UUID of the authenticated user.

        Returns:
            KhataEntry: The matched entry with computed fields.

        Raises:
            AppException: 404 if not found, 500 on unexpected failure.
        """
        try:
            entry = self.repo.get_entry(
                entry_id = entry_id,
                user_id  = user_id,
            )
            logger.info(
                "get_entry | entry_id=%s user_id=%s",
                entry_id,
                user_id,
            )
            return self._attach_computed_fields(entry)

        except NotFoundException:
            raise AppException(404, "Khata entry not found")

        except AppException:
            raise   # 500 from repo — let it propagate as-is

        except Exception as exc:
            logger.error(
                "get_entry unexpected error | entry_id=%s error=%s",
                entry_id,
                repr(exc),
                exc_info=True,
            )
            raise AppException(500, "Failed to fetch entry")

    # ─────────────────────────────────────────────────────────────────────────
    # UPDATE ENTRY  (field corrections)
    # ─────────────────────────────────────────────────────────────────────────

    def update_entry(
        self,
        entry_id: str,
        user_id:  str,
        data:     dict,
    ) -> KhataEntry:
        """
        Apply partial field corrections to an existing KhataEntry.

        After updating, balance and is_cleared are automatically recalculated
        from the final total_bill and cash_received values.

        Args:
            entry_id (str):  UUID of the entry to update.
            user_id  (str):  UUID of the authenticated user.
            data     (dict): Non-None fields to overwrite (from KhataUpdate).

        Returns:
            KhataEntry: Updated entry with computed fields.

        Raises:
            AppException: 404 if not found, 400/500 on other errors.
        """
        try:
            entry = self.repo.get_entry(
                entry_id = entry_id,
                user_id  = user_id,
            )

            # Merge updates, then recalculate derived billing fields.
            updated = self.repo.update_entry(entry, data)

            # ── Recalculate balance from final persisted values ────────────────
            total_bill    = _to_float(updated.total_bill)
            cash_received = _to_float(updated.cash_received)
            new_balance   = round(total_bill - cash_received, 2)

            updated = self.repo.update_entry(updated, {
                "balance":    new_balance,
                "is_cleared": new_balance <= 0,
            })

            logger.info(
                "KhataEntry updated | id=%s new_balance=%s",
                updated.id,
                new_balance,
            )
            return self._attach_computed_fields(updated)

        except NotFoundException:
            raise AppException(404, "Khata entry not found")

        except AppException:
            raise

        except Exception as exc:
            logger.error(
                "update_entry unexpected error | entry_id=%s error=%s",
                entry_id,
                repr(exc),
                exc_info=True,
            )
            raise AppException(500, "Failed to update entry")

    # ─────────────────────────────────────────────────────────────────────────
    # RECORD PAYMENT  (additive)
    # ─────────────────────────────────────────────────────────────────────────

    def update_payment(
        self,
        entry_id:      str,
        user_id:       str,
        cash_received: float,
    ) -> KhataEntry:
        """
        Add an incremental payment to an existing KhataEntry.

        The supplied cash_received is ADDED to the existing total, not
        replacing it. Once balance reaches zero, is_cleared is set True.

        Args:
            entry_id      (str):   UUID of the entry.
            user_id       (str):   UUID of the authenticated user.
            cash_received (float): New payment amount (must be > 0).

        Returns:
            KhataEntry: Updated entry with computed fields.

        Raises:
            AppException: 400 if already cleared, 404 if not found,
                          500 on unexpected failure.
        """
        try:
            entry = self.repo.get_entry(
                entry_id = entry_id,
                user_id  = user_id,
            )

            if entry.is_cleared:
                raise AppException(400, "Entry is already fully cleared")

            # Accumulate cash and recalculate
            new_cash    = round(_to_float(entry.cash_received) + _to_float(cash_received), 2)
            total_bill  = _to_float(entry.total_bill)
            new_balance = round(total_bill - new_cash, 2)

            updated = self.repo.update_entry(entry, {
                "cash_received": new_cash,
                "balance":       new_balance,
                "is_cleared":    new_balance <= 0,
            })

            logger.info(
                "Payment recorded | id=%s added=%s new_balance=%s cleared=%s",
                updated.id,
                cash_received,
                new_balance,
                updated.is_cleared,
            )
            return self._attach_computed_fields(updated)

        except NotFoundException:
            raise AppException(404, "Khata entry not found")

        except AppException:
            raise

        except Exception as exc:
            logger.error(
                "update_payment unexpected error | entry_id=%s error=%s",
                entry_id,
                repr(exc),
                exc_info=True,
            )
            raise AppException(500, "Failed to record payment")

    # ─────────────────────────────────────────────────────────────────────────
    # DELETE ENTRY
    # ─────────────────────────────────────────────────────────────────────────

    def delete_entry(self, entry_id: str, user_id: str) -> bool:
        """
        Hard-delete a KhataEntry — only permitted when fully cleared.

        Args:
            entry_id (str): UUID of the entry to delete.
            user_id  (str): UUID of the authenticated user.

        Returns:
            bool: True on success.

        Raises:
            AppException: 400 if not cleared, 404 if not found,
                          500 on unexpected failure.
        """
        try:
            entry = self.repo.get_entry(
                entry_id = entry_id,
                user_id  = user_id,
            )

            if not entry.is_cleared:
                raise AppException(
                    400,
                    "Cannot delete an entry with an outstanding balance — "
                    "record full payment first via /payment endpoint",
                )

            result = self.repo.delete_entry(entry)

            logger.info(
                "KhataEntry deleted | id=%s user_id=%s",
                entry_id,
                user_id,
            )
            return result

        except NotFoundException:
            raise AppException(404, "Khata entry not found")

        except AppException:
            raise

        except Exception as exc:
            logger.error(
                "delete_entry unexpected error | entry_id=%s error=%s",
                entry_id,
                repr(exc),
                exc_info=True,
            )
            raise AppException(500, "Failed to delete entry")