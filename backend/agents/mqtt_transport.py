from typing import Dict, Any


class MqttTransport:
    def learn_capture(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        raise RuntimeError("MQTT transport is not configured")

    def send(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        raise RuntimeError("MQTT transport is not configured")
