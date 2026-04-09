# from pydantic import BaseModel, Field
# from datetime import datetime

# class MotorTelemetryBase(BaseModel):
#     output_frequency: float = Field(alias="freq")
#     reference_frequency: float = Field(alias="reference_freq")
#     dc_bus_voltage: float = Field(alias="dcbus")
#     output_voltage: float = Field(alias="voltage")
#     output_current: float = Field(alias="current")
#     motor_speed: float = Field(alias="motor_speed")
#     power_load: float = Field(alias="power")
#     torque_load: float = Field(alias="torque_percent")
#     real_power: float = Field(alias="power_percent")

# class MotorTelemetryResponse(MotorTelemetryBase):
#     id: str
#     device_id: str
    
#     class Config:
#         from_attributes = True
#         populate_by_name = True
from pydantic import BaseModel
from typing import Optional


# -----------------------
# Base Schema (ESP32 Input)
# -----------------------
class MotorTelemetryBase(BaseModel):
    # Electrical data
    freq: float
    current: float
    voltage: float
    dcbus: float
    power: float

    # Performance
    reference_freq: float
    motor_speed: float
    power_percent: float
    torque_percent: float

    # Optional fields
    energy_in: Optional[float] = None
    fault: Optional[int] = None
    status_code: Optional[int] = None


# -----------------------
# Create Schema (POST)
# -----------------------
class MotorTelemetryCreate(MotorTelemetryBase):
    device_id: str   # e.g. SMSWELL1001


# -----------------------
# Response Schema (API → Flutter)
# -----------------------
class MotorTelemetryResponse(BaseModel):
    id: str
    device_id: str

    # Timestamp
    timestamp: int
    is_live: int  # 1 = live, 0 = offline/backfill

    # Electrical data
    freq: float
    current: float
    voltage: float
    dcbus: float
    power: float

    # Performance
    reference_freq: float
    motor_speed: float
    power_percent: float
    torque_percent: float

    # Optional
    energy_in: Optional[float]
    fault: Optional[int]
    status_code: Optional[int]

    class Config:
        from_attributes = True