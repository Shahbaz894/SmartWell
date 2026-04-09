
# from pydantic import BaseModel
# from typing import Optional


# # -----------------------
# # Base Schema (ESP32 Input)
# # -----------------------
# class MotorTelemetryBase(BaseModel):
#     # Electrical data
#     freq: float
#     current: float
#     voltage: float
#     dcbus: float
#     power: float

#     # Performance
#     reference_freq: float
#     motor_speed: float
#     power_percent: float
#     torque_percent: float

#     # Optional fields
#     energy_in: Optional[float] = None
#     fault: Optional[int] = None
#     status_code: Optional[int] = None


# # -----------------------
# # Create Schema (POST)
# # -----------------------
# class MotorTelemetryCreate(MotorTelemetryBase):
#     device_id: str   # e.g. SMSWELL1001


# # -----------------------
# # Response Schema (API → Flutter)
# # -----------------------
# class MotorTelemetryResponse(BaseModel):
#     id: str
#     device_id: str

#     # Timestamp
#     timestamp: int
#     is_live: int  # 1 = live, 0 = offline/backfill

#     # Electrical data
#     freq: float
#     current: float
#     voltage: float
#     dcbus: float
#     power: float

#     # Performance
#     reference_freq: float
#     motor_speed: float
#     power_percent: float
#     torque_percent: float

#     # Optional
#     energy_in: Optional[float]
#     fault: Optional[int]
#     status_code: Optional[int]

#     class Config:
#         from_attributes = True

from pydantic import BaseModel
from typing import Optional


# -----------------------
# ESP32 INPUT
# -----------------------
class MotorTelemetryCreate(BaseModel):
    device_id: str

    timestamp: int

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

    is_live: int   # 1 = live, 0 = offline


# -----------------------
# RESPONSE
# -----------------------
class MotorTelemetryResponse(MotorTelemetryCreate):
    id: str

    class Config:
        from_attributes = True