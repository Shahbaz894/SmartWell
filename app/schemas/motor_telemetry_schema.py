from datetime import datetime

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator


STATUS_CODE_MAP = {
    0: { "name": "Motor Off", "description": "Motor is stopped", },
    1: {
        "name": "Forward Running",
        "description": "Motor/device is running in forward direction",
    },
    2: {
        "name": "Reverse Running",
        "description": "Motor/device is running in reverse direction",
    },
    3: {
        "name": "Standby",
        "description": "Device is idle, no movement",
    },
    4: {
        "name": "Fault",
        "description": "Error condition detected",
    },
    5: {
        "name": "Power Off",
        "description": "Device is powered off or shut down",
    },
}


FAULT_CODE_MAP = {
    0: {
        "name": "No Fault",
        "description": "Drive operating normally",
    },
    1: {
        "name": "OUT1",
        "description": "Output phase fault. Possible motor cable disconnect, loose output terminal, or missing motor phase.",
    },
    2: {
        "name": "OUT2",
        "description": "Output abnormality. Possible motor short circuit or output wiring issue.",
    },
    3: {
        "name": "OUT3",
        "description": "Output phase imbalance. Possible open motor phase or motor winding damage.",
    },
    4: {
        "name": "OC1",
        "description": "Acceleration overcurrent. Possible short acceleration time, heavy load, or jammed motor.",
    },
    5: {
        "name": "OC2",
        "description": "Deceleration overcurrent. Possible short deceleration time or high inertia load.",
    },
    6: {
        "name": "OC3",
        "description": "Constant speed overcurrent. Possible mechanical overload or motor rated current exceeded.",
    },
    7: {
        "name": "OV1",
        "description": "Acceleration overvoltage. DC bus voltage too high during acceleration.",
    },
    8: {
        "name": "OV2",
        "description": "Deceleration overvoltage. Possible fast deceleration or missing braking resistor.",
    },
    9: {
        "name": "OV3",
        "description": "Constant overvoltage. DC bus voltage too high during normal operation.",
    },
    10: {
        "name": "UV",
        "description": "Under voltage. Possible weak supply or loose input cable.",
    },
    11: {
        "name": "OL1",
        "description": "Motor overload. Motor current too high for long duration.",
    },
    12: {
        "name": "OL2",
        "description": "Drive overload. Load may exceed VFD capacity.",
    },
    13: {
        "name": "SPI",
        "description": "Internal communication fault.",
    },
    14: {
        "name": "SPO",
        "description": "Output protection triggered.",
    },
    15: {
        "name": "OH1",
        "description": "Drive overheat. Possible cooling fan failure or poor ventilation.",
    },
    16: {
        "name": "OH2",
        "description": "Motor overheat. Motor thermal protection triggered.",
    },
    17: {
        "name": "EF",
        "description": "External fault. External safety device triggered.",
    },
    18: {
        "name": "CE",
        "description": "Communication error.",
    },
    19: {
        "name": "ItE",
        "description": "Current detection error.",
    },
}



class MotorTelemetryCreate(BaseModel):
    # Added Optional to fields so partial MQTT packets don't crash validation
    timestamp: Optional[int] = Field(default=0)
    freq: Optional[float] = Field(default=0.0)
    current: Optional[float] = Field(default=0.0)
    voltage: Optional[float] = Field(default=0.0)
    dcbus: Optional[float] = Field(default=0.0)
    power: Optional[float] = Field(default=0.0)
    energy_in: Optional[float] = Field(default=0.0)
    
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
            return 0 # Fallback to 0 instead of crashing
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
        # FIX: Explicitly allowed 0
        if val not in STATUS_CODE_MAP:
            return 0
        return val

    @field_validator(
        "freq", "current", "voltage", "dcbus", "power",
        "reference_freq", "motor_speed", "power_percent", "torque_percent",
        mode="before"
    )
    @classmethod
    def validate_non_negative_numeric_fields(cls, value):
        if value is None: return 0.0
        val = float(value)
        return val if val >= 0 else 0.0

    model_config = ConfigDict(from_attributes=True)
    

    @field_validator("is_live")
    @classmethod
    def validate_is_live(cls, value: int) -> int:
        """
        Validate live flag.

        The backend stores this field as integer, so ESP32 should send
        1 for live telemetry and 0 for offline stored telemetry.
        """
        if value not in (0, 1):
            raise ValueError("is_live must be 0 or 1")
        return value

    @field_validator("fault")
    @classmethod
    def validate_fault(cls, value: Optional[int]) -> int:
        """
        Validate fault flag.

        0 means no active fault.
        1 means fault is active.
        """
        if value is None:
            return 0

        if value not in (0, 1):
            raise ValueError("fault must be 0 or 1")

        return value

    @field_validator("fault_code")
    @classmethod
    def validate_fault_code(cls, value: Optional[int]) -> int:
        """
        Validate ED510 fault code.

        Current supported range is 0 to 19 because ESP32 sends this range.
        """
        if value is None:
            return 0

        if value not in FAULT_CODE_MAP:
            raise ValueError("fault_code must be between 0 and 19")

        return value

    
    @field_validator("status_code")
    @classmethod
    def validate_status_code(cls, value: Optional[int]) -> int:

        if value is None:
            return 0

        if value not in STATUS_CODE_MAP:
            raise ValueError(
                "status_code must be one of 0,1,2,3,4,5"
            )

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
        """
        Validate telemetry numeric values.

        These values should not be negative in normal VFD telemetry.
        """
        if value is None:
            return value

        if float(value) < 0:
            raise ValueError("Telemetry numeric values must be non-negative")

        return value


class MotorTelemetryResponse(BaseModel):
    """
    Telemetry response schema.

    This response includes raw telemetry values and computed labels for:
    - status code
    - fault code
    """

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
        """
        Human-readable name for status_code.
        """
        if self.status_code is None:
            return "Unknown"

        return STATUS_CODE_MAP.get(
            self.status_code,
            {"name": "Unknown"},
        )["name"]

    @computed_field
    @property
    def status_description(self) -> str:
        """
        Human-readable description for status_code.
        """
        if self.status_code is None:
            return "No status code received"

        return STATUS_CODE_MAP.get(
            self.status_code,
            {"description": "Unknown status code"},
        )["description"]

    @computed_field
    @property
    def fault_name(self) -> str:
        """
        Human-readable name for fault_code.
        """
        code = self.fault_code or 0

        return FAULT_CODE_MAP.get(
            code,
            {"name": "Unknown Fault"},
        )["name"]

    @computed_field
    @property
    def fault_description(self) -> str:
        """
        Human-readable description for fault_code.
        """
        code = self.fault_code or 0

        return FAULT_CODE_MAP.get(
            code,
            {"description": "Unknown fault code"},
        )["description"]

    @computed_field
    @property
    def has_fault(self) -> bool:
        """
        True when the telemetry indicates a fault.

        A fault is active if:
        - fault is 1
        - fault_code is greater than 0
        - status_code is 4
        """
        return (
            (self.fault or 0) == 1
            or (self.fault_code or 0) > 0
            or self.status_code == 4
        )

    model_config = ConfigDict(from_attributes=True)