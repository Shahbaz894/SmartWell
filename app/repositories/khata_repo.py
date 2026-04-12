# app/repositories/khata_repo.py

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.models.khata_entry import KhataEntry
from app.core.logger import logger
from app.core.exceptions import AppException, NotFoundException


class KhataRepository:

    def __init__(self, db: Session):
        self.db = db

    # ─────────────────────────────────────────────
    # CREATE
    # ─────────────────────────────────────────────
    def create_entry(self, entry: KhataEntry):
        try:
            self.db.add(entry)
            self.db.commit()
            self.db.refresh(entry)
            logger.info(
                "Khata entry created: id=%s, customer=%s, total_bill=%s, balance=%s, is_cleared=%s",
                entry.id,
                entry.customer_name,
                entry.total_bill,
                entry.balance,
                entry.is_cleared
            )
            return entry
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(
                "DB error creating khata entry for customer=%s: %s",
                entry.customer_name,
                str(e),
                exc_info=True
            )
            raise AppException(
                f"Database error: failed to create khata entry for {entry.customer_name}"
            )

    # ─────────────────────────────────────────────
    # GET ONE
    # ─────────────────────────────────────────────
    def get_entry(self, entry_id: str):
        try:
            entry = (
                self.db.query(KhataEntry)
                .filter(KhataEntry.id == entry_id)
                .first()
            )
            if not entry:
                logger.warning("Khata entry not found: id=%s", entry_id)
                raise NotFoundException(f"Khata entry not found: {entry_id}")
            return entry
        except NotFoundException:
            raise  # re-raise as-is, not a DB error
        except SQLAlchemyError as e:
            logger.error(
                "DB error fetching khata entry id=%s: %s",
                entry_id,
                str(e),
                exc_info=True
            )
            raise AppException(f"Database error: failed to fetch khata entry {entry_id}")

    # ─────────────────────────────────────────────
    # GET ALL  (by user — cleared entries included)
    # ─────────────────────────────────────────────
    def get_all_entries(self, user_id: str):
        """
        Returns ALL entries for a user.
        Cleared entries remain visible with is_cleared=True.
        """
        try:
            entries = (
                self.db.query(KhataEntry)
                .filter(KhataEntry.customer_id == user_id)
                .order_by(KhataEntry.created_at.desc())
                .all()
            )
            logger.info(
                "Fetched %d khata entries for user_id=%s",
                len(entries),
                user_id
            )
            return entries
        except SQLAlchemyError as e:
            logger.error(
                "DB error fetching khata entries for user_id=%s: %s",
                user_id,
                str(e),
                exc_info=True
            )
            raise AppException(f"Database error: failed to fetch entries for user {user_id}")

    # ─────────────────────────────────────────────
    # SAVE  (used after updating payment)
    # ─────────────────────────────────────────────
    def save(self, entry: KhataEntry):
        """
        Persists changes to an already-tracked entry.
        Used by update_payment — entry stays visible after clearing.
        """
        try:
            self.db.commit()
            self.db.refresh(entry)
            logger.info(
                "Khata entry saved: id=%s, customer=%s, balance=%s, is_cleared=%s",
                entry.id,
                entry.customer_name,
                entry.balance,
                entry.is_cleared
            )
            return entry
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(
                "DB error saving khata entry id=%s: %s",
                entry.id,
                str(e),
                exc_info=True
            )
            raise AppException(f"Database error: failed to save khata entry {entry.id}")

    # ─────────────────────────────────────────────
    # UPDATE  (general field update)
    # ─────────────────────────────────────────────
    def update_entry(self, entry: KhataEntry, data: dict):
        """
        Updates allowed fields, recalculates balance and is_cleared.
        """
        try:
            for key, value in data.items():
                if hasattr(entry, key) and value is not None:
                    setattr(entry, key, value)

            # Recalculate balance after any field change
            total = float(entry.total_bill or 0)
            cash  = float(entry.cash_received or 0)

            entry.balance    = round(total - cash, 2)
            entry.is_cleared = entry.balance <= 0  # flag only — entry stays visible

            self.db.commit()
            self.db.refresh(entry)
            logger.info(
                "Khata entry updated: id=%s, customer=%s, balance=%s, is_cleared=%s",
                entry.id,
                entry.customer_name,
                entry.balance,
                entry.is_cleared
            )
            return entry
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(
                "DB error updating khata entry id=%s: %s",
                entry.id,
                str(e),
                exc_info=True
            )
            raise AppException(f"Database error: failed to update khata entry {entry.id}")

    # ─────────────────────────────────────────────
    # DELETE  (only after is_cleared=True)
    # ─────────────────────────────────────────────
    def delete_entry(self, entry: KhataEntry):
        """
        Permanently removes entry. Service layer ensures is_cleared=True before calling this.
        """
        try:
            self.db.delete(entry)
            self.db.commit()
            logger.info(
                "Khata entry deleted: id=%s, customer=%s",
                entry.id,
                entry.customer_name
            )
            return True
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(
                "DB error deleting khata entry id=%s: %s",
                entry.id,
                str(e),
                exc_info=True
            )
            raise AppException(f"Database error: failed to delete khata entry {entry.id}")