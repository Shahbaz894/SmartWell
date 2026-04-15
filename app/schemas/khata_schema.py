from pydantic import BaseModel, field_validator, model_validator, ConfigDict
from datetime import date as DateType
from typing import Optional, Literal


# ─────────────────────────────────────────────────────────────────────────────
# CREATE
# ─────────────────────────────────────────────────────────────────────────────
class KhataCreate(BaseModel):
    """
    Input schema for creating a new Khata entry.

    NOTE:
    user_id is NOT accepted from request body.
    It is always taken from authenticated JWT user.

    remaining_balance and payment_status are accepted in the request body
    but are ignored — they are always computed server-side from
    total_bill and cash_received.
    """

    # Required
    customer_name: str
    device_id: str
    price_per_hour: float

    # Optional
    motor_log_id: Optional[str] = None
    cash_received: Optional[float] = 0.0
    date: Optional[DateType] = None
    run_hours: Optional[float] = None
    total_bill: Optional[float] = None

    # Accepted but ignored — computed server-side
    remaining_balance: Optional[float] = None
    payment_status: Optional[Literal["paid", "partial", "unpaid"]] = None

    @field_validator("price_per_hour")
    @classmethod
    def price_must_be_positive(cls, v: float):
        if v <= 0:
            raise ValueError("Price per hour must be greater than zero")
        return v

    @field_validator("run_hours")
    @classmethod
    def run_hours_must_be_positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError("run_hours must be greater than zero")
        return v

    @field_validator("cash_received")
    @classmethod
    def cash_not_negative(cls, v):
        if v is not None and v < 0:
            raise ValueError("Cash received cannot be negative")
        return v

    @model_validator(mode="after")
    def require_hours_source(self):
        if not self.run_hours and not self.motor_log_id:
            raise ValueError(
                "Provide either 'run_hours' or 'motor_log_id'"
            )
        return self


# ─────────────────────────────────────────────────────────────────────────────
# UPDATE
# ─────────────────────────────────────────────────────────────────────────────
class KhataUpdate(BaseModel):
    """
    Update schema (partial updates allowed)
    """

    customer_name: Optional[str] = None
    run_hours: Optional[float] = None
    price_per_hour: Optional[float] = None
    total_bill: Optional[float] = None
    cash_received: Optional[float] = None
    date: Optional[DateType] = None

    @field_validator("price_per_hour", "run_hours", "total_bill")
    @classmethod
    def must_be_positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Value must be greater than zero")
        return v

    @field_validator("cash_received")
    @classmethod
    def cash_not_negative(cls, v):
        if v is not None and v < 0:
            raise ValueError("Cash received cannot be negative")
        return v


# ─────────────────────────────────────────────────────────────────────────────
# PAYMENT
# ─────────────────────────────────────────────────────────────────────────────
class KhataPayment(BaseModel):
    """
    Add payment to existing record
    """

    cash_received: float

    @field_validator("cash_received")
    @classmethod
    def must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("Payment amount must be greater than zero")
        return v


# ─────────────────────────────────────────────────────────────────────────────
# RESPONSE
# ─────────────────────────────────────────────────────────────────────────────
class KhataResponse(BaseModel):
    """
    Response schema.

    remaining_balance  — mirrors balance; computed in service layer.
    payment_status     — "paid" | "partial" | "unpaid"; computed in service layer.
    Both are NOT stored in the DB — they are attached to the ORM object
    dynamically before returning from each service method.
    """

    id: str
    user_id: Optional[str]
    customer_name: str
    device_id: str
    motor_log_id: Optional[str]
    date: DateType
    run_hours: float
    price_per_hour: float
    total_bill: float
    cash_received: float
    balance: float
    is_cleared: bool
    remaining_balance: Optional[float] = None          # computed, not stored
    payment_status: Optional[str] = None               # computed, not stored

    model_config = ConfigDict(from_attributes=True)