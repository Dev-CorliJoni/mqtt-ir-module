from typing import Optional
from pydantic import BaseModel, Field


class RemoteUpdate(BaseModel):
    name: str = Field(..., min_length=1, description="Human readable remote name")

    # These are optional transmit parameters. They can stay NULL until you add a sender.
    carrier_hz: Optional[int] = Field(default=None, description="Carrier frequency in Hz (e.g. 38000)")
    duty_cycle: Optional[int] = Field(default=None, description="Duty cycle in percent (1..100)")
    gap_us_default: Optional[int] = Field(default=None, description="Default gap between frames/files in microseconds")

    icon: Optional[str] = Field(default=None, description="MDI icon key (UI)")
    