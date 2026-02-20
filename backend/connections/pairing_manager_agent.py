import json
import logging
import threading
import time
from typing import Any, Dict, Optional

from jmqtt import MQTTMessage, QualityOfService as QoS

from database.schemas.settings import Settings
from .runtime_loader import RuntimeLoader


class PairingManagerAgent:
    PAIRING_OPEN_TOPIC = "ir/pairing/open"
    PAIRING_OFFER_TOPIC_PREFIX = "ir/pairing/offer"
    PAIRING_ACCEPT_TOPIC_PREFIX = "ir/pairing/accept"
    DEFAULT_LISTEN_WINDOW_SECONDS = 300

    def __init__(
        self,
        runtime_loader: RuntimeLoader,
        settings_store: Settings,
        readable_name: str,
        sw_version: str,
        can_send: bool,
        can_learn: bool,
        reset_binding: bool = False,
    ) -> None:
        self._runtime_loader = runtime_loader
        self._settings_store = settings_store
        self._readable_name = str(readable_name or "").strip()
        self._sw_version = str(sw_version or "").strip()
        self._can_send = bool(can_send)
        self._can_learn = bool(can_learn)
        self._reset_binding = bool(reset_binding)

        self._logger = logging.getLogger("pairing_manager_agent")
        self._lock = threading.Lock()
        self._running = False
        self._subscribed_open = False
        self._subscribed_accept = False
        self._listen_timer: Optional[threading.Timer] = None

    def start(self) -> None:
        connection = self._runtime_loader.mqtt_connection()
        if connection is None:
            return

        if self._reset_binding:
            self._clear_binding()

        with self._lock:
            if self._running:
                return
            self._running = True

        if self._is_bound():
            return

        connection.subscribe(self.PAIRING_OPEN_TOPIC, self._on_pairing_open, qos=QoS.AtLeastOnce)
        connection.subscribe(self._accept_topic_wildcard(), self._on_pairing_accept, qos=QoS.AtLeastOnce)
        with self._lock:
            self._subscribed_open = True
            self._subscribed_accept = True
            if self._listen_timer is not None:
                self._listen_timer.cancel()
            timer = threading.Timer(self.DEFAULT_LISTEN_WINDOW_SECONDS, self._stop_listening_if_unbound)
            timer.daemon = True
            timer.start()
            self._listen_timer = timer

    def stop(self) -> None:
        connection = self._runtime_loader.mqtt_connection()
        with self._lock:
            self._running = False
            subscribed_open = self._subscribed_open
            subscribed_accept = self._subscribed_accept
            self._subscribed_open = False
            self._subscribed_accept = False
            timer = self._listen_timer
            self._listen_timer = None
        if timer is not None:
            timer.cancel()

        if connection is None:
            return

        try:
            if subscribed_open:
                connection.unsubscribe(self.PAIRING_OPEN_TOPIC)
            if subscribed_accept:
                connection.unsubscribe(self._accept_topic_wildcard())
        except Exception as exc:
            self._logger.warning(f"Failed to unsubscribe agent pairing topics: {exc}")

    def status(self) -> Dict[str, Any]:
        binding = self._binding_data()
        with self._lock:
            running = self._running
            listening = self._subscribed_open or self._subscribed_accept

        return {
            "running": running,
            "paired": bool(binding.get("pairing_hub_id")),
            "listening": listening,
            **binding,
        }

    def _on_pairing_open(self, connection: Any, client: Any, userdata: Any, message: MQTTMessage) -> None:
        if self._is_bound():
            return

        payload = self._parse_payload(message)
        if payload is None:
            return

        session_id = str(payload.get("session_id") or "").strip()
        nonce = str(payload.get("nonce") or "").strip()
        if not session_id or not nonce:
            return

        expires_at = float(payload.get("expires_at") or 0.0)
        if expires_at <= 0 or time.time() >= expires_at:
            return

        hub_sw_version = str(payload.get("sw_version") or "").strip()
        if not self._is_compatible(hub_sw_version):
            return

        agent_uid = self._agent_uid()
        if not agent_uid:
            return

        runtime_status = self._runtime_loader.status()
        offer_payload = {
            "session_id": session_id,
            "nonce": nonce,
            "agent_uid": agent_uid,
            "readable_name": self._agent_name(agent_uid),
            "base_topic": runtime_status.get("base_topic"),
            "sw_version": self._sw_version,
            "can_send": self._can_send,
            "can_learn": self._can_learn,
            "offered_at": time.time(),
        }
        offer_topic = f"{self.PAIRING_OFFER_TOPIC_PREFIX}/{session_id}/{agent_uid}"
        connection.publish(
            offer_topic,
            json.dumps(offer_payload, separators=(",", ":")),
            qos=QoS.AtLeastOnce,
            retain=False,
        )

    def _on_pairing_accept(self, connection: Any, client: Any, userdata: Any, message: MQTTMessage) -> None:
        if self._is_bound():
            return

        expected_agent_uid = self._agent_uid()
        session_id_from_topic, agent_uid_from_topic = self._parse_accept_topic(message.topic)
        if not session_id_from_topic or not expected_agent_uid or agent_uid_from_topic != expected_agent_uid:
            return

        payload = self._parse_payload(message)
        if payload is None:
            return

        payload_session = str(payload.get("session_id") or "").strip()
        payload_nonce = str(payload.get("nonce") or "").strip()
        if payload_session and payload_session != session_id_from_topic:
            return
        if not payload_nonce:
            return

        self._settings_store.set("pairing_hub_id", str(payload.get("hub_id") or ""))
        self._settings_store.set("pairing_hub_topic", str(payload.get("hub_topic") or ""))
        self._settings_store.set("pairing_hub_name", str(payload.get("hub_name") or ""))
        self._settings_store.set("pairing_session_id", session_id_from_topic)
        self._settings_store.set("pairing_nonce", payload_nonce)
        self._settings_store.set("pairing_accepted_at", str(payload.get("accepted_at") or ""))

        self._stop_listening(connection)

    def _stop_listening(self, connection: Any) -> None:
        with self._lock:
            subscribed_open = self._subscribed_open
            subscribed_accept = self._subscribed_accept
            self._subscribed_open = False
            self._subscribed_accept = False
            timer = self._listen_timer
            self._listen_timer = None
        if timer is not None:
            timer.cancel()

        try:
            if subscribed_open:
                connection.unsubscribe(self.PAIRING_OPEN_TOPIC)
            if subscribed_accept:
                connection.unsubscribe(self._accept_topic_wildcard())
        except Exception as exc:
            self._logger.warning(f"Failed to stop pairing listeners: {exc}")

    def _stop_listening_if_unbound(self) -> None:
        if self._is_bound():
            return
        connection = self._runtime_loader.mqtt_connection()
        if connection is None:
            with self._lock:
                self._subscribed_open = False
                self._subscribed_accept = False
                self._listen_timer = None
            return
        self._stop_listening(connection)

    def _accept_topic_wildcard(self) -> str:
        agent_uid = self._agent_uid()
        if not agent_uid:
            return f"{self.PAIRING_ACCEPT_TOPIC_PREFIX}/+/unknown"
        return f"{self.PAIRING_ACCEPT_TOPIC_PREFIX}/+/{agent_uid}"

    def _parse_accept_topic(self, topic: str) -> tuple[str, str]:
        parts = str(topic or "").split("/")
        if len(parts) != 5:
            return "", ""
        if parts[0] != "ir" or parts[1] != "pairing" or parts[2] != "accept":
            return "", ""
        return parts[3].strip(), parts[4].strip()

    def _is_bound(self) -> bool:
        hub_id = self._settings_store.get("pairing_hub_id", default="") or ""
        return bool(str(hub_id).strip())

    def _clear_binding(self) -> None:
        self._settings_store.set("pairing_hub_id", "")
        self._settings_store.set("pairing_hub_topic", "")
        self._settings_store.set("pairing_hub_name", "")
        self._settings_store.set("pairing_session_id", "")
        self._settings_store.set("pairing_nonce", "")
        self._settings_store.set("pairing_accepted_at", "")

    def _binding_data(self) -> Dict[str, Any]:
        return {
            "pairing_hub_id": self._settings_store.get("pairing_hub_id", default=""),
            "pairing_hub_topic": self._settings_store.get("pairing_hub_topic", default=""),
            "pairing_hub_name": self._settings_store.get("pairing_hub_name", default=""),
            "pairing_session_id": self._settings_store.get("pairing_session_id", default=""),
            "pairing_nonce": self._settings_store.get("pairing_nonce", default=""),
            "pairing_accepted_at": self._settings_store.get("pairing_accepted_at", default=""),
        }

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

    def _is_compatible(self, hub_sw_version: str) -> bool:
        hub_major = self._major_version(hub_sw_version)
        agent_major = self._major_version(self._sw_version)
        if not hub_major or not agent_major:
            return True
        return hub_major == agent_major

    def _major_version(self, value: str) -> str:
        normalized = str(value or "").strip()
        if not normalized:
            return ""
        return normalized.split(".", maxsplit=1)[0]

    def _agent_uid(self) -> str:
        client_id = str(self._runtime_loader.mqtt_client_id() or "").strip()
        if client_id:
            return client_id
        runtime_status = self._runtime_loader.status()
        fallback = str(runtime_status.get("client_id") or runtime_status.get("node_id") or "").strip()
        return fallback

    def _agent_name(self, agent_uid: str) -> str:
        readable = str(self._readable_name or "").strip()
        if readable:
            return readable
        return agent_uid
