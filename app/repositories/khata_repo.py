# app/repositories/khata_repo.py

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.models.khata_entry import KhataEntry
from app.core.logger import logger
from app.core.exceptions import AppException, NotFoundException


class KhataRepository:

    def __init__(self, db: Session):
        self.db = db

    def create_entry(self, entry: KhataEntry):
        try:
            self.db.add(entry)
            self.db.commit()
            self.db.refresh(entry)
            logger.info(
                "Khata entry created: id=%s, customer=%s, amount=%s",
                entry.id,
                entry.customer_name,
                entry.total_bill
            )
            return entry
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(
                "Failed to create khata entry for customer %s: %s",
                entry.customer_name,
                str(e)
            )
            raise AppException(
                f"Database error: failed to create khata entry for customer {entry.customer_name}"
            )
    def update_entry(self, entry: KhataEntry, data: dict):
        try:
            for key, value in data.items():
                if hasattr(entry, key) and value is not None:
                    setattr(entry, key, value)
            # Recalculate balance if needed
            entry.balance = (entry.total_bill or 0) - (entry.cash_received or 0)
            # If fully paid, mark cleared
            entry.is_cleared = entry.balance <= 0
            self.db.commit()
            self.db.refresh(entry)
            logger.info("Khata entry updated: id=%s, customer=%s", entry.id, entry.customer_name)
            return entry
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error("Failed to update khata entry id=%s: %s", entry.id, str(e))
            raise AppException(f"Database error: failed to update khata entry {entry.id}")
    def get_entry(self, entry_id: str):
        try:
            entry = self.db.query(KhataEntry).filter(KhataEntry.id == entry_id).first()
            if not entry:
                logger.warning("Khata entry not found: id=%s", entry_id)
                raise NotFoundException(f"Khata entry {entry_id} not found")
            return entry
        except SQLAlchemyError as e:
            logger.error("Failed to fetch khata entry id=%s: %s", entry_id, str(e))
            raise AppException(f"Database error: failed to fetch khata entry {entry_id}")

    def delete_entry(self, entry: KhataEntry):
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
                "Failed to delete khata entry id=%s: %s",
                entry.id,
                str(e)
            )
            raise AppException(f"Database error: failed to delete khata entry {entry.id}")