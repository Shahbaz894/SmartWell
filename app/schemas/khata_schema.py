


from pydantic import BaseModel, field_validator, model_validator, ConfigDict
from datetime import date as DateType
from typing import Optional, Literal
from datetime import date
from uuid import UUID


# ─────────────────────────────────────────────────────────────────────────────
# CREATE
# ─────────────────────────────────────────────────────────────────────────────
class KhataCreate(BaseModel):
    """
    Input schema for creating a new Khata entry.

    user_id is NOT accepted from request body.
    It is always taken from authenticated JWT user.

    price_per_hour may be 0 when the entry is created from motor stop.
    The real price can be entered later from Khata screen.

    remaining_balance and payment_status are accepted in the request body
    but are ignored. They are computed server-side from total_bill and
    cash_received.
    """

    customer_name: str
    device_id: str
    price_per_hour: float = 0.0

    motor_log_id: Optional[str] = None
    cash_received: Optional[float] = 0.0
    date: Optional[DateType] = None
    run_hours: Optional[float] = None
    total_bill: Optional[float] = 0.0
    advance_amount: Optional[float] = 0.0

    remaining_balance: Optional[float] = None
    payment_status: Optional[Literal["paid", "partial", "unpaid"]] = None

    @field_validator("price_per_hour")
    @classmethod
    def price_not_negative(cls, v: float):
        if v < 0:
            raise ValueError("Price per hour cannot be negative")
        return v

    @field_validator("run_hours")
    @classmethod
    def run_hours_must_be_positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError("run_hours must be greater than zero")
        return v

    @field_validator("total_bill")
    @classmethod
    def total_bill_not_negative(cls, v):
        if v is not None and v < 0:
            raise ValueError("total_bill cannot be negative")
        return v
    @field_validator("advance_amount")
    @classmethod
    def advance_not_negative(cls, v):
        if v is not None and v < 0:
            raise ValueError("Advance amount cannot be negative")
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
            raise ValueError("Provide either 'run_hours' or 'motor_log_id'")
        return self


# ─────────────────────────────────────────────────────────────────────────────
# UPDATE
# ─────────────────────────────────────────────────────────────────────────────
class KhataUpdate(BaseModel):
    """
    Update schema.

    price_per_hour and total_bill may be 0 because newly created Khata
    records can be pending until price is entered.
    """

    customer_name: Optional[str] = None
    run_hours: Optional[float] = None
    price_per_hour: Optional[float] = None
    total_bill: Optional[float] = None
    cash_received: Optional[float] = None
    date: Optional[DateType] = None
    advance_amount: Optional[float] = None

    @field_validator("run_hours")
    @classmethod
    def run_hours_must_be_positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError("run_hours must be greater than zero")
        return v

    @field_validator("price_per_hour", "total_bill")
    @classmethod
    def value_not_negative(cls, v):
        if v is not None and v < 0:
            raise ValueError("Value cannot be negative")
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
    Add payment to existing record.
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
    id: UUID
    user_id: UUID
    customer_name: str
    device_id: UUID
    motor_log_id: Optional[UUID] = None

    date: date
    run_hours: float
    price_per_hour: float

    total_bill: float
    cash_received: float
    balance: float
    is_cleared: bool

    remaining_balance: Optional[float] = None
    payment_status: Optional[str] = None
    advance_amount: float = 0

    model_config = ConfigDict(from_attributes=True)