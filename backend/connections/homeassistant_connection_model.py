from dataclasses import dataclass
from typing import Literal, Optional


ConnectionRole = Literal["hub", "agent"]


@dataclass
class HomeAssistantConnectionModel:
    role: ConnectionRole
    enabled: bool
    origin_name: str
    schedule_resolution: float = 1.0
    publish_timeout: Optional[float] = 5.0

    @property
    def is_homeassistant_configured(self) -> bool:
        return self.role == "hub" and bool(self.enabled)
