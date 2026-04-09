# app/services/khata_service.py

from sqlalchemy.exc import SQLAlchemyError
from app.repositories.khata_repo import KhataRepository
from app.models.khata_entry import KhataEntry
from app.core.logger import logger
from app.core.exceptions import AppException, NotFoundException


# class KhataService:

#     def __init__(self, db):
#         self.repo = KhataRepository(db)

#     def create_entry(self, data):
#         try:
#             entry = KhataEntry(**data)
#             created_entry = self.repo.create_entry(entry)
#             logger.info(
#                 "Khata entry created: id=%s, customer=%s, amount=%s",
#                 created_entry.id,
#                 created_entry.customer_name,
#                 created_entry.total_bill
#             )
#             return created_entry
#         except SQLAlchemyError as e:
#             logger.error(
#                 "Failed to create khata entry for customer %s: %s",
#                 data.get("customer_name", "unknown"),
#                 str(e)
#             )
#             raise AppException(f"Database error: failed to create khata entry for customer {data.get('customer_name', 'unknown')}")

#     def delete_entry(self, entry_id):
#         try:
#             entry = self.repo.get_entry(entry_id)
#             if not entry:
#                 logger.warning("Khata entry not found: id=%s", entry_id)
#                 raise NotFoundException(f"Khata entry {entry_id} not found")

#             self.repo.delete_entry(entry)
#             logger.info(
#                 "Khata entry deleted: id=%s, customer=%s",
#                 entry.id,
#                 entry.customer_name
#             )
#             return True
#         except SQLAlchemyError as e:
#             logger.error("Failed to delete khata entry id=%s: %s", entry_id, str(e))
#             raise AppException(f"Database error: failed to delete khata entry {entry_id}")

class KhataService:

    def __init__(self, db):
        self.repo = KhataRepository(db)

    def create_entry(self, data: dict):
        try:
            # ✅ Validate required fields
            if not data.get("customer_name"):
                raise AppException("Customer name is required")

            if not data.get("price_per_hour"):
                raise AppException("Price per hour is required")

            # ✅ Auto-calculate run_hours from motor_log if not provided
            if not data.get("run_hours") and data.get("motor_log_id"):
                log = self.repo.get_motor_log(data["motor_log_id"])

                if not log or not log.duration_seconds:
                    raise AppException("Invalid motor log or motor not stopped")

                data["run_hours"] = round(log.duration_minutes / 3600, 2)

            # ✅ Calculate total bill
            if not data.get("total_bill"):
                data["total_bill"] = round(
                    data["run_hours"] * data["price_per_hour"], 2
                )

            # ✅ Default values
            cash_received = data.get("cash_received") or 0

            # ❗ Prevent negative payment
            if cash_received < 0:
                raise AppException("Cash received cannot be negative")

            # ❗ Prevent overpayment (optional rule)
            if cash_received > data["total_bill"]:
                raise AppException("Cash received cannot exceed total bill")

            # ✅ Calculate balance
            data["cash_received"] = cash_received
            data["balance"] = round(data["total_bill"] - cash_received, 2)

            # ✅ Auto clear logic
            data["is_cleared"] = data["balance"] <= 0

            # ✅ Create entry
            entry = KhataEntry(**data)
            created_entry = self.repo.create_entry(entry)

            logger.info(
                "Khata created: customer=%s, total=%s, paid=%s, balance=%s",
                created_entry.customer_name,
                created_entry.total_bill,
                created_entry.cash_received,
                created_entry.balance
            )

            return created_entry

        except SQLAlchemyError as e:
            logger.error("Database error while creating khata: %s", str(e))
            raise AppException("Database error: failed to create khata entry")

        except AppException:
            raise

        except Exception as e:
            logger.error("Unexpected error: %s", str(e))
            raise AppException("Unexpected error occurred")

    def update_entry(self, entry_id: str, data: dict):
        entry = self.repo.get_entry(entry_id)
        return self.repo.update_entry(entry, data)

    def delete_entry(self, entry_id: str):
        entry = self.repo.get_entry(entry_id)
        if entry.balance > 0:
            raise AppException("Cannot delete entry: balance not cleared")
        return self.repo.delete_entry(entry)