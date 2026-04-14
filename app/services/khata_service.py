# app/services/khata_service.py
#
# Khata (ledger) service layer.
# Handles all business logic: billing calculations, payment tracking,
# device ownership validation, and entry lifecycle management.
#
# ── Design Notes ──────────────────────────────────────────────────────────────
#  • "user_id" in KhataEntry refers to the LOGGED-IN USER (tube-well owner).
#    It is always set from `user_id` (JWT claim) — never from the request body.
#  • The frontend may send a `customer_id` field; it is explicitly stripped
#    before any DB operation to prevent injection or overwrite attacks.
#  • Cleared entries (is_cleared=True) remain visible; explicit DELETE required.
#  • motor_log_id FK existence is validated BEFORE the INSERT so the DB never
#    raises a raw IntegrityError that would surface as an opaque 500.
#
# ── AppException Usage ────────────────────────────────────────────────────────
#  AppException(status_code: int, detail: str)
#  ALWAYS pass status_code as a keyword arg to avoid passing a string where
#  an int is expected (which itself raises a TypeError → 500).
#
#  Convention used throughout this file:
#    400  Bad request / validation failure
#    403  Ownership / access denied
#    404  Resource not found  (NotFoundException preferred)
#    500  Unexpected / unhandled error
# ──────────────────────────────────────────────────────────────────────────────

from uuid import uuid4
from datetime import datetime

