# app/schemas/khata_schema.py

from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional


# class KhataCreate(BaseModel):
#     customer_id: str
#     device_id: str
#     motor_log_id: Optional[str]
#     date: date
#     run_hours: float
#     price_per_hour: float
#     total_bill: float
#     cash_received: Optional[float] = 0
#     is_cleared: Optional[bool] = False


# class KhataUpdate(BaseModel):
#     run_hours: Optional[float]
#     price_per_hour: Optional[float]
#     total_bill: Optional[float]
#     cash_received: Optional[float]
#     is_cleared: Optional[bool]


# class KhataResponse(BaseModel):
#     id: str
#     customer_id: str
#     device_id: str
#     motor_log_id: Optional[str]
#     date: date
#     run_hours: float
#     price_per_hour: float
#     total_bill: float
#     cash_received: float
#     balance: Optional[float]
#     is_cleared: bool
#     created_at: datetime

#     class Config:
#         from_attributes = True

class KhataCreate(BaseModel):
    customer_name: str
    customer_id: Optional[str] = None
    device_id: str
    motor_log_id: Optional[str] = None
    date: date
    run_hours: float
    price_per_hour: float
    total_bill: float
    cash_received: Optional[float] = 0
    is_cleared: Optional[bool] = False

class KhataUpdate(BaseModel):
    customer_name: Optional[str]
    run_hours: Optional[float]
    price_per_hour: Optional[float]
    total_bill: Optional[float]
    cash_received: Optional[float]
    is_cleared: Optional[bool]