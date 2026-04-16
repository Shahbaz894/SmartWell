from typing import Optional

from pydantic import BaseModel, Field, field_validator


class MotorTelemetryCreate(BaseModel):
    """
    Incoming telemetry payload from ESP32.
    """

    timestamp: int = Field(..., description="Device timestamp in milliseconds or seconds")

    freq: float
    current: float
    voltage: float
    dcbus: float
    power: float
    energy_in: Optional[float] = None

    fault: Optional[int] = None
    fault_code: Optional[int] = None
    status_code: Optional[int] = None

    reference_freq: float
    motor_speed: float
    power_percent: float
    torque_percent: float

    is_live: int = Field(..., description="1 = live packet, 0 = offline EEPROM packet")

    @field_validator("is_live")
    @classmethod
    def validate_is_live(cls, value: int) -> int:
        if value not in (0, 1):
            raise ValueError("is_live must be 0 or 1")
        return value

    @field_validator(
        "freq",
        "current",
        "voltage",
        "dcbus",
        "power",
        "reference_freq",
        "motor_speed",
        "power_percent",
        "torque_percent",
        mode="before",
    )
    @classmethod
    def validate_non_negative_numeric_fields(cls, value):
        if value is None:
            return value
        if float(value) < 0:
            raise ValueError("Telemetry numeric values must be non-negative")
        return value


class MotorTelemetryResponse(BaseModel):
    """
    Telemetry response schema.
    """

    id: str
    device_id: str

    timestamp: int

    freq: float
    current: float
    voltage: float
    dcbus: float
    power: float
    energy_in: Optional[float]

    fault: Optional[int]
    fault_code: Optional[int]
    status_code: Optional[int]

    reference_freq: float
    motor_speed: float
    power_percent: float
    torque_percent: float

    is_live: int

    class Config:
        from_attributes = True