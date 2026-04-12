from pydantic import BaseModel, field_validator, model_validator, ConfigDict
from datetime import date as DateType
from typing import Optional

# ─────────────────────────────────────────────
# CREATE — Minimal input from Frontend/IoT
# ─────────────────────────────────────────────
class KhataCreate(BaseModel):
    # Required from User
    customer_name: str
    device_id: str
    price_per_hour: float

    # Optional — Service layer will calculate these if not sent
    # Defaulting to None/0.0 prevents the "Field required" 422 error
    motor_log_id: Optional[str] = None
    cash_received: Optional[float] = 0.0
    date: Optional[DateType] = None
    run_hours: Optional[float] = None
    total_bill: Optional[float] = None

    @field_validator("price_per_hour")
    @classmethod
    def price_must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Price per hour must be greater than zero")
        return v

    @field_validator("cash_received")
    @classmethod
    def cash_not_negative(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError("Cash received cannot be negative")
        return v

    @model_validator(mode="after")
    def validate_calculation_logic(self) -> "KhataCreate":
        """
        Ensures we have a way to determine how long the motor ran.
        """
        if not self.run_hours and not self.motor_log_id:
            raise ValueError("You must provide either 'run_hours' or a 'motor_log_id'")
        return self


# ─────────────────────────────────────────────
# UPDATE — General field update (manual fixes)
# ─────────────────────────────────────────────
class KhataUpdate(BaseModel):
    customer_name: Optional[str] = None
    run_hours: Optional[float] = None
    price_per_hour: Optional[float] = None
    total_bill: Optional[float] = None
    cash_received: Optional[float] = None
    is_cleared: Optional[bool] = None

    @field_validator("price_per_hour", "run_hours")
    @classmethod
    def must_be_positive(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v <= 0:
            raise ValueError("Value must be greater than zero")
        return v


# ─────────────────────────────────────────────
# PAYMENT — Specific for adding money
# ─────────────────────────────────────────────
class KhataPayment(BaseModel):
    """Used for adding payment to an existing balance."""
    cash_received: float

    @field_validator("cash_received")
    @classmethod
    def must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Payment amount must be greater than zero")
        return v


# ─────────────────────────────────────────────
# RESPONSE — What the API returns
# ─────────────────────────────────────────────
class KhataResponse(BaseModel):
    id: str
    customer_id: Optional[str]
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

    # Pydantic v2 configuration
    model_config = ConfigDict(from_attributes=True)