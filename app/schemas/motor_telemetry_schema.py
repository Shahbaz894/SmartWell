from datetime import datetime
from tokenize import String
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import Mapped
from app.schemas.motor_timer_schema import TriggerType #
from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator
from enum import Enum
from sqlalchemy import Column, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

STATUS_CODE_MAP = {
    0: {"name": "Motor Off", "description": "Motor is stopped"},
    1: {"name": "Forward Running", "description": "Motor/device is running in forward direction"},
    2: {"name": "Reverse Running", "description": "Motor/device is running in reverse direction"},
    3: {"name": "Standby", "description": "Device is idle, no movement"},
    4: {"name": "Fault", "description": "Error condition detected"},
    5: {"name": "Power Off", "description": "Device is powered off or shut down"},
}

FAULT_CODE_MAP = {
    0: {"name": "No Fault", "description": "Drive operating normally"},
    1: {"name": "OUT1", "description": "Output phase fault. Possible motor cable disconnect, loose output terminal, or missing motor phase."},
    2: {"name": "OUT2", "description": "Output abnormality. Possible motor short circuit or output wiring issue."},
    3: {"name": "OUT3", "description": "Output phase imbalance. Possible open motor phase or motor winding damage."},
    4: {"name": "OC1", "description": "Acceleration overcurrent. Possible short acceleration time, heavy load, or jammed motor."},
    5: {"name": "OC2", "description": "Deceleration overcurrent. Possible short deceleration time or high inertia load."},
    6: {"name": "OC3", "description": "Constant speed overcurrent. Possible mechanical overload or motor rated current exceeded."},
    7: {"name": "OV1", "description": "Acceleration overvoltage. DC bus voltage too high during acceleration."},
    8: {"name": "OV2", "description": "Deceleration overvoltage. Possible fast deceleration or missing braking resistor."},
    9: {"name": "OV3", "description": "Constant overvoltage. DC bus voltage too high during normal operation."},
    10: {"name": "UV", "description": "Under voltage. Possible weak supply or loose input cable."},
    11: {"name": "OL1", "description": "Motor overload. Motor current too high for long duration."},
    12: {"name": "OL2", "description": "Drive overload. Load may exceed VFD capacity."},
    13: {"name": "SPI", "description": "Internal communication fault."},
    14: {"name": "SPO", "description": "Output protection triggered."},
    15: {"name": "OH1", "description": "Drive overheat. Possible cooling fan failure or poor ventilation."},
    16: {"name": "OH2", "description": "Motor overheat. Motor thermal protection triggered."},
    17: {"name": "EF", "description": "External fault. External safety device triggered."},
    18: {"name": "CE", "description": "Communication error."},
    19: {"name": "ItE", "description": "Current detection error."},
}


# class MotorTelemetryCreate(BaseModel):
#     # Fallback to defaults instead of crashing backend
#     timestamp: Optional[int] = Field(default=0)
#     freq: Optional[float] = Field(default=0.0)
#     current: Optional[float] = Field(default=0.0)
#     voltage: Optional[float] = Field(default=0.0)
#     dcbus: Optional[float] = Field(default=0.0)
#     power: Optional[float] = Field(default=0.0)
#     energy_in: Optional[float] = Field(default=0.0)
    
#     trigger_type: Mapped[TriggerType] = mapped_column(
#         SQLEnum(TriggerType), 
#         default=TriggerType.physical
#     )  
    
#     fault: Optional[int] = Field(default=0)
#     fault_code: Optional[int] = Field(default=0)
#     status_code: Optional[int] = Field(default=0)

#     reference_freq: Optional[float] = Field(default=0.0)
#     motor_speed: Optional[float] = Field(default=0.0)
#     power_percent: Optional[float] = Field(default=0.0)
#     torque_percent: Optional[float] = Field(default=0.0)
#     is_live: Optional[int] = Field(default=0)

#     @field_validator("is_live", "fault")
#     @classmethod
#     def validate_binary_flags(cls, value: Optional[int]) -> int:
#         """Safely maps binary flags and prevents crashes."""
#         val = value if value is not None else 0
#         if val not in (0, 1):
#             return 0  # Safe Fallback
#         return val

#     @field_validator("fault_code")
#     @classmethod
#     def validate_fault_code(cls, value: Optional[int]) -> int:
#         """Validates VFD fault codes range safely."""
#         val = value if value is not None else 0
#         if val not in FAULT_CODE_MAP:
#             return 0  # Default to No Fault instead of crashing thread
#         return val

#     @field_validator("status_code")
#     @classmethod
#     def validate_status_code(cls, value: Optional[int]) -> int:
#         """Validates motor status codes safely."""
#         val = value if value is not None else 0
#         if val not in STATUS_CODE_MAP:
#             return 0  # Fallback to Motor Off
#         return val

#     @field_validator(
#         "freq", "current", "voltage", "dcbus", "power", "energy_in",
#         "reference_freq", "motor_speed", "power_percent", "torque_percent",
#         mode="before"
#     )
#     @classmethod
#     def validate_non_negative_numeric_fields(cls, value):
#         """Prevents float parse exceptions and negative telemetry values."""
#         if value is None: 
#             return 0.0
#         try:
#             val = float(value)
#             return val if val >= 0 else 0.0
#         except (ValueError, TypeError):
#             return 0.0  # Fallback gracefully if hardware sends corrupt text

#     model_config = ConfigDict(from_attributes=True)


