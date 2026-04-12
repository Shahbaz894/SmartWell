# app/services/khata_service.py
#
# Khata (ledger) service layer.
# Handles all business logic: billing calculations, payment tracking,
# device ownership validation, and entry lifecycle management.
#
# ── Design Notes ──────────────────────────────────────────────────────────────
#  • "customer_id" in KhataEntry refers to the LOGGED-IN USER (tube-well owner).
#    It is always set from `user_id` (JWT claim) — never from request body.
#  • The frontend may send a `customer_id` field; it is explicitly stripped
#    before any DB operation to prevent injection or overwrite attacks.
#  • Cleared entries (is_cleared=True) remain visible; explicit DELETE required.
# ──────────────────────────────────────────────────────────────────────────────

from uuid import uuid4
from datetime import datetime

from app.models.device import Device
from app.models.motor_log import MotorLog
from app.repositories.khata_repo import KhataRepository
from app.models.khata_entry import KhataEntry
from app.core.logger import logger
from app.core.exceptions import AppException, NotFoundException


class KhataService:
    """
    Service layer for Khata (ledger) operations.

    Responsibilities
    ----------------
    - Validate device ownership via user_id (not customer_id).
    - Auto-derive run_hours from a linked MotorLog when not provided manually.
    - Calculate total_bill, balance, and is_cleared flag.
    - Delegate all persistence to KhataRepository.
    """

    def __init__(self, db):
        self.db   = db
        self.repo = KhataRepository(db)

    # ─────────────────────────────────────────────────────────────────────────
    # CREATE
    # ─────────────────────────────────────────────────────────────────────────
    def create_entry(self, user_id: str, data: dict):
        """
        Create a new Khata entry for the authenticated user.

        Parameters
        ----------
        user_id : str
            ID of the authenticated user (tube-well owner), from JWT.
        data : dict
            Validated request body from KhataCreate schema.

        Returns
        -------
        KhataEntry
            The newly created and committed entry.

        Raises
        ------
        AppException
            - Device not found or does not belong to this user.
            - Motor log is missing / still running (no end_time).
            - run_hours could not be determined.
            - Negative or over-limit cash amount.
        """
        try:
            # ── Step 1: Verify device ownership ──────────────────────────────
            # Device.user_id stores the owner; never use customer_id here.
            device = (
                self.db.query(Device)
                .filter(
                    Device.id      == data["device_id"],
                    Device.user_id == user_id            # ← correct field
                )
                .first()
            )
            if not device:
                logger.warning(
                    "Device access denied: device_id=%s, user_id=%s",
                    data.get("device_id"), user_id
                )
                raise AppException("Device not found or access denied")

            # ── Step 2: Default date to today if not supplied ─────────────────
            if not data.get("date"):
                data["date"] = datetime.now().date()

            # ── Step 3: Derive run_hours from MotorLog (if not provided) ──────
            if not data.get("run_hours") and data.get("motor_log_id"):
                log = (
                    self.db.query(MotorLog)
                    .filter(MotorLog.id == data["motor_log_id"])
                    .first()
                )
                if not log:
                    raise AppException(
                        f"Motor log not found: {data['motor_log_id']}"
                    )
                if not (log.start_time and log.end_time):
                    raise AppException(
                        "Motor log is incomplete — motor may still be running"
                    )

                duration_seconds  = (log.end_time - log.start_time).total_seconds()
                data["run_hours"] = round(duration_seconds / 3600, 2)
                logger.debug(
                    "Derived run_hours=%.2f from motor_log_id=%s",
                    data["run_hours"], data["motor_log_id"]
                )

            if not data.get("run_hours"):
                raise AppException(
                    "Could not determine run_hours — "
                    "provide 'run_hours' directly or a valid 'motor_log_id'"
                )

            # ── Step 4: Billing calculations ──────────────────────────────────
            hours = float(data["run_hours"])
            price = float(data["price_per_hour"])

            if data.get("total_bill") is None:
                data["total_bill"] = round(hours * price, 2)

            cash = float(data.get("cash_received") or 0)

            if cash < 0:
                raise AppException("Cash received cannot be negative")

            if cash > data["total_bill"]:
                raise AppException(
                    f"Cash received ({cash}) cannot exceed total bill ({data['total_bill']})"
                )

            data["balance"]    = round(data["total_bill"] - cash, 2)
            data["is_cleared"] = data["balance"] <= 0

            # ── Step 5: Strip fields that must NOT come from the request body ─
            #
            # customer_id  → always set from JWT user_id (see Step 6)
            # created_at   → DB server_default (now())
            # user_id      → not a column; avoid **data leakage into KhataEntry
            #
            for field in ("customer_id", "created_at", "user_id"):
                data.pop(field, None)

            # ── Step 6: Persist ───────────────────────────────────────────────
            entry = KhataEntry(
                id          = str(uuid4()),
                customer_id = user_id,   # always from JWT — never from body
                **data
            )
            created = self.repo.create_entry(entry)
            logger.info(
                "Khata entry created: id=%s, user_id=%s, customer=%s, "
                "total_bill=%s, balance=%s, cleared=%s",
                created.id, user_id, created.customer_name,
                created.total_bill, created.balance, created.is_cleared
            )
            return created

        except AppException:
            raise
        except Exception as exc:
            logger.error("Khata creation failed: %s", exc, exc_info=True)
            raise AppException(f"Unexpected error while creating entry: {exc}")

    # ─────────────────────────────────────────────────────────────────────────
    # UPDATE PAYMENT  (additive — partial or full settlement)
    # ─────────────────────────────────────────────────────────────────────────
    def update_payment(self, entry_id: str, user_id: str, cash_received: float):
        """
        Record an additional payment against an existing entry.

        The entry remains visible after full payment (is_cleared=True).
        Deletion requires a separate explicit DELETE call.

        Parameters
        ----------
        entry_id     : str   UUID of the KhataEntry to update.
        user_id      : str   Authenticated user — used to verify ownership.
        cash_received: float Additional cash amount received (must be > 0).

        Raises
        ------
        NotFoundException  Entry not found.
        AppException       Ownership mismatch, already cleared, bad amount.
        """
        try:
            entry = self.repo.get_entry(entry_id)

            # Ownership check — customer_id on KhataEntry == user_id from JWT
            if entry.customer_id != user_id:
                logger.warning(
                    "Payment update denied: entry_id=%s, user_id=%s, owner=%s",
                    entry_id, user_id, entry.customer_id
                )
                raise AppException("Access denied: this entry does not belong to you")

            if entry.is_cleared:
                raise AppException("Entry is already fully cleared")

            if cash_received <= 0:
                raise AppException("Payment amount must be greater than zero")

            new_total_cash = round(float(entry.cash_received or 0) + cash_received, 2)

            if new_total_cash > float(entry.total_bill):
                raise AppException(
                    f"Total cash ({new_total_cash}) would exceed "
                    f"total bill ({entry.total_bill})"
                )

            entry.cash_received = new_total_cash
            entry.balance       = round(float(entry.total_bill) - new_total_cash, 2)
            entry.is_cleared    = entry.balance <= 0

            saved = self.repo.save(entry)
            logger.info(
                "Payment updated: id=%s, customer=%s, new_cash=%.2f, "
                "balance=%.2f, cleared=%s",
                entry_id, entry.customer_name,
                new_total_cash, entry.balance, entry.is_cleared
            )
            return saved

        except (AppException, NotFoundException):
            raise
        except Exception as exc:
            logger.error("Update payment failed: %s", exc, exc_info=True)
            raise AppException(f"Unexpected error while updating payment: {exc}")

    # ─────────────────────────────────────────────────────────────────────────
    # UPDATE ENTRY  (general field corrections / manual edits)
    # ─────────────────────────────────────────────────────────────────────────
    def update_entry(self, entry_id: str, user_id: str, data: dict):
        """
        Update editable fields on a Khata entry.

        Recalculates balance and is_cleared after any change.
        Ownership is verified before any mutation.

        Parameters
        ----------
        entry_id : str   UUID of the entry.
        user_id  : str   Authenticated user — must match entry.customer_id.
        data     : dict  Fields to update (from KhataUpdate schema).
        """
        try:
            entry = self.repo.get_entry(entry_id)

            if entry.customer_id != user_id:
                logger.warning(
                    "Update denied: entry_id=%s, user_id=%s, owner=%s",
                    entry_id, user_id, entry.customer_id
                )
                raise AppException("Access denied: this entry does not belong to you")

            updated = self.repo.update_entry(entry, data)
            logger.info(
                "Entry updated: id=%s, customer=%s, balance=%.2f, cleared=%s",
                entry_id, updated.customer_name, updated.balance, updated.is_cleared
            )
            return updated

        except (AppException, NotFoundException):
            raise
        except Exception as exc:
            logger.error("Update entry failed: %s", exc, exc_info=True)
            raise AppException(f"Unexpected error while updating entry: {exc}")

    # ─────────────────────────────────────────────────────────────────────────
    # GET ALL  (for one user — cleared entries remain visible)
    # ─────────────────────────────────────────────────────────────────────────
    def get_all_entries(self, user_id: str):
        """
        Return every Khata entry belonging to the authenticated user.

        Cleared entries (is_cleared=True) are included; the caller can
        filter on the frontend if needed.
        """
        try:
            entries = self.repo.get_all_entries(user_id)
            logger.debug(
                "Fetched %d entries for user_id=%s", len(entries), user_id
            )
            return entries
        except Exception as exc:
            logger.error("Get all entries failed: %s", exc, exc_info=True)
            raise AppException(f"Unexpected error while fetching entries: {exc}")

    # ─────────────────────────────────────────────────────────────────────────
    # GET ONE
    # ─────────────────────────────────────────────────────────────────────────
    def get_entry(self, entry_id: str, user_id: str):
        """
        Fetch a single entry, verifying it belongs to the requesting user.
        """
        try:
            entry = self.repo.get_entry(entry_id)
            if entry.customer_id != user_id:
                raise AppException("Access denied: this entry does not belong to you")
            return entry
        except (AppException, NotFoundException):
            raise
        except Exception as exc:
            logger.error("Get entry failed: %s", exc, exc_info=True)
            raise AppException(f"Unexpected error while fetching entry: {exc}")

    # ─────────────────────────────────────────────────────────────────────────
    # DELETE  (only allowed once fully cleared; hard delete)
    # ─────────────────────────────────────────────────────────────────────────
    def delete_entry(self, entry_id: str, user_id: str):
        """
        Permanently delete a Khata entry.

        Rules
        -----
        - Ownership is verified: entry.customer_id must equal user_id.
        - Deletion is only permitted after the balance is fully cleared
          (is_cleared=True). Entries with a pending balance cannot be removed.

        Returns
        -------
        bool  True on successful deletion.
        """
        try:
            entry = self.repo.get_entry(entry_id)

            if entry.customer_id != user_id:
                logger.warning(
                    "Delete denied: entry_id=%s, user_id=%s, owner=%s",
                    entry_id, user_id, entry.customer_id
                )
                raise AppException("Access denied: this entry does not belong to you")

            if not entry.is_cleared:
                raise AppException(
                    f"Cannot delete: balance of {entry.balance} PKR is still pending. "
                    "Clear the balance first."
                )

            result = self.repo.delete_entry(entry)
            logger.info(
                "Entry deleted: id=%s, customer=%s, user_id=%s",
                entry_id, entry.customer_name, user_id
            )
            return result

        except (AppException, NotFoundException):
            raise
        except Exception as exc:
            logger.error("Delete entry failed: %s", exc, exc_info=True)
            raise AppException(f"Unexpected error while deleting entry: {exc}")