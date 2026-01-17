import threading
from typing import Dict, Any

from .local_transport import LocalTransport


class LocalAgent:
    def __init__(self, transport: LocalTransport, agent_id: str = "local", name: str = "Local Agent") -> None:
        self._transport = transport
        self._agent_id = agent_id
        self._name = name
        self._learning_active = False
        self._lock = threading.Lock()
        self._capabilities = {
            "canLearn": True,
            "formatRaw": True,
            "maxPayloadBytes": 65536,
        }

    @property
    def agent_id(self) -> str:
        return self._agent_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def transport(self) -> str:
        return "local"

    @property
    def capabilities(self) -> Dict[str, Any]:
        return dict(self._capabilities)

    def send(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            if self._learning_active:
                raise RuntimeError("Cannot send while learning is active")
        return self._transport.send(payload)

    def learn_start(self, session: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            self._learning_active = True
        return {"ok": True}

    def learn_stop(self, session: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            self._learning_active = False
        return {"ok": True}

    def learn_capture(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        timeout_ms = int(payload.get("timeout_ms") or 0)
        if timeout_ms <= 0:
            raise ValueError("timeout_ms must be > 0")
        with self._lock:
            if not self._learning_active:
                raise RuntimeError("Learning session is not running")
        return self._transport.learn_capture(timeout_ms)

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            learning_active = self._learning_active
        return {
            "agent_id": self._agent_id,
            "name": self._name,
            "transport": self.transport,
            "status": "online",
            "busy": {"learning": learning_active, "sending": False},
            "capabilities": self.capabilities,
        }
