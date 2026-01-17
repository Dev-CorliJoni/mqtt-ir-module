from typing import Optional
from pydantic import BaseModel, Field


class RemoteUpdate(BaseModel):
    name: str = Field(..., min_length=1, description="Human readable remote name")

    # These are optional transmit parameters. They can stay NULL until you add a sender.
    carrier_hz: Optional[int] = Field(default=None, description="Carrier frequency in Hz (e.g. 38000)")
    duty_cycle: Optional[int] = Field(default=None, description="Duty cycle in percent (1..100)")

    icon: Optional[str] = Field(default=None, description="MDI icon key (UI)")

    assigned_agent_id: Optional[str] = Field(default=None, description="Assigned agent id for routing")
    
