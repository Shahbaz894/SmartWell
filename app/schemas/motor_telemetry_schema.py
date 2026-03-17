from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class MotorTelemetryBase(BaseModel):

    output_frequency: float
    reference_frequency: float

    dc_bus_voltage: float
    output_voltage: float
    output_current: float

    motor_speed: float

    power_load: float
    torque_load: float

    real_power: float


class MotorTelemetryCreate(MotorTelemetryBase):
    device_id: UUID


class MotorTelemetryResponse(MotorTelemetryBase):
    id: UUID
    device_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True