import json
import logging
import threading
import time
import uuid
from typing import Any, Dict, Optional

from jmqtt import MQTTMessage, QualityOfService as QoS

from database import Database
from .runtime_loader import RuntimeLoader


class PairingManagerHub:
    PAIRING_OPEN_TOPIC = "ir/pairing/open"
    PAIRING_OFFER_WILDCARD_TOPIC = "ir/pairing/offer/+/+"
    PAIRING_ACCEPT_TOPIC_PREFIX = "ir/pairing/accept"
    DEFAULT_WINDOW_SECONDS = 300

    def __init__(
        self,
        runtime_loader: RuntimeLoader,
        database: Database,
        sw_version: str,
        auto_open: bool = False,
    ) -> None:
        self._runtime_loader = runtime_loader
        self._database = database
        self._sw_version = str(sw_version or "").strip()
        self._auto_open = bool(auto_open)

        self._logger = logging.getLogger("pairing_manager_hub")
        self._lock = threading.Lock()
        self._running = False
        self._subscribed = False
        self._session_id: Optional[str] = None
        self._nonce: Optional[str] = None
        self._expires_at = 0.0
        self._close_timer: Optional[threading.Timer] = None

    def start(self) -> None:
        connection = self._runtime_loader.mqtt_connection()
        if connection is None:
            return

        with self._lock:
            if self._running:
                return
            self._running = True

        connection.subscribe(self.PAIRING_OFFER_WILDCARD_TOPIC, self._on_offer, qos=QoS.AtLeastOnce)
        with self._lock:
            self._subscribed = True

        if self._auto_open:
            try:
                self.open_pairing(duration_seconds=self.DEFAULT_WINDOW_SECONDS)
            except Exception as exc:
                self._logger.warning(f"Failed to auto-open pairing: {exc}")

    def stop(self) -> None:
        self.close_pairing()
        connection = self._runtime_loader.mqtt_connection()

        with self._lock:
            self._running = False
            subscribed = self._subscribed
            self._subscribed = False

        if connection is not None and subscribed:
            try:
                connection.unsubscribe(self.PAIRING_OFFER_WILDCARD_TOPIC)
            except Exception as exc:
                self._logger.warning(f"Failed to unsubscribe hub pairing wildcard topic: {exc}")

    def open_pairing(self, duration_seconds: int = DEFAULT_WINDOW_SECONDS) -> Dict[str, Any]:
        connection = self._runtime_loader.mqtt_connection()
        if connection is None:
            raise RuntimeError("mqtt_not_connected")

        duration = int(duration_seconds or 0)
        if duration < 10:
            duration = 10
        if duration > 3600:
            duration = 3600

        session_id = uuid.uuid4().hex
        nonce = uuid.uuid4().hex
        expires_at = time.time() + duration

        mqtt_status = self._runtime_loader.status()
        hub_topic = str(mqtt_status.get("base_topic") or "")
        hub_id = str(mqtt_status.get("node_id") or "").strip() or self._runtime_loader.technical_name

        payload = {
            "session_id": session_id,
            "nonce": nonce,
            "hub_id": hub_id,
            "hub_name": self._runtime_loader.readable_name,
            "hub_topic": hub_topic,
            "sw_version": self._sw_version,
            "expires_at": expires_at,
        }

        connection.publish(
            self.PAIRING_OPEN_TOPIC,
            json.dumps(payload, separators=(",", ":")),
            qos=QoS.AtLeastOnce,
            retain=True,
        )

        with self._lock:
            self._session_id = session_id
            self._nonce = nonce
            self._expires_at = expires_at
            if self._close_timer is not None:
                self._close_timer.cancel()
            timer = threading.Timer(duration, self._auto_close_pairing, args=(session_id,))
            timer.daemon = True
            timer.start()
            self._close_timer = timer

        return self.status()

    def close_pairing(self) -> Dict[str, Any]:
        connection = self._runtime_loader.mqtt_connection()

        with self._lock:
            self._session_id = None
            self._nonce = None
            self._expires_at = 0.0
            timer = self._close_timer
            self._close_timer = None
        if timer is not None:
            timer.cancel()

        if connection is not None:
            try:
                connection.publish(self.PAIRING_OPEN_TOPIC, "", qos=QoS.AtLeastOnce, retain=True)
            except Exception as exc:
                self._logger.warning(f"Failed to clear retained pairing open topic: {exc}")

        return self.status()

    def status(self) -> Dict[str, Any]:
        with self._lock:
            session_id = self._session_id
            expires_at = self._expires_at
            running = self._running
        return {
            "running": running,
            "open": bool(session_id),
            "session_id": session_id,
            "expires_at": expires_at if session_id else None,
        }

    def _auto_close_pairing(self, session_id: str) -> None:
        with self._lock:
            active = self._session_id
        if active != session_id:
            return
        self.close_pairing()

    def _on_offer(self, connection: Any, client: Any, userdata: Any, message: MQTTMessage) -> None:
        session_from_topic, agent_uid_from_topic = self._parse_offer_topic(message.topic)
        if not session_from_topic or not agent_uid_from_topic:
            return

        with self._lock:
            active_session = self._session_id
            active_nonce = self._nonce
            expires_at = self._expires_at

        now = time.time()
        if not active_session or not active_nonce or now >= expires_at:
            return
        if session_from_topic != active_session:
            return

        payload = self._parse_payload(message)
        if payload is None:
            return

        payload_nonce = str(payload.get("nonce") or "").strip()
        if payload_nonce != active_nonce:
            return

        payload_session_id = str(payload.get("session_id") or "").strip()
        if payload_session_id and payload_session_id != active_session:
            return

        agent_uid = str(payload.get("agent_uid") or "").strip() or agent_uid_from_topic
        if agent_uid != agent_uid_from_topic:
            return

        agent_name = str(payload.get("readable_name") or payload.get("agent_name") or "").strip() or agent_uid
        agent_topic = str(payload.get("base_topic") or payload.get("agent_topic") or "").strip()
        agent_sw_version = str(payload.get("sw_version") or "").strip()
        if not self._is_compatible(agent_sw_version):
            return

        self._database.agents.upsert(
            agent_id=agent_uid,
            name=agent_name,
            transport="mqtt",
            status="online",
            can_send=bool(payload.get("can_send")),
            can_learn=bool(payload.get("can_learn")),
            sw_version=agent_sw_version,
            agent_topic=agent_topic,
            last_seen=now,
        )

        hub_status = self._runtime_loader.status()
        accept_payload = {
            "session_id": active_session,
            "nonce": active_nonce,
            "agent_uid": agent_uid,
            "hub_id": hub_status.get("node_id") or self._runtime_loader.technical_name,
            "hub_name": self._runtime_loader.readable_name,
            "hub_topic": hub_status.get("base_topic"),
            "sw_version": self._sw_version,
            "accepted_at": now,
        }
        accept_topic = f"{self.PAIRING_ACCEPT_TOPIC_PREFIX}/{active_session}/{agent_uid}"
        connection.publish(
            accept_topic,
            json.dumps(accept_payload, separators=(",", ":")),
            qos=QoS.AtLeastOnce,
            retain=False,
        )

    def _parse_offer_topic(self, topic: str) -> tuple[str, str]:
        parts = str(topic or "").split("/")
        if len(parts) != 5:
            return "", ""
        if parts[0] != "ir" or parts[1] != "pairing" or parts[2] != "offer":
            return "", ""
        return parts[3].strip(), parts[4].strip()

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

    def _is_compatible(self, agent_sw_version: str) -> bool:
        hub_major = self._major_version(self._sw_version)
        agent_major = self._major_version(agent_sw_version)
        if not hub_major or not agent_major:
            return True
        return hub_major == agent_major

    def _major_version(self, value: str) -> str:
        normalized = str(value or "").strip()
        if not normalized:
            return ""
        return normalized.split(".", maxsplit=1)[0]
