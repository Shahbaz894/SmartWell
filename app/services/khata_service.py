# app/services/khata_service.py

from sqlalchemy.exc import SQLAlchemyError
from app.repositories.khata_repo import KhataRepository
from app.models.khata_entry import KhataEntry
from app.core.logger import logger
from app.core.exceptions import AppException, NotFoundException


class KhataService:

    def __init__(self, db):
        self.repo = KhataRepository(db)

    def create_entry(self, data):
        try:
            entry = KhataEntry(**data)
            created_entry = self.repo.create_entry(entry)
            logger.info(
                "Khata entry created: id=%s, customer=%s, amount=%s",
                created_entry.id,
                created_entry.customer_name,
                created_entry.total_bill
            )
            return created_entry
        except SQLAlchemyError as e:
            logger.error(
                "Failed to create khata entry for customer %s: %s",
                data.get("customer_name", "unknown"),
                str(e)
            )
            raise AppException(f"Database error: failed to create khata entry for customer {data.get('customer_name', 'unknown')}")

    def delete_entry(self, entry_id):
        try:
            entry = self.repo.get_entry(entry_id)
            if not entry:
                logger.warning("Khata entry not found: id=%s", entry_id)
                raise NotFoundException(f"Khata entry {entry_id} not found")

            self.repo.delete_entry(entry)
            logger.info(
                "Khata entry deleted: id=%s, customer=%s",
                entry.id,
                entry.customer_name
            )
            return True
        except SQLAlchemyError as e:
            logger.error("Failed to delete khata entry id=%s: %s", entry_id, str(e))
            raise AppException(f"Database error: failed to delete khata entry {entry_id}")