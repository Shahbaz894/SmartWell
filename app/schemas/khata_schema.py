# app/schemas/khata_schema.py

from pydantic import BaseModel, field_validator, model_validator
from datetime import date as DateType
from typing import Optional
from uuid import UUID


# ─────────────────────────────────────────────
# CREATE  — fields sent by user (minimal input)
# ─────────────────────────────────────────────
class KhataCreate(BaseModel):
    # Required fields
    customer_name: str
    device_id:     str
    price_per_hour: float

    # Optional fields — auto-calculated in service
    customer_id:   Optional[str]       = None
    motor_log_id:  Optional[str]       = None
    cash_received: Optional[float]     = 0.0
    date:          Optional[DateType]  = None
    run_hours:     Optional[float]     = None
    total_bill:    Optional[float]     = None
    is_cleared:    Optional[bool]      = False

    @field_validator("price_per_hour")
    @classmethod
    def price_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("price_per_hour must be greater than zero")
        return v

    @field_validator("cash_received")
    @classmethod
    def cash_not_negative(cls, v):
        if v is not None and v < 0:
            raise ValueError("cash_received cannot be negative")
        return v

    @field_validator("run_hours")
    @classmethod
    def run_hours_positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError("run_hours must be greater than zero")
        return v

    @model_validator(mode="after")
    def motor_log_or_run_hours_required(self):
        """
        User must provide either run_hours or motor_log_id.
        If neither is given, service will raise — but we can catch it early here.
        """
        if not self.run_hours and not self.motor_log_id:
            raise ValueError("Provide either run_hours or motor_log_id")
        return self


# ─────────────────────────────────────────────
# UPDATE  — general field update (admin/manual fix)
# ─────────────────────────────────────────────
class KhataUpdate(BaseModel):
    customer_name:  Optional[str]   = None
    run_hours:      Optional[float] = None
    price_per_hour: Optional[float] = None
    total_bill:     Optional[float] = None
    cash_received:  Optional[float] = None
    is_cleared:     Optional[bool]  = None

    @field_validator("price_per_hour")
    @classmethod
    def price_must_be_positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError("price_per_hour must be greater than zero")
        return v

    @field_validator("run_hours")
    @classmethod
    def run_hours_positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError("run_hours must be greater than zero")
        return v

    @field_validator("cash_received")
    @classmethod
    def cash_not_negative(cls, v):
        if v is not None and v < 0:
            raise ValueError("cash_received cannot be negative")
        return v


# ─────────────────────────────────────────────
# PAYMENT  — when customer pays balance
# ─────────────────────────────────────────────
class KhataPayment(BaseModel):
    """
    Used for PATCH /khata/{id}/pay
    Adds to existing cash_received, recalculates balance.
    Entry stays visible after clearing — is_cleared is just a flag.
    """
    cash_received: float

    @field_validator("cash_received")
    @classmethod
    def must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("Payment amount must be greater than zero")
        return v


# ─────────────────────────────────────────────
# RESPONSE  — what API returns to client
# ─────────────────────────────────────────────
class KhataResponse(BaseModel):
    id:             str
    customer_id:    Optional[str]
    customer_name:  str
    device_id:      str
    motor_log_id:   Optional[str]
    date:           DateType
    run_hours:      float
    price_per_hour: float
    total_bill:     float
    cash_received:  float
    balance:        float
    is_cleared:     bool  # True = cleared but entry still visible

    class Config:
        from_attributes = True  # replaces orm_mode in Pydantic v2