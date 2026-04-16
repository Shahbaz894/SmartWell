from pydantic import BaseModel, Field


class VFDResetRequest(BaseModel):
    """
    Request payload for resetting VFD settings.
    """
    confirm: bool = Field(..., description="Must be true to allow VFD reset")


class VFDReferenceFrequencyRequest(BaseModel):
    """
    Request payload for setting VFD reference frequency.
    """
    reference_frequency: float = Field(
        ...,
        gt=0,
        le=500,
        description="Reference frequency value to send to VFD",
    )


class VFDCommandResponse(BaseModel):
    """
    Generic response for VFD command operations.
    """
    message: str
    device_id: str
    command: str