# class MotorTelemetryResponse(BaseModel):
#     id: UUID
#     device_id: UUID
#     created_at: datetime 
#     timestamp: int

#     freq: float
#     current: float
#     voltage: float
#     dcbus: float
#     power: float
#     energy_in: Optional[float]

#     fault: Optional[int]
#     fault_code: Optional[int]
#     status_code: Optional[int]

#     reference_freq: float
#     motor_speed: float
#     power_percent: float
#     torque_percent: float

#     is_live: int

#     @computed_field
#     @property
#     def status_name(self) -> str:
#         if self.status_code is None:
#             return "Unknown"
#         return STATUS_CODE_MAP.get(self.status_code, {"name": "Unknown"})["name"]

#     @computed_field
#     @property
#     def status_description(self) -> str:
#         if self.status_code is None:
#             return "No status code received"
#         return STATUS_CODE_MAP.get(self.status_code, {"description": "Unknown status code"})["description"]

#     @computed_field
#     @property
#     def fault_name(self) -> str:
#         code = self.fault_code or 0
#         return FAULT_CODE_MAP.get(code, {"name": "Unknown Fault"})["name"]

#     @computed_field
#     @property
#     def fault_description(self) -> str:
#         code = self.fault_code or 0
#         return FAULT_CODE_MAP.get(code, {"description": "Unknown fault code"})["description"]

#     @computed_field
#     @property
#     def has_fault(self) -> bool:
#         return (
#             (self.fault or 0) == 1
#             or (self.fault_code or 0) > 0
#             or self.status_code == 4
#         )

#     model_config = ConfigDict(from_attributes=True)
class MotorTelemetryCreate(BaseModel):
    # Fallback to defaults instead of crashing backend
    timestamp: Optional[int] = Field(default=0)
    freq: Optional[float] = Field(default=0.0)
    current: Optional[float] = Field(default=0.0)
    voltage: Optional[float] = Field(default=0.0)
    dcbus: Optional[float] = Field(default=0.0)
    power: Optional[float] = Field(default=0.0)
    energy_in: Optional[float] = Field(default=0.0)
    
    # Yahan sirf Pydantic Enum aur Field use hoga, SQLAlchemy nahi
    trigger_type: Optional[TriggerType] = Field(default=TriggerType.physical)
    
    fault: Optional[int] = Field(default=0)
    fault_code: Optional[int] = Field(default=0)
    status_code: Optional[int] = Field(default=0)

    reference_freq: Optional[float] = Field(default=0.0)
    motor_speed: Optional[float] = Field(default=0.0)
    power_percent: Optional[float] = Field(default=0.0)
    torque_percent: Optional[float] = Field(default=0.0)
    is_live: Optional[int] = Field(default=0)

    @field_validator("is_live", "fault")
    @classmethod
    def validate_binary_flags(cls, value: Optional[int]) -> int:
        val = value if value is not None else 0
        if val not in (0, 1):
            return 0  
        return val

    @field_validator("fault_code")
    @classmethod
    def validate_fault_code(cls, value: Optional[int]) -> int:
        val = value if value is not None else 0
        if val not in FAULT_CODE_MAP:
            return 0  
        return val

    @field_validator("status_code")
    @classmethod
    def validate_status_code(cls, value: Optional[int]) -> int:
        val = value if value is not None else 0
        if val not in STATUS_CODE_MAP:
            return 0  
        return val

    @field_validator(
        "freq", "current", "voltage", "dcbus", "power", "energy_in",
        "reference_freq", "motor_speed", "power_percent", "torque_percent",
        mode="before"
    )
    @classmethod
    def validate_non_negative_numeric_fields(cls, value):
        if value is None: 
            return 0.0
        try:
            val = float(value)
            return val if val >= 0 else 0.0
        except (ValueError, TypeError):
            return 0.0 

    model_config = ConfigDict(from_attributes=True)


class MotorTelemetryResponse(BaseModel):
    id: UUID
    device_id: UUID
    created_at: datetime 
    timestamp: int

    freq: float
    current: float
    voltage: float
    dcbus: float
    power: float
    energy_in: Optional[float]

    # API Response me trigger_type bhi dikhana zaroori hai
    trigger_type: TriggerType

    fault: Optional[int]
    fault_code: Optional[int]
    status_code: Optional[int]

    reference_freq: float
    motor_speed: float
    power_percent: float
    torque_percent: float

    is_live: int

    @computed_field
    @property
    def status_name(self) -> str:
        if self.status_code is None:
            return "Unknown"
        return STATUS_CODE_MAP.get(self.status_code, {"name": "Unknown"})["name"]

    @computed_field
    @property
    def status_description(self) -> str:
        if self.status_code is None:
            return "No status code received"
        return STATUS_CODE_MAP.get(self.status_code, {"description": "Unknown status code"})["description"]

    @computed_field
    @property
    def fault_name(self) -> str:
        code = self.fault_code or 0
        return FAULT_CODE_MAP.get(code, {"name": "Unknown Fault"})["name"]

    @computed_field
    @property
    def fault_description(self) -> str:
        code = self.fault_code or 0
        return FAULT_CODE_MAP.get(code, {"description": "Unknown fault code"})["description"]

    @computed_field
    @property
    def has_fault(self) -> bool:
        return (
            (self.fault or 0) == 1
            or (self.fault_code or 0) > 0
            or self.status_code == 4
        )

    model_config = ConfigDict(from_attributes=True)