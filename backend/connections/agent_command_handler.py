import json
import logging
import threading
import time
from typing import Any, Dict, Optional

from jmqtt import MQTTMessage, QualityOfService as QoS

from agents.local_agent import LocalAgent
from .agent_binding_store import AgentBindingStore
from .runtime_loader import RuntimeLoader


class AgentCommandHandler:
    COMMAND_TOPIC_PREFIX = "ir/agents"
    RESPONSE_TOPIC_PREFIX = "ir/hubs"

    def __init__(
        self,
        runtime_loader: RuntimeLoader,
        binding_store: AgentBindingStore,
        local_agent: LocalAgent,
    ) -> None:
        self._runtime_loader = runtime_loader
        self._binding_store = binding_store
        self._local_agent = local_agent
        self._logger = logging.getLogger("agent_command_handler")
        self._lock = threading.Lock()
        self._running = False
        self._subscribed_topic = ""

    def start(self) -> None:
        connection = self._runtime_loader.mqtt_connection()
        if connection is None:
            return

        agent_uid = self._agent_uid()
        if not agent_uid:
            return

        topic = f"{self.COMMAND_TOPIC_PREFIX}/{agent_uid}/cmd/#"
        connection.subscribe(topic, self._on_command, qos=QoS.AtLeastOnce)
        with self._lock:
            self._running = True
            self._subscribed_topic = topic

    def stop(self) -> None:
        connection = self._runtime_loader.mqtt_connection()
        with self._lock:
            topic = self._subscribed_topic
            self._subscribed_topic = ""
            self._running = False

        if connection is None or not topic:
            return

        try:
            connection.unsubscribe(topic)
        except Exception as exc:
            self._logger.warning(f"Failed to unsubscribe command topic {topic}: {exc}")

    def _on_command(self, connection: Any, client: Any, userdata: Any, message: MQTTMessage) -> None:
        expected_agent_uid = self._agent_uid()
        agent_uid_from_topic, command = self._parse_command_topic(message.topic)
        if not expected_agent_uid or not agent_uid_from_topic or agent_uid_from_topic != expected_agent_uid:
            return
        if command not in ("send", "learn/start", "learn/capture", "learn/stop"):
            return

        payload = self._parse_payload(message)
        if payload is None:
            return

        request_id = str(payload.get("request_id") or "").strip()
        request_hub_id = str(payload.get("hub_id") or "").strip()
        if not request_id or not request_hub_id:
            return

        binding_hub_id = self._binding_store.hub_id()
        if not binding_hub_id or request_hub_id != binding_hub_id:
            return

        response_topic = f"{self.RESPONSE_TOPIC_PREFIX}/{request_hub_id}/agents/{expected_agent_uid}/resp/{request_id}"

        try:
            result = self._execute_command(command=command, payload=payload)
            response = {
                "request_id": request_id,
                "ok": True,
                "result": result,
                "responded_at": time.time(),
            }
        except TimeoutError as exc:
            response = self._error_response(
                request_id=request_id,
                code="timeout",
                message=str(exc),
                status_code=408,
            )
        except ValueError as exc:
            response = self._error_response(
                request_id=request_id,
                code="validation_error",
                message=str(exc),
                status_code=400,
            )
        except RuntimeError as exc:
            response = self._error_response(
                request_id=request_id,
                code="runtime_error",
                message=str(exc),
                status_code=409,
            )
        except Exception as exc:
            response = self._error_response(
                request_id=request_id,
                code="internal_error",
                message=str(exc),
                status_code=500,
            )

        try:
            connection.publish(
                response_topic,
                json.dumps(response, separators=(",", ":")),
                qos=QoS.AtLeastOnce,
                retain=False,
            )
        except Exception as exc:
            self._logger.warning(f"Failed to publish command response topic={response_topic}: {exc}")

    def _execute_command(self, command: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if command == "send":
            return self._local_agent.send(payload)

        if command == "learn/start":
            session = payload.get("session")
            if session is None:
                session = {}
            if not isinstance(session, dict):
                raise ValueError("session must be an object")
            return self._local_agent.learn_start(session)

        if command == "learn/capture":
            return self._local_agent.learn_capture(payload)

        if command == "learn/stop":
            session = payload.get("session")
            if session is None:
                session = {}
            if not isinstance(session, dict):
                raise ValueError("session must be an object")
            return self._local_agent.learn_stop(session)

        raise ValueError("Unknown command")

    def _parse_command_topic(self, topic: str) -> tuple[str, str]:
        parts = str(topic or "").split("/")
        if len(parts) < 5:
            return "", ""
        if parts[0] != "ir" or parts[1] != "agents" or parts[3] != "cmd":
            return "", ""
        agent_uid = parts[2].strip()
        command = "/".join(p.strip() for p in parts[4:] if p.strip())
        return agent_uid, command

    def _parse_payload(self, message: MQTTMessage) -> Optional[Dict[str, Any]]:
        value = message.json_value
        if isinstance(value, dict):
            return value
        if not message.text:
            return None
        try:
            parsed = json.loads(message.text)
        except Exception:
            return None
        if not isinstance(parsed, dict):
            return None
        return parsed

    def _agent_uid(self) -> str:
        client_id = str(self._runtime_loader.mqtt_client_id() or "").strip()
        if client_id:
            return client_id
        runtime_status = self._runtime_loader.status()
        fallback = str(runtime_status.get("client_id") or runtime_status.get("node_id") or "").strip()
        return fallback

    def _error_response(self, request_id: str, code: str, message: str, status_code: int) -> Dict[str, Any]:
        return {
            "request_id": request_id,
            "ok": False,
            "error": {
                "code": str(code),
                "message": str(message),
                "status_code": int(status_code),
            },
            "responded_at": time.time(),
        }
