


from sqlalchemy.exc import SQLAlchemyError
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

    def create_entry(self, user_id: str, data: dict):
        try:
            # ✅ Validate device belongs to user
            device = self.db.query(Device).filter_by(id=data["device_id"], user_id=user_id).first()
            if not device:
                raise AppException("Invalid device_id or device doesn't belong to you")

            # ✅ Customer info - mandatory from UI
            if not data.get("customer_name"):
                raise AppException("customer_name is required")

            # ✅ Set customer_id from logged-in user
            data["customer_id"] = str(user_id)   # ← Add it here

            # ✅ run_hours logic
            if not data.get("run_hours") and data.get("motor_log_id"):
                log = self.db.query(MotorLog).filter_by(id=data["motor_log_id"]).first()
                if not log:
                    raise AppException("Invalid motor log")
                if log.start_time and log.end_time:
                    duration = (log.end_time - log.start_time).total_seconds()
                    data["run_hours"] = round(duration / 3600, 2)
                else:
                    raise AppException("Motor log not completed")

            # ✅ Billing calculations
            hours = float(data["run_hours"])
            price = float(data["price_per_hour"])
            if data.get("total_bill") is None:
                data["total_bill"] = round(hours * price, 2)

            cash = float(data.get("cash_received") or 0)
            if cash < 0:
                raise AppException("Cash cannot be negative")
            if cash > data["total_bill"]:
                raise AppException("Cash cannot exceed total bill")

            data["cash_received"] = cash
            data["balance"] = round(data["total_bill"] - cash, 2)
            data["is_cleared"] = data["balance"] <= 0

            # ✅ Save KhataEntry
            entry = KhataEntry(
                id=str(uuid4()),
                created_at=datetime.now(),
                **data
            )

            return self.repo.create_entry(entry)

        except Exception as e:
            logger.error("Create khata failed: %s", str(e), exc_info=True)
            raise AppException(str(e))

    def update_entry(self, entry_id: str, data: dict):
        try:
            entry = self.repo.get_entry(entry_id)
            return self.repo.update_entry(entry, data)
        except Exception as e:
            logger.error("Update khata failed: %s", str(e), exc_info=True)
            raise AppException(str(e))

    def delete_entry(self, entry_id: str):
        try:
            entry = self.repo.get_entry(entry_id)
            if entry.balance > 0:
                raise AppException("Cannot delete entry: balance not cleared")
            return self.repo.delete_entry(entry)
        except Exception as e:
            logger.error("Delete khata failed: %s", str(e), exc_info=True)
            raise AppException(str(e))