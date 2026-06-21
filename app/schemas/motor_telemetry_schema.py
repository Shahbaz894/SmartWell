from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator
from app.schemas.enums import TriggerType

# Global Maps
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
    1: {"name": "OUT1", "description": "Output phase fault."},
    2: {"name": "OUT2", "description": "Output abnormality."},
    3: {"name": "OUT3", "description": "Output phase imbalance."},
    4: {"name": "OC1", "description": "Acceleration overcurrent."},
    5: {"name": "OC2", "description": "Deceleration overcurrent."},
    6: {"name": "OC3", "description": "Constant speed overcurrent."},
    7: {"name": "OV1", "description": "Acceleration overvoltage."},
    8: {"name": "OV2", "description": "Deceleration overvoltage."},
    9: {"name": "OV3", "description": "Constant overvoltage."},
    10: {"name": "UV", "description": "Under voltage."},
    11: {"name": "OL1", "description": "Motor overload."},
    12: {"name": "OL2", "description": "Drive overload."},
    13: {"name": "SPI", "description": "Internal communication fault."},
    14: {"name": "SPO", "description": "Output protection triggered."},
    15: {"name": "OH1", "description": "Drive overheat."},
    16: {"name": "OH2", "description": "Motor overheat."},
    17: {"name": "EF", "description": "External fault."},
    18: {"name": "CE", "description": "Communication error."},
    19: {"name": "ItE", "description": "Current detection error."},
}

class MotorTelemetryCreate(BaseModel):
    timestamp: Optional[int] = Field(default=0)
    freq: Optional[float] = Field(default=0.0)
    current: Optional[float] = Field(default=0.0)
    voltage: Optional[float] = Field(default=0.0)
    dcbus: Optional[float] = Field(default=0.0)
    power: Optional[float] = Field(default=0.0)
    energy_in: Optional[float] = Field(default=0.0)
    
    # Enum field using TriggerType
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
        return val if val in (0, 1) else 0

    @field_validator("fault_code")
    @classmethod
    def validate_fault_code(cls, value: Optional[int]) -> int:
        val = value if value is not None else 0
        return val if val in FAULT_CODE_MAP else 0

    @field_validator("status_code")
    @classmethod
    def validate_status_code(cls, value: Optional[int]) -> int:
        val = value if value is not None else 0
        return val if val in STATUS_CODE_MAP else 0

    @field_validator(
        "freq", "current", "voltage", "dcbus", "power", "energy_in",
        "reference_freq", "motor_speed", "power_percent", "torque_percent",
        mode="before"
    )
    @classmethod
    def validate_non_negative_numeric_fields(cls, value):
        try:
            val = float(value)
            return val if val >= 0 else 0.0
        except (ValueError, TypeError):
            return 0.0

    model_config = ConfigDict(from_attributes=True)


class MotorTelemetryResponse(MotorTelemetryCreate):
    id: UUID
    device_id: str
    created_at: datetime 
    # trigger_type is inherited from MotorTelemetryCreate but we redefine it to ensure it's required
    trigger_type: TriggerType 

    @computed_field
    @property
    def status_name(self) -> str:
        return STATUS_CODE_MAP.get(self.status_code or 0, {"name": "Unknown"})["name"]

    @computed_field
    @property
    def status_description(self) -> str:
        return STATUS_CODE_MAP.get(self.status_code or 0, {"description": "Unknown"})["description"]

    @computed_field
    @property
    def fault_name(self) -> str:
        return FAULT_CODE_MAP.get(self.fault_code or 0, {"name": "Unknown"})["name"]

    @computed_field
    @property
    def fault_description(self) -> str:
        return FAULT_CODE_MAP.get(self.fault_code or 0, {"description": "Unknown"})["description"]

    @computed_field
    @property
    def has_fault(self) -> bool:
        return (self.fault == 1 or (self.fault_code or 0) > 0 or self.status_code == 4)

    model_config = ConfigDict(from_attributes=True,
                              use_enum_values=True)