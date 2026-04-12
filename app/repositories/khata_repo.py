# app/repositories/khata_repo.py
#
# Data-access layer for KhataEntry.
# All SQL operations live here; zero business logic.
#
# ── Naming Convention ─────────────────────────────────────────────────────────
#  KhataEntry.user_id  = tube-well owner's user ID (from JWT).
#  All queries filter by user_id — ownership checks are the service's job.
# ──────────────────────────────────────────────────────────────────────────────

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.models.khata_entry import KhataEntry
from app.core.logger import logger
from app.core.exceptions import AppException, NotFoundException


class KhataRepository:
    """
    Repository for KhataEntry persistence.

    All methods raise AppException on SQLAlchemy errors and
    NotFoundException when a requested record does not exist.
    Business validation belongs in KhataService, not here.
    """

    def __init__(self, db: Session):
        self.db = db

    # ─────────────────────────────────────────────────────────────────────────
    # CREATE
    # ─────────────────────────────────────────────────────────────────────────
    def create_entry(self, entry: KhataEntry) -> KhataEntry:
        """
        Persist a new KhataEntry and return the refreshed object.

        Rolls back the transaction on any SQLAlchemy error to keep
        the session clean for subsequent operations.
        """
        try:
            self.db.add(entry)
            self.db.commit()
            self.db.refresh(entry)
            logger.info(
                "KhataEntry created | id=%s user_id=%s customer=%s "
                "total_bill=%s balance=%s is_cleared=%s",
                entry.id, entry.user_id, entry.customer_name,
                entry.total_bill, entry.balance, entry.is_cleared,
            )
            return entry
        except SQLAlchemyError as exc:
            self.db.rollback()
            logger.error(
                "DB error creating KhataEntry for customer=%s: %s",
                entry.customer_name, exc, exc_info=True,
            )
            raise AppException(
                f"Database error: failed to create khata entry "
                f"for '{entry.customer_name}'"
            )

    # ─────────────────────────────────────────────────────────────────────────
    # GET ONE
    # ─────────────────────────────────────────────────────────────────────────
    def get_entry(self, entry_id: str) -> KhataEntry:
        """
        Fetch a single KhataEntry by primary key.

        Raises NotFoundException when no row matches.
        Ownership checks are the caller's responsibility.
        """
        try:
            entry = (
                self.db.query(KhataEntry)
                .filter(KhataEntry.id == entry_id)
                .first()
            )
            if not entry:
                logger.warning("KhataEntry not found: id=%s", entry_id)
                raise NotFoundException(f"Khata entry not found: {entry_id}")
            return entry
        except NotFoundException:
            raise
        except SQLAlchemyError as exc:
            logger.error(
                "DB error fetching KhataEntry id=%s: %s",
                entry_id, exc, exc_info=True,
            )
            raise AppException(
                f"Database error: failed to fetch khata entry {entry_id}"
            )

    # ─────────────────────────────────────────────────────────────────────────
    # GET ALL  (by owner — cleared entries included)
    # ─────────────────────────────────────────────────────────────────────────
    def get_all_entries(self, user_id: str) -> list[KhataEntry]:
        """
        Return all KhataEntry rows where user_id matches.

        Rows are ordered newest-first.
        Cleared entries (is_cleared=True) are NOT excluded here;
        the service/frontend layer handles any UI-level filtering.
        """
        try:
            entries = (
                self.db.query(KhataEntry)
                .filter(KhataEntry.user_id == user_id)
                .order_by(KhataEntry.created_at.desc())
                .all()
            )
            logger.info(
                "Fetched %d KhataEntries for user_id=%s",
                len(entries), user_id,
            )
            return entries
        except SQLAlchemyError as exc:
            logger.error(
                "DB error fetching KhataEntries for user_id=%s: %s",
                user_id, exc, exc_info=True,
            )
            raise AppException(
                f"Database error: failed to fetch entries for user {user_id}"
            )

    # ─────────────────────────────────────────────────────────────────────────
    # SAVE  (used after in-memory mutations — e.g. update_payment)
    # ─────────────────────────────────────────────────────────────────────────
    def save(self, entry: KhataEntry) -> KhataEntry:
        """
        Commit changes to an already-tracked (dirty) KhataEntry.

        The caller mutates the object fields; this method flushes
        those changes to the database and refreshes the instance.
        """
        try:
            self.db.commit()
            self.db.refresh(entry)
            logger.info(
                "KhataEntry saved | id=%s customer=%s balance=%s is_cleared=%s",
                entry.id, entry.customer_name, entry.balance, entry.is_cleared,
            )
            return entry
        except SQLAlchemyError as exc:
            self.db.rollback()
            logger.error(
                "DB error saving KhataEntry id=%s: %s",
                entry.id, exc, exc_info=True,
            )
            raise AppException(
                f"Database error: failed to save khata entry {entry.id}"
            )

    # ─────────────────────────────────────────────────────────────────────────
    # UPDATE  (general field-level update with balance recalculation)
    # ─────────────────────────────────────────────────────────────────────────
    def update_entry(self, entry: KhataEntry, data: dict) -> KhataEntry:
        """
        Apply a dict of field updates to a KhataEntry and persist.

        After applying all field changes, balance and is_cleared are
        recalculated from the current total_bill and cash_received values.

        Parameters
        ----------
        entry : KhataEntry  The tracked ORM instance to mutate.
        data  : dict        Key-value pairs for allowed fields (from KhataUpdate).
        """
        try:
            for key, value in data.items():
                if hasattr(entry, key) and value is not None:
                    setattr(entry, key, value)
                    logger.debug(
                        "Field updated: %s → %s on entry %s", key, value, entry.id
                    )

            # Recalculate derived fields after any change
            total = float(entry.total_bill    or 0)
            cash  = float(entry.cash_received or 0)

            entry.balance    = round(total - cash, 2)
            entry.is_cleared = entry.balance <= 0

            self.db.commit()
            self.db.refresh(entry)
            logger.info(
                "KhataEntry updated | id=%s customer=%s balance=%s is_cleared=%s",
                entry.id, entry.customer_name, entry.balance, entry.is_cleared,
            )
            return entry
        except SQLAlchemyError as exc:
            self.db.rollback()
            logger.error(
                "DB error updating KhataEntry id=%s: %s",
                entry.id, exc, exc_info=True,
            )
            raise AppException(
                f"Database error: failed to update khata entry {entry.id}"
            )

    # ─────────────────────────────────────────────────────────────────────────
    # DELETE  (permanent; only called after is_cleared guard in service)
    # ─────────────────────────────────────────────────────────────────────────
    def delete_entry(self, entry: KhataEntry) -> bool:
        """
        Hard-delete a KhataEntry from the database.

        The service layer must verify is_cleared=True before calling this.
        This method performs no business validation.

        Returns
        -------
        bool  True on success.
        """
        try:
            self.db.delete(entry)
            self.db.commit()
            logger.info(
                "KhataEntry deleted | id=%s customer=%s",
                entry.id, entry.customer_name,
            )
            return True
        except SQLAlchemyError as exc:
            self.db.rollback()
            logger.error(
                "DB error deleting KhataEntry id=%s: %s",
                entry.id, exc, exc_info=True,
            )
            raise AppException(
                f"Database error: failed to delete khata entry {entry.id}"
            )