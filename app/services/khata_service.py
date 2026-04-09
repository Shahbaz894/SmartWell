# app/services/khata_service.py

from sqlalchemy.exc import SQLAlchemyError
from app.models.device import Device
from app.repositories.khata_repo import KhataRepository
from app.models.khata_entry import KhataEntry
from app.core.logger import logger
from app.core.exceptions import AppException, NotFoundException




class KhataService:

    def __init__(self, db):
        self.repo = KhataRepository(db)

   
    def create_entry(self, data: dict):
        try:
            # ✅ Validate device
            device = self.db.query(Device).filter_by(id=data["device_id"]).first()
            if not device:
                raise AppException("Invalid device_id")

            # ✅ Handle customer (AUTO or MANUAL)
            if device.customer_id:
                # Auto from DB
                data["customer_id"] = device.customer_id
                data["customer_name"] = device.customer.name
            else:
                # Manual entry
                if not data.get("customer_name"):
                    raise AppException("Customer name is required")

            # ✅ run_hours logic
            if not data.get("run_hours") and not data.get("motor_log_id"):
                raise AppException("run_hours or motor_log_id is required")

            if not data.get("run_hours") and data.get("motor_log_id"):
                log = self.repo.get_motor_log(data["motor_log_id"])

                if not log or not log.duration_seconds:
                    raise AppException("Invalid motor log")

                data["run_hours"] = round(log.duration_seconds / 3600, 2)

            # ✅ billing
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

            # ✅ Save
            entry = KhataEntry(**data)
            return self.repo.create_entry(entry)

        except Exception as e:
            logger.error("Create khata failed: %s", str(e))
            raise AppException(str(e))

    def update_entry(self, entry_id: str, data: dict):
        entry = self.repo.get_entry(entry_id)
        return self.repo.update_entry(entry, data)

    def delete_entry(self, entry_id: str):
        entry = self.repo.get_entry(entry_id)
        if entry.balance > 0:
            raise AppException("Cannot delete entry: balance not cleared")
        return self.repo.delete_entry(entry)