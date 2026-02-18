from dataclasses import dataclass
from typing import Literal


ConnectionRole = Literal["hub", "agent"]


@dataclass
class MQTTConnectionModel:
    role: ConnectionRole
    host: str
    port: int
    username: str
    password: str
    instance: str
    readable_name: str

    @property
    def technical_name(self) -> str:
        return f"ir-{self.role}"

    @property
    def app_name(self) -> str:
        return self.technical_name

    @property
    def base_topic(self) -> str:
        if not self.instance:
            return self.technical_name
        return f"{self.technical_name}/{self.instance}"

    @property
    def availability_topic(self) -> str:
        return f"{self.base_topic}/{self.role}/status"

    @property
    def is_mqtt_configured(self) -> bool:
        return bool(self.host)