import sqlalchemy.exc

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
    - Validate device ownership via user_id (JWT claim — never request body).
    - Validate motor_log_id FK existence *before* INSERT to surface a clean
      400 Bad Request instead of a raw DB IntegrityError → 500.
    - Auto-derive run_hours from a linked MotorLog when not provided manually.
    - Calculate total_bill, balance, and is_cleared flag.
    - Delegate all persistence to KhataRepository.

    Error Handling Strategy
    -----------------------
    AppException / NotFoundException  → re-raised as-is (router maps to HTTP).
    sqlalchemy.exc.IntegrityError     → caught explicitly; raises AppException(400).
    All other Exception               → logged with traceback + AppException(500).
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
            ID of the authenticated user (tube-well owner), sourced from JWT.
        data : dict
            Validated request body from KhataCreate schema.

        Returns
        -------
        KhataEntry
            The newly created and committed entry.

        Raises
        ------
        AppException(400)
            - Device not found or does not belong to this user.
            - motor_log_id provided but row does not exist in motor_logs
              (FK pre-validation — prevents IntegrityError 500).
            - Motor log is incomplete / still running (no end_time yet).
            - run_hours could not be determined from either field or log.
            - cash_received is negative.
            - cash_received exceeds total_bill.
        AppException(500)
            Unexpected database or runtime error.
        """
        try:
            # ── Step 1: Verify device ownership ──────────────────────────────
            # Device.user_id is the owner column; never trust customer_id/body.
            device = (
                self.db.query(Device)
                .filter(
                    Device.id      == data["device_id"],
                    Device.user_id == user_id           # ← always JWT, never body
                )
                .first()
            )
            if not device:
                logger.warning(
                    "Device access denied: device_id=%s, user_id=%s",
                    data.get("device_id"), user_id,
                )
                raise AppException(
                    status_code=400,
                    detail="Device not found or access denied",
                )

            # ── Step 2: Default date to today if not supplied ─────────────────
            if not data.get("date"):
                data["date"] = datetime.now().date()

            # ── Step 3: Validate motor_log_id FK *before* INSERT ──────────────
            #
            # PostgreSQL raises ForeignKeyViolation at commit time when
            # motor_log_id references a non-existent row, which surfaces as a
            # 500 IntegrityError.  Querying here first returns a clear 400.
            #
            if data.get("motor_log_id"):
                log_exists = (
                    self.db.query(MotorLog.id)
                    .filter(MotorLog.id == data["motor_log_id"])
                    .first()
                )
                if not log_exists:
                    logger.warning(
                        "FK pre-validation failed: motor_log_id=%s not in motor_logs",
                        data["motor_log_id"],
                    )
                    raise AppException(
                        status_code=400,
                        detail=(
                            f"motor_log_id '{data['motor_log_id']}' does not exist. "
                            "Create the motor log first, or omit motor_log_id."
                        ),
                    )

            # ── Step 4: Derive run_hours from MotorLog (if not provided) ──────
            # log existence is already confirmed in Step 3 when motor_log_id set.
            if not data.get("run_hours") and data.get("motor_log_id"):
                log = (
                    self.db.query(MotorLog)
                    .filter(MotorLog.id == data["motor_log_id"])
                    .first()
                )
                if not (log.start_time and log.end_time):
                    raise AppException(
                        status_code=400,
                        detail="Motor log is incomplete — motor may still be running",
                    )
                duration_seconds  = (log.end_time - log.start_time).total_seconds()
                data["run_hours"] = round(duration_seconds / 3600, 2)
                logger.debug(
                    "Derived run_hours=%.2f from motor_log_id=%s",
                    data["run_hours"], data["motor_log_id"],
                )

            if not data.get("run_hours"):
                raise AppException(
                    status_code=400,
                    detail=(
                        "Could not determine run_hours — "
                        "provide 'run_hours' directly or a valid 'motor_log_id'."
                    ),
                )

            # ── Step 5: Billing calculations ──────────────────────────────────
            hours = float(data["run_hours"])
            price = float(data["price_per_hour"])

            if data.get("total_bill") is None:
                data["total_bill"] = round(hours * price, 2)

            cash = float(data.get("cash_received") or 0)

            if cash < 0:
                raise AppException(
                    status_code=400,
                    detail="Cash received cannot be negative",
                )
            if cash > data["total_bill"]:
                raise AppException(
                    status_code=400,
                    detail=(
                        f"Cash received ({cash}) cannot exceed "
                        f"total bill ({data['total_bill']})"
                    ),
                )

            data["balance"]    = round(data["total_bill"] - cash, 2)
            data["is_cleared"] = data["balance"] <= 0

            # ── Step 6: Strip fields that must NOT come from the request body ─
            #
            # customer_id → always set from JWT user_id below (Step 7).
            # created_at  → DB server_default (now()); must not be overwritten.
            # user_id     → not a KhataEntry column; strip to avoid **data leak.
            #
            for field in ("customer_id", "created_at", "user_id"):
                data.pop(field, None)

            # ── Step 7: Persist ───────────────────────────────────────────────
            entry = KhataEntry(
                id      = str(uuid4()),
                user_id = user_id,   # always from JWT — never from request body
                **data,
            )
            created = self.repo.create_entry(entry)
            logger.info(
                "Khata entry created: id=%s, user_id=%s, customer=%s, "
                "total_bill=%s, balance=%s, cleared=%s",
                created.id, user_id, created.customer_name,
                created.total_bill, created.balance, created.is_cleared,
            )
            return created

        except (AppException, NotFoundException):
            raise

        except sqlalchemy.exc.IntegrityError as exc:
            # Safety net: catches any FK / unique violation missed by pre-checks.
            logger.error(
                "IntegrityError on khata create: %s", exc, exc_info=True
            )
            raise AppException(
                status_code=400,
                detail=(
                    "Database integrity error — a referenced record does not exist "
                    "or a unique constraint was violated. "
                    "Verify device_id and motor_log_id."
                ),
            )

        except Exception as exc:
            logger.error("Khata creation failed: %s", exc, exc_info=True)
            raise AppException(
                status_code=500,
                detail=f"Unexpected error while creating entry: {exc}",
            )

    # ─────────────────────────────────────────────────────────────────────────
    # UPDATE PAYMENT  (additive — partial or full settlement)
    # ─────────────────────────────────────────────────────────────────────────
    def update_payment(self, entry_id: str, user_id: str, cash_received: float):
        """
        Record an additional payment against an existing entry.

        Payments are additive: new cash is added to entry.cash_received.
        The entry remains visible after full payment (is_cleared=True);
        deletion requires a separate explicit DELETE call.

        Parameters
        ----------
        entry_id     : str   UUID of the KhataEntry to update.
        user_id      : str   Authenticated user from JWT — used to verify ownership.
        cash_received: float Additional cash amount received (must be > 0).

        Returns
        -------
        KhataEntry
            Updated entry with recalculated balance and is_cleared flag.

        Raises
        ------
        NotFoundException    Entry not found.
        AppException(403)   Caller does not own this entry.
        AppException(400)   Entry already cleared, or invalid cash amount.
        AppException(500)   Unexpected database or runtime error.
        """
        try:
            entry = self.repo.get_entry(entry_id)

            if entry.user_id != user_id:
                logger.warning(
                    "Payment update denied: entry_id=%s, user_id=%s, owner=%s",
                    entry_id, user_id, entry.user_id,
                )
                raise AppException(
                    status_code=403,
                    detail="Access denied: this entry does not belong to you",
                )

            if entry.is_cleared:
                raise AppException(
                    status_code=400,
                    detail="Entry is already fully cleared",
                )

            if cash_received <= 0:
                raise AppException(
                    status_code=400,
                    detail="Payment amount must be greater than zero",
                )

            new_total_cash = round(float(entry.cash_received or 0) + cash_received, 2)

            if new_total_cash > float(entry.total_bill):
                raise AppException(
                    status_code=400,
                    detail=(
                        f"Total cash ({new_total_cash}) would exceed "
                        f"total bill ({entry.total_bill})"
                    ),
                )

            entry.cash_received = new_total_cash
            entry.balance       = round(float(entry.total_bill) - new_total_cash, 2)
            entry.is_cleared    = entry.balance <= 0

            saved = self.repo.save(entry)
            logger.info(
                "Payment updated: id=%s, customer=%s, new_cash=%.2f, "
                "balance=%.2f, cleared=%s",
                entry_id, entry.customer_name,
                new_total_cash, entry.balance, entry.is_cleared,
            )
            return saved

        except (AppException, NotFoundException):
            raise

        except sqlalchemy.exc.IntegrityError as exc:
            logger.error(
                "IntegrityError on payment update: %s", exc, exc_info=True
            )
            raise AppException(
                status_code=400,
                detail="Database integrity error while updating payment.",
            )

        except Exception as exc:
            logger.error("Update payment failed: %s", exc, exc_info=True)
            raise AppException(
                status_code=500,
                detail=f"Unexpected error while updating payment: {exc}",
            )

    # ─────────────────────────────────────────────────────────────────────────
    # UPDATE ENTRY  (general field corrections / manual edits)
    # ─────────────────────────────────────────────────────────────────────────
    def update_entry(self, entry_id: str, user_id: str, data: dict):
        """
        Update editable fields on a Khata entry.

        Ownership is verified before any mutation. The repository is
        responsible for recalculating balance and is_cleared from the
        updated fields.

        Parameters
        ----------
        entry_id : str   UUID of the entry to update.
        user_id  : str   Authenticated user from JWT — must match entry.user_id.
        data     : dict  Partial fields to update (from KhataUpdate schema).

        Returns
        -------
        KhataEntry
            The updated entry.

        Raises
        ------
        NotFoundException   Entry not found.
        AppException(403)   Caller does not own this entry.
        AppException(500)   Unexpected database or runtime error.
        """
        try:
            entry = self.repo.get_entry(entry_id)

            if entry.user_id != user_id:
                logger.warning(
                    "Update denied: entry_id=%s, user_id=%s, owner=%s",
                    entry_id, user_id, entry.user_id,
                )
                raise AppException(
                    status_code=403,
                    detail="Access denied: this entry does not belong to you",
                )

            updated = self.repo.update_entry(entry, data)
            logger.info(
                "Entry updated: id=%s, customer=%s, balance=%.2f, cleared=%s",
                entry_id, updated.customer_name, updated.balance, updated.is_cleared,
            )
            return updated

        except (AppException, NotFoundException):
            raise

        except sqlalchemy.exc.IntegrityError as exc:
            logger.error(
                "IntegrityError on entry update: %s", exc, exc_info=True
            )
            raise AppException(
                status_code=400,
                detail="Database integrity error while updating entry.",
            )

        except Exception as exc:
            logger.error("Update entry failed: %s", exc, exc_info=True)
            raise AppException(
                status_code=500,
                detail=f"Unexpected error while updating entry: {exc}",
            )

    # ─────────────────────────────────────────────────────────────────────────
    # GET ALL  (for one user — cleared entries remain visible)
    # ─────────────────────────────────────────────────────────────────────────
    def get_all_entries(self, user_id: str):
        """
        Return every Khata entry belonging to the authenticated user.

        Cleared entries (is_cleared=True) are included. The caller / frontend
        can filter on is_cleared if only pending entries are needed.

        Parameters
        ----------
        user_id : str   Authenticated user from JWT.

        Returns
        -------
        list[KhataEntry]

        Raises
        ------
        AppException(500)   Unexpected database or runtime error.
        """
        try:
            entries = self.repo.get_all_entries(user_id)
            logger.debug(
                "Fetched %d entries for user_id=%s", len(entries), user_id
            )
            return entries

        except Exception as exc:
            logger.error("Get all entries failed: %s", exc, exc_info=True)
            raise AppException(
                status_code=500,
                detail=f"Unexpected error while fetching entries: {exc}",
            )

    # ─────────────────────────────────────────────────────────────────────────
    # GET ONE
    # ─────────────────────────────────────────────────────────────────────────
    def get_entry(self, entry_id: str, user_id: str):
        """
        Fetch a single entry, verifying it belongs to the requesting user.

        Parameters
        ----------
        entry_id : str   UUID of the entry.
        user_id  : str   Authenticated user from JWT.

        Returns
        -------
        KhataEntry

        Raises
        ------
        NotFoundException   Entry not found (raised by repository).
        AppException(403)   Caller does not own this entry.
        AppException(500)   Unexpected database or runtime error.
        """
        try:
            entry = self.repo.get_entry(entry_id)

            if entry.user_id != user_id:
                logger.warning(
                    "Get entry denied: entry_id=%s, user_id=%s, owner=%s",
                    entry_id, user_id, entry.user_id,
                )
                raise AppException(
                    status_code=403,
                    detail="Access denied: this entry does not belong to you",
                )

            return entry

        except (AppException, NotFoundException):
            raise

        except Exception as exc:
            logger.error("Get entry failed: %s", exc, exc_info=True)
            raise AppException(
                status_code=500,
                detail=f"Unexpected error while fetching entry: {exc}",
            )

    # ─────────────────────────────────────────────────────────────────────────
    # DELETE  (only allowed once fully cleared; hard delete)
    # ─────────────────────────────────────────────────────────────────────────
    def delete_entry(self, entry_id: str, user_id: str):
        """
        Permanently delete a Khata entry.

        Rules
        -----
        - Ownership verified: entry.user_id must equal the JWT user_id.
        - Deletion is only permitted when is_cleared=True. Entries with a
          pending balance cannot be removed; clear the balance first.

        Parameters
        ----------
        entry_id : str   UUID of the entry to delete.
        user_id  : str   Authenticated user from JWT.

        Returns
        -------
        bool  True on successful deletion.

        Raises
        ------
        NotFoundException   Entry not found (raised by repository).
        AppException(403)   Caller does not own this entry.
        AppException(400)   Entry has a pending balance (not yet cleared).
        AppException(500)   Unexpected database or runtime error.
        """
        try:
            entry = self.repo.get_entry(entry_id)

            if entry.user_id != user_id:
                logger.warning(
                    "Delete denied: entry_id=%s, user_id=%s, owner=%s",
                    entry_id, user_id, entry.user_id,
                )
                raise AppException(
                    status_code=403,
                    detail="Access denied: this entry does not belong to you",
                )

            if not entry.is_cleared:
                raise AppException(
                    status_code=400,
                    detail=(
                        f"Cannot delete: balance of {entry.balance} PKR is still pending. "
                        "Clear the balance first."
                    ),
                )

            result = self.repo.delete_entry(entry)
            logger.info(
                "Entry deleted: id=%s, customer=%s, user_id=%s",
                entry_id, entry.customer_name, user_id,
            )
            return result

        except (AppException, NotFoundException):
            raise

        except Exception as exc:
            logger.error("Delete entry failed: %s", exc, exc_info=True)
            raise AppException(
                status_code=500,
                detail=f"Unexpected error while deleting entry: {exc}",
            )